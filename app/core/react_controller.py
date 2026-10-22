"""
ATS v8 — LangGraph ReAct Controller
Dynamic pipeline orchestration with SqliteSaver checkpoint/resume.

Architecture:
- One central planner node (llama-3.3-70b) decides every transition
- Fixed sequential edges: infer→auth→crawl, post_run_learn→quality_monitor→END
- All other routing is conditional — planner decides at runtime
- AgentState is the single source of truth shared across all nodes
"""

from __future__ import annotations
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, Literal, Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from app.config import (
    CACHE_DIR, OUTPUT_DIR, TARGET_COVERAGE, TARGET_EXEC, MAX_LOOPS,
)
from app.llm.router import Tier, complete
from app.schemas import (
    DomainProfile, AuthContext, PageSelectorMap,
    RequirementBundle, TestSuite, EvaluationReport,
    FeedbackResult, LoopRecord,
)

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# AgentState — single TypedDict shared across all LangGraph nodes
# ══════════════════════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    run_id:         str
    run_mode:       str   # full | extract | codegen | eval | crawl
    base_url:       str
    pdf_path:       Optional[str]
    requirements_path: Optional[str]   # --requirements override

    domain_profile:     Optional[dict]   # DomainProfile.model_dump()
    auth_context:       Optional[dict]   # AuthContext.model_dump()
    selector_map:       Optional[dict]   # PageSelectorMap.model_dump()
    requirement_bundle: Optional[dict]   # RequirementBundle.model_dump()
    test_suite:         Optional[dict]   # TestSuite.model_dump()
    eval_report:        Optional[dict]   # EvaluationReport.model_dump()

    feedback_phase1:    Optional[dict]
    feedback_phase2:    Optional[dict]
    feedback_phase3:    Optional[dict]

    loop_count:         int
    coverage_history:   list[float]
    stall_count:        int
    generate_count:     int
    crawl_demand_count: int

    last_action:        Optional[str]
    planner_reasoning:  Optional[str]
    next_action:        Optional[str]

    # Flags
    force_extract:      bool
    force_crawl:        bool
    interactive:        bool
    auto_mode:          bool

    # Runtime resource config
    resource:           Optional[dict]


# ══════════════════════════════════════════════════════════════════════════════
# PLANNER NODE — llama-3.3-70b decides next action
# ══════════════════════════════════════════════════════════════════════════════

_PLANNER_SYSTEM = """You are the orchestration planner for an autonomous test generation pipeline.

Given the current pipeline state, decide the NEXT action.
Respond ONLY with a JSON object:
{
  "action": "<action_name>",
  "reasoning": "<2-3 sentence explanation>"
}

Available actions:
- "extract"       — Run Agent A requirement extraction (needs: pdf_path)
- "hitl_phase1"   — Pause for human review of requirements (interactive mode only)
- "generate"      — Run Agent B code generation (needs: approved requirements)
- "hitl_phase2"   — Pause for human review of generated tests
- "run_tests"     — Execute Playwright and evaluate
- "repair"        — Run targeted repair on failing tests
- "crawl_demand"  — On-demand crawl for hallucination repair
- "hitl_phase3"   — Pause for human review of results (interactive, phase3 only)
- "learn"         — Run post-run learner (final stage)
- "done"          — Pipeline complete

Decision rules:
- If no requirements: action = "extract"
- If requirements exist but no tests: action = "generate"
- If tests exist but not evaluated: action = "run_tests"
- If hallucinations > 0 AND crawl_demand_count < 2: action = "crawl_demand" (real selectors needed)
- If dominant_failure_type = "selector_not_found" AND hallucinations = 0: action = "crawl_demand" (selectors missing from map)
- If dominant_failure_type = "timeout": action = "repair" (fix waitForLoadState, no crawl needed)
- If dominant_failure_type = "assertion_failure": action = "repair" (fix expected values)
- If dominant_failure_type = "strict_mode": action = "repair" (scope locators)
- If dominant_failure_type = "network_error": action = "repair" (fix URLs)
- If coverage < target OR exec < target: action = "repair"
- If stall_count >= 2 (coverage delta < 2%): switch to full regeneration via "generate"
- If loop_count >= max_loops: action = "learn"
- If all targets met: action = "learn" then "done"
- Only suggest hitl_* if interactive=true"""

_PLANNER_MAX_LOOPS = MAX_LOOPS



def planner_node(state: AgentState) -> AgentState:
    """
    Central ReAct planner. Called after every significant pipeline action.
    Uses llama-3.3-70b to decide the next step.
    """
    eval_report = state.get("eval_report")
    loop_count  = state.get("loop_count", 0)

    # Fast-path: run_mode gates — stop early for partial modes
    run_mode = state.get("run_mode", "full")
    last = state.get("last_action")
    if run_mode == "extract" and last == "agent_a":
        return {**state, "next_action": "learn", "planner_reasoning": "extract-only mode — stopping after Agent A"}
    if run_mode == "codegen" and last == "agent_b":
        return {**state, "next_action": "learn", "planner_reasoning": "codegen-only mode — stopping after Agent B"}

    # Fast-path: check if targets already met
    if eval_report:
        report = EvaluationReport(**eval_report)
        if report.targets_met:
            log.info(f"Planner: targets met (coverage={report.coverage_pct}% exec={report.exec_pct}%)")
            return {**state, "next_action": "learn", "planner_reasoning": "All targets met."}

    if loop_count >= _PLANNER_MAX_LOOPS:
        log.warning(f"Planner: MAX_LOOPS={_PLANNER_MAX_LOOPS} reached")
        return {**state, "next_action": "learn",
                "planner_reasoning": f"Max loops ({_PLANNER_MAX_LOOPS}) reached."}

    # ── Forced shortcuts (must come AFTER the max-loops check above) ──────────
    generate_count = state.get("generate_count", 0)
    # Increment generate_count only immediately after agent_b (not for subsequent planner calls)
    # generate_count is reset to 0 by node_evaluator after each test run
    if last == "agent_b" and generate_count == 0:
        generate_count = 1
        state = {**state, "generate_count": generate_count}
    # If we've regenerated 2+ times without running tests, force run_tests
    if generate_count >= 2:
        log.warning(f"Planner: generate_count={generate_count} — forcing run_tests to break loop")
        return {**state, "next_action": "run_tests", "planner_reasoning": "Forced run_tests after repeated codegen without progress"}
    # After on_demand_crawl, always run tests next (unless max loops reached)
    if last == "on_demand_crawl":
        if loop_count >= _PLANNER_MAX_LOOPS:
            return {**state, "next_action": "learn", "planner_reasoning": f"Max loops ({_PLANNER_MAX_LOOPS}) reached after crawl."}
        log.info("Planner: post on_demand_crawl → forcing run_tests")
        return {**state, "next_action": "run_tests", "planner_reasoning": "Post crawl — must run tests to evaluate fixes"}
    # After repair, always run tests next (unless max loops reached)
    if last == "repair":
        if loop_count >= _PLANNER_MAX_LOOPS:
            return {**state, "next_action": "learn", "planner_reasoning": f"Max loops ({_PLANNER_MAX_LOOPS}) reached after repair."}
        log.info("Planner: post repair → forcing run_tests")
        return {**state, "next_action": "run_tests", "planner_reasoning": "Post repair — must run tests to evaluate fixes"}
    # If crawl_demand cap reached, force repair instead
    crawl_demand_count = state.get("crawl_demand_count", 0)
    if crawl_demand_count >= 2 and state.get("eval_report"):
        report = EvaluationReport(**state["eval_report"])
        if report.hallucination_count > 0:
            log.info("Planner: crawl_demand cap reached with hallucinations — forcing repair")
            return {**state, "next_action": "repair", "planner_reasoning": "Crawl demand cap reached — attempting repair"}
    # Build context for R1
    context = _build_planner_context(state)

    messages = [
        {"role": "system", "content": _PLANNER_SYSTEM},
        {"role": "user",   "content": context},
    ]

    try:
        raw = complete(
            tier=Tier.REASONING,
            messages=messages,
            max_tokens=2048,
            label=f"planner_loop{loop_count}",
        )
        raw = raw.strip()
        # Strip markdown fences
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(raw)
        action    = data.get("action", "done")
        reasoning = data.get("reasoning", "")
    except Exception as e:
        log.warning(f"Planner: LLM parse failed ({e}), using rule-based fallback")
        action, reasoning = _rule_based_decision(state)

    log.info(f"Planner: loop={loop_count} → action={action} | {reasoning[:80]}")

    # ── Telemetry ─────────────────────────────────────────────────────────────
    try:
        from app.core.telemetry import emit as _emit
        _eval = state.get("eval_report") or {}
        _emit(run_id=state.get("run_id",""), agent="planner", event="decision", loop=loop_count, metrics={
            "action":           action,
            "loop_count":       loop_count,
            "coverage_pct":     _eval.get("coverage_pct", 0),
            "exec_pct":         _eval.get("exec_pct", 0),
            "hallucinations":   _eval.get("hallucination_count", 0),
            "used_llm":         True,
        })
    except Exception:
        pass

    return {
        **state,
        "next_action":       action,
        "planner_reasoning": reasoning,
        "last_action":       state.get("last_action"),
    }


def _build_planner_context(state: AgentState) -> str:
    """Summarise pipeline state for the planner LLM."""
    parts = [
        f"run_id: {state.get('run_id')}",
        f"run_mode: {state.get('run_mode')}",
        f"loop_count: {state.get('loop_count', 0)} / {_PLANNER_MAX_LOOPS}",
        f"interactive: {state.get('interactive', False)}",
        f"last_action: {state.get('last_action', 'none')}",
        f"stall_count: {state.get('stall_count', 0)}",
        f"crawl_demand_count: {state.get('crawl_demand_count', 0)} / 2",
    ]

    if state.get("requirement_bundle"):
        bundle = RequirementBundle(**state["requirement_bundle"])
        parts.append(f"requirements: {len(bundle.requirements)} total, "
                     f"{len(bundle.approved_requirements())} approved")

    if state.get("test_suite"):
        suite = TestSuite(**state["test_suite"])
        parts.append(f"tests_generated: {len(suite.tests)}")

    if state.get("eval_report"):
        report = EvaluationReport(**state["eval_report"])
        failure_dist = report.failure_distribution()
        dominant = report.dominant_failure_type()
        parts.extend([
            f"coverage_pct: {report.coverage_pct}% (target: {TARGET_COVERAGE}%)",
            f"exec_pct: {report.exec_pct}% (target: {TARGET_EXEC}%)",
            f"hallucinations: {report.hallucination_count}",
            f"failing_req_ids: {report.failing_req_ids()[:5]}",
            f"failure_distribution: {json.dumps(failure_dist)}",
            f"dominant_failure_type: {dominant or 'none'}",
        ])

    hist = state.get("coverage_history", [])
    if len(hist) >= 2:
        delta = hist[-1] - hist[-2]
        parts.append(f"coverage_delta_last_loop: {delta:+.1f}%")

    return "\n".join(parts)


def _rule_based_decision(state: AgentState) -> tuple[str, str]:
    """Fallback when R1 LLM call fails. Pure rule-based."""
    if not state.get("requirement_bundle"):
        return "extract", "No requirements — run extraction"
    if not state.get("test_suite"):
        # Check if requirements are approved before generating
        bundle_data = state.get("requirement_bundle", {})
        reqs = bundle_data.get("requirements", [])
        approved = [r for r in reqs if r.get("approved") and not r.get("rejected")]
        if not approved:
            if state.get("interactive"):
                return "hitl_phase1", "Requirements need human approval"
            # Auto-approve all for non-interactive mode
            return "generate", "Requirements exist — auto-approve and generate"
        return "generate", "Requirements approved — run codegen"
    if not state.get("eval_report"):
        return "run_tests", "Tests exist but not evaluated"

    report = EvaluationReport(**state["eval_report"])
    # If 0 tests exist, repair is pointless — regenerate
    suite = state.get("test_suite")
    test_count = len(suite.get("tests", [])) if suite else 0
    if test_count == 0:
        return "generate", "No tests exist — must regenerate"

    crawl_demand_count = state.get("crawl_demand_count", 0)
    dominant = report.dominant_failure_type()

    # Hallucinations always get crawl first (up to 2x)
    if report.hallucination_count > 0 and crawl_demand_count < 2:
        return "crawl_demand", "Hallucinations present — on-demand crawl for real selectors"

    # selector_not_found without hallucinations = selectors exist in app but not in map
    if dominant == "selector_not_found" and report.hallucination_count == 0 and crawl_demand_count < 2:
        return "crawl_demand", "Selector not found failures — re-crawl to refresh selector map"

    # Timeout/assertion/strict_mode/network_error → repair directly (no crawl needed)
    if dominant in ("timeout", "assertion_failure", "strict_mode", "network_error"):
        return "repair", f"Dominant failure type '{dominant}' — send to repair agent"

    if not report.targets_met:
        if state.get("stall_count", 0) >= 2:
            return "generate", "Coverage stalled — full regeneration"
        return "repair", "Targets not met — repair failing tests"

    return "learn", "Targets met — run learner"


def route_decision(state: AgentState) -> str:
    """LangGraph conditional edge function — returns the next node name."""
    return state.get("next_action", "done")


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE NODES
# ══════════════════════════════════════════════════════════════════════════════

def node_infer_domain(state: AgentState) -> AgentState:
    from app.agents.domain_inferrer import infer_domain
    profile = infer_domain(state["base_url"], state.get("resource"))
    return {**state, "domain_profile": profile.model_dump(), "last_action": "infer_domain"}


def node_handle_auth(state: AgentState) -> AgentState:
    from app.core.auth_handler import handle_auth
    profile = DomainProfile(**state["domain_profile"])
    ctx = handle_auth(profile, state.get("resource", {}), state["run_id"])
    return {**state, "auth_context": ctx.model_dump(), "last_action": "handle_auth"}


def node_crawl_routes(state: AgentState) -> AgentState:
    from app.core.route_crawler import crawl
    profile  = DomainProfile(**state["domain_profile"])
    auth_ctx = AuthContext(**state["auth_context"])
    selector_map = crawl(
        profile=profile,
        auth_ctx=auth_ctx,
        resource=state.get("resource", {}),
        run_id=state["run_id"],
        force=state.get("force_crawl", False),
    )
    return {**state, "selector_map": selector_map.model_dump(), "last_action": "crawl_routes"}


def node_agent_a(state: AgentState) -> AgentState:
    from app.agents.extraction_agent import run_extraction

    # --requirements override: load saved bundle, skip extraction
    req_path = state.get("requirements_path")
    if req_path and Path(req_path).exists():
        log.info(f"Agent A: loading saved requirements from {req_path}")
        bundle = RequirementBundle.model_validate_json(
            Path(req_path).read_text(encoding="utf-8")
        )
        bundle.run_id = state["run_id"]
        # Auto-approve all when loading saved requirements
        for r in bundle.requirements:
            if not r.rejected:
                r.approved = True
        return {**state, "requirement_bundle": bundle.model_dump(), "last_action": "agent_a"}

    profile = DomainProfile(**state["domain_profile"])
    bundle = run_extraction(
        pdf_path=state["pdf_path"],
        domain_profile=profile,
        run_id=state["run_id"],
        force=state.get("force_extract", False),
    )
    # In non-interactive mode, auto-approve all requirements so codegen can proceed
    if not state.get("interactive"):
        for r in bundle.requirements:
            if not r.rejected:
                r.approved = True
        log.info(f"Agent A: auto-approved {len(bundle.approved_requirements())} requirements (non-interactive)")
    return {**state, "requirement_bundle": bundle.model_dump(), "last_action": "agent_a"}


def node_hitl_phase1(state: AgentState) -> AgentState:
    from app.hitl.hitl_manager import run_hitl_phase1
    bundle = RequirementBundle(**state["requirement_bundle"])
    feedback = run_hitl_phase1(bundle, state["run_id"])
    # Apply feedback to bundle
    bundle = _apply_phase1_feedback(bundle, feedback)
    return {
        **state,
        "requirement_bundle": bundle.model_dump(),
        "feedback_phase1": feedback.model_dump(),
        "last_action": "hitl_phase1",
    }


def _apply_phase1_feedback(bundle: RequirementBundle, feedback: FeedbackResult) -> RequirementBundle:
    approved_ids  = feedback.approved_ids()
    rejected_ids  = feedback.rejected_ids()
    item_map      = {i.item_id: i for i in feedback.items}

    for req in bundle.requirements:
        if req.req_id in approved_ids:
            req.approved = True
        elif req.req_id in rejected_ids:
            req.rejected = True
        else:
            # Default: approve if confidence >= 0.75 and not gap_analysis
            if req.confidence >= 0.75 and not req.gap_analysis:
                req.approved = True

        # Inject per-item human prompt for Agent B
        item = item_map.get(req.req_id)
        if item and item.run_prompt:
            req.human_prompt = item.run_prompt

    return bundle


def node_agent_b(state: AgentState) -> AgentState:
    from app.agents.codegen_agent import run_codegen
    bundle      = RequirementBundle(**state["requirement_bundle"])
    sel_map     = PageSelectorMap(**state["selector_map"]) if state.get("selector_map") else None
    fb1         = FeedbackResult(**state["feedback_phase1"]) if state.get("feedback_phase1") else None

    suite = run_codegen(
        bundle=bundle,
        selector_map=sel_map,
        run_id=state["run_id"],
        global_prompt=fb1.global_prompt if fb1 else None,
        category_prompts=fb1.category_prompts if fb1 else {},
    )
    return {**state, "test_suite": suite.model_dump(), "last_action": "agent_b"}


def node_hitl_phase2(state: AgentState) -> AgentState:
    from app.hitl.hitl_manager import run_hitl_phase2
    suite   = TestSuite(**state["test_suite"])
    bundle  = RequirementBundle(**state["requirement_bundle"])
    feedback = run_hitl_phase2(suite, bundle, state["run_id"])
    suite = _apply_phase2_feedback(suite, feedback)
    return {
        **state,
        "test_suite": suite.model_dump(),
        "feedback_phase2": feedback.model_dump(),
        "last_action": "hitl_phase2",
    }


def _apply_phase2_feedback(suite: TestSuite, feedback: FeedbackResult) -> TestSuite:
    approved_ids = feedback.approved_ids()
    rejected_ids = feedback.rejected_ids()
    item_map     = {i.item_id: i for i in feedback.items}

    for test in suite.tests:
        if test.test_id in approved_ids:
            test.approved = True
        elif test.test_id in rejected_ids:
            test.rejected = True
        else:
            test.approved = True  # default approve
        item = item_map.get(test.test_id)
        if item and item.run_prompt:
            test.human_prompt = item.run_prompt

    return suite


def node_evaluator(state: AgentState) -> AgentState:
    from app.core.evaluator_engine import evaluate
    suite    = TestSuite(**state["test_suite"])
    sel_map  = PageSelectorMap(**state["selector_map"])
    bundle   = RequirementBundle(**state["requirement_bundle"])

    loop_history = []
    if state.get("eval_report"):
        loop_history = EvaluationReport(**state["eval_report"]).loop_history

    report = evaluate(
        suite=suite,
        selector_map=sel_map,
        bundle_req_count=len(bundle.requirements),
        approved_req_count=len(bundle.approved_requirements()),
        run_id=state["run_id"],
        loop_number=state.get("loop_count", 0),
        loop_history=loop_history,
        start_time=time.time(),
        base_url=state.get("base_url", ""),
    )

    # Update coverage history + stall detection
    hist = list(state.get("coverage_history", []))
    hist.append(report.coverage_pct)
    stall = state.get("stall_count", 0)
    if len(hist) >= 2 and abs(hist[-1] - hist[-2]) < 2.0:
        stall += 1
        log.warning(f"Planner: coverage stall detected (stall_count={stall})")
    else:
        stall = 0

    return {
        **state,
        "eval_report":      report.model_dump(),
        "loop_count":       state.get("loop_count", 0) + 1,
        "coverage_history": hist,
        "stall_count":      stall,
        "generate_count":   0,   # reset after each test run
        "last_action":      "evaluator",
    }


def node_repair(state: AgentState) -> AgentState:
    from app.agents.repair_agent import repair_batch
    suite   = TestSuite(**state["test_suite"])
    sel_map = PageSelectorMap(**state["selector_map"])
    report  = EvaluationReport(**state["eval_report"])
    profile = DomainProfile(**state["domain_profile"])

    # Back-populate failure_type and dom_snapshot from test results onto TestCase objects
    # (evaluator sets these on TestCase.last_error etc, but after deserialization they may be stale)
    result_by_test_id = {r.test_id: r for r in report.test_results}
    for test in suite.tests:
        tr = result_by_test_id.get(test.test_id)
        if tr and not tr.passed:
            test.last_error   = tr.error or test.last_error
            test.failure_type = tr.failure_type or test.failure_type
            if tr.dom_snapshot:
                test.dom_snapshot = tr.dom_snapshot

    # Get failing tests — use test_id from results for accuracy
    failing_test_ids = {r.test_id for r in report.test_results if not r.passed}
    failing_tests = [t for t in suite.tests if t.test_id in failing_test_ids]
    if not failing_tests:
        # Fallback: use req_id
        failing_req_ids = set(report.failing_req_ids())
        failing_tests = [t for t in suite.tests if t.req_id in failing_req_ids]

    dominant = report.dominant_failure_type()
    log.info(f"Repair node: {len(failing_tests)} failing tests, dominant failure: {dominant}")

    repaired = repair_batch(
        failing_tests=failing_tests,
        suite=suite,
        selector_map=sel_map,
        domain_profile=profile,
        run_id=state["run_id"],
        batch_idx=state.get("loop_count", 1),
    )
    log.info(f"Repair node: {repaired} tests repaired")
    return {**state, "test_suite": suite.model_dump(), "last_action": "repair"}


def node_on_demand_crawl(state: AgentState) -> AgentState:
    from app.agents.repair_agent import on_demand_crawl_and_repair
    suite    = TestSuite(**state["test_suite"])
    sel_map  = PageSelectorMap(**state["selector_map"])
    auth_ctx = AuthContext(**state["auth_context"])
    profile  = DomainProfile(**state["domain_profile"])
    report   = EvaluationReport(**state["eval_report"]) if state.get("eval_report") else None

    # Back-populate failure_type from eval report onto test cases
    if report:
        result_by_test_id = {r.test_id: r for r in report.test_results}
        for test in suite.tests:
            tr = result_by_test_id.get(test.test_id)
            if tr and not tr.passed:
                test.failure_type = tr.failure_type or test.failure_type
                test.last_error   = tr.error or test.last_error
                if tr.dom_snapshot:
                    test.dom_snapshot = tr.dom_snapshot

    # Include hallucinated tests AND selector_not_found failures for crawl
    hall_tests = [t for t in suite.tests if t.hallucinated]
    if report:
        failing_test_ids = {r.test_id for r in report.test_results if not r.passed and r.failure_type == "selector_not_found"}
        for t in suite.tests:
            if t.test_id in failing_test_ids and t not in hall_tests:
                hall_tests.append(t)

    log.info(f"On-demand crawl: {len(hall_tests)} tests need selector resolution")
    repaired = on_demand_crawl_and_repair(
        hallucinated_tests=hall_tests,
        suite=suite,
        selector_map=sel_map,
        auth_ctx=auth_ctx,
        domain_profile=profile,
        run_id=state["run_id"],
    )
    return {
        **state,
        "test_suite":         suite.model_dump(),
        "selector_map":       sel_map.model_dump(),
        "crawl_demand_count": state.get("crawl_demand_count", 0) + 1,
        "last_action":        "on_demand_crawl",
    }


def node_hitl_phase3(state: AgentState) -> AgentState:
    from app.hitl.hitl_manager import run_hitl_phase3
    report  = EvaluationReport(**state["eval_report"])
    feedback = run_hitl_phase3(report, state["run_id"])
    return {
        **state,
        "feedback_phase3": feedback.model_dump(),
        "last_action": "hitl_phase3",
    }


def node_post_run_learn(state: AgentState) -> AgentState:
    from app.core.post_run_learner import run_learner
    feedback_list = []
    for key in ("feedback_phase1", "feedback_phase2", "feedback_phase3"):
        if state.get(key):
            feedback_list.append(FeedbackResult(**state[key]))

    profile = DomainProfile(**state["domain_profile"])
    suite   = TestSuite(**state.get("test_suite", {"tests": [], "run_id": state["run_id"]}))
    report  = EvaluationReport(**state["eval_report"]) if state.get("eval_report") else None

    run_learner(
        feedback_list=feedback_list,
        domain_profile=profile,
        suite=suite,
        eval_report=report,
        run_id=state["run_id"],
    )
    return {**state, "last_action": "post_run_learn"}


def node_quality_monitor(state: AgentState) -> AgentState:
    from app.core.quality_monitor import record_and_report
    report  = EvaluationReport(**state["eval_report"]) if state.get("eval_report") else None
    profile = DomainProfile(**state["domain_profile"])
    record_and_report(report, profile, state["run_id"])
    return {**state, "last_action": "quality_monitor"}


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════

def build_graph():
    """Build and compile the LangGraph pipeline."""
    CHECKPOINT_DB = str(CACHE_DIR / "checkpoints.db")
    _conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    checkpointer = SqliteSaver(_conn)

    workflow = StateGraph(AgentState)

    # Register all nodes
    workflow.add_node("infer_domain",      node_infer_domain)
    workflow.add_node("handle_auth",       node_handle_auth)
    workflow.add_node("crawl_routes",      node_crawl_routes)
    workflow.add_node("agent_a",           node_agent_a)
    workflow.add_node("hitl_phase1",       node_hitl_phase1)
    workflow.add_node("agent_b",           node_agent_b)
    workflow.add_node("hitl_phase2",       node_hitl_phase2)
    workflow.add_node("evaluator",         node_evaluator)
    workflow.add_node("planner",           planner_node)
    workflow.add_node("repair",            node_repair)
    workflow.add_node("on_demand_crawl",   node_on_demand_crawl)
    workflow.add_node("hitl_phase3",       node_hitl_phase3)
    workflow.add_node("post_run_learn",    node_post_run_learn)
    workflow.add_node("quality_monitor",   node_quality_monitor)

    # Fixed sequential edges (no decision needed)
    workflow.set_entry_point("infer_domain")
    workflow.add_edge("infer_domain",   "handle_auth")
    workflow.add_edge("handle_auth",    "crawl_routes")
    workflow.add_edge("crawl_routes",   "planner")          # planner decides: extract or generate

    # After each agent/action → planner decides next
    for node in ["agent_a", "hitl_phase1", "agent_b", "hitl_phase2",
                 "evaluator", "repair", "on_demand_crawl", "hitl_phase3"]:
        workflow.add_edge(node, "planner")

    # Planner conditional routing
    workflow.add_conditional_edges(
        "planner",
        route_decision,
        {
            "extract":      "agent_a",
            "hitl_phase1":  "hitl_phase1",
            "generate":     "agent_b",
            "hitl_phase2":  "hitl_phase2",
            "run_tests":    "evaluator",
            "repair":       "repair",
            "crawl_demand": "on_demand_crawl",
            "hitl_phase3":  "hitl_phase3",
            "learn":        "post_run_learn",
            "done":         END,
        },
    )

    # Fixed terminal sequence
    workflow.add_edge("post_run_learn",  "quality_monitor")
    workflow.add_edge("quality_monitor", END)

    return workflow.compile(checkpointer=checkpointer)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(
    run_id: str,
    base_url: str,
    pdf_path: Optional[str] = None,
    requirements_path: Optional[str] = None,
    run_mode: str = "full",
    interactive: bool = False,
    auto_mode: bool = False,
    force_extract: bool = False,
    force_crawl: bool = False,
    resource: Optional[dict] = None,
) -> AgentState:
    """
    Execute the full pipeline from scratch.
    Returns final AgentState.
    """
    graph = build_graph()

    initial_state: AgentState = {
        "run_id":            run_id,
        "run_mode":          run_mode,
        "base_url":          base_url,
        "pdf_path":          pdf_path,
        "requirements_path": requirements_path,
        "domain_profile":    None,
        "auth_context":      None,
        "selector_map":      None,
        "requirement_bundle": None,
        "test_suite":        None,
        "eval_report":       None,
        "feedback_phase1":   None,
        "feedback_phase2":   None,
        "feedback_phase3":   None,
        "loop_count":        0,
        "coverage_history":  [],
        "stall_count":       0,
        "generate_count":    0,
        "crawl_demand_count": 0,
        "last_action":       None,
        "planner_reasoning": None,
        "next_action":       None,
        "force_extract":     force_extract,
        "force_crawl":       force_crawl,
        "interactive":       interactive,
        "auto_mode":         auto_mode,
        "resource":          resource,
    }

    config = {"configurable": {"thread_id": run_id}}

    log.info(f"Pipeline: starting run_id={run_id} mode={run_mode}")
    final = graph.invoke(initial_state, config=config)
    log.info(f"Pipeline: complete run_id={run_id}")
    return final


def resume_pipeline(run_id: str) -> AgentState:
    """
    Resume a stopped/crashed pipeline from its last LangGraph checkpoint.
    """
    graph = build_graph()
    config = {"configurable": {"thread_id": run_id}}
    log.info(f"Pipeline: resuming run_id={run_id}")
    # Passing None as input resumes from last checkpoint
    final = graph.invoke(None, config=config)
    log.info(f"Pipeline: resumed and complete run_id={run_id}")
    return final


def list_runs() -> list[dict]:
    """List all runs stored in the checkpoint database."""
    import sqlite3
    db_path = CACHE_DIR / "checkpoints.db"
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            "SELECT thread_id, checkpoint_id, parent_id FROM checkpoints "
            "ORDER BY checkpoint_id DESC"
        )
        rows = cur.fetchall()
        conn.close()
        # Deduplicate by thread_id, keep latest
        seen: set[str] = set()
        runs = []
        for thread_id, ckpt_id, parent_id in rows:
            if thread_id not in seen:
                seen.add(thread_id)
                runs.append({"run_id": thread_id, "checkpoint": ckpt_id})
        return runs
    except Exception as e:
        log.warning(f"list_runs: DB query failed: {e}")
        return []
