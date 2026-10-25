# Decisions and proposals

Baseline recorded 2026-10-22; architecture handoff updated 2026-10-23. Read [CURRENT_STATE](CURRENT_STATE.md) and
[AUDIT_FINDINGS](AUDIT_FINDINGS.md) before using this register. Implemented behavior
is described in [ARCHITECTURE](ARCHITECTURE.md); proposed work is sequenced in
[NEXT_STEPS](NEXT_STEPS.md).

## Accepted constraints

These reflect explicit user direction, not approval of a new runtime architecture.

| ID | Status | Constraint |
| --- | --- | --- |
| C01 | ACCEPTED | The completed audit is the factual baseline; preserve evidence/uncertainty distinctions. |
| C02 | SUPERSEDED IN SCOPE | The initial six-document-only phase is complete. C08/C09 record initial Git work; C10-C17 record successive bounded scopes. |
| C03 | ACCEPTED | Preserve useful current LangGraph functionality; do not describe proposals as implemented. |
| C04 | ACCEPTED | Do not initialize Git, overwrite history, or connect a remote without approval. |
| C05 | ACCEPTED | Preserve requirements/assertions; independently assess suggestions; never invent passing verification. |
| C06 | ACCEPTED | Keep secrets and sensitive environment values out of documentation. |
| C07 | ACCEPTED | Broader AI technology research is paused. Future work must be explicitly scoped. |
| C08 | ACCEPTED 2026-10-22 | User authorized root/provenance checks, safe exclusions, local Git initialization if absent, and an initial source/documentation commit. Publication requires separate approval of exact destination, visibility, and inventory. See [GIT_PREPARATION](GIT_PREPARATION.md). |
| C09 | APPROVED AND COMPLETED 2026-10-23 | User explicitly approved remaining Git setup: private `rohit-0604/ats`, reviewed 51-file initial snapshot. Creation, origin, push and matching SHA/private visibility were verified in that turn. This does not authorize later pushes or public release. |
| C10 | APPROVED SCOPE 2026-10-23 | User authorized saving ADRs/M0/roadmap and updating/reviewing documentation only. No application implementation, dependency install, provider call, generated execution, deployment or GitHub publication. |
| C11 | APPROVED SCOPE 2026-10-23 | User subsequently authorized review and one local commit of the 15 architecture/handoff documentation files, with message `docs: preserve ATS architecture decisions and M0 specification`. Stop after the local commit; no push, implementation, history rewrite or deployment is authorized. |
| C12 | APPROVED DOCUMENTATION SCOPE 2026-10-23 | After local commit `4a59405`, user requested final proposed M0 contracts, decision rationale, acceptance matrix, incremental plan, risks and explicit implementation approval gate. Relevant source inspection/documentation updates only; no application code, installs, generated execution, deployment or publication. No additional commit is authorized. |
| C13 | EXPLICITLY APPROVED AND COMPLETED M0 2026-10-23 | User approved M0-SPEC-2026-10-23-v2, M0-D01..11, offline implementation/AC-01..33, the separate seven-file specification commit, and a verified local implementation commit. Reviewer is the human operator running the CLI. No push, dependency install, runtime integration, provider/target/generated execution, deployment or M1. Verification: 48 passing tests, no skips. |
| C14 | APPROVED DOCUMENTATION SCOPE 2026-10-23 | User requested post-M0 interface verification, dependency-based sequencing, one next-milestone specification and roadmap/handoff proposals. Source reads, existing offline M0 verification and documentation only; stop at implementation approval. No application changes, dependencies, providers, generated execution, publication, deployment or new commit authorized. |
| C15 | APPROVED DOCUMENTATION SCOPE 2026-10-25 | User requested one authoritative capability register, preservation of broader product requirements, explicit tested-portability/adaptive-routing workstreams and a new proposed M1 revision resolving the two review blockers. M1 scope/decisions/cases stay unchanged. Documentation only; no implementation, install, generated execution, providers, publication, commit, push or deployment. Stop at M1 approval. |
| C16 | EXPLICITLY APPROVED AND COMPLETED M1 2026-10-25 | User said "Go" to implement M1-SPEC-2026-10-25-v2 and verify M1-AC-01..30 offline, preserving M0 and the existing runtime. M1-D01..06 and single-operator/non-authorizing readiness apply. All 78 tests passed: 48 unchanged M0 plus 30 M1, no skips. See M1_VERIFICATION. No local commit, M2, dependencies, agents, providers, generated execution, publication or deployment authorized. Stop after completion and records. |
| C17 | APPROVED M1 FINALIZATION SCOPE 2026-10-25 | User separately authorized exact diff/safety review, full offline suite, necessary handoff corrections and one reviewed local M1 implementation commit if verification passes. The finalization rerun passed 78 tests in 30.575 seconds, zero failures/errors/skips. Supersedes C16's no-commit limit for this single commit only. No push, history rewrite, M2, architecture changes, installs, providers, generated execution, publication or deployment. Stop after verified commit and handoff. |
| C18 | APPROVED DOCUMENTATION SCOPE ONLY 2026-10-25 | Post-M1 Architecture Dependency and M2 Specification: inspect actual contracts/Git, verify offline, prepare M2 specification and stop at implementation approval. No code implementation, installs, providers, crawling, generated execution, commits, push, publication or deployment. [M2 proposal](M2_ARTIFACT_PACKAGES.md) narrows M2 to immutable packages/mappings and non-authorizing assessment, deferring durable review to M2-R; M2-D01..07 and AC-01..26 remain PROPOSED. Current unchanged offline suite: 78 passed in 28.819 seconds, no failures/errors/skips. |
| C19 | APPROVED AND COMPLETED M2 OFFLINE IMPLEMENTATION; LOCAL CHECKPOINT 2026-10-25 | User approved M2 v1 decisions/contracts/AC-01..26 and offline implementation plus reviewed local checkpoint. Preflight stopped on the existing decoder string-cap contradiction before application coding. User then explicitly approved M2-SPEC-2026-10-25-v2: context-limited base64 decoding with unchanged M0/M1, original limits and explicit boundary tests. M2 is now implemented: final full rerun 116 passed in 66.165 seconds, zero failures/errors/skips; see M2_VERIFICATION. Preserve prior documentation edits and create only the reviewed local checkpoint. No agents, installs, providers, crawling, generated execution/compilation, later milestones, publication, deployment or push. |

C11's local commit completed as `4a59405ef19f82fbee7c09e2edb3a28cfdf1fcee`.
The intervening specification-only request did not reopen its Git authorization.
C13 separately authorizes the specification commit `bfbf347` and local implementation
commit `d17974a`; neither authorizes pushing. Current local refs may
change independently; do not infer permission to push from tracking configuration.

## Foundational ADR register and implementation status

**The six full ADRs remain PROPOSED. Only the exact M0, M1 and M2 milestone scopes are approved and implemented offline.**
Provisional acceptance of a direction is not acceptance of every schema, security
assumption, migration or milestone. The ADRs are self-contained proposals; the
[review index](adr/README.md) preserves criticism of earlier recommendations.

| Record | Status | Relationship to earlier proposals |
| --- | --- | --- |
| [ADR-01: versioned baselines/oracle authority](adr/01-versioned-baselines.md) | PROPOSED | Refines D02; authority is distinct from hashes and legacy flags. |
| [ADR-02: deterministic LangGraph lifecycle](adr/02-deterministic-lifecycle.md) | PROPOSED | Refines D01; policy code rather than a second graph framework. |
| [ADR-03: artifact identity/approval/results](adr/03-artifact-identity.md) | PROPOSED | Extends D01/D02; approval covers final executable bundle and shared dependencies. |
| [ADR-04: isolated execution](adr/04-isolated-execution.md) | PROPOSED | Refines D03; worker contract first, technology still undecided. |
| [ADR-05: diagnosis and safe repair](adr/05-safe-repair.md) | PROPOSED | Refines D02; reviewed hypotheses, no automatic assertion changes. |
| [ADR-06: persistence/replay/evidence](adr/06-persistence-replay.md) | PROPOSED | Application records plus checkpoints; no exactly-once claim for target effects. |
| [M0: Versioned Baselines and Review Records](M0_VERSIONED_BASELINES.md) | APPROVED AND IMPLEMENTED offline | Narrow subset of ADR-01/06; 33 acceptance cases plus 15 focused regressions pass; no runtime integration. |
| [Post-M0 foundation sequence](POST_M0_FOUNDATIONS.md) | PROPOSED | Refines follow-up ordering: M1 authority/scenario plans, M2 bundles/review, M3 results and M4 lifecycle/effects, M5 worker readiness; no live execution authorization. |
| [M1: Authority-bound scenario plans](M1_AUTHORITY_BOUND_PLANS.md) | APPROVED AND IMPLEMENTED offline | M1-SPEC-2026-10-25-v2; all 30 acceptance families and 48 unchanged M0 tests pass; read-only M0 consumer, no new authority store or runtime integration. See M1_VERIFICATION. |
| [Capability requirements register](CAPABILITY_REQUIREMENTS.md) | USER-REQUESTED REQUIREMENTS RECORDED; delivery deferred | CAP-REG-2026-10-25-v1 owns cross-cutting required behavior, current evidence and future acceptance; not approval of delivery implementations. |
| [Broader roadmap](ROADMAP.md) | PROPOSED | Retains D04-D07 and product/UI/lab/observability/evaluation/security/deployment work. |

The previous first milestone, offline eligibility and result reconciliation, is
superseded **in ordering**, not discarded. It consumes baseline/review authority
from M0 and retains its acceptance cases in ROADMAP and ADR-03. Saving the revised
proposal did not approve M0 implementation; C13 later approved its exact subset.

The latest [sequencing rationale](POST_M0_FOUNDATIONS.md) challenges policy-first
M1A/M1B/M1C ordering: complete policy needs concrete subjects and durable reservations.
It proposes a smaller M1 plan/authority slice and keeps execution denied throughout
offline foundations. M1-D01..06 were subsequently accepted within C16's exact scope. M0-D01..11 remain accepted
without modification. Full ADRs remain proposed; this is a sequencing refinement,
not a seventh replacement architecture or approval of later schemas.

M0 revision `M0-SPEC-2026-10-23-v2` now supplies [exact V1 contracts](M0_CONTRACTS_V1.md),
[11 proposed decision rationales](M0_DECISION_RATIONALE.md), 33 proposed acceptance
cases and an implementation checklist. M0-D01..11 were subsequently explicitly ACCEPTED
within M0 only. They retain the offline baseline/review design. In particular, no direct
reactivation/removal is permitted,
and uncertain post-commit acknowledgment is reconciled by the original request ID.

## Recommendations awaiting an implementation decision

| ID | Proposal and justification | Simpler alternative / trade-off | Validation and maintenance |
| --- | --- | --- | --- |
| D01 | Retain LangGraph nodes/checkpoints; make lifecycle, approval, and budgets deterministic (F04/F07). | Validated LLM planning only for ambiguous recovery; deterministic routing loses some flexibility but is easier to test. | Compare recovery quality, unsafe transitions, latency/cost on fixed cases; maintain transition contracts. |
| D02 | Preserve immutable approved criteria and evidence; separate inferred suggestions and repair proposals (F01/F05/F06). | Initially freeze baseline JSON and require human review of oracle changes; simpler than a new adjudication agent. | Seed genuine defects and faulty tests; verify no silent oracle change; maintain criterion schemas. |
| D03 | Isolate generated execution with per-run artifacts and explicit network/secret policy (F02/F03/F10). | Disable generated execution while validating artifacts offline; a subprocess/env filter alone is insufficient isolation. | Test filesystem, egress, process, timeout, and credential boundaries; worker operations add maintenance. Hosting/isolation technology is unresolved. |
| D04 | Add small typed page/component objects and fixtures through the existing generator. | Functions suffice for isolated actions; avoid universal inheritance or another runtime agent. | Change a shared locator once; affected specs remain traceable and testable. Maintain multi-file artifact/import contracts. |
| D05 | Retain retrieval provisionally and quarantine unverified lessons. | Curated JSON recipes may be sufficient for a small corpus; semantic retrieval adds dependencies and tuning. | Held-out memory-on/off comparison, tenant/domain isolation, provenance and freshness. No benefit assumed. |
| D06 | Build a minimal development harness: instructions, specs, offline tests, types/lint, then CI. | Plain repeatable commands before hooks/skills/custom platforms. | Prove commands locally and in a clean environment; add automation only for demonstrated repetition. |
| D07 | Align direct dependencies and lock a tested runtime/browser baseline (F12). | A constrained requirements file may be simpler than changing package managers; avoid freezing incidental packages. | Clean setup plus import/contract checks; maintain intentional upgrades and compatibility evidence. |

The original documentation request authorized none of D01-D07. C13 subsequently
approved only their narrow M0 baseline/review subset. All broader scope remains proposed.

## Product-requirement preservation and M1 v2 review

The independent review of `M1-SPEC-2026-10-23-v1` recommended REVISE for two
documentation blockers, not a change to the offline plan/authority design. C15 addresses
them with `M1-SPEC-2026-10-25-v2` and the single capability register. Eleven requested
CAP IDs are preserved; CAP-POM/EXEC/RECOVERY/DATA give ownership to existing scattered
cross-cutting requirements. They are required product outcomes with deferred delivery,
not approved adapter schemas, vendors, implementation dates or new M1 obligations.

| Decision | WHAT / WHY / HOW | Alternatives, trade-offs and required evidence |
| --- | --- | --- |
| P-MODEL | Preserve CAP-MODEL and a separate deferred MODEL workstream: task-aware selection, supported effort, privacy/context/quality/latency/cost limits, versioned policy, bounded escalation/abstention and complete attempt accounting. A configured fallback chain is insufficient evidence of adaptive selection. | Begin with curated capabilities and a deterministic task policy; compare against default/fallback and learned/external routing using CAP-MODEL.A1..A3. More expensive is not presumed better; adopt complexity only for demonstrated held-out benefit. No vendor router chosen or implementation approved. |
| P-PORT | Preserve CAP-PORT and a deferred PORT delivery gate: name supported profiles, separate domain rules/adapters, externalize configuration and verify builds, migration/rollback, secrets and common contracts/security. Current Windows M0 evidence cannot establish cloud portability. | One profile initially is simpler; add a second only for real need and CAP-PORT.A1..A2 evidence. No universal portability, default Kubernetes/microservices or M1 cloud adapter; unsupported profiles remain explicit. |

These are documented delivery proposals preserving user-requested requirements. The
register owns their detailed behavior/evidence; this table owns rationale and scope.
M1-D01..06 and M1-AC-01..30 are retained verbatim. V2 adds revision history, capability
compatibility/traceability and a decision-to-evidence mapping; no V1 wire semantics or
runtime contracts change. All full ADRs remain PROPOSED. No new product benchmark,
compatibility result or M1 test result was claimed by that documentation-only phase.

**Historical review recommendation: GO for explicit approval of M1-SPEC-2026-10-25-v2's offline
implementation scope.** Documentation verification passed as recorded in NEXT_STEPS.
Recording this recommendation
is not approval. There is no remaining documentation blocker identified for that scope;
the owner subsequently approved M1-D01..06, all 30 cases, non-authorizing readiness and
the single-operator/local-file trust boundary with "Go" (C16). M1 is now implemented
and [verified](M1_VERIFICATION.md). Later model/profile/data/reviewer/quality
decisions remain at their delivery gates; Git publication needs separate approval.

## Unresolved decisions

- M0 product decisions are resolved under C13: the human CLI operator is the reviewer;
  exact v2 trust, review, identity, serialization, storage, import and CLI rules apply.
  M1 authority-bound scenario planning is now approved/implemented under C16. M2 bundle/
  review specification was authorized by C18; C19 subsequently approved the exact M2 v2 package slice, now implemented/verified. M2-R remains unapproved. Later lifecycle,
  artifacts, eligibility, results and worker controls remain separately scoped.
  M0 approval does not authorize them or close any existing runtime finding.
- Git destination is resolved for the private initial snapshot (`rohit-0604/ats`).
  Prior upstream history remains unknown; public release/licensing and additional
  publication require their own scope. Git approval is not feature approval.
- Which requirement types belong in the first product scope? How are unsupported,
  ambiguous, and inferred requirements represented and approved?
- Who may approve changed expected behavior? What evidence distinguishes a test
  defect from an application defect, and when must the system abstain?
- What should extract-only/codegen-only guarantee about network activity and outputs?
- What are the result/coverage definitions and CLI exit statuses for partial,
  unknown, blocked, budget-exhausted, and infrastructure-failed runs?
- What destinations, redirects, private addresses, state-changing actions, and
  credentials are authorized for a run? What isolation environment enforces this?
- What data may reach external model providers, and what retention/access policy
  applies to SRS content, snapshots, auth artifacts, checkpoints, and memory?
- Is the first release a single-user CLI or a concurrent/multitenant service?
  Current shared directories/state do not establish multitenant safety.
- Which Python/Node/browser versions and dependency workflow will be supported?
- What labeled evaluation corpus and minimum quality criteria justify expanding
  autonomous repair, retrieval, or planning?

## Updating decisions

For a consequential approved choice, record date, scope, owner/authorization,
evidence, alternatives, trade-offs, acceptance checks, and superseded decisions in
this file. Keep proposals labeled PROPOSED until decided; do not infer product
approval from permission to write documentation.

## Existing research references

These were consulted during the completed audit. No new technology research is
required to resume the first offline milestone. Recheck version-specific details
only when an authorized change requires them.

- [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex skills](https://learn.chatgpt.com/use-cases/reusable-codex-skills)
- [Codex MCP](https://developers.openai.com/codex/mcp)
- [Codex security and hook limitations](https://learn.chatgpt.com/docs/enterprise/security-cookbook)
- [LangGraph graph API and recursion limits](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Playwright POM guidance](https://playwright.dev/docs/pom)
- [Playwright assertions, including counts/CSS](https://playwright.dev/docs/test-assertions)
- [Playwright TypeScript: separate type checking required](https://playwright.dev/docs/test-typescript)
- [Google SDK libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Ruff](https://docs.astral.sh/ruff/), [incremental mypy](https://mypy.readthedocs.io/en/stable/existing_code.html),
  [pytest mocking](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
