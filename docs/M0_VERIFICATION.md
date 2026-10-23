# M0 implementation and verification record

Date: 2026-10-23, Asia/Calcutta. Revision: `M0-SPEC-2026-10-23-v2`.
Status: **IMPLEMENTED AND VERIFIED OFFLINE**. The user explicitly approved the exact
M0 contracts and AC-01..33, designated the human CLI operator as reviewer, authorized
the separate specification commit and a reviewed local implementation commit, and
prohibited pushing or beginning M1. The seven preexisting specification changes were
reviewed and preserved separately in **`bfbf347`** before source changes began.

## What was implemented

| File | Responsibility and reason |
| --- | --- |
| [baseline_contracts.py](../app/baseline_contracts.py) | Strict immutable V1 objects, UUID validation, bounded JSON, canonical bytes and SHA-256; keeps authority independent of mutable runtime models |
| [baseline_review.py](../app/core/baseline_review.py) | Pure legacy adapter, deterministic imported IDs, freeze and approval rules; imports never grant approval |
| [review_store.py](../app/core/review_store.py) | Explicit SQLite initialization, immutable snapshots, append-only decisions, expected sequences, history, supersession/revocation and original-request reconciliation |
| [baseline_files.py](../app/core/baseline_files.py) | Bounded reads, explicit Windows paths, exclusive output; shared by CLI/store to avoid an import cycle or duplicated filesystem policy |
| [baseline_cli.py](../app/baseline_cli.py) | Offline prepare/validate/freeze/review/inspect/history commands, safe JSON errors and explicit exit codes; no legacy bootstrap |
| [acceptance tests](../tests/test_m0_acceptance.py) | One named method per AC-01..33, including parameterized transition/path/failure cases |
| [focused regressions](../tests/test_m0_regressions.py) | 15 additional regressions for data disclosure, mutation, overflow, identity, concurrency, tampering and aggregate bounds |
| [synthetic fixtures](../tests/fixtures/baselines/legacy.json), [golden vectors](../tests/fixtures/baselines/golden.json) | Nonsecret legacy input and independently prepared ASCII/Unicode canonical-byte/digest vectors |

The small shared filesystem module is an organizational choice within the approved
file-boundary scope. Existing `RequirementBundle`, LangGraph, crawler, repair engine,
writer, Playwright runner and authentication source were preserved. No new package,
framework, runtime integration, provider/target access or generated execution was used.

## Verification command and actual result

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

Final source verification: **48 tests passed in 14.953 seconds; zero failures, errors
or skips**. This comprises all 33 acceptance families plus 15 focused regressions.
Tests used synthetic requirements and temporary stores on this Windows host. Observed
baseline: Python 3.11.9, SQLite 3.45.1, Pydantic 2.12.5. No dependency installation.
Black, Ruff and mypy were not installed; no lint/type-check pass is claimed.

The final inventory review covered 22 implementation/test/status paths. All 38
preexisting runtime/configuration/prompt/manifest/exclusion files checked against
`bfbf347` were byte-for-byte unchanged. All 38 first-party Python files parsed with
`ast.parse`; 233 local documentation links and 89 heading/source-line anchors resolved.
The bounded changed-content scan found no local credential-value or common token/
private-key matches. Existing external references were not network-checked.

Every row below maps to the unique `Acceptance.test_ac_NN_*` method in the acceptance
file. Focused tests name their additional AC mapping explicitly. Passing evidence is
bounded to those fixtures and failures, not proof for arbitrary requirements or hardware.

| Acceptance | Result | Evidence exercised |
| --- | --- | --- |
| M0-AC-01 | PASS | Approved/rejected/inferred flags retained as untrusted claims; no approval |
| M0-AC-02 | PASS | Positive/negative role requirements and original text retained |
| M0-AC-03 | PASS | Multiple distinct criteria persisted under one requirement |
| M0-AC-04 | PASS | Unresolved content can freeze pending but cannot be approved |
| M0-AC-05 | PASS | Clear unsupported criterion approved and inspectable |
| M0-AC-06 | PASS | Unknown versions/fields, duplicate keys/IDs, invalid references and strict booleans |
| M0-AC-07 | PASS | Exact independently prepared canonical bytes/digest |
| M0-AC-08 | PASS | Threshold change produces a new digest; old snapshot retained |
| M0-AC-09 | PASS | Prior approval does not apply to new content |
| M0-AC-10 | PASS | Foreign-project subject rejected without authority change |
| M0-AC-11 | PASS | Identical original request replays after revocation without a new decision |
| M0-AC-12 | PASS | Conflicting request identity and stale sequence rejected atomically |
| M0-AC-13 | PASS | Supersession/history; revocation clears active and retains head |
| M0-AC-14 | PASS | Injected failure after decision insertion rolls back both record and state |
| M0-AC-15 | PASS | Committed snapshots/decisions survive connection reopen |
| M0-AC-16 | PASS | Tampered bytes/schema rejected; focused test preserves schema while changing bytes |
| M0-AC-17 | PASS | Fresh-process import/help/version with file/database/network effects trapped |
| M0-AC-18 | PASS | Project/source-key identities stable across reordering/content edits |
| M0-AC-19 | PASS | Nested immutable values and validated model/deprecated copy APIs |
| M0-AC-20 | PASS | Unicode/whitespace/nulls/order and substantive identity changes; Unicode golden |
| M0-AC-21 | PASS | All 15 state/command combinations; invalid transitions rejected |
| M0-AC-22 | PASS | Competing branches, stale head and actual concurrent command connections |
| M0-AC-23 | PASS | Parent membership, immutable original claims/evidence, criterion reassignment, fresh successor restoration |
| M0-AC-24 | PASS | Lost commit acknowledgment and actual child-process death immediately after commit; same-request recovery |
| M0-AC-25 | PASS | Actor injection rejected; reviewer comes from project; CLI errors do not echo rejected input |
| M0-AC-26 | PASS | Whole-baseline blockers for empty/missing/unknown/legacy-only evidence |
| M0-AC-27 | PASS | Byte/depth/node/text/item/reference bounds, BOM, encoding/nonfinite/large-number errors; Python snapshot API cannot bypass aggregate limits |
| M0-AC-28 | PASS | Real 5-second SQLite lock wait; simulated disk/permission failures; explicit non-success |
| M0-AC-29 | PASS | Actual Windows Unicode/space paths and junction rejection; forbidden path forms; remote-drive classification supplied synthetically |
| M0-AC-30 | PASS | Original provenance hints and null claims retained; omission warnings; unknown fields rejected |
| M0-AC-31 | PASS | No overwrite/implicit database, export/fsync/stdout failures and review reconciliation |
| M0-AC-32 | PASS | Foreign keys, immutable SQL triggers, schema/version/state checks, real hot rollback journal and explicit writer recovery; unrelated WAL store unchanged |
| M0-AC-33 | PASS | End-to-end offline CLI init/project/prepare/edit/validate/freeze/review/inspect/history/revoke flow |

## Failure history and corrections

The test-first run failed at import because the new application modules did not yet
exist. That was expected absence, not an executed product acceptance pass.

The first complete 33-test run had one failure and four errors. Test-owned raw SQLite
connections had not been explicitly closed before Windows temporary cleanup; a socket
stub prevented standard-library SSL class creation; one path mock addressed the previous
module location. Those harness defects were corrected without weakening assertions.
The 33-case suite then passed.

The final documentation check initially flagged Windows CRLF endings in the rewritten
NEXT_STEPS file. Changed/new M0 text was normalized to LF, with Python AST equivalence
checked; the subsequent whitespace check passed. Existing runtime bytes were preserved.

The focused regressions exposed actual implementation defects: argparse echoed rejected
values; deprecated Pydantic copy bypassed validation; huge numeric metadata caused a raw
overflow; write-open changed an unknown WAL database's journal mode before identity
validation. Each was reproduced and fixed. A Unicode golden-generation shell-encoding
issue was also corrected in the fixture generator. Inspection additionally found that
direct Python snapshot construction could exceed aggregate JSON node limits; a new
regression verifies rejection before storage. Final required assertions were preserved.

## Engineering decisions and trade-offs

| What / why | How | Simpler alternative and remaining trade-off |
| --- | --- | --- |
| Separate offline authority from the current runtime | New modules and entry point import only standard library/Pydantic and M0 modules | Reusing main/config is shorter but performs unrelated import effects; deliberate small duplication of command bootstrap |
| Preserve exact approved content and avoid mutation | Frozen nested records/tuples, validated copies, canonical content digest and revalidation on load | Mutable dicts are shorter but lose revision guarantees; Python API immutability is not an adversarial process boundary |
| Make reviews recoverable | Single SQLite transaction, unique request identity, explicit sequence and head/active distinction | A JSON file is simpler but does not provide the required transaction/history semantics; one-host SQLite locking remains |
| Detect inconsistent authority before returning success | Reconstruct and validate project review history against stored pointers | Trusting mutable projections is faster but risks stale authority; full-history validation is intentionally conservative and not large-store benchmarked |
| Keep all failures explicit | Safe static errors, bounded input, no-overwrite outputs, uncertainty after commit acknowledgment loss | Default library errors are easier but can expose input; API callers retain responsibility for private text and local permissions |

The complete WHAT/WHY/HOW, alternatives, failure modes, verification and reconsideration
triggers remain in [decision rationale](M0_DECISION_RATIONALE.md). No approved semantic
contract was replaced merely to produce a passing test.

## Local use and remaining limits

Run `python -B -m app.baseline_cli --help`. Select an existing private local directory
and explicit `.sqlite3` path. `init-store` creates only a new leaf; `create-project`
records the human operator's reviewer label. `prepare` writes an import report/draft
from an explicitly selected legacy file. The operator must inspect/edit expectations,
support and source/human-decision evidence before approval. `validate`, `freeze` and
`inspect` expose the exact digest and sequence; `review` requires both plus a fresh
request UUID and a nonsecret reason. Retry the identical original request after an
uncertain acknowledgment; do not invent another command identity. `history` paginates
decisions. Revocation never silently selects an ancestor.

Local reviewer labels are attribution under trusted OS access, not authentication or
signatures. Same-user/administrator manipulation, hostile filesystem races, confidential
free text, backup/retention, hardware power loss and synchronized/network stores remain
outside the demonstrated guarantees. Disk-full/permission faults and remote-drive type
were simulated; host power loss, real remote storage and clean installation were not
tested. A real junction and SQLite hot journal were tested, with no required-case skips.

All existing **F01-F17 remain open**, particularly P0 assertion weakening (F01), host
execution/secrets (F02), unsafe artifact writes (F03), and runtime approval bypass (F04).
M0 authority is not integrated with that runtime. The next dependency is a separately
approved foundation follow-up covering lifecycle policy, final artifact manifests,
eligibility and result reconciliation. Do not start M1 or live execution from this result.

The implementation commit is local only. Retrieve its exact snapshot with `git log -1`
after the final inventory/secret review; no push or remote operation is part of M0.
