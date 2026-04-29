# Security Policy

## Reporting a vulnerability

If you've found a security issue in this project, **please do not open a public GitHub issue**. Disclosure-by-issue means everyone running this stack is exposed before a fix exists.

Instead, email the maintainer privately. Include:

- A description of the issue
- Steps to reproduce
- The affected component (Postfix config, Rspamd Lua, feed puller, detonator, Gophish wiring, etc.)
- Your assessment of impact (auth bypass, RCE, sandbox escape, data leak, DoS, etc.)
- Whether you'd like credit in the eventual advisory

Expect:
- An acknowledgement within **72 hours**.
- A first assessment within **7 days**.
- Coordinated disclosure on a timeline that fits the severity (typically 30–90 days).

## Scope

Anything in this repository — Docker images, configurations, Lua scoring, Python feed pullers, detonator service, deployment docs.

## Out of scope

- Vulnerabilities in upstream dependencies (Postfix, Rspamd, dnstwist, Gophish, Playwright, Chromium). Please report those upstream.
- Issues that require an attacker to already have administrative access to the host.
- Phishing-simulation templates (Phase 3) included as training material — these are *intentionally* deceptive by design.
- Configuration mistakes by an operator running an outdated copy of the stack — please update first and re-test.

## Hardening reminders

If you operate this stack:

- The detonator service (Phase 2) **must** run with `read_only: true`, `cap_drop: [ALL]`, and on an isolated Docker network with no route to your other internal services. Sandbox escape is a known risk class for headless Chromium.
- The phishing-simulation half (Phase 3) **must** be configured to never store real credentials. Capture only `submission_occurred` events.
- Reverse DNS and DKIM are required for outbound mail to be accepted by major receivers. Misconfigured DKIM is the most common cause of an operator's own mail landing in spam.
- Quarantined mail can contain credentials, PII, and phishing payloads. Restrict access to the security team and HR.
