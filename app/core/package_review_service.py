"""Fresh M0 observations and deterministic review composition; no runtime integration."""
from __future__ import annotations

from functools import wraps
import os

from app.baseline_contracts import M0Error, InspectionV1
from app.plan_contracts import PlanError, parse_plan, canonical_plan_bytes
from app.artifact_contracts import ArtifactError, parse_artifact_package, canonical_artifact_bytes
from app.core.plan_policy import assess_plan, validate_plan_references
from app.core.artifact_policy import assess_artifact, validate_artifact_references, checked_inspection
from app.core.baseline_files import validate_path, write_export
from app.core.review_store import ReviewStore
from app.core.package_review_store import PackageReviewStore, ReviewSnapshot, LocalReviewContext, now
from app.review_contracts import (
    POLICY_VERSION, ReviewError, ReviewSubjectV1, StoredReviewSubjectV1,
    PlanReviewAssessmentV1, PackageReviewAssessmentV1, translated,
    StoreMetadataV1, RegistrationV1, ReviewCommandV1, ReviewDecisionV1,
)


def safe_errors(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (M0Error, PlanError, ArtifactError) as exc:
            raise translated(exc) from None
    return call


def _distinct(store: PackageReviewStore, baseline: ReviewStore) -> None:
    if not isinstance(baseline, ReviewStore):
        raise ReviewError('INVALID_INPUT')
    a, b = validate_path(store.path, database=True), validate_path(baseline.path, database=True)
    try:
        same = a == b or a.exists() and b.exists() and os.path.samefile(a, b)
    except OSError:
        raise ReviewError('PATH_POLICY') from None
    if same:
        raise ReviewError('STORE_IDENTITY_MISMATCH')


def _observe(view: ReviewSnapshot, subject: ReviewSubjectV1, baseline: ReviewStore) -> InspectionV1:
    observation = checked_inspection(baseline.inspect(subject.project_id, subject.baseline_digest))
    if observation.project != view.metadata.project:
        raise ReviewError('AUTHORITY_MISMATCH')
    return observation


@safe_errors
def initialize(store: PackageReviewStore, baseline: ReviewStore, project: str, digest: str) -> StoreMetadataV1:
    _distinct(store, baseline)
    observation = checked_inspection(baseline.inspect(project, digest))
    if observation.project.project_id != project or observation.snapshot.digest != digest:
        raise ReviewError('AUTHORITY_MISMATCH')
    return store.initialize(store.path, observation.project)


@safe_errors
def register_plan(store: PackageReviewStore, baseline: ReviewStore, raw: bytes) -> RegistrationV1:
    plan = parse_plan(raw)
    _distinct(store, baseline)
    view = store.snapshot(for_write=True)
    subject = ReviewSubjectV1(schema_version=1, project_id=plan.project_id, kind='plan',
        subject_digest=plan.digest, baseline_digest=plan.baseline_digest, plan_digest=plan.digest)
    observation = _observe(view, subject, baseline)
    validate_plan_references(plan, observation.snapshot)
    stored = StoredReviewSubjectV1(schema_version=1, subject=subject, registered_at=now(),
                                   canonical_content=canonical_plan_bytes(plan))
    return store.register(stored, observation.project)


@safe_errors
def register_package(store: PackageReviewStore, baseline: ReviewStore, raw: bytes) -> RegistrationV1:
    package = parse_artifact_package(raw)
    _distinct(store, baseline)
    view = store.snapshot(for_write=True)
    plan = parse_plan(view.subject('plan', package.manifest.plan_digest).canonical_content)
    subject = ReviewSubjectV1(schema_version=1, project_id=package.manifest.project_id, kind='package',
        subject_digest=package.digest, baseline_digest=package.manifest.baseline_digest, plan_digest=plan.digest)
    observation = _observe(view, subject, baseline)
    validate_artifact_references(package, plan, observation.snapshot)
    stored = StoredReviewSubjectV1(schema_version=1, subject=subject, registered_at=now(),
                                   canonical_content=canonical_artifact_bytes(package))
    return store.register(stored, observation.project)


def _status(decision) -> str:
    return {'approve': 'approved', 'reject': 'rejected', 'revoke': 'revoked'}[decision.decision] if decision else 'pending'


def _plan_review(view, stored, observation) -> PlanReviewAssessmentV1:
    subject = stored.subject
    plan = parse_plan(stored.canonical_content)
    structural = assess_plan(plan, observation)
    d = view.latest('plan', subject.subject_digest)
    approved = d is not None and d.decision == 'approve'
    active = observation.review.status == 'approved' and observation.review.active_digest == subject.baseline_digest
    token = observation.review.decision_sequence if active else None
    blockers = set()
    if not active:
        blockers.add('BASELINE_NOT_ACTIVE')
    if structural.disposition != 'ready_for_artifact_design':
        blockers.add('PLAN_STRUCTURALLY_BLOCKED')
    if not approved:
        blockers.add('PLAN_NOT_APPROVED')
    if approved and d.baseline_approval_sequence != token:
        blockers.add('BASELINE_APPROVAL_CHANGED')
    return PlanReviewAssessmentV1(schema_version=1, policy_version=POLICY_VERSION, subject=subject,
        store_id=view.metadata.store_id, review_sequence=view.sequence, raw_status=_status(d),
        latest_decision_sequence=d.sequence if d else None, baseline_review=observation.review,
        baseline_approval_sequence=d.baseline_approval_sequence if approved else None,
        plan_approval_sequence=d.sequence if approved else None, plan_assessment=structural,
        blockers=tuple(sorted(blockers)), plan_review_effective=not blockers,
        disposition='blocked' if blockers else 'reviewed_for_package_review',
        closure_status='unverified', execution_authorized=False)


def _package_review(view, stored, observation) -> PackageReviewAssessmentV1:
    s = stored.subject
    parent = view.subject('plan', s.plan_digest)
    plan_review = _plan_review(view, parent, observation)
    structural = assess_artifact(parse_artifact_package(stored.canonical_content), parse_plan(parent.canonical_content), observation)
    d = view.latest('package', s.subject_digest)
    approved = d is not None and d.decision == 'approve'
    blockers = set(plan_review.blockers)
    if structural.disposition != 'ready_for_review_design':
        blockers.add('PACKAGE_STRUCTURALLY_BLOCKED')
    if not approved:
        blockers.add('PACKAGE_NOT_APPROVED')
    token = observation.review.decision_sequence if observation.review.status == 'approved' else None
    if approved and d.baseline_approval_sequence != token:
        blockers.add('BASELINE_APPROVAL_CHANGED')
    if approved and d.parent_plan_approval_sequence != plan_review.plan_approval_sequence:
        blockers.add('PARENT_PLAN_APPROVAL_CHANGED')
    return PackageReviewAssessmentV1(schema_version=1, policy_version=POLICY_VERSION, subject=s,
        store_id=view.metadata.store_id, review_sequence=view.sequence, raw_status=_status(d),
        latest_decision_sequence=d.sequence if d else None, baseline_review=observation.review,
        baseline_approval_sequence=d.baseline_approval_sequence if approved else None,
        parent_plan_approval_sequence=d.parent_plan_approval_sequence if approved else None,
        plan_review=plan_review, artifact_assessment=structural, blockers=tuple(sorted(blockers)),
        plan_review_effective=plan_review.plan_review_effective, package_review_effective=not blockers,
        disposition='blocked' if blockers else 'reviewed_for_later_validation',
        closure_status='unverified', execution_authorized=False)


@safe_errors
def approval_tokens(view: ReviewSnapshot, stored: StoredReviewSubjectV1,
                    baseline: ReviewStore | None, expected_sequence: int) -> tuple[int, int | None]:
    if not isinstance(baseline, ReviewStore):
        raise ReviewError('INVALID_INPUT')
    observation = _observe(view, stored.subject, baseline)
    if observation.review.project_sequence != expected_sequence:
        raise ReviewError('STALE_AUTHORITY')
    if stored.subject.kind == 'plan':
        plan = assess_plan(parse_plan(stored.canonical_content), observation)
        if plan.disposition != 'ready_for_artifact_design':
            raise ReviewError('NOT_APPROVABLE')
        return observation.review.decision_sequence, None
    parent = view.subject('plan', stored.subject.plan_digest)
    plan_review = _plan_review(view, parent, observation)
    if not plan_review.plan_review_effective:
        raise ReviewError('PARENT_NOT_REVIEWED')
    package = assess_artifact(parse_artifact_package(stored.canonical_content), parse_plan(parent.canonical_content), observation)
    if package.disposition != 'ready_for_review_design':
        raise ReviewError('NOT_APPROVABLE')
    return observation.review.decision_sequence, plan_review.plan_approval_sequence


@safe_errors
def assess_plan_review(store: PackageReviewStore, baseline: ReviewStore, digest: str) -> PlanReviewAssessmentV1:
    _distinct(store, baseline)
    view = store.snapshot()
    stored = view.subject('plan', digest)
    return _plan_review(view, stored, _observe(view, stored.subject, baseline))


@safe_errors
def assess_package_review(store: PackageReviewStore, baseline: ReviewStore, digest: str) -> PackageReviewAssessmentV1:
    _distinct(store, baseline)
    view = store.snapshot()
    stored = view.subject('package', digest)
    return _package_review(view, stored, _observe(view, stored.subject, baseline))


@safe_errors
def record_review(store: PackageReviewStore, command: ReviewCommandV1,
                  context: LocalReviewContext, baseline: ReviewStore | None = None) -> ReviewDecisionV1:
    if baseline is not None:
        _distinct(store, baseline)
    return store.record_review(command, context, baseline)


@safe_errors
def export_subject(store: PackageReviewStore, kind: str, digest: str, path: str) -> None:
    write_export(path, store.export_subject(kind, digest))
