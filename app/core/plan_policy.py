"""Pure M1 structural planning and admission; no I/O or runtime authority."""
from __future__ import annotations

from collections import Counter
from app.baseline_contracts import BaselineSnapshotV1, InspectionV1, M0Error, validate_model
from app.plan_contracts import (
    POLICY_VERSION, PlanAssessmentV1, PlanError, PlanIssueV1, ScenarioPlanDraftV1,
    ScenarioPlanV1, plan_digest, validate_plan_model,
)


def _plan(value: ScenarioPlanDraftV1) -> ScenarioPlanDraftV1:
    cls = ScenarioPlanV1 if isinstance(value, ScenarioPlanV1) else ScenarioPlanDraftV1
    return validate_plan_model(cls, value)


def validate_plan_references(draft_or_plan: ScenarioPlanDraftV1, snapshot: BaselineSnapshotV1) -> None:
    plan = _plan(draft_or_plan)
    if not isinstance(snapshot, BaselineSnapshotV1):
        raise PlanError('AUTHORITY_MISMATCH')
    try:
        snapshot = validate_model(BaselineSnapshotV1, snapshot)
    except M0Error:
        raise PlanError('AUTHORITY_MISMATCH') from None
    if not snapshot.criteria:
        raise PlanError('INVALID_REFERENCE')
    if (plan.project_id, plan.baseline_digest) != (snapshot.project_id, snapshot.digest):
        raise PlanError('AUTHORITY_MISMATCH')
    criteria = {item.criterion_id: item for item in snapshot.criteria}
    dispositions = {item.criterion_id: item for item in plan.dispositions}
    if dispositions.keys() != criteria.keys() or any(s.criterion_id not in criteria for s in plan.scenarios):
        raise PlanError('INVALID_REFERENCE')
    counts = Counter(s.criterion_id for s in plan.scenarios)
    for identity, criterion in criteria.items():
        disposition = dispositions[identity]
        if criterion.automation_support == 'unsupported':
            valid = (disposition.status == 'unsupported' and counts[identity] == 0
                     and disposition.reason == criterion.support_reason)
        elif disposition.status == 'planned':
            valid = (criterion.clarity == 'specified' and criterion.automation_support == 'supported'
                     and counts[identity] > 0 and disposition.reason is None)
        else:
            valid = (disposition.status == 'unplanned' and counts[identity] == 0
                     and disposition.reason is not None)
        if not valid:
            raise PlanError('DISPOSITION_CONFLICT')


def freeze_plan(draft: ScenarioPlanDraftV1, snapshot: BaselineSnapshotV1) -> ScenarioPlanV1:
    draft = validate_plan_model(ScenarioPlanDraftV1, draft)
    validate_plan_references(draft, snapshot)
    return validate_plan_model(ScenarioPlanV1, dict(**draft.model_dump(mode='json'), digest=plan_digest(draft)))


def validate_inspection(inspection: InspectionV1) -> InspectionV1:
    """Reject serialized or malformed observations before any member is consumed."""
    if not isinstance(inspection, InspectionV1):
        raise PlanError('AUTHORITY_MISMATCH')
    try:
        return validate_model(InspectionV1, inspection)
    except M0Error:
        raise PlanError('AUTHORITY_MISMATCH') from None


def assess_plan(validated_plan: ScenarioPlanV1, inspection: InspectionV1) -> PlanAssessmentV1:
    plan = validate_plan_model(ScenarioPlanV1, validated_plan)
    observation = validate_inspection(inspection)
    subject = (plan.project_id, plan.baseline_digest)
    review = observation.review
    if ((observation.project.project_id, observation.snapshot.digest) != subject
            or (observation.snapshot.project_id, review.subject_digest) != subject
            or review.project_id != plan.project_id):
        raise PlanError('AUTHORITY_MISMATCH')
    if (review.active_digest is not None and review.active_digest != review.head_digest
            or review.status == 'pending' and review.decision_sequence is not None
            or review.status != 'pending' and (review.decision_sequence is None
                or not 1 <= review.decision_sequence <= review.project_sequence)
            or review.status == 'approved' and review.active_digest != plan.baseline_digest
            or review.status != 'approved' and review.active_digest == plan.baseline_digest):
        raise PlanError('AUTHORITY_MISMATCH')
    validate_plan_references(plan, observation.snapshot)
    issues = []
    if review.status != 'approved' or review.active_digest != plan.baseline_digest:
        issues.append(PlanIssueV1(code='BASELINE_NOT_ACTIVE', criterion_id=None, scenario_id=None))
    for item in plan.dispositions:
        if item.status == 'unplanned':
            issues.append(PlanIssueV1(code='CRITERION_UNPLANNED', criterion_id=item.criterion_id, scenario_id=None))
    if not plan.scenarios:
        issues.append(PlanIssueV1(code='NO_AUTOMATABLE_SCENARIOS', criterion_id=None, scenario_id=None))
    issues.sort(key=lambda item: (item.code, item.criterion_id or '', item.scenario_id or ''))
    counts = Counter(item.status for item in plan.dispositions)
    return PlanAssessmentV1(
        schema_version=1, policy_version=POLICY_VERSION, project_id=plan.project_id,
        baseline_digest=plan.baseline_digest, plan_digest=plan.digest,
        baseline_status=review.status, decision_sequence=review.decision_sequence,
        project_sequence=review.project_sequence, active_digest=review.active_digest, head_digest=review.head_digest,
        disposition='blocked' if issues else 'ready_for_artifact_design', issues=tuple(issues),
        total_criteria=len(observation.snapshot.criteria), planned_criteria=counts['planned'],
        unplanned_criteria=counts['unplanned'], unsupported_criteria=counts['unsupported'],
        scenario_count=len(plan.scenarios), plan_approved=False, execution_authorized=False,
    )
