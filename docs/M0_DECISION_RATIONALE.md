# M0 approved decisions and rationale

Status: **APPROVED FOR THE M0 SUBSET - implemented and verified offline**. Revision
`M0-SPEC-2026-10-23-v2`. Read the [scope and approval gate](M0_VERSIONED_BASELINES.md)
and [exact V1 contracts](M0_CONTRACTS_V1.md). This completes specification detail;
it does not approve the full ADR-01 through ADR-06 scope. M0 implementation evidence
is recorded in [M0 verification](M0_VERIFICATION.md); broader runtime safeguards remain absent.

## Evidence and comparison with the earlier specification

Retain the justified foundation: offline-only M0, one operator, whole-baseline review,
mandatory legacy re-review, immutable snapshots, separate append-only review records,
SQLite and existing Pydantic/standard-library tests. Do not introduce event sourcing,
another agent, an API, signing infrastructure, a broker or a new package manager.

Source inspection for the original specification phase was limited to the legacy contracts/import path,
CLI/configuration import effects, package initializers, exclusions and dependency
metadata. [Requirement](../app/schemas.py#L95) mixes content with approval booleans;
[RequirementBundle](../app/schemas.py#L128) has permissive metadata and no criterion
revision contract. [Saved-bundle loading](../app/core/react_controller.py#L359)
sets approval flags automatically. [Configuration import](../app/config.py#L10)
loads environment data and [creates directories](../app/config.py#L21).
[main.py](../main.py#L27) performs logging/bootstrap imports before commands.
These support a separate offline entry point, not a graph or extraction rewrite.

Read-only metadata inspection found Python 3.11.9, SQLite 3.45.1 and Pydantic 2.12.5.
This is an observed local baseline, not a clean-install test or a new dependency pin.
No product execution, browser/provider call or repeated architecture research occurred
during that original specification phase. The later approved M0 offline tests and
implementation results are recorded separately in M0_VERIFICATION.

The new precision is deliberate: terminal old review states, explicit head versus active
baseline, stable imported IDs, monotonic identity membership, exact canonical bytes,
bounded import and Windows file behavior. One correction is essential: the earlier
statement that *all* failures leave approval unchanged cannot cover a crash after
commit but before acknowledgment. M0 must expose uncertainty and replay the same request.

## M0-D01 - Single-operator reviewer authority

- **What/why:** Retain one designated local reviewer; separate attribution from imported
  claims because current saved-bundle approval is automatic and untrusted.
- **How:** Immutable project reviewer label, explicit review command, trusted local
  filesystem/OS-user boundary; no reviewer identity from requirement JSON. CLI checks
  and store checks share the same policy. No provider integration can issue commands.
- **Simpler alternative:** A free-form actor flag or existing approved boolean is less
  code but permits accidental impersonation and conflates a claim with a decision.
- **Trade-offs/failures:** The same OS user or administrator can impersonate the label
  or alter storage. M0 is not authenticated multi-user review; permission to use a shell
  is effectively permission to review. Do not claim a technical ban on external models
  using an independently granted shell. Private folders are an operating prerequisite.
- **Verify:** AC-01, AC-10, AC-25: imported actors/approvals rejected as authority;
  project-derived reviewer attribution; fail on mismatched project.
- **Reconsider:** Shared machine accounts, multiple reviewers, remote commands,
  delegation or legal-signature requirements need authentication and a new trust model.

## M0-D02 - Whole-baseline approval

- **What/why:** Retain one decision for the exact complete digest; avoid partial approvals
  that disagree with dependency, coverage or revision boundaries.
- **How:** Approval validates every requirement/criterion and evidence reference. One
  unresolved expectation blocks the decision; freeze can still preserve a pending draft.
  Approval concerns accepted business expectations, never execution permission.
- **Simpler alternative:** Approve the imported bundle without criteria validation;
  easier but preserves existing correctness defects. Per-item approval is more flexible,
  not simpler: it needs composition and stale-subset rules.
- **Trade-offs/failures:** A small change requires whole-baseline review; large documents
  can become burdensome. A human can still approve an incorrect expectation.
- **Verify:** AC-03..06, AC-09, AC-26: no vacuous/partial approval, every item represented,
  changes invalidate the prior digest's authority.
- **Reconsider:** Measured review effort or independently owned requirement groups justify
  granular approval, with explicit aggregation semantics first.

## M0-D03 - Mandatory legacy re-review

- **What/why:** Retain every legacy flag only as a historical claim. Current saved JSON
  loading auto-approves nonrejected records; its flags are not reliable authorization.
- **How:** One-for-one draft import, original IDs/text/flags retained, unresolved candidate
  criteria, explicit warnings and fresh review; no inferred source provenance.
- **Simpler alternative:** Trust prior approved=true when not rejected. It is convenient
  but imports the very defect the new authority is intended to avoid.
- **Trade-offs/failures:** Manual effort; missing original source evidence may need an
  explicit human decision. Imported section hints cannot prove the source was inspected.
- **Verify:** AC-01..04, AC-09, AC-30: inferred, approved, rejected and conflicting flags
  never create approval; exact original text and input digest survive.
- **Reconsider:** A future importer with authenticated, version-bound external approval
  records could support a separately reviewed trust migration. No heuristic exemption.

## M0-D04 - Unsupported and ambiguous criteria

- **What/why:** Preserve the distinction between a clear business expectation and its
  automation support. Unsupported is not rejected, missing or satisfied.
- **How:** Separate clarity and support enums. Clear unsupported criteria may be approved
  with a reason and provenance. Unknown support or ambiguous action/expectation blocks
  whole-baseline approval. All remain visible in pending snapshots and inspect output.
- **Simpler alternative:** Treat every unsupported item as unapprovable; simpler but
  confuses business authority with tool capability. Dropping it falsely improves coverage.
- **Trade-offs/failures:** Support classification is human supplied, not a validated
  capability claim; no denominator or runtime behavior is implemented in M0.
- **Verify:** AC-04..06, AC-26: missing expectations and unknown support block; explicit
  unsupported expectations remain in approved content and inspection.
- **Reconsider:** Runtime integration must define support evidence and coverage reporting;
  any exclusion/removal workflow needs its own auditable scope decisions.

## M0-D05 - Revocation, supersession and reactivation

- **What/why:** Fill the open transition rules. No silent fallback, direct reactivation,
  or mutable rewrite of history. Distinguish latest approved head from currently active.
- **How:** Pending may approve/reject; only active approved may revoke. Approval replaces
  active/head transactionally; revoke clears active but retains head. Terminal old subjects
  require a new corrected/rebased successor and fresh review. Parent must equal head at
  approval; stale branches are not automatically merged. Rejected content must change.
- **Simpler alternative:** One active pointer with fallback to the last approval is small
  but can resurrect revoked expectations. Allowing direct reapproval needs more transition
  rules and makes operator intent harder to inspect; defer it.
- **Trade-offs/failures:** Undo is deliberately inconvenient. Retain parent IDs/evidence;
  M0 cannot withdraw or delete criteria. A reviewer error may require another snapshot.
- **Verify:** AC-09, AC-13, AC-21..23: revoke leaves no active baseline, history survives,
  old expectations need fresh review, competing branches fail, removed IDs fail.
- **Reconsider:** Real withdrawal/merge/split or frequent mistaken rejections may justify
  explicit reviewed operations; never add implicit rollback as a convenience fix.

## M0-D06 - Stable requirement and criterion identity

- **What/why:** Specify identity independently of mutable text and array order; preserve
  multiple criteria and distinguish different sources using the same legacy IDs.
- **How:** UUIDv4 for new entities; deterministic UUIDv5 from project/source-key/original
  ID for legacy imports, and requirement ID for the initial candidate. Preserve IDs on
  edits and original claims across successors. Snapshot digest identifies revision.
- **Simpler alternative:** Preserve bare legacy req_id globally; collisions are likely.
  Content-derived IDs change on every edit and erase continuity. Random import IDs avoid
  collisions but make repeated imports indistinguishable from new requirements.
- **Trade-offs/failures:** Reusing a source key incorrectly can imply false continuity;
  the operator owns source-family identity. IDs do not detect semantic subject changes.
- **Verify:** AC-02, AC-03, AC-06, AC-18, AC-23: reorder/edit stability, project/source
  separation, duplicate failure, no title-similarity merges or criterion reassignment.
- **Reconsider:** Cross-project synchronization or richer source adapters need explicit
  mappings and migrations, not changes to the UUID algorithm in place.

## M0-D07 - Immutable V1 contracts

- **What/why:** Retain immutable snapshots but define every field, reference, enum and
  boundary. Frozen top-level models alone do not freeze nested mutable containers.
- **How:** Strict versioned envelopes, frozen nested models/tuples, no Any/resources,
  explicit nulls, safe validation errors, project-scoped references. Snapshot content
  remains distinct from reviews and effective status; old runtime models stay unchanged.
- **Simpler alternative:** Freeze a JSON dict and trust callers. Less validation code,
  but mutation, coercion and silent extra-field loss remain possible.
- **Trade-offs/failures:** More schema/test code and deliberate incompatibility with
  permissive legacy inputs. Python immutability is an API contract, not a hostile-code
  boundary. Unsupported wire/store versions fail rather than auto-migrate.
- **Verify:** AC-06, AC-19, AC-26, AC-32: nested mutation fails through supported APIs,
  coercions/extras/versions fail, copied values are revalidated, no credentials admitted.
- **Reconsider:** New source or product concepts require V2 plus compatibility decisions;
  do not weaken V1 to accept arbitrary fields.

## M0-D08 - Canonical serialization and digest

- **What/why:** Complete the existing canonicalization proposal so identity is reproducible.
  A parent, evidence or support change must invalidate the reviewed revision too.
- **How:** Sorted identity collections/keys, preserved ordered steps/text, explicit nulls,
  UTF-8 compact JSON, no floats, SHA-256 over all snapshot fields except digest. Timestamps
  and review state are outside the snapshot. Verify canonical bytes and digest on load.
- **Simpler alternative:** Hash input file bytes or serializer defaults; harmless formatting
  changes then alter identity. Adopting a general cross-language canonicalization library
  is unnecessary for the restricted Python V1 value domain.
- **Trade-offs/failures:** Semantically equivalent text may hash differently; that is
  intentional. Hashes neither authenticate reviewers nor prevent an administrator from
  replacing content and digest together. Cross-language writers need golden-vector proof.
- **Verify:** AC-07..09, AC-16, AC-20: key/set reordering stable, ordered steps/text/parent
  changes different, Unicode preserved, duplicate keys and tampered bytes fail.
- **Reconsider:** Other language writers, signing protocols or numeric semantics justify
  a versioned canonicalization change; never alter persisted V1 byte rules silently.

## M0-D09 - SQLite transactions and idempotent review commands

- **What/why:** Retain transactional storage; define stale decisions, locks and ambiguous
  acknowledgment. Checkpoints cannot supply these application approval guarantees.
- **How:** Explicit BEGIN IMMEDIATE, sequence comparison, same-transaction decision and
  active/head update, unique project/request ID. Identical retries return the original
  result before stale-sequence checks; conflicts fail. DELETE journal/FULL sync, bounded
  lock wait, foreign keys and immutable-row constraints. Unknown commit outcome triggers
  same-request inspection/retry, never a new guessed approval.
- **Simpler alternative:** One JSON file or separate writes is easier but cannot provide
  transactional command history and conflict handling. WAL/ORM/broker adds maintenance
  without a demonstrated single-operator need.
- **Trade-offs/failures:** Locks can reject simultaneous commands; storage/hardware can
  still fail. Stdout and DB are not atomic. A hot journal may require an explicit write
  open for recovery; read-only inspection does not silently repair it.
- **Verify:** AC-11..16, AC-22, AC-24, AC-28, AC-32: duplicate delivery, conflict, crash
  windows, reopen, lock/disk failure, pointer consistency and original-request recovery.
- **Reconsider:** Multiple independent writers, remote workers, measured contention or
  availability requirements justify a new database/operation model.

## M0-D10 - Legacy import limits and failures

- **What/why:** Fill missing limits without claiming arbitrary legacy compatibility or
  silently dropping requirements. Bound resource use and error disclosure.
- **How:** 4 MiB legacy input, 8 MiB native input/snapshot, explicit record/text/depth/node
  limits, duplicate/unknown-key rejection, no coercion or partial success. Preserve core
  original records; warn per known ancillary field not migrated. Exact input hash links
  back to the operator-retained source; do not archive private input in Git.
- **Simpler alternative:** `json.load` into the existing permissive model; small but accepts
  silent defaults, extras and unsafe sizes. An arbitrary metadata blob preserves everything
  but expands confidential storage and complicates immutable canonicalization.
- **Trade-offs/failures:** Valid large/custom bundles can be rejected. Limits are conservative
  initial policy values, not measured capacity. Warnings require operator attention; the
  original input must be retained separately. Free text may contain secrets despite schema.
- **Verify:** AC-01, AC-06, AC-27, AC-30: boundary/boundary+1, malformed UTF-8/JSON,
  deep nesting, unknown resource fields, no input body in errors, explicit omission warnings.
- **Reconsider:** Measured real bundle sizes or a documented exporter variant can justify
  reviewed limits/adapter changes; no hidden flag to disable all validation.

## M0-D11 - Windows paths and offline CLI

- **What/why:** Retain a small CLI but separate it from import-time configuration effects.
  Make writes explicit and compatible with spaces/Unicode on the actual Windows host.
- **How:** Explicit local `.sqlite3` path, existing parents, new-store-only init, no UNC/
  device/ADS/reparse/network paths or arbitrary URI query parameters. Read-only inspection,
  bounded no-overwrite export, structured output/exit codes, no environment/provider
  bootstrap, no default target. Missing stores fail rather than creating hidden databases.
- **Simpler alternative:** Reuse `main.py` and `app.config`; saves a parser but creates
  directories and couples offline review to unrelated provider/runtime imports. Stdout
  redirection alone is easy but can overwrite an existing file or write failure output.
- **Trade-offs/failures:** Filesystem races against a hostile same-user process are outside
  scope. Synchronized folders cannot be fully detected. No encryption, backup tool or
  cross-platform support claim; Python/SQLite/Windows behavior needs named local tests.
- **Verify:** AC-17, AC-29, AC-31, AC-33: import/help no effects, missing-store/UNC/ADS/
  junction rejection, Unicode paths, output failure, machine-readable status and workflow.
- **Reconsider:** Linux support, network storage, shared operators or services require
  explicit platform/security tests and possibly a different storage boundary.

## Approval boundary

The user explicitly approved these decisions within the exact M0 revision. The
[approval checklist](M0_VERSIONED_BASELINES.md#explicit-implementation-approval-checklist)
records that approval. Even after M0 acceptance, all existing
runtime findings remain open until separately scoped integration and verification.
