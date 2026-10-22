"""
ATS v8 — Agent A: 5-Pass Requirement Extraction

Pass 1: Raw extraction  — Gemini 2.5 Flash (1M ctx), one call per chunk
Pass 2: RAG enrichment  — HuggingFace FAISS, fixes chunk-boundary truncations
Pass 3: Validation      — llama-3.1-8b, cross-refs, orphan IDs, obvious duplicates
Pass 4: Gap analysis    — DeepSeek R1, synthesises missing requirements
Pass 5: Deduplication   — Rule-based two-signal Jaccard (no LLM)
"""

from __future__ import annotations
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import (
    CACHE_DIR, CHUNK_SIZE, CODEGEN_BATCH_SIZE,
    Confidence,
)
from app.llm.router import Tier, complete
from app.llm.huggingface import embed
from app.schemas import Requirement, RequirementBundle, DomainProfile, PageSelectorMap
from app.memory.agent_memory import get_lessons

log = logging.getLogger(__name__)

# ─── Prompts ──────────────────────────────────────────────────────────────────

_P1_SYSTEM = """You are a senior QA analyst. Extract software requirements that can be verified using Playwright browser automation.

Return ONLY a JSON array. Each element:
{
  "req_id": "REQ-001",
  "title": "concise title",
  "description": "full description",
  "priority": "high|medium|low",
  "req_type": "functional|non-functional|security|performance|ui",
  "section_ref": "Section X.Y or null",
  "dependencies": []
}

TESTABILITY RULE — HARD FILTER:
Only extract a requirement if it can be verified by Playwright in a browser.
A requirement is Playwright-testable if and only if at least one of these is true:
  - An element is visible/present on the page (locator + toBeVisible)
  - Text content matches or contains a value (toHaveText / toContainText)
  - A URL navigates correctly (page.goto + expect URL)
  - A click triggers a state change (click + expect result)
  - A form input accepts and submits data
  - An element has a specific attribute (href, alt, target, aria-label)
  - A network response has a status code (page.route or response intercept)
  - A viewport-dependent layout change occurs (setViewportSize + expect)
  - Page title matches expected value (toHaveTitle)

DO NOT extract requirements that require:
  - Performance benchmarks (Lighthouse scores, Core Web Vitals, response time SLAs)
  - Geo-IP or region-based behavior (requires VPN/proxy infrastructure)
  - Server-side logic that produces no visible DOM change
  - Third-party analytics or tag firing (GTM, GA events)
  - SEO crawlability (robots.txt, search engine indexing)
  - Automated copyright year logic (server-side rendering detail)
  - SSL certificate validity
  - CDN or caching behavior

If a requirement is ambiguous, ask: "What exact Playwright assertion would verify this?"
If you cannot write that assertion, do not extract the requirement.

Rules:
- Every distinct testable requirement gets its own entry
- req_id must be unique (REQ-001, REQ-002, ...)
- Do NOT merge separate requirements
- Do NOT invent requirements not present in the text
- Return [] if no testable requirements found in this chunk"""

_P3_SYSTEM = """You are a QA analyst validating a requirements list for Playwright browser automation testing.

For each requirement, check:
1. Does it reference a section/ID that exists in the list? Flag orphaned references.
2. Is it an obvious duplicate of another requirement? (same meaning, different words)
3. Is it complete enough to write a Playwright test for?
4. Can Playwright actually verify this? Flag requirements that CANNOT be tested by browser automation.

Return ONLY a JSON array with the same req_ids plus a "flag" field:
[{"req_id": "REQ-001", "flag": null}, {"req_id": "REQ-002", "flag": "possible_duplicate:REQ-001"}, ...]

Flag values: null | "orphaned_ref" | "possible_duplicate:REQ-XXX" | "incomplete" | "not_playwright_testable"

Flag "not_playwright_testable" for:
- Performance benchmarks (Lighthouse scores, load times, Core Web Vitals)
- Server-side or backend logic (how data is loaded, caching, CDN)
- Geo-IP / region detection logic
- Copyright year auto-update (server-side rendering detail)
- Email delivery, background jobs, analytics
- Legal/contractual compliance
- Computed CSS properties (background-color, font-size, z-index, computed styles) — these vary by browser/OS and cannot be reliably asserted
- Exact pixel counts, dimensions, or spacing measurements
- Counting exact numbers of arbitrary DOM children (e.g. "exactly 4 feature cards") unless the count is verified by a unique role/label
- Verifying DOM structure depth or nesting (e.g. "cards must be inside a grid div")
- Any requirement whose only verifiable aspect is a CSS class name with no semantic meaning

For requirements that are PARTIALLY testable, simplify to the testable part:
- "Hero section has purple background" → rewrite as "Hero section is visible" (flag as simplified, not removed)
- "Minimum 4 feature cards exist" → rewrite as "Feature cards section is visible and contains at least one card"
- "Social icons use brand colors" → rewrite as "Social media links are visible in footer"

Do not remove or modify requirements — only add flags."""

_P4_SYSTEM = """You are a senior QA analyst performing gap analysis on a requirements document.

Given the extracted requirements and the application type, identify requirements that:
1. Are MISSING but CLEARLY NEEDED for this type of application
2. Are implied by other requirements but not explicitly stated
3. Cover common UX, accessibility, or navigation patterns for this app type

CRITICAL: Only suggest requirements that Playwright browser automation CAN test:
- UI elements visible/present on page
- Navigation and link behaviour
- Form interactions
- Page content and structure
- Element attributes and text

Do NOT suggest:
- Performance benchmarks or load time requirements
- Server-side or backend logic
- Geo-IP, CDN, or infrastructure requirements
- Legal compliance or contractual obligations

Return ONLY a JSON array of NEW requirements to add (using same schema as input).
Use req_id format: GAP-001, GAP-002, ...
Return [] if no gaps found.
Do NOT duplicate existing requirements."""


# ─── Pass 1: Raw extraction ───────────────────────────────────────────────────

def _pass1_extract(chunks: list[str], domain_profile: DomainProfile, run_id: str) -> list[Requirement]:
    """Extract requirements from each chunk with Gemini 2.5 Flash."""
    all_reqs: list[Requirement] = []
    req_counter = 1

    # Inject memory lessons if available
    lessons = get_lessons(
        query=f"requirement extraction {domain_profile.app_type}",
        base_url=domain_profile.base_url,
        app_type=domain_profile.app_type,
        n_results=5,
    )
    memory_block = ""
    if lessons:
        lesson_texts = "\n".join(f"- {l['text']}" for l in lessons)
        memory_block = f"\n\nLESSONS FROM PREVIOUS RUNS:\n{lesson_texts}\n"

    system = _P1_SYSTEM + memory_block

    for i, chunk in enumerate(chunks):
        log.info(f"Agent A Pass 1: chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": f"Extract requirements from this text:\n\n{chunk}"},
        ]

        raw = ""
        try:
            raw = complete(
                tier=Tier.EXTRACTION,
                messages=messages,
                max_tokens=8192,
                label=f"pass1_chunk{i+1}",
            )
            raw = _strip_json_fences(raw)
            items = json.loads(raw)
            if not isinstance(items, list):
                items = []
        except Exception as e:
            log.warning(f"Agent A Pass 1 chunk {i+1} parse failed: {e}. Raw: {raw[:200]}")
            items = []

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                # Re-assign req_id to ensure global uniqueness across chunks
                item["req_id"] = f"REQ-{req_counter:03d}"
                item["source_chunk"] = i
                item.setdefault("approved", False)
                item.setdefault("confidence", 0.75)
                req = Requirement(**{k: v for k, v in item.items()
                                     if k in Requirement.model_fields})
                all_reqs.append(req)
                req_counter += 1
            except Exception as e:
                log.debug(f"Agent A Pass 1: skipping malformed item: {e}")

    log.info(f"Agent A Pass 1: extracted {len(all_reqs)} requirements from {len(chunks)} chunks")
    return all_reqs


# ─── Pass 2: RAG enrichment ───────────────────────────────────────────────────

def _pass2_rag_enrichment(
    reqs: list[Requirement],
    chunks: list[str],
    full_text: str,
) -> list[Requirement]:
    """
    Identifies requirements that may have been truncated at chunk boundaries
    (their description ends mid-sentence) and re-extracts them with cross-chunk context.
    Uses FAISS for fast nearest-chunk lookup.
    """
    if len(chunks) <= 1:
        return reqs

    # Build FAISS index over chunks
    log.info("Agent A Pass 2: building FAISS index for RAG enrichment")
    try:
        import faiss
        chunk_embeddings = embed(chunks)
        emb_array = np.array(chunk_embeddings, dtype=np.float32)
        faiss.normalize_L2(emb_array)
        index = faiss.IndexFlatIP(emb_array.shape[1])
        index.add(emb_array)
    except Exception as e:
        log.warning(f"Agent A Pass 2: FAISS init failed, skipping RAG: {e}")
        return reqs

    # Find truncated requirements (description ends without punctuation)
    truncated = [
        r for r in reqs
        if r.description and not r.description.strip()[-1:] in ".!?)"
    ]
    if not truncated:
        log.info("Agent A Pass 2: no truncated requirements found")
        return reqs

    log.info(f"Agent A Pass 2: enriching {len(truncated)} potentially truncated requirements")
    enriched_map: dict[str, Requirement] = {}

    for req in truncated:
        query_text = req.title + " " + req.description
        try:
            q_emb = np.array(embed([query_text]), dtype=np.float32)
            faiss.normalize_L2(q_emb)
            _, indices = index.search(q_emb, k=min(3, len(chunks)))

            # Build context window from adjacent chunks
            context_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
            context = "\n\n---\n\n".join(context_chunks[:3])

            messages = [
                {"role": "system", "content": _P1_SYSTEM},
                {"role": "user",   "content":
                    f"This requirement appears to be truncated:\n"
                    f"Title: {req.title}\n"
                    f"Description: {req.description}\n\n"
                    f"Here is the relevant context from the document:\n{context}\n\n"
                    f"Return the complete requirement as a JSON object with all fields filled."},
            ]
            raw = complete(tier=Tier.EXTRACTION, messages=messages, max_tokens=512,
                           label=f"pass2_enrich_{req.req_id}")
            raw = _strip_json_fences(raw)

            # Accept single object or first item in array
            data = json.loads(raw)
            if isinstance(data, list) and data:
                data = data[0]
            if isinstance(data, dict) and data.get("description"):
                req.description = data["description"]
                enriched_map[req.req_id] = req
        except Exception as e:
            log.debug(f"Agent A Pass 2: enrichment failed for {req.req_id}: {e}")

    log.info(f"Agent A Pass 2: enriched {len(enriched_map)} requirements")
    return reqs


# ─── Pass 3: Validation ───────────────────────────────────────────────────────

def _pass3_validate(reqs: list[Requirement]) -> list[Requirement]:
    """
    llama-3.1-8b cross-reference validation.
    Adds flags to requirements — does not remove anything.
    """
    log.info(f"Agent A Pass 3: validating {len(reqs)} requirements")

    # Send in batches to stay within context
    batch_size = 50
    all_flags: dict[str, str] = {}

    for i in range(0, len(reqs), batch_size):
        batch = reqs[i:i + batch_size]
        req_list = [{"req_id": r.req_id, "title": r.title, "description": r.description[:200]}
                    for r in batch]
        messages = [
            {"role": "system", "content": _P3_SYSTEM},
            {"role": "user",   "content": f"Validate these requirements:\n{json.dumps(req_list, indent=2)}"},
        ]
        try:
            raw = complete(tier=Tier.CLASSIFICATION, messages=messages,
                           max_tokens=1024, label="pass3_validate")
            raw = _strip_json_fences(raw)
            flags = json.loads(raw)
            for item in flags:
                if item.get("flag"):
                    all_flags[item["req_id"]] = item["flag"]
        except Exception as e:
            log.debug(f"Agent A Pass 3 batch failed: {e}")

    # Apply flags
    removed = []
    for req in reqs:
        flag = all_flags.get(req.req_id)
        if flag:
            log.debug(f"Agent A Pass 3: {req.req_id} flagged: {flag}")
            if "not_playwright_testable" in flag:
                # Hard exclude — cannot be tested by Playwright at all
                req.rejected = True
                req.confidence = 0.0
                removed.append(req.req_id)
            elif "possible_duplicate" in flag:
                req.confidence = max(0.3, req.confidence - 0.2)
            elif "incomplete" in flag:
                req.confidence = max(0.4, req.confidence - 0.1)

    # Filter out rejected non-testable requirements
    filtered = [r for r in reqs if not r.rejected]
    flagged_count = len(all_flags)
    log.info(f"Agent A Pass 3: {flagged_count} requirements flagged, {len(removed)} removed (not_playwright_testable)")
    return filtered


# ─── Pass 4: Gap analysis ─────────────────────────────────────────────────────

def _pass4_gap_analysis(
    reqs: list[Requirement],
    domain_profile: DomainProfile,
) -> list[Requirement]:
    """
    DeepSeek R1 identifies missing requirements typical for this app_type.
    All synthesised requirements are tagged gap_analysis=True, confidence=0.60.
    These are always shown for HITL review regardless of auto-approval threshold.
    """
    log.info(f"Agent A Pass 4: gap analysis for {domain_profile.app_type}")

    existing_titles = [r.title for r in reqs]
    feature_areas   = domain_profile.feature_areas

    messages = [
        {"role": "system", "content": _P4_SYSTEM},
        {"role": "user", "content":
            f"Application type: {domain_profile.app_type}\n"
            f"Feature areas: {', '.join(feature_areas)}\n"
            f"Base URL: {domain_profile.base_url}\n\n"
            f"Existing requirements ({len(reqs)} total):\n"
            + "\n".join(f"- {t}" for t in existing_titles[:60])
            + "\n\nIdentify missing requirements."},
    ]

    gap_counter = 1
    try:
        raw = complete(
            tier=Tier.REASONING,
            messages=messages,
            max_tokens=2048,
            label="pass4_gap",
        )
        raw = _strip_json_fences(raw)
        items = json.loads(raw)
        if not isinstance(items, list):
            items = []

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                item["req_id"]      = f"GAP-{gap_counter:03d}"
                item["gap_analysis"] = True
                item["confidence"]   = Confidence.CATEGORY_PROMPT   # 0.60
                item["approved"]     = False
                req = Requirement(**{k: v for k, v in item.items()
                                     if k in Requirement.model_fields})
                reqs.append(req)
                gap_counter += 1
            except Exception as e:
                log.debug(f"Agent A Pass 4: malformed gap item: {e}")

    except Exception as e:
        log.warning(f"Agent A Pass 4: gap analysis failed (non-critical): {e}")

    added = gap_counter - 1
    log.info(f"Agent A Pass 4: {added} gap requirements synthesised")
    return reqs


# ─── Pass 5: Deduplication ────────────────────────────────────────────────────

def _pass5_dedup(reqs: list[Requirement]) -> tuple[list[Requirement], int]:
    """
    Two-signal Jaccard deduplication.
    Signal 1: title token Jaccard > 0.85
    Signal 2: content-word Jaccard >= 0.55  (stopwords stripped)
    EITHER signal triggers removal (keep first, discard later).
    """
    kept: list[Requirement] = []
    removed = 0

    for req in reqs:
        is_dup = False
        for k in kept:
            # Signal 1: title
            t_union = req.title_tokens() | k.title_tokens()
            if t_union:
                t_jaccard = len(req.title_tokens() & k.title_tokens()) / len(t_union)
                if t_jaccard > 0.85:
                    is_dup = True
                    break

            # Signal 2: content words
            c_union = req.content_words() | k.content_words()
            if c_union:
                c_jaccard = len(req.content_words() & k.content_words()) / len(c_union)
                if c_jaccard >= 0.55:
                    is_dup = True
                    break

        if is_dup:
            removed += 1
        else:
            kept.append(req)

    log.info(f"Agent A Pass 5: {removed} duplicates removed, {len(kept)} requirements kept")
    return kept, removed


# ─── Cache helpers ────────────────────────────────────────────────────────────

def _cache_path(sha256: str) -> Path:
    return CACHE_DIR / f"requirements_{sha256[:16]}.json"


def _load_cache(sha256: str) -> Optional[RequirementBundle]:
    path = _cache_path(sha256)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        bundle = RequirementBundle(**data)
        log.info(f"Agent A: cache hit for sha256={sha256[:16]} ({len(bundle.requirements)} reqs)")
        return bundle
    except Exception as e:
        log.warning(f"Agent A: cache read failed: {e}")
        return None


def _save_cache(bundle: RequirementBundle) -> None:
    if not bundle.pdf_sha256:
        return
    path = _cache_path(bundle.pdf_sha256)
    path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    log.info(f"Agent A: cached {len(bundle.requirements)} reqs → {path.name}")


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_extraction(
    pdf_path: str,
    domain_profile: DomainProfile,
    run_id: str,
    force: bool = False,
) -> RequirementBundle:
    """
    Full 5-pass extraction pipeline.
    Returns RequirementBundle with all requirements.

    If force=False and cache exists for this PDF, returns cached bundle.
    """
    from app.core.pdf_extractor import load_pdf

    # Load and validate PDF
    full_text, chunks, sha256 = load_pdf(pdf_path)

    # Check cache
    if not force:
        cached = _load_cache(sha256)
        if cached:
            cached.run_id = run_id
            return cached

    pass_stats: dict = {"chunks": len(chunks)}
    t0 = time.time()

    # Pass 1
    reqs = _pass1_extract(chunks, domain_profile, run_id)
    pass_stats["pass1_count"] = len(reqs)

    # Pass 2
    reqs = _pass2_rag_enrichment(reqs, chunks, full_text)
    pass_stats["pass2_enriched"] = len([r for r in reqs if r.description])

    # Pass 3
    reqs = _pass3_validate(reqs)
    pass_stats["pass3_flagged"] = len([r for r in reqs if r.confidence < 0.65])

    # Pass 4
    reqs = _pass4_gap_analysis(reqs, domain_profile)
    pass_stats["pass4_gap_added"] = len([r for r in reqs if r.gap_analysis])

    # Pass 5
    reqs, removed = _pass5_dedup(reqs)
    pass_stats["pass5_deduped_removed"] = removed

    pass_stats["total_time_s"] = round(time.time() - t0, 1)

    # ── Telemetry ─────────────────────────────────────────────────────────────
    try:
        from app.core.telemetry import emit as _emit
        p1_count = pass_stats.get("pass1_count", 0)
        removed_untestable = p1_count - len(reqs) + removed  # approx untestable removed
        _emit(run_id=run_id, agent="agent_a", event="extraction_complete", metrics={
            "chunks":                  len(chunks),
            "reqs_extracted":          p1_count,
            "reqs_after_validation":   pass_stats.get("pass3_flagged", 0),
            "reqs_removed_untestable": max(0, p1_count - len(reqs) - removed),
            "gap_reqs_added":          pass_stats.get("pass4_gap_added", 0),
            "duplicates_removed":      removed,
            "final_req_count":         len(reqs),
            "duration_s":              pass_stats["total_time_s"],
        })
    except Exception:
        pass

    bundle = RequirementBundle(
        requirements=reqs,
        domain_profile=domain_profile,
        pdf_path=pdf_path,
        pdf_sha256=sha256,
        run_id=run_id,
        extracted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        pass_stats=pass_stats,
    )

    _save_cache(bundle)
    log.info(
        f"Agent A: complete. {len(reqs)} requirements "
        f"({pass_stats['pass4_gap_added']} gap) in {pass_stats['total_time_s']}s"
    )
    return bundle


# ─── Utility ─────────────────────────────────────────────────────────────────

def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences from LLM output before json.loads."""
    return re.sub(r"```(?:json)?|```", "", text).strip()
