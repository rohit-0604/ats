# ADR-03 — Artifact identity, approval and result reconciliation — PROPOSED

Status: **PROPOSED**. Preserved 2026-10-23 from the completed architecture decision review.
No implementation approval is recorded. Provisional agreement with direction does not approve these contracts.

ATS is currently a local Python/LangGraph CLI that extracts requirements, generates inline
Playwright tests, executes them locally and attempts repair. The design below is future work.
Evidence baseline: commit `4bc2093`; audit findings F03/F04/F05/F06 in
[AUDIT_FINDINGS](../AUDIT_FINDINGS.md). Examples are source-derived failure scenarios,
not newly executed tests. Previously consulted external/installed references are retained
for provenance, not re-researched or revalidated in this documentation pass.

Read the [decision index](README.md) for ordering and proposal corrections,
and [M0](../M0_VERSIONED_BASELINES.md) for the first bounded specification.

## A. Problem

ATS does not reliably identify the executable code that was reviewed or map its results to approved criteria.

## B. Current architecture

Generation derives `test_id` from `req_id`, limiting multiple scenarios. The writer groups all test blocks by model-supplied filename, deletes existing specs and transforms code while writing. [write_spec_files()](../../app/core/evaluator_engine.py#L67)

Results are matched by title or code substring, nested suites are missed, and coverage uses a count rather than membership in the approved baseline. [parse_results()](../../app/core/evaluator_engine.py#L260), [build_report()](../../app/core/evaluator_engine.py#L400)

## C. Failure scenario

Two tests share a title. A passing result is assigned to the wrong requirement.

A rejected test shares a file with an approved test. Filtering a list of test IDs does not prevent that file’s top-level code or imported helper from executing.

Even the reviewed bytes may differ from execution because the writer replaces `networkidle` after review.

## D. Alternatives

| Approach | Benefit | Limitation |
|---|---|---|
| Improve title matching and filter approved tests | Small patch | Ambiguous identities and shared executable dependencies remain |
| Explicit test IDs plus a complete artifact manifest | Stable mapping and revision-bound approval | Requires manifest construction and reconciliation |
| New custom reporter immediately | Maximum output control | Additional maintained code before proving it is necessary |

## E. Proposed decision and rationale

Use an immutable **execution manifest** with application-owned test identities and complete executable-bundle identity.

Start with the existing JSON reporter. The installed Playwright 1.58.2 implementation emits annotations, project identity, expected status and retry records. `playwright_project/node_modules/playwright/lib/reporters/json.js` (local installed evidence from the assessment; not tracked)

This avoids a new reporter framework while removing title dependence. Manifest processing adds modest CPU/storage work; its main complexity is precise semantics.

## F. Implementation design and migration

The manifest binds:

- Project and baseline digest.
- Scenario and test IDs.
- Explicit criterion mappings.
- Final artifact paths and byte hashes.
- Shared fixtures/helpers.
- Trusted runner configuration and dependency-lock identity.
- Selected browser/project configuration.
- Approval and execution-policy references.

All transformations occur **before** hashing and review. Materialization must preserve those exact bytes.

Approval is for the closed executable bundle. If rejected code remains inside a shared file, rebuild the bundle and obtain approval; do not rely on skipping its named test.

Use an `ats.test_id` annotation assigned by ATS. Treat reporter annotations as untrusted observations and cross-check them against the manifest. They provide identity, not proof of honest assertions.

Result identity includes run attempt, artifact digest, test ID, browser/project and retry index. Preserve all attempts; a retry pass remains distinguishable from a consistently passing test.

Reconciliation must:

- Traverse nested suites.
- Reject unknown/conflicting identities.
- Identify missing planned tests.
- Separate skipped, failed, interrupted, flaky and infrastructure outcomes.
- Preserve runner-level errors.
- Keep unsupported criteria in the agreed baseline accounting.
- Avoid vacuous success for empty plans.
- Never count an expected failure as positive requirement evidence merely because the runner accepts it.

Use separate measures for planned scenario coverage, execution completeness and supporting evidence. None is universal proof of requirement satisfaction.

Legacy reports remain historical evidence. Do not manufacture stable identities from title matches and relabel them as verified.

## G. Verification

Required cases include duplicate titles, nested suites, multiple scenarios, unknown IDs, missing results, retries, skipped/expected-failure tests, runner errors, altered shared fixtures and changed artifact bytes.

Path tests must include traversal, absolute/UNC paths, Windows reserved names, alternate data streams, case collisions and reparse points. Actual filesystem containment also belongs at materialization time; string validation alone is insufficient.

The published result set must reconcile exactly against the planned set, with discrepancies explicit.

## H. Reconsideration triggers

Add a custom reporter if the pinned JSON format cannot carry required identities/evidence or becomes operationally fragile. Expand mappings beyond one primary criterion per scenario when explicit assertion-level attribution is justified.

## I. Engineering understanding

This demonstrates referential integrity, content addressing and reconciliation.

Interview explanation:

> “We approve a specific executable bundle and reconcile every reported result against its manifest. Names are presentation; identities and revisions determine attribution.”

## Dependencies and open boundaries

Consumes ADR-01 baseline/review identity and ADR-06 attempt records. ADR-04 must enforce the manifest at execution. Coverage denominators, unsupported-item treatment and scenario-to-criterion attribution need explicit approval.
