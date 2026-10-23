# M0 - Versioned Baselines and Review Records

Status: **PROPOSED - awaiting specification approval and implementation authorization**.
Final proposed specification revision: **M0-SPEC-2026-10-23-v2**. The original
architecture handoff is preserved; this revision resolves its open M0 details for
owner review. No M0 application modules, fixtures or regression tests have been created.

This is the authoritative proposed M0 scope. It supersedes the *ordering* of the older
first milestone (offline eligibility/result reconciliation), which remains necessary
follow-up work in [ROADMAP](ROADMAP.md). Its proposed implementation covers a narrow subset of
[ADR-01](adr/01-versioned-baselines.md) and [ADR-06](adr/06-persistence-replay.md).
The [decision register](DECISIONS.md) distinguishes accepted constraints from proposals.

Read this specification with [exact V1 contracts](M0_CONTRACTS_V1.md) and
[decision rationale](M0_DECISION_RATIONALE.md). Together they define the approval
candidate: this file owns scope, acceptance, sequence and approval; the contract file
owns field/serialization/command rules; the rationale file owns alternatives, trade-offs,
failure modes and reconsideration triggers. All three remain PROPOSED. No broader
architecture research was repeated and none of the six ADRs is automatically approved.

## Purpose

Create a usable offline path from an existing requirement bundle to a versioned baseline with explicit review history. Establish the authority later consumed by lifecycle and execution gates.

This is narrower than the previous F03/F04/F05 milestone. It establishes their prerequisite rather than prematurely claiming to fix them.

## Scope

- Import legacy requirement JSON without trusting its approval flags.
- Validate reviewed requirement/criterion drafts.
- Freeze deterministic baseline snapshots.
- Store snapshots and review decisions.
- Inspect effective approval and supersession.
- Provide a small offline command interface.

## Non-goals

No PDF extraction changes, model calls, crawling, code generation, artifact materialization, browser execution, result parsing, POM generation, checkpoint migration, remote service or UI.

## Contracts

| Contract | Required content |
|---|---|
| `BaselineDraftV1` | Project identity, parent, preserved requirements, criterion candidates and source evidence |
| `CriterionRevisionV1` | Stable identity, requirement reference, preconditions, action, expected outcome, origin, clarity and support status |
| `BaselineSnapshotV1` | Schema version, project identity, parent digest, complete immutable content and digest; the digest is the baseline revision identity |
| `ReviewDecisionV1` | Subject digest, approve/reject/revoke decision, trusted caller context, sequence, request ID and timestamp |
| `EffectiveReviewV1` | Pending, approved, rejected, revoked or superseded; supporting decision sequence and active/head pointers |
| `ImportResultV1` | Draft plus explicit warnings about legacy approvals, missing evidence and known metadata not migrated; unknown fields fail |

The full set also includes project, source evidence, original legacy claim, requirement,
review-command, stored-snapshot and safe error contracts. Exact fields, required/null
rules, limits and enums are defined only in [V1 contracts](M0_CONTRACTS_V1.md#3-exact-object-fields).

A draft may contain unresolved criteria. Approval requires a sufficiently specified expectation and source evidence or an explicit human-authored decision reference.

“Unsupported for automation” remains separate from whether the business expectation is approved.

## Interfaces

```text
import_legacy_bundle(raw_bytes, project_id, source_key) -> ImportResultV1
validate_draft(raw_bytes) -> BaselineDraftV1 | ValidationErrors
freeze_baseline(validated_draft) -> BaselineSnapshotV1
store_snapshot(store, snapshot) -> StoredSnapshotV1
record_review(store, command, trusted_local_context) -> ReviewDecisionV1
get_effective_review(store, project_id, digest) -> EffectiveReviewV1
```

The caller context comes from the trusted command boundary. It is not accepted from imported requirement JSON.

For the initial single-operator implementation, trust rests on the local operator and filesystem permissions. This is not multi-user identity assurance and does not defend against an administrator modifying the database.
The reviewer label is attribution, not authentication. An external agent/process with
the same user's shell permissions is not technically excluded by M0; no such integration
is exposed or authorized. See [authority limits](M0_CONTRACTS_V1.md#1-scope-authority-and-runtime-boundary).

## Persistence and canonicalization

Use one application-owned SQLite database at an explicitly selected local path:

- Immutable snapshots.
- Append-only review decisions.
- Current project baseline/review sequence.

Record a review decision and update the active baseline in one transaction. Use an expected sequence to reject stale concurrent decisions.

A repeated request ID with identical content returns the original decision. Reusing it with different content fails.
Check that identity before current sequence/status so a retry after a lost response
does not become a new decision. Pre-commit failures roll back; ambiguous commit or
output failures require same-request reconciliation, not a claim that nothing happened.

Define canonical serialization precisely:

- UTF-8 JSON.
- Sorted object keys and fixed separators.
- No non-finite numbers.
- Declared ordering for identity-based collections.
- Preserve meaningful text and ordered scenario steps.
- Exclude the digest field itself from its calculation.

Do not normalize away negation, whitespace inside meaningful text, or distinct source records.

Recompute the digest when loading a snapshot. A mismatch is an integrity error, not an opportunity to silently repair the record.
The exact SHA-256/canonical-byte rules, timestamp exclusions and collection ordering
are in [V1 section 4](M0_CONTRACTS_V1.md#4-canonical-bytes-and-digest); review transitions,
head/active distinction and transaction rules are in its following sections.

## Security invariants

1. Imported approval booleans never authorize anything.
2. Freezing a snapshot does not approve it.
3. Review targets exactly one project and baseline digest.
4. Content changes require a new snapshot and review.
5. Imported/model-authored content has no review authority; no model integration is exposed. The trusted local OS user remains capable of issuing commands.
6. Review-store errors fail closed.
7. No credentials/resource dictionaries enter the new contracts.
8. No execution capability is exposed by this milestone.
9. Old approvals and snapshots remain available as history.
10. The local trust assumption is documented rather than disguised as cryptographic authenticity.

## Likely files

These are proposed paths, not files created during this review:

| Path | Responsibility |
|---|---|
| `app/baseline_contracts.py` | Versioned immutable models and canonicalization |
| `app/core/baseline_review.py` | Import, validation and review rules |
| `app/core/review_store.py` | SQLite transactions and idempotent review records |
| `app/baseline_cli.py` | Offline prepare/review/inspect commands |
| `tests/test_baseline_contracts.py` | Semantic and identity tests |
| `tests/test_review_store.py` | Transaction, conflict and recovery tests |
| `tests/test_baseline_import.py` | Bounded legacy mapping, identity and safe failure tests |
| `tests/test_baseline_cli.py` | Windows paths, offline effects and command workflow |
| `tests/fixtures/baselines/` | Small synthetic, nonsecret fixtures |

Keep the current `RequirementBundle` and runtime graph unchanged during M0. Update
proposal documents during this authorized specification phase; update implementation
status only after separately authorized implementation and verified results.

## Acceptance tests

All cases below are **PROPOSED / NOT RUN**. Preserve the original AC-01..17 IDs;
AC-18..33 add verification for the now-explicit rules. Parameterized cases are required
where multiple inputs appear in one row. Use synthetic nonsecret fixtures and temporary
directories; assert durable state and output, not only exception names.

| ID | Stimulus / fixture | Required observable result | Layer |
| --- | --- | --- | --- |
| M0-AC-01 | Legacy approved/rejected/inferred and conflicting flags | Untrusted draft and explicit warnings; no trusted review record | Import |
| M0-AC-02 | Positive/negative requirements, roles and distinct thresholds | Exact original text/IDs retained one-for-one; no deduplication | Import/contracts |
| M0-AC-03 | Several criteria for one requirement | Distinct stable IDs and all criteria retained through freeze/load | Contracts/store |
| M0-AC-04 | Missing action/expectation or unresolved criterion | Freeze may preserve pending content; approve fails without state change | Policy/store |
| M0-AC-05 | Clear unsupported criterion with reason/evidence | Visible in approved snapshot/inspect; never dropped or claimed executed | Policy/CLI |
| M0-AC-06 | Unknown schema, duplicate IDs/keys, dangling/cross-project references | Explicit validation error, no partial stored snapshot/approval | Contracts/store |
| M0-AC-07 | Same typed content with permuted object/identity-set order | Identical canonical bytes and digest | Golden vectors |
| M0-AC-08 | Change a threshold only | New digest; original snapshot bytes preserved | Contracts |
| M0-AC-09 | Approve old digest, store changed content | New subject pending; old review never authorizes it | Store |
| M0-AC-10 | Review existing subject under another project | PROJECT_MISMATCH; both project histories/pointers unchanged | Store |
| M0-AC-11 | Identical request retried after later reviews/revocation | Original decision/sequence/timestamp returned; no new row; current effective state remains distinguishable | Store |
| M0-AC-12 | Reuse request ID with changed fields; stale new command | REQUEST_ID_CONFLICT or STALE_SEQUENCE; no partial writes | Store |
| M0-AC-13 | Approve A, approve successor B, revoke B | A superseded, B revoked, active null, head B; all original decisions retrievable | Store |
| M0-AC-14 | Inject failure after decision insert but before commit | Reopen shows neither inserted decision nor pointer/sequence change | Transaction |
| M0-AC-15 | Commit then close/reopen | Canonical snapshot/review/pointers and sequence persist | Store |
| M0-AC-16 | Alter snapshot bytes, digest or stored metadata | INTEGRITY_ERROR on load/review; no silent repair or new approval | Integrity |
| M0-AC-17 | Import new modules and execute help/version in empty temp environment | No directories/database/files/network/provider initialization; no legacy runtime imports | Import/CLI |
| M0-AC-18 | Repeat/reorder legacy input; change text; change project/source key | Same logical IDs for same project/source/legacy ID; separated identities for other namespaces; candidate IDs stable | Identity |
| M0-AC-19 | Mutate nested snapshot values and use invalid copy/update data | Supported APIs reject mutation/invalid copies; original digest/content unchanged | Contracts |
| M0-AC-20 | Unicode/whitespace/nulls, ordered preconditions, project/parent/evidence/support change | Golden bytes preserve text/order; identity-set order ignored; all substantive fields affect digest; no timestamp in snapshot | Golden vectors |
| M0-AC-21 | Every state x approve/reject/revoke with fresh request IDs | Only declared transitions succeed; no direct reactivation/fallback; restoration uses new child and review | Policy matrix |
| M0-AC-22 | Two pending branches; competing commands with equal sequence | One successful decision; loser explicitly stale/lineage-conflicted; rebase requires new digest | Two SQLite connections |
| M0-AC-23 | Remove inherited IDs/evidence, edit original claim, reassign criterion, invalid parent | Reject; preserve parent history; same-expectation restoration as current-head child allowed | Lineage |
| M0-AC-24 | Commit then lose acknowledgment/interrupt before stdout; retry original request | No invented rollback or duplicate decision; original result recovered; ambiguous failure explicitly non-success | Crash/CLI |
| M0-AC-25 | Imported actor/resource fields; reviewer flag injection; forged local label | Untrusted fields cannot set actor; command uses immutable project label; same-user threat documented, not falsely tested as prevented | Authority |
| M0-AC-26 | Empty requirements, no criteria, whitespace-only content, unknown support, legacy-only evidence | Structural/approval failure as specified; unresolved snapshots visible; clear unsupported criteria can pass review checks | Policy |
| M0-AC-27 | At/over byte, depth, node, item and text limits; BOM; malformed UTF-8/JSON; nonfinite values | Bounded explicit all-or-nothing behavior; no input snippets/secret values in errors | Import/contracts |
| M0-AC-28 | Lock beyond 5s, simulated disk-full/permission failures, pre/post-commit interruption | Bounded STORE_BUSY or explicit storage/uncertainty result; reopen/retry follows transaction outcome | Storage failures |
| M0-AC-29 | Local paths with spaces/Unicode; missing parents, UNC, network drive, ADS, devices, reserved names, reparse components | Ordinary local path works; prohibited paths fail before user-data writes; no parent creation/overwrite | Windows filesystem |
| M0-AC-30 | Known optional legacy metadata, absent flags, extra keys/credential dictionary | Original records retained; explicit per-field omission warnings; null claims preserved; unknown keys fail without logging values | Import |
| M0-AC-31 | Existing output/store, interrupted export, stdout failure, inspect missing DB | No overwrite or implicit DB; explicit failure; temporary export is not approved state; DB acknowledgment uncertainty preserved | CLI/filesystem |
| M0-AC-32 | Foreign-key violations, attempted row mutation, wrong DB version, inconsistent state, hot journal | Constraints/integrity errors; no checkpoint migration; read-only inspection refuses required recovery | SQLite |
| M0-AC-33 | Init/project/prepare/edit/validate/freeze/inspect/review/history/revoke sequence | Usable offline flow; explicit expected sequence/digest/request; correct JSON/status/exits; no graph/LLM/browser execution | Offline integration |


Use `unittest`, temporary directories and the already-installed Pydantic initially. Proposed verification command:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py"
```

That command is **proposed, not currently a passing repository gate**.

## Incremental sequence

1. Obtain explicit approval of this revision and the checklist below. Confirm the
   designated local reviewer and supported local Windows storage. No install is assumed.
2. Add synthetic fixtures and meaningful initially failing tests mapped to AC-01..33.
   Record the starting failures; do not add a vacuous suite or claim absent tests pass.
3. Implement isolated immutable contracts, validation, identity and canonicalization.
   Gate: AC-02/03/06..09/18..20/26 plus golden vectors and import-side-effect checks.
4. Implement the pure bounded legacy adapter. Gate: AC-01/02/18/27/30; original inputs
   untouched, no extraction/config/provider imports and no implicit review.
5. Implement explicit store initialization/project creation, immutable snapshot storage,
   review transition policy and transaction/idempotency rules. Gate: AC-09..16/21..25/
   28/32, including two-connection conflicts and crash/reopen tests on temporary stores.
6. Add the separate offline CLI, Windows path policy and bounded output handling.
   Gate: AC-17/29/31/33 with the documented workflow and machine-readable errors.
7. Run the complete offline suite; inspect source/import boundaries, exclusions, tests
   and diff for credentials/effects. A skipped required platform/crash case is a gap,
   not a pass. Repeat only affected checks after failures/changes.
8. Record actual commands, failures, results and limitations; update finding/decision
   status accurately. M0 completion is not runtime approval or closure of F01-F17.
   Commit/push/deployment require a separate user request.

## Definition of done

The operator can prepare, review and inspect a versioned baseline offline; all named acceptance cases pass; no legacy approval is promoted implicitly; and verified commands/results are documented.

M0 does **not** fix the old writer, unsafe repair, planner bypasses, runner isolation or result accounting. Those findings remain open until the new authority is integrated and their own acceptance tests pass. Existing runtime execution remains unapproved.

## Remaining risks and deliberately deferred decisions

- Reviewer identity/provenance are local trust assumptions. Hashing and frozen objects
  do not authenticate intent, prevent administrator edits or prove correct expectations.
- Whole-baseline review and no direct reactivation/removal increase operator work.
  UUID/source-key assignment still depends on correct human source-family identification.
- Legacy input compatibility is intentionally bounded. Known ancillary metadata produces
  warnings; unknown extensions fail. Preserve original input privately for later inspection.
- Numerical limits are proposed starting policy, not benchmarked capacity. Unicode,
  Windows path/reparse behavior, SQLite failure windows and exact bytes need the named tests.
- Filesystem ACLs, local nonsynchronized storage and backups remain operator responsibilities;
  M0 provides neither encryption nor backup/recovery tooling. Same-user path races are outside
  its trust model. Free-text data and explicit inspection output may contain private content.
- A committed review can outlive a lost response. Same-request recovery is mandatory;
  an error alone cannot establish that no write happened.
- Runtime authorization, worker isolation, effects/replay, coverage semantics, safe repair,
  provider data policy, spending limits and lab mutations remain later scoped decisions.
  They are not prerequisites for pure offline M0 and are not implicitly approved here.
- No generated execution, new runtime framework, new dependency, POM, UI, migration,
  telemetry service or deployment belongs to this implementation candidate.

## Explicit implementation approval checklist

All boxes remain unchecked until explicit owner authorization. Approval applies only to
revision `M0-SPEC-2026-10-23-v2` and its linked contracts/rationale, not the full roadmap.

- [ ] Designate one trusted local operator; accept attribution without multi-user identity
  assurance and confirm private local Windows storage under that operator's control.
- [ ] Approve whole-baseline review and mandatory re-review of all legacy flags, including
  inferred entries; approve unsupported-but-clear criteria and block unresolved/unknown ones.
- [ ] Approve the exact transition/lineage rules: revoke clears active, head is retained,
  no automatic fallback/direct reactivation, restored content needs a reviewed successor,
  and M0 cannot remove inherited requirements/criteria/evidence.
- [ ] Approve stable project/source-key UUID identities, strict immutable V1 field contracts,
  exact canonical JSON/SHA-256 rules and explicit parent/evidence participation in identity.
- [ ] Approve SQLite command/sequence/idempotency rules, 5-second lock wait and uncertain
  commit recovery; approve explicit no-overwrite local paths and separate offline CLI.
- [ ] Approve bounded legacy/native input limits, exact adapter fields, explicit metadata
  omission warnings, unknown-field rejection and safe all-or-nothing failures.
- [ ] Authorize the bounded implementation paths and AC-01..33 offline tests using the
  existing Python/Pydantic plus standard library, with no dependency installation assumed.
- [ ] Confirm exclusions: no runtime graph/RequirementBundle integration, live provider/
  browser/generated execution, infrastructure, publication, commit/push or deployment.
- [ ] Require actual passing named acceptance evidence and accurate handoff updates before
  declaring M0 complete; no ADR auto-approval or runtime finding closure from specification approval.

## Next action

Present this final proposal and checklist for explicit implementation approval. The
contracts, rationale, acceptance matrix and incremental plan are prepared; implementation
has not begun. The existing unsafe runner and repair path remain unchanged.
