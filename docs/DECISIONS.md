# Decisions and proposals

Baseline recorded 2026-10-22; architecture handoff updated 2026-10-23. Read [CURRENT_STATE](CURRENT_STATE.md) and
[AUDIT_FINDINGS](AUDIT_FINDINGS.md) before using this register. Implemented behavior
is described in [ARCHITECTURE](ARCHITECTURE.md); proposed work is sequenced in
[NEXT_STEPS](NEXT_STEPS.md).

## Accepted constraints

These reflect explicit user direction, not approval of a new runtime architecture.

| ID | Status | Constraint |
| --- | --- | --- |
| C01 | ACCEPTED | The completed audit is the factual baseline; preserve evidence/uncertainty distinctions. |
| C02 | SUPERSEDED IN SCOPE | The initial six-document-only phase is complete. C08/C09 record completed Git work; C10 defines the current documentation-only task. |
| C03 | ACCEPTED | Preserve useful current LangGraph functionality; do not describe proposals as implemented. |
| C04 | ACCEPTED | Do not initialize Git, overwrite history, or connect a remote without approval. |
| C05 | ACCEPTED | Preserve requirements/assertions; independently assess suggestions; never invent passing verification. |
| C06 | ACCEPTED | Keep secrets and sensitive environment values out of documentation. |
| C07 | ACCEPTED | Broader AI technology research is paused. Future work must be explicitly scoped. |
| C08 | ACCEPTED 2026-10-22 | User authorized root/provenance checks, safe exclusions, local Git initialization if absent, and an initial source/documentation commit. Publication requires separate approval of exact destination, visibility, and inventory. See [GIT_PREPARATION](GIT_PREPARATION.md). |
| C09 | APPROVED AND COMPLETED 2026-10-23 | User explicitly approved remaining Git setup: private `rohit-0604/ats`, reviewed 51-file initial snapshot. Creation, origin, push and matching SHA/private visibility were verified in that turn. This does not authorize later pushes or public release. |
| C10 | APPROVED SCOPE 2026-10-23 | User authorized saving ADRs/M0/roadmap and updating/reviewing documentation only. No application implementation, dependency install, provider call, generated execution, deployment or GitHub publication. |
| C11 | APPROVED SCOPE 2026-10-23 | User subsequently authorized review and one local commit of the 15 architecture/handoff documentation files, with message `docs: preserve ATS architecture decisions and M0 specification`. Stop after the local commit; no push, implementation, history rewrite or deployment is authorized. |

## Foundational ADR register and implementation status

**No foundational runtime implementation is approved by the handoff request.**
Provisional acceptance of a direction is not acceptance of every schema, security
assumption, migration or milestone. The ADRs are self-contained proposals; the
[review index](adr/README.md) preserves criticism of earlier recommendations.

| Record | Status | Relationship to earlier proposals |
| --- | --- | --- |
| [ADR-01: versioned baselines/oracle authority](adr/01-versioned-baselines.md) | PROPOSED | Refines D02; authority is distinct from hashes and legacy flags. |
| [ADR-02: deterministic LangGraph lifecycle](adr/02-deterministic-lifecycle.md) | PROPOSED | Refines D01; policy code rather than a second graph framework. |
| [ADR-03: artifact identity/approval/results](adr/03-artifact-identity.md) | PROPOSED | Extends D01/D02; approval covers final executable bundle and shared dependencies. |
| [ADR-04: isolated execution](adr/04-isolated-execution.md) | PROPOSED | Refines D03; worker contract first, technology still undecided. |
| [ADR-05: diagnosis and safe repair](adr/05-safe-repair.md) | PROPOSED | Refines D02; reviewed hypotheses, no automatic assertion changes. |
| [ADR-06: persistence/replay/evidence](adr/06-persistence-replay.md) | PROPOSED | Application records plus checkpoints; no exactly-once claim for target effects. |
| [M0: Versioned Baselines and Review Records](M0_VERSIONED_BASELINES.md) | PROPOSED; NOT IMPLEMENTED | Narrow subset of ADR-01/06; precedes eligibility/reconciliation work. |
| [Broader roadmap](ROADMAP.md) | PROPOSED | Retains D04-D07 and product/UI/lab/observability/evaluation/security/deployment work. |

The previous first milestone, offline eligibility and result reconciliation, is
superseded **in ordering**, not discarded. It consumes baseline/review authority
from M0 and retains its acceptance cases in ROADMAP and ADR-03. Saving the revised
proposal does not approve M0 implementation.

## Recommendations awaiting an implementation decision

| ID | Proposal and justification | Simpler alternative / trade-off | Validation and maintenance |
| --- | --- | --- | --- |
| D01 | Retain LangGraph nodes/checkpoints; make lifecycle, approval, and budgets deterministic (F04/F07). | Validated LLM planning only for ambiguous recovery; deterministic routing loses some flexibility but is easier to test. | Compare recovery quality, unsafe transitions, latency/cost on fixed cases; maintain transition contracts. |
| D02 | Preserve immutable approved criteria and evidence; separate inferred suggestions and repair proposals (F01/F05/F06). | Initially freeze baseline JSON and require human review of oracle changes; simpler than a new adjudication agent. | Seed genuine defects and faulty tests; verify no silent oracle change; maintain criterion schemas. |
| D03 | Isolate generated execution with per-run artifacts and explicit network/secret policy (F02/F03/F10). | Disable generated execution while validating artifacts offline; a subprocess/env filter alone is insufficient isolation. | Test filesystem, egress, process, timeout, and credential boundaries; worker operations add maintenance. Hosting/isolation technology is unresolved. |
| D04 | Add small typed page/component objects and fixtures through the existing generator. | Functions suffice for isolated actions; avoid universal inheritance or another runtime agent. | Change a shared locator once; affected specs remain traceable and testable. Maintain multi-file artifact/import contracts. |
| D05 | Retain retrieval provisionally and quarantine unverified lessons. | Curated JSON recipes may be sufficient for a small corpus; semantic retrieval adds dependencies and tuning. | Held-out memory-on/off comparison, tenant/domain isolation, provenance and freshness. No benefit assumed. |
| D06 | Build a minimal development harness: instructions, specs, offline tests, types/lint, then CI. | Plain repeatable commands before hooks/skills/custom platforms. | Prove commands locally and in a clean environment; add automation only for demonstrated repetition. |
| D07 | Align direct dependencies and lock a tested runtime/browser baseline (F12). | A constrained requirements file may be simpler than changing package managers; avoid freezing incidental packages. | Clean setup plus import/contract checks; maintain intentional upgrades and compatibility evidence. |

None of D01-D07 is implemented or authorized by the documentation request.

## Unresolved decisions

- M0 approval prerequisites: designate the local reviewer; approve whole-baseline
  review and mandatory legacy re-review; decide unsupported-criterion policy and
  active-baseline revocation/reactivation semantics. Confirm exact V1 constraints
  and canonicalization before coding. See M0's approval checklist.
- Git destination is resolved for the private initial snapshot (`rohit-0604/ats`).
  Prior upstream history remains unknown; public release/licensing and additional
  publication require their own scope. Git approval is not feature approval.
- Which requirement types belong in the first product scope? How are unsupported,
  ambiguous, and inferred requirements represented and approved?
- Who may approve changed expected behavior? What evidence distinguishes a test
  defect from an application defect, and when must the system abstain?
- What should extract-only/codegen-only guarantee about network activity and outputs?
- What are the result/coverage definitions and CLI exit statuses for partial,
  unknown, blocked, budget-exhausted, and infrastructure-failed runs?
- What destinations, redirects, private addresses, state-changing actions, and
  credentials are authorized for a run? What isolation environment enforces this?
- What data may reach external model providers, and what retention/access policy
  applies to SRS content, snapshots, auth artifacts, checkpoints, and memory?
- Is the first release a single-user CLI or a concurrent/multitenant service?
  Current shared directories/state do not establish multitenant safety.
- Which Python/Node/browser versions and dependency workflow will be supported?
- What labeled evaluation corpus and minimum quality criteria justify expanding
  autonomous repair, retrieval, or planning?

## Updating decisions

For a consequential approved choice, record date, scope, owner/authorization,
evidence, alternatives, trade-offs, acceptance checks, and superseded decisions in
this file. Keep proposals labeled PROPOSED until decided; do not infer product
approval from permission to write documentation.

## Existing research references

These were consulted during the completed audit. No new technology research is
required to resume the first offline milestone. Recheck version-specific details
only when an authorized change requires them.

- [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex skills](https://learn.chatgpt.com/use-cases/reusable-codex-skills)
- [Codex MCP](https://developers.openai.com/codex/mcp)
- [Codex security and hook limitations](https://learn.chatgpt.com/docs/enterprise/security-cookbook)
- [LangGraph graph API and recursion limits](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Playwright POM guidance](https://playwright.dev/docs/pom)
- [Playwright assertions, including counts/CSS](https://playwright.dev/docs/test-assertions)
- [Playwright TypeScript: separate type checking required](https://playwright.dev/docs/test-typescript)
- [Google SDK libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Ruff](https://docs.astral.sh/ruff/), [incremental mypy](https://mypy.readthedocs.io/en/stable/existing_code.html),
  [pytest mocking](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
