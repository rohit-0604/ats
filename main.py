"""
ATS v8 — Autonomous Test System
Main CLI entry point.

Usage:
  python main.py run --url https://example.com --pdf requirements.pdf
  python main.py run --url https://example.com --pdf reqs.pdf --interactive
  python main.py run --url https://example.com --pdf reqs.pdf --auto
  python main.py resume --run-id abc123
  python main.py list
  python main.py validate --pdf requirements.pdf

Full options: python main.py --help
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

# ─── Bootstrap logging before any app imports ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ats.main")

# ─── Validate environment early ──────────────────────────────────────────────
from app.config import validate_keys, ROOT, INPUT_DIR, OUTPUT_DIR


def _print_banner() -> None:
    print("""
╔══════════════════════════════════════════════════════════════╗
║          ATS v8 — Autonomous Test System                     ║
║  PDF requirements → Playwright TypeScript tests              ║
╚══════════════════════════════════════════════════════════════╝""")


def _generate_run_id() -> str:
    """Generate short human-readable run ID: ats_YYYYMMDD_HHMMSS_short-uuid"""
    ts   = time.strftime("%Y%m%d_%H%M%S")
    uid  = uuid.uuid4().hex[:6]
    return f"ats_{ts}_{uid}"


def _load_resource(url: str) -> dict:
    """
    Load resource.json from input/ directory or project root.
    resource.json configures auth, skip_routes, and other app-specific settings.
    Falls back to minimal default if not found.
    """
    candidates = [
        INPUT_DIR / "resource.json",
        ROOT / "resource.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                log.info(f"Resource config loaded from {path}")
                return data
            except Exception as e:
                log.warning(f"Failed to parse resource.json at {path}: {e}")

    log.info("No resource.json found — using default (no auth, no skip routes)")
    return {
        "base_url": url,
        "auth": {"type": "none"},
        "skip_routes": [],
    }


def _find_pdf(pdf_arg: Optional[str]) -> Optional[str]:
    """
    Resolves PDF path. Checks:
    1. Exact path as given
    2. input/ directory
    """
    if not pdf_arg:
        return None
    p = Path(pdf_arg)
    if p.exists():
        return str(p)
    in_input = INPUT_DIR / p.name
    if in_input.exists():
        return str(in_input)
    log.error(f"PDF not found: {pdf_arg}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Commands
# ══════════════════════════════════════════════════════════════════════════════

def cmd_run(args: argparse.Namespace) -> int:
    """Execute a full pipeline run."""
    _print_banner()

    # Validate API keys
    missing = validate_keys()
    if missing:
        log.warning(f"Missing API keys: {missing}. Some providers will be skipped.")

    # Resolve inputs
    pdf_path = _find_pdf(args.pdf)
    if not pdf_path and not args.requirements:
        log.error("Either --pdf or --requirements must be provided")
        return 1

    resource = _load_resource(args.url)

    run_id = _generate_run_id()
    print(f"\n  Run ID: {run_id}")
    print(f"  URL:    {args.url}")
    print(f"  PDF:    {pdf_path or 'N/A (using saved requirements)'}")
    print(f"  Mode:   {'interactive' if args.interactive else 'auto' if args.auto else 'standard'}\n")

    # Determine run mode
    run_mode = "full"
    if args.extract_only:
        run_mode = "extract"
    elif args.codegen_only:
        run_mode = "codegen"

    from app.core.react_controller import run_pipeline
    try:
        final_state = run_pipeline(
            run_id=run_id,
            base_url=args.url,
            pdf_path=pdf_path,
            requirements_path=args.requirements,
            run_mode=run_mode,
            interactive=args.interactive,
            auto_mode=args.auto,
            force_extract=args.force_extract,
            force_crawl=args.force_crawl,
            resource=resource,
        )
    except KeyboardInterrupt:
        print("\n\nRun interrupted. Resume with:")
        print(f"  python main.py resume --run-id {run_id}\n")
        return 130

    # Print output paths
    if final_state.get("eval_report"):
        from app.schemas import EvaluationReport
        report = EvaluationReport(**final_state["eval_report"])
        print(f"\n  ✓ Run complete: coverage={report.coverage_pct:.1f}%  pass={report.exec_pct:.1f}%")

    print(f"  Outputs: {OUTPUT_DIR}/")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a previously interrupted run from its last checkpoint."""
    _print_banner()
    print(f"\n  Resuming run: {args.run_id}\n")
    from app.core.react_controller import resume_pipeline
    try:
        final_state = resume_pipeline(args.run_id)
    except Exception as e:
        log.error(f"Resume failed: {e}")
        return 1
    print(f"  ✓ Resumed run complete")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all previous runs in the checkpoint database."""
    from app.core.react_controller import list_runs
    runs = list_runs()
    if not runs:
        print("No previous runs found.")
        return 0
    print(f"\n{'Run ID':<30} {'Last Checkpoint'}")
    print("-" * 55)
    for r in runs:
        print(f"{r['run_id']:<30} {r['checkpoint']}")
    print()
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a PDF file without running the full pipeline."""
    from app.core.pdf_extractor import validate_pdf, extract_text, chunk_text
    pdf_path = _find_pdf(args.pdf)
    if not pdf_path:
        return 1
    ok, err = validate_pdf(pdf_path)
    if not ok:
        print(f"✗ Invalid PDF: {err}")
        return 1
    print(f"✓ Valid PDF: {pdf_path}")
    text = extract_text(pdf_path)
    chunks = chunk_text(text)
    print(f"  Pages of text: {len(text.split(chr(12)))} sections")
    print(f"  Characters: {len(text):,}")
    print(f"  Chunks: {len(chunks)} (overlap=0)")
    print(f"\nFirst 400 chars:\n{text[:400]}")
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    """Show which API keys are configured."""
    from app.config import validate_keys, GROQ_API_KEY, GEMINI_API_KEY
    import os

    key_vars = [
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
    ]
    print("\nAPI Key Status:")
    for k in key_vars:
        val = os.getenv(k, "")
        status = f"✓ {val[:8]}..." if val else "✗ NOT SET"
        print(f"  {k:<25} {status}")

    missing = validate_keys()
    if missing:
        print(f"\n  ⚠ Missing required keys: {missing}")
        print("  Add them to your .env file (see .env.example)")
    else:
        print("\n  ✓ All required keys are set")
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Argument parser
# ══════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ats",
        description="ATS v8 — Autonomous Test System: PDF → Playwright TypeScript tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run --url https://app.example.com --pdf requirements.pdf
  python main.py run --url https://app.example.com --pdf reqs.pdf --interactive
  python main.py run --url https://app.example.com --pdf reqs.pdf --auto
  python main.py run --url https://app.example.com --requirements saved.json
  python main.py resume --run-id ats_20260101_120000_abc123
  python main.py list
  python main.py validate --pdf requirements.pdf
  python main.py keys
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ──
    run_p = sub.add_parser("run", help="Start a new pipeline run")
    run_p.add_argument("--url",          required=True, help="Target application URL")
    run_p.add_argument("--pdf",          help="Path to requirements PDF")
    run_p.add_argument("--requirements", help="Path to saved requirements JSON (skips extraction)")
    run_p.add_argument("--interactive",  action="store_true",
                       help="Pause for HITL review at Phases 1, 2, 3")
    run_p.add_argument("--auto",         action="store_true",
                       help="Fully autonomous — no HITL pauses (default: standard)")
    run_p.add_argument("--force-extract", action="store_true",
                       help="Re-extract requirements even if PDF cache exists")
    run_p.add_argument("--force-crawl",   action="store_true",
                       help="Re-crawl routes even if selector cache exists")
    run_p.add_argument("--extract-only",  action="store_true",
                       help="Only run Agent A (extraction), then stop")
    run_p.add_argument("--codegen-only",  action="store_true",
                       help="Only run Agent B (codegen) from saved requirements")
    run_p.add_argument("--debug",         action="store_true",
                       help="Set log level to DEBUG")

    # ── resume ──
    res_p = sub.add_parser("resume", help="Resume an interrupted run")
    res_p.add_argument("--run-id", required=True, help="Run ID to resume")

    # ── list ──
    sub.add_parser("list", help="List all previous runs")

    # ── validate ──
    val_p = sub.add_parser("validate", help="Validate a PDF file")
    val_p.add_argument("--pdf", required=True, help="Path to PDF file")

    # ── keys ──
    sub.add_parser("keys", help="Show API key configuration status")

    return parser


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    # Load .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        env_path = ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            log.debug(f".env loaded from {env_path}")
    except ImportError:
        pass

    parser = _build_parser()
    args = parser.parse_args()

    # Debug logging
    if getattr(args, "debug", False):
        logging.getLogger().setLevel(logging.DEBUG)

    dispatch = {
        "run":      cmd_run,
        "resume":   cmd_resume,
        "list":     cmd_list,
        "validate": cmd_validate,
        "keys":     cmd_keys,
    }

    handler = dispatch.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
