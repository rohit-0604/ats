"""
ATS v8 — Monitoring Dashboard Generator
Reads monitoring/metrics.jsonl and generates monitoring/dashboard.html.

Dynatrace-style agent observability:
- Per-agent health scores and trend indicators
- Learning effectiveness (are lessons actually improving quality?)
- Repair intelligence (is Agent C getting smarter each run?)
- Planner decision quality (routing accuracy, stall detection)
- Cross-run convergence analysis
"""

from __future__ import annotations
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config import MONITORING_DIR
from app.core.telemetry import read_all, agent_health_summary

log = logging.getLogger(__name__)

_DASHBOARD_FILE = MONITORING_DIR / "dashboard.html"


def _group_by_run(events: list[dict]) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {}
    for e in events:
        runs.setdefault(e["run_id"], []).append(e)
    return runs


def _run_kpis(run_events: list[dict]) -> dict:
    """Extract KPIs from a single run's telemetry events."""
    kpis: dict[str, Any] = {"run_id": "", "ts": ""}
    for e in run_events:
        kpis["run_id"] = e.get("run_id", "")
        kpis["ts"]     = e.get("ts", "")
        m = e.get("metrics", {})
        if e["agent"] == "agent_a" and e["event"] == "extraction_complete":
            kpis["reqs_extracted"]  = m.get("reqs_extracted", 0)
            kpis["reqs_final"]      = m.get("final_req_count", 0)
            kpis["reqs_untestable"] = m.get("reqs_removed_untestable", 0)
            kpis["agent_a_s"]       = m.get("duration_s", 0)
        if e["agent"] == "agent_b" and e["event"] == "codegen_complete":
            kpis["tests_generated"]  = m.get("tests_generated", 0)
            kpis["hallucination_rate"] = m.get("hallucination_rate", 0)
            kpis["agent_b_s"]        = m.get("duration_s", 0)
        if e["agent"] == "agent_c" and e["event"] == "run_summary":
            kpis["loops_to_converge"] = m.get("loops_to_converge", 0)
            kpis["final_coverage"]    = m.get("final_coverage_pct", 0)
            kpis["final_exec"]        = m.get("final_exec_pct", 0)
            kpis["exit_reason"]       = m.get("exit_reason", "")
        if e["agent"] == "learner" and e["event"] == "learning_complete":
            kpis["lessons_added"]  = m.get("lessons_added", 0)
            kpis["targets_met"]    = m.get("targets_met", False)
        if e["agent"] == "crawler" and e["event"] == "crawl_complete":
            kpis["selectors_found"] = m.get("selectors_found", 0)
            kpis["pages_crawled"]   = m.get("pages_crawled", 0)
    return kpis


def _repair_loop_series(run_events: list[dict]) -> list[dict]:
    """Return per-loop repair metrics for a run."""
    loops = []
    for e in run_events:
        if e["agent"] == "planner" and e["event"] == "decision":
            m = e.get("metrics", {})
            loops.append({
                "loop":        m.get("loop_count", 0),
                "action":      m.get("action", ""),
                "coverage":    m.get("coverage_pct", 0),
                "exec":        m.get("exec_pct", 0),
                "hallucinations": m.get("hallucinations", 0),
            })
    return loops


def _agent_score(health: dict) -> dict[str, float]:
    """
    Compute 0–100 health score per agent based on key metrics.
    Higher = healthier.
    """
    scores: dict[str, float] = {}

    if "agent_a" in health:
        h = health["agent_a"]
        tr = h.get("testability_rate", 0.9)
        scores["Agent A\nExtraction"] = round(min(100, tr * 100), 1)

    if "agent_b" in health:
        h = health["agent_b"]
        hall = h.get("avg_hallucination_rate", 0.5)
        scores["Agent B\nCodegen"] = round(min(100, (1 - hall) * 100), 1)

    if "agent_c" in health:
        h = health["agent_c"]
        rsr = h.get("avg_repair_success_rate", 0.5)
        scores["Agent C\nRepair"] = round(min(100, rsr * 100), 1)

    if "planner" in health:
        h = health["planner"]
        repair_ratio = h.get("repair_ratio", 0.5)
        # Ideal planner shouldn't need to repair constantly — lower repair ratio = better
        scores["Planner"] = round(min(100, (1 - repair_ratio * 0.5) * 100), 1)

    if "learner" in health:
        h = health["learner"]
        lpr = min(h.get("avg_lessons_per_run", 0) / 30, 1.0)
        scores["Learner"] = round(lpr * 100, 1)

    if "crawler" in health:
        h = health["crawler"]
        sel = min(h.get("avg_selectors_per_crawl", 0) / 100, 1.0)
        scores["Crawler"] = round(sel * 100, 1)

    return scores


def generate_dashboard() -> Path:
    """Read metrics.jsonl and write monitoring/dashboard.html."""
    events   = read_all()
    by_run   = _group_by_run(events)
    health   = agent_health_summary(last_n_runs=10)
    scores   = _agent_score(health)

    run_ids   = list(by_run.keys())
    run_kpis  = [_run_kpis(by_run[r]) for r in run_ids]

    # Time-series for coverage/exec trend chart
    ts_labels   = json.dumps([k.get("run_id", "")[:8] for k in run_kpis])
    ts_coverage = json.dumps([k.get("final_coverage", 0) for k in run_kpis])
    ts_exec     = json.dumps([k.get("final_exec", 0)     for k in run_kpis])
    ts_hall     = json.dumps([k.get("hallucination_rate", 0) * 100 for k in run_kpis])
    ts_lessons  = json.dumps([k.get("lessons_added", 0)  for k in run_kpis])
    ts_loops    = json.dumps([k.get("loops_to_converge", 0) for k in run_kpis])

    # Agent score gauge data
    score_labels = json.dumps(list(scores.keys()))
    score_values = json.dumps(list(scores.values()))

    # Per-agent trend data for radar
    radar_labels = json.dumps(["Extraction\nQuality", "Codegen\nAccuracy", "Repair\nSuccess", "Planner\nEfficiency", "Learning\nRate", "Crawl\nCoverage"])

    def _radar_val(key: str, metric: str, default: float, scale: float = 100.0) -> float:
        return round(min(100, health.get(key, {}).get(metric, default) * scale), 1)

    radar_values = json.dumps([
        _radar_val("agent_a", "testability_rate", 0.8),
        _radar_val("agent_b", "avg_hallucination_rate", 0.3, -100) + 100,  # invert: low hall = high score
        _radar_val("agent_c", "avg_repair_success_rate", 0.5),
        round(min(100, (1 - health.get("planner", {}).get("repair_ratio", 0.5) * 0.5) * 100), 1),
        round(min(100, health.get("learner", {}).get("avg_lessons_per_run", 0) / 30 * 100), 1),
        round(min(100, health.get("crawler", {}).get("avg_selectors_per_crawl", 0) / 100 * 100), 1),
    ])

    # Latest run summary
    latest = run_kpis[-1] if run_kpis else {}
    prev   = run_kpis[-2] if len(run_kpis) >= 2 else {}

    def _delta(key: str, fmt: str = "+.1f") -> str:
        cur = latest.get(key, 0)
        prv = prev.get(key, 0)
        if not prv:
            return ""
        d = cur - prv
        sign = "▲" if d > 0 else "▼" if d < 0 else "—"
        color = "#10b981" if d > 0 else "#ef4444" if d < 0 else "#64748b"
        return f'<span style="color:{color};font-size:0.75rem"> {sign} {abs(d):.1f}</span>'

    # Build run history table rows
    run_rows = ""
    for k in reversed(run_kpis[-10:]):
        cov   = k.get("final_coverage", 0)
        exc   = k.get("final_exec", 0)
        hall  = k.get("hallucination_rate", 0)
        loops = k.get("loops_to_converge", 0)
        met   = k.get("targets_met", False)
        badge = '<span class="badge pass">✓ MET</span>' if met else '<span class="badge fail">✗ MISS</span>'
        run_rows += f"""<tr>
          <td class="mono">{k.get("run_id","")[:16]}</td>
          <td style="color:{'#10b981' if cov>=85 else '#f59e0b'}">{cov:.1f}%</td>
          <td style="color:{'#10b981' if exc>=80 else '#f59e0b'}">{exc:.1f}%</td>
          <td>{k.get('tests_generated',0)}</td>
          <td style="color:{'#ef4444' if hall>0.1 else '#10b981'}">{hall:.1%}</td>
          <td>{loops}</td>
          <td>{k.get('lessons_added',0)}</td>
          <td>{badge}</td>
        </tr>"""

    # Agent health detail cards
    def _trend_badge(trend: str) -> str:
        if trend == "improving":
            return '<span class="badge pass">▲ Improving</span>'
        if trend == "degrading":
            return '<span class="badge fail">▼ Degrading</span>'
        return '<span class="badge neutral">— Stable</span>'

    agent_cards = ""
    agent_defs = [
        ("agent_a", "Agent A — Extraction", "Extracts requirements from PDF. Filters untestable ones."),
        ("agent_b", "Agent B — Codegen",    "Generates Playwright TypeScript tests from requirements."),
        ("agent_c", "Agent C — Repair",     "Repairs failing tests using DOM snapshots and real selectors."),
        ("planner", "Planner — Orchestrator", "Routes pipeline decisions using ReAct reasoning."),
        ("learner", "Learner — Memory",     "Extracts lessons from each run and banks them for future runs."),
        ("crawler", "Crawler — Selectors",  "Discovers real page selectors to guide code generation."),
    ]
    for key, title, desc in agent_defs:
        h = health.get(key, {})
        if not h:
            continue
        score = scores.get(title.split("—")[0].strip(), 0)
        score_color = "#10b981" if score >= 75 else "#f59e0b" if score >= 50 else "#ef4444"
        metrics_html = "".join(
            f'<div class="metric-row"><span class="metric-key">{k.replace("_"," ").title()}</span>'
            f'<span class="metric-val">{v}</span></div>'
            for k, v in h.items() if k not in ("total_events",)
        )
        trend_key = "hallucination_trend" if key == "agent_b" else "repair_trend" if key == "agent_c" else None
        trend_html = _trend_badge(h.get(trend_key, "stable")) if trend_key and trend_key in h else ""
        agent_cards += f"""
        <div class="agent-card">
          <div class="agent-header">
            <div>
              <div class="agent-title">{title}</div>
              <div class="agent-desc">{desc}</div>
            </div>
            <div class="agent-score" style="color:{score_color}">{score}<span style="font-size:1rem;color:#64748b">/100</span></div>
          </div>
          {trend_html}
          <div class="metrics-grid">{metrics_html}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>ATS v8 — Agent Intelligence Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0a0e1a; color:#e2e8f0; }}
.topbar {{ background:linear-gradient(90deg,#1a1d2e,#0a0e1a); border-bottom:2px solid #6d28d9;
           padding:16px 32px; display:flex; justify-content:space-between; align-items:center; }}
.topbar h1 {{ font-size:1.2rem; color:#a78bfa; font-weight:700; letter-spacing:0.05em; }}
.topbar .subtitle {{ font-size:0.78rem; color:#475569; }}
.live-dot {{ width:8px; height:8px; background:#10b981; border-radius:50%; display:inline-block;
             margin-right:6px; animation:pulse 2s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
.kpi-bar {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; padding:20px 32px; }}
.kpi {{ background:#111827; border:1px solid #1e293b; border-radius:8px; padding:16px; text-align:center; }}
.kpi-val {{ font-size:1.8rem; font-weight:700; }}
.kpi-lbl {{ font-size:0.72rem; color:#475569; text-transform:uppercase; margin-top:4px; letter-spacing:0.06em; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:0 32px 20px; }}
.grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; padding:0 32px 20px; }}
.card {{ background:#111827; border:1px solid #1e293b; border-radius:10px; padding:20px; }}
.card h2 {{ font-size:0.8rem; color:#64748b; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:14px; font-weight:600; }}
.agent-card {{ background:#111827; border:1px solid #1e293b; border-radius:10px; padding:18px; }}
.agent-header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }}
.agent-title {{ font-size:0.88rem; font-weight:700; color:#c4b5fd; }}
.agent-desc  {{ font-size:0.72rem; color:#475569; margin-top:3px; }}
.agent-score {{ font-size:2rem; font-weight:800; }}
.metrics-grid {{ margin-top:10px; }}
.metric-row {{ display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #1e293b; font-size:0.76rem; }}
.metric-key {{ color:#64748b; }}
.metric-val {{ color:#e2e8f0; font-family:monospace; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; margin-bottom:8px; }}
.badge.pass {{ background:#064e3b; color:#6ee7b7; }}
.badge.fail {{ background:#450a0a; color:#fca5a5; }}
.badge.neutral {{ background:#1e293b; color:#94a3b8; }}
table {{ width:100%; border-collapse:collapse; font-size:0.78rem; }}
th {{ background:#0f172a; color:#475569; padding:8px 10px; text-align:left; border-bottom:1px solid #1e293b; font-weight:500; }}
td {{ padding:7px 10px; border-bottom:1px solid #111827; }}
.mono {{ font-family:monospace; font-size:0.72rem; color:#94a3b8; }}
.section-pad {{ padding:0 32px 20px; }}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <h1><span class="live-dot"></span>ATS v8 — Agent Intelligence Monitor</h1>
    <div class="subtitle">Dynatrace-style observability · Auto-refresh every 30s · {len(run_ids)} runs tracked</div>
  </div>
  <div style="font-size:0.76rem;color:#475569">Last updated: {time.strftime("%Y-%m-%d %H:%M UTC")}</div>
</div>

<div class="kpi-bar">
  <div class="kpi">
    <div class="kpi-val" style="color:{'#10b981' if latest.get('final_coverage',0)>=85 else '#f59e0b'}">{latest.get('final_coverage',0):.1f}%</div>
    <div class="kpi-lbl">Coverage (latest){_delta('final_coverage')}</div>
  </div>
  <div class="kpi">
    <div class="kpi-val" style="color:{'#10b981' if latest.get('final_exec',0)>=80 else '#f59e0b'}">{latest.get('final_exec',0):.1f}%</div>
    <div class="kpi-lbl">Pass Rate (latest){_delta('final_exec')}</div>
  </div>
  <div class="kpi">
    <div class="kpi-val" style="color:{'#ef4444' if latest.get('hallucination_rate',0)>0.1 else '#10b981'}">{latest.get('hallucination_rate',0):.1%}</div>
    <div class="kpi-lbl">Hallucination Rate{_delta('hallucination_rate')}</div>
  </div>
  <div class="kpi">
    <div class="kpi-val">{latest.get('loops_to_converge',0)}</div>
    <div class="kpi-lbl">Loops to Converge{_delta('loops_to_converge')}</div>
  </div>
  <div class="kpi">
    <div class="kpi-val" style="color:#a78bfa">{latest.get('lessons_added',0)}</div>
    <div class="kpi-lbl">Lessons Banked (latest)</div>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <h2>Coverage &amp; Pass Rate Trend</h2>
    <canvas id="trendChart" height="140"></canvas>
  </div>
  <div class="card">
    <h2>Agent Intelligence Radar</h2>
    <canvas id="radarChart" height="140"></canvas>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <h2>Learning Velocity (Lessons + Hallucination Rate)</h2>
    <canvas id="learningChart" height="130"></canvas>
  </div>
  <div class="card">
    <h2>Repair Convergence (Loops per Run)</h2>
    <canvas id="loopChart" height="130"></canvas>
  </div>
</div>

<div class="grid3">
  {agent_cards}
</div>

<div class="section-pad">
  <div class="card">
    <h2>Run History</h2>
    <table>
      <thead><tr>
        <th>Run ID</th><th>Coverage</th><th>Pass Rate</th>
        <th>Tests</th><th>Hall Rate</th><th>Loops</th><th>Lessons</th><th>Target</th>
      </tr></thead>
      <tbody>{run_rows}</tbody>
    </table>
  </div>
</div>

<script>
const labels    = {ts_labels};
const coverage  = {ts_coverage};
const execRate  = {ts_exec};
const hallRate  = {ts_hall};
const lessons   = {ts_lessons};
const loops     = {ts_loops};
const agScores  = {score_values};
const agLabels  = {score_labels};
const radarLbls = {radar_labels};
const radarVals = {radar_values};

const chartDefs = [
  {{ id:'trendChart', type:'line', labels, datasets:[
    {{ label:'Coverage %', data:coverage, borderColor:'#7c3aed', backgroundColor:'rgba(124,58,237,0.1)', tension:0.3, fill:true, pointRadius:3 }},
    {{ label:'Pass Rate %', data:execRate, borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.08)', tension:0.3, fill:true, pointRadius:3 }},
  ], yMin:0, yMax:100 }},
  {{ id:'learningChart', type:'line', labels, datasets:[
    {{ label:'Lessons Added', data:lessons, borderColor:'#a78bfa', tension:0.3, pointRadius:3, yAxisID:'y' }},
    {{ label:'Hallucination % × 10', data:hallRate, borderColor:'#f87171', tension:0.3, pointRadius:3, yAxisID:'y' }},
  ], yMin:0 }},
  {{ id:'loopChart', type:'bar', labels, datasets:[
    {{ label:'Loops to Converge', data:loops, backgroundColor:'rgba(139,92,246,0.6)', borderColor:'#7c3aed', borderWidth:1 }},
  ], yMin:0 }},
];

const baseOpts = (yMin=0, yMax=null) => ({{
  responsive:true,
  plugins:{{ legend:{{ labels:{{ color:'#94a3b8', font:{{size:10}} }} }} }},
  scales:{{
    x:{{ ticks:{{ color:'#475569', font:{{size:9}} }}, grid:{{ color:'#1e293b' }} }},
    y:{{ min:yMin, ...(yMax!=null?{{max:yMax}}:{{}}), ticks:{{ color:'#475569', font:{{size:9}} }}, grid:{{ color:'#1e293b' }} }},
  }},
}});

chartDefs.forEach(d => {{
  const ctx = document.getElementById(d.id);
  if (!ctx) return;
  new Chart(ctx, {{ type:d.type, data:{{ labels:d.labels, datasets:d.datasets }}, options:baseOpts(d.yMin||0, d.yMax||null) }});
}});

// Radar
const radarCtx = document.getElementById('radarChart');
if (radarCtx) {{
  new Chart(radarCtx, {{
    type: 'radar',
    data: {{
      labels: radarLbls,
      datasets: [{{
        label: 'Agent Health',
        data: radarVals,
        borderColor: '#7c3aed',
        backgroundColor: 'rgba(124,58,237,0.2)',
        pointBackgroundColor: '#a78bfa',
        pointRadius: 4,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ labels: {{ color:'#94a3b8', font:{{size:10}} }} }} }},
      scales: {{ r: {{
        min: 0, max: 100,
        ticks: {{ color:'#475569', font:{{size:9}}, stepSize:25, backdropColor:'transparent' }},
        grid: {{ color:'#1e293b' }},
        pointLabels: {{ color:'#94a3b8', font:{{size:9}} }},
      }} }},
    }},
  }});
}}
</script>
</body>
</html>"""

    _DASHBOARD_FILE.write_text(html, encoding="utf-8")
    log.info(f"Dashboard: written → {_DASHBOARD_FILE}")
    return _DASHBOARD_FILE


def update_dashboard() -> None:
    """Called by quality_monitor after every run. Safe to call even with no data."""
    try:
        generate_dashboard()
    except Exception as e:
        log.warning(f"Dashboard generation failed (non-critical): {e}")
