# ATS v8 — Autonomous Test System

> **Transform PDF requirements into a live, self-repairing Playwright test suite — fully automatically.**

ATS v8 is an agentic AI pipeline that reads a PDF requirements document, crawls a live web application, generates TypeScript Playwright tests, runs them, repairs failures, and learns from every run. It requires zero manual test authoring.

---

## Table of Contents

1. [What It Does](#1-what-it-does)
2. [High-Level Architecture](#2-high-level-architecture)
3. [End-to-End Workflow & Dataflow](#3-end-to-end-workflow--dataflow)
4. [File-by-File Reference](#4-file-by-file-reference)
5. [Agent Deep Dives](#5-agent-deep-dives)
6. [LLM Tier System & Model Choices](#6-llm-tier-system--model-choices)
7. [Memory & Learning System](#7-memory--learning-system)
8. [Human-in-the-Loop (HITL)](#8-human-in-the-loop-hitl)
9. [Planner Logic & Loop Control](#9-planner-logic--loop-control)
10. [Failure Classification & Repair](#10-failure-classification--repair)
11. [Telemetry & Monitoring Dashboard](#11-telemetry--monitoring-dashboard)
12. [CLI Reference](#12-cli-reference)
13. [Configuration Reference](#13-configuration-reference)
14. [Data Schemas](#14-data-schemas)
15. [Persistence & State Management](#15-persistence--state-management)
16. [Design Decisions & Alternatives](#16-design-decisions--alternatives)
17. [Key Constants & Thresholds](#17-key-constants--thresholds)
18. [Reset Procedures](#18-reset-procedures)
19. [Dependencies](#19-dependencies)
20. [Frequently Asked Questions](#20-frequently-asked-questions)

---

## Quick Start

```bash
# 1. Clone and install Python dependencies
pip install -r requirements.txt

# 2. Install Playwright browsers
cd playwright_project && npm install && npx playwright install chromium && cd ..

# 3. Configure API keys (copy and fill in)
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS

# 4. Run
python main.py run --url https://your-app.com --pdf input/requirements.pdf
```

**Minimum required API keys** (set in `.env`):
- `GROQ_API_KEY` — primary LLM provider ([groq.com](https://groq.com))
- `GEMINI_API_KEY` — PDF extraction ([aistudio.google.com](https://aistudio.google.com))
- `OPENROUTER_API_KEY` — reasoning fallback ([openrouter.ai](https://openrouter.ai))

---

## 1. What It Does

Given:
- A **URL** of any web application
- A **PDF** of functional requirements

ATS v8 autonomously:

1. Classifies the application domain (e-commerce, SaaS, blog, etc.)
2. Handles authentication (form login, bearer token, API key, or none)
3. Crawls the application and extracts stable CSS selectors
4. Reads the PDF and extracts all Playwright-testable requirements
5. Generates TypeScript Playwright tests — one per requirement
6. Runs the tests and classifies every failure
7. Repairs failures by re-crawling for real selectors, then rewriting broken tests
8. Repeats repair → run → evaluate until coverage targets are met or loop cap reached
9. Learns from every run — stores lessons, working selectors, repair strategies in a persistent vector database
10. Applies learned knowledge automatically on the next run

**Targets (configurable):**
- Coverage ≥ 85% (approved requirements with at least one passing test)
- Pass rate ≥ 80% (passing tests / total tests)

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ATS v8 PIPELINE                                    │
│                                                                             │
│   Input                   Orchestrator              Outputs                 │
│  ┌──────┐               ┌────────────────┐        ┌──────────────────────┐  │
│  │ PDF  │──────────────▶│                │        │ *.spec.ts test files │  │
│  └──────┘               │  LangGraph     │───────▶│ HTML quality report  │  │
│  ┌──────┐               │  ReAct         │        │ monitoring dashboard │  │
│  │ URL  │──────────────▶│  Controller    │        │ memory/lessons       │  │
│  └──────┘               │                │        └──────────────────────┘  │
│  ┌──────────┐            │  (react_       │                                  │
│  │resource  │──────────▶│   controller)  │                                  │
│  │.json     │            └───────┬────────┘                                  │
│  └──────────┘                    │                                           │
│                                  │ routes decisions to nodes                │
│          ┌───────────────────────┼──────────────────────────────────┐       │
│          ▼           ▼           ▼          ▼          ▼            ▼       │
│   ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │
│   │ Domain   │ │  Route   │ │Agent A │ │Agent B │ │Evaluate│ │Agent C  │  │
│   │ Infer    │ │ Crawler  │ │Extract │ │Codegen │ │ Engine │ │ Repair  │  │
│   └──────────┘ └──────────┘ └────────┘ └────────┘ └────────┘ └─────────┘  │
│          │           │           │          │          │            │       │
│          └───────────┴───────────┴──────────┴──────────┴────────────┘       │
│                                  │                                           │
│                          ┌───────▼───────┐                                  │
│                          │    Memory     │                                   │
│                          │  (ChromaDB +  │                                  │
│                          │   JSON files) │                                  │
│                          └───────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Design Principle: ReAct (Reason + Act)

The orchestrator is a **LangGraph state machine** where a central **Planner** node (an LLM) observes the current state and decides what to do next. This is the ReAct (Reasoning + Acting) pattern:

- **Reason:** The planner sees coverage%, pass rate, hallucination count, loop count, failure types, and decides the best next step
- **Act:** It routes to one of 10 possible nodes (extract, generate, run_tests, repair, crawl, learn, etc.)
- **Observe:** The result of every action updates the shared state, which the planner reads on the next iteration

This makes the pipeline adaptive: instead of a fixed script, the system responds intelligently to its own output.

---

## 3. End-to-End Workflow & Dataflow

### Fixed Startup Sequence (always runs in order)

```
main.py
   │
   ▼
infer_domain ──────────────────────────────────────────────────────────┐
   │  Visits base_url, reads homepage HTML + sitemap + robots.txt      │
   │  LLM classifies: app_type, auth_type, feature_areas, routes      │
   │  Output: DomainProfile                                            │
   ▼                                                                   │
handle_auth                                                            │
   │  If resource.json has credentials → Playwright logs in           │
   │  Saves session to storage_state.json                              │
   │  Output: AuthContext                                              │
   ▼                                                                   │
crawl_routes                                                           │
   │  5 route sources: domain hints + sitemap + robots + spider + LLM │
   │  Caps at MAX_CRAWL_PAGES=15 to avoid rate limits                 │
   │  Dual-track: guest pass + authenticated pass                      │
   │  Extracts selectors from each page (data-testid, aria, id, etc.) │
   │  Scores selectors by stability (1.0=data-testid → 0.2=position)  │
   │  Output: PageSelectorMap                                          │
   ▼                                                                   │
planner (loop starts here) ◀───────────────────────────────────────────┘
```

### Main Decision Loop (planner routes between these nodes)

```
planner
   │
   ├─── "extract" ──────────────────────────────────────────────────────────┐
   │       Agent A (5-pass PDF extraction)                                  │
   │       Pass 1: Gemini 2.5 Flash reads each PDF chunk → raw requirements │
   │       Pass 2: FAISS RAG enriches truncated requirements                │
   │       Pass 3: llama-8b validates/filters non-testable requirements     │
   │       Pass 4: llama-3.3-70b (Tier 4) synthesizes implied gap requirements │
   │       Pass 5: Rule-based Jaccard deduplication                         │
   │       Output: RequirementBundle (e.g., 43 requirements)                │
   │       [--interactive: pause → HITL Phase 1 browser UI]                │
   │       └──────────────────────────────────────────────────────────────▶ planner
   │
   ├─── "generate" ─────────────────────────────────────────────────────────┐
   │       Agent B (TypeScript codegen)                                      │
   │       Batches 10 requirements per LLM call (moonshotai/kimi-k2)        │
   │       Injects: lessons from memory, confirmed selectors, blocklist      │
   │       Generates: one test per requirement                               │
   │       [--interactive: pause → HITL Phase 2 browser UI]                │
   │       Output: TestSuite (e.g., 43 TestCase objects with .ts_code)      │
   │       └──────────────────────────────────────────────────────────────▶ planner
   │
   ├─── "run_tests" ────────────────────────────────────────────────────────┐
   │       Evaluator Engine                                                  │
   │       Writes *.spec.ts files to playwright_project/tests/              │
   │       Runs: npx playwright test --reporter=json                        │
   │       Parses JSON output: passed, failed, error messages, duration      │
   │       Classifies each failure: selector_not_found / strict_mode /      │
   │         assertion_failure / timeout / network_error                     │
   │       Detects hallucinations (selectors not in selector_map)           │
   │       Output: EvaluationReport (coverage%, pass%, failures[])          │
   │       └──────────────────────────────────────────────────────────────▶ planner
   │
   ├─── "crawl_demand" ─────────────────────────────────────────────────────┐
   │       On-demand re-crawl                                                │
   │       Re-visits pages for hallucinated/failing tests                   │
   │       Finds real CSS selectors that actually exist                      │
   │       Updates selector_map with newly found selectors                  │
   │       → Forces "run_tests" next                                        │
   │       └──────────────────────────────────────────────────────────────▶ planner
   │
   ├─── "repair" ───────────────────────────────────────────────────────────┐
   │       Agent C (Test repair)                                             │
   │       Batches 8 failing tests per LLM call (kimi-k2)                  │
   │       Per-test: receives error + failure_type + DOM snapshot            │
   │       Strategy varies by failure_type (see Section 10)                 │
   │       Injects: repair_strategies from memory, current selector_map     │
   │       Output: repaired TestCase objects (updated .ts_code)             │
   │       → Forces "run_tests" next                                        │
   │       └──────────────────────────────────────────────────────────────▶ planner
   │
   ├─── "learn" ────────────────────────────────────────────────────────────┐
   │       Post-run learner                                                  │
   │       Extracts lessons from: feedback, repair successes, hallucinations│
   │       Stores to ChromaDB: lessons, repair_strategies, hallucinations   │
   │       Scopes lessons: universal / app_type:{type} / domain:{url}       │
   │       → Quality monitor → generate HTML report → telemetry dashboard   │
   │       └──────────────────────────────────────────────────────────────▶ END
   │
   └─── "done" ─────────────────────────────────────────────────────────────▶ END
          (targets met, no further action needed)
```

### Dataflow: What Flows Between Nodes

```
infer_domain        ──[ DomainProfile ]──────────────────────────────────────▶ all agents
handle_auth         ──[ AuthContext ]────────────────────────────────────────▶ crawler, codegen
crawl_routes        ──[ PageSelectorMap ]────────────────────────────────────▶ codegen, repair, evaluator
Agent A             ──[ RequirementBundle ]──────────────────────────────────▶ codegen, HITL1
HITL Phase 1        ──[ FeedbackResult (approved/rejected + prompts) ]───────▶ codegen
Agent B             ──[ TestSuite ]──────────────────────────────────────────▶ evaluator, HITL2
HITL Phase 2        ──[ FeedbackResult (approved tests) ]────────────────────▶ evaluator
Evaluator           ──[ EvaluationReport ]───────────────────────────────────▶ planner, repair
Agent C             ──[ TestSuite (repaired) ]───────────────────────────────▶ evaluator
Post-run learner    ──[ Lessons, Strategies ]────────────────────────────────▶ ChromaDB
Quality monitor     ──[ HTML report, metrics ]───────────────────────────────▶ output/

Shared state (LangGraph AgentState) carries all of the above across the entire run.
```

---

## 4. File-by-File Reference

### Root Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point. Parses arguments, validates inputs, constructs initial `AgentState`, calls `run_pipeline()` in `react_controller.py`. Handles 5 commands: `run`, `resume`, `list`, `validate`, `keys`. |
| `requirements.txt` | All Python dependencies. Split into: LLM SDKs, orchestration, memory, browser, extraction, UI, OCR. |
| `resource.example.json` | Template for per-target configuration: auth credentials, routes to skip, extra headers, feature areas to focus on. Copy to `input/resource.json` and fill in. |
| `RESET_INSTRUCTIONS.txt` | Step-by-step instructions for full/partial/retry resets with exact file deletion commands. |

### `app/config.py` — Central Configuration

The single source of truth for all pipeline constants.

| Constant Class | Contains |
|----------------|----------|
| `Models` | Model ID strings for each tier (Tier1–Tier5). Edit here to swap models globally. |
| `DailyRPD` | Daily request-per-day budgets per provider (Groq free: 14,400/day; Gemini free: 1,500/day). |
| `RunBudget` | Estimated LLM calls per full run by tier. Used to warn before exhausting daily quota. |
| `Confidence` | Lesson confidence scoring constants (HUMAN_TYPED=1.0, AUTO_NEW=0.55, etc.). |
| Pipeline constants | `MAX_LOOPS=5`, `CHUNK_SIZE=4000`, `TARGET_COVERAGE=85`, `TARGET_EXEC=80` |
| HITL constants | `HITL_TIMEOUT_MINUTES=60`, `HITL_SERVER_PORT=9999` |
| Crawler constants | `MAX_CRAWL_PAGES=15`, `CRAWL_DEPTH=2`, `SELECTOR_MIN_SCORE=0.4` |

### `app/schemas.py` — Pydantic Data Models

All pipeline data flows through these models. Every agent receives and returns typed objects.

| Schema | Key Fields |
|--------|-----------|
| `DomainProfile` | `app_type`, `auth_type`, `feature_areas[]`, `likely_routes[]`, `has_rest_api`, `confidence` |
| `AuthContext` | `auth_type`, `credentials`, `storage_state_path`, `api_key` |
| `SelectorEntry` | `selector` (CSS string), `score` (0-1), `tag`, `text`, `page_url`, `confirmed`, `requires_auth` (bool — True if selector only appears in authenticated crawl) |
| `PageSelectorMap` | `pages: dict[path, list[SelectorEntry]]`, `auth_routes[]`, `guest_routes[]`, `api_endpoints[]` |
| `Requirement` | `req_id`, `title`, `description`, `priority`, `type`, `feature_area`, `approved`, `gap_analysis` |
| `RequirementBundle` | `requirements[]`, `domain_profile`, `pdf_hash`, `pass_stats` |
| `TestCase` | `test_id`, `req_id`, `title`, `spec_file`, `ts_code`, `selectors_used[]`, `hallucinated[]`, `repair_count` |
| `TestSuite` | `tests[]`, `.spec_files()` groups tests by file, `.deduplicate()` removes exact-code duplicates |
| `TestResult` | `test_id`, `passed`, `error`, `duration_ms`, `failure_type`, `dom_snapshot` |
| `EvaluationReport` | `coverage_pct`, `execution_pct`, `hallucination_count`, `results[]`, `loop_history[]`, `exit_reason` |
| `FeedbackResult` | `phase`, `items[]` (approved/rejected + per-item prompts), `global_prompt`, `category_prompts{}` |

### `app/core/react_controller.py` — LangGraph Orchestrator

The brain of the entire system. Defines the LangGraph graph, all node functions, and the planner.

**Key components:**
- `AgentState` (TypedDict) — shared state passed between every node
- `build_graph()` — Assembles the LangGraph graph with fixed + conditional edges
- `planner_node()` — LLM call (Tier 4) that decides next action; falls back to rule-based logic if LLM fails
- All node functions: `infer_domain_node`, `handle_auth_node`, `crawl_routes_node`, `agent_a_node`, `agent_b_node`, `evaluator_node`, `repair_node`, `on_demand_crawl_node`, `post_run_learn_node`, `quality_monitor_node`
- Checkpoint integration: `SqliteSaver` persists state to `cache/checkpoints.db` for resume support

**Loop control rules (enforced in controller, not planner LLM):**
- After every `repair` → force `run_tests` next (no planner decision)
- After every `on_demand_crawl` → force `run_tests` next
- If `loop_count >= MAX_LOOPS` → force `learn` immediately, bypass planner
- If `stall_count >= 2` → planner forced to pick `generate` (full regeneration) or `learn`

### `app/agents/extraction_agent.py` — Agent A

5-pass requirement extraction from PDF using Gemini 2.5 Flash.

**What each pass does:**

| Pass | Model | Purpose |
|------|-------|---------|
| 1 — Raw Extraction | Gemini 2.5 Flash | Read each 4000-char chunk; extract testable requirements with structured fields |
| 2 — RAG Enrichment | all-MiniLM + FAISS | Fix truncated requirements at chunk boundaries using semantic search |
| 3 — Validation | llama-3.1-8b (Groq) | Remove non-Playwright-testable requirements; flag orphaned refs; check completeness |
| 4 — Gap Analysis | llama-3.3-70b | Synthesize implied requirements not explicitly written in PDF |
| 5 — Deduplication | Rule-based Jaccard | Two-signal (title token + content word) overlap; remove near-duplicates |

**What is considered "non-Playwright-testable" (filtered in Pass 3):**
- CSS computed properties (background-color, font-size, z-index, etc.)
- Pixel/dimension measurements ("header is exactly 80px tall")
- Server-side logic ("database saves within 100ms")
- SEO/meta tags ("page has correct Open Graph tags")
- Analytics/tracking ("GA event fires on click")
- Geo-IP based content differences

**Why Gemini 2.5 Flash for extraction?**
Its 1M token context window means the entire PDF can be processed with very large chunks. Other free-tier models (like llama on Groq) have 8K–32K context limits, forcing tiny chunks that lose inter-paragraph context.

### `app/agents/codegen_agent.py` — Agent B

Generates TypeScript Playwright tests. One test per approved requirement.

**What gets injected into every codegen prompt:**
1. **Lessons from memory** — Proven patterns from previous runs (e.g., "always use `page.waitForLoadState('domcontentloaded')`")
2. **Confirmed selectors** — Real CSS selectors from crawler and memory for this domain
3. **Hallucination blocklist** — Selectors confirmed to not exist (must never use these)
4. **Auth route info** — Which pages require login (prepend login block for those tests)
5. **HITL global/category prompts** — Human guidance injected as high-priority instructions

**Hard rules enforced in system prompt:**
- Use `page.waitForLoadState('domcontentloaded')` — never `networkidle` (which never resolves on analytics-heavy sites)
- Never use `locator('generic')`, `locator('paragraph')`, `locator('listitem')` — these are ARIA snapshot labels, not valid CSS
- Never assert `window.getComputedStyle()` values
- Never count exact numbers of arbitrary DOM children
- Only use selectors that exist in the confirmed selector list

**Why these rules matter:**
The most common failure types in initial codegen are: (1) using ARIA snapshot labels as CSS selectors (causes timeouts), (2) using `networkidle` which never fires on Heroku/analytics-heavy sites, (3) inventing CSS classes that don't exist.

### `app/agents/repair_agent.py` — Agent C

Repairs failing tests using error messages, DOM snapshots, and LLM (kimi-k2-instruct).

**What each repair call receives:**
- The failing test's current `.ts_code`
- The exact Playwright error message
- The classified `failure_type` (`selector_not_found`, `strict_mode`, etc.)
- A DOM snapshot of the page (text representation of actual DOM)
- Real selectors from the current `selector_map` for that page
- Similar repair strategies from memory (retrieved by failure_type)

**Why batch size is 8 (not 10 like codegen):**
Groq's free tier for Kimi K2 and Llama 70B has a 1,000 RPD (requests per day) limit. More critically, each repair call includes DOM snapshots which average 2–3K tokens per test. At 10 failing tests, a single repair batch exceeds the per-request context window on the free tier and triggers 413 errors. Batch size 8 keeps each request safely within limits.

### `app/agents/domain_inferrer.py` — Domain Classifier

First node in the pipeline. Visits the base URL and classifies the application.

**Inputs:** Homepage HTML (8K chars), sitemap structure, robots.txt
**Output:** `DomainProfile` with `app_type`, `auth_type`, `feature_areas[]`, `likely_routes[]`

**Known app types:**
`ecommerce`, `finance_saas`, `blog`, `crm`, `project_mgmt`, `healthcare`, `education`, `social`, `developer_platform`, `marketing_site`, `generic`

Each app type has a hardcoded feature area list in `config.py`. These feature areas guide:
- What kinds of requirements Agent A looks for
- Which pages the crawler prioritizes
- How the planner interprets coverage stalls

### `app/core/pdf_extractor.py` — PDF Text Extraction

Validates and extracts text from PDF files.

**Process:**
1. Magic byte validation (checks `%PDF` header — not just file extension)
2. `pdfplumber` extracts text + tables (tables become pipe-delimited rows)
3. Falls back to OCR (pdf2image + pytesseract) for scanned/image PDFs
4. Chunks text into 4000-char segments with 0 overlap

**Why chunk overlap is hardcoded to 0:**
Non-zero overlap causes systematic duplicate requirements at every chunk boundary. When a requirement spans the boundary between chunk N and chunk N+1, it gets extracted twice with slightly different text. Even with deduplication, this wastes LLM calls. Chunks of 4000 chars with 0 overlap and Gemini's smart context handling works better than overlapping smaller chunks.

### `app/core/route_crawler.py` — Route Discovery & Selector Extraction

Discovers application routes and extracts CSS selectors. The crawler is the system's "eyes."

**5 route discovery sources:**
1. `domain_profile.likely_routes` — LLM-inferred routes from domain classification
2. `sitemap.xml` parsing (filters out `.xml`, `.rss`, `.atom`, `.xsl` files and `sitemap` paths to avoid crawling the sitemap index as a page)
3. `robots.txt` `Allow:` and `Disallow:` directives (reveals hidden routes)
4. Homepage spider — follows `<a href>` links (depth=2, same-domain only)
5. LLM pattern completion — infers parameterized routes like `/products/{id}` → `/products/1`

**Selector scoring by stability:**

| Selector Type | Score | Rationale |
|---------------|-------|-----------|
| `data-testid` | 1.0 | Explicitly added for testing; extremely stable |
| `aria-label` | 0.9 | Semantic; rarely changes without also changing UX |
| `id` | 0.8 | Unique per page; stable unless dynamically generated |
| `name` | 0.7 | Form inputs; stable if form structure doesn't change |
| `type` | 0.6 | Input type (`text`, `submit`); semi-stable |
| `class` | 0.4 | Styling-driven; changes with CSS refactors |
| Positional (nth-child) | 0.2 | Breaks on any DOM restructure; filtered by default |

**Dual-track crawl:**
- **Guest track:** Fetches each route without authentication
- **Auth track:** Fetches each route with `storage_state.json` from auth handler
- Routes that return 200 in auth track but 401/403/redirect in guest track → labeled as `auth_routes`
- Agent B uses this to prepend a login block before `page.goto()` in tests for auth routes

**XML/sitemap filtering (hard-coded in `_make_adder`):**
Without this filter, sitemap index files (`post-sitemap.xml`, `page-sitemap.xml`) get added to the route list. Playwright then tries to `querySelector` on raw XML, which always fails with parse errors. Any discovered path is discarded before it enters the crawl queue if it matches:
- Static asset extensions: `.css`, `.js`, `.png`, `.jpg`, `.gif`, `.svg`, `.ico`, `.woff`, `.ttf`, `.map`, `.json`, `.xml`, `.xsl`, `.txt`, `.rss`, `.atom`
- Path contains the word `sitemap`

This filtering applies to all 5 route discovery sources.

### `app/core/auth_handler.py` — Authentication

Handles four auth patterns:

| Type | Mechanism |
|------|-----------|
| `none` | No auth required; proceeds directly |
| `form_login` | Playwright browser → navigate to login_url → fill credentials → click submit → save storage_state.json |
| `bearer_token` | HTTP POST to token_endpoint → extract access_token → set as Authorization header |
| `api_key` | Store API key for injection into request headers |

The saved `storage_state.json` (Playwright's session storage format) is reused by both the crawler's auth track and any test that navigates to an auth-required route.

### `app/core/evaluator_engine.py` — Test Runner & Failure Classifier

Writes spec files, runs Playwright, parses results, detects hallucinations.

**Failure classification logic:**

| Error Message Pattern | Classified As |
|-----------------------|---------------|
| "locator.waitFor", "No element found", "waiting for" | `selector_not_found` |
| "strict mode violation", "multiple elements" | `strict_mode` |
| "expect(locator).to", "received" | `assertion_failure` |
| "Timeout", "exceeded" | `timeout` |
| "net::ERR", "NS_ERROR", "Navigation failed" | `network_error` |

**Hallucination detection:**
After each Playwright run, every `selectors_used` list in each `TestCase` is checked against the `PageSelectorMap`. Any selector not found in the map (on any page) is marked as hallucinated. The test is flagged for on-demand crawl resolution.

**`npx` resolution (Windows compatibility):**
On Windows with `nvm4w`, `npx` may not be on the PATH as a standard executable. The evaluator tries: `npx.cmd`, then `npx`, then a full path search in Node.js installation directories.

**Why the evaluator re-writes spec files on every loop:**
`write_spec_files()` always regenerates from the in-memory `TestSuite` object. This ensures repaired tests (which update `TestCase.ts_code` in memory) are reflected in the files before Playwright runs. The downside: any manual edits to `.spec.ts` files are lost on the next loop. All fixes must go through Agent C.

### `app/core/post_run_learner.py` — Learning Engine

Runs after the pipeline completes. Extracts structured lessons from the run.

**What it learns from:**
- **HITL Phase 1 feedback** — Human approval/rejection patterns → domain-specific extraction lessons
- **HITL Phase 2 feedback** — Human test code feedback → codegen lessons
- **Successful repairs** — `failure_type` + original code + repaired code → `repair_strategy` entry
- **Confirmed hallucinations** — Selectors marked non-existent → blocklist entry
- **Coverage deltas** — Which requirement feature areas stalled → extraction gap hints

**Lesson scoping (3 scopes):**

| Scope | Key | Example |
|-------|-----|---------|
| Universal | `universal` | "Always use `domcontentloaded` instead of `networkidle`" |
| App-type | `app_type:ecommerce` | "Cart total is dynamic; use `toContainText()` not `toEqual()`" |
| Domain | `domain:heroku.com` | "The hero section uses `.hero-unit h1` selector" |

Universal lessons require `confidence >= 0.90` and are injected into all future runs regardless of domain.

### `app/core/quality_monitor.py` — Run Quality Assessment

Runs at the end of every pipeline execution.

**What it checks:**
- Coverage regression > 5% vs previous run
- Hallucination spike > +3 absolute, or total count > 5
- Coverage fell below `TARGET_COVERAGE` after previously exceeding it

**Output:** `output/report_{run_id}.html` — a full HTML report with test result tables, coverage trend, failure distribution, and per-feature-area breakdown.

### `app/core/telemetry.py` — Event Logging

Lightweight structured event logging to `monitoring/metrics.jsonl`.

Every agent emits events on completion:

```json
{
  "ts": "2026-03-18T13:44:46",
  "run_id": "ats_20260318_131928_81d907",
  "agent": "agent_b",
  "event": "codegen_complete",
  "loop": 0,
  "metrics": {
    "tests_generated": 43,
    "hallucination_rate": 0.11,
    "batch_count": 5,
    "duration_s": 8.9
  },
  "ok": true
}
```

**Agents that emit telemetry:**
- `crawler` → `crawl_complete` (pages_crawled, selectors_found)
- `agent_a` → `extraction_complete` (reqs_extracted, reqs_removed_untestable, duration_s)
- `agent_b` → `codegen_complete` (tests_generated, hallucination_rate, batch_count)
- `agent_c` → `repair_complete` (repair_success_rate, failure_types{})
- `planner` → `decision` (action, coverage_pct, hallucinations, loop)
- `learner` → `learning_complete` (lessons_added, strategies_added)

### `app/core/monitoring_dashboard.py` — Intelligence Dashboard

Reads `monitoring/metrics.jsonl` and generates `monitoring/dashboard.html`. Called automatically by `quality_monitor.py` at the end of every run.

**Dashboard sections:**
- 5 KPI tiles: coverage, pass rate, hallucination rate, loops to converge, lessons banked
- Coverage & pass rate trend chart (Chart.js line chart across runs)
- Agent intelligence radar chart (6 axes: hallucination control, repair effectiveness, extraction accuracy, planning efficiency, learning velocity, selector quality)
- Learning velocity chart (lessons added per run vs hallucination rate trend)
- Repair convergence chart (loops needed per run to reach target)
- Per-agent health cards with 0–100 scores and trend badges (↑↓→)
- Run history table with delta indicators (green/red vs previous run)

Auto-refreshes every 30 seconds.

### `app/hitl/hitl_manager.py` — Human Review

Manages the three human-in-the-loop review phases. See [Section 8](#8-human-in-the-loop-hitl) for full details.

### `app/memory/agent_memory.py` — Persistent Memory

Unified API for all memory operations. See [Section 7](#7-memory--learning-system) for full details.

### `app/llm/router.py` and LLM Providers

Routes LLM calls to the appropriate model/provider by tier, with fallback chains. See [Section 6](#6-llm-tier-system--model-choices) for full details.

**Provider files:**
- `groq.py` — Groq API (OpenAI-compatible client, base URL: `https://api.groq.com/openai/v1`)
- `gemini.py` — Google Gemini (native `google-generativeai` SDK, not OpenAI-compat)
- `openrouter.py` — OpenRouter (OpenAI-compatible, paid fallback)
- `cerebras.py` — Cerebras (OpenAI-compatible, fast inference fallback)
- `mistral.py` — Mistral (OpenAI-compatible, code generation fallback)
- `huggingface.py` — Local embeddings only (`all-MiniLM-L6-v2`, no API calls)

---

## 5. Agent Deep Dives

### Agent A — Requirement Extraction (5 Passes)

```
PDF file
   │
   ▼ pdf_extractor.py
Text (4000-char chunks, overlap=0)
   │
   ├── Pass 1: Gemini 2.5 Flash ──────────────────────────────────────────────┐
   │   For each chunk:                                                         │
   │   System: "You are a QA analyst. Extract only Playwright-testable         │
   │            requirements. Format as JSON array..."                         │
   │   → raw_requirements: list (e.g., 46 reqs from 4 chunks)                 │
   │                                                                           │
   ├── Pass 2: FAISS + all-MiniLM ──────────────────────────────────────────── │
   │   Build embeddings index of all extracted reqs                            │
   │   For any truncated requirement: find similar in other chunks + merge     │
   │                                                                           │
   ├── Pass 3: llama-3.1-8b (Groq) ─────────────────────────────────────────── │
   │   Validate all 46 requirements:                                           │
   │   - Flag non-Playwright-testable (computed CSS, server-side, SEO)        │
   │   - Check for orphaned references                                         │
   │   - Identify obvious duplicates                                           │
   │   → 0-5 removed; remainder validated                                     │
   │                                                                           │
   ├── Pass 4: llama-3.3-70b (Groq) ─────────────────────────────────────────── │
   │   "Are there implied requirements from the domain that the PDF missed?"   │
   │   Gap analysis for the specific app_type                                  │
   │   → 0-N new gap_analysis=True requirements synthesized                   │
   │                                                                           │
   └── Pass 5: Rule-based ──────────────────────────────────────────────────── │
       Two-signal Jaccard: title token overlap + content word overlap          │
       Remove near-duplicates (threshold: combined score > 0.7)               │
       → RequirementBundle (43 final requirements)                             │
                                                                               │
   Cache: requirements_ffb6b4e9c77b6c34.json (keyed by PDF SHA-256)           ◀┘
   (If same PDF re-used, Pass 1 and all network calls are skipped entirely)
```

### Agent B — Code Generation

```
RequirementBundle (43 approved reqs)
   │
   ├── Memory injection:
   │   get_lessons(scope=["universal", "app_type:developer_platform", "domain:heroku.com"])
   │   get_selectors(domain=base_url, min_score=0.5)
   │   get_hallucination_blocklist(domain=base_url)
   │
   ├── Context assembly per batch (10 reqs):
   │   - system_prompt (from agent_b_codegen_v1.txt)
   │   - memory lessons (as bullet list)
   │   - confirmed selectors for each relevant page
   │   - blocklisted selectors (must not use)
   │   - auth route list (prepend login block for these)
   │   - HITL global_prompt (if provided)
   │   - HITL category_prompts (if provided)
   │
   ├── 5 batches × 10 reqs → 3 parallel async calls (ASYNC_CONCURRENCY=3)
   │
   ├── JSON sanitization (3 passes):
   │   1. Strip markdown fences (```json, ```typescript)
   │   2. Fix invalid escape sequences
   │   3. json.loads() + validate fields
   │
   └── Output: TestSuite (43 TestCase objects)
       Each has: test_id, req_id, title, spec_file (grouped by feature_area), ts_code
```

### Agent C — Repair

```
EvaluationReport (9 failing tests, dominant: strict_mode)
   │
   ├── Memory injection:
   │   get_repair_strategies(failure_type="strict_mode")
   │   → 3 similar strategies retrieved from previous runs
   │
   ├── Per-test repair context:
   │   - Original .ts_code
   │   - Playwright error message (exact)
   │   - failure_type classification
   │   - DOM snapshot (text representation of what's actually on the page)
   │   - Real selectors from selector_map for that page
   │   - Retrieved repair_strategies from memory
   │
   ├── Batch 8 tests per call
   │
   └── Repair strategies by failure_type:
       selector_not_found → Use DOM snapshot; switch to getByRole/getByText; never reuse failing selector
       strict_mode        → Scope locator to parent container; or add .first() if appropriate
       assertion_failure  → Update expected value; use toContainText() instead of toEqual()
       timeout            → Entire approach is wrong; rewrite using visible semantic element from DOM snapshot
       network_error      → Check URL against likely_routes; use a route that actually returns 200
```

---

## 6. LLM Tier System & Model Choices

### Tier Assignment Table

| Tier | Purpose | Model | Provider | Why This Model |
|------|---------|-------|----------|----------------|
| **1** | Classification, validation, quick decisions | `llama-3.1-8b-instant` | Groq | Fastest free-tier model (14.4K RPD); sufficient for binary classification and structured filtering |
| **2** | Long-context PDF extraction | `gemini-2.5-flash` | Google Gemini | 1M token context window; handles entire large PDFs in one pass; free tier available |
| **3** | TypeScript code generation | `moonshotai/kimi-k2-instruct` | Groq | Kimi K2 is a coding-specialized model; better TypeScript + Playwright code quality than general models |
| **4** | Reasoning, ReAct planning | `llama-3.3-70b-versatile` | Groq | Best free-tier reasoning model with reliable JSON output; 70B parameters. Note: DeepSeek R1 and qwen3-32b were tested and removed — R1 is 404 on OpenRouter as of March 2026; qwen3-32b's thinking-budget tokens consume all `max_tokens` and return empty output |
| **5** | Semantic embeddings (local) | `all-MiniLM-L6-v2` | HuggingFace local | No API calls; runs on CPU; ~90MB; sufficient quality for lesson retrieval |
| **6** | Post-run lesson extraction | `llama-3.1-8b-instant` | Groq | Same as Tier 1 — lesson extraction is classification-level work; no need for larger model |

### Fallback Chains

Every tier has a fallback chain. If the primary model fails (rate limit, server error, timeout), the router automatically tries the next provider:

```
Tier 1: groq/llama-3.1-8b-instant     →  cerebras/llama3.1-8b      →  mistral/mistral-small-latest
Tier 2: gemini-2.5-flash               →  gemini-2.5-flash-lite     →  groq/llama-3.3-70b-versatile (chunked)
Tier 3: groq/kimi-k2-instruct          →  mistral/codestral-latest  →  groq/llama-3.3-70b-versatile  →  openrouter/deepseek-v3-2
Tier 4: groq/llama-3.3-70b-versatile   →  groq/llama-3.1-8b-instant →  openrouter/deepseek-v3-2
```

### Router Features
- **Retry logic:** `MAX_RETRIES=3`, exponential backoff starting at 1 second
- **Provider availability tracking:** Marks a provider unavailable after 3 consecutive failures; skips it for the rest of the run
- **Rate-limit awareness:** Reads `DailyRPD` budgets; warns before exhausting quotas
- **Async concurrent batching:** `asyncio.gather()` on up to `ASYNC_CONCURRENCY=3` simultaneous calls

### Why Not OpenAI / Anthropic?

**Cost:** OpenAI GPT-4o and Claude cost roughly $0.01–0.05 per 1K tokens. A single ATS run does ~500 LLM calls. At average 2K tokens per call, that's ~$5–50 per run. The current tier system uses free-tier models and achieves comparable results for this structured, prompt-engineered task.

**Alternative considered:** GPT-4o-mini for Tier 1/3, Claude 3.5 Sonnet for Tier 4. These would improve quality slightly but add cost. The system is architected to swap models by changing `config.py:Models` constants only.

---

## 7. Memory & Learning System

### Storage Architecture

```
memory/
├── chroma_db/                    # ChromaDB vector store (semantic lessons + repair strategies)
├── domain_selectors.json         # {domain: {page_path: [{selector, score, tag, text}]}}
├── hallucination_list.json       # [{selector, domain, confirmed_at, run_id}]
├── run_metrics.json              # [{run_id, timestamp, coverage_pct, exec_pct, hallucinations}]
├── feedback_history.json         # Full HITL feedback audit trail (created on first interactive run)
└── prompt_versions.json          # Evolved prompt history (created on-demand when prompt evolution triggers)
```

### ChromaDB Collections

| Collection | Content | Retrieval |
|------------|---------|-----------|
| `lessons` | Semantic patterns about what works/fails for specific domains and app types | Cosine similarity search by context query |
| `repair_strategies` | `failure_type → (original_code, repaired_code, explanation)` from successful repairs | Lookup by failure_type |
| `hallucinations` | CSS selectors confirmed to not exist | Blocklist (always injected into codegen) |

### Memory Scoping (3 Levels)

```
universal               → Applies to every domain, every app type
   └── "Always use domcontentloaded, never networkidle"
   └── "Never use locator('generic') — ARIA label, not CSS"

app_type:developer_platform → Applies to all developer platform sites (like Heroku, Vercel, etc.)
   └── "Developer platform sites use hero sections with CTA buttons"
   └── "Pricing sections typically have 2-3 plan cards with getByRole('heading')"

domain:heroku.com       → Applies only to heroku.com
   └── "Social links are in role='navigation' with aria-label='social'"
   └── "Login form selector is #heroku-header .login-btn"
```

### Confidence Scoring

Lessons are only injected into future prompts if `confidence >= INJECTION_MIN (0.65)`.

| Lesson Source | Confidence | Notes |
|---------------|-----------|-------|
| Human types directly in HITL | 1.00 (`HUMAN_TYPED`) | Always above injection threshold |
| Human selects category prompt | 0.60 (`CATEGORY_PROMPT`) | Below injection threshold; stored as lesson at `INJECTION_MIN` (0.65) by post_run_learner |
| Human provides global prompt | 0.65 (`GLOBAL_PROMPT`) | At injection threshold |
| Auto-extracted from repair success | 0.65 (`REPAIR_STRATEGY`) | At injection threshold |
| Auto-extracted new lesson | 0.55 (`AUTO_NEW`) | Below threshold; must be confirmed by repeat to reach injection |
| Confirmed hallucination | 0.70 (`CONFIRMED_HALL`) | Above threshold; always blocklisted |

Lessons accumulate confidence if the same lesson is independently learned multiple times (bumped by +0.05 per confirmation). This naturally promotes the most reliable patterns to universal scope.

### What the Memory System Prevents on the Next Run

1. **Repeated hallucinations** — Blocklisted selectors are never generated again
2. **Repeated repair loops** — Same failure type → same fix strategy retrieved immediately
3. **Repeated extraction errors** — Lessons guide Agent A to extract better requirements
4. **Unnecessary crawling** — Confirmed selectors from previous runs are injected directly

---

## 8. Human-in-the-Loop (HITL)

HITL is optional (disabled with `--auto`, minimal with default, full with `--interactive`).

### Three Review Phases

#### Phase 1 — Requirement Review

**When:** After Agent A extracts requirements
**Interface:** Browser opens auto-generated HTML review page; feedback posted via HTTP to port 9999
**Auto-approve logic (constants: `AUTO_APPROVE_SILENT=0.90`, `AUTO_APPROVE_FLAGGED=0.75`, `REVIEW_REQUIRED_BELOW=0.65`):**
- `confidence >= 0.90` → silently approved (green badge, no action required)
- `confidence >= 0.75` → approved with yellow badge (shown in UI but auto-approved)
- `confidence 0.65–0.74` → flagged for review queue (shown, needs attention)
- `confidence < 0.65` → must be explicitly approved or rejected
- `gap_analysis=True` → always shown for review regardless of confidence score (synthesized requirements need human validation)

**What humans can do:**
- Approve / reject individual requirements
- Provide a per-requirement `run_prompt` (specific instruction for this run only)
- Provide a `memory_note` (lesson to store permanently for future runs)
- Override a selector with a specific CSS string
- Write a `global_prompt` (high-priority instruction applied to entire run)
- Write `category_prompts` per feature area (e.g., "for auth tests, always use the real login URL")

#### Phase 2 — Test Code Review

**When:** After Agent B generates tests
**Interface:** Same browser-based HTML review
**Default:** All tests auto-approved; human can reject specific tests
**Feedback:** Per-test rejection notes become lessons for Agent B improvement

#### Phase 3 — Results Review

**When:** Before post-run learning (interactive mode only)
**Interface:** Terminal TUI using `rich` + `questionary` libraries
**Purpose:** Quick decisions on failing tests: "Mark as flaky", "Skip permanently", "Worth retrying"

### Timeout Behavior

If no human feedback is received within `HITL_TIMEOUT_MINUTES=60`, all pending items are auto-approved and the pipeline continues. This prevents blocked pipelines in automated environments.

### Running Without HITL

```bash
# Full automation — no pauses
python main.py run --url https://example.com --pdf reqs.pdf --auto
```

In `--auto` mode:
- All extracted requirements are auto-approved
- All generated tests are auto-approved
- Phase 3 is skipped entirely

---

## 9. Planner Logic & Loop Control

The planner (Tier 4 LLM) is called after every node completes. It receives the full current state and reasons about what to do next.

### Decision Context Provided to Planner

```
Current state:
- loop_count: 4
- coverage_pct: 79.1%  (target: 85%)
- exec_pct: 88.4%       (target: 80%)
- hallucination_count: 3
- crawl_demand_count: 1 (max: 2)
- stall_count: 1
- dominant_failure_type: "selector_not_found"
- last_action: "run_tests"
- requirements_approved: True
- tests_generated: True
```

### Planner Decision Rules (hard-coded override layer)

These rules run BEFORE the LLM to prevent logic errors:

```python
# 1. After repair → always run tests (no planner call)
if last_action == "repair":
    return "run_tests"

# 2. After on_demand_crawl → always run tests (no planner call)
if last_action == "on_demand_crawl":
    return "run_tests"

# 3. Max loops reached → terminate
if loop_count >= MAX_LOOPS:
    return "learn"

# 4. Stall detected (coverage hasn't improved in 2 loops) → force regeneration
if stall_count >= 2 and coverage_pct < TARGET_COVERAGE:
    return "generate"  # full regeneration, not repair

# 5. Crawl demand cap reached with hallucinations → force repair
if crawl_demand_count >= 2 and hallucination_count > 0:
    return "repair"
```

After these overrides, the planner LLM reasons freely over the remaining cases.

### Why Override Rules Exist

Without override rules, the LLM planner sometimes enters infinite loops:
- **Repair without running tests:** Planner might decide to repair again before checking if the repair worked. The `after repair → run_tests` override prevents this.
- **Generate without evaluating:** Planner might regenerate endlessly without ever running tests.
- **Never terminating:** Without `MAX_LOOPS`, the planner might keep trying indefinitely if stuck near 84% coverage.

The override layer separates "mechanical" control flow from "intelligent" decision-making. The LLM handles ambiguous judgment calls; hard rules handle deterministic state transitions.

### Stall Detection

```
Loop 1: coverage = 35%  → delta = 35%  → stall_count = 0
Loop 2: coverage = 75%  → delta = 40%  → stall_count = 0
Loop 3: coverage = 77%  → delta = 2%   → stall_count = 1  (< 2% delta threshold)
Loop 4: coverage = 77%  → delta = 0%   → stall_count = 2  → FORCE REGENERATE
```

If coverage improves by < 2% between two consecutive loops, the planner considers the system "stalled." At `stall_count == 2`, it forces a full code regeneration instead of continuing to repair the same tests.

---

## 10. Failure Classification & Repair

### Failure Types

| Type | When It Occurs | What It Means |
|------|----------------|---------------|
| `selector_not_found` | `page.locator(sel).waitFor()` times out; error says "No element found" | The CSS selector doesn't exist on the page |
| `strict_mode` | Playwright finds multiple elements matching the selector | The locator is too broad; multiple DOM nodes match |
| `assertion_failure` | Element found, but `expect().toEqual()` / `toHaveText()` fails | Element exists but value differs from expected |
| `timeout` | Entire test times out (default: 30s per test) | Could be slow page, or locator using ARIA labels as CSS |
| `network_error` | `page.goto()` fails with ERR_CONNECTION / 404 / redirect | URL doesn't exist or requires different auth state |

### Repair Strategy by Type

```
selector_not_found:
  ✗ Don't try: different CSS variations of the same broken selector
  ✓ Do: Look at DOM snapshot → find visible semantic equivalent
  ✓ Do: page.getByRole('button', {name: /text/i})
  ✓ Do: page.getByText('exact visible text')
  ✓ Do: page.getByLabel('form label text')

strict_mode:
  ✗ Don't try: adding .first() blindly (wrong semantics)
  ✓ Do: Scope to parent container first
        page.getByRole('navigation').getByRole('link', {name: 'Pricing'})
  ✓ Do: Use a more specific attribute to disambiguate

assertion_failure:
  ✗ Don't try: hardcoding a new exact value that might change
  ✓ Do: Use flexible matchers: toContainText(), toMatch(/regex/)
  ✓ Do: Update to match what the DOM snapshot shows is actually there

timeout:
  ✗ Don't try: adding more await page.waitForTimeout() calls
  ✗ Don't try: increasing page.setDefaultTimeout()
  ✓ Do: Recognize the locator approach is fundamentally broken
  ✓ Do: Rewrite entire assertion using a visible element from DOM snapshot
  Note: locator('generic') and locator('paragraph') are ARIA labels, not CSS selectors
        They will ALWAYS timeout — must be completely replaced

network_error:
  ✗ Don't try: retrying the same URL
  ✓ Do: Check domain_profile.likely_routes for the correct URL
  ✓ Do: Verify the page exists in selector_map before navigating to it
```

### How Hallucinations Are Handled

A "hallucination" is when Agent B generates a test using a CSS selector that does not actually exist on the page.

**Detection:** After Playwright run, `evaluator_engine.py` checks `TestCase.selectors_used` against `PageSelectorMap`. Any selector missing from the map is flagged.

**Resolution pipeline:**
```
Hallucination detected
   │
   ├── Loop 1-2: crawl_demand (Planner action, separate from repair)
   │   Re-crawl the pages those tests navigate to
   │   Find real selectors that actually exist
   │   Updated selector_map fed back to Planner → Planner then routes to repair
   │
   ├── Loop 3+: repair only (crawl_demand cap reached)
   │   Planner routes directly to Agent C (no re-crawl)
   │   Agent C repairs using existing selector_map + DOM snapshot
   │
   └── Post-run: add_hallucination() → blocklist
       Never generate these selectors again in future runs
```

---

## 11. Telemetry & Monitoring Dashboard

### Why This Was Built

Without telemetry, it's impossible to answer questions like:
- "Is Agent B getting better or worse at avoiding hallucinations?"
- "How many loops does the repair cycle typically take to converge?"
- "Which agent is causing the most retries?"

The monitoring system provides Dynatrace-style observability for the AI agents themselves.

### Metrics Emitted Per Agent

| Agent | Event | Key Metrics |
|-------|-------|-------------|
| Crawler | `crawl_complete` | `pages_crawled`, `selectors_found`, `auth_routes`, `duration_s` |
| Agent A | `extraction_complete` | `reqs_extracted`, `reqs_removed_untestable`, `gap_reqs_added`, `duration_s` |
| Agent B | `codegen_complete` | `tests_generated`, `hallucination_rate`, `batch_count`, `duration_s` |
| Agent C | `repair_complete` | `tests_repaired`, `repair_success_rate`, `failure_types{}`, `duration_s` |
| Planner | `decision` | `action`, `loop`, `coverage_pct`, `hallucinations`, `stall_count` |
| Learner | `learning_complete` | `lessons_added`, `strategies_added`, `hallucinations_added` |

### Agent Health Scoring (0–100)

Each agent gets a composite score based on its key metric trends:

| Agent | Score Formula |
|-------|--------------|
| Agent A | `(1 - untestable_rate) × 100` — fewer non-testable extractions = better |
| Agent B | `(1 - hallucination_rate) × 100` — fewer hallucinations = better |
| Agent C | `repair_success_rate × 100` — higher repair success = better |
| Crawler | `min(selectors_found / 50, 1) × 100` — more selectors found = better coverage |

Trend badges (↑↓→) show whether each agent is improving or degrading across runs.

### Accessing the Dashboard

After any run, open `monitoring/dashboard.html` in a browser. It auto-refreshes every 30 seconds if a run is in progress.

---

## 12. CLI Reference

```bash
# Start a new run
python main.py run \
  --url https://your-app.com \           # Required: target application URL
  --pdf input/requirements.pdf \         # Required (or --requirements): requirements PDF
  --auto                                 # Optional: skip all HITL pauses
  --interactive                          # Optional: pause at all 3 HITL phases
  --extract-only                         # Optional: stop after extraction
  --codegen-only                         # Optional: stop after code generation (needs --requirements)
  --requirements cache/req.json          # Optional: use pre-extracted requirements (skips Agent A)
  --force-extract                        # Optional: re-extract even if PDF cache exists
  --force-crawl                          # Optional: re-crawl even if selector cache exists
  --debug                                # Optional: set log level to DEBUG

# Resume an interrupted run
python main.py resume --run-id ats_20260318_131928_81d907

# List all previous runs with their metrics
python main.py list

# Validate a PDF before running (checks file validity + page count)
python main.py validate --pdf input/requirements.pdf

# Show API key status — which keys are set, which are missing
python main.py keys
```

> **Note:** `resource.json` is auto-loaded from `input/resource.json` or the project root — there is no `--resource` CLI flag. `MAX_LOOPS` is configured via the `.env` file, not a CLI flag.

### Run Modes

| Mode | HITL Phase 1 | HITL Phase 2 | HITL Phase 3 |
|------|-------------|-------------|-------------|
| Default | ✓ Pauses | ✓ Pauses | ✗ Skipped |
| `--interactive` | ✓ Pauses | ✓ Pauses | ✓ Pauses |
| `--auto` | ✗ Auto-approved | ✗ Auto-approved | ✗ Skipped |

---

## 13. Configuration Reference

### Environment Variables (`.env`)

```bash
# Required (3 providers — code treats all three as required)
GROQ_API_KEY=gsk_...           # Primary LLM provider (free tier)
GEMINI_API_KEY=AIza...         # Required for PDF extraction (1M context)
OPENROUTER_API_KEY=sk-or-...   # Required for Tier 3/4 fallback chains

# Optional: additional fallback providers
CEREBRAS_API_KEY=csk-...       # Fast inference fallback (Tier 1)
MISTRAL_API_KEY=...            # Code generation fallback (Tier 3)

# Optional: crawler tuning
MAX_CRAWL_PAGES=15             # Default: 15; increase for larger sites
CRAWL_DEPTH=2                  # Default: 2; how deep to follow links

# Optional: pipeline tuning
MAX_LOOPS=5                    # Default: 5; max repair iterations
TARGET_COVERAGE=85             # Default: 85%; minimum coverage to consider success
TARGET_EXEC=80                 # Default: 80%; minimum pass rate to consider success
USE_ASYNC=true                 # Default: true; enable async concurrent LLM batching
ASYNC_CONCURRENCY=3            # Default: 3; parallel LLM calls per batch

# Optional: HITL tuning
HITL_TIMEOUT_MINUTES=60        # Default: 60; auto-continue if no feedback
HITL_SERVER_PORT=9999          # Default: 9999; port for HITL browser UI

# Optional: memory tuning
MEMORY_INJECTION_THRESHOLD=0.65  # Default: 0.65; min confidence to inject lessons
PROMPT_EVOLUTION_INTERVAL=3      # Default: 3; runs between prompt evolution

# Optional: logging
LOG_LEVEL=INFO                 # Default: INFO; set to DEBUG for verbose output

# Optional: OCR (for scanned PDFs)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe  # Path to Tesseract binary
```

> **Note:** `ATS_BASE_URL` is set automatically by the evaluator engine when running Playwright — you do not need to set it manually.

### `resource.json` Schema

```json
{
  "base_url": "https://app.example.com",
  "auth": {
    "type": "none | form_login | bearer_token | api_key",
    "credentials": {
      "username": "testuser@example.com",
      "password": "testpassword123"
    },
    "login_url": "/login",
    "token_endpoint": "/api/auth/token",
    "api_key": "your-api-key"
  },
  "skip_routes": ["/admin", "/debug", "/_next", "/api/internal"],
  "extra_headers": {
    "X-Test-Mode": "true",
    "X-API-Version": "2"
  },
  "feature_areas": ["auth", "dashboard", "products", "cart", "checkout"]
}
```

---

## 14. Data Schemas

### Full Field Reference for Key Schemas

#### `Requirement`
```python
req_id: str              # "REQ-001" format
title: str               # Short title (< 80 chars)
description: str         # Full requirement text
priority: str            # "must_have" | "should_have" | "nice_to_have"
type: str                # "functional" | "ui" | "navigation" | "integration"
feature_area: str        # "auth" | "checkout" | "dashboard" | ... (from domain_profile)
approved: bool           # True after HITL Phase 1 or auto-approval
gap_analysis: bool       # True if synthesized by Agent A Pass 4 (not in PDF)
confidence: float        # 0.0-1.0 extraction confidence score
run_prompt: str | None   # Human-provided instruction for this run
memory_note: str | None  # Human-provided lesson for future runs
```

#### `TestCase`
```python
test_id: str             # "TC-001" format, linked to req_id
req_id: str              # Links back to Requirement
title: str               # Playwright test() title
spec_file: str           # Which .spec.ts file this belongs to (by feature_area)
ts_code: str             # Full TypeScript test block (import + test())
selectors_used: list     # CSS selectors referenced in ts_code (for hallucination detection)
hallucinated: list       # Subset of selectors_used that are NOT in selector_map
repair_count: int        # How many times this test has been repaired (0 = original)
approved: bool           # True after HITL Phase 2 or auto-approval
```

#### `EvaluationReport`
```python
run_id: str
coverage_pct: float      # % of approved reqs with ≥1 passing test
execution_pct: float     # % of tests that passed
hallucination_count: int # Total unique hallucinated selectors this run
results: list[TestResult]
loop_history: list[dict] # [{loop, coverage, execution, hallucinations, action}]
exit_reason: str         # "targets_met" | "max_loops" | "stall" | "error"
dominant_failure_type: str  # Most common failure type this loop
```

---

## 15. Persistence & State Management

### What Is Persisted Where

```
cache/
├── checkpoints.db              # LangGraph SQLite checkpoint (entire AgentState per node)
│                               # Used for: resume interrupted run with --run-id
│                               # Delete to: start a completely fresh run
│
└── requirements_<sha256>.json  # Agent A output, keyed by PDF file hash
                                # Used for: skip re-extraction if same PDF used again
                                # Delete to: force re-extraction from PDF

memory/
├── chroma_db/                  # Vector database: lessons, repair strategies, hallucinations
│                               # Used for: cross-run learning, selector injection, blocklisting
│                               # Delete to: start learning from zero (loses all history)
│
├── domain_selectors.json       # Confirmed CSS selectors per domain+page
│                               # Grows across runs; injected into Agent B
│
├── hallucination_list.json     # Confirmed non-existent selectors
│                               # Injected into Agent B to prevent reuse
│
├── run_metrics.json            # Coverage/pass history for monitoring dashboard
│
├── feedback_history.json       # Audit trail of all HITL decisions (created on first interactive run)
│
└── prompt_versions.json        # Evolved prompt versions (created on-demand)

output/
├── report_<run_id>.html        # Quality report for each run
├── pw_results_<run_id>.json    # Raw Playwright test results (JSON reporter output)
├── review_<run_id>_phase1.html # HITL Phase 1 review page (served at localhost:9999)
├── review_<run_id>_phase2.html # HITL Phase 2 review page
└── feedback_<run_id>_phase*.json  # Saved HITL feedback

monitoring/
├── metrics.jsonl               # Telemetry events (append-only, one JSON per line)
└── dashboard.html              # Generated monitoring dashboard

playwright_project/
├── playwright.config.ts        # Playwright configuration (workers=1, timeout=90s, baseURL from env)
├── package.json                # @playwright/test dependency
└── tests/
    └── *.spec.ts               # Generated test files (re-written every evaluator loop)
```

### Resume Behavior

When `python main.py resume --run-id ats_20260318_131928_81d907`:
1. LangGraph reads last saved checkpoint from `cache/checkpoints.db`
2. Restores full `AgentState` (requirements, tests, eval report, loop count, etc.)
3. Determines last completed node
4. Continues from the next node
5. All memory and selector data are also still intact in `memory/`

**When to use resume vs fresh run:**
- Resume: Pipeline crashed mid-run, Playwright timed out, rate limit halted execution
- Fresh run: New PDF, new URL, or you want to test from scratch with learned memory
- Full reset: New URL AND you want to discard all memory

---

## 16. Design Decisions & Alternatives

### Decision 1: LangGraph for Orchestration

**Chosen:** LangGraph (graph-based state machine with conditional routing)

**Why:**
- Built-in checkpoint/resume for fault-tolerant long runs
- Clean separation of state from computation (each node receives/returns state slices)
- Native async support for concurrent node execution
- First-class conditional edges map exactly to the planner's routing decisions

**Alternatives considered:**
- **CrewAI / AutoGen multi-agent:** Better for collaborative agent conversations; overkill for a sequential pipeline with shared state
- **Prefect / Airflow:** DAG-based; can't express conditional loops (repair → test → repair)
- **Custom async loop:** Simpler but no checkpoint support, harder to add new nodes

### Decision 2: ReAct Planning Pattern

**Chosen:** Single LLM planner that observes state and decides next action each loop

**Why:**
- Single decision point = easy to reason about and debug
- LLM reasons naturally over the multi-dimensional state (coverage, failures, hallucinations, loops)
- Override rules prevent pathological loops without constraining good decisions

**Alternatives considered:**
- **Rule-based state machine:** Faster and more predictable; but can't handle edge cases the rules don't cover (e.g., "should I repair or regenerate when I'm at 84% and loop 7?")
- **Multi-agent voting:** Multiple LLMs vote on next action; more robust but 3-5× more API calls per decision
- **Hierarchical planner:** Separate meta-planner + micro-planners; over-engineered for the current decision space

### Decision 3: Separate Agents for Extract/Codegen/Repair

**Chosen:** Three specialized agents (A, B, C) with different models and system prompts

**Why:**
- Different models are optimal for different tasks (extraction=long context, codegen=code model, repair=reasoning)
- Specialized system prompts per agent dramatically outperform a single generic agent
- Isolation means bugs in one agent don't corrupt the others

**Alternatives considered:**
- **Single LLM for everything:** Simpler architecture; but a single prompt trying to do extraction + codegen + repair simultaneously produces mediocre results at all three
- **GPT-4 function calling:** More structured but expensive; the current tier system achieves similar structure via JSON prompts for free

### Decision 4: ChromaDB for Lesson Memory

**Chosen:** ChromaDB (local vector database) with FAISS-based similarity search

**Why:**
- Local (no external service dependency)
- Semantic similarity search for lesson retrieval works much better than keyword matching
- Native Python integration
- Handles multiple collections with metadata filtering (scope, confidence, domain)

**Alternatives considered:**
- **JSON flat file of lessons:** Simpler but no semantic similarity — "always use domcontentloaded" and "avoid networkidle" are the same lesson expressed differently; a flat file would store them twice
- **Pinecone / Weaviate (cloud):** Better scalability but adds an external dependency and cost
- **SQLite full-text search:** Decent for keyword matching but misses semantic equivalence

### Decision 5: `domcontentloaded` instead of `networkidle`

**Chosen:** `page.waitForLoadState('domcontentloaded')` in all generated tests

**Why:**
`networkidle` requires all network requests to be idle for 500ms. Modern web applications (especially analytics-heavy sites like Heroku) continuously fire background requests (analytics beacons, chat widgets, websockets). This means `networkidle` **never** fires — causing every test to timeout after 30 seconds.

`domcontentloaded` fires when the initial HTML is parsed and all blocking scripts are executed. For functional UI testing, this is the right moment to start asserting.

**Alternative:** `load` event (all resources including images loaded). Slower than `domcontentloaded`, but more stable for pages that render content via synchronous JS. `domcontentloaded` is the right default.

### Decision 6: Chunk Overlap = 0 for PDF Extraction

**Chosen:** 4000-char chunks with 0 overlap

**Why:**
Positive chunk overlap (e.g., 200 chars) causes requirements near chunk boundaries to appear in two consecutive chunks. Agent A extracts them twice with slightly different phrasing. Even with deduplication, this wastes 10–15% of Gemini API calls on content that's already been extracted.

The RAG enrichment in Pass 2 handles boundary truncation more precisely using semantic similarity — it identifies requirements that appear to be cut off mid-sentence and retrieves the continuation from adjacent chunks.

**Alternative:** 500-char overlap with stricter deduplication. Works but wastes API calls on an already costly extraction step.

### Decision 7: Batch Size Limits (10 for codegen, 8 for repair)

**Chosen:** Codegen: 10 requirements/batch; Repair: 8 tests/batch

**Why codegen=10:**
10 requirements with system prompt + memory injection stays comfortably within Groq's 6000 token/minute rate limit. 15 would exceed it consistently.

**Why repair=8 (not 10):**
Each repair call includes the original test code + error message + DOM snapshot for each failing test. DOM snapshots average 2–3K tokens per test. At 10 tests, a repair batch would be ~25K tokens, well above Groq's per-request context window on the free tier.

### Decision 8: Selector Stability Scoring

**Chosen:** `data-testid=1.0, aria-label=0.9, id=0.8, name=0.7, type=0.6, class=0.4, positional=0.2`

**Why:**
Selectors are scored by their likelihood of surviving application code changes. `data-testid` attributes are explicitly added for testing and only removed when tests are removed. Positional selectors (`.container:nth-child(3) > div:first-child`) break on any DOM restructure.

**Alternative:** Require all selectors be `data-testid`. This would be ideal but requires the target application to have testing attributes, which most real-world sites don't.

---

## 17. Key Constants & Thresholds

| Constant | Value | Effect of Changing |
|----------|-------|-------------------|
| `DEFAULT_TEMPERATURE` | 0.1 | Low temperature for structured extraction and codegen; higher values introduce unpredictability in JSON output |
| `PLANNING_TEMPERATURE` | 0.3 | Slightly higher for the ReAct planner to allow more varied reasoning |
| `MAX_LOOPS` | 5 | Lower = faster runs, lower final coverage; Higher = more thorough but slower |
| `TARGET_COVERAGE` | 85% | Minimum coverage to call the run "successful" |
| `TARGET_EXEC` | 80% | Minimum pass rate to call the run "successful" |
| `CHUNK_SIZE` | 4000 chars | Larger = fewer chunks but may hit model context limits |
| `CHUNK_OVERLAP` | 0 | Keep at 0; any positive value causes systematic duplicate extraction |
| `MAX_CRAWL_PAGES` | 15 | Higher = more selectors but much longer crawl time |
| `CRAWL_DEPTH` | 2 | How deep to follow links from homepage |
| `SELECTOR_MIN_SCORE` | 0.4 | Lower = include class-based selectors; raise to 0.7 to use only id/aria/data-testid |
| `CODEGEN_BATCH_SIZE` | 10 | Requirements per Agent B LLM call |
| `REPAIR_BATCH_SIZE` | 8 | Failing tests per Agent C LLM call |
| `ASYNC_CONCURRENCY` | 3 | Parallel LLM calls; higher = faster but more rate limits |
| `MEMORY_INJECTION_THRESHOLD` | 0.65 | Minimum lesson confidence to include in prompts |
| `HITL_TIMEOUT_MINUTES` | 60 | Auto-continue if no human feedback received |
| `STALL_COVERAGE_DELTA` | 2% | Coverage improvement below this = stall detected |

---

## 18. Reset Procedures

### Full Reset (New URL or New PDF)

Delete all generated state, keep source code and prompts:

**Linux / macOS:**
```bash
rm -f cache/checkpoints.db cache/requirements_*.json
rm -f memory/domain_selectors.json memory/hallucination_list.json
rm -f memory/run_metrics.json memory/feedback_history.json memory/prompt_versions.json
rm -rf memory/chroma_db/
rm -f output/*.html output/*.json
rm -f playwright_project/tests/*.spec.ts
rm -f monitoring/metrics.jsonl monitoring/dashboard.html
rm -f prompts/history/*
```

**Windows (PowerShell):**
```powershell
Remove-Item cache\checkpoints.db, cache\requirements_*.json -ErrorAction SilentlyContinue
Remove-Item memory\domain_selectors.json, memory\hallucination_list.json -ErrorAction SilentlyContinue
Remove-Item memory\run_metrics.json, memory\feedback_history.json, memory\prompt_versions.json -ErrorAction SilentlyContinue
Remove-Item memory\chroma_db -Recurse -ErrorAction SilentlyContinue
Remove-Item output\*.html, output\*.json -ErrorAction SilentlyContinue
Remove-Item playwright_project\tests\*.spec.ts -ErrorAction SilentlyContinue
Remove-Item monitoring\metrics.jsonl, monitoring\dashboard.html -ErrorAction SilentlyContinue
Remove-Item prompts\history\* -ErrorAction SilentlyContinue
```

### Partial Reset (Same URL, Iterate on PDF)

Keep learned memory (selectors, lessons, hallucination blocklist); clear only run-specific state:

```bash
# Linux/macOS
rm -f cache/checkpoints.db cache/requirements_*.json
rm -f output/*.html output/*.json
rm -f playwright_project/tests/*.spec.ts
```
```powershell
# Windows (PowerShell)
Remove-Item cache\checkpoints.db, cache\requirements_*.json -ErrorAction SilentlyContinue
Remove-Item output\*.html, output\*.json -ErrorAction SilentlyContinue
Remove-Item playwright_project\tests\*.spec.ts -ErrorAction SilentlyContinue
```

### Retry Only (Re-run Playwright on Existing Tests)

Keep everything; just clear the checkpoint to re-run from test execution:

```bash
rm -f cache/checkpoints.db                                          # Linux/macOS
```
```powershell
Remove-Item cache\checkpoints.db -ErrorAction SilentlyContinue       # Windows
```

### Memory-Only Reset

Keep run outputs, clear only the learned memory (start learning from scratch):

```bash
# Linux/macOS
rm -rf memory/chroma_db/
rm -f memory/domain_selectors.json memory/hallucination_list.json
```
```powershell
# Windows (PowerShell)
Remove-Item memory\chroma_db -Recurse -ErrorAction SilentlyContinue
Remove-Item memory\domain_selectors.json, memory\hallucination_list.json -ErrorAction SilentlyContinue
```

---

## 19. Dependencies

### Python Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `openai` | ≥1.30.0 | OpenAI-compatible SDK (used for Groq, OpenRouter, Cerebras, Mistral) |
| `google-generativeai` | ≥0.7.0 | Google Gemini API (native SDK, required for PDF extraction) |
| `langgraph` | ≥0.2.0 | Graph-based pipeline orchestration |
| `langgraph-checkpoint-sqlite` | ≥1.0.0 | SQLite checkpoint backend for resume support |
| `langchain-core` | ≥0.2.0 | Base types for LangGraph |
| `chromadb` | ≥0.5.0 | Local vector database for lesson storage |
| `sentence-transformers` | ≥3.0.0 | Local embedding model for ChromaDB |
| `faiss-cpu` | ≥1.8.0 | Similarity search for RAG enrichment |
| `playwright` | ≥1.44.0 | Browser automation for crawling + test execution |
| `pdfplumber` | ≥0.11.0 | PDF text + table extraction |
| `httpx` | ≥0.27.0 | Async HTTP client for crawling + LLM APIs |
| `beautifulsoup4` | ≥4.12.0 | HTML parsing for route discovery |
| `pydantic` | ≥2.7.0 | Data validation + serialization for all schemas |
| `python-dotenv` | ≥1.0.0 | `.env` file loading |
| `rich` | ≥13.7.0 | Terminal output styling + HITL Phase 3 TUI |
| `questionary` | ≥2.0.0 | Interactive terminal prompts for HITL Phase 3 |
| `watchdog` | ≥4.0.0 | File system watcher for HITL feedback detection |
| `plotly` | ≥5.22.0 | Charts in quality report |
| `pdf2image` | ≥1.16.0 | OCR fallback for scanned PDFs |
| `pytesseract` | ≥0.3.10 | OCR fallback (requires system `tesseract` package) |

### Node.js Dependencies (`playwright_project/package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| `@playwright/test` | 1.58.2 | TypeScript Playwright test runner |

Install with:
```bash
cd playwright_project && npm install
npx playwright install chromium
```

### Playwright Configuration (`playwright_project/playwright.config.ts`)

Non-default settings that affect test behavior:

| Setting | Value | Playwright Default | Rationale |
|---------|-------|--------------------|-----------|
| `workers` | 1 | Half CPU cores | Sequential execution ensures tests don't interfere with each other |
| `timeout` | 90,000ms | 30,000ms | Agent-generated tests may need longer setup |
| `actionTimeout` | 20,000ms | No timeout | Prevents tests from hanging indefinitely |
| `navigationTimeout` | 45,000ms | 30,000ms | Slow sites need more time |
| `fullyParallel` | false | true | Sequential prevents state conflicts |
| `baseURL` | `process.env.ATS_BASE_URL` | none | Set automatically by evaluator engine |

### Required API Keys

| Key | Required | Provider | Free Tier |
|-----|----------|----------|-----------|
| `GROQ_API_KEY` | Yes | groq.com | 14,400 req/day |
| `GEMINI_API_KEY` | Yes | aistudio.google.com | 1,500 req/day |
| `OPENROUTER_API_KEY` | Yes (in `REQUIRED_KEYS`) | openrouter.ai | Pay-per-use |
| `CEREBRAS_API_KEY` | No (fallback) | cerebras.ai | Limited free tier |
| `MISTRAL_API_KEY` | No (fallback) | mistral.ai | Limited free tier |

---

## 20. Frequently Asked Questions

### Why does the first run always start at 14-34% pass rate?

Agent B has no confirmed selectors for a new domain on the first run. It either invents selectors (hallucinations) or uses generic role-based selectors that may match multiple elements (strict mode). The repair loop and on-demand crawl progressively discover real selectors and fix the tests. By loop 3-4 on most sites, coverage reaches 75-90%.

The second run on the same domain starts much higher because confirmed selectors and lessons from the first run are injected into Agent B upfront.

### Why does the crawler cap at 15 pages? The site has hundreds.

`MAX_CRAWL_PAGES=15` is the default to prevent extremely long crawl times and rate limiting on target sites. The crawler is smart about which 15 pages to pick: it prioritizes pages from `domain_profile.likely_routes` (high-value pages like login, checkout, dashboard) over arbitrary blog posts.

For thorough testing of larger sites, increase `MAX_CRAWL_PAGES=50` in `.env`. Expect 4–5× longer crawl time.

### Why does the repair agent sometimes fail to fix a test after 3 loops?

Some failures are genuinely unresolvable by the repair agent:
1. **Dynamic content:** Content that changes on every page load (recommendations, timestamps, randomized CTAs)
2. **Auth-gated content:** Tests navigating to auth-required routes without the correct auth state
3. **JavaScript-rendered content:** Content that only appears after complex JS execution that `domcontentloaded` doesn't wait for
4. **A/B tests:** The application shows different UI to different users

These tests will remain failing unless (1) the requirement is marked non-testable and removed, (2) `resource.json` is updated with the correct auth config, or (3) the test is manually simplified.

### How does the system know when it's "stalling"?

If coverage improves by less than 2% between two consecutive loops, `stall_count` increments. At `stall_count == 2` (three consecutive near-zero improvements), the planner forces a full code regeneration instead of continuing to repair the same tests.

This prevents the pipeline from spending MAX_LOOPS doing repairs that aren't improving coverage.

### Can I use this on a site that requires login?

Yes. Add auth config to `input/resource.json`:
```json
{
  "auth": {
    "type": "form_login",
    "credentials": { "username": "...", "password": "..." },
    "login_url": "/login"
  }
}
```

The auth handler performs the login via Playwright and saves the session. The crawler's auth track crawls authenticated routes. Agent B adds login preambles to tests for auth-required pages.

### What happens if the LLM API rate limits mid-run?

The LLM router has `MAX_RETRIES=3` with exponential backoff per call. If a provider is rate-limited, the router tries the next provider in the fallback chain. If all providers fail for a specific tier, the call raises an exception, which LangGraph catches and can checkpoint. The run can be resumed with `python main.py resume --run-id <id>` once the rate limits reset.

### Why is Gemini used only for extraction and not for everything?

**Context window:** Gemini 2.5 Flash has a 1M token context, which is uniquely useful for processing large PDFs in Pass 1 without splitting into too many chunks. Other free models have 8K–32K context.

**Rate limits:** Gemini free tier allows 1,500 requests/day, which is sufficient for 1-2 full runs. Using it for codegen and repair (which need 50-100+ calls per loop) would exhaust the daily quota in a single run.

**Cost/quality tradeoff:** Kimi K2 on Groq produces better TypeScript than Gemini for the same task.

### Why is there a separate `prompts/` directory if prompts are also in the Python files?

Agent A's system prompts (`_P1_SYSTEM`, `_P3_SYSTEM`, etc.) are inline in `extraction_agent.py` because they are tightly coupled to the parsing logic — changing them requires changing how the output is processed.

Agent B (`agent_b_codegen_v1.txt`) and Agent C (`agent_c_repair_v1.txt`) prompts are in separate files because:
1. They are versioned (the `v1` in the name is intentional)
2. They can be evolved by a prompt evolution system without code changes
3. They are shared between the generation path and any future fine-tuning pipeline

The `prompts/history/` directory stores previous versions when prompts are evolved.

### What is the difference between `coverage_pct` and `execution_pct`?

- **Coverage %** = (approved requirements with ≥1 passing test) / (total approved requirements)
  - Measures: "Are we testing what was required?"
  - Example: 40 requirements, 37 have at least one passing test → coverage = 92.5%

- **Execution % (pass rate)** = (tests that passed) / (total tests)
  - Measures: "Are the tests we wrote actually passing?"
  - Example: 43 tests total, 42 pass → execution = 97.7%

A test suite can have high execution % but low coverage if multiple tests cover the same requirement and some requirements have no tests.

### Can I run just the extraction or just the code generation?

```bash
# Only extract requirements (output to cache/)
python main.py run --url https://example.com --pdf reqs.pdf --extract-only

# Only generate code (needs cached or provided requirements)
python main.py run --url https://example.com \
  --requirements cache/requirements_ffb6b4e9c77b6c34.json \
  --codegen-only
```

### How do I add support for a new authentication type?

1. Add the new auth type to `app/schemas.py:AuthContext.auth_type` literal type
2. Implement the auth logic in `app/core/auth_handler.py:handle_auth()`
3. Add a test case in `resource.example.json`
4. The rest of the pipeline picks up `AuthContext` automatically

---

## Project Structure Summary

```
ats/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── resource.example.json            # Auth/config template
├── RESET_INSTRUCTIONS.txt           # Reset guide
│
├── app/
│   ├── config.py                    # All constants, model IDs, thresholds
│   ├── schemas.py                   # All Pydantic data models
│   │
│   ├── agents/
│   │   ├── extraction_agent.py      # Agent A: 5-pass PDF → requirements
│   │   ├── codegen_agent.py         # Agent B: requirements → TypeScript tests
│   │   ├── repair_agent.py          # Agent C: failing tests → repaired tests
│   │   └── domain_inferrer.py       # URL → DomainProfile classification
│   │
│   ├── core/
│   │   ├── react_controller.py      # LangGraph orchestrator + planner
│   │   ├── pdf_extractor.py         # PDF text extraction + chunking
│   │   ├── route_crawler.py         # Route discovery + CSS selector extraction
│   │   ├── auth_handler.py          # Authentication flow handler
│   │   ├── evaluator_engine.py      # Playwright runner + failure classifier
│   │   ├── post_run_learner.py      # Extract + persist lessons post-run
│   │   ├── quality_monitor.py       # Run quality assessment + HTML report
│   │   ├── telemetry.py             # Agent event logging → metrics.jsonl
│   │   └── monitoring_dashboard.py  # Dynatrace-style HTML dashboard
│   │
│   ├── hitl/
│   │   └── hitl_manager.py          # Human-in-the-loop review phases 1/2/3
│   │
│   ├── llm/
│   │   ├── router.py                # Tier routing + fallback chains + retries
│   │   ├── gemini.py                # Google Gemini API
│   │   ├── groq.py                  # Groq API (OpenAI-compat)
│   │   ├── openrouter.py            # OpenRouter (paid fallback)
│   │   ├── cerebras.py              # Cerebras (fast inference)
│   │   ├── mistral.py               # Mistral (code fallback)
│   │   └── huggingface.py           # Local embeddings (all-MiniLM-L6-v2)
│   │
│   └── memory/
│       └── agent_memory.py          # ChromaDB + JSON persistent memory API
│
├── prompts/
│   ├── agent_b_codegen_v1.txt       # Agent B system prompt (versioned)
│   ├── agent_c_repair_v1.txt        # Agent C system prompt (versioned)
│   └── history/                     # Evolved prompt versions
│
├── playwright_project/
│   ├── package.json                 # @playwright/test dependency
│   ├── playwright.config.ts         # Playwright config (workers=1, timeouts, baseURL)
│   └── tests/
│       └── *.spec.ts                # Generated test files (auto-created)
│
├── input/                           # Input files (PDFs, resource.json)
├── cache/                           # checkpoints.db + requirements cache
├── memory/                          # ChromaDB + JSON memory files
├── output/                          # HTML reports + Playwright results
└── monitoring/                      # metrics.jsonl + dashboard.html
```

---

*ATS v8 — Built with LangGraph, Playwright, ChromaDB, and a tiered multi-model LLM pipeline.*
