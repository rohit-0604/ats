# Domain workflows, authentication and coverage review

Revision: **DOMAIN-REVIEW-2026-10-25-v1**. Documentation and requirement proposals only.
This focused review answers the post-M2 domain request; it does not reopen completed
milestone implementations, accept a full ADR or authorize any integration/implementation.
[CAPABILITY_REQUIREMENTS](CAPABILITY_REQUIREMENTS.md) owns product requirements;
[ROADMAP](ROADMAP.md) owns sequencing. This document owns the evidence assessment,
terminology, proposed measurement definitions and decision rationale, not new wire schemas.

## Evidence and scope

Starting state: clean `main` at `b94d76da1a09d6b3df220965c1c7f14884ca394c`, two
commits ahead of the locally recorded `origin/main`. No remote query was made.
[M0](M0_VERIFICATION.md), [M1](M1_VERIFICATION.md) and [M2](M2_VERIFICATION.md)
record offline verification; M2's final report is **116 passed in 66.165 seconds,
zero failures/errors/skips**. This review read the evidence and contracts; it did not
rerun that suite or validate authentication, a target, a provider or generated code.
No clean-install, live quality, authentication interoperability or security-conformance
claim follows from the offline results. Existing F01-F17 remain open.

Read-only metadata confirms LangGraph 1.1.1, Python Playwright 1.58.0 and installed
Node Playwright 1.58.2. Current official documentation below informs concepts, not a
claim that new APIs have been tested on those versions. No new SDK, worker or vendor
is selected. Focused source inspection covered auth/crawl, graph/planner, generation,
evaluation, HITL, routing/memory and M0/M1/M2 boundaries. Private resource/auth files
and historical target artifacts were not read or copied into this review.

Status meanings: **IMPLEMENTED AND VERIFIED** requires existing scoped execution
evidence; **IMPLEMENTED BUT DEFECTIVE** has concrete source contradictions or existing
finding evidence; **PARTIALLY IMPLEMENTED** has useful pieces but missing guarantees;
**DOCUMENTED BUT UNIMPLEMENTED** has an explicit proposed obligation; **NOT DOCUMENTED**
means no adequate explicit requirement was found before this review; **UNVERIFIED**
means evidence does not establish the claim. Source-confirmed defects below were not
newly reproduced against a live application. A subsystem can have different statuses
for different guarantees; presence of code is not verification.

## Current capability matrix

| Concern / precise guarantee | Status at review start | Evidence and consequence |
| --- | --- | --- |
| Immutable baseline, explicit baseline review, history/revocation | IMPLEMENTED AND VERIFIED offline | [M0 verification](M0_VERIFICATION.md), [ReviewStore](../app/core/review_store.py#L253); approvals bind exact baseline content, under single-operator trust |
| Multi-scenario planning and complete criterion dispositions | IMPLEMENTED AND VERIFIED offline | [M1 contracts](../app/plan_contracts.py#L124), [policy](../app/core/plan_policy.py#L18); no manual-case or plan approval |
| Final candidate bytes, test/config identities and mapping assessment | IMPLEMENTED AND VERIFIED offline | [M2 verification](M2_VERIFICATION.md), [manifest](../app/artifact_contracts.py#L342); closure unverified and authority literal false |
| Form login, bearer acquisition and API-key/header plumbing | PARTIALLY IMPLEMENTED | [handle_auth](../app/core/auth_handler.py#L21), [headers](../app/core/auth_handler.py#L257); actual provider/session success is UNVERIFIED |
| Positive authentication success/failure distinction | IMPLEMENTED BUT DEFECTIVE (source) | [form login](../app/core/auth_handler.py#L60) saves state after navigation heuristics and logs success; exceptions continue without authentication. Missing credentials return the same context type without an explicit blocked outcome |
| Explicit login endpoint propagation | IMPLEMENTED BUT DEFECTIVE (source) | [context construction](../app/core/auth_handler.py#L34) does not copy configured login_url although the [login routine](../app/core/auth_handler.py#L79) consults it; endpoints can instead be guessed |
| Public/protected route classification | IMPLEMENTED BUT DEFECTIVE (source) | [guest link scan](../app/core/route_crawler.py#L172), [set subtraction](../app/core/route_crawler.py#L338); absence from homepage anchors is labeled auth-only, without checking access |
| Authenticated selector extraction and observed API paths | PARTIALLY IMPLEMENTED | [browser context](../app/core/route_crawler.py#L219) reuses storage state/headers; [capture](../app/core/route_crawler.py#L230) records paths, not API contracts. Pages receive a precomputed auth label |
| Guest and multiple-role discovery without privilege leakage | PARTIALLY IMPLEMENTED for guest/single context; DOCUMENTED BUT UNIMPLEMENTED for role guarantees | [AuthContext](../app/schemas.py#L16) is singular, with no role/tenant/environment identity; [CAP-EXEC/DATA](CAPABILITY_REQUIREMENTS.md) already require isolation. No complete role matrix or cross-role tests |
| Safe authenticated-state reuse, expiration and token refresh | PARTIALLY IMPLEMENTED for file reuse; NOT DOCUMENTED adequately for lifecycle | [storage save](../app/core/auth_handler.py#L121), [storage load](../app/core/route_crawler.py#L220); no explicit freshness/refresh/challenge state machine found. Actual expiry handling is UNVERIFIED |
| Credential/session confidentiality | IMPLEMENTED BUT DEFECTIVE (source) | Raw username/password/API key in [AuthContext](../app/schemas.py#L16); [graph serialization](../app/core/react_controller.py#L338) persists its dump, token overloaded into login_url at [bearer handler](../app/core/auth_handler.py#L134). F02/F09 remain open |
| Discovery and generated execution share the intended identity | IMPLEMENTED BUT DEFECTIVE (source) | Crawler accepts state/headers; [generator prompt](../prompts/agent_b_codegen_v1.txt#L34) asks for an env-based login preamble, while [runner](../app/core/evaluator_engine.py#L106) and [config](../playwright_project/playwright.config.ts#L29) have no equivalent role/session binding; F09 |
| Destination/redirect/mutation policy | IMPLEMENTED BUT DEFECTIVE (source) | [_spider](../app/core/route_crawler.py#L111) uses substring-style host membership, unrestricted redirects and incomplete recursive skip handling; [F10](AUDIT_FINDINGS.md#f10---crawling-lacks-consistent-destination-and-skip-enforcement). Discovery and endpoint guessing can cause real requests |
| Environment profiles: local/shared-dev/QA/staging/authorized-production | PARTIALLY IMPLEMENTED for URL/resource configuration; NOT DOCUMENTED adequately for full domain model | [resource loader](../main.py#L54), [DomainProfile](../app/schemas.py#L72); no verified versioned environment/tenant/account/reset/mutation/budget binding |
| OTP/MFA/CAPTCHA authorized test mode or explicit human checkpoint | NOT DOCUMENTED adequately; implementation UNVERIFIED/absent in inspected paths | Roadmap already excludes bypass; no dedicated challenge lifecycle in [auth handler](../app/core/auth_handler.py). New CAP-AUTHENV preserves legitimate test/human paths |
| SRS to manual cases, review/export, manual execution records | NOT DOCUMENTED adequately; DOCUMENTED BUT UNIMPLEMENTED after this review | [legacy TestCase](../app/schemas.py#L150) requires ts_code/spec_file; [M1 scenario](../app/plan_contracts.py#L124) is a proposal, not a reviewed manual procedure with recorded execution |
| Import/augment existing cases; incremental additions; selected automation | PARTIALLY IMPLEMENTED foundations | Saved [legacy requirements](../app/core/react_controller.py#L359), M0 successor revisions and M1 stable keys exist. Reviewed manual import/selection/impact workflow absent; legacy load auto-approves and [deduplication](../app/schemas.py#L187) removes same-requirement scenarios |
| Domain test-design methodology and finite design obligations | DOCUMENTED BUT UNIMPLEMENTED for broad negative/boundary goals; NOT DOCUMENTED for complete method/obligation policy | [evaluation plan](ROADMAP.md#model-and-agent-evaluation) names omissions/roles/boundaries; no maintained equivalence/decision/state/pairwise/property corpus or formal adequacy policy found |
| Coverage percentages and complete result reconciliation | IMPLEMENTED BUT DEFECTIVE legacy metrics; DOCUMENTED BUT UNIMPLEMENTED M3 | [build_report](../app/core/evaluator_engine.py#L400) divides passing-ID count by approved count and labels pass fraction exec_pct; [F05](AUDIT_FINDINGS.md#f05---result-mapping-and-coverage-are-unsound). M2 expected pairs are not results |
| Several graph modes, model actions, checkpoint/resume | PARTIALLY IMPLEMENTED | [planner mode gates](../app/core/react_controller.py#L125), [graph](../app/core/react_controller.py#L651), [resume](../app/core/react_controller.py#L771); useful branching exists, not one purely linear pipeline |
| Effect-free manual/design entry point, deterministic authority/budgets/finalization | IMPLEMENTED BUT DEFECTIVE for legacy mode guarantees; DOCUMENTED BUT UNIMPLEMENTED M4 | Graph always starts infer/auth/crawl; done can reach END; generation/evaluation counters differ. [F07/F08/F13](AUDIT_FINDINGS.md), ADR-02/06 |
| Human feedback and asynchronous authoritative resumption | PARTIALLY IMPLEMENTED; IMPLEMENTED BUT DEFECTIVE approval handling | [HITL wait](../app/hitl/hitl_manager.py#L76) uses server/thread/file polling and timeout auto-approval; no authenticated revision-bound durable human challenge flow. M0 explicit reviews remain separately verified |
| Routing, context, cache and retrieval | PARTIALLY IMPLEMENTED; measured benefit UNVERIFIED | [router](../app/llm/router.py#L153), [generator context](../app/agents/codegen_agent.py#L117), [memory scopes](../app/memory/agent_memory.py#L1); task tiers/fallbacks/retrieval exist, adaptive quality/global budgets and role/environment freshness do not follow |
| Diagnosis with uncertainty, source-aware workflows | DOCUMENTED BUT UNIMPLEMENTED desired behavior; IMPLEMENTED BUT DEFECTIVE repair baseline | [failure classifier](../app/core/evaluator_engine.py#L188), [repair](../app/agents/repair_agent.py#L196), ADR-05; source/API-contract ingestion missing. Symptoms are not proven causes |
| Telemetry/model evaluations | PARTIALLY IMPLEMENTED telemetry; DOCUMENTED BUT UNIMPLEMENTED maintained runtime/model evaluation corpus | [emit](../app/core/telemetry.py#L39) appends events and suppresses write errors; CAP-OBS/EVAL already cover missing provenance/redaction/accounting/benchmarks |
| Professional UI, public showcase, portable deployment and owned Test Lab | DOCUMENTED BUT UNIMPLEMENTED promised outcomes; runtime compatibility UNVERIFIED | [UI](ROADMAP.md#professional-ui-and-ux), SC-01, PORT and CAP-LAB have separate gates. Static legacy review HTML is not that complete product |

## Domain relationships and workflow recommendations

| Entity | Domain meaning and revision rule |
| --- | --- |
| Requirement | Business need with source/provenance; M0 requirement_id persists across revisions |
| Acceptance criterion | Explicit approved expected behavior within an exact baseline; criterion_id plus baseline_digest pins the oracle |
| Test scenario | Logical situation/condition exercising a criterion, with preconditions and steps. Existing M1 identity is project/criterion/scenario-key scoped; exact prose belongs to plan_digest |
| Manual test case | Proposed separate repeatable procedure with data/setup, ordered actions and observable expected checks, criterion references, version, review, and provenance. Several cases can realize a scenario; no TypeScript required |
| Automated test | Concrete automated realization with explicit scenario/test/configuration mapping; M2 stable test ID plus package digest identifies intent and exact implementation |
| Executable artifact | Candidate specs/helpers/config/fixtures/locks/runtime declarations; exact M2 byte inventory, distinct from permission or verified executability |
| Execution attempt | One future authorized invocation of a selected exact revision/environment/data/identity context. Retries/subattempts retain correlation and evidence; no durable run implementation yet |
| Evidence | Versioned attributable observation: operator attestation or trusted worker output with distinct provenance. Missing/conflicting/unknown observations remain explicit |
| Finding | Reviewed or qualified interpretation supported by evidence; separate expected/observed behavior, cause hypothesis, confidence/uncertainty and adjudication state |

**Recommend a separate manual-case lifecycle**, in a later bounded specification. It
needs repeatable steps/expected observations, imports/exports, review/history and manual
attempt records that M1/M2 do not supply. Reusing legacy TestCase would force ts_code and
inherit mutable approval booleans. Renaming M1 scenarios would imply reviews/expected-step
semantics they do not have. A simple criterion-linked immutable case record and explicit
review is sufficient initially; no second orchestration framework or generic test platform.

There is a compatibility constraint: [M1 policy](../app/core/plan_policy.py#L36) permits
scenarios only for specified, automation-supported criteria; unsupported criteria retain
a disposition with zero scenarios. A manually testable but automation-unsupported criterion
must remain designable later without changing this completed M1 rule. The manual-case
specification should allow exact baseline/criterion references directly, plus an M1
scenario reference when applicable. Do not fabricate M1 scenarios or reclassify support
to fit manual cases. A broader common scenario model is a versioned future alternative,
justified only if real manual workflows require it.

Business expectations remain M0 authority. A manual-case reviewer confirms a procedure
faithfully checks that oracle; a plan reviewer confirms selected design scope; a package
reviewer inspects exact code/dependencies. None approves a changed business expectation.
Per-step expected observations must derive from the criterion or identify an unresolved
business decision; changing the expected count from four to three requires a new baseline,
not merely case/code review. A passing generated test remains an observation, not proof
that the application or test is correct.

| Workflow | Recommended path and explicit stop |
| --- | --- |
| A: SRS to manual design | Extract/import untrusted draft -> clarify/freeze/review M0 -> propose scenarios/cases -> review cases -> export with exact IDs/digests/review status and unresolved/unsupported scope; stop without auth/crawl/codegen |
| B: Reviewed cases to selected automation | Preserve reviewed cases -> explicit versioned automation selection with exclusions/reasons -> propose code -> M2 immutable package -> separate plan/package review -> stop before validation/execution gates unless authorized |
| C: Existing cases | Bounded import with external-ID namespace/provenance -> validate criterion mappings and expectations -> propose augmentation/diff -> explicit case review; imported approval is untrusted, no title deduplication |
| D: Add requirements/scenarios | New M0 successor for requirement/oracle changes; new M1 plan digest for scenario changes. Retain logical keys for same intent, produce impact proposal and re-review affected exact revisions |
| E: Partial automation | Preserve the full baseline/manual design denominator and exact selected subset; not-selected is visible, distinct from unsupported/unresolved/unbuilt. Review selection before generation; no silent omission to get ready |
| F: Revisions/history/impact | Compare immutable IDs/content and shared dependency references; retain originals/results. Changes to baseline/plan/shared files invalidate effective current use as specified; impact analysis proposes affected scope and abstains where uncertain |

Current APIs support parts of D/F, not these complete paths. M2 requires the exact M1
scenario set, and **unbuilt scenarios block readiness**. M1 unplanned criteria also block
its readiness. Partial packages can be frozen as blocked proposals, but cannot become
ready simply through a future approval flag. Selective automation needs an explicit
versioned selection/eligibility policy in a separate contract scope; preserve M0/M1/M2.
Do not shrink the baseline, label not-selected as unsupported, or silently construct an
apparently complete subplan whose omissions disappear from project reporting.

## Authentication and environment design

Research confirms useful primitives, not ATS interoperability: Playwright documents
separate role states, state reuse, expiry replacement and account isolation for shared
mutations; stored state can impersonate accounts and belongs outside repositories.
Browser contexts isolate browser state; they are not ADR-04's untrusted-code worker
boundary. [Playwright authentication](https://playwright.dev/docs/auth),
[browser-context isolation](https://playwright.dev/docs/browser-contexts).

Model a versioned **environment profile** and a separate **identity binding** later.
Names such as staging or production are descriptive risk context; the actual permission
comes from exact destinations, tenant/account references and explicit action scope.
Recommended attributes, not an approved serialization: project/environment/build IDs,
base URL and approved application/IdP origins, issuer/audience/tenant, auth method,
account/role references, permitted read/mutation operations, data/reset policy and owner,
secret/session handles, capability constraints, budgets/deadlines and retention policy.
No credential/OTP/session bytes in plans, package metadata, telemetry or review records.

| Environment | Required distinction; do not infer safety from its name |
| --- | --- |
| Local development | Explicit owned target and isolated data/identity test mode; localhost does not authorize reading unrelated services or host files |
| Shared development | Other users may share accounts/data; name ownership/reset locks and mutation limits before concurrent work |
| QA/testing | Versioned fixture/build/role/tenant matrix, reproducible resets and provider test modes only where authorized |
| Staging | Verify actual IdP/tenant, integrations and data classification; may share production identity or services, so use explicit destinations and credentials |
| Production | Only separately authorized targets/accounts/actions/time windows; default deny mutation unless approved. No assumed test tenant/reset, security bypass or automatic privilege escalation |

Development and production may use the same or different identity setup. Resolve and
verify the selected profile; never derive issuer/tenant/secrets from a mode flag or URL
suffix. Changing identity, reset policy, destinations or allowed mutations changes
eligibility context and requires fresh authorization under the later lifecycle contract.

### Discovery, roles and session lifecycle

1. Enumerate candidate routes from approved inputs; keep observed, inferred and supplied
   candidates distinct. robots/sitemap or an LLM suggestion conveys no crawl permission.
2. Check destination/action budget before every effect, including IdP authentication,
   redirect, browser subrequest, direct HTTP and endpoint guessing. An authorized IdP is
   an explicit separate origin, not a blanket external-network exception.
3. Establish only the requested account/tenant/role; verify a trusted identity outcome
   through a separately authorized nonmutating check. URL change or storage file presence
   alone is insufficient. Auth failure becomes blocked/unknown, never a guest fallback
   presented as a successful privileged crawl.
4. Use a fresh context for anonymous and each role/tenant/account, with scoped state
   references. Record observed URL/status/redirect/identity/build/time and redacted element
   provenance. Do not merge selector catalogs across roles or flatten them by path alone.
5. Classify access observations as observed-content/denied/login-redirect/challenge/
   session-expired/error/unknown, retaining the evidence and freshness. Direct-route checks
   differ from whether navigation exposed a link. Hidden elements do not prove endpoint denial.
6. Authorization correctness needs reviewed actor-resource-action/ownership/tenant
   expectations and separately authorized positive/negative tests. Discovery can suggest
   candidates, but cannot infer access rules or assert absence of privilege defects.

The actor/resource/action and tenant distinction follows
[OWASP authorization regression guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Regression_Testing_Cheat_Sheet.html).
ATS must preserve its own reviewed oracle; importing a matrix is not approval to run it.

Reuse sessions only within the same environment, tenant, account/role, credential and
policy versions, target scope and approved lifetime. Role changes, logout, revocation,
expiry or uncertainty invalidate reuse. Separate mutating accounts/datasets when required;
isolated browser storage does not isolate server-side state. Authentication and test
execution must resolve the same intended identity binding without copying discovery
secrets into generated source. Runtime secret delivery belongs inside the approved worker.
Include environment/role/tenant/build/policy freshness in future cache/retrieval eligibility;
current domain-only memory is insufficient for cross-role selector reuse.

Expired credentials may require reauthentication or provider-specific refresh; neither
is universally available. Budget and record the refresh attempt, verify identity again,
and keep its failure separate from a business assertion failure. Never blindly replay
an uncertain state-changing action after refreshing. Session-expiry testing and privilege
changes need explicit scenarios and server-observed evidence; see
[OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

### Alternatives and authorized challenges

| Alternative | Useful when / trade-off |
| --- | --- |
| Login per case | Simplest freshness/account provenance, useful for authentication tests; slow, rate-limited and not itself an auth correctness oracle |
| Scoped reusable state and small explicit fixtures | Recommended initial application-test approach once isolated execution exists; less repeated login, but needs expiry/identity/account-data invalidation and leak tests |
| Supported API sign-in/provider test tenant | More deterministic setup where an authorized provider exposes it; test flow may differ from real UI login, so keep independent auth-flow coverage |
| Identity emulator | Strong local determinism for supported features; does not prove production federation/MFA interoperability. Add only for a named lab/profile |
| Central vault/session broker | Useful for measured concurrent/hosted needs; premature for a local pilot. Start with narrow secret-reference interfaces and private scoped storage, not a generic identity platform |

For OTP/MFA, prefer provider-supported test identities/modes only within an approved
test environment; otherwise request explicit human intervention or stop unsupported.
Google's Identity Platform documents development test numbers but warns that resulting
identities can have real access, so they still need least privilege and isolation.
[Official test-number guidance](https://docs.cloud.google.com/identity-platform/docs/test-phone-numbers).
For CAPTCHA, a site's approved test integration can use its provider's testing controls;
Google explicitly documents separate test configuration. This does not authorize changing
production defenses or claiming production CAPTCHA was tested.
[Official reCAPTCHA test guidance](https://developers.google.com/recaptcha/docs/faq).
No test keys, OTPs or provider configuration are embedded here.

A human challenge must bind project/run/attempt/environment/identity and current
challenge revision, with expiry, cancellation, denial and safe reissue. Values are
ephemeral secrets; do not log/persist them in general workflow state or exported evidence.
Timeout means waiting/expired/blocked, never approval. CAPTCHA-solving services, automatic
OTP interception and weakening production security controls are outside the recommendation.

## Test-design methodology and coverage

Adopt a reviewed finite design model: criterion -> relevant risks/conditions -> explicit
design obligations -> scenarios/cases -> chosen automated realizations. Record the
technique, constraints, rationale, applicability and unsatisfied obligations with a policy
version. A list of generated scenarios is not an objective completeness denominator.

The foundational methods and risk-based prioritization are supported by
[ISTQB CTFL v4.0.1, chapters 1, 4 and 5](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf).
ATS must adapt them to approved criteria; it cannot promise exhaustive tests of all
possible situations. No method label alone proves the expected behavior was checked.

| Technique | Reviewable obligation / limitation |
| --- | --- |
| Positive and negative | Allowed behavior plus rejected/forbidden behavior, meaningful expected response and retained side-effect evidence; not simply good/bad data labels |
| Equivalence partitions | Justified valid/invalid classes and representatives; record why behavior is expected to be equivalent, revise when evidence contradicts it |
| Boundary analysis | At/below/above relevant thresholds, empty/maximum/missing data and precision/units; avoid inventing thresholds absent from the oracle |
| Decision tables | Feasible combinations of business conditions/actions and explicit don't-care/impossible rules; missing rules remain questions |
| State transitions | Named states, valid/invalid transitions, ordering and session/workflow recovery; include transitions whose effects may be uncertain |
| Roles/permissions | Actor-resource-action plus ownership/tenant/anonymous dimensions, both allowed and denied cases; scope every request before testing |
| Risk prioritization | Severity/likelihood/exposure and rationale, mandatory high-impact cases first; low frequency does not remove catastrophic risks from the inventory |
| Pairwise/combinatorial | Versioned factors/values/constraints and measured t-way interaction coverage; justify interaction strength. Pairwise does not cover every higher-order failure |
| Property-based | Explicit reviewed invariant, valid input generator/domain, seed and reproducible counterexamples; random examples alone are not coverage of the domain |
| Metamorphic | Approved transformation/relation when exact outputs are hard to enumerate; the relation itself needs independent review and can be wrong |
| Concurrency/recovery/timeout | Named interleavings, conflicts, retries, cancellation, resource exhaustion and interruption boundaries; generated schedules cannot prove all interleavings |
| Rare high-impact edges | Privilege changes, cross-tenant access, destructive operations, partial commit/ack loss, empty/vacuous checks and extreme data; retain explicit mandatory cases despite sampling |

Combinatorial measurement should follow a constrained factor model, not a claim about
the number of generated tests. NIST describes t-way coverage measures and work beyond
pairwise; no ACTS tool or new library is required by this review.
[NIST IR 7878](https://csrc.nist.gov/pubs/ir/7878/final),
[NIST beyond pairwise](https://www.nist.gov/publications/practical-combinatorial-testing-beyond-pairwise).
Property/metamorphic/concurrency rows are ATS recommendations; no framework or efficacy
result is inferred from those sources.

### Proposed measurement policy: ATS-COVERAGE-2026-10-25-v1

**PROPOSED, NOT IMPLEMENTED.** Definitions below are product measurement requirements,
not a replacement for M0/M1/M2 wire contracts or evidence of achieved coverage. Every
report pins project, baseline/plan/case/selection/package revisions, environment/build,
configuration, execution/campaign scope, policy version and evidence cutoff where relevant.
Show numerator, denominator and ID-set differences, not only a percentage. Zero denominator
is N/A with a reason, never 100%. Unsupported, unresolved, not-selected, excluded,
blocked and missing outcomes are separate counts, with both full-project and selected-scope
views. Reasons/exclusions require reviewed provenance; never silently reduce the denominator.

Let R be all requirements and C all criteria in the selected baseline. A requirement
with no criteria remains visible as a design gap. Let O be a finite independently
reviewed set of design obligations with criterion references. Unknown/unresolved criteria
cannot fabricate O; report their count beside known-obligation metrics. Let U be frozen
manual case/configuration/data units for a campaign, P frozen automated test/configuration
units for an attempt, and D independently labeled unique defect instances/builds.

| Measure | Proposed numerator / denominator and interpretation |
| --- | --- |
| Requirement disposition coverage | Requirements with an explicit valid disposition, rationale and criterion/design-gap rollup / all R. Deferred, unsupported and unresolved records can be accounted for; 100% means bookkeeping complete, not fully designed or tested. Report criterion disposition counts separately, using M1 only within its supported rules |
| Scenario design coverage | O with at least one reviewed adequate scenario/case mapping / all reviewed applicable O. Keep approved inapplicable obligations in a separate exclusion inventory and show the original total; deferred or undesigned obligations remain open; automation-unsupported obligations can be designed manually. Report unresolved criteria/no-criterion requirements outside O, so a high known-scope score cannot hide undefined scope |
| Manual test execution coverage | Unique U with attributable completed execution evidence and a decisive pass/fail observation / all U planned for the frozen campaign. Blocked/skipped/not-run/unknown are not executed coverage; retain attestation identity/time and original evidence. Repeat runs do not multiply numerator; never call manual attestation trusted worker output |
| Automation coverage | O mapped to current reviewed automated test/package revisions meeting the separately specified validation policy / all applicable O. Also show supported-only eligible mapping rate with its explicit denominator; unsupported/manual-only/unknown scope remains visible in the full view. Draft code, duplicate tests or selecting fewer suites cannot increase project coverage |
| Execution completeness | Unique P with reconciled decisive final pass/fail evidence / all P planned at dispatch. Missing/unknown/interrupted/skipped units are incomplete; infrastructure failures are explicit. Track full accounting of all units separately from actually executed completeness. Preserve retries/flakiness and runner expected-failure semantics; runner acceptance is not positive criterion evidence |
| Evidence-backed criterion coverage | C for which every required obligation/configuration in the reviewed evidence policy has current attributable supporting evidence, with contradictions/unknowns exposed / all C. Show manual-attested and automated/trusted provenance separately, plus partial support. Unsupported/unresolved criteria do not disappear; no one passing test automatically proves a criterion |
| Defect detection effectiveness | Independently confirmed unique detected D / all valid seeded D evaluated under a fixed policy. Count known defects missed/abstained as undetected; report invalid/infrastructure trials separately and a conservative scheduled-trial view. Pair with false alarms on known-good controls, false causal attributions, sample size, per-risk strata and uncertainty. This estimates behavior on the corpus, not all real defects |

Historical metrics stay attached to their original revisions. For future use, revoked
or changed subjects fail fresh eligibility; do not rewrite old observations into new
baseline evidence. Unknown IDs/duplicates/conflicts are quarantined discrepancies, not
additional passes. Titles are display only. Shared assertions cannot be counted multiple
times as independent evidence without explicit attribution. Test counts and risk-weighted
scores may supplement these sets, but cannot replace raw denominators and critical gaps.

Example, deliberately synthetic: a project has ten specified criteria, three automation-
unsupported. Six of the seven supported criteria have evidence satisfying the
reviewed policy. Full criterion coverage is 6/10; an explicitly labeled supported-known
view is 6/7. Selecting just those six is not 100% project coverage. Two unknown passing
test IDs contribute zero; repeating one passing test does not change either numerator.
If a criterion is unresolved or support is unknown, M0 approval is blocked by its
[existing policy](../app/core/baseline_review.py#L20); proposed design-inventory metrics
must not imply execution eligibility. Automation-unsupported criteria may later obtain
manual evidence under their own reviewed case/evidence policy.

### Evaluation design

Extend CAP-EVAL/CAP-LAB, without inventing measured thresholds. Human adjudicators
independently establish design obligations and expected behavior for each dataset item:
roles/tenants, thresholds/partitions, decision rules, transitions, auth challenges,
unsupported/ambiguous requirements, incremental changes and rare destructive/recovery
conditions. Record disagreement, adjudication and acceptable equivalent designs rather
than requiring identical generated prose or one fixed test count.

Measure omission/precision against those obligations, invalid oracle changes, correctly
retained unknowns, unsafe permission proposals and incremental change impact accuracy.
Use paired known-good/seeded-application-defect/test-defect/environment-fault builds with
independent reference checks. A repair passes evaluation only if defect sensitivity is
retained, not merely because it turns a failing test green. Keep failures and abstentions
in the report. Compare routing/context/retrieval policies on the same held-out tasks and
budgets, with versions, tokens/cost/latency, per-risk sample counts and uncertainty.

Split by application/requirement family before authoring/retrieval to reduce leakage;
hold out labels and seeded-defect metadata from generators/models and memory. Use
deterministic fixtures/manual rubric first, calibrated judges only as assistance.
Unit contracts, scenario-design quality, runtime defect sensitivity and operator usability
are distinct evaluations. This review ran none of those product benchmarks.

## Graph, services and development harness

Retain LangGraph where durable long-running branching and human interruption provide
value; existing branching/checkpoints are useful. Ordinary services should own pure
validation, immutable snapshots, review commands, mapping/measurement and exports.
Deterministic lifecycle policy owns legal actions, terminal states and prerequisites;
the model may suggest/rank permitted next steps, never grant tools or budget.
Do not introduce another agent, workflow framework or queue to solve missing domain rules.

| Responsibility | Existing support and recommended boundary |
| --- | --- |
| Entry/stop points | Separate M0/M1/M2 CLIs already demonstrate offline service boundaries. Future manual design/export/import paths must not require discovery/authentication; source/API evidence and codegen/execution are opt-in capabilities |
| Lifecycle/authorization | M4/ADR-02, not graph edges alone. Include proposal/review/waiting/blocked/cancelled/failed/completed and explicit effects per mode. Completed means requested workflow finished, not application correctness |
| Human wait/resume | Durable reviewed commands/challenges, exact subject/run/phase identity, no timeout approval. Current HITL server/thread is not an authenticated resumable authority system |
| Effects/recovery | M4/ADR-06 reservations and unknown usage before any charged/model/auth/target effect; M5 cancellation/worker evidence. Checkpoints cannot establish external exactly-once outcomes |
| Incremental reprocessing | Revision/subject dependency analysis and explicit affected-set proposals; reuse only matching versions/eligibility, preserve unaffected histories and abstain on semantic ambiguity |
| Routing/efficiency | Existing tier/fallback/context/memory are starting pieces. CAP-MODEL/EFFICIENCY already require suitability/privacy/quality/budgets and measured benefits; scope caches by identity/environment/build/permission versions |
| Source-aware/diagnosis | Read-only capability-authorized source/API/log input; no repository build/write merely because reading was allowed. Observations and uncertain hypotheses remain separate from findings and oracle decisions |
| Events/evaluations | Durable application audit records define authority; optional traces expose operations. Version identities and missing telemetry explicitly; sampled traces/model scores cannot approve anything |

LangGraph's official interrupt guidance explains that resumed nodes rerun and prior
side effects need idempotency. This supports the existing ADR-06 boundary rather than
a framework migration. [Official interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts).
Before an eventual migration, test restart after interruption, duplicate command delivery,
stale feedback, ambiguous mutations, all mode boundaries and one terminal finalization.
Keep old checkpoints read-only unless a separately approved compatibility policy exists.

## Professional UI and HITL implications

Use durable domain states and inspectable version links, not a graphic of autonomous
agents. The existing WCAG 2.2 AA target remains in ROADMAP. Status updates must be exposed
to assistive technology, and authentication/challenge interaction must support accessible
completion; these are future acceptance obligations, not conformance established here.
[W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html),
[W3C accessible authentication](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html).

| Journey | Required UI state/evidence and meaningful control |
| --- | --- |
| Manual review/edit/export | Criterion alongside steps/data/expected checks; revision diff and unresolved/unsupported labels; save proposal separately from review, preserve export provenance |
| Select automation | Full project design plus explicit selected scope/reasons, readiness blockers and changed denominators; selection never reclassifies unsupported criteria |
| Configure environment/auth | Exact destination/tenant/role/account references, permission/mutation/data/reset policy and profile diff; secrets entered through private reference flow, not case text |
| Role discovery | Compare redacted observations by role/tenant/build/time, including unknown/redirect/challenge; distinguish observed access from reviewed permission expectation |
| Monitor work | Stage plus planned/processed/remaining/blocked counts, attempt IDs, actual budget use and unknown usage; unknown work total shown as such, no fabricated percentage/ETA |
| OTP/HITL | Pending challenge identity/expiry, secure ephemeral input, accessible labels/focus/paste support where permitted, cancel/reissue/deny; stale/expired response explicitly rejected |
| Inspect progress/logs/evidence | Timeline correlated to exact revisions/attempts, collection gaps/redaction, stable navigation and no auto-scroll focus theft |
| Understand coverage | Full and selected scope side by side, numerator/denominator ID drilldown, excluded/unsupported/not-selected/missing outcomes visible; zero denominator N/A |
| Diagnose/repair | Original criterion, code, observations and cause alternatives before proposal diff; preserve original failure and require new review for changed bytes |

Validate keyboard/screen-reader/reflow/contrast and task completion/error rates for these
journeys before claiming usability. A synthetic UI prototype can precede the backend,
but must label unsupported actions and synthetic states. The public SC-01 remains a
separate sanitized showcase; no private worker or arbitrary URL/upload execution path.

## Consequential domain decisions

All following choices are recommendations for later scoped approval, not implemented
capabilities. CAP IDs below refer to the single register's new/extended obligations.

| ID / WHAT | WHY now / HOW | Simpler alternative and trade-off | Failures / verification / reconsideration |
| --- | --- | --- | --- |
| DW-D01: separate manual-case authority | M1's automation-constrained proposal cannot own manual procedure/review/execution. Add later immutable criterion-linked cases and explicit reviews; optional M1 scenario link | Export scenario prose only: useful draft aid, lacks step expectations/data/review and unsupported-criterion cases. General shared scenario refactor costs more compatibility work | No implicit approval/import flags or oracle replacement; CAP-MANUAL.A1..A3. Reconsider if representative users need only draft exports and accept explicitly weaker claims |
| DW-D02: versioned environment + identity binding | Auth discovery/execution mismatch and raw secrets require one explicit context. Start with a local profile/reference boundary, not a hosted broker | One resource dict is shorter but lacks tenant/role/expiry/mutation identity; login per case offers freshness at extra cost | Cross-role/profile/session/redirect/reset challenges fail closed; CAP-AUTHENV.A1..A4. Reconsider broker/emulator only for real supported provider/concurrency need |
| DW-D03: observations separate from access-control oracles | Homepage link difference cannot prove protection. Record scoped observations and review actor-resource-action expectations independently | Guest/auth route Boolean is cheaper and can be a labeled hint, unsuitable as authority or policy proof | Known public-unlinked/protected-linked/expired/tenant cases remain distinct; CAP-AUTHENV.A2. Reconsider inference only for evaluated advisory ranking |
| DW-D04: finite obligations and versioned set metrics | Test/pass counts inflate completeness. Freeze design/selection/attempt denominator sets and retain unknowns with provenance | Simple counts/percentages are cheaper but acceptable only as labeled workload totals | Duplicate/foreign/missing IDs never improve coverage; CAP-COVERAGE.A1..A3 and M3 fixtures. Reconsider aggregation only with independent validity evidence |
| DW-D05: explicit selective/incremental scope | Product needs partial automation; M2 intentionally blocks unbuilt scenarios. Specify selection/impact policy separately, preserve full baseline | Fully automate every M1 scenario first is the simplest compatible pilot; smaller implicit subplans hide project omissions | Changed scope invalidates relevant effective authority and reports both scopes; CAP-MANUAL.A3/CAP-WORKFLOW.A3. Reconsider exact placement after representative subset/import fixtures |
| DW-D06: services for local commands, graph for long-running orchestration | Existing pure modules already establish the seam. M4 enforces policy/effects; later graph adapter composes it | Plain procedural flow is simplest for offline CLI; retain graph where persisted branching/resume earns its cost | Zero unauthorized effects across entry/stop/restart matrix; CAP-WORKFLOW.A3/RECOVERY. Reconsider graph replacement only on measured operational failure/complexity |
| DW-D07: keep M2-R narrow | Reliable review subjects now exist; manual/env/coverage implementation is unrelated to durable subject decisions | Fold all product features into M2-R: fewer named handoffs, much larger authority/compatibility surface | M2-R scope/evidence boundary below; reconsider only if its actual contracts cannot express plan/package review without one narrowly proven prerequisite |

## Requirement changes and M2-R impact

Three missing owners are added to the register: **CAP-AUTHENV**, **CAP-MANUAL** and
**CAP-COVERAGE**. Existing CAP-WORKFLOW/HITL/OBS/EFFICIENCY/EVAL receive only material
domain acceptance additions. CAP-DIAG/MODEL/PORT/EXT/SHOWCASE/LAB/POM/EXEC/RECOVERY/DATA
retain their existing obligations and links; no duplicate source-aware/router/UI/cloud
platform specification is created. ROADMAP adds explicit domain delivery rows and
manual-only stop journeys. Full ADRs, M0/M1/M2 contracts and verification records remain
unchanged. This review adds no capability implementation or target authorization.

**Exact next recommendation: specify `M2-R - Durable Plan and Whole-Package Review`,
offline only.** This request authorizes the present domain review, not its implementation
or a complete new M2-R wire specification. The next scoped specification should settle:

- Exact discriminated plan/package subjects with project/baseline/plan/package digests;
  separate explicit decisions. Baseline approval does not approve either subject, and
  package approval must not silently create plan/manual-case approval.
- Trusted single-operator review commands initially, outside untrusted subject JSON;
  append-only history, rejection/revocation, request idempotency, stale sequence checks,
  lost acknowledgment/crash recovery and bounded safe inspection. No assumed hosted roles.
- Fresh M0/M1/M2 composition and effective status distinct from immutable historical
  decisions. Approval observations can become stale; separate stores are not atomic.
  M4 later defines authority/dispatch linearization and in-flight revocation. A reviewer
  label or cached response never authorizes execution.
- Whether valid blocked proposals can be inspected/rejected while approval is denied
  until current prerequisite policy holds. Do not change M2 readiness to accommodate
  selection: first M2-R can support fully mapped packages; selective-automation contracts
  remain a separately specified extension. Several packages/configurations may coexist;
  do not copy M0's single active baseline rule blindly into package review.
- An external review/effective-status record, leaving M1 plan_approved and M2
  bundle_approved/execution_authorized literal-false assessment contracts unchanged.
  Reviewing byte content may be useful while closure stays unverified; approval must
  not imply validation, safety, target permission or eligibility to dispatch.
- Offline acceptance: exact subject mismatch, changed shared helper/config/lock,
  separate plan/package decisions, stale/revoked baseline/plan/package, replay/conflict,
  multiple packages, uncertain commit acknowledgment, malicious review display/input,
  no timeout approval/no effects, and unchanged 116-test M0/M1/M2 regressions.

A manual-first next specification is a credible alternative if immediate manual-case
usability is the product priority; it delivers earlier operator value but leaves the
approved automation foundation without durable plan/package reviews. Recommend M2-R
as the next foundation specification because its concrete subjects already exist and
its authority rules are prerequisites for eventual effects. Reorder independent MANUAL
specification work if representative user tasks establish that higher priority; do not
expand M2-R to conceal that product choice.

Do not absorb case import/export/manual execution, OTP/auth/session services, crawling,
environment adapters, subset generation, coverage engine, UI, routing, telemetry,
evaluation infrastructure or workers into M2-R. Design-only manual/selection requirements
and lab/evaluation fixtures can later proceed under independent scoped authorizations.
Controlled automation still waits for M2-R + M3 + M4 + M5, actual validation/closure,
an owned authorized target and an explicit execution gate. A manual-design release need
not wait for a worker, but must have its own truthful case/review/export acceptance.

## Documentation verification

The final documentation review covered eight changed/new Markdown paths, 285 local
links and 127 source/heading anchors; all resolved and code fences balanced.
`git diff --check` passed. All 66 tracked non-documentation files, completed M0/M1/M2
specifications and their verification records are byte-for-byte unchanged against HEAD.
Existing CAP/acceptance IDs and all six SC-01 acceptance rows are preserved; seven
DW-D decision rows and the three new capability owners are present. Common credential
token/private-key patterns produced no matches. This bounded scan is not a claim that
arbitrary future user evidence cannot contain secrets.

Twelve cited official research pages/PDFs were accessed read-only for this review;
older external references elsewhere were not exhaustively rechecked. No live auth,
target/model/provider execution, package installation or application test run occurred.
The 116-test number remains the previously recorded offline milestone result. HEAD
remains the M2 checkpoint; the index is empty and these documentation edits are local,
uncommitted and unpublished. No deployment, commit or push was performed.

## Remaining uncertainty and stop boundary

Confidence is high in the source/contract mismatches and preserving the offline milestones;
medium in the proposed manual-case separation/metrics until representative user cases and
human labeling expose edge cases. No live provider, identity federation, token refresh,
CAPTCHA/MFA integration, product usability or defect-detection benchmark was exercised.
Production data permissions, supported providers/profiles, reset ownership, reviewer
roles and metric/evaluation release thresholds still need explicit decisions at their gates.

Stop after this documentation review. No application changes, new tests/dependencies,
provider calls, target crawling/authentication, generated execution/compilation, M2-R
implementation, commits, Git push, publication or deployment are authorized here.
