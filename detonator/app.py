"""URL detonation sandbox — Phase 2."""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import structlog
import tldextract
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
log = structlog.get_logger()

TIMEOUT_SEC = int(os.environ.get("TIMEOUT_SEC", "30"))
CACHE_TTL_SEC = int(os.environ.get("CACHE_TTL_SEC", "86400"))
SCREENSHOT_DIR = Path(os.environ.get("SCREENSHOT_DIR", "/tmp/screenshots"))
USER_AGENT = os.environ.get(
    "DETONATOR_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
)

FREE_HOSTING_HOSTS = {
    "pages.dev",
    "vercel.app",
    "netlify.app",
    "github.io",
    "firebaseapp.com",
    "web.app",
    "repl.co",
    "glitch.me",
    "weeblysite.com",
    "wixsite.com",
}


class ScanRequest(BaseModel):
    url: str


class ScanResponse(BaseModel):
    verdict: str
    has_login_form: bool
    final_url: str
    screenshot_path: str
    cached: bool


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def etld1(url_or_host: str) -> str:
    ext = tldextract.extract(url_or_host)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}".lower()
    return (ext.domain or url_or_host).lower()


def host_of(url: str) -> str:
    from urllib.parse import urlparse
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_free_hosting(host: str) -> bool:
    host = host.lower()
    return any(host == h or host.endswith("." + h) for h in FREE_HOSTING_HOSTS)


def classify(initial_url: str, final_url: str, has_login_form: bool, loaded: bool) -> str:
    if not loaded:
        return "unknown"
    if not has_login_form:
        return "clean"
    initial_etld1 = etld1(initial_url)
    final_etld1 = etld1(final_url)
    if initial_etld1 and final_etld1 and initial_etld1 != final_etld1:
        return "phishing"
    if is_free_hosting(host_of(final_url)):
        return "phishing"
    return "clean"


# ─── Renderer ─────────────────────────────────────────────────────────

async def render(url: str) -> dict[str, Any]:
    from playwright.async_api import async_playwright

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = str(SCREENSHOT_DIR / f"{url_hash(url)}.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            try:
                await page.goto(url, timeout=TIMEOUT_SEC * 1000, wait_until="load")
            except Exception as e:
                return {
                    "loaded": False,
                    "final_url": url,
                    "has_login_form": False,
                    "screenshot_path": "",
                    "error": str(e),
                }

            try:
                await page.screenshot(path=screenshot_path, full_page=False)
            except Exception:
                screenshot_path = ""

            has_login_form = await page.evaluate(
                """() => {
                    if (document.querySelector('input[type=\"password\"]')) return true;
                    for (const f of document.querySelectorAll('form')) {
                        const inputs = f.querySelectorAll('input');
                        let hasPw = false, hasUser = false;
                        for (const i of inputs) {
                            const t = (i.type || '').toLowerCase();
                            const n = ((i.name || '') + ' ' + (i.id || '') + ' ' + (i.placeholder || '')).toLowerCase();
                            if (t === 'password' || /pass(word|wd)?/.test(n)) hasPw = true;
                            if (t === 'email' || t === 'text' || /user|email|login/.test(n)) hasUser = true;
                        }
                        if (hasPw && hasUser) return true;
                    }
                    return false;
                }"""
            )
            final_url = page.url
            return {
                "loaded": True,
                "final_url": final_url,
                "has_login_form": bool(has_login_form),
                "screenshot_path": screenshot_path,
            }
        finally:
            await browser.close()


# ─── Cache (Postgres) ─────────────────────────────────────────────────

class PostgresCache:
    def __init__(self, conninfo: str):
        from psycopg_pool import AsyncConnectionPool
        self._pool = AsyncConnectionPool(conninfo, min_size=1, max_size=4, open=False)

    async def open(self) -> None:
        await self._pool.open()

    async def close(self) -> None:
        await self._pool.close()

    async def get(self, h: str) -> Optional[dict[str, Any]]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT verdict, has_login_form, final_url, screenshot_path, cached_until "
                    "FROM detonation WHERE url_hash = %s",
                    (h,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                verdict, has_login_form, final_url, screenshot_path, cached_until = row
                if cached_until and cached_until < datetime.now(timezone.utc):
                    return None
                return {
                    "verdict": verdict,
                    "has_login_form": bool(has_login_form),
                    "final_url": final_url or "",
                    "screenshot_path": screenshot_path or "",
                }

    async def put(self, h: str, url: str, result: dict[str, Any]) -> None:
        cached_until = datetime.now(timezone.utc) + timedelta(seconds=CACHE_TTL_SEC)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO detonation (url_hash, url, final_url, verdict,
                        has_login_form, screenshot_path, cached_until, last_seen)
                    VALUES (%s,%s,%s,%s,%s,%s,%s, now())
                    ON CONFLICT (url_hash) DO UPDATE SET
                        final_url=EXCLUDED.final_url,
                        verdict=EXCLUDED.verdict,
                        has_login_form=EXCLUDED.has_login_form,
                        screenshot_path=EXCLUDED.screenshot_path,
                        cached_until=EXCLUDED.cached_until,
                        last_seen=now()
                    """,
                    (
                        h,
                        url,
                        result["final_url"],
                        result["verdict"],
                        result["has_login_form"],
                        result["screenshot_path"],
                        cached_until,
                    ),
                )
            await conn.commit()


def build_cache() -> Any:
    host = os.environ.get("POSTGRES_HOST")
    if not host:
        return None
    conninfo = (
        f"host={host} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']} "
        f"dbname={os.environ['POSTGRES_DB']}"
    )
    return PostgresCache(conninfo)


# ─── App ──────────────────────────────────────────────────────────────

class AppState:
    cache: Any = None
    renderer: Callable[[str], Any] = render


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.cache = build_cache()
    if state.cache is not None:
        await state.cache.open()
    yield
    if state.cache is not None:
        await state.cache.close()


app = FastAPI(lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scan", response_model=ScanResponse)
async def scan(req: ScanRequest) -> ScanResponse:
    url = req.url
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="invalid url")

    h = url_hash(url)
    started = time.monotonic()

    if state.cache is not None:
        try:
            hit = await state.cache.get(h)
        except Exception as e:
            log.warning("cache_get_failed", error=str(e))
            hit = None
        if hit is not None:
            duration_ms = int((time.monotonic() - started) * 1000)
            log.info(
                "scan",
                url_hash=h,
                verdict=hit["verdict"],
                duration_ms=duration_ms,
                cached=True,
            )
            return ScanResponse(cached=True, **hit)

    try:
        rendered = await state.renderer(url)
    except Exception as e:
        log.warning("render_failed", url_hash=h, error=str(e))
        rendered = {
            "loaded": False,
            "final_url": url,
            "has_login_form": False,
            "screenshot_path": "",
        }

    verdict = classify(
        url,
        rendered.get("final_url", url),
        bool(rendered.get("has_login_form", False)),
        bool(rendered.get("loaded", False)),
    )
    result = {
        "verdict": verdict,
        "has_login_form": bool(rendered.get("has_login_form", False)),
        "final_url": rendered.get("final_url", url),
        "screenshot_path": rendered.get("screenshot_path", ""),
    }

    if state.cache is not None:
        try:
            await state.cache.put(h, url, result)
        except Exception as e:
            log.warning("cache_put_failed", error=str(e))

    duration_ms = int((time.monotonic() - started) * 1000)
    log.info("scan", url_hash=h, verdict=verdict, duration_ms=duration_ms, cached=False)
    return ScanResponse(cached=False, **result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7000")),
    )
