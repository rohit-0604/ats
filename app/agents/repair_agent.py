"""
ATS v8 — Repair Agent (Agent C component)
Repairs failing tests using:
  - Error messages from Playwright
  - On-demand page crawl for real selectors
  - Memory: repair strategies + confirmed selectors + hallucination blocklist
Model: moonshotai/kimi-k2-instruct (Groq) — Tier 3.
Batches: REPAIR_BATCH_SIZE=8 (avoids 413 on free tier)
"""

from __future__ import annotations
import json
import logging
import re
from typing import Optional

from app.config import REPAIR_BATCH_SIZE, PROMPTS_DIR
from app.llm.router import Tier, complete
from app.memory.agent_memory import (
    get_repair_strategies, get_selectors, get_hallucination_blocklist,
    add_hallucination, add_repair_strategy,
)
from app.schemas import (
    TestCase, TestSuite, PageSelectorMap, SelectorEntry, DomainProfile, EvaluationReport,
)

log = logging.getLogger(__name__)

_DEFAULT_REPAIR_SYSTEM = """You are an expert Playwright TypeScript test engineer performing intelligent test repair.

You will receive failing tests with their error messages, failure type classification, and the real DOM snapshot at the moment of failure.

Return ONLY a JSON array. Each element:
{
  "test_id": "<same test_id as input>",
  "ts_code": "<complete corrected TypeScript test block>"
}

FAILURE TYPE REPAIR STRATEGIES:

1. failure_type = "selector_not_found"
   - The element does not exist with that selector
   - Look at the DOM SNAPSHOT to find what actually exists
   - Switch to page.getByRole(), page.getByText(), or page.getByLabel() using real text from the snapshot
   - NEVER keep the original selector that failed

2. failure_type = "strict_mode"
   - The selector matched multiple elements — Playwright refuses to pick one
   - Scope the locator: use page.getByRole('contentinfo').getByRole('link', ...) to narrow scope
   - Or add .first() to take the first match
   - Or use a more specific selector from the DOM SNAPSHOT

3. failure_type = "assertion_failure"
   - The element was found but the value didn't match
   - Read the actual value from the error message ("Received: ...")
   - Update the assertion to match reality, or use a flexible matcher (toContainText, regex)
   - Do NOT hardcode brittle values like exact colours or counts

4. failure_type = "timeout"
   - The locator NEVER attached — the element does not exist in this form
   - DO NOT just add more waits or increase timeout — the element is not there
   - This is a structural mismatch: the test was written for an element that doesn't exist
   - Look at the DOM SNAPSHOT to find what ACTUALLY exists on the page that proves the same requirement
   - Common causes: locator('generic'), locator('paragraph'), window.getComputedStyle(), counting arbitrary divs
   - ALWAYS rewrite using a visible semantic element from the DOM SNAPSHOT:
     * If test counted items → assert section heading is visible instead
     * If test checked computed CSS → assert the element containing that text is visible instead
     * If test used window.getComputedStyle() → assert the element is visible instead
     * If test navigated to a non-existent route → use the closest real route from REAL SELECTORS
   - Replace the entire assertion approach, not just the selector

5. failure_type = "network_error"
   - Navigation failed — wrong URL or page doesn't exist
   - Check the test URL against likely routes from the domain profile
   - Use a valid route from the REAL SELECTORS page list

GENERAL RULES:
- Use the DOM SNAPSHOT as your source of truth for what exists on the page
- Replace hallucinated selectors with ones from REAL SELECTORS list or DOM SNAPSHOT
- Never use positional selectors (nth-child, nth-of-type)
- Never use waitForLoadState('networkidle') — always use 'domcontentloaded'
- Maintain same test intent and assertions
- All TypeScript must be syntactically valid
- JSON must be valid — double quotes, no trailing commas"""


def _get_repair_system() -> str:
    prompt_file = PROMPTS_DIR / "agent_c_repair_v1.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    prompt_file.write_text(_DEFAULT_REPAIR_SYSTEM, encoding="utf-8")
    return _DEFAULT_REPAIR_SYSTEM


def _sanitise_json(raw: str) -> str:
    """Same three-pass sanitisation as codegen_agent."""
    text = re.sub(r"```(?:typescript|json|ts)?|```", "", raw).strip()

    VALID_ESCAPES = set("ntrb/f\\\"u'")
    def fix_escape(m: re.Match) -> str:
        char = m.group(1)
        return m.group(0) if char in VALID_ESCAPES else char
    text = re.sub(r"\\([^ntrb/f\\\"u'])", fix_escape, text)
    text = text.replace("\\'", "'").replace("\\\\'", "'")

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
            replacements = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
            result.append(replacements[ch])
            continue
        result.append(ch)
    return "".join(result)


def _parse_repair_batch(raw: str) -> dict[str, str]:
    """Parse repair response. Returns {test_id: ts_code}."""
    sanitised = _sanitise_json(raw)
    try:
        items = json.loads(sanitised)
        if not isinstance(items, list):
            return {}
        return {
            item["test_id"]: item["ts_code"]
            for item in items
            if isinstance(item, dict) and item.get("test_id") and item.get("ts_code")
        }
    except json.JSONDecodeError as e:
        log.warning(f"Repair: JSON parse failed: {e}")
        log.debug(f"Repair: raw (first 500): {raw[:500]}")
        return {}


def _build_repair_context(
    tests: list[TestCase],
    real_selectors: list[str],
    domain_profile: DomainProfile,
) -> str:
    """
    Builds the user message for a repair batch.
    Includes: error messages, current code, real selectors, memory.
    """
    parts = []

    # Memory: repair strategies for the error types seen
    all_errors = " ".join(t.last_error or "" for t in tests)
    strategies = get_repair_strategies(all_errors, domain_profile.base_url, domain_profile.app_type)
    if strategies:
        strat_lines = "\n".join(f"- ERROR: {s['error']} → FIX: {s['fix']}" for s in strategies)
        parts.append(f"KNOWN REPAIR STRATEGIES:\n{strat_lines}")

    # Memory: confirmed selectors
    mem_sels = get_selectors(domain_profile.base_url, min_score=0.7)
    combined_sels = list(set(real_selectors + mem_sels))[:50]
    if combined_sels:
        parts.append(f"REAL SELECTORS FOR THIS APP:\n" + "\n".join(combined_sels))

    # Hallucination blocklist
    blocklist = get_hallucination_blocklist()
    if blocklist:
        parts.append(f"NEVER USE THESE (confirmed hallucinations):\n" + "\n".join(blocklist[:15]))

    # Failing tests with errors
    test_items = []
    for t in tests:
        item = {
            "test_id":            t.test_id,
            "req_id":             t.req_id,
            "failure_type":       t.failure_type or "unknown",
            "error":              t.last_error or "Unknown error",
            "ts_code":            t.ts_code,
            "hallucinated_selectors": t.hallucinated,
        }
        if t.dom_snapshot:
            item["dom_snapshot"] = t.dom_snapshot[:2000]  # Cap to avoid token bloat
        test_items.append(item)
    parts.append(f"TESTS TO REPAIR:\n{json.dumps(test_items, indent=2)}")

    return "\n\n".join(parts)


def repair_batch(
    failing_tests: list[TestCase],
    suite: TestSuite,
    selector_map: PageSelectorMap,
    domain_profile: DomainProfile,
    run_id: str,
    batch_idx: int = 1,
) -> int:
    """
    Repair a batch of failing tests in-place on the suite.
    Returns count of successfully repaired tests.
    """
    if not failing_tests:
        return 0

    # Split into sub-batches of REPAIR_BATCH_SIZE
    repaired_total = 0
    batches = [
        failing_tests[i:i + REPAIR_BATCH_SIZE]
        for i in range(0, len(failing_tests), REPAIR_BATCH_SIZE)
    ]

    system = _get_repair_system()
    test_map = {t.test_id: t for t in suite.tests}

    for sub_idx, batch in enumerate(batches):
        real_sels = selector_map.all_selectors(min_score=0.5)
        user_content = _build_repair_context(batch, real_sels, domain_profile)

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ]

        raw = ""
        try:
            raw = complete(
                tier=Tier.CODEGEN,
                messages=messages,
                max_tokens=4096,
                label=f"repair_b{batch_idx}.{sub_idx+1}",
            )
            repaired_map = _parse_repair_batch(raw)
        except Exception as e:
            log.error(f"Repair: batch {batch_idx}.{sub_idx+1} LLM call failed: {e}")
            continue

        for test_id, new_code in repaired_map.items():
            if test_id in test_map:
                original = test_map[test_id]
                original.ts_code = new_code
                original.repair_count += 1
                original.hallucinated = []   # cleared — re-checked by evaluator
                repaired_total += 1
                log.debug(f"Repair: repaired {test_id} (repair #{original.repair_count})")

        log.info(
            f"Repair: batch {batch_idx}.{sub_idx+1} → "
            f"{len(repaired_map)}/{len(batch)} tests repaired"
        )

    # ── Telemetry ─────────────────────────────────────────────────────────────
    try:
        from app.core.telemetry import emit as _emit
        total_attempted = len(failing_tests)
        failure_types = {}
        for t in failing_tests:
            ft = t.failure_type or "unknown"
            failure_types[ft] = failure_types.get(ft, 0) + 1
        _emit(run_id=run_id, agent="agent_c", event="repair_complete", loop=batch_idx, metrics={
            "tests_attempted":    total_attempted,
            "tests_repaired":     repaired_total,
            "repair_success_rate": round(repaired_total / total_attempted, 3) if total_attempted else 0,
            "failure_types":      failure_types,
            "sub_batches":        len(batches),
        })
    except Exception:
        pass

    return repaired_total


def on_demand_crawl_and_repair(
    hallucinated_tests: list[TestCase],
    suite: TestSuite,
    selector_map: PageSelectorMap,
    auth_ctx,
    domain_profile: DomainProfile,
    run_id: str,
) -> int:
    """
    For tests with confirmed hallucinations:
    1. Infer which page the test targets from requirement context
    2. Playwright-crawl that specific page to get real selectors
    3. Repair using confirmed real selectors
    Saves confirmed selectors to memory.
    Adds confirmed hallucinations to blocklist.
    Returns count of tests sent for repair.
    """
    from app.core.route_crawler import crawl_single_page
    from app.memory.agent_memory import save_selector

    if not hallucinated_tests:
        return 0

    log.info(f"Repair: on-demand crawl for {len(hallucinated_tests)} hallucinated tests")

    # Group by likely page (inferred from test title/code)
    page_groups: dict[str, list[TestCase]] = {}
    for test in hallucinated_tests:
        page = _infer_page(test, domain_profile)
        page_groups.setdefault(page, []).append(test)

    new_entries: list[SelectorEntry] = []

    for page_path, tests in page_groups.items():
        url = domain_profile.base_url.rstrip("/") + page_path
        log.info(f"Repair: crawling {url} for real selectors")

        page_selectors = crawl_single_page(url, auth_ctx, domain_profile.base_url)

        if page_selectors:
            # Update selector map with fresh selectors
            selector_map.pages[page_path] = page_selectors
            new_entries.extend(page_selectors)

            # Persist to memory
            for entry in page_selectors:
                if entry.score >= 0.6:
                    save_selector(
                        domain_profile.base_url, page_path,
                        entry.selector, entry.score,
                    )

            # Add confirmed hallucinations to blocklist
            all_page_sels = {e.selector for e in page_selectors}
            for test in tests:
                for hall_sel in test.hallucinated:
                    if hall_sel not in all_page_sels:
                        # Still not found even after crawl — confirmed hallucination
                        add_hallucination(hall_sel, domain_profile.base_url)
                        log.debug(f"Repair: confirmed hallucination: {hall_sel}")

    if new_entries:
        log.info(f"Repair: on-demand crawl found {len(new_entries)} new selectors")

    # Now repair using the updated selector map
    return repair_batch(
        failing_tests=hallucinated_tests,
        suite=suite,
        selector_map=selector_map,
        domain_profile=domain_profile,
        run_id=run_id,
        batch_idx=99,   # Special batch ID for on-demand
    )


def _infer_page(test: TestCase, profile: DomainProfile) -> str:
    """
    Infer the most likely page path for a test from its title and code.
    Checks against domain profile's likely_routes.
    Falls back to feature_area → route mapping.
    """
    text = (test.title + " " + test.ts_code[:500]).lower()

    FEATURE_ROUTE_MAP = {
        "auth":     "/login",
        "login":    "/login",
        "cart":     "/cart",
        "checkout": "/checkout",
        "search":   "/search",
        "product":  "/products",
        "profile":  "/profile",
        "dashboard": "/dashboard",
        "account":  "/account",
        "register": "/register",
        "signup":   "/signup",
    }

    # Check page.goto() calls in test code
    goto_match = re.search(r"page\.goto\(['\"]([^'\"]+)['\"]\)", test.ts_code)
    if goto_match:
        path = goto_match.group(1)
        if path.startswith("/"):
            return path
        # Relative path
        from urllib.parse import urlparse
        return urlparse(path).path or "/"

    # Match keywords against likely_routes
    for route in profile.likely_routes:
        route_lower = route.lower()
        for kw in route_lower.split("/"):
            if kw and kw in text:
                return route

    # Keyword → route mapping
    for kw, route in FEATURE_ROUTE_MAP.items():
        if kw in text:
            return route

    return "/"
