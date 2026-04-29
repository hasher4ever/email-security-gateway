from __future__ import annotations

import pytest

import app as app_module


def _stub_renderer(result):
    async def _r(url: str):
        return result
    return _r


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_scan_clean_no_login_form(client, monkeypatch):
    monkeypatch.setattr(
        app_module.state,
        "renderer",
        _stub_renderer({
            "loaded": True,
            "final_url": "https://example.com/about",
            "has_login_form": False,
            "screenshot_path": "/tmp/screenshots/abc.png",
        }),
    )
    r = client.post("/scan", json={"url": "https://example.com/about"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "clean"
    assert body["has_login_form"] is False
    assert body["cached"] is False


def test_scan_phishing_etld_mismatch(client, monkeypatch):
    monkeypatch.setattr(
        app_module.state,
        "renderer",
        _stub_renderer({
            "loaded": True,
            "final_url": "https://chr0binson.com/login",
            "has_login_form": True,
            "screenshot_path": "/tmp/screenshots/x.png",
        }),
    )
    r = client.post("/scan", json={"url": "https://chrobinson.com/load"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "phishing"
    assert body["has_login_form"] is True


def test_scan_phishing_free_hosting(client, monkeypatch):
    monkeypatch.setattr(
        app_module.state,
        "renderer",
        _stub_renderer({
            "loaded": True,
            "final_url": "https://fake-bank.pages.dev/login",
            "has_login_form": True,
            "screenshot_path": "/tmp/screenshots/y.png",
        }),
    )
    r = client.post("/scan", json={"url": "https://fake-bank.pages.dev/login"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "phishing"


def test_scan_cache_hit_skips_browser(client, monkeypatch):
    calls = {"n": 0}

    async def renderer(url: str):
        calls["n"] += 1
        return {
            "loaded": True,
            "final_url": "https://example.com/",
            "has_login_form": False,
            "screenshot_path": "/tmp/screenshots/c.png",
        }

    monkeypatch.setattr(app_module.state, "renderer", renderer)
    r1 = client.post("/scan", json={"url": "https://example.com/"})
    assert r1.status_code == 200
    assert r1.json()["cached"] is False
    assert calls["n"] == 1

    r2 = client.post("/scan", json={"url": "https://example.com/"})
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    assert calls["n"] == 1


def test_scan_unknown_on_render_failure(client, monkeypatch):
    async def boom(url: str):
        raise RuntimeError("timeout")

    monkeypatch.setattr(app_module.state, "renderer", boom)
    r = client.post("/scan", json={"url": "https://broken.example/"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "unknown"
    assert body["has_login_form"] is False


def test_scan_unknown_when_loaded_false(client, monkeypatch):
    monkeypatch.setattr(
        app_module.state,
        "renderer",
        _stub_renderer({
            "loaded": False,
            "final_url": "https://broken.example/",
            "has_login_form": False,
            "screenshot_path": "",
        }),
    )
    r = client.post("/scan", json={"url": "https://broken.example/"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "unknown"


def test_scan_rejects_non_http(client):
    r = client.post("/scan", json={"url": "javascript:alert(1)"})
    assert r.status_code == 400
