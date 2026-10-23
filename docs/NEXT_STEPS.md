# Next steps and session handoff

Handoff date: 2026-10-23 (Asia/Calcutta). Audit baseline remains 2026-10-22.

**Exact next step: M0 specification approval and implementation preparation.**
Read [M0](M0_VERSIONED_BASELINES.md), [six ADRs](adr/README.md) and
[ROADMAP](ROADMAP.md). All remain PROPOSED. Do not begin M0 implementation until
explicitly authorized; this session preserved documentation only.

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

The architecture handoff began on `main` at initial snapshot `4bc2093`, tracking `origin/main`.
The user approved private `rohit-0604/ats`; creation and push were completed and
verified in the publication turn. Local remote configuration was rechecked for this
handoff; no live remote fetch or publication occurred. The original handoff left its
documentation changes uncommitted and unpublished. A subsequent explicit request
authorizes their review and one local documentation commit, with no push. Read
[GIT_PREPARATION](GIT_PREPARATION.md) for original inventory and publication history.

## Current authorization and resuming without chat history

The latest authorized phase is review and one local commit of the 15 documentation
files preserving the architecture assessment, six proposed ADRs and proposed M0.
Stop after that commit. Git setup is already complete; do not repeat it. Further
commits/pushes, implementation, installs, model calls, generated execution or
deployment require a new scoped authorization. No runtime
finding has been fixed. Broader research remains paused; no skills/hooks/MCPs/agents
are authorized. Do not infer M0 approval from permission to save its specification.

At the start of the next Codex session:

1. Read [AGENTS.md](../AGENTS.md), then CURRENT_STATE, ARCHITECTURE,
   AUDIT_FINDINGS, DECISIONS, GIT_PREPARATION, this file, the ADR index and six ADRs,
   M0_VERSIONED_BASELINES, and ROADMAP. These files supply the working context;
   no conversation history is required.
2. Read the new user task and establish its authorized scope. Documentation
   authorization alone does not authorize implementation or dependency installation.
3. Check current files and Git status/history before editing; preserve the local
   handoff and any user changes. Git setup is complete. Do not initialize or
   reconnect Git as an assumed setup step.
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

- Supported environment; private source destination is now established.
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

## Proposed M0 and implementation preparation

[M0: Versioned Baselines and Review Records](M0_VERSIONED_BASELINES.md) is the
canonical specification; do not copy its contracts into this handoff. It contains
scope/non-goals, interfaces, SQLite/canonicalization rules, security invariants,
acceptance cases, proposed files, sequence, definition of done and open questions.

Resolve the proposed single-operator trust model, whole-baseline approval, mandatory
legacy re-review, unsupported-item handling, revocation/reactivation semantics and
precise V1 contracts. Then obtain explicit M0 implementation authorization and prepare
a bounded offline plan using standard-library tests and existing Pydantic.
No new dependency is assumed. Approval of a baseline in future product use must not
be confused with approval to implement M0 now.

The dependency correction is substantive: durable baseline/review authority comes
before eligibility/result accounting. Persistence semantics are designed alongside
identity, not postponed until after effects are connected. Only the narrow baseline/
review store is in M0; graph integration, execution manifests, worker isolation,
repair, effect ledgers and checkpoint migration remain later work.

The older first milestone (offline eligibility/reconciliation, F03/F04/F05) remains
in [ROADMAP](ROADMAP.md), with detailed contracts in ADR-03. Its priority moved after
M0; its failure cases and obligations were not removed. M0 alone resolves none of
the runtime P0 findings and does not authorize real-target execution.

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
| CI | Repeat verified local commands and preserve failure evidence; introduce required checks only after verifying them. The private remote exists; CI remains unimplemented. |

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
