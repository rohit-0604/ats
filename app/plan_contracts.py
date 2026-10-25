"""Immutable, bounded M1 plan records; no runtime imports or import-time effects."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Callable, Literal, Self, TypeVar
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from app.baseline_contracts import (
    MAX_INPUT, ERROR_CODES as M0_CODES, Digest, M0Error, Sequence, ShortText,
    SourceKey, Text, UUIDText, Version, parse_json,
)

POLICY_VERSION = 'm1-plan-admission-v1'
PLAN_CODES = (
    'INVALID_INPUT', 'UNKNOWN_FIELD', 'UNSUPPORTED_VERSION', 'LIMIT_EXCEEDED',
    'DUPLICATE_ID', 'INVALID_REFERENCE', 'SCENARIO_ID_MISMATCH',
    'DISPOSITION_CONFLICT', 'PLAN_DIGEST_MISMATCH', 'AUTHORITY_MISMATCH',
    'OUTPUT_FAILURE',
)
IssueCode = Literal['BASELINE_NOT_ACTIVE', 'CRITERION_UNPLANNED', 'NO_AUTOMATABLE_SCENARIOS']
NonblankText = Annotated[Text, Field(min_length=1)]


class PlanError(Exception):
    """Only fixed codes/messages and safe pointers cross the error boundary."""

    def __init__(self, code: str, pointer: str = '', *, source: str = 'm1'):
        if source not in ('m0', 'm1') or code not in (M0_CODES if source == 'm0' else PLAN_CODES):
            raise ValueError('Unknown plan error code')
        self.code, self.pointer, self.source = code, pointer, source
        self.message = code.replace('_', ' ').capitalize()
        super().__init__(self.message)

    def as_dict(self) -> dict[str, str]:
        return dict(source=self.source, code=self.code, pointer=self.pointer, message=self.message)


def bounded_json(raw: bytes) -> object:
    """Reuse the approved decoder, translating M1 input failures at this boundary."""
    try:
        return parse_json(raw, MAX_INPUT)
    except M0Error as exc:
        raise PlanError(exc.code) from None


def _tuple_tree(value: object, depth: int = 0, count: list[int] | None = None) -> object:
    # Direct Python callers must receive the wire's aggregate/depth protection too.
    count = [0] if count is None else count
    count[0] += 1
    if count[0] > 100000:
        raise PlanError('LIMIT_EXCEEDED')
    if isinstance(value, (dict, list, tuple)):
        if depth >= 32:
            raise PlanError('LIMIT_EXCEEDED')
        if isinstance(value, dict):
            return {key: _tuple_tree(item, depth + 1, count) for key, item in value.items()}
        return tuple(_tuple_tree(item, depth + 1, count) for item in value)
    return value


class PlanModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra='forbid', revalidate_instances='always')

    @model_validator(mode='before')
    @classmethod
    def boundary(cls, value: object) -> object:
        if isinstance(value, dict):
            if set(value) - set(cls.model_fields):
                raise PlanError('UNKNOWN_FIELD')
            if 'schema_version' in value:
                if type(value['schema_version']) is not int:
                    raise PlanError('INVALID_INPUT')
                if value['schema_version'] != 1:
                    raise PlanError('UNSUPPORTED_VERSION')
            return _tuple_tree(value)
        return value

    @model_validator(mode='wrap')
    @classmethod
    def safe_validation(cls, value: object, handler: Callable[[object], Self]) -> Self:
        try:
            return handler(value)
        except M0Error as exc:
            raise PlanError(exc.code) from None
        except ValidationError as exc:
            oversized = any(error['type'] in ('too_long', 'string_too_long')
                            for error in exc.errors(include_input=False))
            raise PlanError('LIMIT_EXCEEDED' if oversized else 'INVALID_INPUT') from None

    def model_copy(self, *, update: dict[str, object] | None = None, deep: bool = False) -> Self:
        data = self.model_dump(mode='python')
        data.update(update or {})
        return validate_plan_model(type(self), data)

    def copy(self, *, include: object = None, exclude: object = None,
             update: dict[str, object] | None = None, deep: bool = False) -> Self:
        if include is not None or exclude is not None:
            raise PlanError('INVALID_INPUT')
        return self.model_copy(update=update, deep=deep)


T = TypeVar('T', bound=PlanModel)


def validate_plan_model(cls: type[T], value: object) -> T:
    return cls.model_validate(value)


class _ScenarioKey(PlanModel):
    project_id: UUIDText
    criterion_id: UUIDText
    scenario_key: SourceKey


def scenario_id(project_id: str, criterion_id: str, scenario_key: str) -> str:
    subject = _ScenarioKey(project_id=project_id, criterion_id=criterion_id, scenario_key=scenario_key)
    name = json.dumps(['ats-scenario-v1', subject.project_id, subject.scenario_key],
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return str(uuid5(UUID(subject.criterion_id), name))


class ScenarioV1(PlanModel):
    scenario_id: UUIDText
    criterion_id: UUIDText
    scenario_key: SourceKey
    title: ShortText
    preconditions: Annotated[tuple[NonblankText, ...], Field(max_length=64)]
    steps: Annotated[tuple[NonblankText, ...], Field(min_length=1, max_length=64)]

    @field_validator('preconditions', 'steps')
    @classmethod
    def nonblank_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise PlanError('INVALID_INPUT')
        return values


class CriterionDispositionV1(PlanModel):
    criterion_id: UUIDText
    status: Literal['planned', 'unplanned', 'unsupported']
    reason: NonblankText | None

    @field_validator('reason')
    @classmethod
    def nonblank_reason(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise PlanError('INVALID_INPUT')
        return value


def _canonical(value: PlanModel) -> bytes:
    data = value.model_dump(mode='json')
    for field, key in (('scenarios', 'scenario_id'), ('dispositions', 'criterion_id')):
        if field in data:
            data[field].sort(key=lambda item: item[key])
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def canonical_plan_bytes(value: PlanModel) -> bytes:
    if not isinstance(value, (ScenarioPlanDraftV1, ScenarioPlanV1)):
        raise PlanError('INVALID_INPUT')
    raw = _canonical(value)
    bounded_json(raw)
    return raw


def plan_digest(draft: ScenarioPlanDraftV1) -> str:
    data = bounded_json(canonical_plan_bytes(draft))
    if not isinstance(data, dict):
        raise PlanError('INVALID_INPUT')
    data.pop('digest', None)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


class ScenarioPlanDraftV1(PlanModel):
    schema_version: Version
    project_id: UUIDText
    baseline_digest: Digest
    scenarios: Annotated[tuple[ScenarioV1, ...], Field(max_length=5000)]
    dispositions: Annotated[tuple[CriterionDispositionV1, ...], Field(min_length=1, max_length=5000)]

    @model_validator(mode='after')
    def identities_and_bounds(self) -> Self:
        for values in ([s.scenario_id for s in self.scenarios],
                       [(s.criterion_id, s.scenario_key) for s in self.scenarios],
                       [d.criterion_id for d in self.dispositions]):
            if len(set(values)) != len(values):
                raise PlanError('DUPLICATE_ID')
        for item in self.scenarios:
            if item.scenario_id != scenario_id(self.project_id, item.criterion_id, item.scenario_key):
                raise PlanError('SCENARIO_ID_MISMATCH')
        canonical_plan_bytes(self)
        return self


class ScenarioPlanV1(ScenarioPlanDraftV1):
    digest: Digest

    @model_validator(mode='after')
    def integrity(self) -> Self:
        if self.digest != plan_digest(self):
            raise PlanError('PLAN_DIGEST_MISMATCH')
        return self


class PlanIssueV1(PlanModel):
    code: IssueCode
    criterion_id: UUIDText | None
    scenario_id: UUIDText | None


Count = Annotated[Sequence, Field(le=5000)]


class PlanAssessmentV1(PlanModel):
    schema_version: Version
    policy_version: Literal['m1-plan-admission-v1']
    project_id: UUIDText
    baseline_digest: Digest
    plan_digest: Digest
    baseline_status: Literal['pending', 'approved', 'rejected', 'revoked', 'superseded']
    decision_sequence: Sequence | None
    project_sequence: Sequence
    active_digest: Digest | None
    head_digest: Digest | None
    disposition: Literal['ready_for_artifact_design', 'blocked']
    issues: Annotated[tuple[PlanIssueV1, ...], Field(max_length=5002)]
    total_criteria: Count
    planned_criteria: Count
    unplanned_criteria: Count
    unsupported_criteria: Count
    scenario_count: Count
    plan_approved: Literal[False]
    execution_authorized: Literal[False]

    @field_validator('plan_approved', 'execution_authorized', mode='before')
    @classmethod
    def never_authorized(cls, value: object) -> bool:
        if type(value) is not bool or value is not False:
            raise PlanError('INVALID_INPUT')
        return False

    @model_validator(mode='after')
    def accounting(self) -> Self:
        if self.total_criteria != self.planned_criteria + self.unplanned_criteria + self.unsupported_criteria:
            raise PlanError('INVALID_INPUT')
        if (self.disposition == 'ready_for_artifact_design') != (not self.issues):
            raise PlanError('INVALID_INPUT')
        return self


def parse_plan_draft(raw_bytes: bytes) -> ScenarioPlanDraftV1:
    return validate_plan_model(ScenarioPlanDraftV1, bounded_json(raw_bytes))


def parse_plan(raw_bytes: bytes) -> ScenarioPlanV1:
    return validate_plan_model(ScenarioPlanV1, bounded_json(raw_bytes))
