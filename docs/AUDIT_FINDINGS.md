# Audit findings

Baseline: 2026-10-22. This is the canonical finding register; other documents link
here instead of reproducing details. See [CURRENT_STATE](CURRENT_STATE.md) for
validation limits and [NEXT_STEPS](NEXT_STEPS.md) for prioritization.

## Evidence labels

- **SOURCE**: directly inspected implementation. Reachable behavior may be clear
  without running the full system; exploitability/operational success is not implied.
- **PROBE**: executed selected source functions with in-memory substitutes, or a
  read-only database query. These are bounded demonstrations, not end-to-end tests.
- **ARTIFACT**: inspected previously stored files; no current rerun was performed.
- **UNVERIFIED**: claim not established by source/probe/artifact evidence.
- **RECOMMENDATION**: proposed remedy, not implemented or approved for execution.

P0 means resolve before treating execution/approval/results as a trusted boundary.
P1 means foundational correctness/reproducibility work. P2 is important follow-up.
No findings have been fixed by this documentation pass. Source links use relative
paths and line anchors from the inspected baseline; recheck anchors after edits.

## P0 findings

### F01 - Repairs can change the test oracle and hide application defects

**Status: SOURCE + ARTIFACT; defect adjudication is missing.**

The active [repair prompt:25](../prompts/agent_c_repair_v1.txt#L25) instructs the
model to replace expected values with observed values. Its timeout strategy
replaces count/CSS checks with visibility or substitutes nearby routes. The
general request to preserve intent contradicts these specific instructions.
[Planner prompt:112](../app/core/react_controller.py#L112) similarly directs
assertion failures toward fixing expected values. [_build_repair_context():178](../app/agents/repair_agent.py#L178)
sends test code and observations without original requirement descriptions or
acceptance criteria. Error classification alone cannot establish root cause.

Existing artifacts demonstrate the semantic loss:

- [homepage.spec.ts:50](../playwright_project/tests/homepage.spec.ts#L50):
  "Minimum Four Feature Cards" only asserts text visibility.
- [elements.spec.ts:17](../playwright_project/tests/elements.spec.ts#L17):
  "Client-Side Filtering" only asserts a navigation link is visible.
- [homepage.spec.ts:124](../playwright_project/tests/homepage.spec.ts#L124):
  monthly-price assertions can execute zero times and include `/$d+/`.

The stored requirement cache describes actual counts/filtering/prices, not these
weaker observations. Exact generation-versus-repair attribution is unverified.
The extraction prompt also incorrectly treats broad classes of count/CSS checks
as unsuitable and suggests weaker replacements ([extraction_agent.py:93](../app/agents/extraction_agent.py#L93)).

**Recommendation:** preserve immutable approved criteria, provide them to repair,
classify application/test/environment/unknown causes, and require review for
changes to expected behavior. Validate on seeded application defects and faulty
tests; a genuine defect must remain detectable after attempted repair.

### F02 - Generated tests execute with host privileges and inherited environment

**Status: SOURCE; no exploitation performed.**

[run_playwright():123](../app/core/evaluator_engine.py#L123) runs generated Node
code locally and passes `os.environ`. No isolated worker, secret-free environment,
filesystem boundary, or centralized egress policy is implemented. Filtering env
alone would not prevent host filesystem access. Untrusted document/DOM/model data
can influence executable output. Credentials also enter graph state through
resource/auth dictionaries ([AgentState:42](../app/core/react_controller.py#L42),
[handle_auth():34](../app/core/auth_handler.py#L34)).

**Recommendation:** disposable isolated workers, minimal environment, no secret
or source mounts, scoped target credentials, process/resource limits, and enforced
network policy. Verify denied file/network/process actions before real-target use.

### F03 - Untrusted filenames and shared destructive artifact writes

**Status: SOURCE + PROBE of acceptance; no escaping write was performed.**

[_parse_batch():308](../app/agents/codegen_agent.py#L308) accepts arbitrary model
`spec_file` and unknown `req_id` values. A probe accepted `../../escape.ts` and an
ID absent from its inputs. [write_spec_files():67](../app/core/evaluator_engine.py#L67)
deletes existing top-level specs and joins the generated name directly to TESTS_DIR
without resolved containment checks. Absolute/traversal paths can escape the
intended directory. Concurrent runs share the same artifacts.

**Recommendation:** validate artifact names, extensions, resolved containment and
symlink/reparse-point boundaries; reject unknown IDs; create per-run output
directories and publish only validated artifacts. Test both Windows and POSIX
path forms. Never reproduce traversal using real workspace writes.

### F04 - Human rejection and required review are not enforced

**Status: SOURCE + PROBE.**

[_apply_phase2_feedback():459](../app/core/react_controller.py#L459) sets rejection,
but [write_spec_files():78](../app/core/evaluator_engine.py#L78) iterates every test.
An in-memory writer probe confirmed a rejected test was materialized.
[_auto_approve_requirements():145](../app/hitl/hitl_manager.py#L145) approves every
branch, including gaps and low-confidence requirements. A probe with a gap at
confidence 0.1 returned approved. Noninteractive and saved-bundle paths also
approve nonrejected requirements ([node_agent_a():359](../app/core/react_controller.py#L359)).
HITL scheduling remains planner-selected; auto-mode is not enforced as a complete
deterministic routing policy.

**Recommendation:** explicit approval states and eligibility checks immediately
before materialization/execution. Required review must remain pending on timeout.
Test rejection, pending states, inferred requirements, mode combinations, and
attempted planner bypasses.

## P1 findings

### F05 - Result mapping and coverage are unsound

**Status: SOURCE + PROBE.**

[parse_results():289](../app/core/evaluator_engine.py#L289) visits only direct
suite specs, skipping nested describe suites. A flat synthetic passing spec
returned one result; the same spec nested under a child suite returned zero.
[_find_test_by_title():344](../app/core/evaluator_engine.py#L344) matches title
equality or a substring anywhere in test code; duplicate titles are ambiguous.
[build_report():417](../app/core/evaluator_engine.py#L417) counts distinct passing
IDs without membership in the approved set. Two passing IDs with one approved
requirement produced 200% coverage. Unknown model IDs are accepted by generation.
Missing results and top-level runner errors are not fully reconciled with plans.

**Recommendation:** explicit stable test IDs/annotations and artifact manifest,
recursive report traversal, full planned-result reconciliation, and approved-ID
membership checks. Reject invalid identities rather than merely clamping totals.
Distinguish planned coverage, execution status, and proven criteria.

### F06 - Deduplication discards distinct requirements/scenarios

**Status: SOURCE + PROBE.**

[Requirement.content_words():111](../app/schemas.py#L111) removes negation terms.
[_pass5_dedup():401](../app/agents/extraction_agent.py#L401) drops later entries on
title/content token overlap. A probe using "Users must access admin reports" and
"Users must not access admin reports" removed one requirement.
[TestSuite.deduplicate():187](../app/schemas.py#L187) also removes later tests
sharing req_id and can merge similar code for different requirements.

**Recommendation:** preserve source records; propose duplicates for adjudication.
Allow multiple positive/negative/boundary scenarios per criterion. Verify negation,
different roles/thresholds, and similar test code for distinct requirements.

### F07 - Lifecycle and budget guards are incomplete

**Status: SOURCE + PROBE.**

[planner_node():154](../app/core/react_controller.py#L154) changes generate_count
from zero to one only; the guard requires two. A stubbed planner returning generate
four times stayed at count one. loop_count increments only at evaluation
([node_evaluator():513](../app/core/react_controller.py#L513)), so repeated other
actions evade the application evaluation budget. Planner output is not validated
against deterministic state prerequisites. Direct done can bypass finalization;
stale reports can survive regeneration. Framework recursion limits are a separate
backstop and must not be confused with repair budgets.

**Recommendation:** validate transitions, increment action-specific and total
budgets at their actual effects, set time/cost limits, invalidate stale results,
and record explicit terminal reasons. Test empty generation, invalid actions,
provider failure, repeated regeneration, review routing, and replay.

### F08 - Extract-only finalization and run listing fail

**Status: SOURCE + PROBE.**

Extract-only routes to learning after extraction. Initial test_suite is None;
[node_post_run_learn():625](../app/core/react_controller.py#L625) attempts
`TestSuite(**None)`. A stubbed-learner probe reproduced TypeError. Startup still
performs inference/auth/crawl before extraction. Codegen-only returns generated
state but does not reach the evaluator's spec writer.

[list_runs():794](../app/core/react_controller.py#L794) queries parent_id. Read-only
SQLite inspection found parent_checkpoint_id instead; the query failed with
`no such column: parent_id`. The function catches the error and returns an empty
list, obscuring stored runs.

**Recommendation:** specify mode inputs/effects/outputs and valid terminal states;
fix finalization and checkpoint queries. Test each CLI mode offline. Separately
decide whether extract-only should perform target network access.

### F09 - Authentication configuration and test execution diverge

**Status: SOURCE; authenticated end-to-end behavior UNVERIFIED.**

[handle_auth():30](../app/core/auth_handler.py#L30) omits configured login_url from
AuthContext. [_handle_bearer_token():143](../app/core/auth_handler.py#L143) does not
resolve relative token endpoints. Form-login failure can continue unauthenticated,
and successful session saving does not prove valid login. Crawler auth state/headers
are not passed to Node tests through [evaluate():448](../app/core/evaluator_engine.py#L448).
Generated login code instead relies on separate environment credentials and guessed
routes. Resource extra_headers/feature_areas examples are not fully wired through.

**Recommendation:** validated auth configuration, resolved URLs, verified login,
explicit auth failure state, and a shared execution fixture using secret references.
Test each auth mode against an owned local fixture, including failed login.

### F10 - Crawling lacks consistent destination and skip enforcement

**Status: SOURCE; unauthorized access was not exercised.**

[_spider():111](../app/core/route_crawler.py#L111) uses substring host comparison,
follows redirects, and recurses even when add_route rejects a skipped path. The
page cap is applied after discovery requests. [crawl():368](../app/core/route_crawler.py#L368)
can navigate non-relative routes without a central authorization policy. Browser
subrequests also lack such a policy. robots Disallow entries are used as discovery
inputs; they do not grant testing authorization.

**Recommendation:** a single destination policy for initial targets, discovered
URLs, redirects, direct HTTP, and browser requests. Validate scheme/origin/resolved
address and explicitly approved private/local targets. Enforce skip rules and
request budgets before requests, not only before storing routes.

### F11 - Review/report rendering and feedback are unsafe

**Status: SOURCE; browser exploitability not dynamically tested.**

[_FeedbackHandler:44](../app/hitl/hitl_manager.py#L44) accepts unauthenticated JSON
POSTs, with wildcard CORS and no run-bound nonce/body-size enforcement.
[Review rendering:300](../app/hitl/hitl_manager.py#L300) embeds JSON into script
content and unescaped requirement fields into innerHTML. Escaping test code alone
does not protect all contexts. [_generate_html_report():76](../app/core/quality_monitor.py#L76)
inserts errors/identifiers into HTML unescaped.

**Recommendation:** contextual escaping/safe DOM rendering; safe JSON embedding;
feedback origin, nonce, run/phase, schema, and size validation. Test malicious
document/DOM-derived strings without contacting third-party pages.

### F12 - Dependency declarations do not reproduce the installed environment

**Status: SOURCE + installed metadata; clean installation UNVERIFIED.**

[gemini.py:27](../app/llm/gemini.py#L27) imports google.genai while
[requirements.txt:5](../requirements.txt#L5) declares legacy google-generativeai.
[react_controller.py:22](../app/core/react_controller.py#L22) imports the separate
SQLite checkpointer without an active requirement declaration. The relevant
packages are installed locally, masking omissions. Python uses broad lower bounds;
no Python lockfile exists. Python and Node Playwright versions differ.

**Recommendation:** declare direct dependencies and agree supported runtime/browser
versions; produce a tested lock strategy and clean setup gate. Do not blindly freeze
all incidental packages or treat pip check as a fresh-install verification.

### F13 - Completion status can report success despite unmet targets

**Status: SOURCE.**

[cmd_run():152](../main.py#L152) returns zero after pipeline completion even if targets
are unmet. [build_report():411](../app/core/evaluator_engine.py#L411) defaults exit_reason
to unknown; the evaluator does not supply a meaningful terminal reason. Parse/startup
failures can be conflated with test failures. CI cannot reliably infer outcome.

**Recommendation:** agree machine-readable terminal statuses and CLI exit semantics;
propagate runner/startup/infrastructure errors and incomplete evidence. Test success,
application failure, invalid output, timeout, budget exhaustion, and cancellation.

## P2 and supporting architectural risks

- **F14 - Misleading telemetry (SOURCE):** repair success counts accepted rewrites
  before validation ([repair_agent.py:243](../app/agents/repair_agent.py#L243)); codegen
  hallucination metrics precede detection ([codegen_agent.py:496](../app/agents/codegen_agent.py#L496)).
  Evaluation duration resets per evaluation. History is sorted newest-first but
  anomaly detection uses the last record; current metrics are saved before comparison.
  Record attempts, valid edits, executed repairs, preserved criteria, and actual passes separately.
- **F15 - Cache and memory reliability (SOURCE):** PDF cache keys omit target and
  extraction/prompt/model versions ([_cache_path():441](../app/agents/extraction_agent.py#L441)).
  Blocklist retrieval is global ([agent_memory.py:384](../app/memory/agent_memory.py#L384));
  JSON writes are non-atomic. Learned confidence does not demonstrate causal benefit.
  Scope/version caches and lessons, preserve provenance, and benchmark retrieval.
- **F16 - Selector evidence is incomplete (SOURCE):** absence from a partial map is
  labeled hallucination ([detect_hallucinations():353](../app/core/evaluator_engine.py#L353)).
  Guest homepage-link absence labels routes auth-only ([route_crawler.py:338](../app/core/route_crawler.py#L338)).
  force_crawl has no effective cache invalidation. Evaluator mutations of a reconstructed
  suite are not returned by node_evaluator, weakening downstream evidence propagation.
- **F17 - Development gates and documentation drift (SOURCE):** no ATS regression
  suite, lint/type config, CI, evaluation corpus, or verified clean setup was found.
  Active prompt files override differing embedded defaults. Prompt-evolution constants
  do not establish an implementation. Reset instructions include destructive commands
  and must not serve as routine development setup.

## Probe provenance and reproduction contract

Probes ran through existing Python with `-B`; schemas/functions were compiled or
selected into an in-memory namespace. LLM, telemetry, learner, snapshot loading,
and writer effects were replaced where relevant. No browser/provider call or real
generated-file write occurred. SQLite was opened with mode=ro. Probe scripts were
not saved during the read-only audit; the descriptions in F03-F08 define inputs and
observed failures for future maintained regression tests. A successful reproduction
of a bug is evidence of the bug, not a passing product acceptance test.

## Claims still unverified

Reliable generalization to arbitrary applications, improved quality from memory,
provider cost/free-tier claims, current model availability, OCR system setup,
authenticated end-to-end execution, safe replay/resume, production readiness,
and extraction accuracy against an independently adjudicated original SRS remain
unverified. POM generation, upload APIs, source/API-document ingestion, and automatic
prompt evolution were not found. Future implementation must not relabel these as
confirmed without evidence.
