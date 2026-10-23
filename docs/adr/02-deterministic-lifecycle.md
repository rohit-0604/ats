# ADR-02 — Deterministic lifecycle policy within LangGraph — PROPOSED

Status: **PROPOSED**. Preserved 2026-10-23 from the completed architecture decision review.
No implementation approval is recorded. Provisional agreement with direction does not approve these contracts.

ATS is currently a local Python/LangGraph CLI that extracts requirements, generates inline
Playwright tests, executes them locally and attempts repair. The design below is future work.
Evidence baseline: commit `4bc2093`; audit findings F04/F07/F08/F13 in
[AUDIT_FINDINGS](../AUDIT_FINDINGS.md). Examples are source-derived failure scenarios,
not newly executed tests. Previously consulted external/installed references are retained
for provenance, not re-researched or revalidated in this documentation pass.

Read the [decision index](README.md) for ordering and proposal corrections,
and [M0](../M0_VERSIONED_BASELINES.md) for the first bounded specification.

## A. Problem

The planner can choose actions whose prerequisites are not enforced consistently. Counters do not bound every costly action, and completion can bypass finalization.

## B. Current architecture

[planner_node()](../../app/core/react_controller.py#L125) combines hardcoded shortcuts, model-selected actions and fallback rules.

The generation counter reaches one but the guard requires two. Evaluation increments the main loop counter. The graph’s `done` edge goes directly to `END`, bypassing reporting.

Startup always performs inference, authentication and crawling, including extract-only mode. [Graph assembly](../../app/core/react_controller.py#L651)

## C. Failure scenario

The planner repeatedly requests generation without evaluation. Model calls continue while the evaluation budget remains unchanged.

Alternatively, the planner returns `done` before required evidence exists. The CLI can finish without communicating that the requested work was incomplete.

## D. Alternatives

| Approach | Benefit | Limitation |
|---|---|---|
| Add more planner prompt instructions | Very small change | Model compliance cannot enforce permissions or budgets |
| Replace LangGraph with a fixed procedural pipeline | Simple execution model | Discards useful checkpoints and requires migration |
| Keep LangGraph; centralize deterministic transition policy | Preserves useful code and makes legality testable | Requires explicit state and transition contracts |

## E. Proposed decision and rationale

Retain LangGraph. Implement a small **pure lifecycle policy** that determines allowed actions and mandatory transitions.

The model may rank permitted recovery options. It cannot bypass review, increase budgets, execute an unapproved artifact, or declare success.

This reduces model calls and unpredictability in routine stages. It adds explicit policy code, but makes failures easier to reproduce. The trade-off is less flexible recovery until new actions are deliberately supported.

## F. Implementation design and migration

Proposed interfaces:

```text
allowed_actions(state, policy, evidence) -> AllowedActions
validate_transition(state, action, evidence) -> Decision
apply_outcome(state, action_result) -> NewState
```

Separate:

- **Phase:** extraction, review, generation, execution, assessment.
- **Lifecycle status:** running, waiting for review, completed, blocked, failed, cancelled.
- **Assessment:** observed results, suspected defects, incomplete or unknown evidence.

“Completed” must not mean “the application satisfies its requirements.”

Enforce prerequisites both when selecting an action and immediately before its effect. This protects against stale state between planning and execution.

Reserve budgets before dispatch. Track model calls, retries, generation attempts, execution attempts and deadlines separately. An interrupted provider request can still incur cost; unresolved usage must remain unknown or conservatively reserved.

All normal terminal paths pass through a finalizer. Recovery handles abrupt process death that cannot execute that finalizer.

Mode contracts become explicit. Proposed extract-only behavior: no target discovery/authentication unless separately requested.

Migration proceeds by putting the existing planner behind policy checks, then replacing routine planner decisions with deterministic edges. Version graph state. Do not automatically resume incompatible legacy checkpoints.

## G. Verification

Use stubbed model/tool results to test:

- Every allowed and forbidden transition.
- Repeated generation, repair and malformed planner responses.
- Missing approval and stale artifact revisions.
- Budget exhaustion before dispatch.
- Cancellation during waiting, provider calls and execution.
- Empty extraction/generation.
- Every CLI mode’s permitted effects.
- Finalization after failure and restart.
- A model-selected `done` with outstanding work.

Completion evidence is the tested transition matrix and named terminal outcomes—not merely reaching `END`.

## H. Reconsideration triggers

Allow more model-driven planning only if equal-budget benchmarks show better recovery without increased unsafe transitions, cost or unpredictable latency.

## I. Engineering understanding

This demonstrates finite-state machines and the distinction between decision suggestions and executable authority.

Interview explanation:

> “LangGraph runs the workflow, but ordinary policy code decides which transitions are legal. The model cannot override prerequisites or budgets.”

## Dependencies and open boundaries

Consumes ADR-01 approvals, ADR-03 artifact identity and ADR-06 effect records. Pure policy tests can precede worker integration; execution still requires ADR-04. Exact mode and CLI exit semantics remain open.
