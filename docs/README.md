# ATS documentation index

Read by task, not by directory. The three levels describe loading order, not a change
to requirements or authority. Historical records cannot grant permission for new work.

## Level 1 - always-read context

Start with [AGENTS](../AGENTS.md), [NEXT_STEPS](NEXT_STEPS.md) and
[CURRENT_STATE](CURRENT_STATE.md). Establish the exact task and authorization, inspect
local Git status, then retrieve only affected Level 2 sections. Recheck relevant source
and tests before changing behavior; old observations are not substitutes for verification.

## Level 2 - task-specific authorities

| Task / question | Authoritative material to load |
| --- | --- |
| Requirements and future acceptance | [CAP inventory/delivery map](CAPABILITY_REQUIREMENTS.md#coverage-inventory-and-delivery-map), then affected CAP sections and their domain-specific additions; do not copy the register into a milestone |
| Milestone order / deferrals | [ROADMAP delivery order](ROADMAP.md#dependency-aware-delivery-order); read only relevant workstreams |
| Baseline/oracle authority | [M0 specification](M0_VERSIONED_BASELINES.md), [exact V1 contracts](M0_CONTRACTS_V1.md), [M0 decisions/trade-offs](M0_DECISION_RATIONALE.md) |
| Scenario planning | [M1 specification/contracts](M1_AUTHORITY_BOUND_PLANS.md); M0 interfaces it consumes |
| Artifact bytes/mapping | [M2 specification/contracts](M2_ARTIFACT_PACKAGES.md); relevant M0/M1 subjects |
| M2-R approved implementation | [M2-R v1 contracts and acceptance](M2R_DURABLE_REVIEW.md), [original bounded task](NEXT_STEPS.md#next-bounded-specification---unchanged-recommendation), relevant M0/M1/M2 contracts, CAP-HITL/EXEC/RECOVERY and ADR-03/06; C23 explicitly approves v1, D01..08 and AC-01..30 for offline implementation/tests and local commits |
| Runtime architecture / source boundaries | [Runtime boundary](ARCHITECTURE.md#runtime-boundary), [graph](ARCHITECTURE.md#graph-and-state), relevant offline subsystem section; inspect affected source/tests |
| Compatibility / fitness gates | [Framework constraints](ARCHITECTURE.md#framework-and-language-compatibility), [provider constraints](ARCHITECTURE.md#model-and-provider-interoperability), [coherence](ARCHITECTURE.md#integration-coherence-blockers-and-reconsideration), [ATS-FIT matrix](ARCHITECTURE.md#versioned-architecture-fitness-and-assurance-matrix) |
| Findings and remedies | [F01-F17](AUDIT_FINDINGS.md); read relevant finding details and evidence labels, not just severity summaries |
| Decisions / permissions | [Accepted constraints C01 onward](DECISIONS.md#accepted-constraints), [ADR status register](DECISIONS.md#foundational-adr-register-and-implementation-status), relevant recommendations/unresolved choices |
| ADR alternatives/invariants | [ADR index](adr/README.md); load applicable ADRs only: [01 authority](adr/01-versioned-baselines.md), [02 lifecycle](adr/02-deterministic-lifecycle.md), [03 artifacts/results](adr/03-artifact-identity.md), [04 isolation](adr/04-isolated-execution.md), [05 repair](adr/05-safe-repair.md), [06 replay](adr/06-persistence-replay.md) |

| Product workstream / CAP IDs | Required sections and additional evidence |
| --- | --- |
| MODEL | [CAP-MODEL](CAPABILITY_REQUIREMENTS.md#cap-model---adaptive-model-selection-and-routing), including A4/A5 interoperability; [MODEL roadmap](ROADMAP.md#model---adaptive-routing-workstream) |
| FRAMEWORK / POM / EXT | [FRAMEWORK](CAPABILITY_REQUIREMENTS.md#cap-framework---versioned-automation-profiles-and-multi-language-generation), [POM](CAPABILITY_REQUIREMENTS.md#cap-pom---maintainable-playwright-artifacts), [EXT](CAPABILITY_REQUIREMENTS.md#cap-ext---plug-and-play-extensibility); [FRAMEWORK roadmap](ROADMAP.md#framework---qualified-language-and-runner-profiles) |
| MANUAL / AUTHENV / COVERAGE | [MANUAL](CAPABILITY_REQUIREMENTS.md#cap-manual---manual-cases-incremental-design-and-selective-automation), [AUTHENV](CAPABILITY_REQUIREMENTS.md#cap-authenv---authentication-aware-discovery-and-environment-identity), [COVERAGE](CAPABILITY_REQUIREMENTS.md#cap-coverage---test-design-methods-and-truthful-coverage); relevant [domain review](DOMAIN_WORKFLOWS_REVIEW.md) methodology/journeys/constraints |
| WORKFLOW / EFFICIENCY | [WORKFLOW](CAPABILITY_REQUIREMENTS.md#cap-workflow---capability-driven-testing-workflows), [EFFICIENCY](CAPABILITY_REQUIREMENTS.md#cap-efficiency---context-and-execution-efficiency); source-aware/selection/context requirements remain deferred |
| HITL / professional UI | [HITL](CAPABILITY_REQUIREMENTS.md#cap-hitl---professional-workflow-ux-and-human-review), [UI roadmap](ROADMAP.md#professional-ui-and-ux) |
| DIAG / EVAL / OBS / LAB | [DIAG](CAPABILITY_REQUIREMENTS.md#cap-diag---evidence-driven-failure-intelligence), [EVAL](CAPABILITY_REQUIREMENTS.md#cap-eval---model-agent-and-system-evaluations), [OBS](CAPABILITY_REQUIREMENTS.md#cap-obs---observability-and-telemetry), [LAB](CAPABILITY_REQUIREMENTS.md#cap-lab---controlled-test-lab); [defect/evaluation gates](ROADMAP.md#model-and-agent-evaluation) |
| EXEC / RECOVERY / DATA | [EXEC](CAPABILITY_REQUIREMENTS.md#cap-exec---execution-authorization-and-isolation), [RECOVERY](CAPABILITY_REQUIREMENTS.md#cap-recovery---durable-effects-and-operational-recovery), [DATA](CAPABILITY_REQUIREMENTS.md#cap-data---data-lifecycle-and-project-governance) |
| PORT | [PORT](CAPABILITY_REQUIREMENTS.md#cap-port---cloud-and-infrastructure-portability), [portability roadmap](ROADMAP.md#port---tested-deployment-portability-workstream) |
| SHOWCASE / SC-01 | [SHOWCASE](CAPABILITY_REQUIREMENTS.md#cap-showcase---public-ats-showcase), [SC-01 and SC-AC-01..06](ROADMAP.md#sc-01---separately-trackable-public-showcase-deliverable); preparation is not publication permission |

CAP-REG-2026-10-25-v3 remains the single cross-cutting requirements authority.
Also retrieve [domain-specific acceptance additions](CAPABILITY_REQUIREMENTS.md#domain-specific-additions-to-existing-capability-owners)
when an affected CAP has A3 obligations there. Milestone specifications own exact contracts
and acceptance matrices; the roadmap owns sequencing and SC-01; decisions own alternatives,
status and authorization. Source/tests establish implementation; verification records
establish only the behavior and environment actually checked.

## Level 3 - historical evidence

- [M0 verification](M0_VERIFICATION.md), [M1 verification](M1_VERIFICATION.md),
  [M2 verification](M2_VERIFICATION.md): unchanged results, commands, failures and limits;
  load applicable evidence when assessing or changing the corresponding milestone.
- [Pre-refactor context archive](history/CONTEXT_BEFORE_2026-10-25.md): complete earlier
  AGENTS/NEXT_STEPS/CURRENT_STATE and ROADMAP preamble, including superseded handoffs,
  authorization history, API/environment observations and negative evidence.
- [Foundation assessment](POST_M0_FOUNDATIONS.md), [domain review](DOMAIN_WORKFLOWS_REVIEW.md),
  [architecture assurance](ARCHITECTURE.md#consolidated-assurance-review---2026-10-25),
  [Git provenance](GIT_PREPARATION.md) and [decision research](DECISIONS.md#existing-research-references)
  retain completed assessments, sources and trade-offs. Referenced proposed obligations
  still apply through their authoritative owners; historical classification does not retire them.
- [Refactor inventory and preservation verification](history/DOCUMENTATION_REFACTOR_2026-10-25.md)
  records measurements, unchanged authorities and the limits of consolidation.

Do not append another session history to Level 1. Keep current status in CURRENT_STATE,
active scope/next action in NEXT_STEPS, standing rules in AGENTS, and dated evidence in
the applicable verification/history record. Update only authorities whose facts changed.
