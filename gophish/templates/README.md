# Phishing-simulation templates

Trucking-industry training templates for the Phase 3 Gophish simulator.
Each subdirectory is one template:

- `email.html` — the simulated phishing email body (Gophish tokens: `{{.FirstName}}`, `{{.URL}}`, `{{.TrackingURL}}`, etc.)
- `landing.html` — the credential-harvest page shown if the recipient clicks
- `meta.json` — audience, difficulty, lures, indicators, and a 1-line note on why the lure is industry-relevant

## Safety rules — read before importing

These templates are **for internal employee training only** against the
organization that operates this gateway. Do not point a campaign at any
mailbox you do not control or have written authorization to test.
Configure Gophish with `Capture Credentials = true` but **never** with
`Capture Submitted Data = true` against the password field — see
`SECURITY.md` and the README's "Security & ethics disclaimer".

The `from_address` values use deliberately fictional typosquat domains
(e.g. `chr0binson.com`, `landstarsystem-portal.net`). The accompanying test
suite (`_test_templates.py`) refuses to ship a template whose `from_address`
points at a real broker, load-board, or factoring domain.

## Importing into Gophish

Gophish has no folder-import: you upload one Email Template and one Landing
Page per template via the Gophish UI or API. See the upstream docs:
<https://docs.getgophish.com/user-guide/documentation/templates>.

Paste the contents of `email.html` into a new Email Template, the contents of
`landing.html` into a new Landing Page, and use `meta.json` to configure the
campaign's subject, sender, and audience group.

## Tests

```bash
python -m pytest gophish/templates/_test_templates.py -q
```
