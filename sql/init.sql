-- Email Security Gateway — Postgres schema
-- Loaded once on first postgres container boot (docker-entrypoint-initdb.d)

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── Reputation feeds ──────────────────────────────────────────────────
-- Populated by feeds/ service. Rspamd queries this for URL/domain scoring.
CREATE TABLE IF NOT EXISTS reputation (
    id          BIGSERIAL PRIMARY KEY,
    indicator   TEXT NOT NULL,                  -- url, domain, or hash
    kind        TEXT NOT NULL,                  -- 'url' | 'domain' | 'sha256'
    source      TEXT NOT NULL,                  -- 'gsb' | 'phishtank' | 'openphish' | 'dnstwist'
    verdict     TEXT NOT NULL,                  -- 'malicious' | 'suspicious' | 'lookalike'
    metadata    JSONB DEFAULT '{}'::jsonb,
    first_seen  TIMESTAMPTZ DEFAULT now(),
    last_seen   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(indicator, kind, source)
);
CREATE INDEX IF NOT EXISTS idx_reputation_indicator ON reputation(indicator);
CREATE INDEX IF NOT EXISTS idx_reputation_last_seen ON reputation(last_seen);

-- ─── Mail audit log ────────────────────────────────────────────────────
-- Every inbound mail produces one row. Shadow mode logs but does not block.
CREATE TABLE IF NOT EXISTS mail_audit (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_id        TEXT,
    received_at     TIMESTAMPTZ DEFAULT now(),
    sender          TEXT,
    sender_domain   TEXT,
    rcpt            TEXT[],
    subject         TEXT,
    score           NUMERIC(6,2),
    verdict         TEXT,                        -- 'deliver' | 'quarantine' | 'spam' | 'shadow_pass' | 'shadow_flag'
    matched_rules   TEXT[],
    urls            TEXT[],
    attachments     JSONB DEFAULT '[]'::jsonb,
    detonator_calls JSONB DEFAULT '[]'::jsonb,
    raw_headers     TEXT
);
CREATE INDEX IF NOT EXISTS idx_mail_audit_received ON mail_audit(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_mail_audit_verdict  ON mail_audit(verdict);
CREATE INDEX IF NOT EXISTS idx_mail_audit_sender   ON mail_audit(sender_domain);

-- ─── Quarantine ────────────────────────────────────────────────────────
-- Mails held for security-team review. Released or deleted via admin UI.
CREATE TABLE IF NOT EXISTS quarantine (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id        UUID REFERENCES mail_audit(id) ON DELETE CASCADE,
    raw_path        TEXT NOT NULL,               -- pointer to mbox file on disk
    created_at      TIMESTAMPTZ DEFAULT now(),
    reviewed_by     TEXT,
    reviewed_at     TIMESTAMPTZ,
    action          TEXT                         -- 'released' | 'deleted' | 'reported_phish'
);

-- ─── Allowlists / blocklists (admin-managed) ───────────────────────────
CREATE TABLE IF NOT EXISTS allowlist (
    id          BIGSERIAL PRIMARY KEY,
    indicator   TEXT NOT NULL,                   -- domain, sender, or DKIM key
    kind        TEXT NOT NULL,                   -- 'domain' | 'sender' | 'dkim'
    note        TEXT,
    added_by    TEXT,
    added_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(indicator, kind)
);

CREATE TABLE IF NOT EXISTS blocklist (
    id          BIGSERIAL PRIMARY KEY,
    indicator   TEXT NOT NULL,
    kind        TEXT NOT NULL,
    reason      TEXT,
    added_by    TEXT,
    added_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(indicator, kind)
);

-- ─── Detonation cache ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS detonation (
    url_hash        TEXT PRIMARY KEY,            -- sha256 of normalized URL
    url             TEXT NOT NULL,
    final_url       TEXT,
    verdict         TEXT,                        -- 'clean' | 'phishing' | 'malware' | 'unknown'
    has_login_form  BOOLEAN,
    screenshot_path TEXT,
    network_log     JSONB,
    cached_until    TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_detonation_cached_until ON detonation(cached_until);

-- ─── Phishing simulation (Phase 3) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS sim_campaign (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    template        TEXT,
    audience        TEXT,                        -- 'dispatchers' | 'drivers' | 'accounting' | 'all'
    sent_at         TIMESTAMPTZ,
    landing_domain  TEXT
);

CREATE TABLE IF NOT EXISTS sim_event (
    id              BIGSERIAL PRIMARY KEY,
    campaign_id     UUID REFERENCES sim_campaign(id) ON DELETE CASCADE,
    employee_email  TEXT NOT NULL,
    event_type      TEXT NOT NULL,               -- 'sent' | 'opened' | 'clicked' | 'submitted' | 'reported'
    occurred_at     TIMESTAMPTZ DEFAULT now(),
    metadata        JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_sim_event_campaign ON sim_event(campaign_id);
CREATE INDEX IF NOT EXISTS idx_sim_event_employee ON sim_event(employee_email);
