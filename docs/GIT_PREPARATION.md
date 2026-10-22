# Local Git preparation and publication gate

Prepared 2026-10-22. This records version-control work only. The application,
prompts, dependency manifests, legacy documents, and open findings were preserved.
Read [AGENTS](../AGENTS.md), [CURRENT_STATE](CURRENT_STATE.md), and
[NEXT_STEPS](NEXT_STEPS.md) before resuming work.

## Provenance and authorization

- Verified root: `C:\Users\rohit\Desktop\ATS\ats`. Git 2.56.0.windows.1 is installed.
- Before initialization, `git rev-parse --show-toplevel` failed; no Git marker
  existed in this root or its ancestors. No nested Git marker was found in the
  inspected first-party tree. Installed dependency trees were excluded from that
  inspection. The ATS parent contained this workspace only.
- The connected GitHub account exposed 19 repositories under `rohit-0604`.
  An installed-repository search for `ATS` and a code search for
  `react_controller` returned no matches. Search/index/access scope is limited;
  this does not prove no other copy or upstream repository exists.
- The ambiguous `rohit-0604/CapstoneProject` default branch contained a Java/Maven
  tree (`pom.xml`, `src`, `testng.xml`), not this Python/Node layout. Its README
  lookup returned 404. A read-only GitHub CLI tree request resolved the ambiguity
  after the sandbox network proxy blocked the first request.
- The generic `https://github.com/ats-v8` HTTP-Referer in
  `app/llm/openrouter.py:19` is not evidence of an owner/repository remote.
- The user explicitly authorized local initialization and a clean initial commit
  after exclusion validation. Local branch: `main`; no remote is configured.
  This is a new workspace snapshot, not a reconstruction of prior history.
- Initialization used an empty Git template directory; no hooks were installed.
  Repository-local `core.autocrlf=false` preserves the existing file bytes.
  The existing configured Git author identity is used; commit metadata includes
  its email address. Review that metadata before any public publication.
- No GitHub repository creation, remote attachment, push, or other publication
  is authorized. No application execution, installs, or feature changes occurred.

## Exclusion decisions and sensitive-file assessment

The rules are in [`.gitignore`](../.gitignore). All excluded files remain on disk.
Ignoring content is neither encryption nor removal from existing Git history.
Never use force-add to bypass this review.

| Content | Decision and evidence |
| --- | --- |
| `.env`, `.env.*` | Local `.env` contains credential material; exclude all variants except the reviewed root `.env.example`. Never print the values. |
| Templates | Retain `.env.example` and `resource.example.json`; their credential fields are examples/placeholders. New templates need review and explicit exceptions. |
| `.venv`, `venv`, `env`, `node_modules` | Exclude installed dependencies; retain Python requirements and both Node manifests, including the lockfile. No dependency installation was needed. |
| `/input/` | Exclude both local SRS PDFs and real target configuration. These are user inputs, not established sanitized regression fixtures. Root configuration templates remain available. |
| `/cache/`, `/memory/` | Exclude cached SRS requirements, SQLite checkpoints/journals, ChromaDB data/indexes, learned selectors, and metrics. No checkpoint payloads were deserialized. |
| `/output/`, `/monitoring/` | Exclude generated results, review/report pages, telemetry, and any future auth state in output. These may contain target/user data. |
| `app/memory/` | Retain this Python source package. The old unanchored `memory/` rule would have hidden it; root anchoring fixes that error. |
| `/playwright_project/tests/` | Exclude eight generated site-specific specs. They are disposable execution artifacts, not maintained ATS regression tests. The evaluator owns this output directory. |
| Browser state/cookies | Exclude `.auth/`, storage-state/auth-state JSON patterns, cookie files. No standalone auth-state/cookie file was found outside excluded runtime areas; serialized runtime databases were not exhaustively inspected. |
| Browser artifacts | Exclude test-results, Playwright/blob reports, and root screenshots/traces/videos. Existing failed-test screenshot and error context remain local. No global image/PDF/ZIP exclusion hides documentation or future sanitized fixtures. |
| Other databases/keys | Exclude common SQLite files/journals and private-key containers. Any intentional database/key fixture needs explicit review before an exception. |
| Local configuration | Exclude credential files/directories, `.aws`, `.codex`, editor workspaces, and agent-local overrides. Shared `AGENTS.md` and source configuration remain tracked. |
| Logs/temp/build/cache | Exclude logs, temporary/editor files, Python/tool caches, build and coverage products. |
| Legacy documentation | Retain README, both DOCX guides, and reset instructions as historical documentation. DOCX XML, metadata, relationships, and concatenated text were scanned; neither document contained non-XML embedded payloads. Their claims and reset commands are not newly endorsed. |

Auth examples in README, the setup guide, and the resource template contain
illustrative credential literals. Pattern hits were reviewed as examples or
explanatory text; none matched the local secret values used in the scan.
Workspace paths, document metadata, and target/product references remain in
documentation. Keep the initial backup private; public release needs a separate
privacy, ownership/licensing, and author-metadata review. No project-wide license
was established by this task; the npm scaffold license is not such a decision.

## Validation and limitations

- Initial first-party inventory: 81 files, excluding dependency installations,
  bytecode, and Git internals. No first-party reparse points were found.
- A read-only scanner checked UTF-8 text and DOCX package XML/text for matches to
  local credential values and common provider/GitHub/AWS token, private-key, JWT,
  credential-URL, and literal-credential patterns. Values were never reported.
  Credential material was found in excluded `.env`; remaining pattern hits were
  documentation examples/explanatory text. Binary runtime databases, PDFs, and
  screenshot content were not exhaustively scanned and are excluded from Git.
- Git ignore probes passed: 35 sensitive/generated paths ignored and 16 source,
  template, manifest, documentation, and hypothetical fixture paths retained.
- The staged inventory matched the 51-file list below; no ignored file was tracked.
  Scanning all 51 staged blobs found no local-secret matches or token/private-key
  pattern hits. Nine literal-credential pattern matches were the reviewed example
  credentials/explanatory text in README, the setup guide, and the resource template.
  Both DOCX files were inspected internally; no staged binary file was left without
  content inspection. This remains subject to the bounded-scan limitation below.
- Hash comparison confirmed that only `.gitignore`, AGENTS, CURRENT_STATE,
  DECISIONS, and NEXT_STEPS changed among preexisting files. This preparation record
  is the only new project file. Application, prompts, manifests, and local runtime
  artifacts remain byte-for-byte unchanged.
- Validation of the seven instruction/handoff documents found 104 valid local
  links and 61 valid source line anchors; UTF-8 and code-fence checks passed.
- Default `git diff --cached --check` returned 2 with 722 CRLF end-of-line warnings
  in the existing monitoring_dashboard.py, telemetry.py, and two prompt files.
  `git -c core.whitespace=cr-at-eol diff --cached --check` passed with zero warnings.
  The compatible check recognizes existing Windows line endings; source bytes were
  not reformatted, and the default-check result is retained here explicitly.
- The final handoff supplies the initial commit ID. Retrieve it locally with
  `git log --max-parents=0 --oneline`; compare the actual committed inventory with
  the list below before any publication.
- This is a bounded custom scan, not a guarantee that no unknown secret or
  confidential information exists. Gitleaks was not installed; nothing was
  downloaded to obtain it. No application or external-target tests were run.
- Existing audit links to excluded runtime evidence/generated specs will not
  resolve in a fresh clone. Preserve the recorded observations in
  [AUDIT_FINDINGS](AUDIT_FINDINGS.md); do not publish raw artifacts to repair links.

## Exact initial file inventory

51 files. Only the ignore rules, AGENTS, current-state/decision/next-step handoffs,
and this new preparation record change during Git preparation. All other listed
files are the existing project snapshot. Recheck `git ls-tree -r --name-only HEAD`
before approving publication; any inventory change requires renewed review.

```text
.env.example
.gitignore
AGENTS.md
ATS_v8_README_Architecture.docx
ATS_v8_Setup_Guide (1).docx
README.md
RESET_INSTRUCTIONS.txt
app/__init__.py
app/agents/__init__.py
app/agents/codegen_agent.py
app/agents/domain_inferrer.py
app/agents/extraction_agent.py
app/agents/repair_agent.py
app/config.py
app/core/__init__.py
app/core/auth_handler.py
app/core/evaluator_engine.py
app/core/monitoring_dashboard.py
app/core/pdf_extractor.py
app/core/post_run_learner.py
app/core/quality_monitor.py
app/core/react_controller.py
app/core/route_crawler.py
app/core/telemetry.py
app/hitl/__init__.py
app/hitl/hitl_manager.py
app/llm/__init__.py
app/llm/cerebras.py
app/llm/gemini.py
app/llm/groq.py
app/llm/huggingface.py
app/llm/mistral.py
app/llm/openrouter.py
app/llm/router.py
app/memory/__init__.py
app/memory/agent_memory.py
app/schemas.py
docs/ARCHITECTURE.md
docs/AUDIT_FINDINGS.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
docs/GIT_PREPARATION.md
docs/NEXT_STEPS.md
main.py
playwright_project/package-lock.json
playwright_project/package.json
playwright_project/playwright.config.ts
prompts/agent_b_codegen_v1.txt
prompts/agent_c_repair_v1.txt
requirements.txt
resource.example.json
```

## Proposed destination and safe publication sequence

PROPOSED, NOT APPROVED: **`rohit-0604/ats`, private**. This is descriptive and
matches the workspace name; availability must be rechecked. The simpler backup
is this local source snapshot. A private GitHub copy adds off-machine access and
backup but still uploads project information and commit metadata to a third party.
Neither option backs up the deliberately excluded local inputs, credentials, or
runtime evidence. Any separate encrypted data backup needs its own scope.

Stop here until the user explicitly approves the exact owner/name, private
visibility, and the 51-file inventory above (or its reviewed successor).

After approval, perform these steps sequentially from the verified root:

1. Recheck `git status --short`, `git log --oneline --all`,
   `git ls-tree -r --name-only HEAD`, and `git remote -v`. Confirm the approved
   snapshot and scan any new changes. Inspect commit author metadata locally.
2. Confirm account with `gh api user --jq .login`. Inspect destination using
   `gh repo view rohit-0604/ats --json nameWithOwner,visibility,url`.
   An authentication/network failure is not proof the repository is absent.
   If it already exists, stop and inspect its history/ownership; do not overwrite
   it or merge unrelated histories as a shortcut.
3. Only after confirmed absence and approval, create an empty private repository:
   `gh repo create rohit-0604/ats --private`. Do not request a generated README,
   license, initial commit, or automatic push. Recheck name and visibility.
4. With no existing local remote, connect the approved destination:
   `git remote add origin https://github.com/rohit-0604/ats.git`.
   Verify `git remote get-url origin` and `git ls-remote origin`. The newly created
   destination should have no refs; stop if unexpected refs or errors appear.
5. Preview `git push --dry-run origin main`, then, only within that approval,
   `git push --set-upstream origin main`. Never use force or mirror options.
6. Verify private visibility and compare `git rev-parse HEAD` with
   `git ls-remote origin refs/heads/main`. Record the approved destination and
   successful result in the handoff. Do not claim success on a failed push.

If a different owner/name is approved, substitute that exact destination and
repeat the checks. If existing upstream history is later discovered, preserve
both histories and agree a reconciliation plan before writing to that remote.
