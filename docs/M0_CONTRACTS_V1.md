# M0 V1 contracts and command semantics

Status: **APPROVED FOR M0 - implemented and verified offline**. Specification revision:
`M0-SPEC-2026-10-23-v2`. These are the normative contracts for the approved
[M0 scope](M0_VERSIONED_BASELINES.md). See [verification](M0_VERIFICATION.md).
[Decision rationale](M0_DECISION_RATIONALE.md) explains alternatives and limitations.
The existing six ADRs remain PROPOSED.

## 1. Scope, authority and runtime boundary

One local operator manages one or more explicitly identified projects in one local
SQLite database. Each project records one immutable `reviewer_label` at creation.
Review commands obtain that label from the project record, never from imported JSON
or a review `--actor` flag. The operator explicitly supplies project, snapshot digest,
decision, reason, expected sequence and request ID. No implicit approval, timeout
approval, batch auto-approval or execution permission exists.

This is attribution under a trusted-user assumption, not authentication. Another
process running as that OS user can invoke the same CLI or edit the database. A hash
does not establish authorship; a locally stored reviewer label is not a signature.
M0 exposes no model/provider/tool integration, but cannot technically prevent an
external agent with that user's shell access from issuing commands. Use a private,
operator-controlled directory. Hostile same-user processes, administrators, malicious
filesystem races and cryptographic attestation are outside M0's boundary. Multiple
reviewers or untrusted command callers require a new authenticated boundary first.

Keep `RequirementBundle`, existing CLI, runtime graph, writer, repair and runner
unchanged. New modules may import the standard library and existing Pydantic, but
not `app.config`, `main`, extraction/provider/browser/memory modules. `app/__init__.py`
and `app/core/__init__.py` are currently empty. Import and `--help` have no filesystem,
database, logging-file, environment-file or network effects.

## 2. V1 type rules and identity

All wire objects below reject unknown fields and require every listed field; nullable
fields use explicit JSON `null`, collections use explicit arrays. No type coercion:
booleans are not integers, strings are not parsed as numbers, and integers are not
converted into strings. The JSON boundary may deliberately construct tuples from
validated arrays. All domain objects and their nested values are immutable through
supported APIs: frozen models, tuples and scalar values; no mutable dictionaries,
lists, arbitrary `Any`, resource/auth objects, or trusted `model_construct` shortcuts
on external input. Copies/updates must be fully revalidated.

| Type | Exact rule |
| --- | --- |
| `Version` | Integer `1`, excluding boolean |
| `UUID` | Canonical lowercase, hyphenated UUID text; generated project/new entity/request IDs use UUIDv4; deterministic import entities use UUIDv5 |
| `Digest` | `sha256:` followed by exactly 64 lowercase hex digits |
| `Sequence` | Integer from 0 through 9007199254740991; persisted decision sequences start at 1; fail on exhaustion |
| `ShortText` | Nonblank Unicode string, at most 512 code points |
| `Text` | Unicode string, at most 16384 code points; may be empty only where explicitly allowed |
| `Reference` | Nonblank string, at most 1024 code points; inert text, never fetched or evaluated |
| `Pointer` | JSON Pointer string, at most 1024 code points; empty string denotes the root; escape path tokens with `~0` / `~1`; diagnostics use only known-field/index paths |
| `Timestamp` | UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`, generated at command execution; sequence, not clock time, orders reviews |

Strings reject unpaired surrogates, NUL and C0 control characters other than tab,
LF and CR. Preserve meaningful whitespace, Unicode normalization form, case,
negation and thresholds. Validation may check `strip()` for blankness but must not
store a stripped or otherwise normalized replacement. No floating-point fields exist
in V1 contracts. Fields described as nonblank use that rule in addition to their limit.

Entity identity is `(project_id, requirement_id)` or `(project_id, criterion_id)`;
a revision is identified by `(snapshot_digest, entity_id)`. There are no independent
item revision counters to synchronize. A baseline's identity is its snapshot digest;
do not add a second random baseline ID.

New author-created entities use UUIDv4, minted once and retained on edits. Legacy
import requires an operator-supplied `source_key` matching `[a-z0-9][a-z0-9._-]{0,63}`.
It identifies a source family within a project, not a file path or content hash.
Require the same key for later versions of the same source and a different key for
unrelated sources reusing IDs such as `REQ-001`.

Imported requirement IDs use UUIDv5 with namespace `UUID(project_id)` and name equal
to canonical UTF-8 JSON text of `['legacy-requirement', source_key, original_req_id]`.
The initial candidate criterion uses namespace `UUID(requirement_id)` and literal name
`legacy-criterion-1`. Evidence IDs use namespace `UUID(project_id)` and canonical JSON
name `['legacy-evidence', source_key, input_digest, json_pointer]`. The serialization
rules in section 4 apply to these arrays without reordering their elements.
Original legacy IDs and requirement text remain recorded exactly; semantic similarity,
array position and content hashes never determine requirement identity.

IDs are unique within each entity kind in a snapshot. Duplicate legacy IDs fail the
whole import, even when content matches. References must resolve in the same project
and snapshot. Editing an expectation retains the criterion ID only for the same
business subject; M0 cannot infer semantic identity. A criterion cannot be reassigned
to another requirement in a successor. M0 disallows removing parent requirements,
criteria or evidence: retain their IDs and original provenance. Explicit withdrawal,
merge/split retirement and scope-removal workflows require a later specification.
This conservative restriction must not be bypassed by silently dropping unsupported
items; a deliberately different project is a distinct review context, not a migration.

## 3. Exact object fields

Fields separated by commas have the stated type individually. Arrays below are tuples
in domain objects. Schema version belongs to each top-level persisted/wire envelope;
nested objects inherit it. The same limits apply to drafts and snapshots.

| Object | Required fields and constraints |
| --- | --- |
| `ProjectRecordV1` | `schema_version: Version`, `project_id: UUID`, `reviewer_label: ShortText` (max 128), `created_at: Timestamp`; immutable after explicit project creation |
| `SourceEvidenceV1` | `evidence_id: UUID`, `kind: legacy_import / document / human_decision`, `reference: Reference`, `content_digest: Digest or null`, `excerpt: Text`; nonblank excerpt; document/legacy kinds require digest; human_decision requires null digest and an explicit decision reference |
| `LegacyClaimV1` | `source_key: source-key token`, `original_req_id: ShortText` (max 256), `original_title: Text`, `original_description: Text` (both may be empty), `approved: boolean or null`, `rejected: boolean or null`, `gap_analysis: boolean or null`, `section_ref: Text or null`, `source_chunk: integer 0..9007199254740991 or null`, `human_prompt: Text or null` (these two text hints may be empty), `claimed_pdf_sha256: 64 hexadecimal characters or null` (preserve case), `input_digest: Digest`, `json_pointer: Pointer`; flags and provenance hints are historical claims only |
| `RequirementRevisionV1` | `requirement_id: UUID`, `title: Text` (max 512, may be empty in a draft/pending snapshot), `description: Text` (may be empty there), `source_ids: array[UUID]`, `dependency_ids: array[UUID]`, `legacy: LegacyClaimV1 or null` |
| `CriterionRevisionV1` | `criterion_id: UUID`, `requirement_id: UUID`, `preconditions: array[Text]`, `action: Text or null`, `expected_outcome: Text or null`, `origin: legacy_extracted / inferred / human_authored`, `clarity: unresolved / specified`, `unresolved_reason: Text or null`, `automation_support: unknown / supported / unsupported`, `support_reason: Text or null`, `source_ids: array[UUID]` |
| `BaselineDraftV1` | `schema_version: Version`, `project_id: UUID`, `parent_digest: Digest or null`, `requirements: array[RequirementRevisionV1]`, `criteria: array[CriterionRevisionV1]`, `sources: array[SourceEvidenceV1]` |
| `BaselineSnapshotV1` | All `BaselineDraftV1` fields plus `digest: Digest`; digest computed from all other fields, including schema/project/parent identity |
| `ImportWarningV1` | `code: LEGACY_APPROVAL_UNTRUSTED / MISSING_PROVENANCE / CRITERION_REVIEW_REQUIRED / METADATA_NOT_MIGRATED / BOM_REMOVED`, `pointer: Pointer`, `message: ShortText`; message is a fixed template without user input values |
| `ImportResultV1` | `schema_version: Version`, `draft: BaselineDraftV1`, `input_digest: Digest`, `warnings: array[ImportWarningV1]`; no authoritative approval field |
| `ReviewCommandV1` | `schema_version: Version`, `project_id: UUID`, `subject_digest: Digest`, `decision: approve / reject / revoke`, `expected_sequence: Sequence`, `request_id: UUID`, `reason: Text` (nonblank); no actor, timestamp or active-baseline override supplied by imported content |
| `ReviewDecisionV1` | All command fields plus `sequence: Sequence`, `reviewer_label: ShortText`, `recorded_at: Timestamp`, `previous_active_digest: Digest or null`, `resulting_active_digest: Digest or null`; append-only |
| `EffectiveReviewV1` | `schema_version: Version`, `project_id: UUID`, `subject_digest: Digest`, `status: pending / approved / rejected / revoked / superseded`, `decision_sequence: Sequence or null`, `project_sequence: Sequence`, `active_digest: Digest or null`, `head_digest: Digest or null`; unknown subject is an error, never pending |
| `StoredSnapshotV1` | `schema_version: Version`, `project_id: UUID`, `digest: Digest`, `created: boolean`; identical stored bytes return `created=false` |
| `ValidationErrorV1` | `code: error enum from section 8`, `pointer: Pointer`, `message: ShortText`; no input bodies, excerpts or exception repr |
| `InspectionV1` | `schema_version: Version`, `project: ProjectRecordV1`, `snapshot: BaselineSnapshotV1`, `review: EffectiveReviewV1`; consistent read transaction |
| `HistoryPageV1` | `schema_version: Version`, `project_id: UUID`, `decisions: array[ReviewDecisionV1]`, `next_after_sequence: Sequence or null`; ascending sequence, next cursor is last returned sequence only when more rows exist |
| `ValidationReportV1` | `schema_version: Version`, `structurally_valid: boolean`, `errors: array[ValidationErrorV1]`, `approval_blockers: array[ValidationErrorV1]`, `store_checks: not_performed`; validation does not connect to a store |

Structural validation: 1..1000 requirements, 0..5000 criteria, 0..10000 evidence
records, at most 64 references/dependencies per item and 64 preconditions per criterion.
Each precondition is nonblank. Duplicate references fail; dependency cycles are retained
as declared relationships, not interpreted as an execution graph. Self-dependencies
fail. Unresolved criteria require a nonblank `unresolved_reason`; specified criteria
require nonblank action/expectation and a null unresolved reason. Unsupported criteria
require a nonblank support reason; supported/unknown criteria require null support reason.
An empty precondition array explicitly means no stated preconditions.

Freeze permits structurally valid unresolved snapshots and grants no approval.
Approval requires all requirement titles/descriptions nonblank; at least one criterion
per requirement; every criterion specified; automation support explicitly supported
or unsupported; and each requirement and criterion linked to at least one document
or human-decision evidence record. `legacy_import` alone does not prove original SRS
provenance. Document hashes/references supplied by a human are claims for that operator
to verify, not proof that M0 fetched the document. Whole-baseline review affirms all
expectations and provenance together. Unsupported but clear criteria may be approved;
ambiguous or missing expectations block the entire approval. No score or confidence
threshold substitutes for review. New snapshots always start pending.

`LegacyClaimV1` and inherited evidence records are unchanged in descendants. Reviewed
title/description, dependency links and criterion content may change only in a new
snapshot. New evidence can be appended and referenced; old evidence remains available.
No credential fields are admitted, but free text can still contain confidential data.
Repeated legacy imports produce independent drafts with stable entity IDs. To promote a
later import into an existing lineage, explicitly merge it with the current head draft,
retaining the first original legacy claim and adding the new import's evidence. M0 does
not implement an automatic merge or silently replace the original source claim.

## 4. Canonical bytes and digest

1. Validate the complete typed object first. Reject duplicate JSON object keys at any
   depth, unknown properties, unknown versions and non-finite input numbers.
2. Sort requirements by `requirement_id`, criteria by `criterion_id`, evidence by
   `evidence_id`, and UUID reference/dependency arrays lexicographically. Reject
   duplicates before sorting. Preserve precondition order and all string contents.
3. Emit every listed field, including nulls and empty arrays. Encode tuples as arrays.
   Sort object keys lexicographically; the defined property names are ASCII.
4. Emit UTF-8 JSON without BOM, indentation or trailing newline. The reference
   serializer is standard-library `json.dumps(..., ensure_ascii=False,
   sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')` over
   the validated primitive tree. Escape quotes, backslashes and controls as that
   serializer does; do not escape `/` or non-ASCII characters unnecessarily.
5. Calculate SHA-256 over the snapshot object excluding only its top-level `digest`.
   Store as `sha256:<lowercase hex>`. All other fields participate; in particular,
   changing the project, parent, evidence, support status, original claim or expectation
   changes identity. A digest identifies the complete revision, not only its prose.

Snapshots contain no creation timestamp, review, random revision ID, local storage path
or current status. Project/review timestamps live outside the hashed snapshot. Reordered
identity collections produce the same digest; reordered preconditions need not. A new
parent produces a new digest even when expectations are unchanged, enabling an explicit
new review after revocation. Hashing is not a semantic-equivalence test or signature.

Store the full snapshot as canonical bytes including `digest`. On every load, strictly
decode and validate, recompute the digest, verify stored project/parent metadata, and
compare the stored bytes with the canonical full representation. Fail on mismatch;
never silently rewrite a damaged row. Snapshot insertion is idempotent only for exactly
matching canonical bytes. Golden-byte/digest vectors are recorded in the synthetic
test fixtures and passed offline verification. They establish compatibility only for
this tested V1 scope.

## 5. Review lifecycle and lineage

Per project, keep `review_sequence` (initially 0), `head_digest` (latest ever approved,
initially null) and `active_digest` (currently authorized baseline, initially null).
The head is retained on revocation. Snapshot creation does not advance the sequence
or either pointer. A nonnull parent must already exist in the same project. Parent
membership/provenance rules from sections 2 and 3 are checked at storage and approval.

| Command | Preconditions | Atomic result |
| --- | --- | --- |
| approve | Subject is pending; approval content checks pass; subject parent equals current head, including null for the first approved root; expected sequence matches | Append decision at sequence + 1; set head and active to subject; previous active approval becomes superseded |
| reject | Subject is pending; expected sequence matches; content need not be approvable | Append rejection at sequence + 1; head/active unchanged |
| revoke | Subject is currently active and approved; expected sequence matches | Append revocation at sequence + 1; active becomes null; head unchanged; no fallback |

No other transitions are allowed for a new request ID. Rejected, revoked and superseded
subjects cannot be directly approved again. Already approved cannot be approved/rejected
again by a new command. Superseded/rejected subjects need no separate revoke operation:
they have no current authority and cannot be reactivated. A rejected snapshot must be
corrected into different content before review; merely changing its review reason does
not change the subject. To restore revoked or older expectations, create a successor
whose parent is the current head, retain all required identities/provenance, and obtain
fresh review. No rollback command or automatic ancestor activation exists.

Pending branches may be stored, but a branch based on an older head cannot be approved:
return `LINEAGE_CONFLICT`. Rebase its draft explicitly onto the current head, resolve
content/membership differences, freeze a new digest and review that digest. There is
no automatic merge. These conservative rules favor inspectable history over convenient
undo; operator mistakes can require a new snapshot.

Effective status is derived from append-only decisions plus current pointers: no
decision means pending; latest reject/revoke means rejected/revoked; approved subject
matching active means approved; a formerly approved subject replaced by a later approval
means superseded. Verify pointer/decision/sequence consistency; contradictory storage
is `INTEGRITY_ERROR`, not an inferred approval. Historical decisions remain inspectable
even when an identical command retry returns an approval that is no longer effective.

## 6. SQLite and idempotent command rules

Use Python's existing `sqlite3` and an application-owned database, never checkpoint
tables. Database `user_version=1`; schema fingerprint/table constraints are checked on
open. Existing nonempty/unrecognized files, future versions and legacy checkpoint
databases fail explicitly. No automatic migrations or overwrites.

Logical tables: immutable project identity; mutable project state; immutable snapshots
keyed by `(project_id,digest)`; append-only review decisions keyed by
`(project_id,sequence)` and unique `(project_id,request_id)`. Snapshots contain canonical
bytes plus project/digest/parent metadata. Application foreign keys and checks prohibit
cross-project subjects, parents and active/head pointers. SQL constraints and triggers
block UPDATE/DELETE of snapshot and decision rows through supported connections;
direct administrative edits remain outside the trust boundary.

Set and verify `foreign_keys=ON`, `journal_mode=DELETE`, `synchronous=FULL`, and
`busy_timeout=5000` ms on write connections, outside transactions where required.
Use explicit transaction control (`isolation_level=None` with `BEGIN IMMEDIATE`),
parameterized SQL and rollback on every pre-commit failure. One connection per command;
no pooling, WAL, background job, ORM or retry daemon. Reads use a coherent read transaction
and a `mode=ro` SQLite URI generated from a validated local path, never user URI syntax.
Do not use `immutable=1` to ignore possible active transactions or recovery needs.

For each review command:

1. Validate syntax and limits without effects; open the explicitly selected valid store.
2. `BEGIN IMMEDIATE`; resolve project/reviewer, validate relevant stored integrity, and
   look up `(project_id,request_id)` **before** comparing current sequence or status.
3. If an existing decision's canonical command fields match exactly, return that original
   decision unchanged, without another row, timestamp or sequence increment. Its original
   expected sequence remains part of the comparison. If any command field differs, fail
   `REQUEST_ID_CONFLICT`. Reviewer/project identity cannot change in M0.
4. For a new request, require `expected_sequence == project.review_sequence`, validate
   subject, parent, approval requirements and legal transition. Compute sequence + 1.
5. Insert the decision and update project state in the **same transaction**, then commit.
   Only then emit success. Use the original request ID for recovery after output failure.

No automatic application retry on lock timeout. Return `STORE_BUSY` after the bounded
SQLite wait; operator retries the same command. Failure before commit leaves approval
unchanged. If the process dies or an I/O error makes the commit outcome uncertain, report
`COMMIT_OUTCOME_UNKNOWN` when possible and inspect/retry the same request ID on reopen.
Do not promise unchanged state after an ambiguous commit acknowledgment. This explicitly
refines the older proposal's overly broad "all failures leave approval unchanged" rule.
SQLite transactions cannot atomically include stdout or another JSON file.

Snapshot store and project creation each use their own transaction. Freeze stores one
snapshot atomically and returns its digest; it does not write a second authoritative
snapshot file. Duplicate project creation is an explicit error; reviewer replacement is
outside M0. Disk-full, corruption and permission failures return non-success; no empty
result or automatic repair. Test reopen and crash windows; do not claim protection
against all power loss, storage devices or user tampering. Remote/network/synchronized
storage and database backup tooling are outside the initial supported environment.

## 7. Bounded legacy import

Accept only a UTF-8 JSON object representing the current legacy `RequirementBundle`.
Read at most 4194305 bytes and reject more than 4194304 bytes (4 MiB) before parsing.
An optional single UTF-8 BOM is accepted with a warning; hash the exact original bytes,
including BOM. Reject invalid encoding, duplicate keys, non-finite numeric constants,
more than 32 levels of nesting, more than 100000 JSON nodes, oversized strings and
excessive record counts. Bound nesting using a string/escape-aware pre-scan before
recursive decoding; enforce node and scalar limits during bounded parsing/validation.
No truncation, partial successful import, code-fence extraction or model repair.

Allowed top-level legacy fields: `requirements`, `domain_profile`, `pdf_path`,
`pdf_sha256`, `run_id`, `extracted_at`, `pass_stats`. `requirements` is required;
1..1000 entries, each with string `req_id`, `title`, `description` required.
Optional requirement keys are exactly those in
[Requirement](../app/schemas.py#L95): `priority`, `req_type`, `feature_area`, `section_ref`,
`dependencies`, `gap_analysis`, `confidence`, `approved`, `rejected`, `human_prompt`,
`source_chunk`. Validate types without coercion; priority is high/medium/low; confidence
is finite in [0,1]; source_chunk is null or a nonnegative integer; optional strings may
be null only where the legacy schema permits. Missing booleans remain null claims,
not inferred false/approval. Reject duplicate/blank IDs and dangling dependency IDs.

`domain_profile` accepts only its declared fields in
[DomainProfile](../app/schemas.py#L72), with their declared scalar/list types;
`pass_stats` accepts only `pass1_count`, `pass2_enriched`, `pass3_flagged`,
`pass4_gap_added`, `pass5_deduped_removed`, and `chunks`, each a nonnegative integer
at most 9007199254740991, plus `total_time_s` as a finite nonnegative number. These
last two fields are emitted by [the current exporter](../app/agents/extraction_agent.py#L493),
although the schema comment does not list them. Unknown keys
anywhere fail `UNKNOWN_FIELD`; a bundle with resource/auth/token fields is rejected,
not scrubbed into a successful import. This deliberately supports a bounded legacy
format rather than every permissive `Dict[str, Any]` historical extension.

Import maps every requirement one-for-one, preserving original title/description/ID
and approval/gap flags, section/chunk hints, human prompt and claimed PDF hash in
`LegacyClaimV1`, and resolving dependencies to stable IDs. Absent or explicit-null
optional hints remain null; no content is invented. A supplied PDF hash must be 64
hexadecimal characters; it remains a claim, not verified original-document evidence.
Create one unresolved candidate criterion per requirement: no invented action or expected
outcome, empty preconditions, unknown support, and origin inferred only when the legacy
gap flag is true, otherwise legacy_extracted. Its reason is a fixed "Legacy expectation
requires explicit review" message. Add legacy evidence referencing the input digest and
JSON pointer with original description (or title if nonblank; otherwise a fixed
"Legacy record has no requirement text" placeholder explicitly marked legacy_import).
This source is provenance of the imported record, not a fabricated SRS quotation.

Warn explicitly about all legacy approval claims and missing authoritative provenance.
Known ancillary metadata not represented in V1 (priority, type, feature, confidence,
and top-level runtime/PDF-path/domain/pass metadata) produces a
`METADATA_NOT_MIGRATED` warning per present field with its pointer. It is never silently
discarded or treated as a human decision; the input digest identifies the original
operator-retained file. This is a baseline adapter, not an archive of the full cache.
Section hints do not become verified document evidence. The original input is neither
modified, copied into Git nor automatically opened at its embedded paths/URLs.

Warnings are retained in `ImportResultV1` (max 20000) and returned by prepare; they are
not part of stored snapshots or the authority for approval. `validate` accepts the
envelope and validates its warning records before selecting the enclosed draft.
Operators retain that import report, edit the draft and supply explicit criteria/evidence.
Input failures emit only fixed error codes, JSON pointers and safe messages;
never input excerpts, arbitrary unknown key text, traceback
locals or Pydantic's default error output containing `input_value`.

## 8. Windows storage, CLI and errors

Proposed entry point: `python -B -m app.baseline_cli`, independent of `main.py`.
Use explicit `--db` on database commands; no environment-derived default or global
current project. Existing-directory paths are resolved from the caller's working
directory. For database/output writes, require an existing parent, local fixed drive,
ordinary file (or new leaf), no symlink/junction/reparse-point components, no UNC,
device namespace, mapped network drive, NTFS alternate stream, reserved DOS basename,
trailing dot/space, or drive-relative path such as `C:review.db`. Permit spaces and
Unicode; use path APIs and bound SQL parameters, never shell interpolation. Recheck
before opening; this is accidental-path protection, not a race-proof host sandbox.
Document local, non-synchronized storage as a prerequisite; synchronization cannot
be comprehensively detected from path text.

Database suffix is `.sqlite3`. Create only through `init-store`, reserving a new leaf
without overwriting existing bytes. `init-store` never creates parents. On failure,
leave an explicitly reported incomplete store for manual inspection rather than
deleting an arbitrary path. All other database commands open an existing identified
M0 database; missing path never creates a new one. SQLite rollback journals and its
bounded recovery writes are permitted inside this explicitly chosen trusted directory.
Read-only inspect cannot perform recovery; report `RECOVERY_REQUIRED` if a hot journal
prevents a read, and require an explicit write-mode command/retry for SQLite recovery.
Do not delete journal files manually. Database/journal patterns are already excluded
by [.gitignore](../.gitignore); JSON drafts/exports must be kept in an excluded private
runtime directory (for example `output/baselines`) or a private directory outside Git.
M0 does not add a new broad ignore rule or pretend `.gitignore` provides encryption.

Native drafts/import envelopes are limited to 8388608 input bytes (8 MiB), canonical
snapshots to 8 MiB, and review-command input to 65536 bytes. Apply the same depth/node/
string limits as legacy import. Paths in requirement evidence are inert references.
Explicit input/output arguments may name only ordinary local files under the documented
path policy; stdin, pipes, URLs and compressed inputs are outside V1. Preparation
exports use a same-directory temporary file and no-replace publication on the supported
Windows filesystem, without deleting/overwriting an existing destination. Flush/close
before publication; failure leaves no successful output and may leave an identified
temporary file. This export is not an approval record or a database transaction.

| CLI operation | Effects and required arguments |
| --- | --- |
| `--help`, `version`, `new-id` | No file/database/provider effects; version prints supported wire/store version; new-id prints UUIDv4 |
| `init-store --db PATH` | Explicitly create an empty V1 store; never overwrite |
| `create-project --db PATH --project UUID --reviewer LABEL` | Insert immutable local project identity; no existing-project overwrite |
| `prepare --input PATH --project UUID --source-key KEY --out PATH` | Bounded legacy import; write an exclusive `ImportResultV1` JSON export; no DB required; parent null initially |
| `validate --draft PATH` | Read strict `BaselineDraftV1` or `ImportResultV1`, report structural issues and approval blockers without writes; file validity alone is not approval |
| `freeze --db PATH --draft PATH` | Require known project; use explicit parent in draft; validate/store snapshot transactionally; emit digest and created flag |
| `review --db PATH --project UUID --digest DIGEST --decision DECISION --expected-sequence N --request-id UUID --reason TEXT` | Atomic explicit command; reviewer comes from stored project; reason must be nonsecret because command lines may be recorded |
| `inspect --db PATH --project UUID --digest DIGEST` | Read-only full snapshot, effective review and project sequence; exposes unsupported/unresolved criteria |
| `history --db PATH --project UUID --after-sequence N --limit N` | Read-only decisions in ascending sequence; default after=0, limit=100, allowed limit 1..1000; cursor is last sequence |

JSON responses go to stdout with one terminal newline and no ANSI; escape terminal
control sequences rather than rendering imported text. Diagnostics go to stderr as
safe structured errors. `inspect` intentionally reveals private baseline text to the
operator; no automatic logging or telemetry export. A returned digest is the exact
subject to review; `review` never accepts `latest` or guesses active state.

Exit 0: completed operation (including rejected/revoked decisions and identical retries;
inspect status remains explicit). Exit 2: usage/validation/size/version failure, or
validate reports approval blockers. Exit 3: review/state conflict, unknown subject/project,
or content not approvable. Exit 4: storage/path/integrity/recovery/output failure or
uncertain commit outcome. Exit 130: interruption, without promising pre-commit state.
Nonzero results do not prove that a commit never happened; same-request recovery applies.

Error enum: `INVALID_INPUT`, `UNKNOWN_FIELD`, `UNSUPPORTED_VERSION`, `LIMIT_EXCEEDED`,
`DUPLICATE_ID`, `INVALID_REFERENCE`, `PROJECT_EXISTS`, `UNKNOWN_PROJECT`, `UNKNOWN_SUBJECT`,
`PROJECT_MISMATCH`, `NOT_APPROVABLE`, `INVALID_TRANSITION`, `LINEAGE_CONFLICT`,
`PARENT_ID_LOSS`, `STALE_SEQUENCE`, `REQUEST_ID_CONFLICT`, `SEQUENCE_EXHAUSTED`,
`PATH_POLICY`, `STORE_EXISTS`, `STORE_NOT_FOUND`, `STORE_BUSY`, `STORE_FAILURE`,
`INTEGRITY_ERROR`, `RECOVERY_REQUIRED`, `OUTPUT_FAILURE`, `COMMIT_OUTCOME_UNKNOWN`.
Choose the most specific applicable code; return bounded structured errors, no swallowed
exceptions. Unknown-field diagnostics use a safe parent pointer and fixed message, not
the unknown field's contents. Whole-input rejection never emits a partial successful draft.

## 9. Proposed internal interfaces

```text
import_legacy_bundle(raw_bytes, project_id, source_key) -> ImportResultV1
validate_draft(raw_bytes) -> BaselineDraftV1 | ValidationErrors
freeze_baseline(validated_draft) -> BaselineSnapshotV1
store_snapshot(store, snapshot) -> StoredSnapshotV1
record_review(store, command, trusted_local_context) -> ReviewDecisionV1
get_effective_review(store, project_id, digest) -> EffectiveReviewV1
```

Parsing/identity/canonicalization/content-validation functions are pure. Store operations
enforce project, lineage and authority rules independently of CLI checks. The trusted
local context is constructed by the command boundary from the project record, not accepted
as serialized imported data. A separate validator reports approval blockers; `freeze`
allows pending unresolved content, while `record_review(approve)` rechecks blockers.
These interfaces refine the earlier generic names without replacing the approved
modular design. They do not integrate the new authority with the unsafe existing runtime.
