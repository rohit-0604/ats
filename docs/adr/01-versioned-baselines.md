# ADR-01 — Versioned requirements, acceptance criteria, and oracle authority — PROPOSED

Status: **PROPOSED**. Preserved 2026-10-23 from the completed architecture decision review.
The full ADR remains PROPOSED. The user subsequently explicitly approved only its
M0 subset; that offline slice is [implemented and verified](../M0_VERIFICATION.md).
This does not approve broader runtime integration or the complete ADR contracts.

ATS is currently a local Python/LangGraph CLI that extracts requirements, generates inline
Playwright tests, executes them locally and attempts repair. The design below is future work.
Evidence baseline: commit `4bc2093`; audit findings F01/F04/F06 in
[AUDIT_FINDINGS](../AUDIT_FINDINGS.md). Examples are source-derived failure scenarios,
not newly executed tests. Previously consulted external/installed references are retained
for provenance, not re-researched or revalidated in this documentation pass.

Read the [decision index](README.md) for ordering and proposal corrections,
and [M0](../M0_VERSIONED_BASELINES.md) for the first bounded specification.

## A. Problem

ATS does not maintain a reliable distinction between:

- What a source document says.
- What the model inferred.
- What a reviewer approved.
- What a generated test actually checks.

[Requirement](../../app/schemas.py#L95) combines mutable text, confidence, source references, and approval booleans. It has no separately versioned acceptance criteria.

## B. Current architecture

Extraction creates `Requirement` objects, performs filtering and deduplication, then returns a bundle. Saved bundles and noninteractive extraction can automatically approve nonrejected requirements in [node_agent_a()](../../app/core/react_controller.py#L359).

Generation consumes this bundle. Repair later receives test code and observations without the original acceptance criteria.

## C. Failure scenario

Two requirements differ only by negation:

- Administrators may access reports.
- Guests must not access reports.

Token similarity can discard a distinct requirement. Separately, an inferred criterion can become approved through noninteractive execution without an explicit business decision.

The resulting test suite may appear complete against an already-damaged baseline.

## D. Alternatives

| Approach | Benefit | Limitation |
|---|---|---|
| Keep mutable models; add validation and audit fields | Smallest immediate patch | Every caller must correctly preserve history and approval validity |
| Immutable revision snapshots plus separate review records | Explicit provenance, reliable comparisons and approval invalidation | Introduces revision handling and storage |
| Full event-sourced requirements system | Complete reconstruction from events | Excessive complexity for the current product |

## E. Proposed decision and rationale

Use **immutable snapshots and separate review records**, backed initially by ordinary transactional storage.

A requirement expresses the business need. A criterion expresses one reviewable expected behavior. Scenarios exercise that criterion.

This adds some review and storage overhead, but requires no extra model calls and provides a stable foundation for reporting, repair, POM generation, and evaluations. Full event sourcing is unnecessary.

Approval establishes the project’s accepted expectation. It does not prove the expectation is universally correct.

## F. Implementation design and migration

Introduce versioned contracts for:

- `SourceEvidence`: document identity/hash, location, excerpt or human decision reference, provenance status.
- `RequirementRevision`: stable identity, original text, revision, source references.
- `CriterionRevision`: requirement reference, preconditions, action, expected outcome, origin, support status.
- `BaselineRevision`: the exact requirement/criterion set selected for a project.
- `ReviewDecision`: subject digest, decision, actor/context, timestamp, sequence and supersession.

Important rules:

- Extraction produces drafts, never approval records.
- Inferred and unsupported requirements remain visible.
- Changing expected behavior creates a new revision and requires new approval.
- Historical runs remain attached to their original baseline.
- A newer approved baseline becomes active for future runs; historical evidence is not rewritten.
- A hash detects content differences, not trusted authorship.
- Approval records must originate through a trusted review boundary, not model-generated JSON.

Use immutable nested structures, not merely `frozen=True`: Pydantic explicitly documents that a frozen model can still contain mutable dictionaries. [Pydantic immutability guidance](https://docs.pydantic.dev/latest/concepts/models/#faux-immutability)

Legacy imports preserve original IDs and text but treat existing approval flags as **unverified legacy claims**. Missing provenance stays missing; migration must not invent source evidence.

## G. Verification

Acceptance evidence must demonstrate:

- Negation, roles, thresholds and distinct scenarios survive import.
- Changing one expected value changes the revision digest.
- Old approval cannot authorize the changed revision.
- Unknown, inferred and unsupported items remain identifiable.
- Nested data cannot mutate an accepted snapshot through supported APIs.
- Legacy `approved=True` never creates a trusted approval.
- Duplicate IDs and conflicting review commands fail explicitly.
- Historical snapshots remain retrievable after supersession.

## H. Reconsideration triggers

Reconsider the storage and review model if multiple organizations require delegated approval, legal signatures, cross-system specification synchronization, or large collaborative editing workflows.

## I. Engineering understanding

This demonstrates separation of concerns, versioning, provenance and authorization.

Interview explanation:

> “We separated the expected behavior from generated tests. Every run references an approved specification revision, so a repair cannot silently redefine success.”

## Dependencies and open boundaries

ADR-06 supplies transactional review persistence; M0 implements only that narrow part
of ADR-01/06. The user resolved reviewer authority, whole-baseline granularity and
legacy re-review for M0. Broader runtime integration remains proposed.
