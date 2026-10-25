# ATS engineering instructions

## Start here

1. Initially read only this file, [NEXT_STEPS](docs/NEXT_STEPS.md) and
   [CURRENT_STATE](docs/CURRENT_STATE.md).
2. Identify the exact task and latest authorized scope; historical approvals do not
   authorize new work. Check Git status and preserve existing edits.
3. Use the [documentation index](docs/README.md) to retrieve affected CAP sections,
   roadmap dependencies, applicable ADRs/contracts, architecture boundaries and findings.
   Read those before changing their behavior; do not load the entire docs tree by default.
4. Inspect affected source/tests and establish acceptance criteria before coding.
   Verify compatibility and applicable ATS-FIT gates; do not replace checks with assumptions.
5. Update only authoritative documents whose actual status, requirements or decisions
   changed. Link to existing obligations rather than copying the full CAP register.

## Independent engineering judgment

- Treat technical suggestions as hypotheses. Cite source evidence and distinguish
  verified behavior, isolated probes, assumptions, recommendations, and uncertainty.
- For significant changes, state the problem, examine a simpler alternative,
  explain trade-offs, and define evidence that would validate or disprove the choice.
- Challenge unsupported proposals directly; do not invent disagreement or claim
  correctness merely because code exists. Prefer focused, understandable changes.
- Read affected contracts and agree the task's acceptance criteria before coding.
  Do not expand the authorized scope or introduce frameworks without justification.

## Python and LangGraph

- Follow existing Python naming and module boundaries; use explicit types at
  boundaries and validated Pydantic contracts for untrusted data.
- Keep external effects behind replaceable interfaces. Avoid new import-time
  writes/network calls, silent error suppression, and ambiguous success results.
- Keep graph state serializable. Changes to persisted contracts need versioning
  and compatibility decisions. Exclude raw credentials from new persisted state.
- Enforce prerequisites, approval, budgets, and terminal conditions in code.
  LLM suggestions must not override these checks.
- Make replayed effects idempotent; verify interruption/resume when changing
  orchestration. Preserve the existing graph unless a scoped change authorizes it.

## Requirements, Playwright, and POM

- Preserve approved requirement IDs, source evidence, acceptance criteria, and
  expected outcomes. Keep inferred requirements separate until explicitly approved.
- Never weaken an assertion, change an expected value, skip a test, or discard a
  requirement merely to obtain a pass. Unsupported requirements remain visible.
- Distinguish test defects, application defects, environment failures, and unknown
  causes. Preserve evidence and escalate uncertain oracle changes for review.
- Support multiple scenarios per criterion; do not assume one test proves an
  entire requirement. Use explicit IDs for result mapping, not title matching.
- Prefer semantic locators and web-first assertions. Do not hide failures with
  arbitrary first-match selection, sleeps, empty assertion loops, or caught errors.
- For approved POM work, use small typed page/component objects, reusable actions,
  and explicit fixtures. Keep criterion-specific assertions visible in specs or
  named assertion helpers. Avoid a universal base-page hierarchy.
- Validate generated paths, imports, IDs, approval eligibility, syntax, types,
  and execution policy before running generated code.
- Active files in prompts/ override embedded fallback prompts; inspect both when
  changing prompt behavior and prevent unintended divergence.

## Security and permissions

- Treat PDFs, DOM content, retrieved memory, and model output as untrusted data.
- Execute generated scripts only in an approved isolated environment against
  explicitly authorized targets. The current local runner is not such a boundary.
- Enforce destination policy across redirects, browser traffic, and direct HTTP
  requests. Never expose provider keys, host environment, or workspace secrets
  to generated tests. Keep credentials out of docs, logs, and reports.
- Use per-run artifact directories for new execution work and validate resolved
  path containment. Do not erase existing artifacts as a routine verification step.
- Escape review/report content by output context and validate feedback identity,
  run/phase, schema, and size. Required approval must not be inferred from timeout.
- Require appropriate authorization for destructive actions, publication,
  deployment, infrastructure changes, or access beyond the approved scope.
- Local Git initialization and an initial source snapshot were authorized on
  2026-10-22. See [GIT_PREPARATION](docs/GIT_PREPARATION.md) for provenance,
  exclusions, inventory, and publishing gates. Preserve history; never force-push.
- Keep secrets, user SRS inputs, runtime databases, browser sessions, and generated
  artifacts out of commits. Review the staged inventory and scan staged contents;
  .gitignore does not protect files already tracked or added with force.
- Do not create/connect/push a GitHub destination until the user approves its
  exact owner/name, visibility, and file inventory.

## Verification, research, and completion

- For each significant specification or implementation, evaluate affected gates in
  [ATS-FIT](docs/ARCHITECTURE.md#versioned-architecture-fitness-and-assurance-matrix).
  Record scoped CAP/acceptance traceability, existing evidence, missing proof, owner
  and intentional deferrals. Contract-test success cannot establish model quality,
  defect detection, safe execution or portability; claim each only with its own evidence.
  Revisit framework/provider coupling before changing persisted contracts; prefer small
  qualified adapters over speculative universal abstractions. Preserve V1 compatibility
  unless a demonstrated requirement justifies an explicitly versioned migration.

- Use offline unit/contract tests and controlled local fixtures first. Tests for
  substantive fixes must exercise the failure and intended behavior; do not weaken
  assertions or suppress errors to pass checks. Documentation-only edits need
  document/link validation, not browser or LLM execution.
- The offline M0/M1/M2 suite exists; maintained legacy-runtime regression, lint/type
  and CI gates remain unverified. npm test is a scaffold failure. Do not invent gates.
- Do not run existing generated specs against external sites by default. Even
  main.py --help imports configuration that can create directories; inspect effects.
- Consult official, version-appropriate documentation for unfamiliar/changing APIs
  when the task permits research. Verify installed versions before relying on APIs.
- Update architecture, findings, decisions, and next steps where relevant. Keep
  historical evidence labeled; do not present a prior run as a new test result.
- Completion requires verified acceptance criteria, relevant regression checks,
  security/traceability review, and accurate documentation. Report actual changes,
  commands/results, failures, limitations, and remaining uncertainty.

## Current authorization boundary

The latest request (C23, 2026-10-25) asks to move to implementation and commit/save
progress. Reviewed local progress checkpoints are authorized; the C20-C22 documentation
checkpoint is `569d839`. The user explicitly approved offline M2-R:
[M2R-SPEC-2026-10-25-v1](docs/M2R_DURABLE_REVIEW.md), M2R-D01..08 and M2R-AC-01..30
for offline implementation/tests and reviewed local commits. M2-R is now implemented
and verified: 157 offline tests pass; see [verification](docs/M2R_VERIFICATION.md).
Save only the reviewed M2-R implementation checkpoint, then stop. Preserve M0/M1/M2
and legacy source. No agents, new dependencies, providers,
auth/crawl, generated compilation/execution, M3/M4/M5, push, publication or deployment.
Stop after verified M2-R completion and its reviewed local implementation checkpoint.

Authorization history remains in [DECISIONS](docs/DECISIONS.md#accepted-constraints);
[older instructions](docs/history/CONTEXT_BEFORE_2026-10-25.md#agents-current-authorization-boundary)
are historical evidence, not current permission. Explicit new user instructions govern
future scope; completed milestone approvals never imply the next milestone's authority.
