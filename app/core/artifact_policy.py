"""Pure M2 mapping/completeness checks. There is no execution-permit result."""
from __future__ import annotations

from collections import Counter

from app.baseline_contracts import BaselineSnapshotV1, InspectionV1
from app.plan_contracts import ScenarioPlanV1, PlanError, validate_plan_model
from app.core.plan_policy import assess_plan, validate_inspection, validate_plan_references
from app.artifact_contracts import (
    POLICY_VERSION, ArtifactCandidateV1, ArtifactPackageV1, ArtifactAssessmentV1,
    ArtifactError, ArtifactIssueV1, manifest_digest, parse_artifact_candidate,
)


def checked_plan(plan: ScenarioPlanV1) -> ScenarioPlanV1:
    try:
        return validate_plan_model(ScenarioPlanV1, plan)
    except PlanError as exc:
        raise ArtifactError(exc.code, source=exc.source) from None


def checked_inspection(inspection: InspectionV1) -> InspectionV1:
    try:
        return validate_inspection(inspection)
    except PlanError as exc:
        raise ArtifactError(exc.code, source=exc.source) from None


def validate_artifact_references(package: ArtifactCandidateV1, plan: ScenarioPlanV1,
                                 snapshot: BaselineSnapshotV1) -> None:
    cls = ArtifactPackageV1 if isinstance(package, ArtifactPackageV1) else ArtifactCandidateV1
    package = cls.model_validate(package)
    plan = checked_plan(plan)
    try:
        validate_plan_references(plan, snapshot)
    except PlanError as exc:
        raise ArtifactError(exc.code, source=exc.source) from None
    manifest = package.manifest
    if (manifest.project_id, manifest.baseline_digest, manifest.plan_digest) != (plan.project_id, plan.baseline_digest, plan.digest):
        raise ArtifactError('AUTHORITY_MISMATCH')
    scenarios = {s.scenario_id: s for s in plan.scenarios}
    dispositions = {d.scenario_id: d for d in manifest.scenario_dispositions}
    if scenarios.keys() != dispositions.keys():
        raise ArtifactError('INVALID_REFERENCE')
    counts = Counter(t.scenario_id for t in manifest.tests)
    for test in manifest.tests:
        if test.scenario_id not in scenarios or any(a.criterion_id != scenarios[test.scenario_id].criterion_id for a in test.assertions):
            raise ArtifactError('INVALID_REFERENCE')
    for identity, disposition in dispositions.items():
        valid = (counts[identity] > 0 and disposition.reason is None) if disposition.status == 'mapped' else (counts[identity] == 0 and disposition.reason is not None)
        if not valid:
            raise ArtifactError('INVALID_REFERENCE')


def freeze_artifact_candidate(candidate_bytes: bytes, plan: ScenarioPlanV1,
                              snapshot: BaselineSnapshotV1) -> ArtifactPackageV1:
    candidate = parse_artifact_candidate(candidate_bytes)
    validate_artifact_references(candidate, plan, snapshot)
    return ArtifactPackageV1.model_validate(dict(**candidate.model_dump(mode='python'),
                                                 digest=manifest_digest(candidate.manifest)))


def assess_artifact(package: ArtifactPackageV1, plan: ScenarioPlanV1,
                    inspection: InspectionV1) -> ArtifactAssessmentV1:
    package = ArtifactPackageV1.model_validate(package)
    plan = checked_plan(plan)
    observation = checked_inspection(inspection)
    try:
        plan_assessment = assess_plan(plan, observation)
    except PlanError as exc:
        raise ArtifactError(exc.code, source=exc.source) from None
    validate_artifact_references(package, plan, observation.snapshot)
    manifest = package.manifest
    issues = []
    if plan_assessment.disposition == 'blocked':
        issues.append(ArtifactIssueV1(code='PLAN_BLOCKED', scenario_id=None, configuration_key=None))
    for disposition in manifest.scenario_dispositions:
        if disposition.status == 'unbuilt':
            issues.append(ArtifactIssueV1(code='SCENARIO_UNBUILT', scenario_id=disposition.scenario_id, configuration_key=None))
    used = {key for test in manifest.tests for key in test.configuration_keys}
    for config in manifest.configurations:
        if config.configuration_key not in used:
            issues.append(ArtifactIssueV1(code='CONFIGURATION_UNUSED', scenario_id=None, configuration_key=config.configuration_key))
    if not manifest.tests:
        issues.append(ArtifactIssueV1(code='NO_TESTS', scenario_id=None, configuration_key=None))
    issues.sort(key=lambda i: (i.code, i.scenario_id or '', i.configuration_key or ''))
    mapped = sum(d.status == 'mapped' for d in manifest.scenario_dispositions)
    return ArtifactAssessmentV1(
        schema_version=1, policy_version=POLICY_VERSION, project_id=manifest.project_id,
        baseline_digest=manifest.baseline_digest, plan_digest=manifest.plan_digest, package_digest=package.digest,
        plan_assessment=plan_assessment, issues=tuple(issues), scenario_count=len(manifest.scenario_dispositions),
        mapped_scenario_count=mapped, unbuilt_scenario_count=len(manifest.scenario_dispositions)-mapped,
        test_count=len(manifest.tests), configuration_count=len(manifest.configurations),
        planned_pair_count=sum(len(t.configuration_keys) for t in manifest.tests), file_count=len(manifest.files),
        disposition='blocked' if issues else 'ready_for_review_design', closure_status='unverified',
        bundle_approved=False, execution_authorized=False,
    )
