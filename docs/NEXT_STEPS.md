# Next steps and session handoff

Updated 2026-10-23 (Asia/Calcutta). Audit baseline remains 2026-10-22.

**M0 is complete within its approved offline scope. Stop after its reviewed local implementation commit.**
The next dependency is a separately approved foundation follow-up; M1 is not authorized.

## Verified baseline

ATS retains its existing Python/LangGraph CLI for PDF/saved-JSON extraction, discovery,
authentication, inline Playwright generation/execution and attempted repair. That runtime
was not changed or executed during M0. POM generation, dependable defect adjudication,
execution isolation and a maintained runtime evaluation corpus remain absent.
All F01-F17 remain open in [AUDIT_FINDINGS](AUDIT_FINDINGS.md).

The user explicitly approved `M0-SPEC-2026-10-23-v2`. M0 now provides a separate offline
CLI for bounded legacy import, immutable canonical snapshots, explicit digest-bound
review, transactional SQLite storage, supersession/revocation and history/inspection.
The reviewer is the human operator running the CLI under a single-user filesystem
trust assumption; imported approval flags have no authority.

The full command `python -B -m unittest discover -s tests -p "test_*.py" -v` using the
existing `.venv` passed **48 tests in 14.953 seconds**, including all AC-01..33 plus
15 focused regressions, no skips. [M0_VERIFICATION](M0_VERIFICATION.md) records each
outcome, failure fixes, Windows/crash checks, environment and limitations. No dependencies
were installed and no target/provider/generated browser code was executed.

## Git and authorization

The initial snapshot is `4bc2093`; architecture handoff commit is `4a59405`. The seven
M0 specification changes were separately reviewed and locally committed as `bfbf347`
before source work. The user authorized a separate reviewed local implementation
commit after successful verification. Retrieve its exact hash/inventory with `git log -1`
and `git show --stat HEAD`; no push, fetch or deployment belongs to this phase.
Private `rohit-0604/ats` is the existing destination, not permission for further publication.

M0 approval covers only the exact baseline/review subset of ADR-01/06. The six full
ADRs and all later roadmap stages remain PROPOSED. No M1, runtime integration, new
provider calls, generated execution, package installation, deployment or additional
publishing is authorized. Do not infer authorization from local Git tracking refs.

## Resume without chat history

1. Read [AGENTS](../AGENTS.md), [CURRENT_STATE](CURRENT_STATE.md),
   [ARCHITECTURE](ARCHITECTURE.md), [AUDIT_FINDINGS](AUDIT_FINDINGS.md),
   [DECISIONS](DECISIONS.md), [M0](M0_VERSIONED_BASELINES.md),
   [V1 contracts](M0_CONTRACTS_V1.md), [rationale](M0_DECISION_RATIONALE.md),
   [verification](M0_VERIFICATION.md), [ADRs](adr/README.md), [ROADMAP](ROADMAP.md)
   and [Git preparation/history](GIT_PREPARATION.md).
2. Inspect current Git status/history; preserve user changes and the approved snapshot.
   Do not initialize/reconnect Git or repeat architecture research.
3. Read the next explicit user request. M0 completion does not authorize its dependencies.
4. Scope acceptance criteria and contracts before new code; keep tests offline unless
   owned fixtures and a controlled execution boundary are explicitly authorized.
5. Do not run main.py/generated specs as casual smoke tests or use reset instructions.
   Existing config imports create directories, and the old evaluator deletes shared
   specs and runs generated code with the host environment.

## Remaining risks and next dependency

| Priority | Findings | Remaining requirement |
| --- | --- | --- |
| P0 | F01 | Prevent repair from changing approved expected behavior |
| P0 | F02/F03 | Isolate generated code, prevent host-secret access and unsafe artifact writes |
| P0 | F04 | Integrate explicit authority into deterministic runtime materialization/execution eligibility |
| P1 | F05/F06 | Stable scenario/artifact identities, preserved requirements and truthful full result reconciliation |
| P1 | F07/F08/F13 | Deterministic lifecycle/budgets, mode contracts and terminal/exit semantics |
| P1 | F09/F10/F11 | Consistent auth, destination policy, safe rendering and run-bound feedback |
| P1 | F12 | Reproducible direct dependencies and supported environment |

The next foundation proposal should consume M0 authority, not trust legacy flags.
Specify lifecycle policy plus final-bundle manifests/approval, artifact paths and
synthetic result reconciliation before connecting effects. Persistence/effect identity
must be designed alongside those changes. Worker isolation, target authorization,
credential policy and crash/cancellation tests still gate generated execution.
Reviewed oracle-preserving repair requires additional evidence and its own approval.

Within M0, local reviewer attribution is not authentication; hostile same-user/admin
access, filesystem races, private free text, backup/retention and hardware power loss
remain limitations. Full-history integrity validation is intentionally conservative;
large-store performance and clean installation are not measured. Keep real inputs,
drafts, SQLite files/journals and evidence excluded from Git. Use synthetic fixtures.

No remaining M0 implementation task is authorized after the final local commit.
