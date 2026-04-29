# Email Security Gateway

Self-hosted email defense + phishing-simulation stack for small-to-mid-size companies. Built specifically with the **trucking / TMS industry** in mind — typosquatted load-board domains, fake rate confirmations, fake ELD alerts, and broker wire-instruction scams are first-class threats here, not afterthoughts.

Open-source. Docker-first. Designed to deploy on Railway, Fly.io, or any docker-compose host.

> **Status:** Phase 1 scaffolding. Inbound filtering works. Detonation sandbox and phishing simulator are stubbed. See [Roadmap](#roadmap).

---

## What it does

**Inbound (defense):**
- Routes incoming mail through **Postfix** → **Rspamd** before delivery.
- Scores mail against multiple free reputation feeds: **Google Safe Browsing**, **PhishTank**, **OpenPhish**.
- Detects sender-domain **lookalikes / typosquats** (e.g. `hlghway.com`, `tm5360.com`) using a `dnstwist`-generated weekly blocklist of your trusted domains.
- Blocks **risky attachment extensions** (`.exe`, `.scr`, `.lnk`, `.iso`, macro-enabled Office, etc.).
- Logs every verdict to Postgres for audit and tuning.
- **Shadow mode by default** — never blocks anything until you've watched two weeks of traffic and tuned the false-positive rate. Then flip one env var to enforce.

**Outbound (training, Phase 3):**
- **Gophish** sends scheduled phishing-simulation campaigns to your employees.
- Trucking-specific templates: load offers, rate confirmations, ELD compliance alerts, settlement statements, fake DOT notices, broker wire-instruction changes.
- Tracks click rate, report rate, repeat clickers, and credential-form submission (without storing actual passwords).

---

## Why

If you run a TMS, dispatch office, or carrier company, you've already seen this:

- A dispatcher logs into `truckstop-portal.net` thinking it's `truckstop.com`. Credentials gone.
- An accountant changes a broker's wire instructions because the email "from `chrobinson.com`" was actually from `chr0binson.com`.
- A driver clicks a fake DOT inspection notice and types their CDL/SSN into a "compliance portal".

Generic spam filters (M365, Gmail, free SpamAssassin) **miss this class** because the lures are industry-specific and the lookalike domains are freshly registered. This stack closes that gap with cheap, self-hosted defenses + ongoing training.

---

## Quick start (local)

You'll need Docker, docker-compose, and ~5 minutes.

```bash
git clone https://github.com/<you>/email-security-gateway.git
cd email-security-gateway

cp .env.example .env
$EDITOR .env                       # set CORP_DOMAIN, GATEWAY_HOSTNAME, TRUSTED_DOMAINS

docker compose up -d postgres redis
docker compose logs -f postgres    # wait for "database system is ready"

docker compose up -d feeds         # populates reputation + lookalike maps
docker compose up -d rspamd        # config-tests on build; will fail loudly if broken
docker compose up -d postfix
```

Smoke test — send a test message through Postfix:

```bash
docker compose exec postfix sh -c '\
    echo "Subject: hello\n\nbody with link http://malicious.example/login" \
    | sendmail -f from@example.org user@${CORP_DOMAIN}'
docker compose logs rspamd | grep AUDIT
```

You should see an `AUDIT score=… symbols=…` log line. That's a real Rspamd verdict.

---

## Configuration

Everything lives in `.env`. The important variables:

| Variable | Purpose |
|---|---|
| `CORP_DOMAIN` | The domain whose mail flows through this gateway, e.g. `acme-trucking.com` |
| `GATEWAY_HOSTNAME` | The MX hostname, e.g. `mail.acme-trucking.com` |
| `TRUSTED_DOMAINS` | Comma-separated list seeded into `dnstwist` to generate the typosquat blocklist. Include your own domain plus all the load boards, brokers, ELD vendors, and banks your team interacts with daily |
| `GSB_API_KEY` | [Google Safe Browsing](https://developers.google.com/safe-browsing/v4/get-started) — free |
| `PHISHTANK_APP_KEY` | Optional; PhishTank works without a key but rate-limits without one |
| `OPENPHISH_API_KEY` | Optional; community feed is free |
| `GATEWAY_MODE` | `shadow` (default; logs only) or `enforce` (blocks/quarantines) |
| `SHADOW_BCC` | Where to BCC every inbound mail in shadow mode for human review |

See `.env.example` for the full list.

---

## Deployment

### Railway (or any per-service container host)

The compose file maps cleanly to Railway services. One service per build context:

| Railway service | Build context | Notes |
|---|---|---|
| `postgres` | Use Railway's managed Postgres plugin | Cheaper than self-hosted |
| `redis` | Use Railway's managed Redis plugin | |
| `postfix` | `./postfix` | Expose TCP 25 (and 587) via Railway's TCP proxy |
| `rspamd` | `./rspamd` | Internal-only |
| `feeds` | `./feeds` | Internal-only; runs cron |

Paste your `.env` into each service's **Variables** tab. Use Railway's `${{Postgres.PGHOST}}` template references for the DB hosts.

Run the SQL init once after first boot:
```bash
psql $POSTGRES_URL -f sql/init.sql
```

### Generic VPS / docker-compose host

Just `docker compose up -d` on a Linux box. You'll need:
- Inbound TCP 25 reachable from the public internet
- A subdomain (`mail.your-corp.com`) with an A record pointing at the host
- **Reverse DNS** for that A record (most VPS providers let you set rDNS in their dashboard) — recipient mail servers reject inbound from hosts with no rDNS

### MX cutover

Once you've watched the stack in shadow mode for ~2 weeks against real traffic (BCCing the office mailbox is enough — no MX change yet), do the cutover:

1. Lower the TTL of your existing MX record to 300s a day in advance.
2. Add a secondary MX pointing at this gateway, *higher* priority (lower number) than the existing.
3. Watch logs. Mail should start flowing through the gateway.
4. Configure SPF (`v=spf1 mx -all`), DKIM (`rspamadm dkim_keygen -s mail -d your-corp.com`), DMARC (`v=DMARC1; p=none; rua=mailto:dmarc@your-corp.com`).
5. After a week of clean delivery, demote the old MX to fallback or remove it.

Full step-by-step in **[docs/DEPLOY.md](docs/DEPLOY.md)**.

---

## Operating it

| Task | How |
|---|---|
| **Daily quarantine review** | Open the BCC mailbox, judge real / phish / sim, allowlist false positives |
| **Add a real partner domain to allowlist** | Append to `rspamd/lists/allowlist.map`, redeploy. Rspamd reloads maps on change — no restart |
| **Refresh typosquat list** | Runs automatically weekly. Manual: `docker compose exec feeds python dnstwist_runner.py` |
| **Refresh reputation feeds** | Runs hourly. Manual: `docker compose exec feeds python feed_pull.py` |
| **Switch from shadow to enforce** | Change `GATEWAY_MODE=enforce` in `.env`, restart Postfix + Rspamd |
| **Investigate a clicked link** | `psql $POSTGRES_URL` → query `mail_audit` for the recipient + URL |

Full operator playbook in **[docs/RUNBOOK.md](docs/RUNBOOK.md)** including incident response, false-positive surge handling, and the phishing-simulation operator checklist.

---

## Project structure

```
email_security/
├── docker-compose.yml      Full stack — shadow mode by default
├── .env.example            All configuration knobs
├── postfix/                Postfix Dockerfile + main.cf template + milter wiring
├── rspamd/
│   ├── local.d/            Module overrides (phishing, multimap, redis, actions)
│   ├── lists/              Allowlist, lookalike domains, known-phish URLs, risky extensions
│   └── lua/                Custom scoring (audit, detonator hook)
├── feeds/                  Python + cron — pulls reputation feeds, runs dnstwist
├── detonator/              [Phase 2] Hardened Playwright/Chromium URL sandbox
├── gophish/                [Phase 3] Phishing-simulation config + trucking templates
├── admin-ui/               [Phase 3] Vite/React review dashboard
├── sql/init.sql            Postgres schema
└── docs/
    ├── ARCHITECTURE.md     Component diagram + data flow + isolation boundaries
    ├── DEPLOY.md           Step-by-step deployment + MX cutover + DKIM/SPF/DMARC
    └── RUNBOOK.md          Daily / weekly / incident playbooks
```

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| **1** | Postfix + Rspamd + reputation feeds + dnstwist + attachment blocklist + audit log. Shadow mode. | ✅ Scaffold complete |
| **2** | Headless-Chrome **URL detonation sandbox** with login-form detection, hardened Docker isolation, verdict caching | ⏳ Stubbed (Lua hook prepped) |
| **3** | **Gophish** simulation campaigns + 8–10 trucking-specific templates + employee sync + metrics dashboard | ⏳ |
| **4** | **CAPE Sandbox** for runnable-attachment detonation (only if attachment-based attacks land) | 📦 Deferred |

PRs welcome for Phase 2 / 3 work — see issues for breakdown.

---

## Caveats — what this does *not* defend against

Be honest about scope:

- **Compromised real broker accounts** — real domain, real DKIM. We can't tell. Out-of-band verification (call the broker before any wire change) is the human control.
- **Voice / SMS phishing** — different channel.
- **Encrypted attachments with the password in the email body** — gateway can flag the pattern, not scan the contents.
- **Time-bombed URLs** — a link benign at scan time can serve a phishing kit hours later. Mitigation requires URL rewriting (rewrite all links to `gateway.your-corp.com/click?u=...` and re-scan on click); not in Phase 2.
- **Sandbox-aware phishing kits** — residential proxies + cursor heuristics defeat headless Chrome. Commercial gateways have similar gaps; mitigation is partial.

If your threat model includes nation-state-grade adversaries, this is one layer in a defense-in-depth stack, not a replacement for an enterprise email security gateway.

---

## Security & ethics disclaimer

This is **defensive** security tooling. The phishing-simulation half is for **internal employee training only**, with these guardrails:

- ✅ Employees notified in onboarding policy that simulated phishing is part of training.
- ✅ Per-user data restricted to security team + HR. Aggregate reporting only when shared more widely.
- ✅ Gophish credential-capture configured to record `submission_occurred` only — **no real passwords stored**.
- ✅ Repeat clickers get 1-on-1 training, never punishment.
- ✅ For EU employees: GDPR processing record on file (legitimate-interest basis); works-council notified in jurisdictions that require it (Germany, France).

**Do not** use this stack to phish anyone outside your own organization. Do not use it to simulate against systems you do not own. Use of these tools against unauthorized targets is illegal in most jurisdictions.

---

## License

MIT — see [LICENSE](LICENSE). (Add your preferred license file before publishing.)

## Acknowledgments

Built on the shoulders of:
- [Postfix](http://www.postfix.org/) — the mail transport
- [Rspamd](https://rspamd.com/) — the modern spam filter
- [dnstwist](https://github.com/elceef/dnstwist) — typosquat permutation engine
- [Gophish](https://getgophish.com/) — open-source phishing toolkit
- [PhishTank](https://phishtank.org/), [OpenPhish](https://openphish.com/), [Google Safe Browsing](https://safebrowsing.google.com/) — reputation feeds
