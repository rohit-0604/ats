# Next steps and session handoff

## Current handoff: M2 complete; stop after local checkpoint

The user approved `M2-SPEC-2026-10-25-v2`, M2-D01..07, V1 contracts and all 26
acceptance families, with the explicitly corrected M2-specific decoder and the original
limits. M2 is implemented and verified offline; read [M2_VERIFICATION](M2_VERIFICATION.md)
for exact commands, counts, failures/fixes, local usage and residual risks. The full suite
has 116 passing tests, zero failures/errors/skips. M0/M1 and all legacy runtime source,
prompts and dependency manifests are unchanged. Earlier specification-only stops below
are historical and superseded for this exact C19 scope.

M2 provides immutable inert packages, explicit scenario/test/configuration identity,
exact byte checks and a fresh non-authorizing assessment. Its CLI is
`python -B -m app.artifact_cli`; no provider/config/code loading or generated execution.
A complete candidate remains unapproved, closure-unverified and unauthorized to execute.

The authorized local checkpoint subject is
`feat: implement offline M2 artifact packages and mapping assessment`, parent
`58c1faef6fb6b96e126e67afa73e6c3af2cce41f`. It includes the reviewed preexisting M2
documentation changes. Recover completed state before retrying an interrupted commit:

```powershell
git log -1 --format="%H %s" --grep="^feat: implement offline M2 artifact packages and mapping assessment$"
git status --short --branch
git diff --cached --stat
git rev-list --left-right --count origin/main...HEAD
```

After checkpoint completion expect a clean worktree/index, local main two commits ahead
of the locally recorded M0 origin/main, with no fetch or live remote query. The exact
checkpoint hash is reported after commit creation, not embedded in its own contents.
**Stop after verification, documentation and this one checkpoint.** No next milestone,
agents, installs, providers, crawling, TypeScript compilation, generated execution,
publication, deployment or push is authorized. M2-R durable review, M3 reconciliation,
M4 lifecycle/reservations and M5 isolation each need new scoped approval. All CAP and
SC-01 requirements remain preserved in the capability register and roadmap.

## Current task and stop point: M2 specification approval

The 2026-10-25 post-M1 request authorizes documentation-only dependency analysis and
M2 specification (C18), superseding the earlier stop-before-specification instruction
below. Read [M2-SPEC-2026-10-25-v1](M2_ARTIFACT_PACKAGES.md) for all ten deliverables,
M2-D01..07, M2-AC-01..26 and the explicit implementation gate. Recommendation: immutable
artifact packages/mappings now; durable review in separately scoped M2-R; results,
policy/reservations and isolated execution remain M3/M4/M5. The split is PROPOSED.
M1 plans are proposals, not approved plans. M2 execution authority stays literal false.

Verified starting HEAD: `58c1faef6fb6b96e126e67afa73e6c3af2cce41f`, clean tree/index,
local main ahead 1/behind 0 of local origin/main; no remote query. Existing full offline
suite rerun: **78 passed in 28.819 seconds, zero failures/errors/skips**. M0/M1 source,
tests, schemas and legacy runtime are unchanged. This task leaves documentation edits
uncommitted. No further commit authorization survives from completed M1 finalization.

**Stop at the specification approval gate.** Implementation, M2-R, agents, installs,
providers, crawling, generated execution, publication, push and deployment are not
allowed. Earlier handoff sections below record completed M1 work and historical gates;
this section and C18 govern the present task.

Updated 2026-10-25 (Asia/Calcutta). Audit baseline remains 2026-10-22.

**M1 is complete and verified offline. Stop after the authorized local commit and handoff.**
Read [verification](M1_VERIFICATION.md), [foundation rationale](POST_M0_FOUNDATIONS.md) and the approved
[M1 specification](M1_AUTHORITY_BOUND_PLANS.md), revision `M1-SPEC-2026-10-25-v2`.
The user explicitly approved it with "Go" (C16), then separately authorized final
verification, handoff and one local implementation commit (C17). No M2 work or runtime
integration is authorized. The next foundation boundary is M2 bundle/review specification,
which needs a new scoped request; do not begin it automatically.

Read the single [capability requirements register](CAPABILITY_REQUIREMENTS.md) before
scoping future work. It preserves 11 requested capabilities plus explicit ownership for
POM, execution authorization, recovery and data lifecycle. MODEL and PORT are separately
tracked deferred workstreams with acceptance gates; they resolve v1's two documentation
review blockers without adding routing, source-aware mode, UI or cloud adapters to M1.
SC-01 remains independently tracked with its original six acceptance criteria.

The earlier GO recommendation was accepted for M1-D01..06, all 30 offline cases and
the single-operator/non-authorizing-readiness boundary. **The full suite passed 78 tests
in 30.575 seconds at finalization, with zero failures/errors/skips: 48 unchanged M0 plus 30 M1 cases.**
M1 now supplies a separate `app.plan_cli`, strict plans, deterministic scenario identities,
complete dispositions, exclusive exports and fresh read-only M0 assessments. No plan
approval, runtime/generated execution, dependency or database was added. No full ADR
is accepted. Later vendor/profile/budget/quality/data choices retain their own gates.

## Verified baseline

ATS retains its existing Python/LangGraph CLI for PDF/saved-JSON extraction, discovery,
authentication, inline Playwright generation/execution and attempted repair. That runtime
was not changed or executed during M0 or M1. POM generation, dependable defect adjudication,
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

The earlier post-M0 assessment reran that same existing command after inspecting
test boundaries: **48 tests passed in 14.280 seconds**, no failures/errors/skips.
It verified the actual `ReviewStore.inspect(project_id, digest)` interface and relevant
runtime source. This is recorded M0 regression evidence, not a new run in the 2026-10-25
documentation reconciliation, an M1 acceptance result or
an end-to-end runtime test. It predates the M1 implementation and 78-test result above.

Historical documentation reconciliation verification (2026-10-25): 22 Markdown files, 334 local
links and 143 source/heading anchors resolved; fences, CAP IDs/delivery mappings and
revision references passed. All 30 M1 acceptance rows, six M1 decision rows, M1 scope/
non-goals and six SC-01 acceptance rows match their pre-edit snapshots exactly. All
53 tracked non-documentation files checked were byte-for-byte unchanged, and the
preexisting user instruction appended to AGENTS was retained. Bounded credential/token/
private-key scans found no matches. The eight changed/new paths are documentation only;
the index remains empty. `git diff --check` passed. No application/M1 tests, generated
tests, providers, package installs or external reference checks ran in this reconciliation.

## Git and authorization

The initial snapshot is `4bc2093`; architecture handoff commit is `4a59405`. The seven
M0 specification changes were separately reviewed and locally committed as `bfbf347`
before source work. The user authorized a separate reviewed local implementation
commit after successful verification, now verified as
`d17974a9ac17f209ed110a86b11c504e2cc3bc49`. The post-M0 assessment began on a clean
`main` at that commit with matching locally recorded `origin/main`; no remote query
was performed. That assessment prepared documentation only, without a new commit or push.
Private `rohit-0604/ats` is the existing destination, not permission for further publication.

The finalization request authorizes one local commit with subject
`feat: implement offline M1 authority-bound scenario plans`, parent
`d17974a9ac17f209ed110a86b11c504e2cc3bc49`. This handoff is included in that commit;
recover its exact hash without chat history using:

```powershell
git log -1 --format="%H %s" --grep="^feat: implement offline M1 authority-bound scenario plans$"
git status --short --branch
git diff --cached --stat
git rev-list --left-right --count origin/main...HEAD
```

Verify the commit exists before retrying an interrupted commit. Expected completed
state is a clean index/worktree, local `main` one commit ahead of the locally recorded
`origin/main` at the M0 hash above. No fetch, push or live remote verification is part
of finalization. The containing commit's hash is reported after commit creation;
it is deliberately not embedded into its own hashed contents.

M0 approval covers only the exact baseline/review subset of ADR-01/06. The six full
ADRs and all later roadmap stages remain PROPOSED. C16 authorized M1 implementation
and offline verification, now complete; C17 adds only finalization and one local commit.
Neither authorizes
M2, runtime integration, provider calls, generated execution,
installs, deployment, further commits, publication or agents. Do not infer authorization
from local Git tracking refs or specification preparation.

## Implemented API entry points

| Boundary | Modules and callable/command |
| --- | --- |
| M0 immutable contracts and pure review rules | [baseline_contracts.py](../app/baseline_contracts.py), [baseline_review.py](../app/core/baseline_review.py): `validate_draft`, `freeze_baseline`, `approval_blockers` |
| M0 authority and history | [review_store.py](../app/core/review_store.py): `ReviewStore.inspect(project_id, digest)` is the coherent read used by M1; explicit M0 review writes remain separate |
| M0 offline operator CLI | [baseline_cli.py](../app/baseline_cli.py): `python -B -m app.baseline_cli`; exact contracts in M0_CONTRACTS_V1 |
| M1 contracts/identity | [plan_contracts.py](../app/plan_contracts.py): `scenario_id`, `parse_plan_draft`, `parse_plan`, `canonical_plan_bytes`, `plan_digest` |
| M1 pure policy and read service | [plan_policy.py](../app/core/plan_policy.py): `validate_plan_references`, `freeze_plan`, `assess_plan`; [plan_service.py](../app/core/plan_service.py): `inspect_plan`, `prepare_plan`, one public M0 inspection each |
| M1 offline CLI and tests | [plan_cli.py](../app/plan_cli.py): `python -B -m app.plan_cli`, scenario-id/validate/freeze/assess; [verification](M1_VERIFICATION.md) maps all 30 families and the full 78-test command |

Plans retain provenance through baseline/criterion/requirement/source IDs; they do not
duplicate the approved oracle. A ready assessment is an observation, never plan approval
or execution permission. Freeze may export blocked proposals. Reassess after authority
changes; inspect an existing export after lost acknowledgment instead of overwriting it.

## Resume without chat history

1. Read [AGENTS](../AGENTS.md), [CURRENT_STATE](CURRENT_STATE.md),
   [ARCHITECTURE](ARCHITECTURE.md), [AUDIT_FINDINGS](AUDIT_FINDINGS.md),
   [DECISIONS](DECISIONS.md), [M0](M0_VERSIONED_BASELINES.md),
   [V1 contracts](M0_CONTRACTS_V1.md), [rationale](M0_DECISION_RATIONALE.md),
   [verification](M0_VERIFICATION.md), [ADRs](adr/README.md), [ROADMAP](ROADMAP.md)
   and [Git preparation/history](GIT_PREPARATION.md). For the current decision, read
   [POST_M0_FOUNDATIONS](POST_M0_FOUNDATIONS.md) and [M1](M1_AUTHORITY_BOUND_PLANS.md)
   plus the [capability register](CAPABILITY_REQUIREMENTS.md) rather than repeating the
   completed audit/research survey. Check affected CAP IDs and compatibility/deferrals
   in the milestone decision before designing or implementing anything.
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
| P2 | F14/F15/F16/F17 | Truthful telemetry, reliable context/cache handling, complete selector evidence and maintained runtime development gates; offline M0/M1 tests do not close these findings |

The completed M1 scope consumes M0 through one coherent read, preserves complete
criterion dispositions, establishes stable scenario identity and exports immutable
proposals. Readiness grants neither plan/code approval nor execution permission.
M1 added no new authority database or M0 contract change. The next proposed scope is
M2 final executable bundle identity, plan/bundle review and static eligibility: it
depends on M0 effective review and M1 plan/scenario identity, and needs an agreed minimum
test/configuration/attempt envelope for later result and lifecycle contracts. It has
no detailed approved specification or implementation yet; do not start it here.

The proposal revises policy-first M1A/M1B/M1C ordering. Full policy needs concrete
artifact/attempt subjects and durable reservations. Follow M1 with M2 final-bundle
identity/review, M3 offline result reconciliation and M4 lifecycle/budgets/effect recovery;
M3/M4 can remain separate after shared contracts are agreed. M5 worker isolation and a
combined readiness review still precede a separately authorized controlled execution.
All later boundaries are proposals, not detailed implementation approval.

The accepted M1 decisions are M1-D01..06: scope, deterministic scenario keys,
complete criterion disposition, no new plan approval store, one coherent M0 authority
read and separate offline CLI. The [specification gate](M1_AUTHORITY_BOUND_PLANS.md#implementation-approval-gate)
records the completed authorization and exact acceptance scope. Later unresolved decisions include plan/bundle review,
result semantics, mode/exit behavior, finite usage budgets, dispatch/revocation protocol,
target mutations, worker technology, data/retention and operational policy.

The roadmap retains all product workstreams. SC-01 is the separately tracked public
showcase; SC-AC-01..06 clarify its existing scope and acceptance. It is not built or
authorized for publication. Professional UI, lab, POM, telemetry/evaluations, safe repair
and operations remain separately scoped; none is implemented by this documentation.

Within M0, local reviewer attribution is not authentication; hostile same-user/admin
access, filesystem races, private free text, backup/retention and hardware power loss
remain limitations. Full-history integrity validation is intentionally conservative;
large-store performance and clean installation are not measured. Keep real inputs,
drafts, SQLite files/journals and evidence excluded from Git. Use synthetic fixtures.

M0 and M1 implementation are complete under C13/C16. C17 permits only the reviewed
local M1 commit and verified handoff. Stop afterward; further work or publication
requires a new scoped request. Preserve any later user changes.
