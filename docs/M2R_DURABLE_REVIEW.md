# M2-R - Durable Plan and Whole-Package Review

Revision **M2R-SPEC-2026-10-25-v1**. Status: **APPROVED AND IMPLEMENTED OFFLINE;
157 TESTS VERIFIED**. Under C23 the user approved this exact v1, M2R-D01..08 and
M2R-AC-01..30, including offline tests and reviewed local commits. The
[engineering agreement prerequisite](../AGENTS.md#independent-engineering-judgment)
is satisfied. No provider/target/generated execution or push is authorized. See
[M2-R verification](M2R_VERIFICATION.md) for actual results, fixes and limitations.

## Scope and preserved contracts

Provide offline custody, explicit local decisions, append-only history and fresh effective
review of exact M1 plans and complete M2 packages. Initially approve only structurally
ready plans and fully mapped packages. Preserve all M0/M1/M2 schemas, APIs, canonical
bytes, source, tests, prompts and runtime. Their assessments retain literal-false
plan/bundle/execution fields. New review envelopes may report effective human review;
they never report executable closure or execution permission.

Consume public [M0 inspection](../app/core/review_store.py),
[M1 validation/assessment](../app/core/plan_policy.py),
[M2 validation/assessment](../app/core/artifact_policy.py) and their existing parsers/
canonicalizers. Do not import runtime configuration, providers, agents or generated code.
No new dependency, existing-store migration, source-aware adapter, subset/manual-case
system, auth service, coverage engine, framework profile, UI, model router, telemetry
platform, dispatch, result parser, worker or generated execution enters M2-R.

## Decisions and alternatives

| ID | Proposed decision | Simpler alternative / trade-off / falsification |
| --- | --- | --- |
| M2R-D01 | Separate offline service/CLI and SQLite review store; one project per store | Extending M0 tables is smaller in file count but breaks its exact schema identity; JSON decisions lack tested concurrent/crash transaction semantics. One-project files avoid a second project registry; revisit for demonstrated multi-user/scale needs |
| M2R-D02 | Store canonical exact plan/package exports as immutable subjects; package requires its stored parent plan | Paths alone are simpler but can change/disappear after review. Stored bytes preserve inspectable custody. Reuse M2 bounded bytes, do not unpack or execute; reconsider only for real size/performance evidence |
| M2R-D03 | Single local human operator with reviewer attribution bound to the canonical M0 project record | Filesystem access is the trust boundary, not authentication. A hosted/multi-user reviewer requires a separately approved identity/authorization design |
| M2R-D04 | Separate plan and whole-package decisions; every new explicit approval creates a fresh approval sequence | Permanent terminal rejection/revocation matches M0 but forces artificial content edits to rereview identical bytes. Permit explicit reapproval; dependent package approval must reference the exact parent approval sequence |
| M2R-D05 | Global per-store decision sequence, request-ID idempotency and append-only decisions with replay validation | Mutable booleans are shorter but lose attribution/history and stale-request protection. No full event-sourcing platform or graph-checkpoint changes |
| M2R-D06 | Fresh effective-review envelope, with explicit M0 observation and review-store sequence; no cross-store atomicity claim | Persisted ready flags become stale. SQLite transactions across independent stores are not a dispatch boundary; M4 owns authority/dispatch linearization |
| M2R-D07 | Exact-subject review, no implicit current-plan/package head or inferred supersession | Selecting the newest registration is simpler but silently changes scope. Changed subjects receive new reviews; explicit revocation retires an older subject. Baseline supersession still blocks descendants |
| M2R-D08 | Versioned bounded contracts, safe JSON-only CLI and no new runtime effects | Reuse public file primitives with translated safe errors; do not reuse private M0 SQL/session methods. Retain known local-filesystem/power-loss/hostile-same-user limits |

All eight decisions are approved for this exact milestone. No full ADR changes status.

## Identity, custody and local trust

Store metadata contains `schema_version=1`, a new canonical UUID `store_id`, the exact
M0 `ProjectRecordV1`, creation timestamp and store policy version `m2r-review-v1`.
One store serves that project. Every M0 observation used for registration or approval
must have the identical canonical project record, including reviewer label/creation
identity. A chosen M0 path is an explicit local input, not an authenticated authority
endpoint. Copied/rolled-back files and hostile same-user/admin access remain outside
the single-operator integrity model; no anti-rollback or global authority claim.

Subjects are keyed by `(project_id, kind, subject_digest)`, `kind=plan|package`.
For plans `subject_digest=plan.digest`; for packages it is `package.digest` (M2's
manifest digest, whose file entries bind the exact payload bytes). Do not rehash raw
JSON whitespace or confuse a plan digest with a package digest. Each record stores
`baseline_digest`, `plan_digest`, canonical export bytes and registration timestamp.
For plan records `plan_digest=subject_digest`; package parent is the exact stored plan.

Registration parses frozen exports only, verifies their existing digest/canonical and
cross-reference rules, and validates them against a public M0 inspection. It may store
structurally valid proposals with inactive baseline or blocked readiness; it grants no
review. A package may register while its parent plan is unapproved. Candidate/draft input,
foreign project/baseline/parent, missing plan, altered digest or inconsistent payload fails.
Same kind/digest and identical canonical export is idempotent; any content conflict is
integrity failure. Registration does not increment the decision sequence or change reviews.

Review code uses a local-context value obtained from the initialized review store's
metadata by the explicit operator CLI path. Compare project/store/reviewer identity at
the write boundary. Serialized labels, imported JSON approval flags, model output,
review notes and ready assessments cannot construct trusted authority. Python code
executing as the trusted operator is not an independent hostile principal. No network,
web feedback, timeout approval or externally imported decision endpoint is provided.

## V1 commands and decision contracts

All records are strict/frozen, reject unknown fields/versions and revalidate on copy/load.
Reuse canonical UUID/digest/timestamp/sequence types and limits; booleans must not pass
as integers. New records use deterministic UTF-8 JSON, sorted keys, compact separators,
finite numbers and explicitly ordered history. Do not alter existing canonicalizers.

| Record | Required fields and invariant |
| --- | --- |
| `ReviewSubjectV1` | schema_version, project_id, kind, subject_digest, baseline_digest, plan_digest; exact subject/parent bindings above |
| `StoredReviewSubjectV1` | schema_version, subject ReviewSubjectV1, registered_at Timestamp, canonical_content bytes in the Python/store boundary; JSON inspection omits bytes and export returns the unchanged frozen content |
| `ReviewCommandV1` (M2-R module namespace) | schema_version, project_id, kind, subject_digest, request_id UUID, expected_sequence, expected_m0_sequence, decision approve/reject/revoke, note; expected_m0_sequence required integer for approve and null otherwise; note null or nonblank bounded text |
| `ReviewDecisionV1` (M2-R namespace) | All command fields plus store_id, sequence, recorded_at, reviewer_label, previous_decision_sequence, baseline_approval_sequence and parent_plan_approval_sequence; sequence=expected_sequence+1; dependency tokens required only for approve, parent token only for package approve |
| `RegistrationV1` | schema_version, exact subject, created boolean; no approval flag |
| `HistoryPageV1` | schema_version, store_id, project_id, observed_sequence, ordered decisions, next_after_sequence or null |

`previous_decision_sequence` is the previous decision for this same subject or null.
All per-store sequences start at zero and cap at existing `MAX_SEQUENCE`; decision
sequence starts at one. Global request IDs are unique within this store. Notes are
at most 2,048 characters; all command/decision/metadata records are at most 64 KiB.
History limits are default 100, maximum 1,000, with strictly increasing cursor semantics;
each returned JSON envelope must also fit 8 MiB. Reject an overlarge requested result
with a bounded error and let the caller request a smaller page; never silently omit rows.

### Decisions, prerequisites and reapproval

Unreviewed subjects have raw state `pending`; the most recent decision gives
`approved`, `rejected` or `revoked`. New commands follow this table:

| Decision | Allowed raw states | Guard / result |
| --- | --- | --- |
| approve | pending, approved, rejected, revoked | Fresh M0 baseline active and structurally ready subject; package also requires effective exact parent approval. Record a new approval token even when the bytes were approved before |
| reject | pending, rejected, revoked | Existing exact subject and fresh expected review sequence; record rejection without M0 availability requirement |
| revoke | approved (including currently ineffective approval) | Existing raw approval and fresh expected review sequence; record revocation without M0 availability requirement |

Reviewing a plan requires `assess_plan(...).disposition=ready_for_artifact_design`.
Package approval requires the unchanged M2 assessment `ready_for_review_design`:
no unbuilt scenarios, no unused configuration and at least one test; unsupported M0
criteria stay visible under unchanged M1 rules. Review attests the selected design/code
against the approved oracle; it neither changes the business expectation nor proves
assertion semantics, dependency closure, toolchain compatibility or defect sensitivity.

An approval records the exact active M0 baseline's decision sequence. Package approval
also records the currently effective parent plan approval sequence, inside the same
M2-R write transaction. Every new plan approval invalidates existing dependent package
approval tokens, even for unchanged plan bytes; a human must explicitly approve that
package again. Reapproval never happens on import, refresh, retry or timeout.

Examples: plan approval 3 + package approval 4 (parent token 3) are effective. Revoke
plan at 5: package 4 is ineffective. Reapprove plan at 6: package 4 stays ineffective.
Explicit package approval at 7 binds token 6. Replaying request 4 returns historical
decision 4 and cannot reactivate it. A separately registered plan/package digest starts
pending; it inherits no review. Merely registering or approving another plan/package
does not revoke an older exact subject; choosing a changed digest requires that digest's
reviews. There is no implicit plan lineage/head in M1 to infer supersession from.

## Transactions, idempotency and integrity

Initialize an absent, distinct `.sqlite3` path explicitly. Never overwrite/adopt an
existing database or add tables to M0. Reject resolved-equal paths and existing same-file
aliases between stores. Use existing local fixed-drive/no-link/reparse path policy;
document its same-user/TOCTOU limits. Constructors/import/help/version create nothing.

The new schema contains immutable singleton metadata, immutable subject rows and an
append-only decision ledger. Use foreign keys for subject/parent references and
UPDATE/DELETE denial triggers. Store `user_version=1` plus an M2-R-specific application
identifier `0x41545352` (ATSR); require the exact expected schema before operating, rather than adopting
any SQLite database. Use journal DELETE, synchronous FULL, foreign keys ON, bounded
busy timeout and explicit `BEGIN IMMEDIATE` for writes, coherent read transactions
for queries. Enforce key columns against decoded canonical record fields and replay
the decision sequence, transitions and token references before trusting existing rows.
Check stored BLOB length before materializing/decoding it. Corruption must fail closed.

Logical SQL inventory: `store_metadata` has one singleton key and canonical metadata
BLOB; `subjects` has kind/digest primary key, baseline/plan digest columns, nullable
parent_kind/parent_digest, canonical_content BLOB and registration timestamp. Plans
have null parent columns; packages require parent_kind=plan and parent_digest=plan_digest,
with a composite self foreign key. `decisions` has global sequence primary key, unique
request_id, kind/subject_digest foreign key and canonical decision BLOB. All three tables
deny UPDATE/DELETE. Replay derives the current head/status without a mutable state table.
Keys/digests/timestamps/dependency tokens decoded from BLOBs must agree with SQL columns
and stored subjects. Exact SQL declarations, constraints and denial triggers become a
fixed schema constant with tests; do not accept extra tables/triggers/changed constraints.

Review transaction order:

1. Validate the bounded command and local context; read/validate store metadata/history.
2. Check request ID before fresh sequence/approval guards. Exact same canonical command
   returns the original immutable decision, even after revocation or changed M0 state;
   this is acknowledgment replay, not an effective-review result. A changed command
   with the same request ID fails `REQUEST_ID_CONFLICT`, without new writes.
3. Require expected review sequence to match the transactional ledger head; reject
   sequence exhaustion. Validate the exact subject and permitted raw transition.
4. For a new approval, perform one public read-only M0 `inspect` during the M2-R write
   transaction. Validate the bound project, baseline and expected M0 project sequence;
   run existing structural assessments and verify parent approval from that transaction.
   Reject/revoke use stored subjects and need no M0 read, permitting offline revocation.
5. Append one canonical decision, then commit once. No separate cache/state mutation is
   authoritative. M0 receives no writes, recovery, migrations or private-SQL access.

Fault before commit rolls back the decision. Lost acknowledgment after/during commit
returns `COMMIT_OUTCOME_UNKNOWN`; do not claim rollback or retry under a fresh request
ID. Inspect history or repeat the exact original request to reconcile. Registration is
reconciled by exact subject/digest; initialization interrupted before schema commit may
leave an unusable file, which must not be overwritten or silently deleted.

Read-only inspection/history/assessment/export must not repair a hot journal; surface
`RECOVERY_REQUIRED`. Explicit registration/review writes may recover only this M2-R
store, then validate it before changes. M0 hot-journal/corruption errors remain upstream
failures; the operator uses existing M0 procedures separately. Disk-full, lock contention,
corruption, interrupted output and failed publication remain distinguishable failures.
FULL journaling and crash tests do not prove hardware power-loss durability or backups.

## Fresh effective review and race limits

New `PlanReviewAssessmentV1` and `PackageReviewAssessmentV1` expose exact subjects,
store_id, review_sequence, raw status/latest decision sequence, M0 effective observation
(including project_sequence and baseline approval sequence), current dependency tokens,
unchanged nested structural assessments, deterministic blockers and boolean
`plan_review_effective` (plus `package_review_effective` for a package).
Disposition is `reviewed_for_package_review` for an effective plan or
`reviewed_for_later_validation` for an effective package, otherwise `blocked`.
Both records have `policy_version=m2r-review-v1`, `closure_status=unverified` and strict
literal `execution_authorized=false`. Unknown/contradictory observations are errors,
not a successful blocked/ready response. Do not deserialize arbitrary assessment input
and treat it as authority; service calls construct these from actual store reads.

Assessment loads one coherent M2-R subject/decision snapshot and performs one fresh public
M0 inspection, validates canonical project/subject linkage and recomputes unchanged
M1/M2 structural policy. Plan review is effective only when its latest decision is approve,
its stored baseline approval token equals the currently active baseline's approval
sequence, and structural readiness holds. Package review additionally needs its latest
approve decision, matching baseline token and matching currently effective parent plan
approval sequence. Missing/rejected/revoked parents, inactive/superseded baseline,
changed selected subject or stale dependency tokens cannot be effective.

Blocker codes are `BASELINE_NOT_ACTIVE`, `PLAN_STRUCTURALLY_BLOCKED`,
`PACKAGE_STRUCTURALLY_BLOCKED`, `PLAN_NOT_APPROVED`, `PACKAGE_NOT_APPROVED`,
`BASELINE_APPROVAL_CHANGED`, `PARENT_PLAN_APPROVAL_CHANGED`. Return sorted unique codes;
the existing nested assessments preserve their detailed scope/issue accounting.

The two SQLite stores have **no joint atomic snapshot or dispatch transaction**. M0
may change after the approval observation but before M2-R commit, or after assessment;
a decision records review against the observed authority, not current dispatch authority.
An assessment reports its two observed versions and may immediately be stale. A second
read/retry loop cannot eliminate that race. Mandatory future M4 revalidation/linearization
and M5 worker controls remain; M2-R contains no execution interface to exploit the gap.
Tests must demonstrate revocation after observation rather than claim atomic protection.

## Public interfaces and safe CLI

Proposed modules: `app/review_contracts.py`, `app/core/package_review_store.py`,
`app/core/package_review_service.py`, `app/review_cli.py`; focused tests under `tests/`.
Do not introduce a universal review framework, ORM or dependency injection library.
Use descriptive M2-R namespaces to avoid importing the homonymous M0 command types.

The store constructor is I/O-free. Public service operations are initialize,
register_plan, register_package, record_review, inspect_subject, inspect_history,
assess_plan_review, assess_package_review and export_subject. Registration/approval/
assessment receive an explicit public M0 store reference; other queries use only the
initialized review store. Local context is a separate trusted value, not a serialized
contract field. Existing M0/M1/M2 private store methods are not extension interfaces.

`python -B -m app.review_cli` is separate from the legacy CLI. All options reject
abbreviation and unknown arguments; no `--force`, `--auto`, `--execute`, `--actor`,
imported-approval or model-generated-command option exists.

| Command | Exact required inputs / output |
| --- | --- |
| help / version | No store access; version reports schema/policy version |
| init | --db, --baseline-db, --project, --baseline; one read-only M0 inspection binds project metadata; output store/project identity |
| register-plan | --db, --baseline-db, --plan; bounded frozen export; output RegistrationV1 |
| register-package | --db, --baseline-db, --package; parent plan already in this store; output RegistrationV1 |
| review | --db, --kind, --digest, --decision, --request-id, --expected-sequence; --expected-m0-sequence required only for approve; optional --note; project/reviewer from store context; output immutable decision only |
| review approve extra | --baseline-db mandatory; reject/revoke reject this and expected-M0 options to keep the no-M0-read boundary explicit |
| inspect | --db, --kind, --digest; safe subject/registration summary and raw latest decision, no effective-ready claim or automatic payload display |
| history | --db; optional --after (default 0), --limit (default 100); bounded ordered page |
| assess | --db, --baseline-db, --kind, --digest; fresh new review envelope |
| export | --db, --kind, --digest, --out; exclusive unchanged canonical frozen export, no unpacking |

No file argument is a default runtime path; all stores/exports are explicit. Reuse
`read_bounded`, `validate_path` and exclusive `write_export` for permitted local files.
Read plans/packages at their existing 8 MiB input cap; package payload strings pass only
the unchanged M2 parser, not M0's generic small-string decoder. Metadata/commands use
64 KiB JSON bounds; reject duplicate keys, nonfinite numbers, invalid UTF-8/surrogates,
deep/oversized trees and unknown versions/fields. Expected sequence CLI values must
be canonical nonnegative decimal strings within MAX_SEQUENCE (no sign/whitespace).

JSON output is ASCII-escaped, bounded and includes no raw exception/input/config values;
notes are untrusted JSON strings. Export copies inert data and never renders HTML,
opens a browser, runs a shell, compiles, installs or imports payloads. Failure output
contains only static `source`, `code`, empty `pointer`, safe static `message`.
Sources m0/m1/m2 retain their error codes; m2r adds `STORE_IDENTITY_MISMATCH`,
`SUBJECT_CONFLICT`, `PARENT_NOT_REVIEWED`, `STALE_AUTHORITY`, `LOCAL_CONTEXT_REQUIRED`
to existing bounded input/path/store/integrity/sequence/transition/request/output codes.
Exit 0: successful operation, including an acknowledged rejection/revocation;
2: invalid input/command or policy/sequence/transition conflict;
3: well-formed assess result blocked; 4: store/integrity/authority/I/O/commit uncertainty;
130: interruption. A failed post-commit stdout write is `COMMIT_OUTCOME_UNKNOWN`, not
an assertion the decision was absent. Idempotent replay is its recovery path.
In particular `STALE_SEQUENCE`, `STALE_AUTHORITY`, `REQUEST_ID_CONFLICT`,
`NOT_APPROVABLE`, `PARENT_NOT_REVIEWED`, `INVALID_TRANSITION`, `SEQUENCE_EXHAUSTED`
and `LOCAL_CONTEXT_REQUIRED` are exit 2. Wrong/contradictory project/store/subject
authority and upstream store failures are exit 4. Unknown subject is exit 2; corrupted
stored references are integrity failure/exit 4. Read-only output failure is exit 4.

## Offline acceptance matrix

Every family requires observable positive and failure behavior, no skipped assertions.
Use synthetic temp stores and inert payloads; trusted crash-test child processes are
permitted only for store/CLI fixtures, never generated code or target/provider calls.

| ID | Required evidence |
| --- | --- |
| M2R-AC-01 | New absent store initializes with bound canonical M0 project; reopen validates schema/application identity; constructor/help/version perform no effects |
| M2R-AC-02 | Existing/foreign/M0 database and aliased/same-file paths are refused without overwriting or adding tables; M0 remains byte-for-byte unchanged |
| M2R-AC-03 | Plan registration preserves exact frozen digest/canonical bytes and all source/criterion links; inactive/blocked proposal remains visibly unapproved |
| M2R-AC-04 | Package registration preserves exact bytes and stored parent; missing/foreign/mismatched plan/baseline/criterion/payload fails |
| M2R-AC-05 | Canonical-equivalent registration is idempotent, conflicting same-key bytes fail; registration changes neither decisions nor effective reviews |
| M2R-AC-06 | Ready plan explicit approval records operator/store identity and observed M0 token; imported flags/labels/forged context cannot grant approval |
| M2R-AC-07 | Inactive/rejected/revoked/superseded baseline, wrong canonical project or stale expected M0 sequence denies plan/package approval |
| M2R-AC-08 | Package approve requires ready complete M2 mapping and effective exact parent approval; unbuilt/unused-config/no-tests cases remain blocked |
| M2R-AC-09 | Every permitted/forbidden decision transition in the table is covered; no approval on timeout/default/import |
| M2R-AC-10 | Same request/canonical command returns exact original decision before stale-state guards; altered reuse fails; replay after revocation never reactivates review |
| M2R-AC-11 | Stale/overflow/malformed sequences and two competing writers produce one valid outcome, no duplicated or lost decisions |
| M2R-AC-12 | Plan revoke invalidates dependent package effectively without mutating its history or stored bytes |
| M2R-AC-13 | Plan reapproval creates new token; old package stays ineffective until explicit package approval; even repeated new plan approval cannot silently revive descendants |
| M2R-AC-14 | Package rejection/revocation blocks only that exact subject; separate plan/package digests inherit nothing and do not implicitly supersede other exact subjects |
| M2R-AC-15 | Baseline changes invalidate effective reviews; unrelated M0 decision-sequence changes do not invalidate approval when the actual baseline approval token is unchanged |
| M2R-AC-16 | Fresh assessment exposes coherent local sequence plus fresh M0 observation and existing nested false fields; copied/forged assessment is not service authority |
| M2R-AC-17 | Cross-store revoke-after-read/before-commit and revoke-after-assessment tests expose documented staleness and never emit execution authorization |
| M2R-AC-18 | Reject/revoke and exact acknowledgment replay work with M0 unavailable; new approvals/assessments cannot fabricate an upstream observation |
| M2R-AC-19 | History pagination preserves complete ordered cursor/sequence identity; bounded overflow errors require smaller pages, not hidden truncation |
| M2R-AC-20 | Unknown fields/versions, bool-as-int, invalid UUID/digest/UTF-8, duplicate keys/nonfinite/deep/oversized values fail in CLI and direct Python boundaries |
| M2R-AC-21 | Canonical independent vectors, copy/revalidation and SQL-row/blob identity checks reject changed metadata/subject/dependency/sequence or noncanonical stored records |
| M2R-AC-22 | Crash before/after decision insertion but before commit yields no partial decision; commit/lost-ack crash yields one recoverable outcome under exact request replay |
| M2R-AC-23 | Busy/locked/disk-full/corrupt/schema/journal failures are bounded and distinguished; read operations leave hot journals untouched; explicit M2-R writes cannot recover/write M0 |
| M2R-AC-24 | Windows path/export/reparse/UNC/reserved/overwrite denials and interrupted/failed exclusive publication preserve originals; no routine artifact cleanup |
| M2R-AC-25 | Safe JSON/notes/malicious code payloads and failed stdout/stderr expose no raw sensitive sentinel; post-commit output failure is reconciled as uncertain |
| M2R-AC-26 | Guarded imports/socket/process/write hooks verify effects limited to explicit stores/exports; no config/provider/runtime/generated-code loading or execution |
| M2R-AC-27 | Full separate CLI journey: init/register/inspect/export/plan approve/package approve/assess/revoke/history/replay; exact flags/exits and unsupported-effect flags tested |
| M2R-AC-28 | Complete existing 116-test M0/M1/M2 suite passes unchanged with new families; protected source/interface/canonical inventories stay identical |
| M2R-AC-29 | Real M0 store integration and unchanged M1/M2 consumption cover full trace chain and revocation; no claim this demonstrates actual test effectiveness |
| M2R-AC-30 | Verification record reports actual commands/counts/failures/limitations, safe staged inventory/secret scan and verified local checkpoint; no push or broader milestone |

## Traceability, fitness and deliberate deferrals

CAP-HITL.A1 is supported only for the local plan/package review boundary; UI and human
usability evidence remain deferred. CAP-EXEC supplies review-before-effects invariants,
but dispatch/closure/isolation acceptance remains M4/M5. CAP-RECOVERY applies to local
review idempotency/crash behavior here; charged/target effects remain M4/M5. CAP-WORKFLOW
and CAP-DATA retain exact-project lineage and local trust/privacy limits. MANUAL, AUTHENV,
COVERAGE, FRAMEWORK/POM/EXT, MODEL, DIAG, OBS/EVAL/LAB, PORT and SC-01 remain intact in
the [single CAP register](CAPABILITY_REQUIREMENTS.md); this milestone implements none
of their deferred integrations. Relevant full ADRs 03/06 remain PROPOSED beyond scope.

| FIT gate | M2-R evidence plan / owner / missing proof |
| --- | --- |
| FIT-01/02 | M2-R owner: AC-01..21, 28/29 trace/contract/golden inventory; no V1 migration |
| FIT-03 | Independent review of contracts and then implementation required before claiming independent review; this author's self-review is not that evidence |
| FIT-06/07 | M2-R owner: AC-02,06..18,20..26 local review threat/failure matrix; hostile operator/remote auth/dispatch races not solved |
| FIT-08 | M2-R owner: AC-27..29 actual M0/local CLI integration; M3/M4/M5 runtime integration remains unproven |
| FIT-11/13 | M2-R owner: AC-19,22..25,30 crash/history/output/doc evidence; no operations/backup/power-loss claim |
| Other gates | Existing clean-install/lint/CI, model/agent quality, true defect detection, portability and UX proof remain open with their current owners |

## Contract agreement and implementation sequence

The user explicitly agreed this exact revision, M2R-D01..08 and M2R-AC-01..30 before application code changes.
The consequential choices are one project per separate SQLite store, immutable subject
custody, explicit repeatable approvals with parent-decision tokens, exact-subject rather
than implicit-head supersession, and observable cross-store staleness with execution denial.
The user's explicit approval authorizes offline implementation/tests and reviewed local
commits for these contracts, with no permission to push or execute generated code.

After agreement: implement strict contracts/pure rules, then new store, small service and
separate CLI; exercise each acceptance family and existing offline regressions, fix real
failures without changing expectations, update actual verification/status documents,
review staged inventory/secrets, create a local implementation checkpoint and verify Git
state. Stop at verified M2-R completion. No M3/M4/M5, providers, targets, generated code,
dependencies, agents, publication, push or deployment is included.
