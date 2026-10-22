"""
ATS v8 — Route Crawler
Discovers all application routes via 5 sources, then extracts
CSS selectors from each page and scores their stability.

Dual-track crawl:
  Track 1 (guest)         — fetches routes WITHOUT auth session
  Track 2 (authenticated) — fetches routes WITH auth session (storage_state)

Routes that appear ONLY in Track 2 are labelled auth_routes in PageSelectorMap.
Agent B uses this to add an explicit login preamble to tests for those routes.

Source 1: DomainProfile.likely_routes (from domain inference)
Source 2: sitemap.xml parsing
Source 3: robots.txt parsing
Source 4: Homepage spider (depth=CRAWL_DEPTH, same-domain <a href>)
Source 5: LLM pattern completion (infers parameterised templates)
"""

from __future__ import annotations
import logging
import re
import time
import warnings
from typing import Optional
from urllib.parse import urlparse, urljoin

from app.schemas import DomainProfile, AuthContext, PageSelectorMap, SelectorEntry
from app.memory.agent_memory import save_selector
from app.llm.router import Tier, complete
from app.config import CRAWL_DEPTH, SELECTOR_MIN_SCORE, SELECTOR_SCORES, MAX_CRAWL_PAGES
log = logging.getLogger(__name__)


# ─── Selector stability scoring ───────────────────────────────────────────────

def score_selector(selector: str, tag: str) -> float:
    if "nth-child" in selector or "nth-of-type" in selector:
        return 0.2
    if "data-testid" in selector:  return SELECTOR_SCORES["data-testid"]
    if "aria-label"  in selector:  return SELECTOR_SCORES["aria-label"]
    if selector.startswith("#"):   return SELECTOR_SCORES["id"]
    if "[name="      in selector:  return SELECTOR_SCORES["name"]
    if "[type="      in selector:  return SELECTOR_SCORES["type"]
    if "."           in selector:  return SELECTOR_SCORES["class"]
    return 0.3


def _build_selector(el_attrs: dict, tag: str) -> Optional[tuple[str, float]]:
    if el_attrs.get("data-testid"):
        return f'[data-testid="{el_attrs["data-testid"]}"]', SELECTOR_SCORES["data-testid"]
    if el_attrs.get("aria-label"):
        return f'[aria-label="{el_attrs["aria-label"]}"]', SELECTOR_SCORES["aria-label"]
    if el_attrs.get("id"):
        return f"#{el_attrs['id']}", SELECTOR_SCORES["id"]
    if el_attrs.get("name") and tag in ("input", "select", "textarea", "button"):
        return f'{tag}[name="{el_attrs["name"]}"]', SELECTOR_SCORES["name"]
    if el_attrs.get("type") and tag in ("input", "button"):
        return f'{tag}[type="{el_attrs["type"]}"]', SELECTOR_SCORES["type"]
    classes = el_attrs.get("class", "")
    if classes and isinstance(classes, str):
        meaningful = [c for c in classes.split() if not re.match(r"^(css-|sc-|_|[0-9])", c)]
        if meaningful:
            return f"{tag}.{meaningful[0]}", SELECTOR_SCORES["class"]
    return None


# ─── Route collection helpers ─────────────────────────────────────────────────

def _make_adder(target: list[str], seen: set[str], skip_prefixes: list[str]):
    def add_route(path: str) -> None:
        path = path.strip()
        if not path or path in seen:
            return
        if re.search(r"\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|ttf|map|json|xml|xsl|txt|rss|atom)$", path, re.I):
            return
        if re.search(r"sitemap", path, re.I):
            return
        if any(path.startswith(s) for s in skip_prefixes if s):
            return
        seen.add(path)
        target.append(path)
    return add_route


def _routes_from_web(base_url: str, add_route) -> None:
    import httpx
    headers = {"User-Agent": "ATS-v8-crawler/1.0"}
    with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
        try:
            r = client.get(base_url + "/sitemap.xml")
            if r.status_code == 200:
                for match in re.findall(r"<loc>(.*?)</loc>", r.text):
                    path = urlparse(match).path
                    if path:
                        add_route(path)
        except Exception:
            pass
        try:
            r = client.get(base_url + "/robots.txt")
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.lower().startswith(("allow:", "disallow:")):
                        path = line.split(":", 1)[-1].strip()
                        if path and "*" not in path:
                            add_route(path)
        except Exception:
            pass


def _spider(base_url: str, url: str, depth: int, add_route, skip: list[str]) -> None:
    if depth == 0:
        return
    import httpx
    try:
        resp = httpx.get(url, timeout=10.0, follow_redirects=True,
                         headers={"User-Agent": "ATS-v8-crawler/1.0"})
        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(url, href)
            parsed = urlparse(full)
            if parsed.netloc and parsed.netloc not in base_url:
                continue
            path = parsed.path
            if not path or path == "/":
                continue
            add_route(path)
            if depth > 1:
                _spider(base_url, base_url + path, depth - 1, add_route, skip)
    except Exception:
        pass


def _complete_patterns(routes: list[str], app_type: str, add_route) -> None:
    if not routes:
        return
    route_sample = "\n".join(routes[:30])
    prompt = (
        f"Given these discovered routes from a {app_type} application:\n{route_sample}\n\n"
        "List up to 5 additional parameterised route templates likely to exist.\n"
        "Respond with ONE route per line, nothing else. Use {id} for numeric IDs.\n"
        "Only routes not already in the list above."
    )
    try:
        result = complete(
            tier=Tier.CLASSIFICATION,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            label="route_patterns",
        )
        for line in result.strip().splitlines():
            line = line.strip().strip("-").strip()
            if line.startswith("/"):
                add_route(line)
    except Exception as e:
        log.debug(f"Crawler: pattern completion failed (non-critical): {e}")


# ─── Dual-track guest crawl ───────────────────────────────────────────────────

def _guest_accessible_routes(base_url: str, skip_prefixes: list[str]) -> set[str]:
    """
    Fetch the homepage WITHOUT any auth session.
    Returns the set of paths reachable by a guest (no login).
    Used to compare against authenticated routes.
    """
    guest_routes: list[str] = []
    seen: set[str] = set()
    add = _make_adder(guest_routes, seen, skip_prefixes)

    import httpx
    headers = {"User-Agent": "ATS-v8-crawler/1.0"}
    try:
        resp = httpx.get(base_url, timeout=10.0, follow_redirects=True, headers=headers)
        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.netloc and parsed.netloc not in base_url:
                continue
            if parsed.path:
                add(parsed.path)
    except Exception as e:
        log.debug(f"Crawler: guest route fetch failed: {e}")

    return set(guest_routes)


# ─── Selector extraction from a single page ───────────────────────────────────

def _extract_selectors_from_page(
    url: str,
    auth_ctx: AuthContext,
    base_url: str,
    requires_auth: bool = False,
) -> tuple[list[SelectorEntry], list[str]]:
    """
    Load a page with Playwright (with or without auth), extract selectors.
    Returns (selector_entries, api_endpoints).
    """
    from playwright.sync_api import sync_playwright

    selectors: list[SelectorEntry] = []
    api_endpoints: list[str] = []
    seen_selectors: set[str] = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            ctx_kwargs: dict = {}
            if auth_ctx.storage_state_path:
                ctx_kwargs["storage_state"] = auth_ctx.storage_state_path

            context = browser.new_context(**ctx_kwargs)

            from app.core.auth_handler import get_auth_headers
            auth_headers = get_auth_headers(auth_ctx)
            if auth_headers:
                context.set_extra_http_headers(auth_headers)

            def on_request(req):
                if req.resource_type in ("xhr", "fetch"):
                    parsed = urlparse(req.url)
                    if "/api/" in parsed.path or parsed.path.startswith("/api"):
                        ep = parsed.path
                        if ep not in api_endpoints:
                            api_endpoints.append(ep)

            page = context.new_page()
            page.on("request", on_request)

            try:
                page.goto(url, timeout=20000, wait_until="networkidle")
            except Exception:
                try:
                    page.goto(url, timeout=20000, wait_until="domcontentloaded")
                except Exception as e:
                    log.debug(f"Crawler: failed to load {url}: {e}")
                    browser.close()
                    return [], []

            INTERACTIVE_SELECTORS = (
                "button, input, select, textarea, a[href], "
                "[role='button'], [role='link'], [role='tab'], "
                "[role='menuitem'], [data-testid], [aria-label]"
            )

            elements = page.query_selector_all(INTERACTIVE_SELECTORS)

            for el in elements[:200]:
                try:
                    tag = el.evaluate("el => el.tagName.toLowerCase()")
                    attrs = el.evaluate("""el => {
                        const a = {};
                        for (const attr of el.attributes) {
                            a[attr.name] = attr.value.substring(0, 100);
                        }
                        return a;
                    }""")

                    result = _build_selector(attrs, tag)
                    if result is None:
                        continue
                    sel_str, score = result

                    if score < SELECTOR_MIN_SCORE or sel_str in seen_selectors:
                        continue
                    seen_selectors.add(sel_str)

                    try:
                        text = (el.text_content() or "").strip()[:50]
                    except Exception:
                        text = ""

                    selectors.append(SelectorEntry(
                        selector=sel_str,
                        score=score,
                        tag=tag,
                        text=text,
                        page_url=url,
                        requires_auth=requires_auth,
                    ))
                except Exception:
                    continue

            browser.close()

    except Exception as e:
        log.warning(f"Crawler: selector extraction failed for {url}: {e}")

    log.debug(f"Crawler: {url} -> {len(selectors)} selectors (auth={requires_auth})")
    return selectors, api_endpoints


# ─── Main entry point ─────────────────────────────────────────────────────────

def crawl(
    profile: DomainProfile,
    auth_ctx: AuthContext,
    resource: dict,
    run_id: str,
    force: bool = False,
) -> PageSelectorMap:
    """
    Full route discovery + dual-track selector extraction.
    Guest routes vs auth-only routes are identified and labelled.
    Returns populated PageSelectorMap.
    """
    base_url = profile.base_url.rstrip("/")
    log.info(f"Crawler: starting on {base_url}")

    skip_prefixes = [p.rstrip("*") for p in resource.get("skip_routes", [])]

    # ── Collect all routes ────────────────────────────────────────────────────
    all_routes: list[str] = []
    seen: set[str] = set()
    add_route = _make_adder(all_routes, seen, skip_prefixes)

    for r in profile.likely_routes:
        add_route(r)

    _routes_from_web(base_url, add_route)
    _spider(base_url, base_url, depth=CRAWL_DEPTH, add_route=add_route, skip=skip_prefixes)
    _complete_patterns(all_routes, profile.app_type, add_route)

    log.info(f"Crawler: {len(all_routes)} unique routes discovered")

    # ── Dual-track: identify guest vs auth-only routes ────────────────────────
    needs_auth = auth_ctx.type != "none"

    if needs_auth:
        log.info("Crawler: running guest crawl to identify auth-only routes")
        guest_route_set = _guest_accessible_routes(base_url, skip_prefixes)
        auth_only_routes = [r for r in all_routes if r not in guest_route_set]
        guest_only_routes = [r for r in all_routes if r in guest_route_set]
        log.info(
            f"Crawler: {len(guest_only_routes)} guest routes, "
            f"{len(auth_only_routes)} auth-only routes"
        )
    else:
        auth_only_routes = []
        guest_only_routes = list(all_routes)

    # Cap routes to avoid crawling hundreds of pages
    if len(all_routes) > MAX_CRAWL_PAGES:
        log.info(f"Crawler: capping {len(all_routes)} routes to {MAX_CRAWL_PAGES}")
        all_routes = all_routes[:MAX_CRAWL_PAGES]

    # ── Extract selectors from each route ─────────────────────────────────────
    selector_map = PageSelectorMap(
        base_url=base_url,
        crawled_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        auth_routes=auth_only_routes,
        guest_routes=guest_only_routes,
    )

    auth_only_set = set(auth_only_routes)

    for path in all_routes:
        url = base_url + path if path.startswith("/") else path
        is_auth = path in auth_only_set
        selectors, api_endpoints = _extract_selectors_from_page(
            url, auth_ctx, base_url, requires_auth=is_auth
        )

        if selectors:
            selector_map.pages[path] = selectors
            for entry in selectors:
                if entry.score >= 0.7:
                    save_selector(base_url, path, entry.selector, entry.score)

        for ep in api_endpoints:
            if ep not in selector_map.api_endpoints:
                selector_map.api_endpoints.append(ep)

    total_selectors = sum(len(v) for v in selector_map.pages.values())
    log.info(
        f"Crawler: complete. pages={len(selector_map.pages)} "
        f"selectors={total_selectors} "
        f"auth_routes={len(auth_only_routes)} "
        f"api_endpoints={len(selector_map.api_endpoints)}"
    )

    # ── Telemetry ─────────────────────────────────────────────────────────────
    try:
        from app.core.telemetry import emit as _emit
        _emit(run_id=run_id, agent="crawler", event="crawl_complete", metrics={
            "routes_discovered":  len(all_routes),
            "pages_crawled":      len(selector_map.pages),
            "selectors_found":    total_selectors,
            "auth_routes":        len(auth_only_routes),
            "api_endpoints":      len(selector_map.api_endpoints),
        })
    except Exception:
        pass

    return selector_map


def crawl_single_page(
    url: str,
    auth_ctx: AuthContext,
    base_url: str,
) -> list[SelectorEntry]:
    """On-demand single-page crawl for hallucination repair."""
    log.info(f"Crawler (on-demand): {url}")
    selectors, _ = _extract_selectors_from_page(url, auth_ctx, base_url)
    return selectors
