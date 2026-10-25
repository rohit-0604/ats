# ATS capability requirements register

Architecture assurance update, 2026-10-25 (C21): **CAP-REG-2026-10-25-v3** adds
CAP-FRAMEWORK and CAP-MODEL.A4/A5, preserving every V2 requirement/acceptance ID
and SC-01. [Architecture assurance](ARCHITECTURE.md#consolidated-assurance-review---2026-10-25)
owns source findings, alternatives and ATS-FIT-2026-10-25-v1. Profile/provider support
remains deferred; no M0/M1/M2 contract or runtime behavior changes. The V2 notes below
record the preceding domain review; the 116-test result remains historical.

Domain review update, 2026-10-25: C20 authorizes documentation/research only. V2 adds
CAP-AUTHENV/MANUAL/COVERAGE and domain acceptance under existing owners, based on
[DOMAIN_WORKFLOWS_REVIEW](DOMAIN_WORKFLOWS_REVIEW.md). All new acceptance obligations
are unimplemented/unexecuted; M0/M1/M2 remain unchanged and no full ADR is accepted.

Current M2 evidence, 2026-10-25: the user approved the narrow v2 package/mapping
slice and decoder correction. [M2 verification](M2_VERIFICATION.md) records 116 passing
offline tests (78 unchanged M0/M1 plus 38 M2), no failures/errors/skips. Immutable byte
packages and explicit planned mappings now exist; durable plan/bundle review stays M2-R.
No other CAP acceptance obligation, professional UI, source-aware workflow, public
showcase, MODEL/OBS/EVAL/LAB/PORT workstream or execution gate is removed or claimed
implemented. The historical delivery clarification below remains the rationale.

Post-M1 delivery clarification, 2026-10-25: [M2](M2_ARTIFACT_PACKAGES.md) proposes
immutable artifact packages and explicit mappings; M2-R separately owns durable
plan/bundle review previously grouped under M2 in the inventory below. M2-R must precede
M4 dispatch authority. M5 owns actual closure/materialization validation under isolation.
The specification maps every CAP ID to preserved contracts and intentional deferrals;
all acceptance obligations below remain unchanged. No deferred capability is implemented
or approved by this refinement.

Revision: **CAP-REG-2026-10-25-v3**. Status: **USER-REQUESTED PRODUCT REQUIREMENTS
RECORDED; DELIVERY DEFERRED UNLESS SEPARATELY AUTHORIZED**. Acceptance/evaluation
criteria below are required future evidence, **not executed checks or benchmark results**.
This is the single authoritative cross-cutting capability register. [ROADMAP](ROADMAP.md)
owns sequencing; [DECISIONS](DECISIONS.md) owns consequential choices/authorization;
milestone specifications own exact contracts. Do not copy those contracts here.

## Authority, evidence and maintenance

The 2026-10-25 request preserves these product requirements; it does not authorize
implementing every capability now. Proposed delivery boundaries, adapter technologies,
supported targets, thresholds and vendor choices still require scoped decisions.
All six [ADRs](adr/README.md) remain PROPOSED beyond the exact approved M0/M1/M2 scopes.
[M0 contracts](M0_CONTRACTS_V1.md) and [verification](M0_VERIFICATION.md) remain authoritative
for implemented baseline/review behavior; no new approval lifecycle is defined here.

Inspection found no separate maintained PRD/capability register. [ROADMAP](ROADMAP.md)
already contains product requirements and proposed workstreams. README and the two root
Word architecture/setup documents are historical descriptive material, not authoritative
acceptance specifications or evidence that their claims work. Preserve those artifacts;
use [CURRENT_STATE](CURRENT_STATE.md), [ARCHITECTURE](ARCHITECTURE.md) and the existing
[findings](AUDIT_FINDINGS.md) to distinguish implementation from proposals.

Current status below is based on those records and bounded source inspection, without
rerunning the audit, importing the runtime or contacting providers. The subsequent
M1 implementation now has 78 offline tests (48 M0 plus 30 M1), recorded in
[M1_VERIFICATION](M1_VERIFICATION.md). Legacy implementations are partial,
unsafe or unverified as specified; existence is not successful product verification.

Before approving each milestone, map affected CAP IDs to its scope/acceptance and record
intentional deferrals and compatibility implications. IDs remain stable on revision;
retire/supersede with reasons rather than delete. One requirement may support several
milestones; cross-reference its owner rather than create competing contracts. Capability
acceptance IDs `CAP-*.A1` etc. identify evidence obligations, not tests already present.

## Coverage inventory and delivery map

"Prior coverage" describes documentation before this register. "Delivery" is proposed,
not a date or permission. M1 references foundations only; it implements none of the
deferred model, source, UI, worker or cloud integrations in this register.

| Stable ID | Prior coverage | Current implementation | Proposed delivery / canonical design |
| --- | --- | --- | --- |
| CAP-MODEL | Partial: default/fallback; adaptive selection missing | Legacy tier routing; adaptive policy unverified/missing | MODEL workstream; M4 budgets; CAP-EVAL/OBS |
| CAP-DIAG | Documented, taxonomy/report criteria partial | Error heuristics and unsafe repair; no dependable adjudication | Safe repair after controlled evidence; ADR-05 |
| CAP-WORKFLOW | Partial: source/API modes deferred | M0 authority and M1 offline planning verified; legacy black-box runtime unsafe | M2-M5 foundations, then source-aware expansion |
| CAP-EFFICIENCY | Partial and scattered | Retries/cache/memory/async helpers; benefits and full limits unverified | M4 plus measured efficiency/retrieval work |
| CAP-HITL | Documented UI direction, runtime guarantees partial | M0 reviews and M2 review subjects verified; legacy feedback unsafe; professional UI absent | M2-R durable review contracts, then private UI |
| CAP-OBS | Documented proposed schema | Local JSONL/logs/dashboard; incomplete attempt accounting | OBS workstream after shared IDs; M4/M5 effects |
| CAP-EVAL | Documented evaluation plan | 116 offline M0/M1/M2 unit/contracts verified; maintained runtime/model corpus absent | EVAL plus CAP-LAB; before adaptive promotion |
| CAP-PORT | Missing as tested deliverable | Local Windows M0 verified; deployment portability unverified | PORT workstream and deployment/operations |
| CAP-EXT | Partial boundaries; no versioned extension acceptance | Concrete provider modules; general safe extension boundary absent | Contract-driven adapters as integrations are authorized |
| CAP-SHOWCASE | SC-01 already explicit | Not built or published by this work | Independent SC-01; canonical SC-AC-01..06 in ROADMAP |
| CAP-LAB | Documented target/defect direction | Owned reproducible lab/ground truth not verified | Lab fixtures before controlled end-to-end/evaluations |
| CAP-POM | Documented, no dedicated CAP owner | Inline TS generator exists; POM absent | Maintainable POM after M2 and controlled evidence |
| CAP-EXEC | Scattered security gates; no CAP owner | Legacy host execution unsafe; no approved isolation | M2/M4/M5 and explicit target authorization; ADR-04 |
| CAP-RECOVERY | ADR-06, incomplete operational requirements | M0 review recovery verified; runtime effect recovery unverified | M4 reservations, M5 cancellation, operations |
| CAP-DATA | Scattered privacy/operations requirements | Bounded M0 files; shared legacy stores; retention/access incomplete | Data governance and operations before hosted access |
| CAP-AUTHENV | Partial auth/scope requirements; environment/role/session lifecycle incomplete | Form/token/API-key and single-context discovery plumbing; source-confirmed auth/access classification and execution mismatches | AUTHENV profile/identity/discovery requirements; CAP-EXEC/RECOVERY/DATA and controlled lab |
| CAP-MANUAL | Manual case/review/import/selection lifecycle materially incomplete | M0 revisions, M1 scenario proposals and M2 mappings are reusable; no independent reviewed manual-case lifecycle | MANUAL design/review/export first; versioned selection/impact extension separately scoped |
| CAP-COVERAGE | Negative/boundary evaluation goals existed; formal domain denominators/methods incomplete | M1/M2 structural counts verified; legacy percentage/result semantics defective | COVERAGE measurement/design policy; manual campaigns, M3 reconciliation, CAP-EVAL/LAB |
| CAP-FRAMEWORK | Generic extension/POM requirements existed; named language/runner support and qualification gates missing | Legacy TS/Playwright Test only; Python Playwright discovery is not Python test generation; no Selenium runner adapters | FRAMEWORK profiles/adapters; M3 result vocabulary, M4 admission and M5 isolated qualification; CAP-EXT/POM/EVAL |

## CAP-MODEL - Adaptive model selection and routing

- **Problem/benefit:** different tasks need different capabilities; route deliberately
  without paying more or disclosing more data merely because a fallback exists.
- **Required behavior:** support multiple provider/model families through compatibility
  checks and capability discovery (a versioned curated catalog is a valid starting point).
  Select by task suitability, quality, latency, cost, privacy and context limits; configure
  reasoning effort only where supported and record requested/effective settings. Separate
  provider availability/auth/rate-limit failures from invalid or poor-quality responses.
  Bound total retries, fallback and escalation; permit validated user overrides within
  safety/budget limits; version routing policies; abstain with a reason when no suitable
  model or budget remains. Record every attempt and evaluate policy on fixed benchmarks.
- **Invariants:** price is not a quality ranking; unsupported effort/options fail explicitly;
  no fallback crosses data/permission limits or creates fresh budget; no silent promotion.
- **Current evidence:** [router Tier/chains](../app/llm/router.py#L24) and
  [complete](../app/llm/router.py#L153) implement configured task tiers and retries returning
  the first successful response. This is not verified adaptive suitability, quality-failure
  routing, capability discovery or per-attempt usage/cost enforcement. No provider was called.
- **Delivery/dependencies:** MODEL, after CAP-EVAL/OBS policy fixtures and M4 reservation
  semantics; may design/evaluate offline first. CAP-EXT supplies adapter compatibility.
- **Decision/trade-off:** compare an explicit task policy/curated catalog with a learned
  selector or external router. Adopt the simpler policy unless held-out evidence justifies
  adaptation; defer live selection until data/budget approval; reject an option that
  worsens mandatory safety/quality or lacks measurable benefit. No router vendor mandated.
- **Acceptance:** **CAP-MODEL.A1** fake catalog/failure matrix covers task/effort/context/
  privacy incompatibility, provider vs quality failure, override denial and explicit abstention;
  no forbidden dispatch or budget overshoot. **CAP-MODEL.A2** compare default/fallback,
  task-aware and escalation policies on the same versioned held-out tasks and budgets;
  report quality, latency, tokens, cost, sample size and uncertainty by task/provider.
  **CAP-MODEL.A3** every attempt, including rejected outputs and fallbacks, has policy/
  model/config provenance and known/unknown usage; promotion needs reviewed thresholds.

### CAP-MODEL interoperability additions - C21

These extend A1..A3 without introducing a competing routing specification. Managed
APIs, local open-weight deployments, self-hosted inference and hosted open weights
must distinguish model/weights/revision identity from deployment/operator/endpoint/
server/API/region identity. Local does not imply zero cost or guaranteed privacy.
Capabilities are versioned per deployment/model combination, including structured
schema dialect, tools, streaming, effort, context/output limits and supported options.
Catalogs/configuration never grant destination, data-disclosure or spending permission.
The MODEL workstream owns implementation; CAP-EXT/OBS/EVAL and M4 reservations are
dependencies. [Architecture assessment](ARCHITECTURE.md#model-and-provider-interoperability)
records direct SDK vs compatible API vs optional gateway alternatives and current gaps.

- **CAP-MODEL.A4:** offline fake deployment/catalog matrices cover all four deployment
  classes, same model at different endpoints, changed weights/server/template revisions,
  unsupported or silently ignored schema/tool/stream/effort settings, malformed/refused/
  truncated text, partial streams and unknown actual-model/usage metadata. Required
  incompatibilities cause zero dispatch; policy/privacy/override denial is explicit.
  Validate outputs independently of transport success. Optional live support claims
  require separately authorized qualification of exact pinned deployment combinations.
- **CAP-MODEL.A5:** fake-clock/transport tests bound the composed SDK/router/gateway
  retry/escalation envelope by total attempts, tokens/cost reservations and deadline;
  preserve requested/actual model and deployment, policy/catalog/prompt versions,
  provider vs quality failure, unknown usage, cancellation/lost acknowledgment and
  every rejected/fallback attempt. No retry creates budget or crosses privacy policy.
  Compare simple direct-adapter/task-policy baseline against any gateway or adaptive
  selector under A2 held-out criteria; require measured benefit before adopting complexity.

## CAP-DIAG - Evidence-driven failure intelligence

- **Problem/benefit:** a failure needs an actionable explanation without hiding a genuine
  application defect by changing the test.
- **Required behavior:** distinguish script/locator defects, application behavior, test
  data, authentication, environment, infrastructure, policy and specification failures;
  retain unknown/insufficient evidence and mixed-cause hypotheses. Separate observations
  from diagnoses; correlate authorized browser/network/console and requirement evidence.
  Produce actionable reports with expected/observed behavior, reproduction context,
  evidence/provenance and uncertainty. Preserve originals; propose reviewed repairs.
- **Invariants:** approved expectations remain unchanged; repair creates a new artifact
  revision/review; no passing rewrite alone proves correct diagnosis or successful repair.
- **Current evidence:** [failure heuristics](../app/core/evaluator_engine.py#L188) and
  [repair_batch](../app/agents/repair_agent.py#L196) exist, but F01/F14/F16 and
  [ADR-05](adr/05-safe-repair.md) identify oracle/provenance gaps; no taxonomy accuracy claimed.
- **Delivery/dependencies:** safe-repair workstream after M0/M1/M2 identity, M3 outcomes,
  CAP-LAB ground truth and M5 authorized evidence; not an M1 implementation obligation.
- **Decision/trade-off:** stop repair vs reviewed proposals vs narrowly automated edits.
  Adopt useful reviewed assistance with retained defect sensitivity; defer automation until
  held-out validation; reject edits/classes that weaken oracles or overstate causality.
- **Acceptance:** **CAP-DIAG.A1** labeled corpus includes all named causes, ambiguous/mixed
  cases, good builds, seeded defects and stale locators; report confusion matrix, false
  attribution, abstention and uncertainty. **CAP-DIAG.A2** seeded genuine defects remain
  detectable after proposed repairs; assertion weakening/skips/swallowed failures fail;
  original evidence, proposal diff, review and actionable report resolve to exact revisions.

## CAP-WORKFLOW - Capability-driven testing workflows

- **Problem/benefit:** one traceable system should work with the evidence a user can
  authorize, rather than requiring source access or a separate framework per mode.
- **Required behavior:** shared requirements/criterion/scenario/artifact foundations;
  black-box operation without source access; optional explicitly authorized repositories,
  API contracts and diagnostic logs. Branch by available capabilities and permissions;
  source analysis is read-only by default, and source changes remain human-reviewed
  proposals within separately authorized scope. Enforce deterministic lifecycle/budgets
  and persist inspectable running, waiting, blocked and terminal states.
- **Invariants:** source/API/log content is untrusted evidence, not oracle authority;
  no repository build/tool call/write merely because access to read was granted.
- **Current evidence:** [legacy graph](../app/core/react_controller.py#L651) is a black-box
  pipeline with policy/mode gaps; source/API-contract ingestion absent. M0 authority is
  [verified offline](M0_VERIFICATION.md); [M1 planning](M1_VERIFICATION.md) is now verified
  as a separate offline subsystem and remains disconnected from the legacy runtime.
- **Delivery/dependencies:** M1-M5 foundations then source-aware expansion, CAP-EXT and
  CAP-DATA; state/recovery semantics owned by M4/ADR-06, not redefined here.
- **Decision/trade-off:** one modular workflow with explicit branches vs another agent
  framework per mode. Adopt a branch only for a real authorized evidence need; defer
  source mutation/builds; reject implicit permissions or duplicated orchestration.
- **Acceptance:** **CAP-WORKFLOW.A1** fake capability/permission matrix exercises black-box,
  source-only, API/log-present/missing and denied tools, with zero unauthorized effects.
  **CAP-WORKFLOW.A2** all evidence and states resolve to exact baseline/source/plan versions;
  unavailable capabilities block/abstain visibly; source proposals require explicit review.

## CAP-EFFICIENCY - Context and execution efficiency

- **Problem/benefit:** reduce unnecessary latency/spend without lowering assertion fidelity.
- **Required behavior:** task-level model/context budgets; relevant-context selection and
  retrieval; version-aware caches with explicit invalidation; bounded retries and duplicate
  work; controlled parallelism only where effects/data are independent. Account for latency,
  tokens and cost; exhaust/cancel gracefully; reuse verified work during recovery.
- **Invariants:** omission of criteria/evidence is not an optimization; concurrency cannot
  bypass approval, shared budget or target policy. Unknown usage stays unknown/reserved.
- **Current evidence:** [architecture storage limits](ARCHITECTURE.md#provider-routing-and-persistence)
  describe cache/memory and retry helpers; benefit, freshness, global budgets and safe
  parallel effects are unverified. M0 bounds input, not provider spending.
- **Delivery/dependencies:** M4 plus CAP-RECOVERY; efficiency/retrieval experiments require
  CAP-EVAL/OBS and versioned input identities. No parallel agent work is authorized here.
- **Decision/trade-off:** serial explicit context vs caching/retrieval/parallel scheduling.
  Adopt an optimization only with equal-quality measured benefit; defer until a bottleneck
  is measured; reject stale reuse, unbounded work or reduced defect sensitivity.
- **Acceptance:** **CAP-EFFICIENCY.A1** fake clock/usage/cache tests cover stale versions,
  changed prompts/models/data, duplicate work, bounded retry, exhaustion and cancellation.
  **CAP-EFFICIENCY.A2** equal-budget baseline/optimized comparisons report quality, latency,
  tokens/cost and sample sizes; concurrent tests preserve total budgets and traceability.

## CAP-HITL - Professional workflow UX and human review

- **Problem/benefit:** operators need to understand evidence and control consequential work.
- **Required behavior:** derive stage progress from durable backend state; show running,
  blocked, failed, completed and waiting-for-review distinctly. Review requirements,
  scenarios, generated code and repairs with evidence/diffs and explicit approval/rejection
  records. Expose model/tool attempts and resource/budget status; support cancellation,
  retries/resume only where backend semantics support them. Provide accessible responsive UI.
- **Invariants:** no fabricated completion percentage, timeout approval or hidden default
  approval. Completion is not proof of requirement satisfaction. Stale feedback is rejected.
- **Current evidence:** M0 explicit reviews are verified; legacy review defaults/feedback
  are unsafe (F04/F11); [professional UI](ROADMAP.md#professional-ui-and-ux) is proposed.
- **Delivery/dependencies:** M2-R plan/bundle review design and M4 durable state/recovery,
  then private professional UI; M1 has a separate offline CLI and grants no plan approval.
- **Decision/trade-off:** CLI/polling first vs streaming/full UI; adopt UI for demonstrated
  review tasks, defer unsupported backend controls, reject cosmetic status disconnected
  from authority. Multi-user review needs a new authenticated boundary.
- **Acceptance:** **CAP-HITL.A1** interrupted/stale/rejected/waiting workflows display true
  backend state and cannot silently approve; every review links exact subject/evidence.
  **CAP-HITL.A2** representative review/cancellation tasks get keyboard, screen-reader,
  contrast/reflow and narrow-screen checks; report task completion/error findings and
  the chosen accessibility target, rather than claiming conformance from appearance.

## CAP-OBS - Observability and telemetry

- **Problem/benefit:** inspect a run and its failures across models/tools/workers without
  relying on opaque agent explanations or losing the authorization record.
- **Required behavior:** correlate requirements/scenarios/artifacts/runs/model/tool attempts;
  structured operational logs and agent/LangGraph traces; requested/resolved provider/model
  versions/configuration, reasoning effort where applicable, prompt/template versions;
  input/output/cached tokens when available, latency, retries/fallbacks and estimated cost.
  Include worker/Playwright evidence and CI/CD-style stage/attempt/failure inspection.
  Apply redaction, retention and access policy; separate durable audits from sampled traces.
- **Invariants:** no credentials or unrestricted prompt/DOM export; unavailable usage is
  unknown, not zero. Audit authority cannot depend on telemetry availability/sampling.
- **Current evidence:** [telemetry.emit](../app/core/telemetry.py#L39) appends local JSONL
  and suppresses write failures; dashboard/logs exist, comprehensive per-attempt accounting
  is absent/unverified. The [roadmap event proposal](ROADMAP.md#observability-and-telemetry-architecture)
  remains a design direction, not an implemented schema.
- **Delivery/dependencies:** OBS after shared M1/M2/M4 IDs; CAP-DATA governs export;
  instrument every authorized adapter, not only framework-visible calls.
- **Decision/trade-off:** local structured evidence first vs one external trace backend.
  Adopt a backend after representative coverage/redaction comparison; defer export when
  policy is unset; reject vendor coupling or making sampled telemetry an approval source.
- **Acceptance:** **CAP-OBS.A1** known fake trajectory accounts for all calls/retries/
  fallbacks/failures with stable correlations, versions and known/unknown usage/cost basis.
  **CAP-OBS.A2** export outage/redaction/access/retention tests preserve audit decisions,
  suppress synthetic secrets and expose collection gaps; failure inspection reconstructs
  stage, original evidence and attempt relationships without executing artifacts.

## CAP-EVAL - Model, agent and system evaluations

- **Problem/benefit:** distinguish measured improvement from more passing rewritten tests.
- **Required behavior:** versioned golden datasets/held-out cases; extraction and scenario
  fidelity, generated test/POM validity, failure classification, repair correctness and
  genuine defect detection. Compare models/prompts/adaptive routes/workflow reliability,
  policy violations, justified retrieval on/off and cost/latency trade-offs; keep regression
  gates and uncertainty-aware reports. Separate human labels from model hypotheses.
- **Invariants:** no train/retrieval leakage of held-out labels; a model judge cannot
  approve an oracle change. Report abstention, false attribution and sample sizes.
- **Current evidence:** 78 M0/M1 unit/contract tests are verified offline; generated
  target specs and historical percentages are not an evaluation corpus. Runtime/model
  benchmark outcomes remain unknown; [evaluation plan](ROADMAP.md#model-and-agent-evaluation)
  and ADR-05 supply canonical rationale.
- **Delivery/dependencies:** EVAL plus CAP-LAB and CAP-OBS; offline data/validators can
  precede providers/workers, while live comparisons require separate authorization.
- **Decision/trade-off:** deterministic validators/manual rubric first vs calibrated LLM
  judges; adopt calibrated methods with disagreements retained, defer numeric release
  thresholds until baseline/owner review, reject uncalibrated aggregate quality scores.
- **Acceptance:** **CAP-EVAL.A1** fixed versioned corpus, split/label provenance and
  independent validators reproduce scores with missing cases/abstentions explicit.
  **CAP-EVAL.A2** paired equal-budget comparisons and policy/seeded-defect regressions
  report quality, false alarms, sensitivity, latency/cost and uncertainty; approval gates
  name thresholds and evidence before promotion, with no fabricated results.

## CAP-PORT - Cloud and infrastructure portability

- **Problem/benefit:** deploy or move an authorized ATS profile without rewriting domain
  rules or claiming every host/cloud has equivalent safety.
- **Required behavior:** explicitly supported deployment profiles and compatibility matrix;
  domain rules separated from platform/provider adapters; configurable storage, artifacts,
  model, worker and telemetry boundaries; appropriately externalized infrastructure config,
  reproducible builds/deployment and secret/environment management. Document data/artifact
  migration, portable correlation/events and platform-specific restrictions.
- **Invariants:** unsupported profiles fail explicitly; migrations preserve identity,
  authority and evidence. No universal portability, mandatory Kubernetes/microservices or
  automatic fallback from a required sandbox to local host execution.
- **Current evidence:** M0's recorded evidence is local Windows/Python/SQLite only;
  [M0 Windows contract](M0_CONTRACTS_V1.md#8-windows-storage-cli-and-errors) is not a cloud
  profile. Worker technology, clean installation and cross-profile migration are unverified.
- **Delivery/dependencies:** PORT workstream with deployment/operations, CAP-EXT/DATA/
  RECOVERY/EXEC; no M0 storage/path change or cloud adapter in M1. A profile must name OS/
  runtime, filesystem/database, execution boundary, identity/secrets and deployment mode.
- **Decision/trade-off:** one tested deployment first vs additional adapters/profiles;
  retain local pilot if sufficient. Adopt a second profile for a real hosting/migration
  need only after equivalent contract/security evidence; defer speculative adapters and
  reject targets unable to enforce mandatory isolation or durability.
- **Acceptance:** **CAP-PORT.A1** for every claimed profile, reproduce build/config/startup
  and run common authority/artifact/result/adapter/security contract fixtures; publish
  exact runtime/config versions, limitations and unsupported features. Portability needs
  demonstrated operation on at least two named profiles, not a universal cloud claim.
  **CAP-PORT.A2** rehearse export/import and rollback between supported profiles using
  synthetic baselines/reviews/artifacts; validate digests, history, access controls and
  evidence after migration, plus secrets/redaction and portable event correlations.

## CAP-EXT - Plug-and-play extensibility

- **Problem/benefit:** add a real integration with predictable compatibility and failure
  behavior, without spreading external SDK assumptions through domain rules.
- **Required behavior:** versioned contracts for providers, evidence sources, workers,
  storage and tools; capability checks before invocation; validated configuration and
  explicit unsupported-integration errors. Contract-test compatibility; secure registration,
  permissions/access checks and minimal external-SDK coupling.
- **Invariants:** configuration/discovered capabilities cannot grant permissions;
  registering an extension is not permission to load untrusted executable plugins.
- **Current evidence:** concrete [provider dispatcher](../app/llm/router.py#L125) exists;
  a general safe versioned adapter/registration layer is not implemented. M0 store V1
  is fixed; extension requirements do not authorize altering its schema or contracts.
- **Delivery/dependencies:** authorize contracts per actual MODEL/PORT/evidence/worker
  integration; M2/M4/M5 define their own boundaries. No generic plugin platform now.
- **Decision/trade-off:** direct injected interfaces/configuration vs dynamic plugins.
  Adopt only needed adapter seams, defer dynamic loading, reject untrusted registration
  or abstraction with no concrete second use case; explicit unsupported errors suffice.
- **Acceptance:** **CAP-EXT.A1** adapter contract tests cover supported/unsupported
  versions/capabilities, invalid config and failure translation without silent fallback.
  **CAP-EXT.A2** denied/unregistered adapters make zero calls; replacing a supported adapter
  retains domain decisions, identities and bounded errors with no leaked SDK/secrets.

## CAP-FRAMEWORK - Versioned automation profiles and multi-language generation

- **Problem/benefit:** use the appropriate supported automation library, language and
  runner without losing approved expectations, exact artifacts or trustworthy results.
- **Required behavior:** qualify Playwright/TypeScript/Playwright Test,
  Playwright/Python/pytest, Selenium/Java/JUnit and Selenium/Python/pytest as separate
  named, versioned profiles. Future API/non-browser profiles require a concrete use
  case and their own transport/oracle/evidence policy. Distinguish engine/library,
  language, runner and POM pattern. Support checks precede generation or dispatch.
  Profiles identify toolchain/runtime/browser/driver/plugin/reporter versions,
  dependencies/locks, configuration, sync/async mode where relevant, generation,
  collection/discovery, invocation identity, evidence and result semantics. Small
  profile-specific adapters retain common baseline/scenario/test/package identities.
- **Invariants:** no unsupported-profile fallback or fabricated compatibility. POM
  actions cannot hide criterion assertions. Tests/configuration/dependencies/profile
  and worker environment must be bound to exact review/execution subjects before use.
  Loading, compilation, installation and collection can execute code and require
  approved isolation. Unsupported/unknown/missing/retry/skip/expected-failure outcomes
  stay visible; matching names or JUnit-style XML alone is not trusted identity.
- **Current evidence:** [M2 contracts](../app/artifact_contracts.py) allow generic byte
  inventories but do not validate profiles/closure. Legacy [generator](../app/agents/codegen_agent.py)
  and [evaluator](../app/core/evaluator_engine.py) assume inline TS/Playwright JSON.
  Other test profiles and reliable safe execution are absent. See
  [compatibility findings](ARCHITECTURE.md#framework-and-language-compatibility).
- **Owner/dependencies:** deferred FRAMEWORK workstream, coordinated with CAP-EXT/POM,
  M3 result vocabulary, M4 admission and M5 isolated qualification; AUTHENV for identity
  context and CAP-EVAL/LAB for semantics. M2-R reviews exact inert subjects independently
  of profile executability; this requirement does not expand its scope.
- **Decision/trade-off:** begin with explicit curated profiles/adapters and qualify the
  existing TS path first. A single framework is simpler initially but does not satisfy
  all named support requirements. Defer other implementations, universal IR and dynamic
  plugins until separately scoped; reconsider V1 envelopes only for demonstrated cases.
- **Acceptance:** **CAP-FRAMEWORK.A1** fake support/version/capability matrix for all four
  named combinations and a justified API profile rejects unsupported combinations/options
  before calls. Exact profiles/manifests resolve toolchain/dependency/runtime identities
  with explicit migration/version decisions and unchanged V1 golden contracts.
  **CAP-FRAMEWORK.A2** each claimed profile passes generation/static/import/collection
  and isolated-runner contract checks on owned fixtures; positive/negative/role/boundary
  scenarios retain approved expected outcomes. POM profiles demonstrate independent
  specs and shared-locator maintenance. These future checks need separate authorization.
  **CAP-FRAMEWORK.A3** profile-specific report fixtures preserve ATS test/config/attempt
  identity across nesting, parameterization/dynamic cases, retries, skips/xfails,
  duplicate names, missing/foreign results and runner failures. M3's common vocabulary
  reconciles exact planned sets without title inference or inflated criterion evidence.
  **CAP-FRAMEWORK.A4** tampered config/lock/helper/profile, denied collection/build plugin,
  secret/egress/host access and incompatible worker environment fail closed; all claimed
  profiles pass the same authority/revocation/isolation suite. Publish supported versions,
  limitations and evidence; API profiles do not inherit browser permission automatically.

## CAP-SHOWCASE - Public ATS showcase

- **Problem/benefit:** explain ATS professionally with inspectable evidence and honest claims.
- **Required behavior:** professional public product website, safe interactive evidence
  explorer, architecture/decision/evaluation-methodology explanations and documentation/
  GitHub links. Use sanitized authentic examples for observed claims; label LIVE/RECORDED/
  PLANNED and synthetic data truthfully. Deploy independently from the private engine.
- **Invariants:** no arbitrary public generated execution, credentials/uploads/URLs or
  route into workers; publication/privacy/licensing/destination approval is separate.
- **Current evidence:** SC-01 is proposed, not built/published by this work. Its exact
  scope and **SC-AC-01..06** stay solely in [ROADMAP](ROADMAP.md#sc-01---separately-trackable-public-showcase-deliverable).
- **Delivery/dependencies:** independent SC-01; authentic run claims depend on CAP-LAB,
  CAP-EVAL/OBS/DATA and separately approved controlled execution. A labeled synthetic
  local prototype need not wait for a hosted private product.
- **Decision/trade-off:** static recorded explorer vs a fixed live lab catalog. Adopt
  static evidence first, defer live access, reject arbitrary public execution and claims
  unsupported by authentic provenance. A professional site need not expose a live backend.
- **Acceptance:** **CAP-SHOWCASE.A1** satisfy the canonical SC-AC-01..06 with traceable
  artifact review; verify documentation/GitHub links and provenance without publishing
  private links/data unintentionally. **CAP-SHOWCASE.A2** separately approve/review public
  destination and release; record actual deployment outcome only when authorized.

## CAP-LAB - Controlled Test Lab

- **Problem/benefit:** determine whether ATS detects real defects against known outcomes.
- **Required behavior:** owned reproducible target, reviewed baseline, known-good behavior,
  seeded application/test/environment defects, deterministic reset/fixtures and verified
  expected outcomes; maintain ground-truth datasets for system evaluations.
- **Invariants:** use disposable authorized state/accounts; lab labels never leak into
  generation/retrieval; unrelated public sites are not ground truth or resettable fixtures.
- **Current evidence:** [lab workstream](ROADMAP.md#controlled-test-lab) is documented;
  owned build/reset/reference-test evidence has not been established by this assessment.
- **Delivery/dependencies:** separately scoped lab data/reference tests alongside offline
  contracts; controlled ATS execution waits for CAP-EXEC and the M2/M3/M4/M5 gate.
- **Decision/trade-off:** small manually understandable app vs realistic broad application.
  Adopt the smallest independently verifiable workflows; defer breadth until labels/resets
  are reliable; reject a lab whose only oracle is ATS's generated test.
- **Acceptance:** **CAP-LAB.A1** independent reference checks distinguish good builds and
  each named application/test/environment variant; reset repeatability and exact versions
  are recorded. **CAP-LAB.A2** dataset labels/provenance/held-out splits remain inspectable;
  state-changing/cancellation fixtures cleanly restore known authorized state.

## Additional cross-cutting ownership found during reconciliation

These four capabilities consolidate real existing requirements that lacked CAP owners;
they are not new frameworks or additions to M1. They prevent POM, execution authorization,
effect recovery and data governance from disappearing between other workstreams.

## CAP-POM - Maintainable Playwright artifacts

- **Problem/benefit:** maintain generated suites without duplicating locators or obscuring assertions.
- **Required behavior:** small typed page/component objects, explicit fixtures and specs;
  visible criterion-specific assertions; traceable shared dependencies and independent specs.
- **Invariants:** approved oracle preserved; final multi-file bundle/version/review includes
  helpers/configuration. No universal base-page hierarchy or artificial file-count target.
- **Current evidence:** [inline generator](../app/agents/codegen_agent.py#L423) exists;
  POM generation is absent, as [the roadmap records](ROADMAP.md#pom-source-understanding-memory-and-agentic-expansion).
- **Delivery/dependencies:** maintainable POM after M1/M2 and controlled evidence; CAP-EVAL.
- **Decision/trade-off:** functions suffice for isolated actions; adopt objects where
  shared-locator maintenance benefits are demonstrated, defer generalization, reject
  hidden/vacuous assertions or framework complexity without reuse.
- **Acceptance:** **CAP-POM.A1** authorized syntax/type/import checks and independently
  runnable specs preserve exact criterion/scenario mappings. **CAP-POM.A2** one shared
  locator change repairs affected specs without oracle edits; good/mutant discrimination
  and final-bundle review remain intact. Executable validation still needs CAP-EXEC.

## CAP-EXEC - Execution authorization and isolation

- **Problem/benefit:** protect host/targets and enforce what the operator actually authorized.
- **Required behavior:** project/target/mutation scope, revision-bound approval, contained
  per-attempt artifacts, isolated process/filesystem/network/resource controls, scoped secret
  references and trusted bounded evidence; enforce redirects/direct HTTP/browser traffic.
  Validate access/project boundaries before hosted/multi-user operation.
- **Invariants:** models/content cannot authorize tools, credentials or target changes;
  no local-runner fallback. Discovery/config loading/dependency validation that can run
  untrusted code needs the same boundary; isolation does not prove honest assertions.
- **Current evidence:** [legacy runner](../app/core/evaluator_engine.py#L106) inherits host
  environment; F02/F03/F04/F10/F11 remain open. [ADR-04](adr/04-isolated-execution.md)
  and [security gates](ROADMAP.md#security-and-reliability-gates) own the proposed boundary.
- **Delivery/dependencies:** M2 manifests, M4 authority/effects, M5 isolation; CAP-DATA.
- **Decision/trade-off:** keep execution disabled vs evaluate a dedicated container/VM/
  sandbox. Adopt only a tested boundary for explicit targets; defer technology choice;
  reject permissive fallback or a host process/env filter masquerading as isolation.
- **Acceptance:** **CAP-EXEC.A1** synthetic secret/file/egress/process/output/resource
  denial matrix and stale approval/manifest tests observe no forbidden effect.
  **CAP-EXEC.A2** cancellation/cleanup/redirect/DNS/project-access cases pass on the exact
  approved profile; separately authorize controlled runs, without claiming universal safety.

## CAP-RECOVERY - Durable effects and operational recovery

- **Problem/benefit:** restart or cancel without duplicating charged work/target mutations.
- **Required behavior:** stable effect/attempt identity, pre-dispatch budget reservation,
  duplicate reconciliation, explicit uncertain outcomes, stale-result rejection and verified
  worker cancellation; backups/restores and inspectable versioned workflow state.
- **Invariants:** checkpoint/lease expiry is not proof an effect stopped; uncertain target
  mutations cannot auto-repeat. Do not promise exactly-once browser effects.
- **Current evidence:** M0 same-request review/transaction recovery is verified;
  [legacy resume](../app/core/react_controller.py#L771) and application effect recovery are
  unverified. [ADR-06](adr/06-persistence-replay.md) owns the design, beyond M0 still proposed.
- **Delivery/dependencies:** M4 reservations/fake effects, M5 cancellation, then operations;
  M2 input revisions, M3 outcomes and CAP-DATA backup/retention decisions.
- **Decision/trade-off:** restart-only vs app records plus checkpoints; adopt a simple
  local transactional design first, defer leases/fleets until needed, reject blind retries
  or automatic legacy-checkpoint migration without compatibility decisions.
- **Acceptance:** **CAP-RECOVERY.A1** crash matrix before/after reservation, dispatch,
  evidence and acknowledgment preserves budgets and exposes uncertain effects; duplicates
  do not dispatch again. **CAP-RECOVERY.A2** stale worker/cancellation, disk-full and restore
  drills retain identities/evidence and never invent success; power-loss limits explicit.

## CAP-DATA - Data lifecycle and project governance

- **Problem/benefit:** prevent private requirements, source, credentials and evidence from
  leaking or being retained/migrated without an operator's policy.
- **Required behavior:** classify data; govern provider/export permissions, redaction,
  project-scoped access, retention/deletion of caches/checkpoints/artifacts/telemetry and
  backups; recoverable sanitized exports/migrations and operational access/runbooks.
- **Invariants:** private raw data stays out of Git/public showcase; no raw credentials
  in new state; hashes/reviewer labels are not authentication. Tenant/role claims require
  an authenticated boundary and tested isolation, not just project ID fields.
- **Current evidence:** M0 bounds paths/inputs and preserves history; [legacy storage](ARCHITECTURE.md#provider-routing-and-persistence)
  has shared/sensitive data and no complete retention/access policy. [M0 limits](M0_VERIFICATION.md#local-use-and-remaining-limits)
  exclude hardware durability, hostile same-user access and operational backup tooling.
- **Delivery/dependencies:** data/operations before hosted access or telemetry export;
  CAP-PORT/OBS/SHOWCASE/RECOVERY share the same policy. M0 immutable retention remains
  unchanged; any destructive purge needs new scope/compatibility/authorization.
- **Decision/trade-off:** private single-operator filesystem first vs authenticated service.
  Adopt broader access only for actual users; defer multitenancy; reject unrestricted
  exports or deletion that silently breaks retained authority/evidence relationships.
- **Acceptance:** **CAP-DATA.A1** synthetic-secret and cross-project access/export cases
  deny unauthorized disclosure, including logs/screenshots/prompts/backups.
  **CAP-DATA.A2** approved retention/deletion/restore/migration drills account for all data
  classes, retained-history constraints and inaccessible copies; publish limitations and
  tested recovery objectives instead of inventing availability/privacy guarantees.

## CAP-AUTHENV - Authentication-aware discovery and environment identity

- **Problem/benefit:** discover and test the intended application identity/environment
  without mistaking navigation visibility, stale sessions or a different tenant for
  valid access or a business failure.
- **Required behavior:** versioned profiles for local development, shared development,
  QA/testing, staging and separately authorized production. Bind exact application/IdP
  destinations, build, issuer/audience/tenant, accounts/roles, secret/session references,
  datasets/reset ownership, permitted mutations and budgets. Resolve actual auth setup;
  neither equality nor difference between development/production is assumed. Keep
  anonymous and role/tenant discovery observations distinct, with freshness and unknowns.
  Verify intended identity before protected discovery; share that binding with later
  execution. Scope session reuse, expiry, revocation and supported refresh; otherwise
  block or request explicit human intervention. OTP/MFA/CAPTCHA use only authorized
  provider test modes, dedicated least-privilege test identities or human checkpoints.
- **Invariants:** a missing guest link does not prove protection; successful login does
  not prove authorization. No silent guest fallback reported as authenticated success,
  cross-role/tenant state reuse or secret/OTP/raw-session export. An auth test mode is
  not production bypass permission. IdP redirects, HTTP/browser requests and refresh
  must obey explicit destination/action/budget policy. Refresh does not authorize replay
  of uncertain mutations. Browser contexts do not replace worker isolation.
- **Current evidence:** [auth handler](../app/core/auth_handler.py#L21) and
  [crawler](../app/core/route_crawler.py#L306) provide actual partial plumbing;
  F02/F09/F10 remain open. [Domain review](DOMAIN_WORKFLOWS_REVIEW.md) classifies exact
  implemented/defective/unverified guarantees and official research. This requirement
  does not claim any live provider/auth/session test has passed.
- **Delivery/dependencies:** AUTHENV contract/fake-fixture design before any protected
  discovery/execution integration; identity/data/target permissions with CAP-EXEC/DATA,
  finite effects with CAP-RECOVERY/M4 and real adapters inside the M5 boundary. No need
  to implement it inside M2-R or make manual offline design depend on authentication.
- **Decision/trade-off:** explicit local profile + small identity/session interfaces first;
  compare per-case login, scoped reusable state and supported test-mode/API setup. Defer
  a broker/vault/emulator integration until a named provider/profile justifies it.
- **Acceptance:** **CAP-AUTHENV.A1** a synthetic five-environment/two-role/two-tenant
  permission matrix denies mismatched destination/issuer/account/mutation/reset/budget
  use, preserves full version/provenance, and never infers production authorization.
  **CAP-AUTHENV.A2** owned fixtures distinguish public-unlinked, protected-linked,
  HTTP-200 login pages, true denied access, expired state and role/tenant differences;
  discovery observations cannot manufacture the reviewed access-control oracle.
  **CAP-AUTHENV.A3** fake session reuse/expiry/logout/role-change/refresh and concurrent
  account-data cases enforce identity/freshness isolation; secret sentinels never enter
  plans/packages/graphs/reports/logs; discovery/execution bindings match. Actual profile
  compatibility later requires separately authorized controlled evidence.
  **CAP-AUTHENV.A4** test-mode and human-challenge cases bind project/run/attempt/identity,
  reject stale/expired/replayed responses, expose waiting/blocked/cancelled states and
  make no protected/model/target dispatch on timeout/denial; bounded audit/cleanup is
  explicitly permitted. Redirect/subrequest/refresh destination cases obey
  policy; test integrations cannot select production credentials or weaken its defenses.

## CAP-MANUAL - Manual cases, incremental design and selective automation

- **Problem/benefit:** support manual test design/review/export and optional automation
  as distinct workflows, without manufacturing code or dropping project scope.
- **Required behavior:** derive/import repeatable cases with setup/data, ordered actions,
  observable expected checks, provenance, stable logical identity and immutable revisions.
  Link exact baseline criteria and M1 scenarios where applicable; support manually
  testable automation-unsupported criteria without altering M1's automation-only rules.
  Keep case review distinct from baseline/plan/package authority. Export/import IDs,
  revision/review state and unresolved gaps; retain external IDs in explicit namespaces.
  Record manual executions and evidence with human attestation provenance. Support A-F
  workflows in [the domain review](DOMAIN_WORKFLOWS_REVIEW.md): new design, case-first
  automation, existing-case augmentation, incremental additions, selected suites and
  revision/impact history. Use explicit frozen automation selection and exclusion reasons,
  retaining the full project inventory and identifying uncertain impacts.
- **Invariants:** importing a case/approval flag or changing a title cannot grant review
  or erase distinct cases. Manual expected checks cannot replace an M0 business oracle.
  No mandatory auth/crawl/provider/generated execution for manual design/export. Selection
  is not automation-support status; unselected criteria remain visible. Existing M1/M2
  blocked assessments cannot become ready through a new caller flag or review alone.
- **Current evidence:** [legacy TestCase](../app/schemas.py#L150) is TypeScript-oriented;
  M0/M1/M2 provide identities and revisions, not manual-case review/execution authority.
  No reviewed manual import/export/impact pipeline is claimed implemented.
- **Delivery/dependencies:** separately scoped MANUAL design/review/export specification,
  then manual execution records and selection/impact policy as needed. It can precede
  workers. M2-R remains plan/package review only; partial automation needs its own
  compatibility/selection decision before generation integration, not an M2 readiness patch.
- **Decision/trade-off:** export M1 prose as an explicitly unreviewed draft is simpler,
  but does not meet full manual-case requirements. Prefer a small criterion-linked
  immutable case lifecycle; reconsider a general scenario schema only for demonstrated
  manual reuse needs. No new agent/framework is required.
- **Acceptance:** **CAP-MANUAL.A1** synthetic imports/designs preserve IDs/provenance,
  source negation/thresholds, multiple cases, expected checks and unsupported/manual-only
  criteria; unknowns stay blocked. Same title never deduplicates a distinct case;
  imported approval cannot approve a case or change the baseline oracle.
  **CAP-MANUAL.A2** case review/revision/export/import and manual campaign fixtures retain
  originals, record exact versions/attestations and pass/fail/blocked/not-run/unknown
  outcomes; never claim automated evidence or approve on timeout. Design/export makes
  no auth/crawl/provider/worker calls.
  **CAP-MANUAL.A3** A-F incremental/selection fixtures retain the full baseline and all
  not-selected/unbuilt/unsupported scope, propose explicit affected sets after criterion,
  scenario, case or shared-file changes and require new effective reviews where needed.
  Uncertain impacts abstain; historical evidence is never rebound to a new revision.

## CAP-COVERAGE - Test-design methods and truthful coverage

- **Problem/benefit:** show what is designed, selected, executed and supported by evidence
  without treating test count or green tests as complete requirements satisfaction.
- **Required behavior:** maintain a reviewed finite design-obligation inventory and
  method/risk/applicability policy. Assess positive/negative, partitions, boundaries,
  decision/state models, roles/tenants, risk, constrained combinatorial strength,
  property/metamorphic invariants and concurrency/recovery/rare high-impact conditions
  where relevant. Keep unknown business expectations visible. Proposed measurement
  policy **ATS-COVERAGE-2026-10-25-v1**, with the exact definitions/denominators in
  [DOMAIN_WORKFLOWS_REVIEW](DOMAIN_WORKFLOWS_REVIEW.md), distinguishes requirement
  disposition, scenario design, manual execution, automation, execution completeness,
  evidence-backed criterion coverage and defect detection effectiveness.
- **Invariants:** no exhaustive-coverage promise; no percentage without frozen scope,
  policy version and numerator/denominator ID sets. Unsupported/unresolved/not-selected/
  excluded/blocked/missing remain explicit; full-project scope is not replaced by the
  selected subset. Empty denominator is N/A. Duplicate titles/tests/retries/foreign IDs,
  skipped or expected-failure runner success cannot inflate positive evidence. Manual
  attestation and trusted automated evidence retain different provenance.
- **Current evidence:** M1/M2 counts prove structural inventory/mapping, not semantic
  coverage. [Legacy report](../app/core/evaluator_engine.py#L400) and F05 remain defective;
  proposed M3 is not implemented. Product benchmarks have not been run.
- **Delivery/dependencies:** COVERAGE policy/fixture specification before new reported
  metrics; MANUAL for cases/campaigns, M3 for automated set reconciliation, CAP-EVAL/LAB
  for adequacy/defect sensitivity. No new runtime parser or measurement code in this review.
- **Decision/trade-off:** workload counts are simpler and useful when explicitly labeled;
  they cannot substitute for evidence/coverage. Prefer exact sets and visible gaps to an
  aggregate model-generated score; add weighted metrics only with retained raw measures.
- **Acceptance:** **CAP-COVERAGE.A1** deterministic fixtures exercise every proposed measure,
  zero denominators, no-criterion requirements, unsupported/unresolved scope and versioned
  exclusions. Ten criteria with six supported by valid evidence yields full 6/10, while
  an eligible-only 6/7 view is separately labeled; subset selection cannot make project
  coverage 100%, and duplicate/foreign passes contribute nothing.
  **CAP-COVERAGE.A2** reviewed design datasets include the named techniques with finite
  obligations, feasible combinations, risk rationale and justified N/A cases; omitted
  high-impact/negative/role/boundary/transition obligations remain visible. Pairwise or
  property generation cannot claim unmodeled combinations/relations were covered.
  **CAP-COVERAGE.A3** held-out paired good/seeded-defect evaluations report obligation
  precision/omission, retained defect sensitivity, false alarms/causal attributions,
  abstentions, invalid trials, per-risk sample sizes and uncertainty. Generator/retrieval
  cannot access held-out labels. Release thresholds require owner-reviewed baseline evidence.

## Domain-specific additions to existing capability owners

These additions fill material gaps; original CAP obligations remain unchanged.
No second model-routing, source-aware, observability, UI, lab or cloud specification
is introduced. [The domain review](DOMAIN_WORKFLOWS_REVIEW.md) owns the decision
rationale and example journeys; this register owns the required acceptance evidence.

- **CAP-WORKFLOW.A3:** fake entry/stop/restart matrix supports manual-design/export,
  case import/augmentation, incremental planning, selected automation and future execution
  as independent requested outcomes. No mode triggers an unrequested auth/crawl/build/
  provider/tool effect. Every normal terminal path reports completed/partial/blocked/
  cancelled/failed truthfully; resume/revision cannot reuse stale eligibility.
- **CAP-EFFICIENCY.A3:** context/cache/retrieval fixtures isolate project/environment/
  tenant/role/build and exact baseline/plan/package/case/prompt/model/policy versions as
  applicable. Missing/freshness-unknown keys deny reuse; compare saved work against
  retained assertion fidelity and defect sensitivity, not reduced test inventory.
- **CAP-HITL.A3:** representative manual editing/review/export, selection, environment/
  role discovery, OTP checkpoint, stage/log/evidence/coverage and diagnosis/repair journeys
  expose actual backend states/revisions/permissions and incomplete scope. Keyboard,
  screen-reader, focus/contrast/reflow and accessible challenge tasks meet the existing
  ROADMAP WCAG 2.2 AA target when implemented; report actual findings and unsupported
  actions. No fabricated progress/ETA or secret-bearing general feedback channel.
- **CAP-OBS.A3:** synthetic trajectories correlate environment/build/identity references,
  manual-case/campaign/selection revisions and auth-challenge lifecycle with existing
  artifact/model/tool/worker attempts. Missing or unknown usage/state is explicit; no
  OTP/session/credential data in operational events, public evidence or model context.
- **CAP-EVAL.A3:** extend the existing held-out corpus with manually adjudicated design
  obligations, imported cases, incremental/selection changes, role/tenant/challenge and
  rare high-impact examples. Preserve adjudicator disagreements/equivalent valid designs;
  evaluate completeness and safe abstention separately from cost, runtime pass rate or
  text similarity. CAP-LAB/DIAG already own reference builds and defect sensitivity.

## Approval boundary and open decisions

No implementation is authorized by recording these requirements. Profile choices,
adapter schemas, reviewer roles, data classes/retention, run modes, budgets, taxonomy,
model quality thresholds and accessibility targets need decisions at their delivery gates.
Numerical quality/cost/latency targets require a measured baseline and owner agreement.
No model/vendor, cloud, trace backend, dynamic plugin system or orchestration replacement
is selected. M0 constraints stand. [M1 v2](M1_AUTHORITY_BOUND_PLANS.md) was subsequently
explicitly approved and [implemented offline](M1_VERIFICATION.md); that approval covers
only its plan subsystem, not the deferred product capabilities in this register.
