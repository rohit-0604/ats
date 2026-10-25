"""One coherent read-only M0 observation per offline M2 operation."""
from __future__ import annotations

from app.core.review_store import ReviewStore
from app.plan_contracts import ScenarioPlanV1
from app.artifact_contracts import (
    ArtifactPackageV1, ArtifactAssessmentV1, parse_artifact_candidate,
)
from app.core.artifact_policy import assess_artifact, freeze_artifact_candidate, checked_plan, checked_inspection


def inspect_artifact(store: ReviewStore, package: ArtifactPackageV1,
                     plan: ScenarioPlanV1) -> ArtifactAssessmentV1:
    package = ArtifactPackageV1.model_validate(package)
    plan = checked_plan(plan)
    observation = store.inspect(plan.project_id, plan.baseline_digest)
    return assess_artifact(package, plan, observation)


def prepare_artifact(store: ReviewStore, candidate_bytes: bytes,
                     plan: ScenarioPlanV1) -> tuple[ArtifactPackageV1, ArtifactAssessmentV1]:
    plan = checked_plan(plan)
    parse_artifact_candidate(candidate_bytes)  # Reject malformed bytes before any store access.
    observation = checked_inspection(store.inspect(plan.project_id, plan.baseline_digest))
    package = freeze_artifact_candidate(candidate_bytes, plan, observation.snapshot)
    return package, assess_artifact(package, plan, observation)
