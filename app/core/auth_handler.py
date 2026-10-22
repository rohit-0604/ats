"""
ATS v8 — Auth Handler
Establishes authenticated browser session for the route crawler.
Supports: none, form_login, bearer_token, api_key.
Output: storage_state.json (Playwright session) or auth headers dict.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional
import httpx

from app.schemas import AuthContext, DomainProfile
from app.config import OUTPUT_DIR

log = logging.getLogger(__name__)


def handle_auth(
    profile: DomainProfile,
    resource: dict,
    run_id: str,
) -> AuthContext:
    """
    Reads resource.json auth config, performs the appropriate auth flow,
    returns a populated AuthContext ready for the crawler.
    """
    auth_config = resource.get("auth", {})
    auth_type   = auth_config.get("type", "none")
    creds       = auth_config.get("credentials", {})

    ctx = AuthContext(
        type=auth_type,
        username=creds.get("username"),
        password=creds.get("password"),
        token_endpoint=auth_config.get("token_endpoint"),
        api_key=auth_config.get("api_key"),
    )

    if auth_type == "none":
        log.info("AuthHandler: no auth required")
        return ctx

    if auth_type == "form_login":
        return _handle_form_login(ctx, profile, run_id)

    if auth_type == "bearer_token":
        return _handle_bearer_token(ctx, profile)

    if auth_type == "api_key":
        log.info("AuthHandler: API key auth configured")
        return ctx

    log.warning(f"AuthHandler: unknown auth_type '{auth_type}', treating as none")
    return ctx


def _handle_form_login(
    ctx: AuthContext,
    profile: DomainProfile,
    run_id: str,
) -> AuthContext:
    """
    Playwright-based form login. Saves storage_state.json for reuse
    across all subsequent crawler sessions.
    """
    from playwright.sync_api import sync_playwright

    storage_path = str(OUTPUT_DIR / f"storage_state_{run_id}.json")

    if not ctx.username or not ctx.password:
        log.warning("AuthHandler: form_login configured but no username/password in resource.json")
        return ctx

    # Determine login URL
    base = profile.base_url.rstrip("/")
    login_url = ctx.login_url or _guess_login_url(base, profile)
    log.info(f"AuthHandler: form_login → {login_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(login_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Find and fill username field
            username_sel = _find_field(page, ["email", "username", "user", "login"])
            if username_sel:
                page.fill(username_sel, ctx.username)
                log.debug(f"AuthHandler: filled username with selector {username_sel}")
            else:
                log.warning("AuthHandler: could not find username field")

            # Find and fill password field
            password_sel = _find_field(page, ["password", "pass", "pwd"])
            if password_sel:
                page.fill(password_sel, ctx.password)
                log.debug(f"AuthHandler: filled password with selector {password_sel}")
            else:
                log.warning("AuthHandler: could not find password field")

            # Submit
            submit_sel = _find_submit(page)
            if submit_sel:
                page.click(submit_sel)
            else:
                page.keyboard.press("Enter")

            # Wait for redirect away from login page
            try:
                page.wait_for_url(lambda url: login_url not in url, timeout=10000)
            except Exception:
                page.wait_for_load_state("networkidle", timeout=10000)

            # Save session
            context.storage_state(path=storage_path)
            browser.close()

        ctx.storage_state_path = storage_path
        log.info(f"AuthHandler: login successful — session saved to {storage_path}")

    except Exception as e:
        log.error(f"AuthHandler: form_login failed: {e}")
        log.warning("AuthHandler: proceeding without authentication")

    return ctx


def _handle_bearer_token(ctx: AuthContext, profile: DomainProfile) -> AuthContext:
    """
    POST to login/token endpoint, extract Bearer token.
    Token stored in ctx for header injection by the crawler.
    """
    if not ctx.username or not ctx.password:
        log.warning("AuthHandler: bearer_token configured but no credentials")
        return ctx

    base = profile.base_url.rstrip("/")
    token_url = ctx.token_endpoint or _guess_token_endpoint(base)
    log.info(f"AuthHandler: fetching bearer token from {token_url}")

    try:
        resp = httpx.post(
            token_url,
            json={"username": ctx.username, "password": ctx.password},
            timeout=15.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()

        # Common token field names
        token = (
            data.get("access_token") or
            data.get("token") or
            data.get("accessToken") or
            data.get("jwt")
        )
        if token:
            # Store token by abusing login_url field temporarily
            # The crawler reads ctx.login_url for the token value
            ctx.login_url = f"Bearer {token}"
            log.info("AuthHandler: bearer token obtained")
        else:
            log.warning(f"AuthHandler: no token field found in response. Keys: {list(data.keys())}")

    except Exception as e:
        log.error(f"AuthHandler: bearer token fetch failed: {e}")

    return ctx


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _guess_login_url(base: str, profile: DomainProfile) -> str:
    """Infer login URL from likely_routes or common defaults."""
    login_keywords = ["signin", "sign-in", "login", "log-in", "auth"]
    for route in profile.likely_routes:
        for kw in login_keywords:
            if kw in route.lower():
                return base + route
    # Common defaults — try each path
    for path in ["/login", "/signin", "/auth/login", "/user/login", "/account/login"]:
        import httpx
        try:
            r = httpx.head(base + path, timeout=5.0, follow_redirects=True)
            if r.status_code < 400:
                return base + path
        except Exception:
            pass
    return base + "/login"


def _guess_token_endpoint(base: str) -> str:
    for path in ["/api/auth/login", "/api/login", "/api/token", "/auth/token", "/login"]:
        import httpx
        try:
            r = httpx.options(base + path, timeout=5.0, follow_redirects=True)
            if r.status_code < 400:
                return base + path
        except Exception:
            pass
    return base + "/api/auth/login"


def _find_field(page, keywords: list[str]) -> Optional[str]:
    """
    Try common selectors for a form field matching any of the keywords.
    Returns first matching selector or None.
    """
    from playwright.sync_api import Page
    for kw in keywords:
        candidates = [
            f"input[name='{kw}']",
            f"input[id='{kw}']",
            f"input[type='{kw}']",
            f"input[placeholder*='{kw}' i]",
            f"input[autocomplete='{kw}']",
            f"input[aria-label*='{kw}' i]",
        ]
        for sel in candidates:
            try:
                if page.locator(sel).count() > 0:
                    return sel
            except Exception:
                pass
    return None


def _find_submit(page) -> Optional[str]:
    """Find the form submit button."""
    candidates = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
        "button:has-text('Login')",
        "button:has-text('Continue')",
        "[data-testid*='login']",
        "[data-testid*='signin']",
        "[data-testid*='submit']",
    ]
    for sel in candidates:
        try:
            if page.locator(sel).count() > 0:
                return sel
        except Exception:
            pass
    return None


def get_auth_headers(ctx: AuthContext) -> dict[str, str]:
    """
    Returns HTTP headers dict for this auth context.
    Used by crawler and repair agent for direct HTTP requests.
    """
    if ctx.type == "bearer_token" and ctx.login_url and ctx.login_url.startswith("Bearer "):
        return {"Authorization": ctx.login_url}
    if ctx.type == "api_key" and ctx.api_key:
        return {"X-API-Key": ctx.api_key}
    return {}
