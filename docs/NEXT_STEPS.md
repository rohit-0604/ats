# Next steps and session handoff

## Current scope and stop point

C23 requests implementation and local progress commits. The completed C20-C22 reviews
and refactor are saved in `569d839`. [M2-R v1](M2R_DURABLE_REVIEW.md) now defines proposed
contracts, eight decisions and 30 offline acceptance families. The user explicitly approved
that exact v1 and all decisions/acceptance for offline implementation/tests and local commits.
Implement, verify and checkpoint only offline
M2-R. No providers, agents, installs, generated execution, later milestones or push.
See [current status](CURRENT_STATE.md), [index](README.md) and
[authorization](DECISIONS.md#accepted-constraints).

M0/M1/M2 are complete offline. M2-R v1 is approved for implementation, not yet implemented. The
original bounded recommendation below remains its scope reference; execution/product
readiness is unproven. Do not reopen completed V1 contracts.

## Next bounded specification - unchanged recommendation

**Exact next bounded task recommendation (not started or automatically authorized):**
prepare an offline specification titled **M2-R - Durable Plan and Whole-Package Review**.
On a new scoped request:

1. Read current V1 contracts, M2 verification, domain compatibility constraints and
   applicable FIT gates. Establish acceptance IDs and scope before any implementation.
2. Specify separate exact plan and whole-package review subjects, project/parent digest
   binding, trusted local single-operator decisions, append-only history/revocation,
   idempotent command identity, transaction/crash/lost-acknowledgment behavior and
   handling of imported/forged/stale review claims. Compare a focused review store with
   reusing M0 persistence helpers without changing M0 schemas or canonical bytes.
3. Define a new effective-review assessment using fresh M0 state plus plan/package
   decisions and policy version. State baseline/plan/package supersession/revocation
   effects, snapshot consistency and cross-store read/race limits. It grants no dispatch
   permission; atomic dispatch/revocation and budget reservations belong to M4.
4. Initially cover fully mapped packages. Specify malformed/mismatched subjects, review
   independence, revoked/stale parents, duplicate/conflicting decisions, crash/replay,
   lost acknowledgment, exact bytes and preserved V1 non-authorizing assessments as
   offline acceptance families. Include review rendering/input safety and trust limits.
5. Record M3/M4/M5 consumption/compatibility, assumptions, alternatives, applicable
   FIT-01/02/03/06/07/08/13 evidence plans and unresolved choices; stop at specification
   review/implementation approval. Do not implement or commit under specification scope.

Explicit non-goals: manual-case lifecycle, subset/impact contracts, auth/environment
services, coverage engine, framework profiles/IR/runner adapters, model routing/gateways,
UI/telemetry platform, workers, live execution or changes to completed M0/M1/M2.
These retain their own CAP IDs, dependencies and measurable future acceptance. MANUAL-first
remains an explicit product-priority alternative, not an implicit scope change.

## Historical handoffs

These links preserve older section anchors for readers and existing references.
Their old stop points, Git state and permissions are historical, not active guidance.

| Prior section | Historical record |
| --- | --- |
| <a id="current-stop-point-consolidated-architecture-assurance-review"></a>Current stop point: consolidated architecture assurance review | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-current-stop-point-consolidated-architecture-assurance-review) |
| <a id="current-stop-point-domain-review-and-updated-requirements"></a>Current stop point: domain review and updated requirements | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-current-stop-point-domain-review-and-updated-requirements) |
| <a id="current-handoff-m2-complete-stop-after-local-checkpoint"></a>Current handoff: M2 complete; stop after local checkpoint | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-current-handoff-m2-complete-stop-after-local-checkpoint) |
| <a id="current-task-and-stop-point-m2-specification-approval"></a>Current task and stop point: M2 specification approval | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-current-task-and-stop-point-m2-specification-approval) |
| <a id="verified-baseline"></a>Verified baseline | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-verified-baseline) |
| <a id="git-and-authorization"></a>Git and authorization | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-git-and-authorization) |
| <a id="implemented-api-entry-points"></a>Implemented API entry points | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-implemented-api-entry-points) |
| <a id="resume-without-chat-history"></a>Resume without chat history | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-resume-without-chat-history) |
| <a id="remaining-risks-and-next-dependency"></a>Remaining risks and next dependency | [Preserved](history/CONTEXT_BEFORE_2026-10-25.md#next-remaining-risks-and-next-dependency) |
