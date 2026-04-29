# Architecture

Tracking ticket: [Jira DEV-581](https://infomaxmgt-team.atlassian.net/browse/DEV-581) (local file `jira_vault/tickets/DEV-585.md`).

## Component diagram

```
                  ┌─────────────────────────────────────────────┐
                  │  Public internet                            │
                  │  ┌──────────┐                               │
                  │  │ Sender   │ ── SMTP ──┐                   │
                  │  └──────────┘           │                   │
                  └─────────────────────────┼───────────────────┘
                                            │
                                            ▼ port 25
                                ┌──────────────────────┐
                                │   svc-A: Postfix     │
                                │   (MX target)        │
                                │   shadow BCC enabled │
                                └──────────┬───────────┘
                                           │ milter (port 11332)
                                           ▼
                          ┌─────────────────────────────────┐
                          │   svc-B: Rspamd                 │
                          │  ┌───────────────────────────┐  │
                          │  │ multimap (lookalike,      │  │
                          │  │   known_phish, allowlist, │  │
                          │  │   risky_extensions)       │  │
                          │  ├───────────────────────────┤  │
                          │  │ phishing module           │  │
                          │  │ url_reputation            │  │
                          │  │ DKIM/SPF/DMARC            │  │
                          │  ├───────────────────────────┤  │
                          │  │ lua/audit.lua             │  │
                          │  │ lua/detonate.lua (Phase 2)│  │
                          │  └───────────┬───────────────┘  │
                          └──────────────┼──────────────────┘
                              ▲          │           ▲
                              │ reads    │ verdict   │ writes
                              │ maps     │           │ audit
                              │          │           │
            ┌─────────────────┴┐    ┌────┴───┐  ┌───┴─────────┐
            │ rspamd/lists/    │    │ Postfix │  │ Postgres    │
            │  - known_phish   │    │ delivers│  │ (mail_audit │
            │  - lookalike_dom │    │ or BCCs │  │  reputation │
            │  - allowlist     │    │ to     │  │  detonation │
            │  - risky_ext     │    │ inbox   │  │  sim_*)     │
            └────────▲─────────┘    └─────────┘  └─────────────┘
                     │                                ▲
                     │ writes maps                    │ writes
                     │                                │
            ┌────────┴───────────────────────────────┴────┐
            │   svc-feeds (Python + cron)                 │
            │   - feed_pull.py (hourly)                   │
            │       PhishTank / OpenPhish / GSB           │
            │   - dnstwist_runner.py (weekly)             │
            │       TRUSTED_DOMAINS → lookalike_domains   │
            └─────────────────────────────────────────────┘

   ─── Phase 2 additions ──────────────────────────────────────────────
   svc-C: Detonator   (Playwright + headless Chromium, hardened Docker)
                      called by Rspamd Lua for unknown URLs
                      isolated network, dropped caps, read-only FS
   ─── Phase 3 additions ──────────────────────────────────────────────
   svc-D: Gophish     (outbound phishing simulations to employees)
   svc-E: Admin UI    (Vite/React; quarantine review + sim metrics)
```

## Data flow — inbound mail

1. MX record points at `mail.<corp_domain>`. Sender connects to **Postfix** on port 25.
2. Postfix accepts the envelope, hands the message to **Rspamd** over the milter protocol (port 11332) before queueing.
3. Rspamd evaluates:
   - **DKIM/SPF/DMARC** — built-in modules.
   - **multimap** rules — sender domain against `lookalike_domains.map`, body URLs against `known_phish.map`, attachments against `risky_extensions.map`, allowlist for known-good senders.
   - **phishing** module — display-name/URL mismatch + open feeds.
   - **url_reputation** — historical sender behavior cached in Redis.
   - **detonate.lua** (Phase 2) — sends unknown URLs to detonator.
   - **audit.lua** — logs the verdict and matched symbols (Phase 1 logs to stdout; Phase 1.1 ships rows to Postgres via Redis pub/sub).
4. Rspamd returns a score and one of: `no action`, `add header`, `greylist`, `reject`. Score thresholds in `actions.conf`.
5. **Shadow mode**: Postfix delivers regardless and BCCs the mail to the quarantine address for human review.
6. **Enforce mode**: scores ≥ 15 → reject (5xx); 6–14 → header tag + spam folder; <6 → deliver clean.

## Storage

- **Postgres** — durable audit log, reputation feed cache, quarantine pointers, simulation results.
- **Redis** — Rspamd's transient cache (URL reputation, fuzzy hashes, greylist), and Phase 2 detonation verdict cache (24h TTL).

## Security boundaries (Phase 2 detonator)

The detonator runs Chromium against possibly-malicious URLs. Mandatory isolation:

- Separate Railway service / container.
- `read_only: true` filesystem.
- `cap_drop: [ALL]` + `no-new-privileges`.
- `tmpfs` for `/tmp` and `/var/run` only.
- No host-volume mounts.
- Dedicated Docker network with `internal: false` for outbound web access, but no route to the rest of the stack (Postgres, Redis, Postfix unreachable).
- Egress firewall — allow 80/443 only.
- Per-URL container teardown (no long-lived browser between scans) so a successful exploit cannot persist.

## What this stack does NOT defend against

- **Compromised legitimate broker accounts** — real domain, real DKIM. Out of scope; flagged in RUNBOOK.
- **Voice / SMS phishing** — different channel.
- **Encrypted attachments with password in body** — gateway can flag, can't scan.
- **Time-bombed URLs** — benign on detonation, malicious post-delivery. Phase 3+ requires URL rewriting (rewrite all links to `gateway.example.com/click?u=...` and re-scan on click).
- **Sandbox-aware phishing kits** — residential proxies + cursor heuristics defeat headless Chrome; mitigation is out-of-band and partial (commercial gateways have similar gaps).
