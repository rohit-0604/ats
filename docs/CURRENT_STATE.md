# Current state

Baseline date: 2026-10-22 (Asia/Calcutta). This records the completed repository
audit, accepted by the user as the factual baseline. It is not a claim of a
successful current end-to-end execution.

## Read this documentation

- [AGENTS.md](../AGENTS.md): enforceable engineering instructions.
- [ARCHITECTURE](ARCHITECTURE.md): implemented components and data flow.
- [AUDIT_FINDINGS](AUDIT_FINDINGS.md): evidence, priorities, validation, remedies.
- [DECISIONS](DECISIONS.md): accepted constraints, proposals, unresolved choices.
- [NEXT_STEPS](NEXT_STEPS.md): scoped milestone and self-contained session handoff.

## Repository provenance and scope

Workspace: `C:\Users\rohit\Desktop\ATS\ats`.

At the initial audit, `git rev-parse --show-toplevel` failed and no workspace or
parent Git marker was found. On 2026-10-22 the user subsequently authorized safe
local version control preparation. Git was initialized at this exact workspace
on branch `main` after checking exclusions and provenance; there was no existing
local history to preserve. The initial commit is a snapshot of this workspace,
not recovered upstream development history. No remote is configured or approved.
No matching repository was identified in the connected GitHub account; copies
outside that account/access scope remain unverified. See
[GIT_PREPARATION](GIT_PREPARATION.md) for the exact inventory, sensitive-file
assessment, validation, and approval steps before any GitHub publication.

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
| ATS tests/evaluation corpus | MISSING | Generated target-site specs are not ATS regression tests |
| Platform backend/UI | PARTIAL | CLI, static review pages, local feedback endpoint; no upload service |
| CI/deployment infrastructure | MISSING | No maintained quality workflow/deployment manifests found |

Sources and detailed limitations are in [ARCHITECTURE](ARCHITECTURE.md) and
[AUDIT_FINDINGS](AUDIT_FINDINGS.md).

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
