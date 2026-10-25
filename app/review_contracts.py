"""M2-R review records. These identify human reviews, never execution permission."""
from __future__ import annotations

import json
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictBytes, ValidationError, field_validator, model_validator

from app.baseline_contracts import (
    MAX_INPUT, MAX_SEQUENCE, ERROR_CODES, Digest, EffectiveReviewV1, M0Error,
    ProjectRecordV1, Sequence, ShortText, Text, Timestamp, UUIDText, Version, parse_json,
)
from app.plan_contracts import PLAN_CODES, PlanAssessmentV1, PlanError, PlanModel, parse_plan, canonical_plan_bytes
from app.artifact_contracts import ARTIFACT_CODES, ArtifactAssessmentV1, ArtifactError, parse_artifact_package, canonical_artifact_bytes

POLICY_VERSION = 'm2r-review-v1'
MAX_RECORD = 65536
REVIEW_CODES = tuple(dict.fromkeys((*ERROR_CODES, 'AUTHORITY_MISMATCH',
    'STORE_IDENTITY_MISMATCH', 'SUBJECT_CONFLICT', 'PARENT_NOT_REVIEWED',
    'STALE_AUTHORITY', 'LOCAL_CONTEXT_REQUIRED')))
Kind = Literal['plan', 'package']
Note = Annotated[Text, Field(max_length=2048)]
PositiveSequence = Annotated[Sequence, Field(ge=1)]
BlockerCode = Literal['BASELINE_NOT_ACTIVE', 'PLAN_STRUCTURALLY_BLOCKED',
    'PACKAGE_STRUCTURALLY_BLOCKED', 'PLAN_NOT_APPROVED', 'PACKAGE_NOT_APPROVED',
    'BASELINE_APPROVAL_CHANGED', 'PARENT_PLAN_APPROVAL_CHANGED']


class ReviewError(Exception):
    def __init__(self, code: str, *, source: str = 'm2r'):
        catalogs = {'m0': ERROR_CODES, 'm1': PLAN_CODES, 'm2': ARTIFACT_CODES, 'm2r': REVIEW_CODES}
        if source not in catalogs or code not in catalogs[source]:
            raise ValueError('Unknown review error code')
        self.code, self.source = code, source
        self.interrupted = False  # Local exit semantics; never a persisted/wire field.
        self.message = code.replace('_', ' ').capitalize()
        super().__init__(self.message)

    def as_dict(self) -> dict[str, str]:
        return dict(source=self.source, code=self.code, pointer='', message=self.message)


def translated(exc: M0Error | PlanError | ArtifactError) -> ReviewError:
    return ReviewError(exc.code, source=getattr(exc, 'source', 'm0'))


def canonical_review_bytes(value: object, *, limit: int = MAX_RECORD) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode='json')
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        parse_json(raw, limit)
        return raw
    except M0Error as exc:
        raise ReviewError(exc.code) from None
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ReviewError('INVALID_INPUT') from None


class ReviewModel(PlanModel):
    @model_validator(mode='wrap')
    @classmethod
    def safe_validation(cls, value, handler):
        try:
            result = handler(value)
            limit = MAX_INPUT if cls.__name__ in ('HistoryPageV1', 'PlanReviewAssessmentV1', 'PackageReviewAssessmentV1') else MAX_RECORD
            canonical_review_bytes(result, limit=limit)
            return result
        except (M0Error, PlanError, ArtifactError) as exc:
            if isinstance(exc, (M0Error, PlanError)) and exc.code in REVIEW_CODES:
                raise ReviewError(exc.code) from None
            raise translated(exc) from None
        except ValidationError as exc:
            code = 'LIMIT_EXCEEDED' if any(e['type'] in ('too_long', 'string_too_long') for e in exc.errors(include_input=False)) else 'INVALID_INPUT'
            raise ReviewError(code) from None


class StoreMetadataV1(ReviewModel):
    schema_version: Version
    store_id: UUIDText
    project: ProjectRecordV1
    created_at: Timestamp
    policy_version: Literal['m2r-review-v1']


class ReviewSubjectV1(ReviewModel):
    schema_version: Version
    project_id: UUIDText
    kind: Kind
    subject_digest: Digest
    baseline_digest: Digest
    plan_digest: Digest

    @model_validator(mode='after')
    def identity(self) -> Self:
        if self.kind == 'plan' and self.subject_digest != self.plan_digest:
            raise ReviewError('INVALID_REFERENCE')
        return self


class StoredReviewSubjectV1(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra='forbid', revalidate_instances='always')
    schema_version: Version
    subject: ReviewSubjectV1
    registered_at: Timestamp
    canonical_content: Annotated[StrictBytes, Field(max_length=MAX_INPUT)]

    @model_validator(mode='after')
    def content_identity(self) -> Self:
        s = self.subject
        if s.kind == 'plan':
            value = parse_plan(self.canonical_content)
            fields = value.project_id, value.baseline_digest, value.digest
            canonical = canonical_plan_bytes(value)
        else:
            value = parse_artifact_package(self.canonical_content)
            fields = value.manifest.project_id, value.manifest.baseline_digest, value.manifest.plan_digest
            canonical = canonical_artifact_bytes(value)
        if fields != (s.project_id, s.baseline_digest, s.plan_digest) or value.digest != s.subject_digest or canonical != self.canonical_content:
            raise ReviewError('SUBJECT_CONFLICT')
        return self

    @model_validator(mode='wrap')
    @classmethod
    def safe_validation(cls, value, handler):
        try:
            return handler(value)
        except (M0Error, PlanError, ArtifactError) as exc:
            raise translated(exc) from None
        except ValidationError as exc:
            code = 'LIMIT_EXCEEDED' if any(e['type'] == 'bytes_too_long' for e in exc.errors(include_input=False)) else 'INVALID_INPUT'
            raise ReviewError(code) from None

    def model_copy(self, *, update=None, deep=False):
        data = self.model_dump(mode='python')
        data.update(update or {})
        return type(self).model_validate(data)

    def copy(self, *, include=None, exclude=None, update=None, deep=False):
        if include is not None or exclude is not None:
            raise ReviewError('INVALID_INPUT')
        return self.model_copy(update=update, deep=deep)


class ReviewCommandV1(ReviewModel):
    schema_version: Version
    project_id: UUIDText
    kind: Kind
    subject_digest: Digest
    request_id: UUIDText
    expected_sequence: Sequence
    expected_m0_sequence: Sequence | None
    decision: Literal['approve', 'reject', 'revoke']
    note: Note | None

    @model_validator(mode='after')
    def dependencies(self) -> Self:
        if (self.decision == 'approve') != (self.expected_m0_sequence is not None):
            raise ReviewError('INVALID_INPUT')
        if self.note is not None and not self.note.strip():
            raise ReviewError('INVALID_INPUT')
        return self


class ReviewDecisionV1(ReviewCommandV1):
    store_id: UUIDText
    sequence: PositiveSequence
    recorded_at: Timestamp
    reviewer_label: ShortText
    previous_decision_sequence: PositiveSequence | None
    baseline_approval_sequence: PositiveSequence | None
    parent_plan_approval_sequence: PositiveSequence | None

    @model_validator(mode='after')
    def tokens(self) -> Self:
        approval = self.decision == 'approve'
        if (self.sequence != self.expected_sequence + 1
                or (self.previous_decision_sequence is not None and self.previous_decision_sequence >= self.sequence)
                or approval != (self.baseline_approval_sequence is not None)
                or (approval and self.kind == 'package') != (self.parent_plan_approval_sequence is not None)
                or (self.parent_plan_approval_sequence is not None and self.parent_plan_approval_sequence >= self.sequence)
                or (approval and self.baseline_approval_sequence > self.expected_m0_sequence)):
            raise ReviewError('INVALID_INPUT')
        return self


class RegistrationV1(ReviewModel):
    schema_version: Version
    subject: ReviewSubjectV1
    created: StrictBool


class HistoryPageV1(ReviewModel):
    schema_version: Version
    store_id: UUIDText
    project_id: UUIDText
    observed_sequence: Sequence
    decisions: Annotated[tuple[ReviewDecisionV1, ...], Field(max_length=1000)]
    next_after_sequence: PositiveSequence | None

    @model_validator(mode='after')
    def ordering(self) -> Self:
        sequences = [d.sequence for d in self.decisions]
        if (sequences != sorted(set(sequences)) or any(d.project_id != self.project_id or d.store_id != self.store_id or d.sequence > self.observed_sequence for d in self.decisions)
                or self.next_after_sequence is not None and (not sequences or self.next_after_sequence != sequences[-1] or self.next_after_sequence >= self.observed_sequence)):
            raise ReviewError('INVALID_INPUT')
        return self


class PlanReviewAssessmentV1(ReviewModel):
    schema_version: Version
    policy_version: Literal['m2r-review-v1']
    subject: ReviewSubjectV1
    store_id: UUIDText
    review_sequence: Sequence
    raw_status: Literal['pending', 'approved', 'rejected', 'revoked']
    latest_decision_sequence: PositiveSequence | None
    baseline_review: EffectiveReviewV1
    baseline_approval_sequence: PositiveSequence | None
    plan_approval_sequence: PositiveSequence | None
    plan_assessment: PlanAssessmentV1
    blockers: tuple[BlockerCode, ...]
    plan_review_effective: StrictBool
    disposition: Literal['reviewed_for_package_review', 'blocked']
    closure_status: Literal['unverified']
    execution_authorized: Literal[False]

    @field_validator('execution_authorized', mode='before')
    @classmethod
    def no_execution(cls, value):
        if type(value) is not bool or value is not False:
            raise ReviewError('INVALID_INPUT')
        return False

    @model_validator(mode='after')
    def consistency(self) -> Self:
        if (self.subject.kind != 'plan' or self.blockers != tuple(sorted(set(self.blockers)))
                or self.plan_review_effective != (not self.blockers)
                or (self.disposition == 'reviewed_for_package_review') != self.plan_review_effective
                or (self.raw_status == 'pending') != (self.latest_decision_sequence is None)
                or self.plan_approval_sequence != (self.latest_decision_sequence if self.raw_status == 'approved' else None)
                or (self.baseline_approval_sequence is not None) != (self.raw_status == 'approved')
                or self.latest_decision_sequence is not None and self.latest_decision_sequence > self.review_sequence
                or (self.subject.project_id, self.subject.baseline_digest, self.subject.plan_digest) !=
                   (self.plan_assessment.project_id, self.plan_assessment.baseline_digest, self.plan_assessment.plan_digest)
                or (self.baseline_review.project_id, self.baseline_review.subject_digest) != (self.subject.project_id, self.subject.baseline_digest)):
            raise ReviewError('INVALID_INPUT')
        if self.plan_review_effective and (self.raw_status != 'approved' or self.plan_approval_sequence != self.latest_decision_sequence
                or self.baseline_review.status != 'approved' or self.baseline_review.active_digest != self.subject.baseline_digest
                or self.baseline_approval_sequence != self.baseline_review.decision_sequence
                or self.plan_assessment.disposition != 'ready_for_artifact_design'):
            raise ReviewError('INVALID_INPUT')
        return self


class PackageReviewAssessmentV1(ReviewModel):
    schema_version: Version
    policy_version: Literal['m2r-review-v1']
    subject: ReviewSubjectV1
    store_id: UUIDText
    review_sequence: Sequence
    raw_status: Literal['pending', 'approved', 'rejected', 'revoked']
    latest_decision_sequence: PositiveSequence | None
    baseline_review: EffectiveReviewV1
    baseline_approval_sequence: PositiveSequence | None
    parent_plan_approval_sequence: PositiveSequence | None
    plan_review: PlanReviewAssessmentV1
    artifact_assessment: ArtifactAssessmentV1
    blockers: tuple[BlockerCode, ...]
    plan_review_effective: StrictBool
    package_review_effective: StrictBool
    disposition: Literal['reviewed_for_later_validation', 'blocked']
    closure_status: Literal['unverified']
    execution_authorized: Literal[False]

    @field_validator('execution_authorized', mode='before')
    @classmethod
    def no_execution(cls, value):
        if type(value) is not bool or value is not False:
            raise ReviewError('INVALID_INPUT')
        return False

    @model_validator(mode='after')
    def consistency(self) -> Self:
        if (self.subject.kind != 'package' or self.blockers != tuple(sorted(set(self.blockers)))
                or self.package_review_effective != (not self.blockers)
                or (self.disposition == 'reviewed_for_later_validation') != self.package_review_effective
                or self.plan_review_effective != self.plan_review.plan_review_effective
                or (self.raw_status == 'pending') != (self.latest_decision_sequence is None)
                or (self.baseline_approval_sequence is not None) != (self.raw_status == 'approved')
                or (self.parent_plan_approval_sequence is not None) != (self.raw_status == 'approved')
                or self.latest_decision_sequence is not None and self.latest_decision_sequence > self.review_sequence
                or self.review_sequence != self.plan_review.review_sequence or self.store_id != self.plan_review.store_id
                or self.baseline_review != self.plan_review.baseline_review
                or self.artifact_assessment.plan_assessment != self.plan_review.plan_assessment
                or (self.subject.project_id, self.subject.baseline_digest, self.subject.plan_digest) !=
                   (self.plan_review.subject.project_id, self.plan_review.subject.baseline_digest, self.plan_review.subject.subject_digest)
                or (self.subject.project_id, self.subject.baseline_digest, self.subject.plan_digest, self.subject.subject_digest) !=
                   (self.artifact_assessment.project_id, self.artifact_assessment.baseline_digest, self.artifact_assessment.plan_digest, self.artifact_assessment.package_digest)):
            raise ReviewError('INVALID_INPUT')
        if self.package_review_effective and (self.raw_status != 'approved' or not self.plan_review_effective
                or self.parent_plan_approval_sequence != self.plan_review.plan_approval_sequence
                or self.baseline_approval_sequence != self.baseline_review.decision_sequence
                or self.artifact_assessment.disposition != 'ready_for_review_design'):
            raise ReviewError('INVALID_INPUT')
        return self


def parse_review_command(raw: bytes) -> ReviewCommandV1:
    try:
        return ReviewCommandV1.model_validate(parse_json(raw, MAX_RECORD))
    except M0Error as exc:
        raise ReviewError(exc.code) from None
