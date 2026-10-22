"""
ATS v8 — Quality Monitor
Records per-run metrics, generates the final HTML report,
and flags quality anomalies (coverage regression, hallucination spike, stall).
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Optional

from app.config import OUTPUT_DIR, TARGET_COVERAGE, TARGET_EXEC
from app.schemas import EvaluationReport, DomainProfile
from app.memory.agent_memory import get_run_metrics

log = logging.getLogger(__name__)


# ─── Anomaly detection ────────────────────────────────────────────────────────

def _detect_anomalies(
    current: EvaluationReport,
    history: list[dict],
) -> list[str]:
    """Returns a list of anomaly description strings."""
    flags: list[str] = []

    if not history:
        return flags

    prev = history[-1]
    prev_cov  = prev.get("coverage_pct", 0)
    prev_exec = prev.get("exec_pct", 0)
    prev_hall = prev.get("hallucinations", 0)

    # Coverage regression
    if current.coverage_pct < prev_cov - 5:
        flags.append(
            f"Coverage regression: {prev_cov:.1f}% → {current.coverage_pct:.1f}%"
        )

    # Hallucination spike
    if current.hallucination_count > prev_hall + 3 and current.hallucination_count > 5:
        flags.append(
            f"Hallucination spike: {prev_hall} → {current.hallucination_count}"
        )

    # Below target despite previous run being above
    if prev_cov >= TARGET_COVERAGE and current.coverage_pct < TARGET_COVERAGE:
        flags.append(
            f"Coverage fell below target {TARGET_COVERAGE}% (was {prev_cov:.1f}%)"
        )

    return flags


# ─── HTML report ──────────────────────────────────────────────────────────────

def _generate_html_report(
    report: EvaluationReport,
    domain_profile: DomainProfile,
    run_id: str,
    history: list[dict],
    anomalies: list[str],
) -> Path:
    """Generate a self-contained HTML report for this run."""
    path = OUTPUT_DIR / f"report_{run_id}.html"

    # Build test result rows
    test_rows = ""
    for r in report.test_results:
        status_class = "pass" if r.passed else "fail"
        status_icon  = "✓" if r.passed else "✗"
        error_cell   = f'<span class="error-msg">{r.error[:120] if r.error else ""}</span>'
        test_rows += (
            f'<tr class="{status_class}">'
            f'<td><span class="status-icon">{status_icon}</span></td>'
            f'<td class="mono">{r.req_id}</td>'
            f'<td>{r.test_id}</td>'
            f'<td>{r.spec_file}</td>'
            f'<td>{error_cell}</td>'
            f'</tr>\n'
        )

    # Loop history rows
    loop_rows = ""
    for loop in report.loop_history:
        loop_rows += (
            f'<tr>'
            f'<td>{loop.loop_number}</td>'
            f'<td>{loop.coverage_pct:.1f}%</td>'
            f'<td>{loop.exec_pct:.1f}%</td>'
            f'<td>{loop.hallucinations}</td>'
            f'<td>{loop.action_taken}</td>'
            f'</tr>\n'
        )

    # Historical trend sparkline data
    hist_labels = json.dumps([h.get("run_id", "")[:8] for h in history[-10:]] + [run_id[:8]])
    hist_cov    = json.dumps([h.get("coverage_pct", 0) for h in history[-10:]] + [report.coverage_pct])

    # Anomaly banner
    anomaly_html = ""
    if anomalies:
        items = "".join(f"<li>{a}</li>" for a in anomalies)
        anomaly_html = f'<div class="anomaly-banner"><b>⚠ Anomalies detected:</b><ul>{items}</ul></div>'

    # Hallucination list
    hall_html = ""
    if report.hallucinated_selectors:
        hall_items = "".join(f"<li class='mono'>{s}</li>" for s in report.hallucinated_selectors)
        hall_html = f'<div class="section"><h2>Hallucinated Selectors ({report.hallucination_count})</h2><ul class="hall-list">{hall_items}</ul></div>'

    cov_color  = "#10b981" if report.coverage_pct >= TARGET_COVERAGE else "#f59e0b" if report.coverage_pct >= 60 else "#ef4444"
    exec_color = "#10b981" if report.exec_pct >= TARGET_EXEC else "#f59e0b" if report.exec_pct >= 60 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ATS v8 Report — {run_id[:8]}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:#0f1117; color:#e2e8f0; padding:0 0 40px; }}
  .header {{ background:linear-gradient(135deg,#1a1d2e 0%,#0f1117 100%);
             border-bottom:2px solid #7c3aed; padding:24px 32px; }}
  .header h1 {{ font-size:1.4rem; color:#7c3aed; font-weight:700; }}
  .header .meta {{ font-size:0.82rem; color:#64748b; margin-top:6px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px;
           padding:24px 32px; }}
  .kpi {{ background:#1a1d2e; border:1px solid #2d3748; border-radius:10px;
          padding:20px; text-align:center; }}
  .kpi-value {{ font-size:2.2rem; font-weight:700; }}
  .kpi-label {{ font-size:0.78rem; color:#64748b; margin-top:4px; text-transform:uppercase; }}
  .anomaly-banner {{ background:#78350f; border:1px solid #92400e; border-radius:8px;
                     margin:0 32px 16px; padding:14px 18px; }}
  .anomaly-banner ul {{ margin-top:6px; padding-left:20px; font-size:0.85rem; color:#fcd34d; }}
  .section {{ margin:0 32px 24px; }}
  .section h2 {{ font-size:1rem; color:#94a3b8; margin-bottom:12px; font-weight:600;
                 text-transform:uppercase; letter-spacing:0.05em; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.82rem; }}
  th {{ background:#1a1d2e; color:#64748b; padding:8px 12px; text-align:left;
        border-bottom:1px solid #2d3748; font-weight:500; }}
  td {{ padding:8px 12px; border-bottom:1px solid #1a1d2e; vertical-align:top; }}
  tr.pass td {{ color:#e2e8f0; }}
  tr.fail td {{ color:#fca5a5; }}
  tr:hover td {{ background:#1a1d2e; }}
  .status-icon {{ font-weight:700; }}
  tr.pass .status-icon {{ color:#10b981; }}
  tr.fail .status-icon {{ color:#ef4444; }}
  .mono {{ font-family:monospace; font-size:0.78rem; }}
  .error-msg {{ color:#94a3b8; font-size:0.78rem; }}
  .chart-wrap {{ background:#1a1d2e; border:1px solid #2d3748; border-radius:10px;
                 padding:20px; max-width:600px; }}
  .hall-list {{ padding-left:20px; font-size:0.82rem; color:#fca5a5; line-height:1.8; }}
</style>
</head>
<body>
<div class="header">
  <h1>ATS v8 — Test Generation Report</h1>
  <div class="meta">
    Run ID: <b>{run_id}</b> &nbsp;|&nbsp;
    App: <b>{domain_profile.base_url}</b> &nbsp;|&nbsp;
    Type: <b>{domain_profile.app_type}</b> &nbsp;|&nbsp;
    Duration: <b>{report.total_duration_s}s</b> &nbsp;|&nbsp;
    Generated: {time.strftime("%Y-%m-%d %H:%M UTC")}
  </div>
</div>

<div class="kpis">
  <div class="kpi">
    <div class="kpi-value" style="color:{cov_color}">{report.coverage_pct:.1f}%</div>
    <div class="kpi-label">Coverage (target {TARGET_COVERAGE}%)</div>
  </div>
  <div class="kpi">
    <div class="kpi-value" style="color:{exec_color}">{report.exec_pct:.1f}%</div>
    <div class="kpi-label">Pass Rate (target {TARGET_EXEC}%)</div>
  </div>
  <div class="kpi">
    <div class="kpi-value">{report.passed_tests}<span style="color:#4a5568;font-size:1.2rem">/{report.total_tests}</span></div>
    <div class="kpi-label">Tests Passed</div>
  </div>
  <div class="kpi">
    <div class="kpi-value" style="color:{'#ef4444' if report.hallucination_count > 0 else '#10b981'}">{report.hallucination_count}</div>
    <div class="kpi-label">Hallucinations</div>
  </div>
</div>

{anomaly_html}

{'<div class="section"><h2>Coverage Trend</h2><div class="chart-wrap"><canvas id="trendChart" height="100"></canvas></div></div>' if len(history) > 0 else ''}

{f'<div class="section"><h2>Repair Loop History</h2><table><thead><tr><th>Loop</th><th>Coverage</th><th>Pass%</th><th>Hallucinations</th><th>Action</th></tr></thead><tbody>{loop_rows}</tbody></table></div>' if loop_rows else ''}

<div class="section">
  <h2>Test Results ({report.total_tests} tests)</h2>
  <table>
    <thead><tr><th></th><th>Req ID</th><th>Test ID</th><th>Spec File</th><th>Error</th></tr></thead>
    <tbody>{test_rows}</tbody>
  </table>
</div>

{hall_html}

<script>
const labels = {hist_labels};
const covData = {hist_cov};
const ctx = document.getElementById('trendChart');
if (ctx) {{
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels,
      datasets: [{{
        label: 'Coverage %',
        data: covData,
        borderColor: '#7c3aed',
        backgroundColor: 'rgba(124,58,237,0.1)',
        tension: 0.3,
        fill: true,
        pointRadius: 4,
      }}]
    }},
    options: {{
      plugins: {{ legend: {{ labels: {{ color:'#94a3b8' }} }} }},
      scales: {{
        x: {{ ticks: {{ color:'#64748b' }}, grid: {{ color:'#1e293b' }} }},
        y: {{ min:0, max:100, ticks: {{ color:'#64748b' }}, grid: {{ color:'#1e293b' }} }},
      }},
    }},
  }});
}}
</script>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    return path


# ─── Main entry point ─────────────────────────────────────────────────────────

def record_and_report(
    report: Optional[EvaluationReport],
    domain_profile: DomainProfile,
    run_id: str,
) -> Optional[Path]:
    """
    Called at the end of every pipeline run.
    Detects anomalies, generates HTML report.
    Returns path to generated report or None.
    """
    if report is None:
        log.warning("Quality Monitor: no eval report to process")
        return None

    # Load historical metrics for trend analysis
    history = get_run_metrics(domain_profile.base_url, limit=20)

    # Anomaly detection
    anomalies = _detect_anomalies(report, history)
    if anomalies:
        log.warning(f"Quality Monitor: {len(anomalies)} anomaly(ies) detected")
        for a in anomalies:
            log.warning(f"  ⚠ {a}")
    else:
        log.info("Quality Monitor: no anomalies detected")

    # Generate HTML report
    report_path = _generate_html_report(
        report=report,
        domain_profile=domain_profile,
        run_id=run_id,
        history=history,
        anomalies=anomalies,
    )

    log.info(f"Quality Monitor: report saved → {report_path.name}")

    # Generate monitoring dashboard
    try:
        from app.core.monitoring_dashboard import update_dashboard
        update_dashboard()
        log.info("Quality Monitor: monitoring dashboard updated")
    except Exception as e:
        log.debug(f"Quality Monitor: dashboard update skipped: {e}")

    # Print summary to terminal
    target_met = report.targets_met
    status = "✓ TARGETS MET" if target_met else "⚠ TARGETS NOT MET"
    print(f"\n{'='*60}")
    print(f"  {status}")
    print(f"  Coverage: {report.coverage_pct:.1f}%  |  Pass rate: {report.exec_pct:.1f}%")
    print(f"  Tests: {report.passed_tests}/{report.total_tests} passed")
    if report.hallucination_count:
        print(f"  Hallucinations: {report.hallucination_count}")
    if anomalies:
        print(f"  ⚠ Anomalies: {len(anomalies)}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}\n")

    return report_path
