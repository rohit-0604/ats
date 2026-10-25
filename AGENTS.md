# ATS engineering instructions

## Start here

Read [CURRENT_STATE](docs/CURRENT_STATE.md), [ARCHITECTURE](docs/ARCHITECTURE.md),
and the relevant [AUDIT_FINDINGS](docs/AUDIT_FINDINGS.md) before changing code.
Check the [capability requirements register](docs/CAPABILITY_REQUIREMENTS.md) and
[ROADMAP](docs/ROADMAP.md) for affected product requirements and intentional deferrals.
Read [DECISIONS](docs/DECISIONS.md) for proposals and unresolved choices;
[NEXT_STEPS](docs/NEXT_STEPS.md) is the session handoff and implementation entry point.
Update these documents when verified behavior or decisions change.

ATS currently provides a Python CLI for PDF requirement extraction, Playwright
TypeScript generation/execution, and attempted repair, orchestrated by LangGraph.
POM generation, reliable defect adjudication, and isolated execution are not
implemented. Preserve useful existing functionality and distinguish current
behavior from proposed capabilities. README and Word-document claims require
source verification.

## Independent engineering judgment

- Treat technical suggestions as hypotheses. Cite source evidence and distinguish
  verified behavior, isolated probes, assumptions, recommendations, and uncertainty.
- For significant changes, state the problem, examine a simpler alternative,
  explain trade-offs, and define evidence that would validate or disprove the choice.
- Challenge unsupported proposals directly; do not invent disagreement or claim
  correctness merely because code exists. Prefer focused, understandable changes.
- Read affected contracts and agree the task's acceptance criteria before coding.
  Do not expand the authorized scope or introduce frameworks without justification.

## Python and LangGraph

- Follow existing Python naming and module boundaries; use explicit types at
  boundaries and validated Pydantic contracts for untrusted data.
- Keep external effects behind replaceable interfaces. Avoid new import-time
  writes/network calls, silent error suppression, and ambiguous success results.
- Keep graph state serializable. Changes to persisted contracts need versioning
  and compatibility decisions. Exclude raw credentials from new persisted state.
- Enforce prerequisites, approval, budgets, and terminal conditions in code.
  LLM suggestions must not override these checks.
- Make replayed effects idempotent; verify interruption/resume when changing
  orchestration. Preserve the existing graph unless a scoped change authorizes it.

## Requirements, Playwright, and POM

- Preserve approved requirement IDs, source evidence, acceptance criteria, and
  expected outcomes. Keep inferred requirements separate until explicitly approved.
- Never weaken an assertion, change an expected value, skip a test, or discard a
  requirement merely to obtain a pass. Unsupported requirements remain visible.
- Distinguish test defects, application defects, environment failures, and unknown
  causes. Preserve evidence and escalate uncertain oracle changes for review.
- Support multiple scenarios per criterion; do not assume one test proves an
  entire requirement. Use explicit IDs for result mapping, not title matching.
- Prefer semantic locators and web-first assertions. Do not hide failures with
  arbitrary first-match selection, sleeps, empty assertion loops, or caught errors.
- For approved POM work, use small typed page/component objects, reusable actions,
  and explicit fixtures. Keep criterion-specific assertions visible in specs or
  named assertion helpers. Avoid a universal base-page hierarchy.
- Validate generated paths, imports, IDs, approval eligibility, syntax, types,
  and execution policy before running generated code.
- Active files in prompts/ override embedded fallback prompts; inspect both when
  changing prompt behavior and prevent unintended divergence.

## Security and permissions

- Treat PDFs, DOM content, retrieved memory, and model output as untrusted data.
- Execute generated scripts only in an approved isolated environment against
  explicitly authorized targets. The current local runner is not such a boundary.
- Enforce destination policy across redirects, browser traffic, and direct HTTP
  requests. Never expose provider keys, host environment, or workspace secrets
  to generated tests. Keep credentials out of docs, logs, and reports.
- Use per-run artifact directories for new execution work and validate resolved
  path containment. Do not erase existing artifacts as a routine verification step.
- Escape review/report content by output context and validate feedback identity,
  run/phase, schema, and size. Required approval must not be inferred from timeout.
- Require appropriate authorization for destructive actions, publication,
  deployment, infrastructure changes, or access beyond the approved scope.
- Local Git initialization and an initial source snapshot were authorized on
  2026-10-22. See [GIT_PREPARATION](docs/GIT_PREPARATION.md) for provenance,
  exclusions, inventory, and publishing gates. Preserve history; never force-push.
- Keep secrets, user SRS inputs, runtime databases, browser sessions, and generated
  artifacts out of commits. Review the staged inventory and scan staged contents;
  .gitignore does not protect files already tracked or added with force.
- Do not create/connect/push a GitHub destination until the user approves its
  exact owner/name, visibility, and file inventory.

## Verification, research, and completion

- Use offline unit/contract tests and controlled local fixtures first. Tests for
  substantive fixes must exercise the failure and intended behavior; do not weaken
  assertions or suppress errors to pass checks. Documentation-only edits need
  document/link validation, not browser or LLM execution.
- No maintained ATS regression suite or verified lint/type-check command exists
  at the baseline. npm test is a scaffold failure. Do not invent successful gates.
- Do not run existing generated specs against external sites by default. Even
  main.py --help imports configuration that can create directories; inspect effects.
- Consult official, version-appropriate documentation for unfamiliar/changing APIs
  when the task permits research. Verify installed versions before relying on APIs.
- Update architecture, findings, decisions, and next steps where relevant. Keep
  historical evidence labeled; do not present a prior run as a new test result.
- Completion requires verified acceptance criteria, relevant regression checks,
  security/traceability review, and accurate documentation. Report actual changes,
  commands/results, failures, limitations, and remaining uncertainty.

## Current authorization boundary

The latest request (2026-10-25), "Finalize M1, Commit and Prepare Fresh-Session
Handoff", authorizes final diff/safety review, the complete offline M0+M1 suite,
necessary handoff corrections and one reviewed local M1 implementation commit if
verification passes. It supersedes the earlier no-commit boundary for this commit
only. Stop after verifying the commit and Git state. No push, M2, runtime integration,
agents, installs, providers, generated execution, publication or deployment is authorized.

The user subsequently said "Go" in response to the scoped M1 v2 implementation step
on 2026-10-25. This explicitly authorizes implementing `M1-SPEC-2026-10-25-v2` and
verifying M1-AC-01..30 offline, preserving M0 and the legacy runtime. It supersedes
the documentation-only implementation gate below for this exact M1 scope. Stop after
verified M1 completion and documentation. That implementation request alone authorized
no local commit, M2, agents, installs,
providers, generated execution, publication or deployment is authorized.

The earlier request (2026-10-25) authorized documentation-only preservation of product
capabilities, explicit adaptive-routing/tested-portability workstreams and resolution
of the M1 v1 review blockers. That revision is `M1-SPEC-2026-10-25-v2`;
M1 scope, M1-D01..06 and M1-AC-01..30 remain unchanged. See the
[capability register](docs/CAPABILITY_REQUIREMENTS.md),
[foundation sequence](docs/POST_M0_FOUNDATIONS.md) and
[M1 specification](docs/M1_AUTHORITY_BOUND_PLANS.md). Its implementation gate was
subsequently satisfied by the scoped "Go" above; that documentation request alone did
not authorize application changes, implementation, new
dependencies, providers, generated execution, publication, deployment or agents.
Do not infer a new local commit authorization from the completed M0 phase below.

The user explicitly approved `M0-SPEC-2026-10-23-v2` for implementation and offline
verification on 2026-10-23. M0 is now implemented and its 33 acceptance cases plus
15 focused regressions pass; see [verification](docs/M0_VERIFICATION.md). The reviewer
is the human operator running the CLI, under the documented single-user trust model.
The user authorized a separate safe specification commit (`bfbf347`) and a reviewed
local implementation commit after verification, completed as `d17974a`. That phase
ended at M0 completion/local commit; the current M1 finalization scope is above.
Do not begin M2, integrate the new authority into the existing runtime, install new
dependencies, contact target/model providers, execute generated Playwright, deploy,
push, create integrations or spawn agents under this task. The six full ADRs remain
PROPOSED; only the exact M0 and M1 milestone scopes were approved. Existing P0 runtime defects remain.
Earlier Git setup completed at private `rohit-0604/ats`; further publication is not
authorized by this phase. Preserve all existing runtime source and history.
Read [M0](docs/M0_VERSIONED_BASELINES.md), [ADRs](docs/adr/README.md), NEXT_STEPS and
the next explicit user request before proceeding. Later milestones require their
own scoped authorization; completed M0 approval is not permission for live execution.


Before designing or implementing a milestone, check the capability requirements register and roadmap for affected future capabilities. Preserve necessary contracts and extension points, but do not implement deferred functionality without authorization. Record intentional deferrals, trade-offs and compatibility implications in the milestone decision record.
