"""
ATS v8 — Central Configuration
All environment variables, model IDs, provider tier assignments, and pipeline constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Project root ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
MEMORY_DIR  = ROOT / "memory"
PROMPTS_DIR = ROOT / "prompts"
CACHE_DIR   = ROOT / "cache"
OUTPUT_DIR  = ROOT / "output"
INPUT_DIR   = ROOT / "input"
MONITORING_DIR = ROOT / "monitoring"

for d in [MEMORY_DIR, PROMPTS_DIR / "history", CACHE_DIR,
          OUTPUT_DIR, INPUT_DIR, MONITORING_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── API Keys ────────────────────────────────────────────────────────────────
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")
CEREBRAS_API_KEY    = os.getenv("CEREBRAS_API_KEY", "")
MISTRAL_API_KEY     = os.getenv("MISTRAL_API_KEY", "")

REQUIRED_KEYS = {
    "GROQ_API_KEY":       GROQ_API_KEY,
    "GEMINI_API_KEY":     GEMINI_API_KEY,
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
}

# ─── Provider base URLs (OpenAI-compatible SDK for all except Gemini) ─────────
GROQ_BASE_URL       = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CEREBRAS_BASE_URL   = "https://api.cerebras.ai/v1"
MISTRAL_BASE_URL    = "https://api.mistral.ai/v1"

# ─── Model IDs ───────────────────────────────────────────────────────────────

class Models:
    # Tier 1 — Classification, validation, lessons (8B fast)
    # llama-3.1-8b-instant: RPD=14,400 on Groq — by far the most generous free quota
    TIER1_PRIMARY   = "llama-3.1-8b-instant"          # Groq — fastest, highest RPD
    TIER1_FB1       = "llama3.1-8b"                   # Cerebras — near-instant inference
    TIER1_FB2       = "mistral-small-latest"           # Mistral — 1B tokens/month

    # Tier 2 — Long-context requirement extraction
    # gemini-2.5-flash: best free model for document understanding, 1M context window
    TIER2_PRIMARY   = "gemini-2.5-flash"               # Google — best free doc extraction
    TIER2_FB1       = "gemini-2.5-flash-lite"          # Google — higher RPD fallback
    TIER2_FB2       = "llama-3.3-70b-versatile"        # Groq — chunked fallback

    # Tier 3 — TypeScript code generation + repair
    # kimi-k2: best free codegen on Groq (1T MoE, 256K ctx)
    # codestral: Mistral's code-specialist, significantly better than general models for TS
    TIER3_PRIMARY   = "moonshotai/kimi-k2-instruct"    # Groq — best free codegen
    TIER3_FB1       = "codestral-latest"               # Mistral — code-specialized (1B tok/month)
    TIER3_FB2       = "llama-3.3-70b-versatile"        # Groq — general fallback
    TIER3_FB3       = "deepseek/deepseek-v3-2"         # OpenRouter — paid last resort

    # Tier 4 — Reasoning + ReAct planning
    # llama-3.3-70b: reliable JSON output on Groq, proven to work for ReAct planning
    # qwen3-32b requires thinking budget tokens that consume all max_tokens → empty output
    # NOTE: deepseek-r1:free and r1-distill removed — both 404 on OpenRouter as of March 2026
    TIER4_PRIMARY   = "llama-3.3-70b-versatile"         # Groq — reliable JSON output
    TIER4_FB1       = "llama-3.1-8b-instant"            # Groq — fast fallback
    TIER4_FB2       = "deepseek/deepseek-v3-2"          # OpenRouter — last resort

    # Tier 5 — Embeddings (local, unlimited)
    TIER5_EMBED     = "all-MiniLM-L6-v2"               # HuggingFace local, ~90MB

    # Tier 6 — Post-run lesson extraction (same as Tier 1)
    TIER6_PRIMARY   = TIER1_PRIMARY
    TIER6_FB1       = TIER1_FB1
    TIER6_FB2       = TIER1_FB2


# ─── Rate limit budgets per run (for router throttle logic) ──────────────────
# Used to estimate remaining daily budget and switch providers proactively.
# RPD values: Groq = from official docs. Gemini = community-reported estimates.
class DailyRPD:
    # Groq (confirmed from console.groq.com/docs/rate-limits — March 2026)
    GROQ_LLAMA_8B     = 14_400  # llama-3.1-8b-instant
    GROQ_LLAMA_70B    = 1_000   # llama-3.3-70b-versatile
    GROQ_KIMI_K2      = 1_000   # kimi-k2-instruct
    GROQ_QWQ_32B      = 1_000   # qwq-32b
    MISTRAL_CODESTRAL = 1_000   # codestral (from 1B token/month budget)
    OR_FREE_PER_MODEL = 200     # 200 RPD per :free model on OpenRouter

    # Gemini (community-reported post Dec 2025 — verify at official docs)
    # Source: multiple developer blog posts, NOT confirmed from official table
    GEMINI_25_FLASH      = 500   # gemini-2.5-flash (unconfirmed)
    GEMINI_25_FLASH_LITE = 1_000 # gemini-2.5-flash-lite (unconfirmed)
    GEMINI_25_PRO        = 100   # gemini-2.5-pro (unconfirmed)

    # Cerebras (confirmed: 1M TPD total, RPD not explicitly published)
    CEREBRAS_APPROX = 10_000    # Conservative estimate; TPD is the binding limit

    # Mistral (1B tokens/month; RPD not explicitly published)
    MISTRAL_APPROX  = 1_000     # Conservative daily estimate from monthly budget

MAX_CRAWL_PAGES: int = int(os.getenv("MAX_CRAWL_PAGES", "15"))

# ─── Approximate requests per full pipeline run (for budget planning) ────────
class RunBudget:
    """
    How many LLM API requests one full pipeline run consumes per tier.
    Used to calculate: max_daily_runs = RPD // requests_per_run
    """
    TIER1_REQUESTS = 25   # classification, validation, lessons
    TIER2_REQUESTS = 30   # 5 passes × ~6 chunks per average PDF
    TIER3_REQUESTS = 30   # ~15 codegen + ~15 repair (5 loops × 3 batches)
    TIER4_REQUESTS = 12   # ReAct planner: ~8-12 decisions per full run
    TIER6_REQUESTS = 5    # post-run lesson extraction

    @classmethod
    def max_runs_per_day(cls) -> dict:
        """Returns estimated max full pipeline runs per day per binding constraint."""
        return {
            "groq_kimi_k2":          DailyRPD.GROQ_KIMI_K2     // cls.TIER3_REQUESTS,   # ~33
            "groq_llama_70b":        DailyRPD.GROQ_LLAMA_70B   // cls.TIER2_REQUESTS,   # ~33
            "gemini_25_flash":       DailyRPD.GEMINI_25_FLASH   // cls.TIER2_REQUESTS,   # ~16 (unconfirmed)
            "openrouter_r1_free":    DailyRPD.OR_FREE_PER_MODEL // cls.TIER4_REQUESTS,   # ~16
            "groq_llama_8b":         DailyRPD.GROQ_LLAMA_8B    // cls.TIER1_REQUESTS,   # ~576
        }


# ─── Pipeline constants ───────────────────────────────────────────────────────
TARGET_COVERAGE         = int(os.getenv("TARGET_COVERAGE", "85"))
TARGET_EXEC             = int(os.getenv("TARGET_EXEC", "80"))
MAX_LOOPS               = int(os.getenv("MAX_LOOPS", "5"))
USE_ASYNC               = os.getenv("USE_ASYNC", "true").lower() == "true"
ASYNC_CONCURRENCY       = int(os.getenv("ASYNC_CONCURRENCY", "3"))

# PDF chunking — CHUNK_OVERLAP MUST remain 0.
# Overlap > 0 causes systematic duplicate extraction at every chunk boundary.
CHUNK_SIZE              = int(os.getenv("CHUNK_SIZE", "4000"))
CHUNK_OVERLAP           = 0   # Hardcoded — not configurable. See architecture docs.

SELECTOR_MIN_SCORE      = float(os.getenv("SELECTOR_MIN_SCORE", "0.4"))
CRAWL_DEPTH             = int(os.getenv("CRAWL_DEPTH", "2"))

HITL_TIMEOUT_MINUTES    = int(os.getenv("HITL_TIMEOUT_MINUTES", "60"))
HITL_SERVER_PORT        = int(os.getenv("HITL_SERVER_PORT", "9999"))

MEMORY_INJECTION_THRESHOLD  = float(os.getenv("MEMORY_INJECTION_THRESHOLD", "0.65"))
PROMPT_EVOLUTION_INTERVAL   = int(os.getenv("PROMPT_EVOLUTION_INTERVAL", "3"))

LOG_LEVEL               = os.getenv("LOG_LEVEL", "INFO")

# ─── Codegen batching ─────────────────────────────────────────────────────────
CODEGEN_BATCH_SIZE      = 10   # Requirements per Agent B batch
REPAIR_BATCH_SIZE       = 8    # Repair targets per Agent C batch (avoids 413 on free tier)

# ─── Memory confidence model ──────────────────────────────────────────────────
class Confidence:
    HUMAN_TYPED     = 1.00  # Human types any HITL prompt → instant full confidence
    CATEGORY_PROMPT = 0.60  # Category-level prompt from HITL review
    GLOBAL_PROMPT   = 0.65  # Global run prompt — highest auto-inject
    AUTO_NEW        = 0.55  # New auto-extracted lesson — below inject threshold
    CONFIRMED_HALL  = 0.70  # Confirmed hallucination (auto-detected)
    REPAIR_STRATEGY = 0.65  # Successful repair strategy
    INJECTION_MIN   = 0.65  # Minimum to appear in LLM prompts (= MEMORY_INJECTION_THRESHOLD)
    UNIVERSAL_MIN   = 0.90  # Minimum to become universal (cross-domain) lesson


# ─── Selector quality scores ──────────────────────────────────────────────────
SELECTOR_SCORES = {
    "data-testid":  1.0,
    "aria-label":   0.9,
    "id":           0.8,
    "name":         0.7,
    "type":         0.6,
    "class":        0.4,
    "positional":   0.2,  # nth-child etc — excluded
}


# ─── LLM call defaults ────────────────────────────────────────────────────────
DEFAULT_TEMPERATURE     = 0.1   # Low temp for structured extraction/codegen
PLANNING_TEMPERATURE    = 0.3   # Slightly higher for ReAct reasoning
MAX_RETRIES             = 3     # Per-provider retry before fallback
RETRY_BASE_DELAY        = 1.0   # Seconds — exponential backoff base
PROVIDER_TIMEOUT        = 60.0  # Seconds before treating as timeout


def validate_keys() -> list[str]:
    """Check required API keys are present. Returns list of missing key names."""
    return [k for k, v in REQUIRED_KEYS.items() if not v]
