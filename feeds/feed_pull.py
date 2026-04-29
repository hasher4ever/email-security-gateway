"""Pull URL/domain reputation feeds into Postgres + materialize the
multimap file Rspamd consumes.

Run hourly via cron.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from pathlib import Path
from typing import Iterable

import psycopg
import requests

PG = dict(
    host=os.environ["POSTGRES_HOST"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    dbname=os.environ["POSTGRES_DB"],
)

GSB_KEY = os.environ.get("GSB_API_KEY", "").strip()
PHISHTANK_KEY = os.environ.get("PHISHTANK_APP_KEY", "").strip()
OPENPHISH_KEY = os.environ.get("OPENPHISH_API_KEY", "").strip()

OUT_MAP = Path("/out/lists/known_phish.map")


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ─── Source pullers ────────────────────────────────────────────────────

def pull_phishtank() -> Iterable[tuple[str, str, str]]:
    """PhishTank publishes a public CSV of verified phishing URLs."""
    url = "http://data.phishtank.com/data/online-valid.csv"
    headers = {"User-Agent": "esg-feed-puller/1.0"}
    if PHISHTANK_KEY:
        url = f"http://data.phishtank.com/data/{PHISHTANK_KEY}/online-valid.csv"
    try:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        log(f"phishtank fetch failed: {e}")
        return
    reader = csv.DictReader(io.StringIO(r.text))
    for row in reader:
        u = row.get("url")
        if u:
            yield (u, "url", "phishtank")


def pull_openphish() -> Iterable[tuple[str, str, str]]:
    """OpenPhish community feed — plain text, one URL per line."""
    url = "https://openphish.com/feed.txt"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        log(f"openphish fetch failed: {e}")
        return
    for line in r.text.splitlines():
        line = line.strip()
        if line and line.startswith("http"):
            yield (line, "url", "openphish")


def pull_gsb() -> Iterable[tuple[str, str, str]]:
    """Google Safe Browsing — Update API. We only sample a tiny slice for
    Phase 1; the full database sync is heavy. GSB's intended pattern is
    *lookup* (per-URL), not bulk pull, but the threatLists endpoint can list
    available threat types so the operator can verify the key works.
    """
    if not GSB_KEY:
        log("GSB_API_KEY not set — skipping Google Safe Browsing")
        return
    try:
        r = requests.get(
            f"https://safebrowsing.googleapis.com/v4/threatLists?key={GSB_KEY}",
            timeout=30,
        )
        r.raise_for_status()
        log(f"GSB threat lists available: {len(r.json().get('threatLists', []))}")
    except requests.RequestException as e:
        log(f"gsb probe failed: {e}")
    # Phase 1 leaves bulk-pull as TODO — the `gsb_lookup` Lua hook
    # should call the lookup API per-URL at scan time once detonator
    # caching is in place.
    return
    yield  # pragma: no cover  (keeps generator type)


# ─── DB upsert + map writer ────────────────────────────────────────────

def upsert(conn: psycopg.Connection, rows: list[tuple[str, str, str]]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO reputation (indicator, kind, source, verdict)
            VALUES (%s, %s, %s, 'malicious')
            ON CONFLICT (indicator, kind, source)
            DO UPDATE SET last_seen = now()
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def materialize_map(conn: psycopg.Connection) -> int:
    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    with conn.cursor() as cur, OUT_MAP.open("w") as f:
        cur.execute(
            """
            SELECT DISTINCT indicator FROM reputation
            WHERE kind = 'url' AND verdict IN ('malicious','suspicious')
              AND last_seen > now() - interval '14 days'
            """
        )
        n = 0
        for (url,) in cur:
            f.write(url + "\n")
            n += 1
    return n


def main() -> int:
    log("starting feed pull")
    rows: list[tuple[str, str, str]] = []
    rows.extend(pull_phishtank())
    rows.extend(pull_openphish())
    list(pull_gsb())  # probe-only for now

    with psycopg.connect(**PG) as conn:
        n_inserted = upsert(conn, rows)
        n_map = materialize_map(conn)

    log(f"upserted {n_inserted} indicators; wrote {n_map} entries to {OUT_MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
