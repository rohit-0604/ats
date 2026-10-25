# Current state

Baseline date: 2026-10-22 (Asia/Calcutta). This records the completed repository
audit, accepted by the user as the factual baseline. It is not a claim of a
successful current end-to-end execution.

Current offline implementation update, 2026-10-25: the user explicitly approved M1 v2
with "Go". **M1 is implemented and verified: the finalization rerun passed 78 tests in 30.575 seconds with
zero failures/errors/skips (48 unchanged M0 plus 30 M1 acceptance families).** See
[M1_VERIFICATION](M1_VERIFICATION.md). It adds a separate authority-bound plan CLI,
immutable scenario/plan identities, complete criterion dispositions and read-only M0
admission. It grants no plan/execution approval and has no legacy runtime integration.
All F01-F17 remain open; M2 and later capabilities are not authorized. The subsequent
finalization request permits one reviewed local M1 commit and necessary handoff updates
(C17), with no push. [NEXT_STEPS](NEXT_STEPS.md#git-and-authorization) records its exact
subject, parent and hash-recovery command; verify history/status before retrying a commit.
The earlier specification-only paragraphs below are historical.

Historical architecture handoff update: 2026-10-23. The product/system, UX, SDD, observability and evaluation
assessment and six-decision deep dive are now preserved as proposals. This update
changes documentation only; no runtime finding is fixed and no M0 test has run.

Historical M0 specification update: `M0-SPEC-2026-10-23-v2` included exact proposed V1
contracts, 11 decision rationales, 33 acceptance cases and an implementation approval
checklist. It was unapproved at that point. The user subsequently explicitly approved
M0 implementation; the offline slice is now complete with **48 passing tests**, including
all AC-01..33 and 15 focused regressions, no skips. See [M0 verification](M0_VERIFICATION.md).
The existing runtime remains unchanged and all F01-F17 remain open.

Historical post-M0 foundation assessment, 2026-10-23: started with a clean tree at implementation
commit `d17974a9ac17f209ed110a86b11c504e2cc3bc49`; local `origin/main` matched, with
no live remote query. Actual M0 interfaces and relevant runtime dependencies were read.
The existing offline command was rerun: **48 tests passed in 14.280 seconds, no failures,
errors or skips**. [Foundation analysis](POST_M0_FOUNDATIONS.md) records evidence and
recommends [M1 authority-bound scenario plans](M1_AUTHORITY_BOUND_PLANS.md) before final
bundle contracts, result reconciliation and lifecycle/effect enforcement. At that point
M1 was PROPOSED with 30 unimplemented/unexecuted acceptance families. That phase changed
documentation only and stopped at implementation approval; no runtime defect was closed.

## Read this documentation

Historical 2026-10-25 documentation reconciliation: [CAPABILITY_REQUIREMENTS](CAPABILITY_REQUIREMENTS.md)
now preserves broader product requirements and accurate implementation status in one
register. ROADMAP explicitly tracks deferred MODEL adaptive-routing and PORT tested
deployment-portability deliverables. The revised proposed M1 is
`M1-SPEC-2026-10-25-v2`: documentation blockers resolved, six decisions and 30 offline
acceptance cases unchanged; GO recommendation awaits explicit implementation approval.
SC-01 remains separately scoped. No application source, M0 contract, dependency, full
ADR status or runtime behavior changed; no tests/providers/generated code were executed
by this reconciliation. Prior M0 pass counts above remain historical evidence.

- [AGENTS.md](../AGENTS.md): enforceable engineering instructions.
- [ARCHITECTURE](ARCHITECTURE.md): implemented components and data flow.
- [AUDIT_FINDINGS](AUDIT_FINDINGS.md): evidence, priorities, validation, remedies.
- [DECISIONS](DECISIONS.md): accepted constraints, proposals, unresolved choices.
- [NEXT_STEPS](NEXT_STEPS.md): scoped milestone and self-contained session handoff.
- [ADRs](adr/README.md): six proposed decisions, critique, dependencies and walkthrough.
- [M0](M0_VERSIONED_BASELINES.md): approved and implemented offline baseline/review specification.
- [M0 V1 contracts](M0_CONTRACTS_V1.md): approved fields, canonical bytes, lifecycle, import, storage and CLI rules.
- [M0 rationale](M0_DECISION_RATIONALE.md): alternatives, risks and reconsideration triggers for the 11 decisions approved within M0.
- [Post-M0 foundation sequence](POST_M0_FOUNDATIONS.md): verified interfaces, dependencies and proposed milestone boundaries.
- [M1 specification](M1_AUTHORITY_BOUND_PLANS.md): approved and implemented offline planning contracts and completed authorization gate.
- [M1 verification](M1_VERIFICATION.md): current implemented scope, acceptance outcomes, failure fixes and residual risks; supersedes the earlier M1 proposal-only status.
- [Capability requirements](CAPABILITY_REQUIREMENTS.md): cross-cutting requirements, current evidence, delivery mapping, adoption/deferral criteria and future acceptance obligations.
- [ROADMAP](ROADMAP.md): product, POM, memory, UI, lab, observability, evaluations and deployment.

## Repository provenance and scope

Workspace: `C:\Users\rohit\Desktop\ATS\ats`.

At the initial audit, `git rev-parse --show-toplevel` failed and no workspace or
parent Git marker was found. On 2026-10-22 the user subsequently authorized safe
local version control preparation. Git was initialized at this exact workspace
on branch `main` after checking exclusions and provenance; there was no existing
local history to preserve. The initial commit is a snapshot of this workspace,
not recovered upstream development history. The user subsequently approved publishing
the reviewed snapshot to private `rohit-0604/ats`. Creation and push completed on
2026-10-23: `origin` is `https://github.com/rohit-0604/ats.git`, and `main` tracks
`origin/main`. The publication turn verified private visibility and matching local/
remote SHA `4bc20938d87bbeb00512f058d4abb4434aa7ebc4`.

This handoff rechecked local Git status/configuration, not live GitHub visibility.
It began from a clean tree at that commit; the original handoff left its edits local,
uncommitted and unpublished. A subsequent explicit request authorizes review and one
local documentation commit, with no push or implementation. No application source
changed. Earlier upstream copies outside
known access remain unverified. [GIT_PREPARATION](GIT_PREPARATION.md) preserves the
original inventory, safety review and completed publication record.

The audit inspected Python source, active prompts, CLI/configuration, generated
TypeScript, manifests, documentation, stored run artifacts, and read-only SQLite
metadata. No production/third-party browser tests or provider calls were run.
Only selected nonsecret numeric settings were inspected from local configuration;
credentials and sensitive environment values must not enter these documents.

## Capability inventory

CONFIRMED means implementation evidence exists, not production validation.
PARTIAL means meaningful pieces exist with limitations. BROKEN denotes a specific
contradiction/failure supported by source or a probe. MISSING means not found in
this workspace. UNVERIFIED denotes a claim not established by the audit.

| Capability | Status | Baseline |
| --- | --- | --- |
| Python CLI, configuration | CONFIRMED | URL plus local PDF or saved requirements JSON |
| Offline M0 baseline/review CLI | CONFIRMED, VERIFIED OFFLINE | Strict immutable V1 records, legacy drafts, digest-bound whole-baseline decisions, SQLite history and inspection; no runtime integration |
| Offline M1 authority-bound plan CLI | CONFIRMED, VERIFIED OFFLINE | Complete criterion dispositions, stable scenarios, immutable plan exports and current authority observations; no plan/execution approval or runtime integration |
| SRS ingestion | PARTIAL | PDF text/tables, empty-document OCR fallback; no upload API/DOCX input |
| Extraction/validation | PARTIAL | Five passes; heuristic filtering, inferred gaps, unsafe deduplication |
| LangGraph orchestration | CONFIRMED | Three principal agents plus domain inference and planner calls |
| Discovery/authentication | PARTIAL | HTTP/browser crawl and auth flows; integration/policy gaps |
| Source-code/API-document ingestion | MISSING | Observed API request paths do not constitute API contracts |
| Product MCP integration | MISSING | Runtime uses direct Python/provider/browser calls |
| Inline Playwright generation/execution | CONFIRMED | Batched TypeScript test blocks and local Node runner |
| POM generation | MISSING | No page-object/fixture artifact generation contract |
| Traceability/result accounting | PARTIAL | IDs exist; title matching and coverage accounting are unsafe |
| Defect adjudication/repair fidelity | BROKEN | No reliable defect distinction; repair can weaken assertions |
| Approval enforcement | BROKEN | Rejected tests can be written; timeouts approve pending items |
| Termination | PARTIAL | Evaluation cap exists; generation/transition guards incomplete |
| Checkpoints/resume | PARTIAL | SQLite and resume path exist; run listing broken; replay unverified |
| Memory/retrieval | CONFIRMED | ChromaDB and JSON storage; benefit UNVERIFIED |
| Prompt evolution | MISSING | Configuration/constants without an implemented evolution path |
| Observability | PARTIAL | Logging, JSONL, static reports/dashboard; misleading quality metrics |
| ATS tests/evaluation corpus | PARTIAL | 78 maintained offline M0/M1 tests; no maintained existing-runtime regression/evaluation corpus; generated target-site specs are not ATS regression tests |
| Platform backend/UI | PARTIAL | CLI, static review pages, local feedback endpoint; no upload service |
| CI/deployment infrastructure | MISSING | No maintained quality workflow/deployment manifests found |

Sources and detailed limitations are in [ARCHITECTURE](ARCHITECTURE.md) and
[AUDIT_FINDINGS](AUDIT_FINDINGS.md).

## Historical architecture and M0 specification assessment

The [ADR review](adr/README.md) retains LangGraph but proposes deterministic authority,
immutable criteria, final-bundle approval, isolated execution, reviewed repair and
application-owned evidence records alongside checkpoints. All six ADRs are PROPOSED;
no implementation decision is approved merely by this documentation authorization.

[M0](M0_VERSIONED_BASELINES.md) now precedes the earlier evaluator milestone: import
legacy requirements as untrusted drafts, freeze versioned baselines, persist explicit
review records and inspect approval offline. Single-operator trust, whole-baseline
approval, mandatory legacy re-review and unsupported-item handling were explicitly approved
for M0. Exact V1 fields, canonicalization and review/revocation semantics are implemented
under that bounded approval; the full ADRs still require separate scope decisions.
The old eligibility/reconciliation proposal remains follow-up work in ROADMAP.

M0 will not integrate with the runtime graph or fix the existing writer, repair,
runner, parser or approval bypasses. All F01-F17 remain open. No maintained runtime
regression suite was introduced by the earlier documents. The subsequent M0
implementation now has a maintained offline suite; all 33 acceptance cases pass. Next
dependency is the separately scoped foundation follow-up, not automatic M1 execution.

The prior documentation review/local commit completed as `4a59405`; the tree was clean
at the start of this specification phase. Local `main` and the locally recorded
`origin/main` both pointed to that commit when inspected. This phase performed no
fetch/push or live GitHub verification and does not attribute independent ref changes.
Read-only metadata inspection confirmed Python 3.11.9, SQLite 3.45.1 and Pydantic 2.12.5;
it did not validate a clean installation. Only legacy schemas/import behavior, CLI/config
effects, package initializers and exclusions were inspected for the new specification.

Specification-only validation checked 18 Markdown files, 207 local links and 89
heading/source-line anchors; all resolved. Code fences, the 33 acceptance IDs, all
11 decision rationale sections and `git diff --check` passed. A bounded scan of the
seven changed/new documentation files found no local credential-value or common token/
private-key pattern matches. The 27 existing external reference URLs were not revisited.
Application code, prompts, manifests, the audit register, architecture, roadmap and
six ADRs remained unchanged. No M0 test, install, provider/browser call, new commit,
push or deployment occurred during this specification phase. The seven documentation
changes were subsequently reviewed and preserved in `bfbf347` before M0 source work.
Current completion evidence is in M0_VERIFICATION; the specification-only observations
above are historical and do not replace the later 48-test result.

## Environment observed during the audit

These are installed versions at audit time, not desired pins or a reproducible
installation specification. Recheck metadata before implementation.

| Component | Observed version |
| --- | --- |
| Python / Node.js | 3.11.9 / 22.17.0 |
| LangGraph / LangChain Core | 1.1.1 / 1.2.18 |
| LangGraph checkpoint / SQLite checkpoint | 4.0.1 / 3.0.3 |
| Pydantic / OpenAI SDK | 2.12.5 / 2.26.0 |
| google-genai / legacy google-generativeai | 1.67.0 / 0.8.6 |
| Python Playwright / Node Playwright | 1.58.0 / 1.58.2 |
| ChromaDB | 1.5.5 |
| sentence-transformers / faiss-cpu | 5.2.3 / 1.13.2 |
| pdfplumber / HTTPX | 0.11.9 / 0.28.1 |

[requirements.txt](../requirements.txt) uses broad minimum versions without a
Python lockfile. It does not actively declare google-genai or
langgraph-checkpoint-sqlite, despite imports; a commented installation command
does not declare a dependency. Node has a [lockfile](../playwright_project/package-lock.json)
and manifest constraint `@playwright/test ^1.58.2`. pytest, Ruff, and mypy were
not installed. [package.json:7](../playwright_project/package.json#L7) defines a
scaffold `npm test` command that fails intentionally.

## Validation already performed

- Python 3.11.9 parsed all 31 Python source files using `ast.parse`: no syntax errors.
- `.venv\Scripts\python.exe -B -m pip check`: no broken installed requirements.
  This does not establish complete manifests, imports, or fresh-install success.
- Installed metadata, Node lockfile, and `node --version` were inspected.
- SQLite queries used `mode=ro`; the run-list query reproduced a missing-column error.
- Isolated source-function probes used in-memory dependencies to demonstrate
  failures; see the finding IDs and reproduction descriptions in AUDIT_FINDINGS.
  These were not a full imported application or a committed regression suite.
- Two audit-harness setup issues (console encoding and an omitted mock constant)
  were corrected; they are not product defects.

No full pipeline, browser, LLM, OCR, resume, or security exploit execution was
performed. No implementation changes or dependency installations were made by
the audit. Its documentation pass created the six original Markdown files.
The subsequent Git preparation changes exclusions and handoff documentation only;
it does not fix runtime findings or establish a successful product execution.

## Architecture handoff verification (2026-10-23)

The documentation pass checked 16 Markdown files (AGENTS and docs), 181 local
links including source-line bounds, six ADRs with sections A-I, and 17 labeled M0
acceptance cases. No missing local targets, invalid source-line bounds or unbalanced
code fences were found. `git diff --check` passed. All changed/new paths were
documentation; application source, prompts, manifests and the audit register stayed
unchanged. Manual review reconciled proposal status, milestone order and completed
Git publication; contracts are linked to their canonical documents rather than
duplicated in the handoff.

The 27 external reference links were retained from earlier research and were not
network-checked. Six distinct historical evidence paths resolve locally but are
deliberately untracked runtime artifacts, so a clean clone cannot inspect them.
Installed-package source references in ADRs are historical local evidence, not
portable tracked dependencies. No product acceptance tests, model calls, browser
execution, dependency installation, deployment, commits or pushes occurred.

## Historical artifact evidence

Run `ats_20260318_131928_81d907` has 43 Playwright results: 42 passed, one failed,
zero skipped/flaky in its stored report. Stored metrics record 95.3% coverage,
97.7% pass rate, and eight evaluations. The checkpoint database contains 46
checkpoints for this run; telemetry contains 21 events. The cached requirements
bundle has 43 requirements, no gaps, and records 46 initial extractions with
three deduplication removals.

References: [Playwright results](../output/pw_results_ats_20260318_131928_81d907.json),
[run metrics](../memory/run_metrics.json), [telemetry](../monitoring/metrics.jsonl),
[requirements cache](../cache/requirements_ffb6b4e9c77b6c34.json).
These runtime artifacts are deliberately excluded from Git and remain locally.
Their links will not resolve in a clean clone; absence does not invalidate the
recorded audit observation, but prevents direct reinspection. Do not copy them
into Git to make audit links pass validation.

The source fallback is five evaluations; `.env.example:33` specifies eight and
the local nonsecret setting inspected during the audit was also eight. This
explains the stored count without establishing exact historical source identity.
Passing artifacts include weakened/vacuous assertions (F01); reported percentages
are not evidence that all corresponding requirements were actually satisfied.
