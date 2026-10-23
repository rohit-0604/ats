"""Strict, immutable M0 V1 contracts. Importing this module performs no I/O."""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
import math
import re
from typing import Annotated, Literal, TypeVar
from uuid import UUID
from pydantic import (
    AfterValidator, BaseModel, ConfigDict, Field, StrictInt, StrictStr,
    ValidationError, model_validator,
)
MAX_INPUT = 8 * 1024 * 1024
MAX_SEQUENCE = 9007199254740991
ERROR_CODES = (
    'INVALID_INPUT', 'UNKNOWN_FIELD', 'UNSUPPORTED_VERSION', 'LIMIT_EXCEEDED',
    'DUPLICATE_ID', 'INVALID_REFERENCE', 'PROJECT_EXISTS', 'UNKNOWN_PROJECT',
    'UNKNOWN_SUBJECT', 'PROJECT_MISMATCH', 'NOT_APPROVABLE', 'INVALID_TRANSITION',
    'LINEAGE_CONFLICT', 'PARENT_ID_LOSS', 'STALE_SEQUENCE', 'REQUEST_ID_CONFLICT',
    'SEQUENCE_EXHAUSTED', 'PATH_POLICY', 'STORE_EXISTS', 'STORE_NOT_FOUND',
    'STORE_BUSY', 'STORE_FAILURE', 'INTEGRITY_ERROR', 'RECOVERY_REQUIRED',
    'OUTPUT_FAILURE', 'COMMIT_OUTCOME_UNKNOWN',
)
class M0Error(Exception):
    """Safe errors contain no source input or underlying exception representation."""
    def __init__(self, code: str, pointer: str = ''):
        if code not in ERROR_CODES:
            raise ValueError('Unknown M0 error code')
        self.code = code
        self.pointer = pointer
        self.message = code.replace('_', ' ').capitalize()
        super().__init__(self.message)
    def as_dict(self):
        return dict(code=self.code, pointer=self.pointer, message=self.message)
def _text(value: str) -> str:
    if any(ord(c) < 32 and c not in '\t\n\r' or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise M0Error('INVALID_INPUT')
    return value
def _nonblank(value: str) -> str:
    if not value.strip():
        raise M0Error('INVALID_INPUT')
    return value
def _uuid(value: str) -> str:
    try:
        if str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, AttributeError):
        raise M0Error('INVALID_INPUT') from None
    return value
def _timestamp(value: str) -> str:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z', value):
        raise M0Error('INVALID_INPUT')
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        raise M0Error('INVALID_INPUT') from None
    return value
Text = Annotated[StrictStr, Field(max_length=16384), AfterValidator(_text)]
ShortText = Annotated[Text, Field(max_length=512), AfterValidator(_nonblank)]
Reference = Annotated[Text, Field(max_length=1024), AfterValidator(_nonblank)]
UUIDText = Annotated[ShortText, AfterValidator(_uuid)]
Digest = Annotated[StrictStr, Field(pattern=r'^sha256:[0-9a-f]{64}$')]
Sequence = Annotated[StrictInt, Field(ge=0, le=MAX_SEQUENCE)]
Version = Annotated[StrictInt, Field(ge=1, le=1)]
Timestamp = Annotated[StrictStr, AfterValidator(_timestamp)]
SourceKey = Annotated[StrictStr, Field(pattern=r'^[a-z0-9][a-z0-9._-]{0,63}$')]
Pointer = Annotated[Text, Field(max_length=1024, pattern=r'^(?:/(?:[^~]|~[01])*)*$')]
Ids = Annotated[tuple[UUIDText, ...], Field(max_length=64)]
def _tuples(value):
    if isinstance(value, list):
        return tuple(_tuples(v) for v in value)
    if isinstance(value, dict):
        return {k: _tuples(v) for k, v in value.items()}
    return value
class FrozenV1(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra='forbid', revalidate_instances='always')
    @model_validator(mode='before')
    @classmethod
    def boundary(cls, value):
        if isinstance(value, dict):
            if set(value) - set(cls.model_fields):
                raise M0Error('UNKNOWN_FIELD')
            if 'schema_version' in value:
                if type(value['schema_version']) is not int:
                    raise M0Error('INVALID_INPUT')
                if value['schema_version'] != 1:
                    raise M0Error('UNSUPPORTED_VERSION')
            return _tuples(value)
        return value
    def model_copy(self, *, update=None, deep=False):
        # Pydantic's default copy(update=...) deliberately skips validation.
        data = self.model_dump(mode='python')
        data.update(update or {})
        return validate_model(type(self), data)
    def copy(self, *, include=None, exclude=None, update=None, deep=False):
        if include is not None or exclude is not None:
            raise M0Error('INVALID_INPUT')
        return self.model_copy(update=update, deep=deep)
T = TypeVar('T', bound=FrozenV1)
def validate_model(cls: type[T], value) -> T:
    try:
        return cls.model_validate(value)
    except ValidationError as exc:
        code = 'LIMIT_EXCEEDED' if any(e['type'] in ('too_long', 'string_too_long') for e in exc.errors(include_input=False)) else 'INVALID_INPUT'
        raise M0Error(code) from None
def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise M0Error('INVALID_INPUT')
        obj[key] = value
    return obj
def parse_json(raw: bytes, limit: int = MAX_INPUT):
    if type(raw) is not bytes:
        raise M0Error('INVALID_INPUT')
    if len(raw) > limit:
        raise M0Error('LIMIT_EXCEEDED')
    try:
        text = raw.decode('utf-8-sig')
        depth = 0
        quoted = False
        escaped = False
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
                    raise M0Error('LIMIT_EXCEEDED')
            elif c in ']}':
                depth -= 1
        obj = json.loads(text, object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(M0Error('INVALID_INPUT')))
        stack = [obj]
        count = 0
        while stack:
            v = stack.pop()
            count += 1
            if count > 100000:
                raise M0Error('LIMIT_EXCEEDED')
            if isinstance(v, str):
                if len(v) > 16384:
                    raise M0Error('LIMIT_EXCEEDED')
                _text(v)
            elif isinstance(v, dict):
                for k in v:
                    if len(k) > 16384:
                        raise M0Error('LIMIT_EXCEEDED')
                    _text(k)
                stack.extend(v.values())
            elif isinstance(v, list):
                stack.extend(v)
            elif isinstance(v, float) and not math.isfinite(v):
                raise M0Error('INVALID_INPUT')
        return obj
    except (UnicodeError, ValueError, RecursionError):
        raise M0Error('INVALID_INPUT') from None
def _canonical_tree(value, key=''):
    if isinstance(value, BaseModel):
        value = value.model_dump(mode='json')
    if isinstance(value, dict):
        return {k: _canonical_tree(v, k) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        values = [_canonical_tree(v) for v in value]
        id_key = {'requirements': 'requirement_id', 'criteria': 'criterion_id', 'sources': 'evidence_id'}.get(key)
        if id_key:
            values.sort(key=lambda v: v[id_key])
        elif key in ('source_ids', 'dependency_ids'):
            values.sort()
        return values
    if isinstance(value, float):
        raise M0Error('INVALID_INPUT')
    return value
def canonical_bytes(value) -> bytes:
    return json.dumps(_canonical_tree(value), ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')
def digest_content(value) -> str:
    return 'sha256:' + hashlib.sha256(canonical_bytes(value)).hexdigest()
class ProjectRecordV1(FrozenV1):
    schema_version: Version
    project_id: UUIDText
    reviewer_label: Annotated[ShortText, Field(max_length=128)]
    created_at: Timestamp
class SourceEvidenceV1(FrozenV1):
    evidence_id: UUIDText
    kind: Literal['legacy_import', 'document', 'human_decision']
    reference: Reference
    content_digest: Digest | None
    excerpt: Annotated[Text, AfterValidator(_nonblank)]
    @model_validator(mode='after')
    def provenance(self):
        if (self.kind == 'human_decision') != (self.content_digest is None):
            raise M0Error('INVALID_INPUT')
        return self
class LegacyClaimV1(FrozenV1):
    source_key: SourceKey
    original_req_id: Annotated[ShortText, Field(max_length=256)]
    original_title: Text
    original_description: Text
    approved: bool | None
    rejected: bool | None
    gap_analysis: bool | None
    section_ref: Text | None
    source_chunk: Sequence | None
    human_prompt: Text | None
    claimed_pdf_sha256: Annotated[StrictStr, Field(pattern=r'^[a-fA-F0-9]{64}$')] | None
    input_digest: Digest
    json_pointer: Pointer
class RequirementRevisionV1(FrozenV1):
    requirement_id: UUIDText
    title: Annotated[Text, Field(max_length=512)]
    description: Text
    source_ids: Ids
    dependency_ids: Ids
    legacy: LegacyClaimV1 | None
class CriterionRevisionV1(FrozenV1):
    criterion_id: UUIDText
    requirement_id: UUIDText
    preconditions: Annotated[tuple[Annotated[Text, AfterValidator(_nonblank)], ...], Field(max_length=64)]
    action: Annotated[Text, AfterValidator(_nonblank)] | None
    expected_outcome: Annotated[Text, AfterValidator(_nonblank)] | None
    origin: Literal['legacy_extracted', 'inferred', 'human_authored']
    clarity: Literal['unresolved', 'specified']
    unresolved_reason: Text | None
    automation_support: Literal['unknown', 'supported', 'unsupported']
    support_reason: Text | None
    source_ids: Ids
    @model_validator(mode='after')
    def semantics(self):
        if self.clarity == 'specified':
            if not self.action or not self.action.strip() or not self.expected_outcome or not self.expected_outcome.strip() or self.unresolved_reason is not None:
                raise M0Error('INVALID_INPUT')
        elif not self.unresolved_reason or not self.unresolved_reason.strip():
            raise M0Error('INVALID_INPUT')
        if self.automation_support == 'unsupported':
            if not self.support_reason or not self.support_reason.strip():
                raise M0Error('INVALID_INPUT')
        elif self.support_reason is not None:
            raise M0Error('INVALID_INPUT')
        return self
def _unique(values):
    if len(values) != len(set(values)):
        raise M0Error('DUPLICATE_ID')
class BaselineDraftV1(FrozenV1):
    schema_version: Version
    project_id: UUIDText
    parent_digest: Digest | None
    requirements: Annotated[tuple[RequirementRevisionV1, ...], Field(min_length=1, max_length=1000)]
    criteria: Annotated[tuple[CriterionRevisionV1, ...], Field(max_length=5000)]
    sources: Annotated[tuple[SourceEvidenceV1, ...], Field(max_length=10000)]
    @model_validator(mode='after')
    def references(self):
        reqs = [v.requirement_id for v in self.requirements]
        sources = [v.evidence_id for v in self.sources]
        _unique(reqs)
        _unique(sources)
        _unique([v.criterion_id for v in self.criteria])
        req_set, src_set = set(reqs), set(sources)
        for r in self.requirements:
            _unique(r.source_ids)
            _unique(r.dependency_ids)
            if not set(r.source_ids) <= src_set or not set(r.dependency_ids) <= req_set or r.requirement_id in r.dependency_ids:
                raise M0Error('INVALID_REFERENCE')
        for c in self.criteria:
            _unique(c.source_ids)
            if c.requirement_id not in req_set or not set(c.source_ids) <= src_set:
                raise M0Error('INVALID_REFERENCE')
        return self
class BaselineSnapshotV1(BaselineDraftV1):
    digest: Digest
    @model_validator(mode='after')
    def integrity(self):
        body = self.model_dump(mode='json')
        body.pop('digest')
        if self.digest != digest_content(body):
            raise M0Error('INTEGRITY_ERROR')
        if len(canonical_bytes(self)) > MAX_INPUT:
            raise M0Error('LIMIT_EXCEEDED')
        # Python callers must not bypass the wire's aggregate node/depth limits
        # and insert a snapshot which a subsequent store load cannot decode.
        parse_json(canonical_bytes(self))
        return self
class ImportWarningV1(FrozenV1):
    code: Literal['LEGACY_APPROVAL_UNTRUSTED', 'MISSING_PROVENANCE', 'CRITERION_REVIEW_REQUIRED', 'METADATA_NOT_MIGRATED', 'BOM_REMOVED']
    pointer: Pointer
    message: ShortText
class ImportResultV1(FrozenV1):
    schema_version: Version
    draft: BaselineDraftV1
    input_digest: Digest
    warnings: Annotated[tuple[ImportWarningV1, ...], Field(max_length=20000)]
class ReviewCommandV1(FrozenV1):
    schema_version: Version
    project_id: UUIDText
    subject_digest: Digest
    decision: Literal['approve', 'reject', 'revoke']
    expected_sequence: Sequence
    request_id: UUIDText
    reason: Annotated[Text, AfterValidator(_nonblank)]
class ReviewDecisionV1(ReviewCommandV1):
    sequence: Annotated[Sequence, Field(ge=1)]
    reviewer_label: Annotated[ShortText, Field(max_length=128)]
    recorded_at: Timestamp
    previous_active_digest: Digest | None
    resulting_active_digest: Digest | None
class EffectiveReviewV1(FrozenV1):
    schema_version: Version
    project_id: UUIDText
    subject_digest: Digest
    status: Literal['pending', 'approved', 'rejected', 'revoked', 'superseded']
    decision_sequence: Sequence | None
    project_sequence: Sequence
    active_digest: Digest | None
    head_digest: Digest | None
class StoredSnapshotV1(FrozenV1):
    schema_version: Version
    project_id: UUIDText
    digest: Digest
    created: bool
class ValidationErrorV1(FrozenV1):
    code: Literal[ERROR_CODES]
    pointer: Pointer
    message: ShortText
class InspectionV1(FrozenV1):
    schema_version: Version
    project: ProjectRecordV1
    snapshot: BaselineSnapshotV1
    review: EffectiveReviewV1
class HistoryPageV1(FrozenV1):
    schema_version: Version
    project_id: UUIDText
    decisions: Annotated[tuple[ReviewDecisionV1, ...], Field(max_length=1000)]
    next_after_sequence: Sequence | None
class ValidationReportV1(FrozenV1):
    schema_version: Version
    structurally_valid: bool
    errors: tuple[ValidationErrorV1, ...]
    approval_blockers: tuple[ValidationErrorV1, ...]
    store_checks: Literal['not_performed']
