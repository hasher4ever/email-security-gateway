from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

import app as app_module


class InMemoryCache:
    def __init__(self, ttl_sec: int = 86400) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_sec

    async def open(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def get(self, h: str) -> Optional[dict[str, Any]]:
        row = self._store.get(h)
        if not row:
            return None
        if row["cached_until"] < datetime.now(timezone.utc):
            return None
        return {
            "verdict": row["verdict"],
            "has_login_form": row["has_login_form"],
            "final_url": row["final_url"],
            "screenshot_path": row["screenshot_path"],
        }

    async def put(self, h: str, url: str, result: dict[str, Any]) -> None:
        self._store[h] = {
            **result,
            "url": url,
            "cached_until": datetime.now(timezone.utc) + timedelta(seconds=self._ttl),
        }


@pytest.fixture
def cache() -> InMemoryCache:
    return InMemoryCache()


@pytest.fixture
def client(cache, monkeypatch):
    monkeypatch.setattr(app_module, "build_cache", lambda: cache)
    with TestClient(app_module.app) as c:
        yield c
