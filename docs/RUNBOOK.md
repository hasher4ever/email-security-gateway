# Runbook

For the on-call security operator. Bookmark this page.

## Setup

- **Seed demo data for the admin-ui** (before live mail flow): `psql $POSTGRES_URL -f sql/seed.sql`. Idempotent; safe to re-run.

## Daily

1. Open the quarantine BCC mailbox. Skim subject lines.
2. For each held message, judge: real / phishing / sim.
3. **False positives** (real mail held): add the sender domain or DKIM key to the allowlist (`rspamd/lists/allowlist.map` — append + commit). Release the mail from the quarantine UI.
4. **True phishing**: report to PhishTank / OpenPhish so the community feed catches the next one. Forward to internal phishing-report inbox for awareness training.
5. **Sim**: tag in dashboard, no action.

## Weekly

1. Review the **detonation cache** — anything with verdict `unknown` for >7 days? Re-run or expire.
2. Re-run `dnstwist_runner.py` ad-hoc if a major broker / load-board domain was just added: `docker compose exec feeds python dnstwist_runner.py`.
3. Check `mail_audit` — sample 10 random `verdict='deliver'` rows. Spot-check for missed phishing.
4. Update `rspamd/lists/allowlist.map` from new partner sign-ups.
5. Read the Phase 3 simulation dashboard. If a campaign is mid-flight, watch the report-rate trend.

## Incident — credential theft suspected

1. Pull all `mail_audit` rows for the affected employee in the last 30 days.
2. Filter for `verdict IN ('shadow_pass','deliver')` AND `urls && ARRAY[...]` of suspect URLs.
3. Identify the source mail, its sender, the URL.
4. Rotate the employee's TMS360 / email / VPN credentials immediately.
5. Add the source domain to `rspamd/lists/blocklist.map` and to PhishTank.
6. Re-run `feed_pull.py` on demand: `docker compose exec feeds python feed_pull.py`.
7. Audit other employees who received mail from the same sender — identical IOC search.
8. Post-incident: write a one-page memo, tag it in the runbook history. Was this catchable at the gateway? If yes, what rule needs to change?

## Incident — gateway down (no mail flowing)

1. **Symptom**: senders see SMTP errors / mail bouncing / silent gap in inbox.
2. Check Railway dashboard — all services green?
3. Tail logs: `docker compose logs -f postfix rspamd`.
4. **Postfix dead**: senders' MX retry hits the secondary MX (your old provider). No data loss yet — investigate the cause.
5. **Rspamd dead**: in `main.cf`, set `milter_default_action = accept` and reload Postfix. Mail flows unfiltered until Rspamd is fixed.
6. **Postgres dead**: Rspamd loses audit log + multimap-from-DB queries. Maps from disk still work; verdicts log to stdout. Restore from Railway backup.

## Incident — false positive surge

1. Symptom: legit broker emails showing up in quarantine; dispatcher complaints.
2. Pull the Rspamd verbose log for one example: `rspamc symbols < /path/to/raw_mail.eml`.
3. Identify the false-positive symbol. Common offenders:
   - `LOOKALIKE_SENDER` — dnstwist false positive on a real broker domain. Add to allowlist.
   - `RISKY_ATTACHMENT_EXT` — broker sent a `.docm`. Add the broker's domain to allowlist (better: ask them to send PDF).
   - `KNOWN_PHISH_URL` — feed false positive (PhishTank wrong). Allowlist the URL.
4. Push the change. No service restart needed for `.map` files (Rspamd reloads them on change).

## Phishing-simulation operator playbook

1. **Schedule** — first Tuesday of the month, 09:00 corp time. Avoid major holidays.
2. **Audience** — rotate. Month 1: dispatchers. Month 2: drivers. Month 3: accounting. Month 4: all.
3. **Template** — pick one from `gophish/templates/`. Vary by audience (load offer for dispatchers, ELD alert for drivers, wire-instruction for accounting).
4. **Landing domain** — use a registered lookalike that we own (`tms360-portal.io`). Renew yearly.
5. **Pre-flight** — allowlist the Gophish sender IP + DKIM in our own gateway so the sim isn't quarantined by us.
6. **Send + monitor** — first hour shows most clicks; tail the dashboard.
7. **Post-mortem** — share aggregate metrics in the next all-hands. **Never** name individuals publicly. Repeat clickers get 1:1 training, not punishment.

## Compliance checklist

- [ ] Employees notified in onboarding policy that simulated phishing is part of training.
- [ ] Per-user data restricted to security team + HR.
- [ ] Aggregate reporting only when sharing externally.
- [ ] No real passwords stored — Gophish credential-capture set to record `submission_occurred` only, not the typed string.
- [ ] If an EU-based employee → GDPR processing record on file (legitimate-interest basis, security training).
- [ ] Works-council notified (Germany / France) before any per-user reporting goes live.
