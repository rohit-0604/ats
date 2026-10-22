"""
ATS v8 — Agent B: TypeScript Code Generation
Generates one Playwright TypeScript test per approved requirement.
Model: moonshotai/kimi-k2-instruct (Groq) — Tier 3.

Key details:
- Batches 10 requirements per LLM call (CODEGEN_BATCH_SIZE)
- Injects memory: lessons + confirmed selectors + hallucination blocklist
- Injects per-item human prompts from HITL Phase 1
- Three-pass JSON escape sanitisation before json.loads
- Async concurrent batching (ASYNC_CONCURRENCY=3)
"""

from __future__ import annotations
import asyncio
import json
import logging
import re
import time
from typing import Optional

from app.config import (
    CODEGEN_BATCH_SIZE, ASYNC_CONCURRENCY,
    USE_ASYNC, PROMPTS_DIR,
)
from app.llm.router import Tier, complete
from app.memory.agent_memory import get_lessons, get_selectors, get_hallucination_blocklist, get_repair_strategies
from app.schemas import (
    Requirement, RequirementBundle, TestCase, TestSuite, DomainProfile, PageSelectorMap,
)

log = logging.getLogger(__name__)

# ─── System prompt (loaded from file if it exists, else inline default) ───────

_DEFAULT_SYSTEM = """You are an expert Playwright TypeScript test engineer.

Generate one complete Playwright test per requirement. Output ONLY a JSON array.

Each element:
{
  "req_id": "<same req_id as input>",
  "title": "<test title>",
  "spec_file": "<feature_area>.spec.ts",
  "ts_code": "<complete TypeScript test block>"
}

PLAYWRIGHT RULES:
- Always use: import { test, expect } from '@playwright/test';
- Every test is async: test('title', async ({ page }) => { ... });
- Use page.goto() for navigation — always await it
- Use await page.waitForLoadState('domcontentloaded') after navigation — NEVER use 'networkidle' (external sites never reach networkidle)
- Use expect(locator).toBeVisible() not .isVisible()
- Use page.locator() not page.$ or page.$$
- For clicks: await page.locator(sel).click()
- For fills: await page.locator(sel).fill('value')
- waitForURL after form submission: await page.waitForURL('**/target-path')
- Wrap assertions in expect() — never use raw boolean checks

SELECTOR RULES:
- ONLY use selectors from the CONFIRMED SELECTORS list if provided
- NEVER invent CSS selectors not in the confirmed list
- If no confirmed selector fits, use: page.getByRole() or page.getByText()
- NEVER use nth-child, nth-of-type, or positional selectors
- NEVER use locator('generic') or locator('paragraph') — these are ARIA snapshot labels, NOT valid CSS selectors
- For text paragraphs use locator('p') not locator('paragraph')
- For list items use locator('li') not locator('listitem')
- For images use locator('img') not locator('image')
- For links use getByRole('link') not locator('link')

WHAT NOT TO TEST (generates unreliable tests that always fail):
- NEVER assert computed CSS values: backgroundColor, color, fontSize, zIndex — these vary by browser
- NEVER count exact numbers of generic DOM children (cards, items, divs) unless using a unique data-testid or role
- NEVER assert pixel dimensions, spacing, or layout positions
- NEVER use window.getComputedStyle() assertions
- NEVER assert DOM nesting depth or structural hierarchy

INSTEAD — test the observable, semantic intent:
- "Minimum 4 feature cards" → assert the section heading is visible + at least one card link is visible
- "Hero has purple background" → assert the hero section or its heading is visible
- "Social icons in footer" → assert the social navigation landmark is visible
- "Pricing plans exist" → assert the pricing page link or heading is visible

AUTH PREAMBLE RULES:
- If a test navigates to a route listed under ROUTES THAT REQUIRE LOGIN,
  you MUST add a login block at the start of that test BEFORE the page.goto().
- Login preamble template (fill in the actual login selectors from the confirmed list):
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.locator(<username_selector>).fill(process.env.TEST_USERNAME || '');
    await page.locator(<password_selector>).fill(process.env.TEST_PASSWORD || '');
    await page.locator(<submit_selector>).click();
    await page.waitForURL('**/dashboard');
- Use the confirmed login selectors if present, otherwise use page.getByLabel('Username') etc.
- Do NOT add the login preamble to tests for guest-accessible routes.

OUTPUT RULES:
- ts_code must be valid TypeScript — no syntax errors
- ts_code must be a complete test block including the import statement
- Use double quotes for attribute selectors: [attr="value"] not [attr='value']
- JSON must be valid — use double quotes, escape backslashes properly
- Return [] if you cannot generate tests for the given requirements"""


def _get_system_prompt() -> str:
    """Load prompt from file if versioned prompt exists, else use default."""
    prompt_file = PROMPTS_DIR / "agent_b_codegen_v1.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    # Write default on first run
    prompt_file.write_text(_DEFAULT_SYSTEM, encoding="utf-8")
    return _DEFAULT_SYSTEM


# ─── Memory injection ─────────────────────────────────────────────────────────

def _build_memory_block(
    domain_profile: DomainProfile,
    selector_map: Optional[PageSelectorMap],
    query_hint: str = "",
) -> str:
    """
    Builds a memory context block to prepend to the system prompt.
    Includes: lessons + confirmed selectors + auth route info + hallucination blocklist.
    Auth-only selectors and routes are labelled separately so the LLM
    knows to add a login preamble for tests that navigate to those routes.
    """
    parts: list[str] = []

    # Lessons
    lessons = get_lessons(
        query=f"playwright typescript test {domain_profile.app_type} {query_hint}",
        base_url=domain_profile.base_url,
        app_type=domain_profile.app_type,
        n_results=10,
    )
    if lessons:
        lesson_lines = "\n".join(f"- {l['text']}" for l in lessons)
        parts.append(f"PROVEN PATTERNS FROM PREVIOUS RUNS:\n{lesson_lines}")

    # Confirmed selectors from memory (high-confidence, seen in previous runs)
    mem_selectors = set(get_selectors(domain_profile.base_url, min_score=0.7))

    # Selectors from current crawl — split by auth vs guest
    # Deduplicate crawl selectors against memory selectors to avoid repetition in prompt
    if selector_map:
        guest_sels = list(set(
            s.selector for _path, entries in selector_map.pages.items()
            for s in entries
            if not s.requires_auth and s.score >= 0.6
        ))
        auth_sels = list(set(
            s.selector for _path, entries in selector_map.pages.items()
            for s in entries
            if s.requires_auth and s.score >= 0.6
        ))
        # Remove crawl selectors already covered by memory to keep prompt concise
        guest_sels_new = [s for s in guest_sels if s not in mem_selectors]
        auth_sels_new  = [s for s in auth_sels  if s not in mem_selectors]
    else:
        guest_sels_new = []
        auth_sels_new  = []

    # Combine memory + new crawl selectors into one confirmed list
    all_confirmed = list(mem_selectors) + guest_sels_new
    if all_confirmed:
        parts.append(
            "CONFIRMED REAL SELECTORS FOR THIS APP (use these — do not invent others):\n"
            + "\n".join(all_confirmed[:40])
        )

    if auth_sels_new:
        parts.append(
            "AUTHENTICATED-ONLY SELECTORS "
            "(only visible after login — add login preamble to these tests):\n"
            + "\n".join(auth_sels_new[:30])
        )

    if selector_map and selector_map.auth_routes:
        parts.append(
            "ROUTES THAT REQUIRE LOGIN "
            "(page.goto() to any of these must be preceded by a login block):\n"
            + "\n".join(selector_map.auth_routes[:20])
        )

    # Repair strategies — what errors previously occurred and what fixed them
    # This closes the Agent C → Agent B feedback loop:
    # Agent C fixes tests each run; these strategies teach Agent B to avoid the same mistakes
    repair_strats = get_repair_strategies(
        error_text=f"playwright test failure {domain_profile.app_type} {query_hint}",
        base_url=domain_profile.base_url,
        app_type=domain_profile.app_type,
        n=5,
    )
    if repair_strats:
        strat_lines = "\n".join(
            f"- Error type '{s['error']}' was fixed by: {s['fix']}" for s in repair_strats
        )
        parts.append(
            f"KNOWN REPAIR PATTERNS (avoid generating tests that will need these fixes):\n{strat_lines}"
        )

    # Hallucination blocklist — deduplicated against confirmed selectors already injected
    # A selector cannot appear in both "use this" and "never use this"
    blocklist = get_hallucination_blocklist()
    if blocklist:
        confirmed_set = set(all_confirmed)  # already computed above
        filtered_blocklist = [s for s in blocklist[:20] if s not in confirmed_set]
        if filtered_blocklist:
            block_lines = "\n".join(filtered_blocklist)
            parts.append(f"NEVER USE THESE SELECTORS (confirmed hallucinations):\n{block_lines}")

    return "\n\n".join(parts)


# ─── JSON escape sanitisation ─────────────────────────────────────────────────

def _sanitise_json(raw: str) -> str:
    """
    Three-pass sanitisation of LLM JSON output before json.loads.

    Root cause: Kimi K2 generates CSS attribute selectors like a[href*='join']
    and escapes the single quote as \\' — invalid JSON escape sequence.

    Pass 1:  Fix invalid \\X sequences (\\d \\w \\s \\p \\h \\v etc.)
             Explicitly EXCLUDE \\' from this pass — handled in Pass 1b.
    Pass 1b: Strip over-escaped single quotes:  \\'  →  '
    Pass 2:  Replace raw control bytes (0x0A, 0x0D, 0x09) inside JSON strings.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:typescript|json|ts)?|```", "", raw).strip()

    # Pass 1: fix invalid \X escape sequences (not \n \t \r \\ \" \/ \b \f \uXXXX \')
    VALID_ESCAPES = set("ntrb/f\\\"u'")
    def fix_escape(m: re.Match) -> str:
        char = m.group(1)
        if char in VALID_ESCAPES:
            return m.group(0)   # leave valid escapes alone
        return char             # strip the backslash
    text = re.sub(r"\\([^ntrb/f\\\"u'])", fix_escape, text)

    # Pass 1b: strip over-escaped single quotes \' → '
    text = text.replace("\\'", "'")
    # Also handle double-escaped: \\' → '
    text = text.replace("\\\\'", "'")

    # Pass 2: replace raw control bytes inside JSON string values
    # Only replace bytes that aren't already escaped
    result = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == "\\":
            result.append(ch)
            escaped = True
            continue
        if ch == '"' and not escaped:
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch in ("\n", "\r", "\t"):
            # Replace with JSON escape
            replacements = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
            result.append(replacements[ch])
            continue
        result.append(ch)

    return "".join(result)


def _parse_batch(raw: str, requirements: list[Requirement]) -> list[TestCase]:
    """
    Parse LLM output for a batch of requirements into TestCase objects.
    Applies three-pass sanitisation, falls back gracefully on parse failure.
    """
    sanitised = _sanitise_json(raw)
    req_map = {r.req_id: r for r in requirements}

    # Iterative fix: strip the offending escape and retry up to 5 times
    for attempt in range(5):
        try:
            items = json.loads(sanitised)
            if not isinstance(items, list):
                items = []
            break
        except json.JSONDecodeError as e:
            msg = str(e)
            if "Invalid \\escape" in msg:
                # Find the char after backslash at error position and strip it
                import re
                sanitised = re.sub(r'\\([^"\\/bfnrtu])', r'\1', sanitised)
            else:
                log.warning(f"Agent B: JSON parse failed after sanitisation: {e}")
                log.debug(f"Agent B: sanitised output (first 500): {sanitised[:500]}")
                return []
    else:
        log.warning("Agent B: JSON parse failed after 5 fix attempts")
        return []

    tests: list[TestCase] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        req_id  = item.get("req_id", "")
        ts_code = item.get("ts_code", "")
        title   = item.get("title", "")
        spec    = item.get("spec_file", "general.spec.ts")
        if not req_id or not ts_code:
            continue
        req = req_map.get(req_id)
        tests.append(TestCase(
            test_id=f"TEST-{req_id}",
            req_id=req_id,
            title=title,
            spec_file=spec,
            ts_code=ts_code,
            human_prompt=req.human_prompt if req else None,
        ))
    return tests


# ─── Single batch call ────────────────────────────────────────────────────────

def _run_batch(
    batch: list[Requirement],
    system_with_memory: str,
    global_prompt: Optional[str],
    category_prompts: dict[str, str],
    run_id: str,
    batch_idx: int,
) -> list[TestCase]:
    """Synchronous single-batch codegen call."""

    # Build per-item prompt additions
    item_prompts = []
    for req in batch:
        parts = []
        if req.human_prompt:
            parts.append(f"[{req.req_id}] SPECIFIC INSTRUCTION: {req.human_prompt}")
        # Category prompt for this requirement's feature area
        if req.feature_area and req.feature_area in category_prompts:
            parts.append(f"[{req.req_id}] CATEGORY RULE: {category_prompts[req.feature_area]}")
        if parts:
            item_prompts.extend(parts)

    user_content_parts = []
    if global_prompt:
        user_content_parts.append(f"GLOBAL INSTRUCTION FOR THIS RUN: {global_prompt}\n")
    if item_prompts:
        user_content_parts.append("PER-REQUIREMENT INSTRUCTIONS:\n" + "\n".join(item_prompts) + "\n")

    req_list = [
        {
            "req_id":      r.req_id,
            "title":       r.title,
            "description": r.description,
            "priority":    r.priority,
            "feature_area": r.feature_area,
        }
        for r in batch
    ]
    user_content_parts.append(
        f"Generate Playwright TypeScript tests for these {len(batch)} requirements:\n"
        + json.dumps(req_list, indent=2)
    )

    messages = [
        {"role": "system", "content": system_with_memory},
        {"role": "user",   "content": "\n".join(user_content_parts)},
    ]

    raw = ""
    try:
        raw = complete(
            tier=Tier.CODEGEN,
            messages=messages,
            max_tokens=4096,
            label=f"codegen_batch{batch_idx}",
        )
        tests = _parse_batch(raw, batch)
        log.info(f"Agent B: batch {batch_idx} → {len(tests)}/{len(batch)} tests generated")
        return tests
    except Exception as e:
        log.error(f"Agent B: batch {batch_idx} failed: {e}")
        return []


# ─── Async concurrent batch runner ────────────────────────────────────────────

async def _run_all_batches_async(
    batches: list[list[Requirement]],
    system_with_memory: str,
    global_prompt: Optional[str],
    category_prompts: dict[str, str],
    run_id: str,
) -> list[TestCase]:
    """Run all batches concurrently with semaphore limiting concurrency."""
    sem = asyncio.Semaphore(ASYNC_CONCURRENCY)
    all_tests: list[TestCase] = []

    async def run_one(batch: list[Requirement], idx: int) -> list[TestCase]:
        async with sem:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: _run_batch(batch, system_with_memory, global_prompt,
                                   category_prompts, run_id, idx)
            )

    tasks = [run_one(batch, i + 1) for i, batch in enumerate(batches)]
    results = await asyncio.gather(*tasks)
    for r in results:
        all_tests.extend(r)
    return all_tests


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_codegen(
    bundle: RequirementBundle,
    selector_map: Optional[PageSelectorMap],
    run_id: str,
    global_prompt: Optional[str] = None,
    category_prompts: Optional[dict[str, str]] = None,
) -> TestSuite:
    """
    Generate TypeScript tests for all approved requirements in the bundle.
    Returns a deduplicated TestSuite.
    """
    domain_profile = bundle.domain_profile
    reqs = bundle.approved_requirements()
    cat_prompts = category_prompts or {}

    if not reqs:
        log.warning("Agent B: no approved requirements to generate tests for")
        return TestSuite(run_id=run_id, generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    if domain_profile is None:
        log.error("Agent B: bundle has no domain_profile — cannot build memory block")
        return TestSuite(run_id=run_id, generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    log.info(f"Agent B: generating tests for {len(reqs)} approved requirements")

    # Build memory-enriched system prompt
    # Use first batch's feature areas as query hint so lessons are requirement-specific
    first_batch_areas = list({r.feature_area for r in reqs[:CODEGEN_BATCH_SIZE] if r.feature_area})
    query_hint = " ".join(first_batch_areas)
    memory_block = _build_memory_block(domain_profile, selector_map, query_hint=query_hint)
    base_system  = _get_system_prompt()
    # Memory block goes FIRST — runtime context (real selectors, blocklist, lessons)
    # gets higher attention weight when it precedes the general rules
    system_with_memory = base_system
    if memory_block:
        system_with_memory = memory_block + "\n\n" + base_system

    # Split into batches
    batches = [
        reqs[i:i + CODEGEN_BATCH_SIZE]
        for i in range(0, len(reqs), CODEGEN_BATCH_SIZE)
    ]
    log.info(f"Agent B: {len(batches)} batches of ≤{CODEGEN_BATCH_SIZE} requirements")

    t0 = time.time()

    if USE_ASYNC and len(batches) > 1:
        all_tests = asyncio.run(
            _run_all_batches_async(
                batches, system_with_memory, global_prompt, cat_prompts, run_id
            )
        )
    else:
        all_tests = []
        for idx, batch in enumerate(batches, 1):
            all_tests.extend(
                _run_batch(batch, system_with_memory, global_prompt, cat_prompts, run_id, idx)
            )

    suite = TestSuite(
        tests=all_tests,
        run_id=run_id,
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    removed = suite.deduplicate()
    elapsed = round(time.time() - t0, 1)
    log.info(
        f"Agent B: complete. {len(suite.tests)} tests "
        f"({removed} duplicates removed) in {elapsed}s"
    )

    # ── Telemetry ─────────────────────────────────────────────────────────────
    try:
        from app.core.telemetry import emit as _emit
        hall_count = sum(1 for t in suite.tests if t.hallucinated)
        total      = len(suite.tests)
        hall_rate  = round(hall_count / total, 3) if total else 0
        _emit(run_id=run_id, agent="agent_b", event="codegen_complete", metrics={
            "tests_generated":     total,
            "duplicates_removed":  removed,
            "hallucination_count": hall_count,
            "hallucination_rate":  hall_rate,
            "batch_count":         len(batches),
            "duration_s":          elapsed,
        })
    except Exception:
        pass

    return suite
