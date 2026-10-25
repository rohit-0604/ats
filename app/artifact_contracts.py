"""Bounded, immutable M2 byte inventories. Content is data, never executable authority."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import re
from typing import Annotated, Callable, Literal, Self
from uuid import UUID, uuid5

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError, field_validator, model_validator

from app.baseline_contracts import (
    MAX_INPUT, ERROR_CODES as M0_CODES, Digest, M0Error, ShortText, SourceKey,
    Text, UUIDText, Version,
)
from app.plan_contracts import PLAN_CODES, PlanAssessmentV1, PlanError

MAX_FILE = 1024 * 1024
MAX_TOTAL = 4 * MAX_FILE
MAX_ENCODED = 4 * ((MAX_FILE + 2) // 3)
POLICY_VERSION = 'm2-artifact-assessment-v1'
ARTIFACT_CODES = (
    'INVALID_INPUT', 'UNKNOWN_FIELD', 'UNSUPPORTED_VERSION', 'LIMIT_EXCEEDED',
    'DUPLICATE_ID', 'INVALID_REFERENCE', 'TEST_ID_MISMATCH', 'PATH_POLICY',
    'INVALID_BASE64', 'INTEGRITY_ERROR', 'AUTHORITY_MISMATCH', 'OUTPUT_FAILURE',
)


class ArtifactError(Exception):
    """Only static codes/messages and a fixed empty pointer cross this boundary."""

    def __init__(self, code: str, *, source: str = 'm2'):
        catalogs = {'m0': M0_CODES, 'm1': PLAN_CODES, 'm2': ARTIFACT_CODES}
        if source not in catalogs or code not in catalogs[source]:
            raise ValueError('Unknown artifact error code')
        self.source, self.code = source, code
        self.message = code.replace('_', ' ').capitalize()
        super().__init__(self.message)

    def as_dict(self) -> dict[str, str]:
        return dict(source=self.source, code=self.code, pointer='', message=self.message)


def _ordinary(value: str) -> None:
    if len(value) > 16384:
        raise ArtifactError('LIMIT_EXCEEDED')
    if any(ord(c) < 32 and c not in '\t\n\r' or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ArtifactError('INVALID_INPUT')


def _base64_size(value: str) -> int:
    # The encoded and projected raw size checks precede any decoder allocation.
    if len(value) > MAX_ENCODED:
        raise ArtifactError('LIMIT_EXCEEDED')
    if len(value) % 4 or re.fullmatch(r'[A-Za-z0-9+/]*={0,2}', value, flags=re.ASCII) is None:
        raise ArtifactError('INVALID_BASE64')
    size = len(value) // 4 * 3 - (len(value) - len(value.rstrip('=')))
    if size < 0:
        raise ArtifactError('INVALID_BASE64')
    if size > MAX_FILE:
        raise ArtifactError('LIMIT_EXCEEDED')
    return size


def decode_payload(value: str) -> bytes:
    """Decode at most one bounded file, checking exact canonical encoding."""
    size = _base64_size(value)
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ArtifactError('INVALID_BASE64') from None
    if len(raw) > MAX_FILE:
        raise ArtifactError('LIMIT_EXCEEDED')
    if len(raw) != size or base64.b64encode(raw).decode('ascii') != value:
        raise ArtifactError('INVALID_BASE64')
    return raw


def _large_paths(value: object, *, payload_record: bool = False) -> set[tuple[object, ...]]:
    """Only exact known root/entry shapes acquire the base64 string exception."""
    if not isinstance(value, dict):
        return set()
    if payload_record:
        return {('content_base64',)} if set(value) == {'path', 'content_base64'} else set()
    if set(value) not in ({'schema_version', 'manifest', 'payloads'},
                          {'schema_version', 'manifest', 'payloads', 'digest'}):
        return set()
    items = value.get('payloads')
    if not isinstance(items, (list, tuple)):
        return set()
    if len(items) > 256:
        raise ArtifactError('LIMIT_EXCEEDED')
    paths = set()
    total = 0
    for n, item in enumerate(items):
        if isinstance(item, BaseModel):
            item = item.model_dump(mode='python')
        if not isinstance(item, dict) or set(item) != {'path', 'content_base64'}:
            continue
        encoded = item['content_base64']
        if type(encoded) is str:
            total += _base64_size(encoded)
            if total > MAX_TOTAL:
                raise ArtifactError('LIMIT_EXCEEDED')
            paths.add(('payloads', n, 'content_base64'))
    return paths


def _tree(value: object, large: set[tuple[object, ...]], path: tuple[object, ...] = (),
          depth: int = 0, count: list[int] | None = None) -> object:
    count = [0] if count is None else count
    count[0] += 1
    if count[0] > 100000:
        raise ArtifactError('LIMIT_EXCEEDED')
    if isinstance(value, BaseModel):
        value = value.model_dump(mode='python')
    if type(value) is str:
        if path in large:
            _base64_size(value)
        else:
            _ordinary(value)
    elif type(value) in (dict, list, tuple):
        if depth >= 32:
            raise ArtifactError('LIMIT_EXCEEDED')
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise ArtifactError('INVALID_INPUT')
                _ordinary(key)
                result[key] = _tree(item, large, path + (key,), depth + 1, count)
            return result
        return tuple(_tree(item, large, path + (n,), depth + 1, count) for n, item in enumerate(value))
    elif type(value) is float:
        if not math.isfinite(value):
            raise ArtifactError('INVALID_INPUT')
    elif value is not None and type(value) not in (int, bool):
        raise ArtifactError('INVALID_INPUT')
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        _ordinary(key)
        if key in result:
            raise ArtifactError('INVALID_INPUT')
        result[key] = value
    return result


def _no_constant(_: str) -> None:
    raise ArtifactError('INVALID_INPUT')


def bounded_artifact_json(raw_bytes: bytes) -> object:
    """8 MiB before parse; standard JSON with narrow context-aware payload bounds."""
    if type(raw_bytes) is not bytes:
        raise ArtifactError('INVALID_INPUT')
    if len(raw_bytes) > MAX_INPUT:
        raise ArtifactError('LIMIT_EXCEEDED')
    try:
        text = raw_bytes.decode('utf-8')
        # Scan nesting before json.loads builds objects. Quoted delimiters are inert.
        depth, quoted, escaped = 0, False, False
        for c in text:
            if quoted:
                if escaped:
                    escaped = False
                elif c == '\\':
                    escaped = True
                elif c == '"':
                    quoted = False
            elif c == '"':
                quoted = True
            elif c in '[{':
                depth += 1
                if depth > 32:
                    raise ArtifactError('LIMIT_EXCEEDED')
            elif c in ']}':
                depth -= 1
        data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_no_constant)
        if type(data) is not dict:
            raise ArtifactError('INVALID_INPUT')
        return _tree(data, _large_paths(data))
    except (ValueError, UnicodeError, RecursionError):
        raise ArtifactError('INVALID_INPUT') from None


class ArtifactModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra='forbid', revalidate_instances='always')

    @model_validator(mode='before')
    @classmethod
    def boundary(cls, value: object) -> object:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode='python')
        if isinstance(value, dict):
            if set(value) - set(cls.model_fields):
                raise ArtifactError('UNKNOWN_FIELD')
            if 'schema_version' in value:
                if type(value['schema_version']) is not int:
                    raise ArtifactError('INVALID_INPUT')
                if value['schema_version'] != 1:
                    raise ArtifactError('UNSUPPORTED_VERSION')
            return _tree(value, _large_paths(value, payload_record=cls.__name__ == 'ArtifactPayloadV1'))
        return value

    @model_validator(mode='wrap')
    @classmethod
    def safe_validation(cls, value: object, handler: Callable[[object], Self]) -> Self:
        try:
            return handler(value)
        except (M0Error, PlanError):
            raise ArtifactError('INVALID_INPUT') from None
        except ValidationError as exc:
            oversized = any(e['type'] in ('too_long', 'string_too_long', 'too_short') for e in exc.errors(include_input=False))
            raise ArtifactError('LIMIT_EXCEEDED' if oversized else 'INVALID_INPUT') from None

    def model_copy(self, *, update: dict[str, object] | None = None, deep: bool = False) -> Self:
        data = self.model_dump(mode='python')
        data.update(update or {})
        return type(self).model_validate(data)

    def copy(self, *, include: object = None, exclude: object = None,
             update: dict[str, object] | None = None, deep: bool = False) -> Self:
        if include is not None or exclude is not None:
            raise ArtifactError('INVALID_INPUT')
        return self.model_copy(update=update, deep=deep)


def _path(value: str) -> str:
    if not 1 <= len(value) <= 240:
        raise ArtifactError('PATH_POLICY')
    for part in value.split('/'):
        if (re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', part, re.ASCII) is None
                or part.endswith('.') or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)):
            raise ArtifactError('PATH_POLICY')
    return value


LogicalPath = Annotated[StrictStr, AfterValidator(_path)]
ByteCount = Annotated[StrictInt, Field(ge=0, le=MAX_FILE)]
NonblankText = Annotated[Text, Field(min_length=1)]


def _unique(values: list[object]) -> None:
    if len(set(values)) != len(values):
        raise ArtifactError('DUPLICATE_ID')


class ArtifactFileV1(ArtifactModel):
    path: LogicalPath
    role: Literal['spec', 'helper', 'fixture', 'config', 'dependency_lock', 'runtime_descriptor', 'data']
    size_bytes: ByteCount
    digest: Digest


class ArtifactPayloadV1(ArtifactModel):
    path: LogicalPath
    content_base64: Annotated[StrictStr, Field(max_length=MAX_ENCODED)]

    @field_validator('content_base64')
    @classmethod
    def canonical_base64(cls, value: str) -> str:
        decode_payload(value)
        return value


class ConfigurationV1(ArtifactModel):
    configuration_key: SourceKey
    config_path: LogicalPath
    project_name: ShortText
    runtime_descriptor_path: LogicalPath
    dependency_lock_path: LogicalPath


class AssertionReferenceV1(ArtifactModel):
    path: LogicalPath
    start_byte: ByteCount
    end_byte: ByteCount
    criterion_id: UUIDText


class ArtifactTestV1(ArtifactModel):
    test_id: UUIDText
    scenario_id: UUIDText
    test_key: SourceKey
    spec_path: LogicalPath
    configuration_keys: Annotated[tuple[SourceKey, ...], Field(min_length=1, max_length=64)]
    assertions: Annotated[tuple[AssertionReferenceV1, ...], Field(min_length=1, max_length=64)]

    @model_validator(mode='after')
    def sets(self) -> Self:
        _unique(list(self.configuration_keys))
        _unique([(a.path, a.start_byte, a.end_byte, a.criterion_id) for a in self.assertions])
        return self


class ScenarioArtifactDispositionV1(ArtifactModel):
    scenario_id: UUIDText
    status: Literal['mapped', 'unbuilt']
    reason: NonblankText | None

    @field_validator('reason')
    @classmethod
    def reason_nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ArtifactError('INVALID_INPUT')
        return value


class _TestKey(ArtifactModel):
    project_id: UUIDText
    scenario_id: UUIDText
    test_key: SourceKey


def _json(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def test_id(project_id: str, scenario_id: str, test_key: str) -> str:
    key = _TestKey(project_id=project_id, scenario_id=scenario_id, test_key=test_key)
    return str(uuid5(UUID(key.scenario_id), _json(['ats-test-v1', key.project_id, key.test_key]).decode('utf-8')))


def _manifest_data(value: ArtifactManifestV1) -> dict:
    data = value.model_dump(mode='json')
    for field, key in (('files', 'path'), ('configurations', 'configuration_key'),
                       ('tests', 'test_id'), ('scenario_dispositions', 'scenario_id')):
        data[field].sort(key=lambda item: item[key])
    for test in data['tests']:
        test['configuration_keys'].sort()
        test['assertions'].sort(key=lambda a: (a['path'], a['start_byte'], a['end_byte'], a['criterion_id']))
    return data


class ArtifactManifestV1(ArtifactModel):
    schema_version: Version
    project_id: UUIDText
    baseline_digest: Digest
    plan_digest: Digest
    files: Annotated[tuple[ArtifactFileV1, ...], Field(min_length=1, max_length=256)]
    configurations: Annotated[tuple[ConfigurationV1, ...], Field(min_length=1, max_length=64)]
    tests: Annotated[tuple[ArtifactTestV1, ...], Field(max_length=5000)]
    scenario_dispositions: Annotated[tuple[ScenarioArtifactDispositionV1, ...], Field(min_length=1, max_length=5000)]

    @model_validator(mode='after')
    def references(self) -> Self:
        for values in ([f.path for f in self.files], [c.configuration_key for c in self.configurations],
                       [t.test_id for t in self.tests], [(t.scenario_id, t.test_key) for t in self.tests],
                       [s.scenario_id for s in self.scenario_dispositions]):
            _unique(values)
        folded = {f.path.lower() for f in self.files}
        if len(folded) != len(self.files):
            raise ArtifactError('PATH_POLICY')
        for path in folded:
            parts = path.split('/')
            if any('/'.join(parts[:n]) in folded for n in range(1, len(parts))):
                raise ArtifactError('PATH_POLICY')
        files = {f.path: f for f in self.files}
        configs = {c.configuration_key for c in self.configurations}
        for c in self.configurations:
            for path, role in ((c.config_path, 'config'), (c.runtime_descriptor_path, 'runtime_descriptor'),
                               (c.dependency_lock_path, 'dependency_lock')):
                if path not in files or files[path].role != role:
                    raise ArtifactError('INVALID_REFERENCE')
        used_specs = set()
        for t in self.tests:
            if t.test_id != test_id(self.project_id, t.scenario_id, t.test_key):
                raise ArtifactError('TEST_ID_MISMATCH')
            if t.spec_path not in files or files[t.spec_path].role != 'spec' or not set(t.configuration_keys) <= configs:
                raise ArtifactError('INVALID_REFERENCE')
            used_specs.add(t.spec_path)
            for a in t.assertions:
                if (a.path not in files or files[a.path].role not in ('spec', 'helper', 'fixture')
                        or not 0 <= a.start_byte < a.end_byte <= files[a.path].size_bytes):
                    raise ArtifactError('INVALID_REFERENCE')
        if used_specs != {f.path for f in self.files if f.role == 'spec'}:
            raise ArtifactError('INVALID_REFERENCE')
        if len(_json(_manifest_data(self))) > MAX_INPUT:
            raise ArtifactError('LIMIT_EXCEEDED')
        return self


def canonical_manifest_bytes(value: ArtifactManifestV1) -> bytes:
    value = ArtifactManifestV1.model_validate(value)
    return _json(_manifest_data(value))


def manifest_digest(value: ArtifactManifestV1) -> str:
    return 'sha256:' + hashlib.sha256(canonical_manifest_bytes(value)).hexdigest()


def _package_bytes(value: ArtifactCandidateV1) -> bytes:
    data = value.model_dump(mode='json')
    data['manifest'] = _manifest_data(value.manifest)
    data['payloads'].sort(key=lambda item: item['path'])
    return _json(data)


class ArtifactCandidateV1(ArtifactModel):
    schema_version: Version
    manifest: ArtifactManifestV1
    payloads: Annotated[tuple[ArtifactPayloadV1, ...], Field(min_length=1, max_length=256)]

    @model_validator(mode='after')
    def integrity(self) -> Self:
        _unique([p.path for p in self.payloads])
        files = {f.path: f for f in self.manifest.files}
        if files.keys() != {p.path for p in self.payloads}:
            raise ArtifactError('INTEGRITY_ERROR')
        total = 0
        for payload in self.payloads:
            raw = decode_payload(payload.content_base64)
            total += len(raw)
            if total > MAX_TOTAL:
                raise ArtifactError('LIMIT_EXCEEDED')
            file = files[payload.path]
            if len(raw) != file.size_bytes or 'sha256:' + hashlib.sha256(raw).hexdigest() != file.digest:
                raise ArtifactError('INTEGRITY_ERROR')
        if len(_package_bytes(self)) > MAX_INPUT:
            raise ArtifactError('LIMIT_EXCEEDED')
        return self


class ArtifactPackageV1(ArtifactCandidateV1):
    digest: Digest

    @model_validator(mode='after')
    def manifest_integrity(self) -> Self:
        if self.digest != manifest_digest(self.manifest):
            raise ArtifactError('INTEGRITY_ERROR')
        return self


def canonical_artifact_bytes(value: ArtifactCandidateV1) -> bytes:
    if not isinstance(value, (ArtifactCandidateV1, ArtifactPackageV1)):
        raise ArtifactError('INVALID_INPUT')
    cls = ArtifactPackageV1 if isinstance(value, ArtifactPackageV1) else ArtifactCandidateV1
    return _package_bytes(cls.model_validate(value))


def parse_artifact_candidate(raw_bytes: bytes) -> ArtifactCandidateV1:
    return ArtifactCandidateV1.model_validate(bounded_artifact_json(raw_bytes))


def parse_artifact_package(raw_bytes: bytes) -> ArtifactPackageV1:
    return ArtifactPackageV1.model_validate(bounded_artifact_json(raw_bytes))


class ArtifactIssueV1(ArtifactModel):
    code: Literal['PLAN_BLOCKED', 'SCENARIO_UNBUILT', 'CONFIGURATION_UNUSED', 'NO_TESTS']
    scenario_id: UUIDText | None
    configuration_key: SourceKey | None


Count = Annotated[StrictInt, Field(ge=0, le=320000)]


class ArtifactAssessmentV1(ArtifactModel):
    schema_version: Version
    policy_version: Literal['m2-artifact-assessment-v1']
    project_id: UUIDText
    baseline_digest: Digest
    plan_digest: Digest
    package_digest: Digest
    plan_assessment: PlanAssessmentV1
    issues: Annotated[tuple[ArtifactIssueV1, ...], Field(max_length=5066)]
    scenario_count: Annotated[Count, Field(ge=1, le=5000)]
    mapped_scenario_count: Annotated[Count, Field(le=5000)]
    unbuilt_scenario_count: Annotated[Count, Field(le=5000)]
    test_count: Annotated[Count, Field(le=5000)]
    configuration_count: Annotated[Count, Field(ge=1, le=64)]
    planned_pair_count: Count
    file_count: Annotated[Count, Field(ge=1, le=256)]
    disposition: Literal['ready_for_review_design', 'blocked']
    closure_status: Literal['unverified']
    bundle_approved: Literal[False]
    execution_authorized: Literal[False]

    @field_validator('bundle_approved', 'execution_authorized', mode='before')
    @classmethod
    def never_authorized(cls, value: object) -> bool:
        if type(value) is not bool or value is not False:
            raise ArtifactError('INVALID_INPUT')
        return False

    @model_validator(mode='after')
    def accounting(self) -> Self:
        if (self.scenario_count != self.mapped_scenario_count + self.unbuilt_scenario_count
                or (self.disposition == 'ready_for_review_design') != (not self.issues)
                or (self.project_id, self.baseline_digest, self.plan_digest) !=
                   (self.plan_assessment.project_id, self.plan_assessment.baseline_digest, self.plan_assessment.plan_digest)):
            raise ArtifactError('INVALID_INPUT')
        if self.disposition == 'ready_for_review_design' and (
                self.plan_assessment.disposition != 'ready_for_artifact_design'
                or self.unbuilt_scenario_count or not self.test_count):
            raise ArtifactError('INVALID_INPUT')
        if (self.mapped_scenario_count > self.test_count
                or not self.test_count <= self.planned_pair_count <= self.test_count * self.configuration_count):
            raise ArtifactError('INVALID_INPUT')
        return self
