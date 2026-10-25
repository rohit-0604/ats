# Current state

Status as of 2026-10-25; audit baseline 2026-10-22. This is the concise current summary.
Verification counts below are recorded milestone evidence, **not new runs**.

| Implemented offline milestone | Verified evidence | Boundary |
| --- | --- | --- |
| M0 - versioned baselines/reviews | [48 passed, 14.953 s](M0_VERIFICATION.md) | 33 acceptance cases + 15 regressions; single-operator digest-bound authority |
| M1 - authority-bound scenario plans | [78 passed, 30.575 s](M1_VERIFICATION.md) | Includes unchanged M0; immutable proposals, no plan/execution approval |
| M2 - inert artifact packages/mappings | [116 passed, 66.165 s](M2_VERIFICATION.md) | Includes M0/M1 + 26 M2 acceptance families + 12 boundary regressions; closure unverified |

Local baseline HEAD is `b94d76da1a09d6b3df220965c1c7f14884ca394c`.
Check live local Git status before work; C20/C21 documentation edits were already
uncommitted when C22 began. No new commit or remote query is part of this refactor.

The separate legacy Python/LangGraph CLI implements PDF/JSON extraction, discovery,
authentication, inline TypeScript/Playwright execution and attempted repair. It does
not consume M0-M2 authority. All [F01-F17](AUDIT_FINDINGS.md) remain open; generated
host execution is unsafe, result mapping/coverage and approval/oracle handling defective.
POM generation, dependable defect adjudication and approved execution isolation are absent.
Contract-test success is not measured product effectiveness or production readiness.

[CAP-REG-2026-10-25-v3](CAPABILITY_REQUIREMENTS.md) preserves framework/model/portability,
manual/auth/environment/coverage, source-aware workflow, HITL/UI, OBS/EVAL/LAB and
SC-01 requirements. These future obligations do not authorize implementation. Full ADRs
remain PROPOSED beyond their exact approved milestone subsets. The
[architecture assessment](ARCHITECTURE.md#consolidated-assurance-review---2026-10-25)
found no demonstrated blocker to a separate M2-R specification. Safe execution still
requires M2-R/M3/M4/M5 and explicit target/effect/isolation authorization and evidence.

The current task and unchanged next recommendation are in [NEXT_STEPS](NEXT_STEPS.md).
Use the [documentation index](README.md) for exact contracts, requirements and findings.

## Historical detail

These compatibility anchors lead to preserved observations, limits and negative evidence.
Installed versions, old Git state and stored percentages are dated observations, not
current qualification. Untracked runtime evidence may be unavailable in a clean clone.

| Prior section | Historical record |
| --- | --- |
| <a id="read-this-documentation"></a>Read this documentation | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-read-this-documentation) |
| <a id="repository-provenance-and-scope"></a>Repository provenance and scope | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-repository-provenance-and-scope) |
| <a id="capability-inventory"></a>Capability inventory | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-capability-inventory) |
| <a id="historical-architecture-and-m0-specification-assessment"></a>Historical architecture and M0 specification assessment | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-historical-architecture-and-m0-specification-assessment) |
| <a id="environment-observed-during-the-audit"></a>Environment observed during the audit | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-environment-observed-during-the-audit) |
| <a id="validation-already-performed"></a>Validation already performed | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-validation-already-performed) |
| <a id="architecture-handoff-verification-2026-10-23"></a>Architecture handoff verification (2026-10-23) | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-architecture-handoff-verification-2026-10-23) |
| <a id="historical-artifact-evidence"></a>Historical artifact evidence | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#state-historical-artifact-evidence) |
