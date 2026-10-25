# M1 implementation and verification record

Date: 2026-10-25 (Asia/Calcutta). Specification: **M1-SPEC-2026-10-25-v2**.
Status: **IMPLEMENTED AND VERIFIED OFFLINE**. The user's "Go" explicitly accepted the
preceding scoped implementation/verification step; C16 in [DECISIONS](DECISIONS.md)
records authorization. M1-D01..06 and all 30 acceptance families were preserved.
That implementation phase authorized no local commit or publication. The subsequent
finalization request (C17) separately authorizes review, a full offline rerun, necessary
handoff corrections and one local M1 implementation commit after passing verification.
Existing documentation edits were preserved; no history rewrite or publication is authorized.

## Result and exact command

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

**Finalization rerun: 78 tests passed in 30.575 seconds; zero failures, errors or skips.** This comprises
all 48 existing M0 acceptance/regression tests plus 30 named M1 acceptance methods.
The earlier implementation verification passed the same 78 tests in 27.674 seconds.
The source under verification used Python 3.11.9, Pydantic 2.12.5 and SQLite 3.45.1
on this Windows host. No packages were installed. Black, Ruff and mypy were unavailable;
no formatting/lint/type-check pass or clean-install validation is claimed.

Final review parsed all 44 first-party Python files with `ast.parse`; 23 Markdown
files, 370 local links and 145 source/heading anchors passed validation. All 53 tracked
preexisting non-documentation files were byte-for-byte unchanged. The approved M1
scope/non-goals, six decision rows, 30 acceptance rows, six SC-01 rows and preexisting
user AGENTS instruction were preserved. The 18 changed/new paths comprise 11
documentation paths and seven new implementation/test/fixture paths. Bounded scans
found no local credential-value or common token/private-key matches. `git diff --check`
passed; external links were not network-checked. The pre-finalization index was empty.
The commit inventory is exactly the seven implementation/test/fixture paths below and
11 documentation paths: AGENTS, ARCHITECTURE, CAPABILITY_REQUIREMENTS, CURRENT_STATE,
DECISIONS, M1_AUTHORITY_BOUND_PLANS, M1_VERIFICATION, NEXT_STEPS, POST_M0_FOUNDATIONS,
ROADMAP and adr/README. No runtime database, real user input, credential or generated
execution artifact belongs to this inventory. Full ADR text, M0 source/contracts/tests,
legacy runtime, prompts and dependency manifests remain unchanged against parent
`d17974a9ac17f209ed110a86b11c504e2cc3bc49`.

The tests use synthetic requirements/scenarios, temporary local stores/files, fake
inspection responses and fault injection. Real bounded SQLite contention, a hot journal,
exclusive exports and a temporary Windows junction were exercised. Trusted test-owned
Python child processes create crash/no-effects fixtures; they do not execute generated
code. No legacy generator/crawler/repair/runner, target, provider or browser was invoked.

## Implemented files and boundaries

| File | Responsibility |
| --- | --- |
| [plan_contracts.py](../app/plan_contracts.py) | Separate strict immutable V1 plan/assessment models, safe errors, deterministic UUIDs, plan-specific ordering/hash and aggregate bounds |
| [plan_policy.py](../app/core/plan_policy.py) | Pure complete-set/disposition validation, freeze, inspection validation and deterministic non-authorizing admission |
| [plan_service.py](../app/core/plan_service.py) | One public M0 inspect call per operation; prepare/freeze consumes the same validated observation as assessment |
| [plan_cli.py](../app/plan_cli.py) | Separate offline help/version/scenario-id/validate/freeze/assess commands, exclusive exports and safe failure exits |
| [test_m1_plans.py](../tests/test_m1_plans.py) | Contract/identity/policy/golden/boundary/count cases and synthetic fixture helpers |
| [test_m1_plan_boundaries.py](../tests/test_m1_plan_boundaries.py) | Real-store authority, CLI, import/no-effects, path/export/fault and full journey cases |
| [golden.json](../tests/fixtures/plans/golden.json) | Synthetic M0/plan input and independently calculated stdlib UUID/canonical/digest vectors; no M1 implementation imported by its generator |

No new database, approval record, worker, adapter platform or runtime graph state was
added. `prepare_plan` is a small internal service convenience, and `validate_inspection`
is a shared pure guard; they do not introduce additional wire contracts or authority.
M0 public APIs, store schema, canonicalization and existing test assertions are unchanged.
Plan collection ordering is implemented separately from M0's canonicalizer.

## Acceptance evidence

Each row maps to the unique `test_m1_ac_NN_*` method in the two test modules. Rows
summarize actual executed fixtures, not arbitrary-input proof. Exact expected behavior
remains in [the approved specification](M1_AUTHORITY_BOUND_PLANS.md#offline-acceptance-matrix).

| Case | Result | Evidence exercised |
| --- | --- | --- |
| M1-AC-01 | PASS | Real approved temporary M0 store; ready observation, exact counts, false authority flags; scenario/criterion/requirement/source chain; store bytes unchanged |
| M1-AC-02 | PASS | Pending/rejected/revoked/superseded states and forbidden legacy approval/actor fields; no ancestor activation |
| M1-AC-03 | PASS | Same immutable plan before/after revocation; fresh read blocks; original content/history retained |
| M1-AC-04 | PASS | Prior approval decision and serialized/cached assessment cannot substitute for a typed current inspection |
| M1-AC-05 | PASS | Fake wrong project/digest/active/head/sequence/status, malformed prepare observation and cross-project plans fail explicitly |
| M1-AC-06 | PASS | Unrelated rejected proposal advances project sequence without revoking the active baseline |
| M1-AC-07 | PASS | Multiple criteria and four scenarios under one requirement; duplicate titles and similar text retained |
| M1-AC-08 | PASS | Independent exact canonical bytes/digest; object/scenario/disposition reordering preserves identity; no canonical newline |
| M1-AC-09 | PASS | Title, steps/precondition order, disposition reason, scenario key and baseline changes; preserved meaningful Unicode normalization differences |
| M1-AC-10 | PASS | Independent project/criterion/key UUID vectors; forged or reassigned scenario identity rejected |
| M1-AC-11 | PASS | Duplicate scenario/disposition IDs, missing/foreign set entries, valid-ID dangling scenarios and no-criterion snapshot fail |
| M1-AC-12 | PASS | Supported unfinished criterion freezes as a proposal but blocks readiness with explicit reasons/counts |
| M1-AC-13 | PASS | Mixed supported/unsupported criteria retain complete accounting; no coverage/result claim |
| M1-AC-14 | PASS | Approved all-unsupported baseline remains a valid blocked proposal with no scenarios |
| M1-AC-15 | PASS | Pending unresolved/unknown, specified/unknown, unresolved/supported and unresolved/unsupported variants; no fabricated readiness |
| M1-AC-16 | PASS | Changed support disposition/reason or attached unsupported scenario rejected; original M0 content preserved |
| M1-AC-17 | PASS | Unknown fields/version, invalid UUID/digest, strict boolean/version rules, duplicate JSON keys and nonfinite input; file/Python validation |
| M1-AC-18 | PASS | Byte/depth/node, title/text/step/precondition and collection bounds; 5000 scenarios/dispositions accepted structurally, excess/aggregate input rejected; BOM/encoding/control/surrogate cases |
| M1-AC-19 | PASS | Nested tuple immutability, validated copy APIs and integrity checks; invalid copies fail |
| M1-AC-20 | PASS | Tampered content/digest fails; valid pretty JSON can be read without rewriting its source |
| M1-AC-21 | PASS | Real missing/future/corrupt stores, exclusive lock and hot journal; safe injected error matrix; no recovery writes or implicit creation |
| M1-AC-22 | PASS | Exactly one inspect call, no other store interface; fresh-process import/help/version/ID with write/network/subprocess/legacy-import traps |
| M1-AC-23 | PASS | Revocation after coherent read but before export: prior observation remains non-authorizing; next assess blocks |
| M1-AC-24 | PASS | Actual Windows Unicode/space output, exclusive publication, UNC/device/drive-relative/ADS/reserved/trailing/missing-parent paths and real junction denial |
| M1-AC-25 | PASS | fsync/rename failures, lost stdout acknowledgment, actual stdout flush failure and interruption; existing/output files preserved as appropriate |
| M1-AC-26 | PASS | Ready/blocked validate, freeze and assess, exact exit semantics/newline; force/execute/auto/approved/actor arguments safely rejected |
| M1-AC-27 | PASS | Instruction/path/private sentinels stay inert; no model/network/subprocess calls or text leakage in diagnostics/assessment; M0 oracle unchanged |
| M1-AC-28 | PASS | Real offline validate -> exclusive freeze -> assess -> explicit test-owned revoke -> blocked reassessment; plan bytes unchanged |
| M1-AC-29 | PASS | M0 schema fingerprint/canonical snapshot vectors; all existing 48 tests passed unchanged in the same full run; separate protected-source inventory |
| M1-AC-30 | PASS | Complete deterministic counts/issues with combined authority/unplanned/empty blockers; literal false rejects integer zero; no success/coverage/result fields |

## Failure history and corrections

The first test-first run failed to import the not-yet-created M1 modules, as expected.
The first complete M1 run had two fixture errors: a rejected snapshot was recreated
with identical content then approved (correctly forbidden by M0), and a test attempted
to encode an unpaired surrogate directly as UTF-8 before reaching the parser. The
fixtures now create distinct successor content and send escaped JSON respectively;
original product expectations were retained.

An expanded negative observation test exposed a real implementation defect:
`prepare_plan` accessed `.snapshot` before validating a malformed inspection result,
raising AttributeError. A shared typed inspection guard now rejects it as safe
`AUTHORITY_MISMATCH` before consuming members. The regression remains in M1-AC-05.
The subsequent 30-case M1 run passed in 12.962 seconds. Further required boundary
variants were then included, followed by the final 78-test run recorded above.
No assertion was weakened, error hidden or approved oracle changed to obtain a pass.

## Decisions, compatibility and operational limits

M1-D01..06 are accepted within M1 only. [The capability register](CAPABILITY_REQUIREMENTS.md)
continues to defer adaptive routing, cloud adapters, source-aware analysis, professional
UI, isolated execution and other product workstreams. No full ADR was approved.

- **Proposals versus authority:** freeze works for structurally valid inactive or
  unfinished content; assessment readiness requires current active M0 approval and a
  complete supported plan. Neither operation reviews/approves the plan or permits a tool.
- **One coherent observation:** existing `ReviewStore.inspect` is sufficient; no SQL or
  write-mode recovery is exposed. A new store/interface framework would add complexity
  without strengthening this limited guarantee. An observation may immediately become stale.
- **Stable identity:** UUIDv5 project/criterion/key identity avoids a new registry but
  depends on retaining keys for the same business scenario. Static checks cannot decide
  semantic sameness or whether scenario prose faithfully exercises its criterion.
- **Content integrity:** exact plan bytes/digest identify a revision, not authorship,
  semantic correctness or safety. Valid noncanonical JSON can be inspected without
  changing the input; only explicit freeze publishes canonical bytes.
- **Local files:** reuse of the approved M0 helpers preserves no-overwrite/local-path
  semantics; they are accidental-path protection, not a race-proof hostile-user sandbox.
  Export and stdout are not one transaction. After output failure/interruption, inspect
  an existing destination's digest rather than overwrite it.
- **Finite input, not runtime budgets:** byte/node/count bounds and SQLite's lock wait
  are tested. Large M0 histories still require conservative integrity reconstruction;
  no worst-case wall-time, global spend budget, cancellation or replay guarantee is added.

All existing F01-F17 runtime findings remain open. The legacy runner still has host
access and is not called by M1. No real target, provider quality/cost, portability,
clean installation, power-loss behavior or adversarial same-user security was verified.

## Local usage and handoff

Use `python -B -m app.plan_cli --help` and `version` without loading legacy config.
Create a JSON draft with an explicit project/baseline digest, a disposition for each
criterion and deterministic scenario IDs from `scenario-id --project ... --criterion ...
--key ...`. Read expectations/provenance using the existing M0 `inspect` command.
No scenario generator or automatic plan-authoring command is introduced.

`validate --db ... --draft ...` returns the current assessment (exit 0 ready, 3 blocked).
`freeze --db ... --draft ... --out ...` publishes an exclusive canonical proposal and
returns exit 0 even for a blocked plan, with that status explicit. `assess --db ...
--plan ...` rereads authority. Input errors exit 2; store/path/integrity/output errors
exit 4; interruption exits 130. Keep real drafts/plans in excluded private runtime
directories, not Git; only synthetic fixtures were added here.

M1 work is complete within the authorized offline scope. Finalization authorizes one
local commit, `feat: implement offline M1 authority-bound scenario plans`, containing
this record. NEXT_STEPS records its parent and exact hash-recovery command for a fresh
session; commit creation is followed by index/worktree/history verification. No push
or remote query is authorized. M2 specification/implementation, runtime integration,
installs, providers, generated execution and Git publication require separate scoped
authorization. All deferred product workstreams remain in CAPABILITY_REQUIREMENTS
and ROADMAP; no second specification or new architecture was introduced.
