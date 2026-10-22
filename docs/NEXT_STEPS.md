# Next steps and session handoff

Handoff date: 2026-10-22 (Asia/Calcutta).

## Current verified baseline

ATS is a Python CLI with a LangGraph workflow for domain inference, authentication,
crawling, PDF/saved-JSON requirements, inline TypeScript generation, local Playwright
execution, repair, learning, and reporting. See [ARCHITECTURE](ARCHITECTURE.md).
POM generation, dependable defect adjudication, execution isolation, upload APIs,
and maintained ATS regression tests are absent. Critical approval, accounting,
and lifecycle defects remain open in [AUDIT_FINDINGS](AUDIT_FINDINGS.md).

The audit parsed 31 Python sources successfully, inspected package metadata,
ran pip check successfully, inspected stored artifacts, and demonstrated specific
bugs using isolated probes/read-only SQL. It did not run the full product or
generated tests. [CURRENT_STATE](CURRENT_STATE.md) records exact validation scope,
environment versions, historical results, and provenance limits.

Local Git was initialized on `main` under the subsequent user authorization for
safe Git preparation. No previous local history or matching connected GitHub
repository was identified. No remote is attached. Read
[GIT_PREPARATION](GIT_PREPARATION.md) for the source snapshot inventory and the
pending approval of exact destination, visibility, and files before publishing.

## Current authorization and resuming without chat history

The latest authorized phase is safe local Git preparation and an initial commit,
with exclusions and related handoff documentation. External publication is pending
separate approval; do not create a GitHub repository, attach a remote, or push.
No runtime finding has been fixed. Implementation below is a recommendation
awaiting a new explicit task. Broader AI research remains paused. No
skills/hooks/MCPs/agents are authorized by this phase.

At the start of the next Codex session:

1. Read [AGENTS.md](../AGENTS.md), then CURRENT_STATE, ARCHITECTURE,
   AUDIT_FINDINGS, DECISIONS, GIT_PREPARATION, and this file. These files supply the working context;
   do not depend on previous conversations.
2. Read the new user task and establish its authorized scope. Documentation
   authorization alone does not authorize implementation or dependency installation.
3. Check current files and Git provenance. If a repository has appeared, inspect
   status/history before editing and preserve user changes. Do not initialize or
   connect Git as an assumed setup step.
4. Inspect only source relevant to the approved milestone, rechecking cited lines
   and installed versions. Do not rerun the broader audit or AI technology survey.
5. Turn the approved scope into acceptance criteria and a bounded change plan.
   Record consequential choices in DECISIONS before relying on them.
6. Keep verification offline until a controlled target/runner is explicitly in
   scope. Report actual commands and results; update finding validation/status and
   this handoff with what remains.

Do not run main.py or the existing generated specs as a casual smoke test. CLI
imports can create directories; even extract-only performs target discovery and
auth. The existing evaluator deletes specs, runs local generated code, and inherits
environment variables. Do not follow RESET_INSTRUCTIONS.txt for routine setup.

## Unresolved architecture decisions

[DECISIONS](DECISIONS.md) is the decision register. Resolve the choices required by
the next milestone without prematurely deciding hosting/frameworks:

- Authoritative source repository and supported environment.
- Approved criterion baseline, test identity, and coverage/result definitions.
- Approval and abstention rules, especially for changed expected behavior.
- CLI mode effects and terminal/exit-code semantics.
- Execution authorization/isolation and credential/data-retention boundaries.
- Single-user versus concurrent/multitenant requirements.

## P0 and P1 priorities

| Order | Findings | Required outcome |
| --- | --- | --- |
| P0 | F01 | Repair cannot silently weaken approved expected behavior. |
| P0 | F02/F03 | Generated code and artifacts cannot access host secrets or escape authorized boundaries. |
| P0 | F04 | Rejected/pending tests cannot execute; required review is enforced. |
| P1 | F05/F06 | Stable IDs, complete result accounting, preserved requirements/scenarios. |
| P1 | F07/F08/F13 | Deterministic valid transitions, complete budgets, correct modes and terminal outcomes. |
| P1 | F09/F10/F11 | Consistent auth, destination policy, safe rendering and feedback. |
| P1 | F12 | Reproducible declared dependencies and supported runtimes. |

P0 execution risks remain blockers for real-target operation even if an initial
offline correctness milestone succeeds. P2 metrics/memory refinements follow
foundational correctness; their details remain in AUDIT_FINDINGS.

## Recommended first safe implementation milestone

**Proposal: trustworthy offline evaluation and execution eligibility.**

Use the existing schemas/evaluator boundaries to address a tightly scoped portion
of F03/F04/F05. This is a preparatory milestone, not authorization to run the local
generated-code runner or a claim to resolve every P0 issue.

Before coding, settle the approved-ID set, execution eligibility semantics, result
identity representation, and outcomes for missing/unknown/duplicate results. Keep
the existing graph and agent responsibilities while introducing only the contracts
needed for this work. If a new test dependency is necessary, include that install
explicitly in the approved milestone rather than assuming authorization.

Proposed deliverables:

- A validated input/result manifest with explicit requirement and test IDs.
- Rejection of unknown generation IDs and unsafe artifact paths before any write.
- A materialization eligibility gate that excludes rejected or pending tests and
  rejects ambiguous approval states.
- Recursive Playwright result parsing with every planned test accounted for.
- Coverage derived only from the approved baseline; invalid evidence cannot create
  passing coverage. Missing output is visible as an error/incomplete outcome.
- Maintained offline regression tests reproducing the corresponding audit probes.

Acceptance evidence must include nested suites, duplicate titles, unknown IDs,
missing results, runner-level errors, rejected/pending tests, traversal/absolute
paths, and two passing IDs against a one-requirement baseline. Tests must prove
the intended semantics, not merely assert that percentages are clamped to 100.

Why first: this has deterministic inputs/outputs, can reuse existing components,
and can be checked without provider calls or a target application. Its limitation
is explicit: execution isolation and repair-oracle preservation still require
subsequent scoped milestones before autonomous operation is trustworthy.

## Required tests and quality gates

These are proposed gates; they are not installed/configured/passing today.

| Layer | Required evidence |
| --- | --- |
| Unit/contracts | Offline failure reproductions with LLM/HTTP/browser/subprocess replaced; no hidden network access. |
| Approval/traceability | Rejected/pending/inferred cases; stable IDs; all planned results reconciled; approved denominator preserved. |
| Paths/security | Windows/POSIX traversal, absolute paths, containment and reparse-point cases; no writes outside a temporary artifact root. |
| Orchestration follow-up | Empty output, repeated generation, invalid transitions, budget exhaustion, all CLI modes, replay and interruption. |
| Repair follow-up | Seeded genuine application defects remain detectable; repaired test bugs retain original criteria; uncertain causes abstain. |
| Runner follow-up | Process/filesystem/network/credential isolation and timeout/cancellation against owned fixtures. |
| Environment | Correct direct dependencies, tested lock strategy, clean setup and browser provisioning. |
| Static checks | Agreed Ruff formatting/lint and incremental mypy; generated TypeScript checked separately with tsc --noEmit and lint. |
| Integration/evals | Owned local app with deterministic data; held-out labeled cases; defect detection, false alarms, fidelity, safety, latency/cost. |
| CI | Repeat verified local commands and preserve failure evidence; block merging on required checks once an authoritative repo exists. |

Do not invent command success or broad coverage thresholds. npm test currently
fails intentionally; no maintained ATS regression runner/lint/type setup was found.
Use meaningful regression evidence for critical contracts before adopting aggregate
coverage targets. Documentation-only validation should check expected files,
cross-references, source anchors, scope, and absence of copied secrets.

## Context and handoff maintenance

- Working directory: `C:\Users\rohit\Desktop\ATS\ats`; shell: PowerShell.
- Python interpreter already present: `.venv\Scripts\python.exe`; prefer `-B`
  for read-only inspection. Installed versions are in CURRENT_STATE.
- Current tests under playwright_project/tests are generated external-target
  artifacts, not trusted ATS regression fixtures. Do not execute them by default.
- Active prompt files override Python fallback prompts. Original approved criteria
  must remain authoritative during future repair changes.
- Runtime cache/memory/output may contain sensitive data. Do not publish or copy
  raw checkpoints, credentials, environment, auth state, or target evidence.
- Historical March results are artifact observations only. The audit probes were
  not retained as scripts; AUDIT_FINDINGS records reproduction inputs/outcomes.
- Update finding status only with named validation evidence; keep the old failure
  description as history. Record changed decisions and the next bounded action here.

The next session should begin with these documents and an explicit scoped task.
No further architecture research or feature implementation is part of this handoff.
