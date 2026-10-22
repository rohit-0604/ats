"""
ATS v8 — Evaluator Engine
Writes .spec.ts files, runs Playwright, parses JSON results,
detects hallucinations against the selector map.
Windows-safe: resolves npx.cmd, uses UTF-8 encoding.
"""

from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from app.config import ROOT, OUTPUT_DIR
from app.schemas import (
    TestSuite, TestCase, PageSelectorMap,
    EvaluationReport, TestResult, LoopRecord,
)

log = logging.getLogger(__name__)

PLAYWRIGHT_DIR  = ROOT / "playwright_project"
TESTS_DIR       = PLAYWRIGHT_DIR / "tests"
REPORTS_DIR     = PLAYWRIGHT_DIR / "playwright-report"


# ─── npx resolution (Windows nvm4w compatibility) ────────────────────────────

def _resolve_npx() -> str:
    """
    Resolves npx executable path.
    Windows with nvm4w installs npx as npx.cmd, not npx.
    Falls back through: npx.cmd → npx → full path search.
    """
    # Check PATH for npx.cmd first (Windows nvm4w)
    for candidate in ["npx.cmd", "npx"]:
        found = shutil.which(candidate)
        if found:
            return found

    # Common nvm4w install path
    nvm4w_path = Path(r"C:\nvm4w\nodejs\npx.cmd")
    if nvm4w_path.exists():
        return str(nvm4w_path)

    # macOS/Linux nvm
    nvm_path = Path.home() / ".nvm" / "versions" / "node"
    if nvm_path.exists():
        for version_dir in sorted(nvm_path.iterdir(), reverse=True):
            npx = version_dir / "bin" / "npx"
            if npx.exists():
                return str(npx)

    raise RuntimeError(
        "npx not found. Install Node.js and ensure it's on PATH. "
        "If using nvm4w: run 'nvm use <version>' to activate Node."
    )


# ─── Write spec files ─────────────────────────────────────────────────────────

def write_spec_files(suite: TestSuite) -> dict[str, Path]:
    """
    Groups tests by spec_file and writes them to playwright_project/tests/.
    Returns {spec_filename: path}.
    """
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # Clear existing generated tests (keep any manual ones)
    for f in TESTS_DIR.glob("*.spec.ts"):
        f.unlink()

    files: dict[str, list[TestCase]] = {}
    for test in suite.tests:
        files.setdefault(test.spec_file, []).append(test)

    # Regex to strip the playwright import line from individual test blocks
    _import_re = re.compile(
        r"^\s*import\s*\{[^}]*\}\s*from\s*['\"]@playwright/test['\"]\s*;?\s*\n?",
        re.MULTILINE,
    )

    written: dict[str, Path] = {}
    for spec_name, tests in files.items():
        path = TESTS_DIR / spec_name
        # Deduplicate import: strip from all blocks, then prepend once
        stripped = [_import_re.sub("", t.ts_code).strip() for t in tests]
        content = "import { test, expect } from '@playwright/test';\n\n" + "\n\n".join(stripped)
        # networkidle never resolves on external sites — replace globally
        content = content.replace("waitForLoadState('networkidle')", "waitForLoadState('domcontentloaded')")
        path.write_text(content, encoding="utf-8")
        written[spec_name] = path
        log.debug(f"Evaluator: wrote {len(tests)} tests to {spec_name}")

    log.info(f"Evaluator: wrote {len(written)} spec files ({sum(len(v) for v in files.values())} tests total)")
    return written


# ─── Run Playwright ───────────────────────────────────────────────────────────

def run_playwright(run_id: str, timeout_s: int = 300, base_url: str = "") -> dict:
    """
    Runs Playwright test suite and returns parsed JSON reporter output.
    Handles Windows encoding issues (cp1252 → UTF-8).
    Returns raw results dict (empty dict on failure).
    """
    npx = _resolve_npx()
    report_path = OUTPUT_DIR / f"pw_results_{run_id}.json"

    # Remove stale results file if present
    if report_path.exists():
        try:
            os.chmod(str(report_path), 0o666)
            report_path.unlink()
        except Exception:
            pass

    cmd = [
        npx, "playwright", "test",
        "--reporter=json",
    ]
    env = {
        **os.environ,
        "PLAYWRIGHT_JSON_OUTPUT_NAME": str(report_path),
        "ATS_BASE_URL": base_url,
    }

    log.info(f"Evaluator: running Playwright ({' '.join(str(c) for c in cmd[:3])} ...)")
    t0 = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PLAYWRIGHT_DIR),
            capture_output=True,
            encoding="utf-8",
            errors="replace",       # Windows cp1252 safety
            timeout=timeout_s,
            env=env,
        )
        elapsed = round(time.time() - t0, 1)
        log.info(f"Evaluator: Playwright finished in {elapsed}s (exit={result.returncode})")

        if result.stderr:
            log.info(f"Playwright stderr: {result.stderr[:1000]}")

    except subprocess.TimeoutExpired:
        log.error(f"Evaluator: Playwright timed out after {timeout_s}s")
        return {}
    except Exception as e:
        log.error(f"Evaluator: Playwright subprocess failed: {e}")
        return {}

    # Parse JSON output
    return _parse_playwright_json(report_path, result.stdout)


def _parse_playwright_json(report_path: Path, stdout: Optional[str]) -> dict:
    """Parse Playwright JSON reporter output from file or stdout."""
    # Try file first (--output flag)
    if report_path.exists():
        try:
            return json.loads(report_path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            log.warning(f"Evaluator: failed to parse {report_path}: {e}")

    # Fallback: extract JSON from stdout
    if stdout:
        # JSON reporter outputs to stdout when no output file
        try:
            start = stdout.find("{")
            if start >= 0:
                return json.loads(stdout[start:])
        except Exception:
            pass

    log.warning("Evaluator: no parseable Playwright output found")
    return {}


# ─── Failure type classification ─────────────────────────────────────────────

def _classify_failure(error_msg: str) -> tuple[str, Optional[str]]:
    """
    Classify a Playwright error message into a structured failure type.
    Returns (failure_type, failed_selector).

    Types:
      strict_mode       — selector matched multiple elements
      selector_not_found — element not found / 0 elements
      assertion_failure — expect() value mismatch
      timeout           — waitForLoadState / action timeout
      network_error     — navigation / fetch error
      unknown           — anything else
    """
    if not error_msg:
        return "unknown", None

    msg = error_msg.lower()

    # Extract selector from common patterns
    failed_selector: Optional[str] = None
    import re as _re
    sel_match = _re.search(r"locator\((['\"])(.+?)\1\)", error_msg)
    if sel_match:
        failed_selector = sel_match.group(2)

    if "strict mode violation" in msg:
        return "strict_mode", failed_selector
    if any(p in msg for p in ["element(s) not found", "no node found", "0 elements", "element not found"]):
        return "selector_not_found", failed_selector
    if any(p in msg for p in ["timeout", "time out", "exceeded"]):
        return "timeout", failed_selector
    if any(p in msg for p in ["net::err", "navigation failed", "err_name_not_resolved", "connection refused"]):
        return "network_error", failed_selector
    if any(p in msg for p in ["expect(", "tobevisible", "tohavetext", "tocontaintext", "tobe(", "expected", "received"]):
        return "assertion_failure", failed_selector

    return "unknown", failed_selector


def _load_dom_snapshot(test_title: str) -> Optional[str]:
    """
    Load the error-context.md DOM snapshot for a failing test from test-results/.
    Matches folder by test title slug. Returns first 3000 chars of YAML snapshot.
    """
    import re as _re
    # Playwright slugifies test titles for folder names
    slug = _re.sub(r"[^a-zA-Z0-9]+", "-", test_title).strip("-")[:50]
    results_dir = PLAYWRIGHT_DIR / "test-results"
    if not results_dir.exists():
        return None

    # Find matching folder (partial slug match)
    for folder in results_dir.iterdir():
        if not folder.is_dir():
            continue
        if slug[:20].lower() in folder.name.lower():
            ctx_file = folder / "error-context.md"
            if ctx_file.exists():
                try:
                    content = ctx_file.read_text(encoding="utf-8", errors="replace")
                    # Strip the markdown header, return just the YAML block
                    yaml_start = content.find("```yaml")
                    if yaml_start >= 0:
                        content = content[yaml_start + 7:]
                    return content[:3000]
                except Exception:
                    pass
    return None


# ─── Parse results ────────────────────────────────────────────────────────────

def parse_results(
    pw_output: dict,
    suite: TestSuite,
) -> tuple[list[TestResult], int, int]:
    """
    Converts Playwright JSON output to TestResult list.
    Classifies each failure type and loads DOM snapshot from error-context.md.
    Returns (test_results, passed_count, failed_count).
    """
    if not pw_output:
        # All tests failed if no output
        results = [
            TestResult(
                test_id=t.test_id,
                req_id=t.req_id,
                spec_file=t.spec_file,
                passed=False,
                error="No Playwright output — possible compilation or startup error",
                failure_type="unknown",
            )
            for t in suite.tests
        ]
        return results, 0, len(results)

    results: list[TestResult] = []
    passed = 0
    failed = 0

    # Playwright JSON format: {"suites": [{"specs": [{"tests": [{"results": [...]}]}]}]}
    for suite_block in pw_output.get("suites", []):
        for spec in suite_block.get("specs", []):
            title = spec.get("title", "")
            test_entries = spec.get("tests", [])

            # Match to our TestCase by title
            matched_test = _find_test_by_title(title, suite)

            for entry in test_entries:
                test_results = entry.get("results", [])
                # Last result = final attempt
                last = test_results[-1] if test_results else {}
                status = last.get("status", "failed")
                ok = status in ("passed", "expected")
                error = None
                failure_type = None
                failed_selector = None
                dom_snapshot = None

                if not ok:
                    error_steps = last.get("errors", [])
                    if error_steps:
                        error = str(error_steps[0].get("message", ""))[:500]
                    failure_type, failed_selector = _classify_failure(error or "")
                    # Load the DOM snapshot from error-context.md
                    dom_snapshot = _load_dom_snapshot(title)

                tr = TestResult(
                    test_id=matched_test.test_id if matched_test else f"UNKNOWN-{title[:20]}",
                    req_id=matched_test.req_id if matched_test else "UNKNOWN",
                    spec_file=spec.get("file", "unknown.spec.ts"),
                    passed=ok,
                    error=error,
                    duration_ms=last.get("duration"),
                    failure_type=failure_type,
                    dom_snapshot=dom_snapshot,
                    failed_selector=failed_selector,
                )
                results.append(tr)

                if matched_test:
                    matched_test.last_error = error
                    matched_test.failure_type = failure_type
                    matched_test.dom_snapshot = dom_snapshot

                if ok:
                    passed += 1
                else:
                    failed += 1
                    log.debug(f"Evaluator: FAIL [{failure_type}] '{title}' — {(error or '')[:80]}")

    log.info(f"Evaluator: {passed} passed, {failed} failed out of {passed+failed} tests")
    return results, passed, failed


def _find_test_by_title(title: str, suite: TestSuite) -> Optional[TestCase]:
    for t in suite.tests:
        if t.title == title or title in t.ts_code:
            return t
    return None


# ─── Hallucination detection ──────────────────────────────────────────────────

def detect_hallucinations(
    suite: TestSuite,
    selector_map: PageSelectorMap,
) -> list[str]:
    """
    Finds selectors in test code that don't exist in the crawled selector map.
    Returns list of hallucinated selector strings.
    """
    known = set(selector_map.all_selectors(min_score=0.0))
    hallucinations: set[str] = set()

    # Patterns that extract selector strings from TypeScript code
    patterns = [
        r"page\.locator\(['\"]([^'\"]+)['\"]\)",
        r"page\.click\(['\"]([^'\"]+)['\"]\)",
        r"page\.fill\(['\"]([^'\"]+)['\"],",
        r"page\.waitForSelector\(['\"]([^'\"]+)['\"]\)",
        r"\$\(['\"]([^'\"]+)['\"]\)",
    ]

    for test in suite.tests:
        code = test.ts_code
        found_sels: set[str] = set()

        for pattern in patterns:
            for match in re.finditer(pattern, code):
                sel = match.group(1)
                # Skip Playwright built-in roles/text selectors
                if sel.startswith(("text=", "role=", "label=", "**/", "**")):
                    continue
                found_sels.add(sel)

        test_halls = found_sels - known
        test.hallucinated = list(test_halls)
        hallucinations.update(test_halls)

    hall_list = sorted(hallucinations)
    if hall_list:
        log.warning(f"Evaluator: {len(hall_list)} hallucinated selectors detected")
        for h in hall_list[:5]:
            log.debug(f"  Hallucination: {h}")

    return hall_list


# ─── Build evaluation report ──────────────────────────────────────────────────

def build_report(
    run_id: str,
    suite: TestSuite,
    bundle_req_count: int,
    approved_req_count: int,
    test_results: list[TestResult],
    passed: int,
    failed: int,
    hallucinated: list[str],
    loop_history: list[LoopRecord],
    start_time: float,
    exit_reason: str = "unknown",
) -> EvaluationReport:
    """Assemble final EvaluationReport from all collected data."""
    total_tests = passed + failed

    # Coverage: how many approved requirements have at least one passing test
    passing_req_ids = {r.req_id for r in test_results if r.passed}
    all_req_ids_in_suite = {r.req_id for r in test_results}
    coverage_pct = (
        len(passing_req_ids) / approved_req_count * 100
        if approved_req_count > 0 else 0.0
    )
    exec_pct = (
        passed / total_tests * 100
        if total_tests > 0 else 0.0
    )

    return EvaluationReport(
        run_id=run_id,
        total_requirements=bundle_req_count,
        approved_requirements=approved_req_count,
        total_tests=total_tests,
        passed_tests=passed,
        failed_tests=failed,
        coverage_pct=round(coverage_pct, 1),
        exec_pct=round(exec_pct, 1),
        hallucination_count=len(hallucinated),
        hallucinated_selectors=hallucinated,
        loop_history=loop_history,
        test_results=test_results,
        exit_reason=exit_reason,
        total_duration_s=round(time.time() - start_time, 1),
    )


# ─── Main entry point ─────────────────────────────────────────────────────────

def evaluate(
    suite: TestSuite,
    selector_map: PageSelectorMap,
    bundle_req_count: int,
    approved_req_count: int,
    run_id: str,
    loop_number: int,
    loop_history: list[LoopRecord],
    start_time: float,
    base_url: str = "",
) -> EvaluationReport:
    """
    Write spec files → run Playwright → parse results → detect hallucinations.
    Returns a full EvaluationReport.
    """
    write_spec_files(suite)

    # Scale timeout with test count: 30s per test + 60s overhead, min 300s
    n_tests = len(suite.tests)
    timeout_s = max(300, n_tests * 30 + 60)
    pw_output = run_playwright(run_id, timeout_s=timeout_s, base_url=base_url)
    test_results, passed, failed = parse_results(pw_output, suite)
    hallucinated = detect_hallucinations(suite, selector_map)

    total = passed + failed
    coverage = (len({r.req_id for r in test_results if r.passed}) / approved_req_count * 100
                if approved_req_count > 0 else 0.0)
    exec_pct = passed / total * 100 if total > 0 else 0.0

    # Build failure distribution for this loop
    failure_dist: dict[str, int] = {}
    for r in test_results:
        if not r.passed:
            ft = r.failure_type or "unknown"
            failure_dist[ft] = failure_dist.get(ft, 0) + 1

    # Append current loop record
    loop_record = LoopRecord(
        loop_number=loop_number,
        coverage_pct=round(coverage, 1),
        exec_pct=round(exec_pct, 1),
        hallucinations=len(hallucinated),
        action_taken="run_tests",
        failure_distribution=failure_dist,
    )
    updated_history = list(loop_history) + [loop_record]

    return build_report(
        run_id=run_id,
        suite=suite,
        bundle_req_count=bundle_req_count,
        approved_req_count=approved_req_count,
        test_results=test_results,
        passed=passed,
        failed=failed,
        hallucinated=hallucinated,
        loop_history=updated_history,
        start_time=start_time,
    )
