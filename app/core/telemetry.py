"""
ATS v8 — Agent Telemetry
Lightweight structured metrics emitter used by all agents during execution.

Each agent calls telemetry.emit() to record what it did, how well it performed,
and what it learned. All events are appended to monitoring/metrics.jsonl.

The quality monitor reads this file to:
  - Assess per-agent health across runs
  - Detect degradation (codegen hallucination rate rising, repair success falling)
  - Auto-tune agent behaviour via the lesson system

Event schema:
  {
    "ts":        ISO timestamp,
    "run_id":    str,
    "agent":     "agent_a" | "agent_b" | "agent_c" | "planner" | "crawler" | "learner",
    "event":     str,          # snake_case event name
    "loop":      int | null,   # repair loop number if applicable
    "metrics":   dict,         # arbitrary KV metrics for this event
    "ok":        bool          # did this agent action succeed?
  }
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from app.config import MONITORING_DIR

log = logging.getLogger(__name__)

_METRICS_FILE = MONITORING_DIR / "metrics.jsonl"


def emit(
    run_id: str,
    agent: str,
    event: str,
    metrics: dict[str, Any],
    ok: bool = True,
    loop: Optional[int] = None,
) -> None:
    """Append one telemetry event to monitoring/metrics.jsonl."""
    record = {
        "ts":      time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id":  run_id,
        "agent":   agent,
        "event":   event,
        "loop":    loop,
        "metrics": metrics,
        "ok":      ok,
    }
    try:
        with _METRICS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        log.debug(f"Telemetry write failed (non-critical): {e}")


def read_all() -> list[dict]:
    """Read all telemetry events from metrics.jsonl."""
    if not _METRICS_FILE.exists():
        return []
    events = []
    for line in _METRICS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events


def read_run(run_id: str) -> list[dict]:
    """Read all telemetry events for a specific run."""
    return [e for e in read_all() if e.get("run_id") == run_id]


def read_agent(agent: str, last_n_runs: int = 20) -> list[dict]:
    """Read events for a specific agent across last N runs."""
    all_events = read_all()
    # Get unique run_ids in order
    seen_runs: list[str] = []
    for e in all_events:
        rid = e.get("run_id", "")
        if rid not in seen_runs:
            seen_runs.append(rid)
    recent_runs = set(seen_runs[-last_n_runs:])
    return [e for e in all_events if e.get("agent") == agent and e.get("run_id") in recent_runs]


def agent_health_summary(last_n_runs: int = 10) -> dict:
    """
    Compute per-agent health metrics across last N runs.
    Used by quality monitor and dashboard to assess agent intelligence.
    """
    all_events = read_all()
    if not all_events:
        return {}

    # Group by run_id
    by_run: dict[str, list[dict]] = {}
    for e in all_events:
        rid = e["run_id"]
        by_run.setdefault(rid, []).append(e)

    recent_runs = list(by_run.keys())[-last_n_runs:]

    summary: dict[str, dict] = {}

    for agent in ("agent_a", "agent_b", "agent_c", "planner", "crawler", "learner"):
        events = [e for e in all_events
                  if e["agent"] == agent and e["run_id"] in recent_runs]
        if not events:
            continue

        ok_rate = sum(1 for e in events if e.get("ok")) / len(events)

        # Agent-specific metrics
        agent_metrics: dict[str, Any] = {"ok_rate": round(ok_rate, 3), "total_events": len(events)}

        if agent == "agent_a":
            extracted = [e["metrics"].get("reqs_extracted", 0) for e in events if e["event"] == "extraction_complete"]
            removed   = [e["metrics"].get("reqs_removed_untestable", 0) for e in events if e["event"] == "extraction_complete"]
            if extracted:
                agent_metrics["avg_reqs_extracted"]    = round(sum(extracted) / len(extracted), 1)
                agent_metrics["avg_untestable_removed"] = round(sum(removed) / len(removed), 1)
                agent_metrics["testability_rate"]       = round(
                    1 - (sum(removed) / max(sum(extracted), 1)), 3)

        elif agent == "agent_b":
            hall_rates = [e["metrics"].get("hallucination_rate", 0) for e in events if e["event"] == "codegen_complete"]
            gen_rates  = [e["metrics"].get("tests_generated", 0) for e in events if e["event"] == "codegen_complete"]
            fail_rates = [e["metrics"].get("batch_parse_failures", 0) for e in events if e["event"] == "codegen_complete"]
            if hall_rates:
                agent_metrics["avg_hallucination_rate"]   = round(sum(hall_rates) / len(hall_rates), 3)
                agent_metrics["avg_tests_generated"]      = round(sum(gen_rates) / len(gen_rates), 1)
                agent_metrics["avg_batch_parse_failures"] = round(sum(fail_rates) / len(fail_rates), 2)
                # Trend: is hallucination rate improving?
                if len(hall_rates) >= 2:
                    agent_metrics["hallucination_trend"] = "improving" if hall_rates[-1] < hall_rates[0] else "degrading" if hall_rates[-1] > hall_rates[0] else "stable"

        elif agent == "agent_c":
            repair_rates   = [e["metrics"].get("repair_success_rate", 0) for e in events if e["event"] == "repair_complete"]
            loops_to_conv  = [e["metrics"].get("loops_to_converge", 0) for e in events if e["event"] == "run_summary"]
            json_failures  = [e["metrics"].get("json_parse_failures", 0) for e in events if e["event"] == "repair_complete"]
            if repair_rates:
                agent_metrics["avg_repair_success_rate"] = round(sum(repair_rates) / len(repair_rates), 3)
                agent_metrics["avg_json_parse_failures"] = round(sum(json_failures) / len(json_failures), 2)
                if len(repair_rates) >= 2:
                    agent_metrics["repair_trend"] = "improving" if repair_rates[-1] > repair_rates[0] else "degrading" if repair_rates[-1] < repair_rates[0] else "stable"
            if loops_to_conv:
                agent_metrics["avg_loops_to_converge"] = round(sum(loops_to_conv) / len(loops_to_conv), 1)

        elif agent == "planner":
            actions = [e["metrics"].get("action") for e in events if e["event"] == "decision" and e["metrics"].get("action")]
            if actions:
                from collections import Counter
                dist = Counter(actions)
                agent_metrics["action_distribution"] = dict(dist.most_common())
                agent_metrics["repair_ratio"] = round(dist.get("repair", 0) / len(actions), 3)
                agent_metrics["crawl_ratio"]  = round(dist.get("crawl_demand", 0) / len(actions), 3)

        elif agent == "crawler":
            sel_counts = [e["metrics"].get("selectors_found", 0) for e in events if e["event"] == "crawl_complete"]
            if sel_counts:
                agent_metrics["avg_selectors_per_crawl"] = round(sum(sel_counts) / len(sel_counts), 1)

        elif agent == "learner":
            lessons = [e["metrics"].get("lessons_added", 0) for e in events if e["event"] == "learning_complete"]
            if lessons:
                agent_metrics["avg_lessons_per_run"]  = round(sum(lessons) / len(lessons), 1)
                agent_metrics["total_lessons_banked"] = sum(lessons)

        summary[agent] = agent_metrics

    return summary
