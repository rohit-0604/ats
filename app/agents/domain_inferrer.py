"""
ATS v8 — Domain Inferrer
Visits base_url, extracts HTML/sitemap/robots, classifies the app type,
and builds a DomainProfile that drives every downstream decision.
Model: llama-3.1-8b-instant (Groq) — Tier 1, ~2s per call.
"""

from __future__ import annotations
import json
import logging
import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from app.llm.router import Tier, complete
from app.schemas import DomainProfile, AuthContext

log = logging.getLogger(__name__)

# ─── Known app_type → feature_areas mapping ──────────────────────────────────
APP_TYPE_FEATURES: dict[str, list[str]] = {
    "ecommerce":          ["auth", "search", "product", "cart", "checkout", "orders", "bidding"],
    "finance_saas":       ["auth", "dashboard", "transactions", "reports", "accounts", "settings"],
    "blog":               ["auth", "posts", "comments", "categories", "admin", "search"],
    "crm":                ["auth", "contacts", "leads", "deals", "pipeline", "reports"],
    "project_mgmt":       ["auth", "projects", "tasks", "sprints", "team", "reports"],
    "healthcare":         ["auth", "patients", "appointments", "records", "billing", "admin"],
    "education":          ["auth", "courses", "lessons", "quizzes", "progress", "admin"],
    "social":             ["auth", "feed", "profile", "messages", "notifications", "search"],
    "developer_platform": ["navigation", "pricing", "marketplace", "documentation", "blog", "support"],
    "marketing_site":     ["navigation", "hero", "pricing", "features", "cta", "footer"],
    "generic":            ["auth", "general", "edge_cases", "security"],
}

_SYSTEM_PROMPT = """You are an expert at classifying web applications from their homepage HTML.

Respond ONLY with a JSON object — no markdown, no explanation.

JSON schema:
{
  "app_type": "<one of: ecommerce, finance_saas, blog, crm, project_mgmt, healthcare, education, social, developer_platform, marketing_site, generic>",
  "auth_type": "<one of: none, form_login, bearer_token, api_key>",
  "has_rest_api": <true|false>,
  "framework_hints": ["<react|vue|angular|jquery|server-rendered|next-js|...>"],
  "likely_routes": ["<path1>", "<path2>", ...],
  "confidence": <0.0-1.0>
}

Rules:
- app_type: classify based on the PRIMARY purpose of the site. Use these definitions:
  - developer_platform: PaaS/IaaS/cloud hosting for developers (Heroku, Netlify, Vercel, AWS, Railway, Render). Key signals: "deploy", "dyno", "buildpack", "CLI", "add-ons", "dev center", "API docs", pricing tiers for compute.
  - marketing_site: public-facing product/company website with no primary app functionality (landing pages, SaaS marketing sites). Key signals: hero section, feature highlights, pricing table, CTA buttons, no user dashboard.
  - ecommerce: shopping, product listings, cart, checkout
  - finance_saas: banking, accounting, invoicing, transactions
  - blog: article/post listings, categories, comment sections
  - crm: contacts, leads, deals, sales pipeline
  - project_mgmt: tasks, boards, sprints, team collaboration
  - healthcare: patients, appointments, medical records
  - education: courses, lessons, quizzes, learning progress
  - social: feed, profiles, messaging, followers
  - generic: catch-all when none of the above fit clearly
- auth_type: form_login if you see a login form, bearer_token if API/SPA with JWT, none if fully public
- has_rest_api: true if you see /api/, fetch calls, or XHR patterns
- likely_routes: up to 10 most likely important routes for this app type
- confidence: your confidence in the classification"""


def _fetch_homepage(base_url: str, timeout: float = 15.0) -> tuple[str, str, str]:
    """
    Fetch homepage HTML, sitemap.xml, robots.txt.
    Returns (html_snippet, sitemap_text, robots_text).
    Truncates HTML to 8K chars for LLM context.
    """
    headers = {"User-Agent": "ATS-v8-crawler/1.0 (automated testing)"}
    html = ""
    sitemap = ""
    robots = ""

    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        # Homepage
        try:
            resp = client.get(base_url)
            html = resp.text
        except Exception as e:
            log.warning(f"DomainInferrer: homepage fetch failed: {e}")

        # sitemap.xml
        try:
            resp = client.get(base_url.rstrip("/") + "/sitemap.xml")
            if resp.status_code == 200:
                sitemap = resp.text[:3000]
        except Exception:
            pass

        # robots.txt
        try:
            resp = client.get(base_url.rstrip("/") + "/robots.txt")
            if resp.status_code == 200:
                robots = resp.text[:1000]
        except Exception:
            pass

    # Extract meaningful HTML subset — strip scripts/styles/SVG, keep structure
    if html:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "svg", "noscript", "iframe"]):
                tag.decompose()
            clean = soup.get_text(separator=" ", strip=True)
            # Also grab visible link hrefs for route hints
            links = [a.get("href", "") for a in soup.find_all("a", href=True)][:30]
            link_block = " | ".join(l for l in links if l.startswith("/"))
            html = f"{clean[:6000]}\n\nINTERNAL LINKS: {link_block}"
        except Exception:
            html = html[:8000]

    return html, sitemap, robots


def _extract_routes_from_sitemap(sitemap_text: str) -> list[str]:
    """Extract URL paths from sitemap.xml."""
    urls = re.findall(r"<loc>(.*?)</loc>", sitemap_text)
    paths = []
    for url in urls[:50]:
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path
            if path and path != "/":
                paths.append(path)
        except Exception:
            pass
    return paths[:20]


def _extract_routes_from_robots(robots_text: str) -> list[str]:
    """Extract Allow/Disallow paths from robots.txt."""
    paths = []
    for line in robots_text.splitlines():
        if line.strip().lower().startswith(("allow:", "disallow:")):
            parts = line.split(":", 1)
            if len(parts) == 2:
                path = parts[1].strip()
                if path and path != "/" and "*" not in path:
                    paths.append(path)
    return paths[:10]


def infer_domain(base_url: str, resource: Optional[dict] = None) -> DomainProfile:
    """
    Main entry point. Returns a populated DomainProfile.
    Falls back to a safe generic profile on any failure.
    """
    log.info(f"DomainInferrer: analysing {base_url}")

    html, sitemap, robots = _fetch_homepage(base_url)

    # Build context for LLM
    context_parts = [f"BASE URL: {base_url}"]
    if html:
        context_parts.append(f"HOMEPAGE CONTENT:\n{html}")
    if sitemap:
        context_parts.append(f"SITEMAP (truncated):\n{sitemap}")
    if robots:
        context_parts.append(f"ROBOTS.TXT:\n{robots}")

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": "\n\n".join(context_parts)},
    ]

    raw = ""
    try:
        raw = complete(
            tier=Tier.CLASSIFICATION,
            messages=messages,
            max_tokens=512,
            label="domain_infer",
        )
        # Strip markdown fences if present
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(raw)
    except Exception as e:
        log.warning(f"DomainInferrer: LLM parse failed ({e}), using generic fallback")
        data = {
            "app_type": "generic",
            "auth_type": "none",
            "has_rest_api": False,
            "framework_hints": [],
            "likely_routes": [],
            "confidence": 0.3,
        }

    app_type = data.get("app_type", "generic")
    if app_type not in APP_TYPE_FEATURES:
        app_type = "generic"

    # Merge LLM routes with sitemap + robots routes
    llm_routes  = data.get("likely_routes", [])
    sitemap_routes = _extract_routes_from_sitemap(sitemap) if sitemap else []
    robots_routes  = _extract_routes_from_robots(robots)   if robots  else []

    # Deduplicate while preserving order
    all_routes: list[str] = []
    seen: set[str] = set()
    for r in llm_routes + sitemap_routes + robots_routes:
        if r not in seen:
            all_routes.append(r)
            seen.add(r)

    # Merge auth type: resource.json overrides LLM inference
    auth_type = data.get("auth_type", "none")
    if resource and resource.get("auth", {}).get("type"):
        auth_type = resource["auth"]["type"]
        log.debug(f"DomainInferrer: auth_type overridden by resource.json: {auth_type}")

    profile = DomainProfile(
        app_type=app_type,
        auth_type=auth_type,
        feature_areas=APP_TYPE_FEATURES.get(app_type, APP_TYPE_FEATURES["generic"]),
        likely_routes=all_routes[:20],
        has_rest_api=data.get("has_rest_api", False),
        framework_hints=data.get("framework_hints", []),
        base_url=base_url,
        inferred_at=__import__("time").strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    log.info(
        f"DomainInferrer: {base_url} → app_type={profile.app_type} "
        f"auth={profile.auth_type} routes={len(profile.likely_routes)} "
        f"confidence={data.get('confidence', '?')}"
    )
    return profile
