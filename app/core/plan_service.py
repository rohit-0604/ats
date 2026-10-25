"""Small read-only M0 consumer. Each operation uses exactly one public inspection."""
from __future__ import annotations

from app.core.review_store import ReviewStore
from app.plan_contracts import (
    PlanAssessmentV1, ScenarioPlanDraftV1, ScenarioPlanV1, validate_plan_model,
)
from app.core.plan_policy import assess_plan, freeze_plan, validate_inspection


def inspect_plan(store: ReviewStore, validated_plan: ScenarioPlanV1) -> PlanAssessmentV1:
    plan = validate_plan_model(ScenarioPlanV1, validated_plan)
    inspection = store.inspect(plan.project_id, plan.baseline_digest)
    return assess_plan(plan, inspection)


def prepare_plan(store: ReviewStore, draft: ScenarioPlanDraftV1) -> tuple[ScenarioPlanV1, PlanAssessmentV1]:
    draft = validate_plan_model(ScenarioPlanDraftV1, draft)
    inspection = validate_inspection(store.inspect(draft.project_id, draft.baseline_digest))
    plan = freeze_plan(draft, inspection.snapshot)
    return plan, assess_plan(plan, inspection)
