"""Run dnstwist against TRUSTED_DOMAINS to generate a typosquat blocklist.

dnstwist permutates a domain into hundreds of lookalikes and resolves each
to see which are actually registered. Registered ones are far more likely
to be in active use for phishing than unregistered permutations.

Output:
    1. Postgres rows in `reputation` (kind='domain', source='dnstwist',
       verdict='lookalike').
    2. /out/lists/lookalike_domains.map — flat list Rspamd's multimap reads.

Run weekly via cron.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg

PG = dict(
    host=os.environ["POSTGRES_HOST"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    dbname=os.environ["POSTGRES_DB"],
)

TRUSTED = [d.strip() for d in os.environ.get("TRUSTED_DOMAINS", "").split(",") if d.strip()]
OUT_MAP = Path("/out/lists/lookalike_domains.map")


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def twist(domain: str) -> list[dict]:
    """Run dnstwist with --registered (only return live registrations) +
    JSON output."""
    try:
        proc = subprocess.run(
            ["dnstwist", "--format", "json", "--registered", domain],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        log(f"dnstwist timed out on {domain}")
        return []
    if proc.returncode != 0:
        log(f"dnstwist failed on {domain}: {proc.stderr[:200]}")
        return []
    try:
        return json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        log(f"dnstwist output not JSON for {domain}")
        return []


def run() -> int:
    if not TRUSTED:
        log("TRUSTED_DOMAINS empty — nothing to twist")
        return 1

    found: dict[str, dict] = {}
    for d in TRUSTED:
        log(f"twisting {d}")
        for perm in twist(d):
            name = perm.get("domain")
            if not name or name == d:
                continue
            # Skip the original itself; we only want lookalikes
            found[name] = {
                "source_domain": d,
                "fuzzer": perm.get("fuzzer"),
                "dns_a": perm.get("dns_a") or [],
                "dns_mx": perm.get("dns_mx") or [],
            }

    log(f"discovered {len(found)} registered lookalikes")

    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    with OUT_MAP.open("w") as f:
        for name in sorted(found):
            f.write(name + "\n")

    rows = [
        (name, "domain", "dnstwist", "lookalike", json.dumps(meta))
        for name, meta in found.items()
    ]
    if rows:
        with psycopg.connect(**PG) as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO reputation (indicator, kind, source, verdict, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (indicator, kind, source)
                DO UPDATE SET last_seen = now(), metadata = EXCLUDED.metadata
                """,
                rows,
            )
            conn.commit()

    log(f"wrote {len(found)} entries to {OUT_MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
