"""
ATS v8 — HITL Manager
Handles all three human-in-the-loop review pauses.

Phase 1: Requirements review  — browser HTML page + http.server POST endpoint
Phase 2: Test code review      — browser HTML page + http.server POST endpoint
Phase 3: Results review        — terminal (rich + questionary), fast decisions

Auto-approval logic (confidence-gated):
  >= 0.90  → approve silently
  >= 0.75  → approve with yellow badge
  0.65-0.74 → flag for review queue
  < 0.65   → must review
  gap_analysis=True → always review regardless of confidence
"""

from __future__ import annotations
import json
import logging
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

from app.config import HITL_TIMEOUT_MINUTES, HITL_SERVER_PORT, OUTPUT_DIR, Confidence
from app.schemas import (
    RequirementBundle, TestSuite, EvaluationReport,
    FeedbackResult, ItemFeedback,
)

log = logging.getLogger(__name__)

AUTO_APPROVE_SILENT   = 0.90
AUTO_APPROVE_FLAGGED  = 0.75
REVIEW_REQUIRED_BELOW = 0.65


# ══════════════════════════════════════════════════════════════════════════════
# http.server feedback endpoint
# ══════════════════════════════════════════════════════════════════════════════

class _FeedbackHandler(BaseHTTPRequestHandler):
    """Receives JSON POST from browser 'Export & Continue' button."""

    feedback_data: Optional[dict] = None  # class-level shared state
    received_event: threading.Event = threading.Event()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            _FeedbackHandler.feedback_data = json.loads(body.decode("utf-8"))
            _FeedbackHandler.received_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"received"}')
        except Exception as e:
            self.send_response(500)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default request logging


def _wait_for_feedback(
    html_path: Path,
    run_id: str,
    phase: str,
    timeout_minutes: int = HITL_TIMEOUT_MINUTES,
) -> Optional[dict]:
    """
    Start http.server, open HTML page in browser, wait for POST feedback.
    Returns feedback dict or None on timeout.
    """
    # Reset shared state
    _FeedbackHandler.feedback_data = None
    _FeedbackHandler.received_event = threading.Event()

    server = HTTPServer(("localhost", HITL_SERVER_PORT), _FeedbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    log.info(f"HITL: feedback server started on port {HITL_SERVER_PORT}")

    # Open browser
    try:
        webbrowser.open(html_path.as_uri())
        log.info(f"HITL: opened {html_path.name} in browser")
    except Exception:
        log.warning(f"HITL: could not open browser. Open manually: {html_path}")

    # Also watch for output file (belt-and-suspenders)
    feedback_file = OUTPUT_DIR / f"feedback_{run_id}_{phase}.json"

    timeout_s = timeout_minutes * 60
    start = time.time()

    print(f"\n{'='*60}")
    print(f"  HITL {phase.upper()} — Review required")
    print(f"  Browser page: {html_path.name}")
    print(f"  Click 'Export & Continue' when done.")
    print(f"  Timeout: {timeout_minutes} min  |  Ctrl+C to skip")
    print(f"{'='*60}\n")

    try:
        received = _FeedbackHandler.received_event.wait(timeout=timeout_s)
    except KeyboardInterrupt:
        log.info("HITL: skipped by Ctrl+C")
        received = False

    server.shutdown()

    if received and _FeedbackHandler.feedback_data:
        data = _FeedbackHandler.feedback_data
        # Persist feedback JSON
        feedback_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log.info(f"HITL: feedback received and saved to {feedback_file.name}")
        return data

    # Fallback: check if file was written by watchdog
    if feedback_file.exists():
        try:
            return json.loads(feedback_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    log.warning(f"HITL: timed out after {timeout_minutes} min — continuing with auto-approval")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Auto-approval helpers
# ══════════════════════════════════════════════════════════════════════════════

def _auto_approve_requirements(bundle: RequirementBundle) -> FeedbackResult:
    """
    Apply confidence-gated auto-approval to all requirements.
    Returns a FeedbackResult with all items pre-decided.
    """
    items = []
    for req in bundle.requirements:
        if req.gap_analysis:
            # Gap analysis always needs review — approve at medium confidence
            items.append(ItemFeedback(item_id=req.req_id, approved=True))
            continue

        if req.confidence >= AUTO_APPROVE_SILENT:
            items.append(ItemFeedback(item_id=req.req_id, approved=True))
        elif req.confidence >= AUTO_APPROVE_FLAGGED:
            items.append(ItemFeedback(item_id=req.req_id, approved=True))
        else:
            # Below threshold — approve anyway in auto mode, but flag
            items.append(ItemFeedback(item_id=req.req_id, approved=True))

    return FeedbackResult(
        phase="phase1",
        run_id=bundle.run_id,
        items=items,
        timed_out=True,
    )


def _auto_approve_tests(suite: TestSuite) -> FeedbackResult:
    items = [
        ItemFeedback(item_id=t.test_id, approved=True)
        for t in suite.tests
    ]
    return FeedbackResult(
        phase="phase2",
        run_id=suite.run_id,
        items=items,
        timed_out=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# HTML page generators
# ══════════════════════════════════════════════════════════════════════════════

def _generate_phase1_html(bundle: RequirementBundle, run_id: str) -> Path:
    """Generate the requirements review HTML page."""
    path = OUTPUT_DIR / f"review_{run_id}_phase1.html"

    reqs_json = json.dumps(
        [r.model_dump() for r in bundle.requirements],
        indent=2, ensure_ascii=False
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ATS v8 — Requirements Review [{run_id[:8]}]</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background: #0f1117; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: #1a1d2e; border-bottom: 1px solid #2d3748;
             padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 1.1rem; color: #7c3aed; font-weight: 600; }}
  .stats {{ display: flex; gap: 20px; font-size: 0.85rem; color: #94a3b8; }}
  .controls {{ background: #1a1d2e; border-bottom: 1px solid #2d3748;
               padding: 12px 24px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
  .filter-btn {{ background: #2d3748; border: 1px solid #4a5568; color: #e2e8f0;
                 padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.82rem; }}
  .filter-btn.active {{ background: #7c3aed; border-color: #7c3aed; }}
  .batch-bar {{ background: #1a1d2e; border-bottom: 1px solid #2d3748;
                padding: 10px 24px; display: flex; gap: 10px; }}
  .batch-btn {{ background: #2d3748; border: 1px solid #4a5568; color: #e2e8f0;
                padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.82rem; }}
  .global-prompt {{ background: #1a1d2e; border-bottom: 2px solid #7c3aed;
                    padding: 12px 24px; display: flex; gap: 10px; align-items: center; }}
  .global-prompt input {{ flex: 1; background: #2d3748; border: 1px solid #4a5568;
                          color: #e2e8f0; padding: 8px 12px; border-radius: 6px;
                          font-size: 0.85rem; }}
  .cards {{ padding: 16px 24px; display: flex; flex-direction: column; gap: 10px; }}
  .card {{ background: #1a1d2e; border: 1px solid #2d3748; border-radius: 8px; padding: 14px; }}
  .card.approved {{ border-left: 3px solid #10b981; }}
  .card.rejected {{ border-left: 3px solid #ef4444; opacity: 0.6; }}
  .card.gap {{ border-left: 3px solid #f59e0b; }}
  .card.low-conf {{ border-left: 3px solid #ef4444; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
  .req-id {{ font-family: monospace; font-size: 0.75rem; color: #64748b; white-space: nowrap; }}
  .req-title {{ font-weight: 600; font-size: 0.95rem; flex: 1; }}
  .badges {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 500; white-space: nowrap; }}
  .badge-green  {{ background: #065f46; color: #6ee7b7; }}
  .badge-yellow {{ background: #78350f; color: #fcd34d; }}
  .badge-red    {{ background: #7f1d1d; color: #fca5a5; }}
  .badge-purple {{ background: #4c1d95; color: #c4b5fd; }}
  .desc {{ font-size: 0.83rem; color: #94a3b8; margin-top: 8px; line-height: 1.5; }}
  .card-actions {{ display: flex; gap: 8px; margin-top: 10px; align-items: center; }}
  .btn-approve {{ background: #065f46; color: #6ee7b7; border: 1px solid #10b981;
                  padding: 5px 14px; border-radius: 5px; cursor: pointer; font-size: 0.82rem; }}
  .btn-reject  {{ background: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444;
                  padding: 5px 14px; border-radius: 5px; cursor: pointer; font-size: 0.82rem; }}
  .prompt-input {{ flex: 1; background: #2d3748; border: 1px solid #4a5568;
                   color: #e2e8f0; padding: 5px 10px; border-radius: 5px;
                   font-size: 0.82rem; }}
  .export-bar {{ position: fixed; bottom: 0; left: 0; right: 0;
                 background: #1a1d2e; border-top: 1px solid #2d3748;
                 padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; }}
  .export-btn {{ background: #7c3aed; color: white; border: none;
                 padding: 10px 28px; border-radius: 8px; cursor: pointer;
                 font-size: 0.95rem; font-weight: 600; }}
  .export-btn:hover {{ background: #6d28d9; }}
  .status-msg {{ font-size: 0.85rem; color: #94a3b8; }}
  .hidden {{ display: none !important; }}
  input[type=text], textarea {{ outline: none; }}
  input[type=text]:focus, textarea:focus {{ border-color: #7c3aed; }}
  body {{ padding-bottom: 60px; }}
</style>
</head>
<body>

<div class="header">
  <h1>ATS v8 — Requirements Review</h1>
  <div class="stats">
    <span>Run: <b>{run_id[:8]}</b></span>
    <span id="stat-total">Total: {len(bundle.requirements)}</span>
    <span id="stat-approved">Approved: 0</span>
    <span id="stat-rejected">Rejected: 0</span>
  </div>
</div>

<div class="global-prompt">
  <span style="color:#7c3aed;font-size:0.82rem;white-space:nowrap">Global prompt:</span>
  <input type="text" id="global-prompt" placeholder="Instruction for ALL agents this run...">
</div>

<div class="controls">
  <button class="filter-btn active" onclick="setFilter('all')">All</button>
  <button class="filter-btn" onclick="setFilter('review')">Needs Review</button>
  <button class="filter-btn" onclick="setFilter('gap')">Gap Analysis</button>
  <button class="filter-btn" onclick="setFilter('low')">Low Confidence</button>
</div>

<div class="batch-bar">
  <button class="batch-btn" onclick="approveAllVisible()">✓ Approve All Visible</button>
  <button class="batch-btn" onclick="rejectAllVisible()">✗ Reject All Visible</button>
</div>

<div class="cards" id="cards"></div>

<div class="export-bar">
  <span class="status-msg" id="export-status">Review items then click Export.</span>
  <button class="export-btn" onclick="exportFeedback()">Export &amp; Continue →</button>
</div>

<script>
const REQUIREMENTS = {reqs_json};
const PORT = {HITL_SERVER_PORT};
let state = {{}};
let currentFilter = 'all';

REQUIREMENTS.forEach(r => {{
  state[r.req_id] = {{
    approved: r.confidence >= 0.75 && !r.gap_analysis,
    rejected: false,
    run_prompt: '',
    memory_note: '',
  }};
}});

function renderCards() {{
  const container = document.getElementById('cards');
  container.innerHTML = '';
  REQUIREMENTS.forEach(r => {{
    const s = state[r.req_id];
    const isGap = r.gap_analysis;
    const isLow = r.confidence < 0.65;
    const needsReview = isGap || isLow || (!s.approved && !s.rejected);

    if (currentFilter === 'review' && !needsReview) return;
    if (currentFilter === 'gap'    && !isGap) return;
    if (currentFilter === 'low'    && !isLow) return;

    const cls = s.approved ? 'approved' : s.rejected ? 'rejected' : isGap ? 'gap' : isLow ? 'low-conf' : '';
    const confPct = Math.round(r.confidence * 100);
    const confBadge = confPct >= 90 ? 'badge-green' : confPct >= 75 ? 'badge-yellow' : 'badge-red';

    container.innerHTML += `
      <div class="card ${{cls}}" id="card-${{r.req_id}}">
        <div class="card-header">
          <span class="req-id">${{r.req_id}}</span>
          <span class="req-title">${{r.title}}</span>
          <div class="badges">
            <span class="badge ${{confBadge}}">${{confPct}}%</span>
            ${{r.priority === 'high' ? '<span class="badge badge-red">HIGH</span>' : ''}}
            ${{isGap ? '<span class="badge badge-yellow">GAP</span>' : ''}}
            ${{r.req_type ? `<span class="badge" style="background:#1e293b;color:#94a3b8">${{r.req_type}}</span>` : ''}}
          </div>
        </div>
        <div class="desc">${{r.description}}</div>
        <div class="card-actions">
          <button class="btn-approve" onclick="approve('${{r.req_id}}')">✓ Approve</button>
          <button class="btn-reject"  onclick="reject('${{r.req_id}}')">✗ Reject</button>
          <input class="prompt-input" type="text" id="prompt-${{r.req_id}}"
                 placeholder="Instruction to Agent B for this test..."
                 value="${{s.run_prompt}}"
                 oninput="state['${{r.req_id}}'].run_prompt=this.value">
        </div>
      </div>`;
  }});
  updateStats();
}}

function approve(id) {{
  state[id].approved = true; state[id].rejected = false;
  document.getElementById('card-' + id)?.classList.replace('rejected','approved') ||
  document.getElementById('card-' + id)?.classList.add('approved');
  renderCards();
}}
function reject(id) {{
  state[id].rejected = true; state[id].approved = false;
  renderCards();
}}
function approveAllVisible() {{
  document.querySelectorAll('.card').forEach(c => {{
    const id = c.id.replace('card-','');
    if (id) {{ state[id] = {{...state[id], approved:true, rejected:false}}; }}
  }});
  renderCards();
}}
function rejectAllVisible() {{
  document.querySelectorAll('.card').forEach(c => {{
    const id = c.id.replace('card-','');
    if (id) {{ state[id] = {{...state[id], rejected:true, approved:false}}; }}
  }});
  renderCards();
}}
function setFilter(f) {{
  currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  renderCards();
}}
function updateStats() {{
  const approved = Object.values(state).filter(s => s.approved).length;
  const rejected = Object.values(state).filter(s => s.rejected).length;
  document.getElementById('stat-approved').textContent = 'Approved: ' + approved;
  document.getElementById('stat-rejected').textContent = 'Rejected: ' + rejected;
}}

async function exportFeedback() {{
  const items = REQUIREMENTS.map(r => ({{
    item_id:     r.req_id,
    approved:    state[r.req_id].approved,
    rejected:    state[r.req_id].rejected,
    run_prompt:  state[r.req_id].run_prompt || null,
    memory_note: state[r.req_id].memory_note || null,
  }}));
  const payload = {{
    phase: 'phase1',
    global_prompt: document.getElementById('global-prompt').value || null,
    items,
  }};
  try {{
    const resp = await fetch('http://localhost:' + PORT + '/feedback', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload),
    }});
    if (resp.ok) {{
      document.getElementById('export-status').textContent = '✓ Pipeline continuing...';
      document.getElementById('export-status').style.color = '#10b981';
    }}
  }} catch(e) {{
    document.getElementById('export-status').textContent = 'Server not reachable — save manually.';
  }}
}}

renderCards();
</script>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    return path


def _generate_phase2_html(suite: TestSuite, bundle: RequirementBundle, run_id: str) -> Path:
    """Generate the test code review HTML page."""
    path = OUTPUT_DIR / f"review_{run_id}_phase2.html"

    # Build req_id → title lookup
    req_titles = {r.req_id: r.title for r in bundle.requirements}

    tests_json = json.dumps(
        [t.model_dump() for t in suite.tests],
        indent=2, ensure_ascii=False
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ATS v8 — Test Review [{run_id[:8]}]</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:#0f1117; color:#e2e8f0; padding-bottom:60px; }}
  .header {{ background:#1a1d2e; border-bottom:1px solid #2d3748;
             padding:16px 24px; display:flex; justify-content:space-between; align-items:center; }}
  .header h1 {{ font-size:1.1rem; color:#7c3aed; font-weight:600; }}
  .batch-bar {{ background:#1a1d2e; border-bottom:1px solid #2d3748;
                padding:10px 24px; display:flex; gap:10px; }}
  .batch-btn {{ background:#2d3748; border:1px solid #4a5568; color:#e2e8f0;
                padding:6px 14px; border-radius:6px; cursor:pointer; font-size:0.82rem; }}
  .cards {{ padding:16px 24px; display:flex; flex-direction:column; gap:10px; }}
  .card {{ background:#1a1d2e; border:1px solid #2d3748; border-radius:8px; padding:14px; }}
  .card.approved {{ border-left:3px solid #10b981; }}
  .card.rejected  {{ border-left:3px solid #ef4444; opacity:0.6; }}
  .card-header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px; }}
  .test-id {{ font-family:monospace; font-size:0.75rem; color:#64748b; }}
  .test-title {{ font-weight:600; font-size:0.92rem; flex:1; }}
  .req-ref {{ font-size:0.78rem; color:#7c3aed; background:#1e1b4b; padding:2px 8px; border-radius:4px; }}
  pre {{ background:#0a0c14; border:1px solid #1e293b; border-radius:6px;
         padding:12px; font-size:0.78rem; overflow-x:auto; max-height:300px;
         overflow-y:auto; color:#e2e8f0; font-family:'Fira Code',monospace; white-space:pre; }}
  .card-actions {{ display:flex; gap:8px; margin-top:10px; align-items:center; }}
  .btn-approve {{ background:#065f46; color:#6ee7b7; border:1px solid #10b981;
                  padding:5px 14px; border-radius:5px; cursor:pointer; font-size:0.82rem; }}
  .btn-reject  {{ background:#7f1d1d; color:#fca5a5; border:1px solid #ef4444;
                  padding:5px 14px; border-radius:5px; cursor:pointer; font-size:0.82rem; }}
  .prompt-input {{ flex:1; background:#2d3748; border:1px solid #4a5568;
                   color:#e2e8f0; padding:5px 10px; border-radius:5px; font-size:0.82rem; }}
  .hall-warn {{ background:#78350f; color:#fcd34d; border-radius:4px;
                padding:4px 10px; font-size:0.78rem; margin-top:6px; }}
  .export-bar {{ position:fixed; bottom:0; left:0; right:0; background:#1a1d2e;
                 border-top:1px solid #2d3748; padding:12px 24px;
                 display:flex; justify-content:space-between; align-items:center; }}
  .export-btn {{ background:#7c3aed; color:white; border:none;
                 padding:10px 28px; border-radius:8px; cursor:pointer;
                 font-size:0.95rem; font-weight:600; }}
  .status-msg {{ font-size:0.85rem; color:#94a3b8; }}
</style>
</head>
<body>
<div class="header">
  <h1>ATS v8 — Test Code Review</h1>
  <div style="font-size:0.85rem;color:#94a3b8">
    Run: <b>{run_id[:8]}</b> &nbsp;|&nbsp; {len(suite.tests)} tests
  </div>
</div>
<div class="batch-bar">
  <button class="batch-btn" onclick="approveAll()">✓ Approve All</button>
  <button class="batch-btn" onclick="rejectAll()">✗ Reject All</button>
</div>
<div class="cards" id="cards"></div>
<div class="export-bar">
  <span class="status-msg" id="export-status">Review tests then click Export.</span>
  <button class="export-btn" onclick="exportFeedback()">Export &amp; Continue →</button>
</div>

<script>
const TESTS = {tests_json};
const REQ_TITLES = {json.dumps(req_titles)};
const PORT = {HITL_SERVER_PORT};
let state = {{}};
TESTS.forEach(t => {{ state[t.test_id] = {{ approved:true, rejected:false, run_prompt:'' }}; }});

function renderCards() {{
  const c = document.getElementById('cards');
  c.innerHTML = '';
  TESTS.forEach(t => {{
    const s = state[t.test_id];
    const cls = s.approved ? 'approved' : s.rejected ? 'rejected' : '';
    const halls = t.hallucinated && t.hallucinated.length > 0;
    c.innerHTML += `
      <div class="card ${{cls}}" id="card-${{t.test_id}}">
        <div class="card-header">
          <span class="test-id">${{t.test_id}}</span>
          <span class="test-title">${{t.title}}</span>
          <span class="req-ref">${{t.req_id}} — ${{REQ_TITLES[t.req_id] || ''}}</span>
        </div>
        ${{halls ? `<div class="hall-warn">⚠ Hallucinated selectors: ${{t.hallucinated.join(', ')}}</div>` : ''}}
        <pre><code>${{escapeHtml(t.ts_code)}}</code></pre>
        <div class="card-actions">
          <button class="btn-approve" onclick="approve('${{t.test_id}}')">✓ Approve</button>
          <button class="btn-reject"  onclick="reject('${{t.test_id}}')">✗ Reject</button>
          <input class="prompt-input" type="text" id="prompt-${{t.test_id}}"
                 placeholder="Repair instruction..."
                 oninput="state['${{t.test_id}}'].run_prompt=this.value">
        </div>
      </div>`;
  }});
}}
function escapeHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}
function approve(id) {{ state[id]={{approved:true,rejected:false,run_prompt:state[id].run_prompt}}; renderCards(); }}
function reject(id)  {{ state[id]={{rejected:true,approved:false,run_prompt:state[id].run_prompt}}; renderCards(); }}
function approveAll() {{ Object.keys(state).forEach(k=>{{state[k].approved=true;state[k].rejected=false;}}); renderCards(); }}
function rejectAll()  {{ Object.keys(state).forEach(k=>{{state[k].rejected=true;state[k].approved=false;}}); renderCards(); }}

async function exportFeedback() {{
  const items = TESTS.map(t => ({{
    item_id: t.test_id,
    approved: state[t.test_id].approved,
    rejected: state[t.test_id].rejected,
    run_prompt: state[t.test_id].run_prompt || null,
  }}));
  try {{
    const resp = await fetch('http://localhost:' + PORT + '/feedback', {{
      method:'POST', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{ phase:'phase2', items }}),
    }});
    if (resp.ok) {{
      document.getElementById('export-status').textContent = '✓ Pipeline continuing...';
      document.getElementById('export-status').style.color = '#10b981';
    }}
  }} catch(e) {{
    document.getElementById('export-status').textContent = 'Server not reachable.';
  }}
}}

renderCards();
</script>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    return path


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Terminal (rich + questionary)
# ══════════════════════════════════════════════════════════════════════════════

def _phase3_terminal(report: EvaluationReport, run_id: str) -> FeedbackResult:
    """Quick terminal review of eval results — binary decisions, no browser."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        import questionary
    except ImportError:
        log.warning("HITL Phase 3: rich/questionary not installed, skipping")
        return FeedbackResult(phase="phase3", run_id=run_id, timed_out=True)

    console = Console()

    # Summary panel
    console.print(Panel(
        f"[bold]Coverage:[/bold] {report.coverage_pct:.1f}%  "
        f"[bold]Pass rate:[/bold] {report.exec_pct:.1f}%  "
        f"[bold]Hallucinations:[/bold] {report.hallucination_count}  "
        f"[bold]Tests:[/bold] {report.passed_tests}/{report.total_tests}",
        title=f"[purple]Run {run_id[:8]} — Results",
        border_style="purple",
    ))

    # Loop history table
    if report.loop_history:
        t = Table(title="Loop History", border_style="dim")
        t.add_column("Loop", style="dim")
        t.add_column("Coverage")
        t.add_column("Pass%")
        t.add_column("Halls")
        t.add_column("Action")
        for loop in report.loop_history:
            t.add_row(
                str(loop.loop_number),
                f"{loop.coverage_pct:.1f}%",
                f"{loop.exec_pct:.1f}%",
                str(loop.hallucinations),
                loop.action_taken,
            )
        console.print(t)

    # Failing tests
    failing = [r for r in report.test_results if not r.passed]
    if failing:
        console.print(f"\n[red]Failing tests ({len(failing)}):[/red]")
        for r in failing[:10]:
            console.print(f"  [dim]{r.req_id}[/dim] — {r.error or 'unknown error'}")

    items = []
    global_prompt = None

    try:
        add_global = questionary.confirm(
            "Add a global instruction for the next run?", default=False
        ).ask()
        if add_global:
            global_prompt = questionary.text("Global instruction:").ask()

        if failing:
            mark_infra = questionary.confirm(
                f"Mark {len(failing)} failing tests as infrastructure-dependent (skip)?",
                default=False
            ).ask()
            if mark_infra:
                for r in failing:
                    items.append(ItemFeedback(item_id=r.test_id, approved=False, rejected=True))

    except (KeyboardInterrupt, Exception):
        pass

    return FeedbackResult(
        phase="phase3",
        run_id=run_id,
        items=items,
        global_prompt=global_prompt,
        submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Public entry points
# ══════════════════════════════════════════════════════════════════════════════

def run_hitl_phase1(
    bundle: RequirementBundle,
    run_id: str,
    auto_mode: bool = False,
) -> FeedbackResult:
    if auto_mode:
        log.info("HITL Phase 1: auto mode — confidence-gated approval")
        return _auto_approve_requirements(bundle)

    html_path = _generate_phase1_html(bundle, run_id)
    raw = _wait_for_feedback(html_path, run_id, "phase1")

    if raw is None:
        return _auto_approve_requirements(bundle)

    items = [
        ItemFeedback(
            item_id=i.get("item_id", ""),
            approved=i.get("approved", False),
            rejected=i.get("rejected", False),
            run_prompt=i.get("run_prompt"),
            memory_note=i.get("memory_note"),
        )
        for i in raw.get("items", [])
        if i.get("item_id")
    ]

    return FeedbackResult(
        phase="phase1",
        run_id=run_id,
        items=items,
        global_prompt=raw.get("global_prompt"),
        category_prompts=raw.get("category_prompts", {}),
        submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def run_hitl_phase2(
    suite: TestSuite,
    bundle: RequirementBundle,
    run_id: str,
    auto_mode: bool = False,
) -> FeedbackResult:
    if auto_mode:
        return _auto_approve_tests(suite)

    html_path = _generate_phase2_html(suite, bundle, run_id)
    raw = _wait_for_feedback(html_path, run_id, "phase2")

    if raw is None:
        return _auto_approve_tests(suite)

    items = [
        ItemFeedback(
            item_id=i.get("item_id", ""),
            approved=i.get("approved", True),
            rejected=i.get("rejected", False),
            run_prompt=i.get("run_prompt"),
        )
        for i in raw.get("items", [])
        if i.get("item_id")
    ]
    return FeedbackResult(
        phase="phase2", run_id=run_id, items=items,
        submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def run_hitl_phase3(
    report: EvaluationReport,
    run_id: str,
    auto_mode: bool = False,
) -> FeedbackResult:
    if auto_mode:
        return FeedbackResult(phase="phase3", run_id=run_id, timed_out=True)
    return _phase3_terminal(report, run_id)
