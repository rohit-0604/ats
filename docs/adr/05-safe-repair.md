# ADR-05 — Failure classification and safe repair — PROPOSED

Status: **PROPOSED**. Preserved 2026-10-23 from the completed architecture decision review.
No implementation approval is recorded. Provisional agreement with direction does not approve these contracts.

ATS is currently a local Python/LangGraph CLI that extracts requirements, generates inline
Playwright tests, executes them locally and attempts repair. The design below is future work.
Evidence baseline: commit `4bc2093`; audit findings F01/F14/F16 in
[AUDIT_FINDINGS](../AUDIT_FINDINGS.md). Examples are source-derived failure scenarios,
not newly executed tests. Previously consulted external/installed references are retained
for provenance, not re-researched or revalidated in this documentation pass.

Read the [decision index](README.md) for ordering and proposal corrections,
and [M0](../M0_VERSIONED_BASELINES.md) for the first bounded specification.

## A. Problem

ATS confuses an execution symptom with the cause of a failure, then permits the repair process to modify the test oracle.

An oracle is the rule deciding what counts as correct behavior.

## B. Current architecture

Error strings become categories such as timeout or assertion failure. The [active repair prompt](../../prompts/agent_c_repair_v1.txt#L25) explicitly allows observed values to replace expected values. The [embedded fallback](../../app/agents/repair_agent.py) contains equivalent instructions.

[_build_repair_context()](../../app/agents/repair_agent.py#L148) omits approved criteria. [repair_batch()](../../app/agents/repair_agent.py#L196) replaces code in place and counts accepted rewrites as successful repairs.

## C. Failure scenario

The approved criterion requires four feature cards. The application renders three.

A test correctly fails. Repair changes the expected count to three—or replaces the count with heading visibility. The application defect disappears from the report without being fixed.

A timeout is similarly ambiguous: it may indicate a stale locator, failed authentication, slow infrastructure, or missing application behavior.

## D. Alternatives

| Approach | Benefit | Limitation |
|---|---|---|
| Stop all automated repair | Safest baseline; easy to understand | Leaves substantial manual diagnosis |
| Generate repair proposals requiring review | Useful assistance while retaining authority | Review effort and slower turnaround |
| Automatically apply a restricted class of repairs | Potentially lower effort | “Locator-only” does not reliably imply semantic preservation |

## E. Proposed decision and rationale

Begin with **evidence-backed classification hypotheses and reviewed repair proposals**.

Do not add a separate adjudication agent as an authority. A model can suggest causes and evidence to gather, but uncertainty must remain explicit.

This sacrifices some autonomy and latency for fidelity. It also creates labeled examples needed to justify later automation.

## F. Implementation design and migration

Separate these records:

- `Observation`: actual error, browser state, response and environment evidence.
- `Diagnosis`: suspected application/test/environment cause, alternatives and evidence references.
- `RepairProposal`: original artifact digest, proposed digest, diff, affected tests and criterion references.
- `ReviewDecision`: acceptance/rejection of that specific proposal.

A repair receives the immutable baseline, scenario, original code, current observations and authorized environment.

Rules:

- Preserve the original artifact and failed result.
- Changing expected behavior requires a new requirement-baseline decision, not a repair approval.
- Every code change creates a new bundle revision and invalidates prior execution approval.
- Changes to shared fixtures expand the affected-test set.
- Static checks reject obvious weakening, skipped assertions and vacuous checks.
- Static checks cannot certify general semantic equivalence.
- Uncertain cases abstain.
- Initial application findings are “suspected” until supported by the defined review/evidence process.

Update both active and fallback prompts during migration. Quarantine old learned repairs; they lack sufficient before/after provenance and assertion-preservation evidence.

## G. Verification

Use paired known-good and seeded-defect builds:

- A stale locator can be repaired while the original criterion still holds.
- A real application defect remains detectable after attempted repair.
- Count-to-visibility substitution is rejected.
- Empty loops, swallowed assertion errors and test skipping are rejected.
- Authentication/environment failures are not reported as confirmed business defects.
- A locator change targeting a different element requires review.
- Original code, proposed code and all executions remain inspectable.

Measure valid test repairs and retained defect sensitivity separately. A passing rewritten test alone is not successful repair evidence.

## H. Reconsideration triggers

Permit narrowly automated repair only after a held-out corpus establishes acceptable error rates and the proposed edit class has a defensible semantic boundary.

## I. Engineering understanding

This demonstrates diagnosis under uncertainty and preservation of the test oracle.

Interview explanation:

> “A failing assertion may be the test working correctly. We preserve the expected behavior and treat repair as a reviewed hypothesis, not a command to make the suite green.”

## Dependencies and open boundaries

Consumes ADR-01 oracle authority, ADR-03 artifacts, ADR-04 controlled evidence and ADR-06 history. Diagnosis labels, reviewer authority and any future automated repair class require measured validation and separate approval.
