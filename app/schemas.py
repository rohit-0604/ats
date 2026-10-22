"""
ATS v8 — All Pydantic Schemas
Single file import for all data models used across the pipeline.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator
import hashlib


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN PROFILE
# ══════════════════════════════════════════════════════════════════════════════

class AuthContext(BaseModel):
    type: Literal["none", "form_login", "bearer_token", "api_key"] = "none"
    login_url:        Optional[str] = None
    username:         Optional[str] = None
    password:         Optional[str] = None
    token_endpoint:   Optional[str] = None
    api_key:          Optional[str] = None
    storage_state_path: Optional[str] = None  # Written by auth_handler after login


class SelectorEntry(BaseModel):
    selector:       str
    score:          float           # 0.0–1.0 per SELECTOR_SCORES in config
    tag:            str             # button, input, a, etc.
    text:           Optional[str] = None
    page_url:       str
    confirmed:      bool = False    # True if human-validated in HITL
    requires_auth:  bool = False    # True if page was only reachable when authenticated


class PageSelectorMap(BaseModel):
    """All selectors discovered during crawl, keyed by page path."""
    base_url:       str
    pages:          Dict[str, List[SelectorEntry]] = Field(default_factory=dict)
    api_endpoints:  List[str] = Field(default_factory=list)
    crawled_at:     Optional[str] = None
    # Routes only reachable when authenticated (absent from guest crawl)
    auth_routes:    List[str] = Field(default_factory=list)
    # Routes reachable by guests (no login needed)
    guest_routes:   List[str] = Field(default_factory=list)

    def get_selectors_for_page(self, path: str, min_score: float = 0.4) -> List[str]:
        selectors = self.pages.get(path, [])
        return [s.selector for s in selectors if s.score >= min_score]

    def all_selectors(self, min_score: float = 0.4) -> List[str]:
        result = []
        for entries in self.pages.values():
            result.extend(s.selector for s in entries if s.score >= min_score)
        return list(set(result))

    def is_auth_required(self, path: str) -> bool:
        """Returns True if this route was only visible to authenticated users."""
        return path in self.auth_routes

    def auth_only_selectors(self, min_score: float = 0.4) -> List[str]:
        """Selectors from authenticated-only pages."""
        result = []
        for path in self.auth_routes:
            result.extend(
                s.selector for s in self.pages.get(path, [])
                if s.score >= min_score
            )
        return list(set(result))


class DomainProfile(BaseModel):
    app_type:       str = "generic"
    auth_type:      Literal["none", "form_login", "bearer_token", "api_key"] = "none"
    feature_areas:  List[str] = Field(default_factory=list)
    likely_routes:  List[str] = Field(default_factory=list)
    has_rest_api:   bool = False
    framework_hints: List[str] = Field(default_factory=list)
    base_url:       str = ""
    inferred_at:    Optional[str] = None

    def spec_file_for(self, keywords: List[str]) -> str:
        """Map requirement keywords to a spec file name based on feature areas."""
        kw_lower = " ".join(keywords).lower()
        for area in self.feature_areas:
            if area.lower() in kw_lower:
                return f"{area}.spec.ts"
        return "general.spec.ts"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIREMENT
# ══════════════════════════════════════════════════════════════════════════════

class Requirement(BaseModel):
    req_id:         str
    title:          str
    description:    str
    priority:       Literal["high", "medium", "low"] = "medium"
    req_type:       str = "functional"          # functional, non-functional, security, etc.
    feature_area:   Optional[str] = None
    section_ref:    Optional[str] = None        # e.g. "Section 3.2"
    dependencies:   List[str] = Field(default_factory=list)  # other req_ids
    gap_analysis:   bool = False                # True = synthesised by Agent A Pass 4
    confidence:     float = 0.75               # extraction confidence
    approved:       bool = False               # set by HITL Phase 1
    rejected:       bool = False
    human_prompt:   Optional[str] = None       # per-item HITL prompt for Agent B
    source_chunk:   Optional[int] = None       # which PDF chunk this came from

    def content_words(self) -> set[str]:
        """Returns meaningful words for Jaccard deduplication (stopwords stripped)."""
        STOPWORDS = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "that", "this", "it", "its", "and", "or", "but", "not", "no",
            "user", "system", "shall", "must", "should", "able", "allow"
        }
        words = (self.title + " " + self.description).lower().split()
        return {w.strip(".,;:()[]") for w in words if w not in STOPWORDS and len(w) > 2}

    def title_tokens(self) -> set[str]:
        return set(self.title.lower().split())


class RequirementBundle(BaseModel):
    requirements:   List[Requirement] = Field(default_factory=list)
    domain_profile: Optional[DomainProfile] = None
    pdf_path:       Optional[str] = None
    pdf_sha256:     Optional[str] = None
    run_id:         str = ""
    extracted_at:   Optional[str] = None
    pass_stats:     Dict[str, Any] = Field(default_factory=dict)
    # pass_stats keys: pass1_count, pass2_enriched, pass3_flagged,
    #                  pass4_gap_added, pass5_deduped_removed

    def approved_requirements(self) -> List[Requirement]:
        return [r for r in self.requirements if r.approved and not r.rejected]

    def pending_review(self) -> List[Requirement]:
        return [r for r in self.requirements if not r.approved and not r.rejected]


# ══════════════════════════════════════════════════════════════════════════════
# TEST CASE
# ══════════════════════════════════════════════════════════════════════════════

class TestCase(BaseModel):
    test_id:        str
    req_id:         str
    title:          str
    spec_file:      str                     # e.g. "auth.spec.ts"
    ts_code:        str                     # Full TypeScript test block
    selectors_used: List[str] = Field(default_factory=list)
    hallucinated:   List[str] = Field(default_factory=list)  # selectors not in map
    approved:       bool = False
    rejected:       bool = False
    human_prompt:   Optional[str] = None    # HITL Phase 2 per-item prompt
    repair_count:   int = 0
    last_error:     Optional[str] = None
    failure_type:   Optional[str] = None   # mirrors TestResult.failure_type
    dom_snapshot:   Optional[str] = None   # live DOM at failure time (from error-context.md)

    def body_words(self) -> set[str]:
        """Meaningful words from ts_code for similarity dedup."""
        words = self.ts_code.lower().split()
        return {w.strip(".,;:()[]{}\"'") for w in words if len(w) > 3}

    @property
    def test_id_hash(self) -> str:
        return hashlib.sha256(self.req_id.encode()).hexdigest()[:8]


class TestSuite(BaseModel):
    tests:          List[TestCase] = Field(default_factory=list)
    run_id:         str = ""
    generated_at:   Optional[str] = None

    def by_spec_file(self) -> Dict[str, List[TestCase]]:
        result: Dict[str, List[TestCase]] = {}
        for t in self.tests:
            result.setdefault(t.spec_file, []).append(t)
        return result

    def deduplicate(self) -> int:
        """
        Remove duplicate tests:
        - Same req_id (keep first)
        - Body similarity >= 0.85 (Jaccard on code tokens)
        Returns count of removed tests.
        """
        seen_req_ids: set[str] = set()
        kept: List[TestCase] = []
        removed = 0

        for test in self.tests:
            # Duplicate req_id check
            if test.req_id in seen_req_ids:
                removed += 1
                continue

            # Body similarity check against already-kept tests
            test_words = test.body_words()
            is_dup = False
            for k in kept:
                k_words = k.body_words()
                union = k_words | test_words
                if not union:
                    continue
                jaccard = len(k_words & test_words) / len(union)
                if jaccard >= 0.85:
                    is_dup = True
                    break

            if is_dup:
                removed += 1
            else:
                seen_req_ids.add(test.req_id)
                kept.append(test)

        self.tests = kept
        return removed

    def approved_tests(self) -> List[TestCase]:
        return [t for t in self.tests if t.approved and not t.rejected]

    def tests_with_hallucinations(self) -> List[TestCase]:
        return [t for t in self.tests if t.hallucinated]


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION REPORT
# ══════════════════════════════════════════════════════════════════════════════

class TestResult(BaseModel):
    test_id:    str
    req_id:     str
    spec_file:  str
    passed:     bool
    error:      Optional[str] = None
    duration_ms: Optional[int] = None
    # Structured failure classification (populated by evaluator_engine)
    failure_type: Optional[str] = None   # selector_not_found | strict_mode | assertion_failure | timeout | network_error | unknown
    dom_snapshot: Optional[str] = None  # First 3000 chars of error-context.md YAML at failure time
    failed_selector: Optional[str] = None  # Extracted selector from error message


class LoopRecord(BaseModel):
    loop_number:    int
    coverage_pct:   float
    exec_pct:       float
    hallucinations: int
    action_taken:   str       # repair_batch | on_demand_crawl | re_extract | ask_human | done
    planner_reasoning: Optional[str] = None
    repaired_count: int = 0
    stalled:        bool = False
    # Failure type distribution for this loop
    failure_distribution: Dict[str, int] = Field(default_factory=dict)
    # e.g. {"selector_not_found": 5, "strict_mode": 3, "assertion_failure": 2}


class EvaluationReport(BaseModel):
    run_id:             str
    total_requirements: int
    approved_requirements: int
    total_tests:        int
    passed_tests:       int
    failed_tests:       int
    coverage_pct:       float       # approved reqs with ≥1 passing test / total approved
    exec_pct:           float       # passed / total tests
    hallucination_count: int
    hallucinated_selectors: List[str] = Field(default_factory=list)
    loop_history:       List[LoopRecord] = Field(default_factory=list)
    test_results:       List[TestResult] = Field(default_factory=list)
    exit_reason:        str = "unknown"  # targets_met | max_loops | manual_stop
    total_duration_s:   Optional[float] = None

    @property
    def targets_met(self) -> bool:
        from app.config import TARGET_COVERAGE, TARGET_EXEC
        return (
            self.coverage_pct >= TARGET_COVERAGE
            and self.exec_pct >= TARGET_EXEC
            and self.hallucination_count == 0
        )

    def failing_req_ids(self) -> List[str]:
        passing = {r.req_id for r in self.test_results if r.passed}
        all_ids = {r.req_id for r in self.test_results}
        return list(all_ids - passing)

    def failure_distribution(self) -> Dict[str, int]:
        """Count failures by type across all failing test results."""
        dist: Dict[str, int] = {}
        for r in self.test_results:
            if not r.passed:
                ft = r.failure_type or "unknown"
                dist[ft] = dist.get(ft, 0) + 1
        return dist

    def dominant_failure_type(self) -> Optional[str]:
        """Returns the most common failure type, or None if no failures."""
        dist = self.failure_distribution()
        if not dist:
            return None
        return max(dist, key=lambda k: dist[k])


# ══════════════════════════════════════════════════════════════════════════════
# HITL FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

class ItemFeedback(BaseModel):
    item_id:        str             # req_id or test_id
    approved:       bool = False
    rejected:       bool = False
    run_prompt:     Optional[str] = None    # per-item prompt for this run only
    memory_note:    Optional[str] = None    # saved to ChromaDB for future runs
    selector_override: Optional[str] = None  # human provides real selector

class FeedbackResult(BaseModel):
    phase:              Literal["phase1", "phase2", "phase3"]
    run_id:             str
    items:              List[ItemFeedback] = Field(default_factory=list)
    category_prompts:   Dict[str, str] = Field(default_factory=dict)  # feature_area → prompt
    global_prompt:      Optional[str] = None
    submitted_at:       Optional[str] = None
    timed_out:          bool = False     # True if HITL_TIMEOUT reached, no human action

    def approved_ids(self) -> set[str]:
        return {i.item_id for i in self.items if i.approved}

    def rejected_ids(self) -> set[str]:
        return {i.item_id for i in self.items if i.rejected}

    def items_with_prompts(self) -> List[ItemFeedback]:
        return [i for i in self.items if i.run_prompt or i.memory_note]

    def items_with_selectors(self) -> List[ItemFeedback]:
        return [i for i in self.items if i.selector_override]
