"""Structural tests for the trucking-industry phishing-simulation templates.

Walks every subdirectory of `gophish/templates/` and checks that each one is a
valid Gophish-importable template plus its meta sidecar, AND that we never
ship a template that points at a real broker / load-board / factoring domain.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).parent

EXPECTED_SLUGS = {
    "load-board-rate-offer",
    "rate-confirmation-update",
    "eld-compliance-alert",
    "settlement-statement-ready",
    "dot-inspection-notice",
    "broker-wire-instruction-change",
    "fuel-card-suspended",
    "factoring-payment-issue",
}

VALID_AUDIENCES = {"dispatchers", "drivers", "accounting", "all"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_LURES = {"urgency", "authority", "money", "fear"}

# Real domains we must never ship as `from_address`. Suffix-match so subdomains
# of these (e.g. mail.chrobinson.com) also fail.
REAL_DOMAIN_DENYLIST = {
    "chrobinson.com",
    "landstarsystem.com",
    "truckstop.com",
    "dat.com",
    "comdata.com",
    "efsllc.com",
    "apexcapitalcorp.com",
    "rtsinc.com",
    "tafs.com",
}

REQUIRED_META_KEYS_TYPES = {
    "slug": str,
    "name": str,
    "audience": str,
    "subject": str,
    "from_name": str,
    "from_address": str,
    "difficulty": str,
    "lures": list,
    "trucking_context": str,
    "indicators": list,
}


def _template_dirs() -> list[Path]:
    return sorted(
        p for p in TEMPLATES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


class _Probe(HTMLParser):
    """Lightweight parser that records form/input shape and rejects parse errors."""

    def __init__(self) -> None:
        super().__init__()
        self.has_form = False
        self.has_password_input = False
        self.has_hidden_rid = False
        self.input_value_attrs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag == "form":
            self.has_form = True
        if tag == "input":
            itype = attr_dict.get("type", "").lower()
            iname = attr_dict.get("name", "").lower()
            ivalue = attr_dict.get("value", "")
            if itype == "password":
                self.has_password_input = True
            if itype == "hidden" and iname == "rid":
                self.has_hidden_rid = True
            if ivalue:
                self.input_value_attrs.append(ivalue)


@pytest.mark.parametrize("tdir", _template_dirs(), ids=lambda p: p.name)
def test_required_files_present(tdir: Path) -> None:
    for name in ("email.html", "landing.html", "meta.json"):
        assert (tdir / name).is_file(), f"{tdir.name}/{name} missing"


@pytest.mark.parametrize("tdir", _template_dirs(), ids=lambda p: p.name)
def test_meta_json_shape(tdir: Path) -> None:
    meta = json.loads((tdir / "meta.json").read_text(encoding="utf-8"))
    for key, typ in REQUIRED_META_KEYS_TYPES.items():
        assert key in meta, f"{tdir.name}/meta.json missing key {key!r}"
        assert isinstance(meta[key], typ), (
            f"{tdir.name}/meta.json[{key!r}] should be {typ.__name__}, "
            f"got {type(meta[key]).__name__}"
        )

    assert meta["slug"] == tdir.name, (
        f"meta.slug={meta['slug']!r} must match dir name {tdir.name!r}"
    )
    assert meta["audience"] in VALID_AUDIENCES, (
        f"{tdir.name}: audience {meta['audience']!r} not in {VALID_AUDIENCES}"
    )
    assert meta["difficulty"] in VALID_DIFFICULTY, (
        f"{tdir.name}: difficulty {meta['difficulty']!r} not in {VALID_DIFFICULTY}"
    )
    assert meta["lures"], f"{tdir.name}: lures must be non-empty"
    bad_lures = [lure for lure in meta["lures"] if lure not in VALID_LURES]
    assert not bad_lures, f"{tdir.name}: unknown lures {bad_lures}"
    assert meta["indicators"], f"{tdir.name}: indicators must be non-empty"


@pytest.mark.parametrize("tdir", _template_dirs(), ids=lambda p: p.name)
def test_from_address_not_real_domain(tdir: Path) -> None:
    meta = json.loads((tdir / "meta.json").read_text(encoding="utf-8"))
    addr = meta["from_address"].lower().strip()
    assert "@" in addr, f"{tdir.name}: from_address must look like an email"
    domain = addr.rsplit("@", 1)[1]
    for real in REAL_DOMAIN_DENYLIST:
        assert not (domain == real or domain.endswith("." + real)), (
            f"{tdir.name}: from_address {addr!r} resolves to real domain {real!r} "
            "— refuse to ship a template that could be mistaken for or used "
            "against a real organization."
        )


@pytest.mark.parametrize("tdir", _template_dirs(), ids=lambda p: p.name)
def test_email_html_has_required_tokens(tdir: Path) -> None:
    body = (tdir / "email.html").read_text(encoding="utf-8")
    probe = _Probe()
    probe.feed(body)  # parse smoke-test; any malformed HTML raises here

    pixel_pattern = re.compile(
        r'<img[^>]*src=["\']\{\{\.TrackingURL\}\}["\'][^>]*>',
        re.IGNORECASE,
    )
    assert pixel_pattern.search(body), (
        f"{tdir.name}/email.html missing the {{{{.TrackingURL}}}} tracking-pixel <img> "
        "(Gophish needs it for open-tracking)."
    )
    assert "{{.URL}}" in body, (
        f"{tdir.name}/email.html must include at least one {{{{.URL}}}} "
        "click-through link."
    )


@pytest.mark.parametrize("tdir", _template_dirs(), ids=lambda p: p.name)
def test_landing_html_form_shape(tdir: Path) -> None:
    body = (tdir / "landing.html").read_text(encoding="utf-8")
    probe = _Probe()
    probe.feed(body)

    assert probe.has_form, f"{tdir.name}/landing.html missing <form>"
    assert probe.has_password_input, (
        f"{tdir.name}/landing.html: a credential-harvest landing page must "
        "have an <input type='password'> — that's what Gophish counts as "
        "a credential submission."
    )
    assert probe.has_hidden_rid, (
        f"{tdir.name}/landing.html: must include "
        "<input type='hidden' name='rid' value='{{.RId}}'> so Gophish can "
        "correlate the submission to the recipient."
    )

    # Guardrail: never ship literal credential strings or {{.Password}} echoes.
    assert "{{.Password}}" not in body, (
        f"{tdir.name}/landing.html: {{{{.Password}}}} is not a real Gophish "
        "token and looks like an attempt to echo a password — remove it."
    )
    forbidden_value = re.compile(
        r'value\s*=\s*["\']password["\']', re.IGNORECASE,
    )
    assert not forbidden_value.search(body), (
        f"{tdir.name}/landing.html: literal value=\"password\" present — the "
        "form must never pre-populate or display a credential."
    )


def test_all_expected_slugs_present() -> None:
    found = {p.name for p in _template_dirs()}
    missing = EXPECTED_SLUGS - found
    assert not missing, f"missing expected template directories: {sorted(missing)}"
