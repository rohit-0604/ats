# M2-R implementation and verification record

2026-10-25 (Asia/Calcutta), C23. The user explicitly approved
[M2R-SPEC-2026-10-25-v1](M2R_DURABLE_REVIEW.md), M2R-D01..08 and M2R-AC-01..30
for bounded offline implementation/tests and reviewed local commits.

## Actual verification

Final full-suite result: **157 tests passed in 85.484 seconds; zero failures, errors
or skips**: all 116 unchanged M0/M1/M2 tests plus 41 new M2-R methods.
Before the final interruption regression, the focused M2-R run passed **40 tests in 22.995 seconds**,
zero failures/errors/skips. The earlier complete suite passed **152 tests in 79.406
seconds**, before four additional CLI/foreign-authority/busy/WAL checks were added.

Commands using the existing environment; no installs:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -p "test_m2r_*.py" -v
.venv/Scripts/python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

Tests use real synthetic M0/M2-R SQLite stores, inert plan/package exports, explicitly
trusted crash-test Python child processes and controlled local thread concurrency.
They never compile, import or execute generated payloads; no target/provider calls,
browser execution, dependencies, runtime graph integration or additional agents occur.
No verified lint/type/CI or clean-install gate is claimed. Environment verified locally:
Python 3.11.9, SQLite 3.45.1, Pydantic 2.12.5 on Windows.

## Implemented boundaries

| Module | Actual role |
| --- | --- |
| [review_contracts](../app/review_contracts.py) | Strict frozen versioned subjects, commands, decisions, histories and separate non-executing review envelopes; canonical bounded records and safe errors |
| [package_review_store](../app/core/package_review_store.py) | One-project SQLite custody/immutable tables, metadata/schema/header identity, transaction/replay validation, optimistic sequence and request-ID idempotency |
| [package_review_service](../app/core/package_review_service.py) | Public read-only M0 observations, unchanged M1/M2 structural policy and exact baseline/parent-decision review tokens |
| [review_cli](../app/review_cli.py) | Explicit offline init/register/review/inspect/history/assess/export; bounded ASCII JSON and exclusive inert export |
| [acceptance and regression tests](../tests/test_m2r_reviews.py) | 29 named automated acceptance families plus 12 focused regression methods; AC-30 is the manual verification/staging/checkpoint gate below |

Every explicit new plan approval has a new sequence. A package review references that
exact plan approval sequence and exact active M0 baseline approval sequence. Revocation
or reapproval never revives stale dependent reviews. Request replay returns the original
historical decision, not a fresh authorization. Reject/revoke work without M0 availability.
New M2-R effective-review booleans are distinct from unchanged M1/M2 literal-false flags;
closure stays unverified and execution_authorized stays false.

The new store owns canonical plan/package bytes; paths are not review subjects. Changed
digests inherit nothing, and registration/approval does not implicitly replace another
plan/package. There is no inferred current head or subset-selection workflow.

## Acceptance evidence

Rows refer to `test_m2r_ac_NN_*` in the linked test file unless a focused/manual check
is named. These are scoped offline evidence, not full product-effectiveness results.

| Family | Observed evidence |
| --- | --- |
| M2R-AC-01 | Explicit absent-store initialization/reopen and matching public M0 project; effect-free constructor/help/version guard |
| M2R-AC-02 | Existing/M0/foreign/same-file aliases denied; existing authority bytes retained |
| M2R-AC-03 | Canonical plan custody and source/criterion identity; inactive registration remains unreviewed |
| M2R-AC-04 | Package byte custody; missing/foreign/digest-mismatched parent denied |
| M2R-AC-05 | Equivalent imports idempotent and byte-preserving; no inferred review |
| M2R-AC-06 | Explicit trusted local context and operator attribution; forged context/import fields denied |
| M2R-AC-07 | Stale/inactive authority denied; focused foreign canonical project fixture denied |
| M2R-AC-08 | Parent review and complete unchanged M2 policy required; unbuilt/no-tests/unused-configuration remain blocked |
| M2R-AC-09 | Every approved decision transition and invalid transition exercised |
| M2R-AC-10 | Exact replay survives subsequent revocation; altered same-ID command denied |
| M2R-AC-11 | Stale competing requests, actual concurrent writers, bounded sequences, real lock contention and synthetic exhaustion frontier |
| M2R-AC-12 | Parent revocation blocks child effectively without mutating child history or bytes |
| M2R-AC-13 | Revocation/reapproval and repeated fresh plan approval leave old child tokens ineffective until explicit new package review |
| M2R-AC-14 | Distinct subject registration has no inherited review or implicit supersession; package revocation retains parent review |
| M2R-AC-15 | Unrelated M0 events do not invalidate the actual baseline approval token; baseline supersession blocks descendants |
| M2R-AC-16 | Fresh versioned envelope and unchanged nested false flags; contradictory/forged envelopes rejected |
| M2R-AC-17 | Real M0 revoke after observation/before M2-R commit demonstrates documented staleness, with execution still false |
| M2R-AC-18 | M0-free rejection/revocation/exact acknowledgment replay; new approval still requires M0 |
| M2R-AC-19 | Complete cursor pagination and bounds; 1,000 large Unicode notes reject oversized envelope, explicit smaller page succeeds |
| M2R-AC-20 | CLI/Python strict keys/versions/UUIDs/sequences/note/input limits and malformed JSON; large inert payload uses unchanged M2 parser |
| M2R-AC-21 | Independent canonical JSON comparison, validated copies, missing/changed schema and restored-schema SQL-column tampering denied |
| M2R-AC-22 | Transaction rollback and lost-commit acknowledgment seams; real process exits at decision insertion, pre-commit and post-commit reconcile to zero/one decision |
| M2R-AC-23 | Busy/disk-full rollback, wrong schema/version, read-only hot-journal denial, explicit own-store recovery, foreign M0 journal left untouched and unapproved WAL refusal |
| M2R-AC-24 | Exact exclusive export, overwrite/UNC/reserved/drive-relative denials; unchanged shared M0 Windows file-boundary regressions remain in full suite |
| M2R-AC-25 | Bounded JSON/static errors, escaped notes, failed post-commit stdout returns uncertainty; replay reconciles one stored decision |
| M2R-AC-26 | Guarded import/help/version and payload registration prevent runtime/config/network/process effects; payload remains inert |
| M2R-AC-27 | Separate CLI approval/revoke/assess/flags, plus focused complete init/register/inspect/history/export journey and exact-byte export |
| M2R-AC-28 | All preexisting source/tests/prompts/dependencies compared to b94d76d; complete existing regression command included |
| M2R-AC-29 | Real M0 authority and unchanged M1/M2 trace chain; fresh assessments leave both stores unchanged |
| M2R-AC-30 | Final source/doc/staged-inventory/secret checks and local checkpoint verification recorded below; not an automated unit-test claim |

## Failures found and corrected

The first focused run had four harness errors: a fixture tried to reapprove a previously
rejected identical M0 successor; a race probe recursively called its own patched inspect;
two SQLite test connections remained open on Windows because a transaction context
manager does not close the connection. These were corrected by creating a distinct
successor, using the original observation for the intentional mutation, and explicitly
closing connections. No assertion or expected policy was weakened. Then 29 tests passed
in 11.134 seconds.

Additional substantive failures were exercised before fixes:

- A real hot journal correctly blocked read queries but also blocked the explicit review
  CLI's context lookup. Explicit review/registration setup now permits recovery only on
  the new review store; inspection/history/assessment/export remain read-only.
- A wrong review-store path could let SQLite recover a foreign hot journal before an
  application-ID query rejected the database. The controlled fixture reproduced deletion
  of the synthetic M0 journal. Store headers are now checked before any SQLite connection;
  the same fixture verifies all M0/journal bytes remain unchanged.
- SQL CHECK expressions permit NULL-valued expressions; independent row validation now
  checks parent-kind/digest columns as well as immutable schema/canonical content.
- Ctrl+C just after commit initially followed the generic exception/exit path. A local
  nonserialized interruption marker now preserves both COMMIT_OUTCOME_UNKNOWN and
  exit 130; replay proves exactly one stored decision. Before-commit interruption rolls back.
- WAL mode is outside this fixed rollback-journal policy and is rejected from its header
  without adopting the mode or creating/using shared-memory sidecars.

The header layout was checked against the official
[SQLite database format](https://www.sqlite.org/fileformat2.html#the_database_header):
application ID and user-version fields plus read/write journal format versions. This was
focused implementation verification, not a new architecture research cycle. Header identity
is an ownership guard, not authentication against a hostile same-user file replacement.

## Security, fitness and residual limits

FIT-01/02/06/07/08/11/13 have scoped contract/trace, negative/concurrency/crash, real-store,
safe-output and documentation evidence above. FIT-03 independent review remains open:
author self-review and user contract agreement are not independent code review.
Clean installation, lint/type/CI, provider/model/agent quality, genuine defect detection,
portability, professional UI and full operations remain unverified under their owners.

M0 and M2-R reads are separate observations. A baseline can change before a new review
commits or immediately after assessment; no dispatch interface exists here. M4 must
define real admission/linearization/reservations, and M5 must establish actual closure,
safe collection/execution and worker evidence. No readiness result closes F01-F17.

Same-user/admin tampering, file replacement races, copied/rolled-back authority files,
hardware power loss, backups/restore, retention and multi-user access are not solved.
Stored plan/package bytes and free-text notes can contain sensitive user content;
keep all real stores/exports out of Git. Existing SQLite/database exclusions cover the
new store, and tests use temporary synthetic data. Full-history/subject validation is
conservative and may be expensive for large stores; no scale/performance claim is made.

## Local usage and checkpoint

Use `python -B -m app.review_cli help` for exact flags. Explicitly initialize a separate
review `.sqlite3` from an existing M0 project/baseline, register frozen plan and package,
inspect their bytes using exclusive export, then issue separate plan/package reviews
with expected M0/review sequences and stable request IDs. `assess` recomputes effective
review; `history` is paginated. A successful review acknowledgment is not execution
permission. After uncertain commit/output, inspect history or replay the exact request.

The earlier progress checkpoints are `569d839` (C20-C22 documentation) and `2cd0537`
(approved M2-R specification). The implementation checkpoint subject is
`feat: implement offline M2-R durable plan and package reviews`, parent `2cd0537`.
Its exact hash is verified after creation, rather than embedded in its own contents.
Stop after the local implementation checkpoint; no push or subsequent milestone is authorized.

Final source/document verification: 31 Markdown files, 664 local links and 279
source/heading/compatibility anchors resolved, with balanced fences. All 38 approved
M2-R decision/acceptance rows and all existing CAP acceptance blocks are unchanged.
All 55 Python files (including maintained tests) parsed with ast.parse; this is syntax
inspection, not lint/type/CI validation. All 66 preexisting non-documentation files
match the approved specification checkpoint byte-for-byte; no existing source/tests,
prompts, dependency manifests or runtime files were edited.

The implementation inventory is four new application modules, one new synthetic test
module and ten M2-R-related documentation paths. The exact 15-path staged inventory matched the reviewed allowlist; staged blobs matched
the tested/reviewed worktree bytes. Bounded credential/token/private-key scans found
no matches, and git diff --cached --check passed. The final Git hash, clean index/
worktree and unchanged prior history are checked after creating the local checkpoint.
No runtime databases, exports, actual inputs, browser sessions or generated artifacts
belong in this commit. The record does not claim independent code review or push.
