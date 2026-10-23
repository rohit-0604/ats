# M0 - Versioned Baselines and Review Records

Status: **PROPOSED - awaiting specification approval and implementation authorization**.
Preserved 2026-10-23 from the completed decision review. No M0 application modules,
fixtures or regression tests exist as a result of this documentation task.

This is the authoritative proposed M0 scope. It supersedes the *ordering* of the older
first milestone (offline eligibility/result reconciliation), which remains necessary
follow-up work in [ROADMAP](ROADMAP.md). Its proposed implementation covers a narrow subset of
[ADR-01](adr/01-versioned-baselines.md) and [ADR-06](adr/06-persistence-replay.md).
The [decision register](DECISIONS.md) distinguishes accepted constraints from proposals.

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
| `BaselineDraft` | Project identity, preserved requirements, criterion candidates, source references and unresolved issues |
| `CriterionRevision` | Stable identity, requirement reference, preconditions, action, expected outcome, origin and support status |
| `BaselineSnapshotV1` | Schema version, project/baseline identity, parent digest, complete immutable content and digest |
| `ReviewDecisionV1` | Subject digest, approve/reject/revoke decision, trusted caller context, sequence, request ID and timestamp |
| `EffectiveReview` | Pending, approved, rejected, revoked or superseded; supporting decision reference |
| `ImportResult` | Draft plus explicit warnings about legacy approvals, missing evidence and unsupported fields |

A draft may contain unresolved criteria. Approval requires a sufficiently specified expectation and source evidence or an explicit human-authored decision reference.

“Unsupported for automation” remains separate from whether the business expectation is approved.

## Interfaces

```text
import_legacy_bundle(raw, project_id) -> ImportResult
validate_draft(raw) -> BaselineDraft | ValidationErrors
freeze_baseline(draft, parent_digest) -> BaselineSnapshotV1
store_snapshot(snapshot) -> StoredSnapshot
record_review(subject_digest, decision, caller_context,
              expected_sequence, request_id) -> ReviewDecisionV1
get_effective_review(project_id, digest) -> EffectiveReview
```

The caller context comes from the trusted command boundary. It is not accepted from imported requirement JSON.

For the initial single-operator implementation, trust rests on the local operator and filesystem permissions. This is not multi-user identity assurance and does not defend against an administrator modifying the database.

## Persistence and canonicalization

Use one application-owned SQLite database at an explicitly selected local path:

- Immutable snapshots.
- Append-only review decisions.
- Current project baseline/review sequence.

Record a review decision and update the active baseline in one transaction. Use an expected sequence to reject stale concurrent decisions.

A repeated request ID with identical content returns the original decision. Reusing it with different content fails.

Define canonical serialization precisely:

- UTF-8 JSON.
- Sorted object keys and fixed separators.
- No non-finite numbers.
- Declared ordering for identity-based collections.
- Preserve meaningful text and ordered scenario steps.
- Exclude the digest field itself from its calculation.

Do not normalize away negation, whitespace inside meaningful text, or distinct source records.

Recompute the digest when loading a snapshot. A mismatch is an integrity error, not an opportunity to silently repair the record.

## Security invariants

1. Imported approval booleans never authorize anything.
2. Freezing a snapshot does not approve it.
3. Review targets exactly one project and baseline digest.
4. Content changes require a new snapshot and review.
5. Models cannot submit review decisions.
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
| `tests/fixtures/baselines/` | Small synthetic, nonsecret fixtures |

Keep the current `RequirementBundle` and runtime graph unchanged during M0. Update the project decision/status documents only as part of the approved implementation and its verified results.

## Acceptance tests

- **M0-AC-01:** Legacy bundles with `approved=True`, including inferred entries, import as untrusted drafts.
- **M0-AC-02:** Positive and negative requirements both survive.
- **M0-AC-03:** Multiple criteria under one requirement remain distinct.
- **M0-AC-04:** Missing expectations prevent approval.
- **M0-AC-05:** Unsupported but well-defined criteria remain visible.
- **M0-AC-06:** Unknown schema versions, duplicate IDs and invalid references fail.
- **M0-AC-07:** Same content produces the same digest under the declared canonicalization.
- **M0-AC-08:** A changed threshold produces a different digest.
- **M0-AC-09:** An approval for the prior digest does not apply to the new digest.
- **M0-AC-10:** Foreign-project review requests fail.
- **M0-AC-11:** Repeated identical review commands are idempotent.
- **M0-AC-12:** Conflicting or stale commands fail without partial writes.
- **M0-AC-13:** Revocation and supersession preserve history.
- **M0-AC-14:** A simulated failure before transaction commit leaves no partial approval.
- **M0-AC-15:** A committed review survives reopening the database.
- **M0-AC-16:** Tampered snapshot content produces an integrity error.
- **M0-AC-17:** Importing the modules creates no directories, network calls or provider initialization.


Use `unittest`, temporary directories and the already-installed Pydantic initially. Proposed verification command:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py"
```

That command is **proposed, not currently a passing repository gate**.

## Incremental sequence

1. Approve contract semantics and trust assumptions.
2. Add synthetic failure fixtures and acceptance tests.
3. Implement immutable contracts and deterministic serialization.
4. Implement the legacy import adapter.
5. Implement transactional review storage.
6. Add the offline command interface.
7. Run acceptance tests and review the diff for effects/secrets.
8. Update decision status, limitations and the next bounded task.

## Definition of done

The operator can prepare, review and inspect a versioned baseline offline; all named acceptance cases pass; no legacy approval is promoted implicitly; and verified commands/results are documented.

M0 does **not** fix the old writer, unsafe repair, planner bypasses, runner isolation or result accounting. Those findings remain open until the new authority is integrated and their own acceptance tests pass. Existing runtime execution remains unapproved.

## Product-owner decisions genuinely needed

| Question | Recommended starting decision |
|---|---|
| Who can approve expected behavior? | One explicitly designated local operator for M0; model output has no authority |
| Must legacy “approved” requirements be reviewed again? | Yes; retain them as historical claims only |
| Whole-baseline or per-criterion approval initially? | Whole-baseline approval for M0; add granular review only when needed |
| Can an approved baseline contain unsupported criteria? | Yes, provided expectations are clear and unsupported status remains visible |
| Can repairs change business expectations? | Only through a new baseline decision, never ordinary repair approval |
| What application mutations will later be permitted? | Owned disposable lab data first; broader target actions require separate policy |
| What are the spending and recovery limits? | Decide before live worker/provider integration; not required to implement M0 |

## Specification approval checklist and remaining detail

The assumptions below are proposed, not silently accepted product decisions:

- One trusted local operator, whole-baseline approval, mandatory re-review of legacy
  approval claims, no runtime integration, and unsupported but clear criteria retained.
- Source evidence or a human decision reference establishes provenance. Hashing alone
  neither authenticates a reviewer nor establishes that a requirement is correct.
- Snapshot content and review state are separate: rejection/revocation never rewrites
  the snapshot. Freezing creates a pending subject; only a trusted review command may
  approve, reject or revoke it. New content starts pending even if its parent was approved.
- Approval of a successor changes the active baseline transactionally; historical
  approvals remain visible. Before coding, specify revocation of the active baseline,
  whether re-approval is permitted, and whether superseded baselines may be reactivated.
  Do not silently fall back to an older approval on revocation.
- Before implementation, fix the exact V1 field constraints, enum values, stable-ID
  generation, identity-collection order, digest algorithm, and timestamp inclusion rule
  in a reviewed contract/test table. The canonicalization requirements above are binding
  proposal requirements, but a byte-exact wire schema is not claimed to exist yet.
- Resolve import size limits and unknown-field treatment without silently discarding
  source records. Never log input bodies on validation failure. General free text can
  still contain sensitive user material; absence of credential fields is not a secret scanner.
- SQLite error categories must distinguish invalid input, unsupported version, unknown
  subject, project mismatch, stale sequence, request-ID conflict, integrity and storage
  failure. All failures must leave approval unchanged and return an explicit non-success.
- No database is created at import time. Runtime storage stays excluded from Git;
  synthetic fixtures must contain no real SRS, account or target evidence.

These items expose unresolved precision in the proposal; they are not new approved
architecture decisions. Agree them during M0 specification approval and implementation
preparation. Any change in scope must be recorded before implementation starts.

## Next action

Obtain M0 specification approval, confirm its trust/review semantics, and prepare the
bounded implementation plan. Do not begin implementation based on permission to save
this document. The existing unsafe runner and repair path remain unchanged.
