"""
ATS v8 — Persistent Memory System
Unified API for ChromaDB (semantic) and JSON (structured) memory.
Three-scope partitioning: universal / app_type:{type} / domain:{base_url}
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Optional, Any
import chromadb
from chromadb.config import Settings

from app.config import MEMORY_DIR, Confidence, MEMORY_INJECTION_THRESHOLD

log = logging.getLogger(__name__)

# ─── ChromaDB setup ───────────────────────────────────────────────────────────
_chroma_client: Optional[chromadb.ClientAPI] = None

def _get_chroma() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=str(MEMORY_DIR / "chroma_db"),
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_collection(name: str) -> chromadb.Collection:
    client = _get_chroma()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ─── JSON file paths ──────────────────────────────────────────────────────────
SELECTORS_FILE   = MEMORY_DIR / "domain_selectors.json"
HALLUC_FILE      = MEMORY_DIR / "hallucination_list.json"
RUN_METRICS_FILE = MEMORY_DIR / "run_metrics.json"
PROMPT_VER_FILE  = MEMORY_DIR / "prompt_versions.json"
FEEDBACK_FILE    = MEMORY_DIR / "feedback_history.json"


def _read_json(path: Path) -> dict | list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {} if path.suffix == ".json" else []


def _write_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# LESSONS (ChromaDB)
# ══════════════════════════════════════════════════════════════════════════════

def add_lesson(
    text: str,
    scope: str,             # "universal" | "app_type:ecommerce" | "domain:ebay.com"
    confidence: float,
    source: str = "auto",   # "human" | "auto" | "repair"
    lesson_id: Optional[str] = None,
    base_url: Optional[str] = None,
    app_type: Optional[str] = None,
    tags: Optional[list] = None,
    dedup_threshold: float = 0.92,
) -> str:
    """
    Store a lesson. Returns the lesson_id.
    Deduplicates semantically: if a lesson with cosine similarity >= dedup_threshold
    already exists in the same scope, bumps its confidence instead of inserting.
    Human-typed prompts should use confidence=Confidence.HUMAN_TYPED (1.00).
    """
    from app.llm.huggingface import embed_one
    collection = _get_collection("lessons")

    # Resolve shorthand scope values using base_url / app_type if provided
    if scope == "domain" and base_url:
        scope = f"domain:{base_url}"
    elif scope == "app_type" and app_type:
        scope = f"app_type:{app_type}"

    embedding = embed_one(text)

    # Semantic dedup: check for near-identical existing lesson in same scope
    try:
        existing = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["metadatas", "distances", "documents"],
        )
        if existing["ids"] and existing["ids"][0]:
            dist = existing["distances"][0][0]
            similarity = 1.0 - dist
            meta = existing["metadatas"][0][0]
            if similarity >= dedup_threshold and meta.get("scope") == scope:
                # Near-duplicate — bump confidence instead of inserting
                existing_id = existing["ids"][0][0]
                new_conf = min(1.0, max(meta.get("confidence", confidence), confidence) + 0.03)
                meta["confidence"] = new_conf
                meta["run_count"] = meta.get("run_count", 1) + 1
                collection.update(ids=[existing_id], metadatas=[meta])
                log.debug(f"Memory: lesson dedup [{existing_id}] similarity={similarity:.2f} conf→{new_conf:.2f}")
                return existing_id
    except Exception:
        pass  # On any query error, fall through to normal insert

    lid = lesson_id or f"lesson_{int(time.time() * 1000)}"
    collection.upsert(
        ids=[lid],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{
            "scope":      scope,
            "confidence": confidence,
            "source":     source,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_count":  1,
        }],
    )
    log.debug(f"Memory: lesson stored [{lid}] scope={scope} conf={confidence:.2f}")
    return lid


def get_lessons(
    query: str,
    base_url: str,
    app_type: str,
    n_results: int = 10,
    min_confidence: Optional[float] = None,
) -> list[dict]:
    """
    Retrieve relevant lessons using cosine similarity.
    Filters by scope: returns universal + app_type-scoped + domain-scoped lessons.
    Only returns lessons at or above min_confidence (defaults to MEMORY_INJECTION_THRESHOLD).
    """
    from app.llm.huggingface import embed_one

    min_conf = min_confidence if min_confidence is not None else MEMORY_INJECTION_THRESHOLD
    collection = _get_collection("lessons")

    # Build allowed scopes for this query
    allowed_scopes = {
        "universal",
        f"app_type:{app_type}",
        f"domain:{base_url}",
    }

    try:
        query_emb = embed_one(query)
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=min(n_results * 3, 50),   # over-fetch, then filter
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        log.warning(f"Memory: lesson query failed: {e}")
        return []

    lessons = []
    ids       = results["ids"][0] if results.get("ids") else []
    docs      = results["documents"][0] if results["documents"] else []
    metas     = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    for lid, doc, meta, dist in zip(ids, docs, metas, distances):
        if meta.get("scope") not in allowed_scopes:
            continue
        if meta.get("confidence", 0) < min_conf:
            continue
        lessons.append({
            "id":         lid,
            "text":       doc,
            "scope":      meta.get("scope"),
            "confidence": meta.get("confidence"),
            "relevance":  1.0 - dist,   # cosine distance → similarity
        })
        if len(lessons) >= n_results:
            break

    # Sort by confidence × relevance
    lessons.sort(key=lambda x: x["confidence"] * x["relevance"], reverse=True)
    return lessons


def prune_stale_lessons(scope_prefix: str, max_lessons: int = 200, min_confidence: float = 0.35) -> int:
    """
    Remove lessons that have decayed below min_confidence or exceed max_lessons cap.
    Called after every run to prevent unbounded memory growth.
    Returns number of lessons pruned.
    """
    collection = _get_collection("lessons")
    try:
        all_items = collection.get(include=["metadatas"])
        if not all_items["ids"]:
            return 0

        # Filter to scope
        scoped = [
            (lid, meta)
            for lid, meta in zip(all_items["ids"], all_items["metadatas"])
            if meta.get("scope", "").startswith(scope_prefix)
        ]

        # Prune below min_confidence
        to_delete = [lid for lid, meta in scoped if meta.get("confidence", 1.0) < min_confidence]

        # Also prune oldest low-confidence entries if over cap
        if len(scoped) > max_lessons:
            sorted_by_conf = sorted(scoped, key=lambda x: x[1].get("confidence", 0))
            excess = len(scoped) - max_lessons
            to_delete += [lid for lid, _ in sorted_by_conf[:excess] if lid not in to_delete]

        if to_delete:
            collection.delete(ids=to_delete)
            log.info(f"Memory: pruned {len(to_delete)} stale lessons (scope={scope_prefix})")
        return len(to_delete)
    except Exception as e:
        log.warning(f"Memory: prune_stale_lessons failed: {e}")
        return 0


def bump_lesson_confidence(lesson_id: str, delta: float = 0.05) -> None:
    """Increase a lesson's confidence after it's validated by another run."""
    collection = _get_collection("lessons")
    try:
        existing = collection.get(ids=[lesson_id], include=["metadatas", "documents", "embeddings"])
        if not existing["ids"]:
            return
        meta = existing["metadatas"][0]
        new_conf = min(1.0, meta.get("confidence", 0.55) + delta)
        meta["confidence"] = new_conf
        meta["run_count"] = meta.get("run_count", 1) + 1
        collection.update(ids=[lesson_id], metadatas=[meta])
        log.debug(f"Memory: lesson {lesson_id} confidence bumped to {new_conf:.2f}")
    except Exception as e:
        log.warning(f"Memory: bump_lesson_confidence failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# REPAIR STRATEGIES (ChromaDB)
# ══════════════════════════════════════════════════════════════════════════════

def add_repair_strategy(
    error_pattern: str,
    fix_pattern: str = "",
    scope: str = "universal",
    confidence: float = Confidence.REPAIR_STRATEGY,
    fix_description: Optional[str] = None,
    base_url: Optional[str] = None,
    app_type: Optional[str] = None,
) -> None:
    # Accept fix_description as alias for fix_pattern
    fix_text = fix_description or fix_pattern

    # Resolve shorthand scope values
    if scope == "domain" and base_url:
        scope = f"domain:{base_url}"
    elif scope == "app_type" and app_type:
        scope = f"app_type:{app_type}"

    from app.llm.huggingface import embed_one
    collection = _get_collection("repair_strategies")
    sid = f"repair_{int(time.time() * 1000)}"
    collection.upsert(
        ids=[sid],
        embeddings=[embed_one(error_pattern)],
        documents=[fix_text],
        metadatas=[{
            "error_pattern": error_pattern,
            "scope":         scope,
            "confidence":    confidence,
            "created_at":    time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }],
    )


def get_repair_strategies(error_text: str, base_url: str, app_type: str, n: int = 5) -> list[dict]:
    from app.llm.huggingface import embed_one
    collection = _get_collection("repair_strategies")
    allowed_scopes = {"universal", f"app_type:{app_type}", f"domain:{base_url}"}
    try:
        results = collection.query(
            query_embeddings=[embed_one(error_text)],
            n_results=min(n * 2, 20),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    strategies = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if meta.get("scope") in allowed_scopes and meta.get("confidence", 0) >= MEMORY_INJECTION_THRESHOLD:
            strategies.append({
                "fix":        doc,
                "error":      meta.get("error_pattern"),
                "relevance":  1.0 - dist,
            })
    return strategies[:n]


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN SELECTORS (JSON)
# ══════════════════════════════════════════════════════════════════════════════

def save_selector(base_url: str, page_path: str, selector: str, score: float, confirmed: bool = False) -> None:
    """Add or update a selector entry for a domain+page."""
    data: dict = _read_json(SELECTORS_FILE)  # type: ignore
    key = base_url
    data.setdefault(key, {})
    data[key].setdefault(page_path, [])

    # Check if selector already exists
    for entry in data[key][page_path]:
        if entry["selector"] == selector:
            if confirmed:
                entry["confirmed"] = True
                entry["score"] = max(entry["score"], score)
            _write_json(SELECTORS_FILE, data)
            return

    data[key][page_path].append({
        "selector":  selector,
        "score":     score,
        "confirmed": confirmed,
        "added_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    _write_json(SELECTORS_FILE, data)


def get_selectors(base_url: str, page_path: Optional[str] = None, min_score: float = 0.4) -> list[str]:
    """Get confirmed+high-score selectors for a domain (optionally filtered by page)."""
    data: dict = _read_json(SELECTORS_FILE)  # type: ignore
    domain_data = data.get(base_url, {})

    if page_path:
        entries = domain_data.get(page_path, [])
    else:
        entries = [e for page_entries in domain_data.values() for e in page_entries]

    return [e["selector"] for e in entries if e.get("score", 0) >= min_score]


def confirm_selector(base_url: str, page_path: str, selector: str) -> None:
    """Mark a selector as human-confirmed (confidence=1.00)."""
    data: dict = _read_json(SELECTORS_FILE)  # type: ignore
    for entry in data.get(base_url, {}).get(page_path, []):
        if entry["selector"] == selector:
            entry["confirmed"] = True
            entry["score"] = 1.0
    _write_json(SELECTORS_FILE, data)


# ══════════════════════════════════════════════════════════════════════════════
# HALLUCINATION BLOCKLIST (JSON)
# ══════════════════════════════════════════════════════════════════════════════

def add_hallucination(selector: str, base_url: str, confidence: float = Confidence.CONFIRMED_HALL) -> None:
    data: dict = _read_json(HALLUC_FILE)  # type: ignore
    if selector in data:
        data[selector]["count"] = data[selector].get("count", 1) + 1
        data[selector]["confidence"] = min(1.0, data[selector]["confidence"] + 0.05)
        data[selector]["domains"].append(base_url)
    else:
        data[selector] = {
            "confidence": confidence,
            "count":      1,
            "domains":    [base_url],
            "added_at":   time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    _write_json(HALLUC_FILE, data)


def get_hallucination_blocklist(min_confidence: float = 0.65) -> list[str]:
    data: dict = _read_json(HALLUC_FILE)  # type: ignore
    return [sel for sel, meta in data.items() if meta.get("confidence", 0) >= min_confidence]


# ══════════════════════════════════════════════════════════════════════════════
# RUN METRICS (JSON)
# ══════════════════════════════════════════════════════════════════════════════

def save_run_metrics(run_id: str, metrics: dict) -> None:
    data: list = _read_json(RUN_METRICS_FILE)  # type: ignore
    if not isinstance(data, list):
        data = []
    metrics["run_id"] = run_id
    metrics["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Remove old entry for same run_id if exists
    data = [m for m in data if m.get("run_id") != run_id]
    data.append(metrics)
    _write_json(RUN_METRICS_FILE, data)


def get_run_metrics(base_url: Optional[str] = None, last_n: int = 20, limit: Optional[int] = None) -> list[dict]:
    data: list = _read_json(RUN_METRICS_FILE)  # type: ignore
    if not isinstance(data, list):
        return []
    if base_url:
        data = [m for m in data if m.get("base_url") == base_url]
    n = limit or last_n
    return sorted(data, key=lambda x: x.get("recorded_at", ""), reverse=True)[:n]


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK HISTORY (JSON — full audit trail)
# ══════════════════════════════════════════════════════════════════════════════

def save_feedback(run_id: str, phase: str, feedback_data: dict) -> None:
    data: list = _read_json(FEEDBACK_FILE)  # type: ignore
    if not isinstance(data, list):
        data = []
    data.append({
        "run_id":      run_id,
        "phase":       phase,
        "feedback":    feedback_data,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    _write_json(FEEDBACK_FILE, data)
