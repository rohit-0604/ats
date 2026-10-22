"""
ATS v8 — Post-Run Learner
After every pipeline run, extracts actionable lessons from:
  - Human feedback (approved/rejected items + notes)
  - Repair outcomes (what error → what fix worked)
  - Hallucination patterns (which selectors were invented)
  - Coverage delta (which requirement types generate failing tests)
Persists lessons to ChromaDB memory for future runs on same domain.
"""

from __future__ import annotations
import logging
import re
import time
from typing import Optional

from app.config import Confidence
from app.schemas import (
    DomainProfile, TestSuite, EvaluationReport,
    FeedbackResult, TestCase,
)
from app.memory.agent_memory import (
    add_lesson, add_repair_strategy, add_hallucination, bump_lesson_confidence,
    save_run_metrics, get_lessons, prune_stale_lessons,
)

log = logging.getLogger(__name__)


# ─── Lesson extraction helpers ────────────────────────────────────────────────

def _learn_from_phase1_feedback(
    feedback: FeedbackResult,
    domain_profile: DomainProfile,
) -> int:
    """Extract lessons from requirement approval/rejection patterns."""
    added = 0
    rejected_ids = feedback.rejected_ids()
    approved_ids  = feedback.approved_ids()

    # Per-item notes → lessons
    for item in feedback.items:
        if item.memory_note:
            add_lesson(
                text=item.memory_note,
                scope="domain",
                base_url=domain_profile.base_url,
                app_type=domain_profile.app_type,
                confidence=Confidence.HUMAN_TYPED,     # 1.00
                tags=["human_note", "phase1", item.item_id],
            )
            added += 1

        # If a requirement was rejected with a prompt, the prompt is the lesson
        if item.item_id in rejected_ids and item.run_prompt:
            add_lesson(
                text=f"Requirement type rejected: {item.run_prompt}",
                scope="domain",
                base_url=domain_profile.base_url,
                app_type=domain_profile.app_type,
                confidence=Confidence.HUMAN_TYPED,
                tags=["rejected_requirement", "phase1"],
            )
            added += 1

    # Global prompt → high-priority lesson
    if feedback.global_prompt:
        add_lesson(
            text=f"Global run instruction: {feedback.global_prompt}",
            scope="domain",
            base_url=domain_profile.base_url,
            app_type=domain_profile.app_type,
            confidence=Confidence.INJECTION_MIN,       # 0.90
            tags=["global_prompt", "phase1"],
        )
        added += 1

    # Category prompts → scoped lessons
    for category, prompt in (feedback.category_prompts or {}).items():
        add_lesson(
            text=f"Category '{category}' instruction: {prompt}",
            scope="app_type",
            base_url=domain_profile.base_url,
            app_type=domain_profile.app_type,
            confidence=Confidence.INJECTION_MIN,
            tags=["category_prompt", category],
        )
        added += 1

    log.info(f"Learner: +{added} lessons from Phase 1 feedback")
    return added


def _learn_from_phase2_feedback(
    feedback: FeedbackResult,
    suite: TestSuite,
    domain_profile: DomainProfile,
) -> int:
    """Extract lessons from test code approval/rejection."""
    added = 0
    test_map = {t.test_id: t for t in suite.tests}
    rejected_ids = feedback.rejected_ids()

    for item in feedback.items:
        test = test_map.get(item.item_id)
        if not test:
            continue

        # Rejected test + repair instruction → repair strategy lesson
        if item.item_id in rejected_ids and item.run_prompt:
            add_lesson(
                text=f"Test rejected: {item.run_prompt}",
                scope="domain",
                base_url=domain_profile.base_url,
                app_type=domain_profile.app_type,
                confidence=Confidence.HUMAN_TYPED,
                tags=["rejected_test", "phase2", test.req_id],
            )
            added += 1

        if item.memory_note:
            add_lesson(
                text=item.memory_note,
                scope="domain",
                base_url=domain_profile.base_url,
                app_type=domain_profile.app_type,
                confidence=Confidence.HUMAN_TYPED,
                tags=["human_note", "phase2"],
            )
            added += 1

    log.info(f"Learner: +{added} lessons from Phase 2 feedback")
    return added


def _learn_from_repairs(
    suite: TestSuite,
    eval_report: EvaluationReport,
    domain_profile: DomainProfile,
) -> int:
    """
    For tests that were repaired and eventually passed:
    extract (error pattern → fix pattern) as repair strategies.
    """
    added = 0
    passing_ids = {r.test_id for r in eval_report.test_results if r.passed}

    for test in suite.tests:
        if test.repair_count == 0:
            continue
        if test.test_id not in passing_ids:
            continue   # Only learn from repairs that worked

        # Try to extract the error type from the test's last_error history
        if not test.last_error:
            continue

        error_type = _classify_error(test.last_error)

        # Summarise what changed (before/after not stored, so note the pattern)
        fix_hint = _extract_fix_hint(test)

        if error_type and fix_hint:
            add_repair_strategy(
                error_pattern=error_type,
                fix_description=fix_hint,
                scope="domain",
                base_url=domain_profile.base_url,
                app_type=domain_profile.app_type,
                confidence=Confidence.REPAIR_STRATEGY,
            )
            added += 1

    log.info(f"Learner: +{added} repair strategies from successful repairs")
    return added


def _learn_from_hallucinations(
    suite: TestSuite,
    eval_report: EvaluationReport,
    domain_profile: DomainProfile,
) -> int:
    """Persist all confirmed hallucinations to blocklist."""
    added = 0
    confirmed = set(eval_report.hallucinated_selectors)
    for sel in confirmed:
        add_hallucination(sel, domain_profile.base_url)
        added += 1
    if added:
        log.info(f"Learner: +{added} hallucinated selectors added to blocklist")
    return added


def _learn_from_coverage_patterns(
    eval_report: EvaluationReport,
    domain_profile: DomainProfile,
) -> int:
    """
    Identify requirement types / feature areas that consistently fail.
    Add a lesson to pre-warn codegen about these.
    """
    added = 0
    failing = [r for r in eval_report.test_results if not r.passed]
    if len(failing) >= 3:
        # Find common error patterns
        errors = [r.error or "" for r in failing if r.error]
        common_error = _most_common_error_type(errors)
        if common_error:
            add_lesson(
                text=(
                    f"Tests for {domain_profile.app_type} frequently fail with: {common_error}. "
                    f"Consider adding explicit waitForLoadState or increasing timeouts."
                ),
                scope="app_type",
                base_url=domain_profile.base_url,
                app_type=domain_profile.app_type,
                confidence=Confidence.AUTO_NEW,          # 0.55
                tags=["coverage_pattern", "auto_learned"],
            )
            added += 1

    return added


def _bump_confirmed_lessons(domain_profile: DomainProfile) -> None:
    """
    Bump confidence of existing lessons for this domain that were relevant
    in a run that achieved good coverage (≥ target).
    """
    lessons = get_lessons(
        query="playwright test generation",
        base_url=domain_profile.base_url,
        app_type=domain_profile.app_type,
        n_results=20,
    )
    for lesson in lessons:
        if lesson.get("confidence", 0) < 0.90 and lesson.get("id"):
            bump_lesson_confidence(lesson["id"], delta=0.05)


# ─── Error classification helpers ─────────────────────────────────────────────

_ERROR_PATTERNS = [
    (r"element.*not found|no element",          "selector_not_found"),
    (r"timeout.*exceeded|waiting.*timed",        "timeout"),
    (r"navigation.*failed|net::ERR",             "navigation_failed"),
    (r"locator.*strict mode",                    "multiple_elements_matched"),
    (r"expect.*toBeVisible.*received.*false",    "element_not_visible"),
    (r"SyntaxError|TypeError|ReferenceError",    "typescript_error"),
    (r"page.*closed|Target.*closed",             "page_closed"),
]

def _classify_error(error: str) -> Optional[str]:
    error_lower = error.lower()
    for pattern, label in _ERROR_PATTERNS:
        if re.search(pattern, error_lower):
            return label
    return "unknown_error"


def _extract_fix_hint(test: TestCase) -> Optional[str]:
    """Infer what fix was likely applied from the repaired test code."""
    code = test.ts_code
    hints = []
    if "waitForLoadState" in code:
        hints.append("added waitForLoadState")
    if "getByRole" in code or "getByText" in code:
        hints.append("replaced with Playwright role/text selector")
    if "waitForSelector" in code:
        hints.append("added explicit waitForSelector")
    if "timeout:" in code:
        hints.append("increased timeout")
    return "; ".join(hints) if hints else "repaired selector usage"


def _most_common_error_type(errors: list[str]) -> Optional[str]:
    counts: dict[str, int] = {}
    for e in errors:
        label = _classify_error(e) or "unknown"
        counts[label] = counts.get(label, 0) + 1
    if not counts:
        return None
    top = max(counts, key=counts.__getitem__)
    return top if counts[top] >= 2 else None


# ─── Run metrics ──────────────────────────────────────────────────────────────

def _save_metrics(
    eval_report: Optional[EvaluationReport],
    domain_profile: DomainProfile,
    run_id: str,
    lesson_count: int,
) -> None:
    metrics = {
        "run_id":          run_id,
        "base_url":        domain_profile.base_url,
        "app_type":        domain_profile.app_type,
        "coverage_pct":    eval_report.coverage_pct   if eval_report else 0,
        "exec_pct":        eval_report.exec_pct       if eval_report else 0,
        "total_tests":     eval_report.total_tests    if eval_report else 0,
        "passed_tests":    eval_report.passed_tests   if eval_report else 0,
        "hallucinations":  eval_report.hallucination_count if eval_report else 0,
        "loop_count":      len(eval_report.loop_history) if eval_report else 0,
        "lessons_added":   lesson_count,
        "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_run_metrics(run_id,metrics)


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_learner(
    feedback_list: list[FeedbackResult],
    domain_profile: DomainProfile,
    suite: TestSuite,
    eval_report: Optional[EvaluationReport],
    run_id: str,
) -> int:
    """
    Run all learning extractors. Returns total lessons added.
    Called once at the end of every pipeline run.
    """
    log.info(f"Learner: starting post-run learning for run_id={run_id}")
    total = 0

    phase_map = {fb.phase: fb for fb in feedback_list if fb}

    if "phase1" in phase_map:
        total += _learn_from_phase1_feedback(phase_map["phase1"], domain_profile)

    if "phase2" in phase_map:
        total += _learn_from_phase2_feedback(phase_map["phase2"], suite, domain_profile)

    if eval_report:
        total += _learn_from_repairs(suite, eval_report, domain_profile)
        total += _learn_from_hallucinations(suite, eval_report, domain_profile)
        total += _learn_from_coverage_patterns(eval_report, domain_profile)

        # Bump existing lessons if the run was successful
        if eval_report.targets_met:
            _bump_confirmed_lessons(domain_profile)
            log.info("Learner: bumped lesson confidence (targets met)")

    # Prune stale/excess lessons to prevent unbounded memory growth
    pruned = prune_stale_lessons(f"domain:{domain_profile.base_url}")
    pruned += prune_stale_lessons(f"app_type:{domain_profile.app_type}")
    if pruned:
        log.info(f"Learner: pruned {pruned} stale lessons")

    _save_metrics(eval_report, domain_profile, run_id, total)
    log.info(f"Learner: complete — {total} total lessons added this run")

    # ── Telemetry ─────────────────────────────────────────────────────────────
    try:
        from app.core.telemetry import emit as _emit
        loops = eval_report.loop_history if eval_report else []
        # Compute improvement slope: did coverage improve loop over loop?
        cov_values = [l.coverage_pct for l in loops]
        improving  = (cov_values[-1] > cov_values[0]) if len(cov_values) >= 2 else None

        _emit(run_id=run_id, agent="learner", event="learning_complete", metrics={
            "lessons_added":        total,
            "lessons_from_repairs": len([t for t in (suite.tests if suite else []) if t.repair_count > 0 and (eval_report and any(r.test_id == t.test_id and r.passed for r in eval_report.test_results))]),
            "hallucinations_added_to_blocklist": eval_report.hallucination_count if eval_report else 0,
            "targets_met":          eval_report.targets_met if eval_report else False,
            "pruned_stale":         pruned,
        })
        _emit(run_id=run_id, agent="agent_c", event="run_summary", metrics={
            "loops_to_converge":    len(loops),
            "coverage_improving":   improving,
            "exit_reason":          eval_report.exit_reason if eval_report else "unknown",
            "final_coverage_pct":   eval_report.coverage_pct if eval_report else 0,
            "final_exec_pct":       eval_report.exec_pct if eval_report else 0,
        })
    except Exception:
        pass

    return total
