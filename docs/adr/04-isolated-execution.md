# ADR-04 — Isolated generated-code execution — PROPOSED

Status: **PROPOSED**. Preserved 2026-10-23 from the completed architecture decision review.
No implementation approval is recorded. Provisional agreement with direction does not approve these contracts.

ATS is currently a local Python/LangGraph CLI that extracts requirements, generates inline
Playwright tests, executes them locally and attempts repair. The design below is future work.
Evidence baseline: commit `4bc2093`; audit findings F02/F03/F09/F10/F11 in
[AUDIT_FINDINGS](../AUDIT_FINDINGS.md). Examples are source-derived failure scenarios,
not newly executed tests. Previously consulted external/installed references are retained
for provenance, not re-researched or revalidated in this documentation pass.

Read the [decision index](README.md) for ordering and proposal corrections,
and [M0](../M0_VERSIONED_BASELINES.md) for the first bounded specification.

## A. Problem

Generated TypeScript is executable untrusted input. Current execution gives it access to the developer host and inherited environment.

## B. Current architecture

[run_playwright()](../../app/core/evaluator_engine.py#L106) launches local Node with `os.environ`.

Authentication data also enters graph state, while discovery follows redirects without a complete destination boundary. [handle_auth()](../../app/core/auth_handler.py#L21), [_spider()](../../app/core/route_crawler.py#L111)

## C. Failure scenario

A generated spec imports a Node filesystem or networking API. It can read host-accessible files or contact a destination outside the authorized target.

Browser routing restrictions alone would not stop direct Node requests.

## D. Alternatives

| Approach | Benefit | Limitation |
|---|---|---|
| Disable execution; validate artifacts offline | Lowest immediate risk and operational cost | Cannot establish runtime behavior |
| Hardened container on a dedicated execution host | Familiar deployment and relatively low startup overhead | Requires careful host/kernel, filesystem and network threat analysis |
| Disposable VM or validated stronger sandbox | Stronger separation from the developer/control host | More provisioning, startup latency and operating cost |

## E. Proposed decision and rationale

**Keep generated execution unavailable until a worker boundary passes explicit tests.** Define a provider-independent worker contract now. Investigate a disposable Linux VM as the first reference environment, comparing it with a managed sandbox.

Do not select a vendor or claim the current machine supports the chosen virtualization approach without a focused compatibility test.

The additional operational complexity is justified by the severity of host access. It is not justified to add a scheduler fleet or Kubernetes before one worker is reliable.

## F. Implementation design and migration

A trusted controller submits an `ExecutionRequest` containing immutable artifact identity, target policy, limits and secret references.

The worker supervisor:

- Fetches approved artifacts through a narrow interface.
- Verifies hashes and execution authorization.
- Starts an isolated environment with no developer workspace or provider keys.
- Supplies only disposable, target-scoped credentials when necessary.
- Applies CPU, memory, process, filesystem, time and output limits.
- Enforces network policy outside generated code.
- Collects bounded evidence and records cleanup results.

Apply target policy to discovery, authentication, browser subrequests, direct HTTP, redirects and retries. Allowlist actual destinations, not hostname substrings.

Package installation, test discovery and configuration loading can execute code. They require the same boundary; `playwright --list` is not inherently a safe host-side validation step.

Path containment needs fresh per-attempt directories, no shared mutable specs, collision checks and protection against symlink/reparse-point races.

The old local runner must have no automatic fallback role in the approved execution path. Migration introduces the worker interface and a deny-by-default implementation before enabling a validated worker.

Hashes and trusted transport protect artifact identity. They cannot prove that generated assertions are semantically honest.

## G. Verification

Before enabling even controlled generated execution, demonstrate:

- Host/provider secrets and unrelated files are inaccessible.
- Direct Node and browser attempts to reach denied destinations fail.
- Redirect, DNS-resolution and private-address cases obey policy.
- Child processes are terminated on timeout/cancellation.
- Resource/output limits work.
- Cross-run artifacts and credentials do not leak.
- Tampered manifests/artifacts are rejected.
- Worker failure and cleanup failure produce explicit outcomes.

Tests should use owned fixtures and synthetic secrets.

## H. Reconsideration triggers

Choose a different sandbox when compatibility, isolation testing, concurrency, startup latency or measured operating cost makes the initial worker unsuitable.

## I. Engineering understanding

This demonstrates trust boundaries and least privilege.

Interview explanation:

> “Generated tests are treated like untrusted programs. Validation checks their structure, while an independent execution boundary limits what they can access.”

## Dependencies and open boundaries

Consumes ADR-03 immutable manifests and ADR-06 reservations/evidence. Worker technology, target permissions, credentials, retention and permitted mutations remain unresolved. No vendor or infrastructure has been approved.
