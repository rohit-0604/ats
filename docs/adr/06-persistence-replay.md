# ADR-06 — Persistence, checkpoints, replay and execution evidence — PROPOSED

Status: **PROPOSED**. Preserved 2026-10-23 from the completed architecture decision review.
No implementation approval is recorded. Provisional agreement with direction does not approve these contracts.

ATS is currently a local Python/LangGraph CLI that extracts requirements, generates inline
Playwright tests, executes them locally and attempts repair. The design below is future work.
Evidence baseline: commit `4bc2093`; audit findings F02/F08/F15/F17 in
[AUDIT_FINDINGS](../AUDIT_FINDINGS.md). Examples are source-derived failure scenarios,
not newly executed tests. Previously consulted external/installed references are retained
for provenance, not re-researched or revalidated in this documentation pass.

Read the [decision index](README.md) for ordering and proposal corrections,
and [M0](../M0_VERSIONED_BASELINES.md) for the first bounded specification.

## A. Problem

Graph checkpoints, filesystem writes, subprocesses and application-side effects do not commit atomically.

Resuming saved graph state can repeat work or associate old evidence with new code.

## B. Current architecture

[build_graph()](../../app/core/react_controller.py#L651) creates a SQLite checkpointer. [resume_pipeline()](../../app/core/react_controller.py#L771) invokes the graph with saved thread state. Shared spec and result files are overwritten.

The installed LangGraph interrupt contract explicitly states that resumption starts the node again and re-executes its logic. `.venv/Lib/site-packages/langgraph/types.py` (local installed evidence from the assessment; not tracked)

Run listing also depends directly on an incorrect internal checkpoint column name.

## C. Failure scenario

A browser submits an order. The target accepts it. ATS crashes before recording completion.

On resume, the node executes again and submits a second order.

A durable checkpoint does not tell ATS whether the first external action happened.

## D. Alternatives

| Approach | Benefit | Limitation |
|---|---|---|
| Disable resume and restart every run | Simple | Restart can still repeat external mutations; loses useful progress |
| Treat checkpoints as the sole authoritative record | Smallest persistence design | Cannot reconcile independent effects |
| Application records plus checkpoints and effect identities | Explicit recovery and evidence provenance | Requires effect state and reconciliation |
| Full distributed workflow platform | More operational capabilities | Unnecessary before workload and reliability needs justify migration |

## E. Proposed decision and rationale

Use an application-owned transactional store for baselines, approvals, run attempts and effect records. Keep LangGraph checkpoints for orchestration progress.

Start with SQLite on one supported local host. Keep checkpoint storage separate from application tables rather than modifying checkpointer internals.

This introduces a consistency boundary, but makes it explicit. The application store is authoritative for whether an effect may start or its result may be accepted.

SQLite transactions do not automatically make filesystem publication or external requests atomic. Its durability also depends on filesystem and hardware behavior; crash testing remains necessary. [SQLite atomic-commit documentation](https://www.sqlite.org/atomiccommit.html)

## F. Implementation design and migration

Give each effect a stable identity derived from the run attempt, action and input revision.

Typical lifecycle:

`PLANNED → STARTED → SUCCEEDED | FAILED | CANCELLED | UNCERTAIN`

Before dispatch, transactionally reserve the effect and budget. Persist output evidence before marking success.

For repeat delivery:

- Reuse a verified completed result.
- Reattach to known running work where supported.
- Reconcile expired ownership before launching replacement work.
- Mark ambiguous target mutations `UNCERTAIN`.
- Never assume lease expiry proves a worker or browser stopped.

Fencing tokens can reject stale result publication. They cannot undo a request already sent to the target.

Use idempotency keys where the target supports them. Otherwise require disposable test data, a verified reset, or human reconciliation before repeating state-changing work.

Files are immutable per attempt. Publish via a staged write and completed manifest; recovery distinguishes incomplete artifacts from complete evidence.

Graph state carries references and secret handles, not raw credentials. Refuse unsupported checkpoint versions. Preserve legacy databases and reports for read-only investigation; do not silently rewrite or deserialize arbitrary imported checkpoint data.

## G. Verification

Inject crashes:

- Before reservation.
- After reservation but before dispatch.
- After target mutation but before acknowledgment.
- After artifact creation but before success recording.
- During review persistence.
- During cancellation and worker replacement.

Verify that recovery neither invents success nor silently repeats an uncertain mutation. Test duplicate delivery, stale worker results, disk-full errors, corrupt/missing artifacts and backup restoration.

## H. Reconsideration triggers

Move to PostgreSQL or a dedicated durable-job system when multiple independent writers, high availability, remote workers or measured contention exceed the single-host design.

## I. Engineering understanding

This demonstrates idempotency, transactional boundaries and reconciliation.

Interview explanation:

> “We do not promise exactly-once execution across a browser and an external application. We identify effects, reuse completed work and expose ambiguous outcomes instead of repeating them blindly.”

## Dependencies and open boundaries

The M0 subset is baseline/review storage only; effect ledgers, leases, workers and checkpoint migration are later work. Supported filesystem, retention/backup policy and concurrency assumptions must be settled before operational use.
