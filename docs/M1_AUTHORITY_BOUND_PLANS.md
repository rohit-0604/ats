# M1 - Authority-bound scenario plans

Revision: **M1-SPEC-2026-10-25-v2**. Status: **APPROVED AND IMPLEMENTED; VERIFIED OFFLINE**.
Date: 2026-10-25 (Asia/Calcutta). This document owns the single next milestone's
contracts, acceptance and approval boundary. [Foundation rationale](POST_M0_FOUNDATIONS.md)
owns dependency analysis and later milestone proposals. The user explicitly approved
this exact offline scope with "Go"; see C16 in DECISIONS. **All 30 M1 acceptance
families passed together with all 48 unchanged M0 tests (78 total).** Actual outcomes,
failure corrections and limitations are in [M1_VERIFICATION](M1_VERIFICATION.md).

## Revision history and capability compatibility

`M1-SPEC-2026-10-23-v1` received a documentation-only REVISE recommendation: the
roadmap lacked explicit tested-portability and adaptive-routing deliverables. V2 resolves
both through the authoritative [capability register](CAPABILITY_REQUIREMENTS.md) and
the roadmap's [MODEL](ROADMAP.md#model---adaptive-routing-workstream) and
[PORT](ROADMAP.md#port---tested-deployment-portability-workstream) delivery gates.
These are deferred product workstreams, not M1 prerequisites or implementation scope.

Exact v2 changes: new revision/date/history, capability compatibility/decision-evidence
cross-references, and updated approval wording. **M1-D01..06, M1-AC-01..30, fields,
identity, canonicalization, disposition/admission rules, CLI/error contracts, scope,
non-goals, proposed implementation files and definition of done remain unchanged.**
No M0 contract/schema, full-ADR status or runtime integration is changed or approved.

Real capability relationships: M1 supplies baseline-bound scenario identity to
[CAP-WORKFLOW](CAPABILITY_REQUIREMENTS.md#cap-workflow---capability-driven-testing-workflows),
[CAP-POM](CAPABILITY_REQUIREMENTS.md#cap-pom---maintainable-playwright-artifacts) and later
evaluation/diagnosis; [CAP-HITL](CAPABILITY_REQUIREMENTS.md#cap-hitl---professional-workflow-ux-and-human-review)
owns later plan review. Preserve the trace chain `(plan_digest, scenario_id)` ->
`(baseline_digest, criterion_id)` -> requirement/source IDs in the immutable M0 snapshot;
no duplicate source or oracle contract is introduced. CLI/file/store interfaces remain
small boundaries; a generalized cloud/provider/plugin adapter is unnecessary for M1.

| Preserved decision | Existing offline evidence obligations |
| --- | --- |
| `M1-D01` | M1-AC-01, 07, 28, 29: usable authority-bound planning, multiple scenarios, preserved M0 |
| `M1-D02` | M1-AC-08..11, 19, 20: deterministic identity, revision changes and immutable/golden content |
| `M1-D03` | M1-AC-11..16, 30: complete disposition, unsupported/unfinished scope and exact accounting |
| `M1-D04` | M1-AC-02..06, 12..15, 23, 26: proposals/readiness do not create approval |
| `M1-D05` | M1-AC-03..06, 21..23, 29: coherent current authority, fail-closed reads and M0 compatibility |
| `M1-D06` | M1-AC-17..18, 22, 24..29: bounded offline CLI, effects denied and preserved runtime |

The mapping originally named planned evidence; its executed outcomes are now recorded
in M1_VERIFICATION. It implements the register's
requirement to record affected capabilities, intentional deferrals and compatibility.

## Problem and intended outcome

M0 establishes approved expectations, but no consumer currently binds a planned set
of scenarios to that authority. The legacy generator derives one test ID from each
requirement, and [deduplication](../app/schemas.py#L187) discards additional scenarios.
Later bundle approval and result reconciliation need an explicit planned identity set.

Deliver a separate offline command path: author a scenario draft against an exact M0
baseline, validate/freeze immutable proposal bytes, then assess current baseline authority
and planning completeness. An operator can see every criterion as planned, unplanned or
unsupported, with several scenarios per supported criterion. No percentage or pass claim
is produced. Readiness means only ready for subsequent artifact design and review.

## Scope and exclusions

In scope: strict versioned plan records; deterministic scenario identity; full criterion
disposition; canonical plan bytes/digest; a read-only M0 authority adapter; bounded local
JSON input/exclusive output; offline assessment with explicit blockers; synthetic tests.

Excluded: scenario generation by models, new requirement extraction, plan/bundle approval
writes, executable manifests/files, test IDs/configurations, result parsing, global lifecycle
or budget engine, effects/attempt persistence, graph/CLI integration, replay, providers,
crawling, repair, Playwright discovery/execution, UI, package changes and deployment.
Do not add a database, generic policy DSL, plan event log, plugin or runtime agent.

Preserve every M0 contract, CLI command, error, canonical byte vector and store schema.
The old runtime stays untouched and unsafe. M1 is a foundation consumer, not a patch
that enforces these rules on `main.py`.

## Authority and trust

Use [ReviewStore.inspect(project_id, digest)](../app/core/review_store.py#L305), which
returns project, verified snapshot and effective review under one read transaction.
Never infer current authority from imported flags, `ReviewDecisionV1`, a prior command's
success, `head_digest` alone, a JSON assessment or a caller-supplied `approved` field.

The adapter calls only `inspect`; it must not call `initialize`, `local_context`,
`record_review`, `_open(write=True)` or private SQL methods. `local_context` can perform
write-mode recovery and is not a harmless authority-read helper. Missing/corrupt/busy/
future-version/hot-journal stores fail explicitly. No implicit creation or recovery.

All expected IDs/digests must match across requested subject, inspection and plan.
Revalidate returned typed objects and internal cross-field consistency at the adapter
boundary. A fake is permitted in tests; production CLI constructs the real adapter from
the explicit `--db`. Imported JSON cannot substitute an inspection or authority decision.
Require pending status to have a null decision sequence; all other statuses need a
decision sequence in 1..project_sequence. An approved subject must match active/head;
an inactive status cannot claim that subject as active. Contradictory observations are
an authority error, not an ordinary blocked plan.

A baseline is currently usable only when `status == approved`, `active_digest` equals
the requested baseline digest and `head_digest == active_digest`. The inspection's
decision/project sequences are reported as observations, not leases or capabilities.
An unrelated review may advance project sequence without changing the active subject;
this alone does not invalidate a plan. A later revoke/supersede must block a fresh assess.
The snapshot and authority come from one coherent read, but can change after that read.
No claim of atomic check-and-dispatch exists in M1; it performs no dispatch.

Trust remains the M0 single human operator with trusted local OS access. Scenario text
is untrusted and inert. Same-user tampering, malicious filesystem races and authenticity
of human intent are not solved by hashes or frozen Python models.

## Approved V1 records

All listed fields are required; nullable values must be explicit null. Unknown fields,
duplicate JSON keys, unknown versions, coercions, booleans used as integers and floats
fail. Models and nested collections are immutable; supported copy/update paths revalidate.
Use M0's existing scalar syntax/bounds for UUID, digest, sequence and safe Unicode text,
without changing M0 implementations. No `Any`, mutable resource dictionaries, credentials,
URLs to fetch, executable source, file destinations or arbitrary metadata fields.

| Record | Exact fields |
| --- | --- |
| `ScenarioV1` | `scenario_id: UUID`, `criterion_id: UUID`, `scenario_key: Key`, `title: ShortText`, `preconditions: tuple[NonblankText, ...]` (0..64), `steps: tuple[NonblankText, ...]` (1..64) |
| `CriterionDispositionV1` | `criterion_id: UUID`, `status: planned / unplanned / unsupported`, `reason: NonblankText or null` |
| `ScenarioPlanDraftV1` | `schema_version: 1`, `project_id: UUID`, `baseline_digest: Digest`, `scenarios: tuple[ScenarioV1, ...]` (0..5000), `dispositions: tuple[CriterionDispositionV1, ...]` (1..5000) |
| `ScenarioPlanV1` | All draft fields plus `digest: Digest` |
| `PlanIssueV1` | `code: IssueCode`, `criterion_id: UUID or null`, `scenario_id: UUID or null`; IDs only from validated records; fixed messages are rendered by the CLI |
| `PlanAssessmentV1` | `schema_version: 1`, `policy_version: literal m1-plan-admission-v1`, `project_id`, `baseline_digest`, `plan_digest` (UUID/digest types as above), `baseline_status: pending / approved / rejected / revoked / superseded`, `decision_sequence: Sequence or null`, `project_sequence: Sequence`, `active_digest: Digest or null`, `head_digest: Digest or null`, `disposition: ready_for_artifact_design / blocked`, `issues: tuple[PlanIssueV1, ...]`, `total_criteria`, `planned_criteria`, `unplanned_criteria`, `unsupported_criteria`, `scenario_count` (strict integers 0..5000), `plan_approved: literal false`, `execution_authorized: literal false` |

`Key` matches `[a-z0-9][a-z0-9._-]{0,63}`. `ShortText` is nonblank, at most 512
Unicode code points; `NonblankText` at most 16384. Preserve whitespace, negation, case,
normalization form and ordered steps/preconditions. Reject M0-forbidden controls,
NUL and unpaired surrogates. Planning text cannot override the referenced criterion's
`expected_outcome`; do not introduce an independent scenario oracle field. Contradictory
natural-language setup/steps still require human review in later plan/bundle review.

`PlanAssessmentV1` is output, not an accepted authority input or persisted approval.
Its counts must agree with the exact plan/baseline sets. All-unsupported plans are
representable but blocked with zero scenarios; no vacuous ready result.

### Scenario identity

Mint scenario identity deterministically using existing standard-library UUIDv5:

```text
scenario_id = uuid5(
    namespace=UUID(criterion_id),
    name=canonical UTF-8 JSON text of
         ["ats-scenario-v1", project_id, scenario_key]
)
```

The array order is fixed; JSON uses `ensure_ascii=False`, sorted object keys and
compact separators, with no newline. Recompute and validate the supplied ID. Keys
are unique within a criterion; the same key under another criterion/project produces
a different ID. IDs do not depend on title, position, code bytes or requirement alone.

Keep the key for the same scenario when wording/steps change; the plan digest changes.
A changed business scenario should receive a new key. Static validation cannot decide
semantic sameness. IDs can survive a baseline successor with the same criterion ID,
but the plan must explicitly reference that new digest and be reassessed. No automatic
rebasing, inherited readiness, plan lineage database or removal prohibition is introduced.
Different plan revisions may add/remove scenarios while retaining every baseline criterion
disposition; later approvals bind the exact plan digest, so omission cannot inherit approval.

An identity is `(project_id, scenario_id)`; its concrete planned revision is
`(plan_digest, scenario_id)`. M2 will assign logical test/configuration identities against
that pair. M1 does not equate one scenario with one runtime test or browser attempt.

### Referential integrity and completeness

Validation uses the exact verified M0 snapshot, including for pending/rejected/historical
baselines. Such content can be inspected and planned without acquiring authority.
A snapshot with no criteria cannot form a valid M1 plan; report INVALID_REFERENCE.

1. Disposition criterion IDs equal the complete baseline criterion set exactly once.
   Missing, duplicate or foreign IDs fail validation. Requirements and their criteria
   are never removed from the baseline by a plan.
2. Every scenario references one criterion in that set and has its correct deterministic
   ID. Duplicate IDs or duplicate `(criterion_id, scenario_key)` fail; duplicate titles
   and similar steps are allowed. No semantic/token deduplication.
3. `planned`: criterion has `clarity=specified`, `automation_support=supported`, one or
   more scenarios, and null disposition reason.
4. `unplanned`: zero scenarios and a nonblank reason. Required for unknown support or
   unresolved clarity unless the criterion is explicitly unsupported; also allowed
   for an intentionally unfinished supported criterion.
   It always blocks readiness, but not structural freezing.
5. `unsupported`: required when the criterion has `automation_support=unsupported`, zero scenarios and
   reason exactly equal to the baseline's nonblank `support_reason`. It remains visible
   and is not executable or counted as planned. An unresolved unsupported criterion is
   representable, but M0 cannot approve its baseline and admission therefore blocks.
6. Baseline-supported criteria cannot be relabeled unsupported in the plan. Only a new
   M0 baseline/review may change support/expected behavior. No scenario may be attached
   to an unsupported criterion, even on an approved baseline.

These rules check structure and explicit scope; they do not prove that one or more
scenarios adequately cover the behavior. M0 requirement dependency IDs are retained
through the baseline reference; M1 does not schedule or execute those dependencies.
Full supported-criterion planning is deliberately required for readiness. Partial drafts
remain usable, but intentional partial execution/selection is a later product decision;
do not implement it by hiding criteria or treating unplanned items as unsupported.

### Canonical plan bytes and limits

Canonicalize a validated plan using the M0 JSON encoding conventions, but **a separate
plan ordering function**: sort scenarios by `scenario_id` and dispositions by
`criterion_id`; keep preconditions/steps in their given order. Hash all fields except
the top-level `digest` using SHA-256 and prefix `sha256:`. No timestamps, live approval
state, store paths or review sequences enter the digest. A baseline/step/reason/key
change changes the digest. Permuting identity collections does not.

Input is UTF-8 JSON, at most 8 MiB, depth 32, 100000 nodes; accept a single BOM at input
as M0 does, but canonical output has none. Enforce the same aggregate limits for direct
Python calls and full canonical output, not only file parsing. Each record must also
meet its own bounds. No partial import, truncation, code-fence extraction or repair.
Assessment issues are bounded to 5002 (one per unplanned criterion plus authority and
empty-plan blockers), sorted by code then criterion ID then scenario ID, treating null
as empty text. No arbitrary diagnostics from rejected input.

Freeze recomputes/returns a snapshot of proposal content. Loading a plan recomputes the
digest; mismatch fails without rewrite. Canonical exports are exact bytes including
digest with no trailing newline; stdout JSON responses have one terminal newline.
Do not alter `baseline_contracts.canonical_bytes` or reuse it with an assumption that
it sorts new `scenarios`/`dispositions` collections.

## Deterministic admission and command flow

Fixed flow: bounded parse -> one coherent M0 inspection -> structural/reference
validation -> canonicalization -> assessment -> explicit output. No planner/model,
retry loop, wait-for-approval or long-lived lifecycle state is needed.

For valid plan content, collect these issue codes:

- `BASELINE_NOT_ACTIVE` if the current effective authority condition fails. Return
  the actual baseline status and observed pointers/sequences; never promote it.
- `CRITERION_UNPLANNED` once for each unplanned criterion.
- `NO_AUTOMATABLE_SCENARIOS` if there are zero scenarios, including all-unsupported plans.

An empty issue list yields `ready_for_artifact_design`; otherwise `blocked`.
Both have `plan_approved=false` and `execution_authorized=false`. Every assess rereads
M0. Do not accept serialized inspection/assessment files, `--approved`, `--force`,
`--auto`, `--execute`, raw review actor or a `latest` baseline alias.

The finite limits here are input/work/output bounds and the existing 5-second SQLite
busy timeout, not runtime budgets. M0 performs full-history integrity validation, so
large-store latency remains unmeasured; do not claim a hard wall-time guarantee.
Model/retry/execution/spend reservations belong to M4 before any effect is connected.

### Internal interfaces

```text
scenario_id(project_id, criterion_id, scenario_key) -> UUID text
parse_plan_draft(raw_bytes) -> ScenarioPlanDraftV1
parse_plan(raw_bytes) -> ScenarioPlanV1  # validates hash and bounded content
validate_plan_references(draft_or_plan, snapshot) -> None | PlanError
freeze_plan(draft, snapshot) -> ScenarioPlanV1  # pure, revalidates references; no approval
assess_plan(validated_plan, inspection) -> PlanAssessmentV1  # pure, cross-checks subjects
inspect_plan(store: ReviewStore, validated_plan) -> PlanAssessmentV1
```

The service calls `store.inspect` once, validates references and assesses using that
same inspection. CLI freeze also uses a coherent inspection to validate references;
pending or blocked content may freeze. Assess must not freeze or change input files.
Pure functions do not claim their supplied inspection is fresh; only the read service
provides an observation from the store at invocation. No external input can choose
a fake adapter in the production CLI.

### Offline CLI

Separate entry point: `python -B -m app.plan_cli`. No import of `main`, `app.config`,
legacy schemas/agents, providers, crawler, evaluator, repair or LangGraph bootstrap.

| Command | Behavior |
| --- | --- |
| `--help`, `version` | No file/database/network/log initialization; version names M1 wire/policy versions |
| `scenario-id --project UUID --criterion UUID --key KEY` | Pure deterministic ID; no assertion that the IDs exist or are approved |
| `validate --db PATH --draft PATH` | Read-only structural/reference validation and assessment using a computed candidate plan digest; return `{schema_version:1, structurally_valid:true, assessment:PlanAssessmentV1}` for valid content |
| `freeze --db PATH --draft PATH --out PATH` | Validate references; create one exclusive canonical plan export even if assessment is blocked; return `{schema_version:1, plan_digest:Digest, assessment:PlanAssessmentV1}` only after publication |
| `assess --db PATH --plan PATH` | Verify plan hash/references and return current `PlanAssessmentV1`; no writes |

All DB subjects come from the strictly parsed plan. No project/digest override flags
may silently relabel content. M0 `baseline_cli inspect` remains the way to inspect the
full oracle/provenance; do not duplicate that output in assessments.

Read/export through existing bounded M0 file helpers without changing their semantics.
Only explicit operator-selected ordinary local paths are accessed. Preserve existing
files; no parent creation, overwrite, shared directory cleanup, globbing, URL fetching
or paths obtained from scenario text. Export into an excluded private runtime directory
or an explicitly selected temp directory. Synthetic test fixtures alone belong in Git.
Reuse `write_export`'s no-replace behavior; a failed stdout acknowledgment after a complete
export means output may exist. Inspect its digest, never overwrite or imply no effect.
Do not claim export+assessment is an atomic authorization transaction.

Exit 0: command completed; freeze may produce a blocked proposal and must display that
status. Validate/assess return 0 only for ready content, 3 for structurally valid blocked
content. Exit 2: usage/schema/limits/reference/digest failure. Exit 4: authority-read,
path/store/recovery/integrity/output failure. Exit 130: interruption; do not assert that
publication did not occur. Unknown project/subject during read is exit 4, not an empty plan.

Use a separate `PlanError` with bounded code/pointer/fixed-message envelope. M1 validation
codes: `INVALID_INPUT`, `UNKNOWN_FIELD`, `UNSUPPORTED_VERSION`, `LIMIT_EXCEEDED`,
`DUPLICATE_ID`, `INVALID_REFERENCE`, `SCENARIO_ID_MISMATCH`, `DISPOSITION_CONFLICT`,
`PLAN_DIGEST_MISMATCH`. Reference mismatch between inspection and request is
`AUTHORITY_MISMATCH` (exit 4). Reuse safe M0 error codes for authority/file failures with
`source: m0`; new errors use `source: m1`. No extension of M0's error enum. No tracebacks,
rejected argument values, unknown key names or free-text excerpts in error output.
No new approval command is exposed; errors must never yield a ready assessment.
If a reused M0 parser/scalar validator rejects M1 input, translate its safe validation
code to `source: m1` and exit 2; errors from actual M0 store/file operations remain
`source: m0` with exit 4. Classification follows the failing boundary, not the helper's
exception class. File byte-limit errors are input-limit failures (exit 2).

## Security and compatibility invariants

1. Baseline approval is read from the actual store and remains distinct from plan/code/
   execution approval. Assessments are observations, never transferable permissions.
2. The full criterion set remains visible, with unsupported and unplanned separate.
   A passing structural check or all-unsupported plan cannot mean requirements satisfied.
3. Criterion oracle text is referenced, never edited/copied into a competing authority.
   A scenario cannot move to another criterion under the same validated ID.
4. Every file/CLI/Python input follows the same strict limits; failures produce no partial
   valid plan or authority and no implicit recovery/overwrite.
5. M0 APIs, schema version/fingerprint, snapshots, decisions, canonical vectors and CLI
   behavior are unchanged. No plan tables are added to the M0 database.
6. Existing runtime imports and entry points remain disconnected. No generated artifact,
   path, import or dependency is evaluated, installed or executed by planning commands.
7. Stale plan assessments cannot authorize future work; M2/M4/M5 must define/recheck their
   own review/reservation/worker boundaries. M1 closes no existing runtime finding.

## Offline acceptance matrix

Every row is **EXECUTED / PASS**, backed by [verification](M1_VERIFICATION.md).
The implementation uses named `test_m1_ac_NN_*` methods; parameterize
listed variants and assert complete outputs plus unchanged store/file state. Do not
replace failure assertions with broad exception checks. Fixtures are synthetic only.

| ID | Stimulus | Required evidence |
| --- | --- | --- |
| M1-AC-01 | Real temporary M0 store with approved supported criterion and one scenario | Coherent inspection; ready assessment; both authority booleans false; exact counts/IDs |
| M1-AC-02 | Pending, rejected, revoked, superseded subjects; legacy approval fields | Every state blocked; imported approval fields rejected; no fallback to head/ancestor |
| M1-AC-03 | Assess approved A, revoke or supersede, assess same plan again | Fresh read blocks; original plan bytes and historical M0 decisions retained |
| M1-AC-04 | Reuse old successful review response after revocation; attempt imported assessment | Neither supplies authority; only actual inspect state is consumed |
| M1-AC-05 | Wrong project, digest, active/head relation or mismatched fake inspection | Explicit subject/integrity error; no ready assessment or writes |
| M1-AC-06 | Unrelated review advances sequence while active baseline remains | Still ready with updated observed sequence; no sequence-as-approval shortcut |
| M1-AC-07 | Two criteria under one requirement; several scenarios under each | All survive freeze/read; unique IDs; duplicate titles/similar text retained |
| M1-AC-08 | Permute input collections and object keys | Exact independent golden canonical bytes and digest unchanged |
| M1-AC-09 | Change step/order/precondition/title/reason/key/baseline | Expected digest differences; scenario ID stable only for same project/criterion/key |
| M1-AC-10 | Same key under different criteria/projects; forged supplied UUID | Deterministic independent UUID vectors; reassignment/forgery rejected |
| M1-AC-11 | Duplicate IDs/keys, foreign references, missing/extra disposition, baseline with no criteria | Whole-input failure, no silently discarded or invented item |
| M1-AC-12 | Supported criterion deliberately unplanned | Freeze succeeds as proposal; validate/assess blocked with reason and complete counts |
| M1-AC-13 | Mixed planned supported and unsupported approved criteria | Unsupported preserved with exact M0 reason; ready for design only; no coverage claim |
| M1-AC-14 | All unsupported, zero scenarios | Valid proposal, blocked with NO_AUTOMATABLE_SCENARIOS; never vacuous readiness |
| M1-AC-15 | Unknown support/unresolved content on pending baseline | Unplanned representation allowed; planned representation rejected; admission blocked |
| M1-AC-16 | Relabel supported as unsupported, change support reason, attach scenario to unsupported | DISPOSITION_CONFLICT; M0 snapshots/review history unchanged |
| M1-AC-17 | Unknown fields/version, booleans as integers, bad UUID/digest, duplicate JSON keys | Strict failure through file and direct Python boundaries; safe codes |
| M1-AC-18 | Byte/depth/node/text/scenario/disposition/step limits, BOM/Unicode/control/nonfinite cases | Exact boundaries exercised; oversize rejected before publication; no partial plan |
| M1-AC-19 | Nested mutation and supported model copy/update APIs | Immutability and revalidation; malformed copies rejected |
| M1-AC-20 | Tampered plan bytes/digest, changed canonical content | Digest failure; no automatic rewrite; valid noncanonical input normalizes only through explicit freeze |
| M1-AC-21 | Missing/future/corrupt/busy/hot-journal M0 store and unknown subject | Explicit error; no store creation/write-mode recovery or fallback; compare bytes/state |
| M1-AC-22 | Fake adapter spies and fresh-process import/help/version/ID command | Only inspect used for authority; no legacy imports, DB/file writes, network or subprocess effects |
| M1-AC-23 | Authority changes after inspect returns, before export | Output remains an observation with false authority flags; next assess blocks; no claim of a reservation |
| M1-AC-24 | Windows spaces/Unicode, UNC/device/ADS/reserved/reparse paths, existing output | Existing helper policy enforced; no overwrite, parent creation or scenario-text path access |
| M1-AC-25 | Export fsync/publication/stdout failure or interruption | Explicit non-success; existing files retained; possible completed export distinguished from acknowledgment |
| M1-AC-26 | CLI validate/freeze/assess ready and blocked flows, invalid/force/execute flags | Exact exit/output contracts; no implied approval from exit 0; safe usage errors |
| M1-AC-27 | Scenario prose with instructions, embedded paths, private-text sentinels | Inert bytes only; no execution/fetch; errors/assessments do not echo text or unknown keys |
| M1-AC-28 | Complete offline M0 -> draft -> freeze -> assess -> revoke -> reassess journey | Real temporary store, unchanged M0 authority except explicit test-owned review commands; no runtime calls |
| M1-AC-29 | Full existing M0 suite and preexisting source inventory | All 48 existing tests retain assertions and pass; M0 golden bytes/schema/CLI and legacy runtime unchanged |
| M1-AC-30 | Aggregate issues/counts, collection ordering and all blocker combinations | Deterministic bounded issue set; counts sum to full baseline criterion set; no result/pass/percentage fields |

Test adapters must assert forbidden provider/browser/network/subprocess imports/calls.
M0's existing controlled Python subprocess tests remain permitted for regression; this
does not permit a generated-code subprocess. Reuse fixture builders only where their
semantics match; golden UUID/digest expectations must be independently calculated.

## Implementation files and sequence

The paths below were implemented during the separately authorized M1 phase.

| Path | Responsibility |
| --- | --- |
| `app/plan_contracts.py` | Strict immutable models, PlanError, scenario UUID and plan canonicalization |
| `app/core/plan_policy.py` | Pure reference/disposition validation and deterministic assessment |
| `app/core/plan_service.py` | Small read-only M0 adapter; one inspect per assessment; no new storage |
| `app/plan_cli.py` | Separate bounded commands using existing file helpers |
| `tests/test_m1_plans.py` | Contract, identity, policy and golden vector cases |
| `tests/test_m1_plan_boundaries.py` | Store adapter, no-effects, CLI/filesystem/fault and journey cases |
| `tests/fixtures/plans/` | Synthetic drafts/plans and independent golden vectors only |
| `docs/M1_VERIFICATION.md` | Future actual commands/outcomes/failures and scope limitations |

The explicitly approved implementation followed this sequence:

1. Recheck clean/changed Git inventory and actual M0 APIs. Agree any necessary spec
   correction before changing accepted semantics; preserve all existing work.
2. Add failing identity/canonicalization/immutability/reference tests and minimal contracts.
3. Implement pure disposition/admission rules; exercise the full blocked/ready matrix.
4. Add read-only adapter using real temporary M0 stores and authority-change/error tests.
5. Implement CLI with bounded reads/exclusive exports and zero-effect import/help tests.
6. Run the M1 matrix and all 48 M0 regressions offline; investigate failures without
   relaxing assertions. Perform documentation/link and changed-content safety review.
7. Record actual evidence and residual risks; update current state/architecture/handoff
   only for implemented behavior. Stop at M1 completion; Git commit/publication needs
   whatever separate authorization the implementation request explicitly supplies.

Definition of done: all 30 acceptance families exercised without required-case skips;
all 48 M0 tests pass unchanged; demonstrated usable offline journey; immutable/golden
and error/authority invariants verified; no M0 schema/API/runtime source changes or new
dependencies; exact file inventory reviewed; accurate verification/handoff documents.
No live execution, P0 closure, lint/type-check pass or installation reproducibility claim
can be inferred from those results. Existing tools only; do not add a test framework.

## Accepted M1 decisions, alternatives and remaining unsafe behavior

| ID | Proposed choice / why | Simpler or competing alternative / trade-off |
| --- | --- | --- |
| M1-D01 | Scenario plan plus real M0 read adapter first; complete useful offline boundary | Pure lifecycle first is smaller code but depends on undefined subjects/reservations; combining with manifests is a larger review surface |
| M1-D02 | Deterministic project/criterion/key UUIDs; plan digest versions content | Random IDs need operator discipline or a registry to prevent accidental reassignment; keys need stable human naming and cannot infer semantic identity |
| M1-D03 | Exactly one disposition per baseline criterion; unsupported remains visible | Omitting unsupported/unplanned entries simplifies JSON but hides denominator loss |
| M1-D04 | No new plan approval/store; freeze proposals and assess current M0 | Persisting plan reviews now adds a second authority lifecycle before bundle scope is settled; defer to M2, so M1 readiness cannot permit generation |
| M1-D05 | Use one public M0 inspect transaction, no M0 schema/canonical changes | Separate reads risk incoherent observations; direct SQL or extending the store couples M1 to protected M0 internals |
| M1-D06 | Separate offline CLI, no runtime integration or global lifecycle/budgets yet | In-place legacy integration would need manifests, effects and isolation; costs an additional later adapter but preserves current behavior and keeps effects out |

After M1, the legacy runner, planner, approval bypasses, result accounting and repair
remain unsafe. Plan text can misrepresent a criterion; a hash only identifies it.
Assessments can become stale immediately, and local operator labels are not authentication.
Final bundle closure, approval persistence, runtime budget/replay enforcement, trusted
evidence and isolated execution remain mandatory later work.

## Implementation approval gate

The owner's "Go" accepted the preceding scoped authorization for this revision,
including M1-D01..06, all 30 offline cases and the trust/non-authority conditions below.
This gate is complete for M1 only; it is not approval of any full ADR or later milestone.

- Approve M1-D01..06 and the exact bounded offline scope, including deterministic
  scenario keys, full disposition rules and all 30 acceptance families.
- Accept `ready_for_artifact_design` as a non-authorizing observation; no plan review,
  provider generation or execution is permitted by it. Require later review design.
- Confirm M0's single-operator/local-file trust model continues; multiple reviewers,
  authenticated callers and hosted storage require a separate specification.

Approved scoped instruction: **Implement M1-SPEC-2026-10-25-v2 and verify M1-AC-01..30
offline, preserving M0 and existing runtime source.** Implementation and verification
are complete; see M1_VERIFICATION. That implementation request did not authorize a
commit. The subsequent finalization request separately authorizes one reviewed local
M1 commit after verification (C17); no M2-M5 work, runtime integration, provider/generated execution or
publication follows automatically.
