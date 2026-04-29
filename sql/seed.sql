-- Demo seed for the admin-ui — populates mail_audit, quarantine, sim_campaign,
-- sim_event so the dashboard has something to render before live mail flows.
-- Safe to re-run: every insert uses ON CONFLICT DO NOTHING or temp UUIDs.

BEGIN;

-- Clear any rows from a previous seed run so totals stay stable on re-run.
DELETE FROM sim_event    WHERE campaign_id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333'
);
DELETE FROM sim_campaign WHERE id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333'
);
DELETE FROM quarantine   WHERE audit_id IN (SELECT id FROM mail_audit WHERE rcpt && ARRAY['user1@example.com','user2@example.com','user3@example.com','user4@example.com','user5@example.com','user6@example.com','user7@example.com','user8@example.com','user9@example.com','user10@example.com','user11@example.com','user12@example.com','user13@example.com','user14@example.com','user15@example.com','user16@example.com','user17@example.com','user18@example.com','user19@example.com']);
DELETE FROM mail_audit   WHERE sender_domain IN (
    'chr0binson.com','truckstop-portal.net','fmcsa-eld-portal.net','landstarsystem-portal.net',
    'comdata-driver-portal.net','tafs-carrier-portal.co','us-dot-inspection.net',
    'driver-settlements-portal.co','apex-capitalcorp.net','office365-loginalerts.com',
    'chrobinson-payments.net','dat-loadboard.co','efs-cardholder.net','rts-financial-portal.com',
    'docusign-secured-mail.net','fastfreight-brokers.co','payroll-portal-hr.net',
    'docu-sign-trk.com','dispatchpro-cloud.net','example.com'
);

-- ─── mail_audit + quarantine ───────────────────────────────────────────
WITH samples (idx, sender, sender_domain, subject, score, verdict, rules, urls) AS (
    VALUES
    (1,  'dispatch@chr0binson.com',          'chr0binson.com',          'Revised rate confirmation — load 88241',           14.2, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN','URL_DETONATION'],    ARRAY['http://chr0binson.com/portal/login']),
    (2,  'noreply@truckstop-portal.net',     'truckstop-portal.net',    'New high-rate load posted near you',                12.7, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://truckstop-portal.net/claim?id=8841']),
    (3,  'compliance@fmcsa-eld-portal.net',  'fmcsa-eld-portal.net',    'Driver ELD violation detected — action required',   13.5, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN','PHISH_FEED'],          ARRAY['http://fmcsa-eld-portal.net/login']),
    (4,  'billing@landstarsystem-portal.net','landstarsystem-portal.net','URGENT: updated wire instructions effective Friday',16.0,'quarantine',  ARRAY['LOOKALIKE_DOMAIN','BEC_KEYWORDS','URL_DETONATION'],ARRAY['http://landstarsystem-portal.net/wire']),
    (5,  'noreply@comdata-driver-portal.net','comdata-driver-portal.net','Your fuel card has been suspended',                 11.4, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://comdata-driver-portal.net/reactivate']),
    (6,  'admin@tafs-carrier-portal.co',     'tafs-carrier-portal.co',  'Held factoring payment — login to release',         12.0, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN','URL_DETONATION'],      ARRAY['http://tafs-carrier-portal.co/release']),
    (7,  'inspect@us-dot-inspection.net',    'us-dot-inspection.net',   'DOT inspection scheduled — verify CDL details',     10.8, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://us-dot-inspection.net/cdl']),
    (8,  'pay@driver-settlements-portal.co', 'driver-settlements-portal.co','Your weekly settlement is ready',              9.4,  'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://driver-settlements-portal.co/login']),
    (9,  'support@apex-capitalcorp.net',     'apex-capitalcorp.net',    'Action required: invoice review',                   10.2, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://apex-capitalcorp.net/login']),
    (10, 'security@office365-loginalerts.com','office365-loginalerts.com','Unusual sign-in detected — verify now',           13.1, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN','PHISH_FEED'],          ARRAY['http://office365-loginalerts.com/verify']),
    (11, 'invoice@chrobinson-payments.net',  'chrobinson-payments.net', 'Past due invoice 99831',                            11.9, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://chrobinson-payments.net/inv?id=99831']),
    (12, 'no-reply@dat-loadboard.co',        'dat-loadboard.co',        'Premium load board access expiring',                10.0, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://dat-loadboard.co/renew']),
    (13, 'driver@efs-cardholder.net',        'efs-cardholder.net',      'EFS card balance alert',                             9.1, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://efs-cardholder.net/login']),
    (14, 'support@rts-financial-portal.com', 'rts-financial-portal.com','Funding request needs attention',                   11.0, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://rts-financial-portal.com/login']),
    (15, 'alerts@docusign-secured-mail.net', 'docusign-secured-mail.net','You have a secured document to review',            12.4, 'quarantine',  ARRAY['LOOKALIKE_DOMAIN','URL_DETONATION','RISKY_EXT'],ARRAY['http://docusign-secured-mail.net/sign']),
    (16, 'broker@fastfreight-brokers.co',    'fastfreight-brokers.co',  'Updated banking info for our carriers',             15.8, 'quarantine',  ARRAY['BEC_KEYWORDS','URL_DETONATION'],          ARRAY['http://fastfreight-brokers.co/wire']),
    (17, 'hr@payroll-portal-hr.net',         'payroll-portal-hr.net',   'Direct-deposit verification required',              13.6, 'quarantine',  ARRAY['LOOKALIKE_DOMAIN','PHISH_FEED'],          ARRAY['http://payroll-portal-hr.net/dd']),
    (18, 'noreply@docu-sign-trk.com',        'docu-sign-trk.com',       'Please review and sign — load BOL',                 12.9, 'quarantine',  ARRAY['LOOKALIKE_DOMAIN','URL_DETONATION'],      ARRAY['http://docu-sign-trk.com/sign?id=44']),
    (19, 'ops@dispatchpro-cloud.net',        'dispatchpro-cloud.net',   'Your dispatch session has expired',                 10.6, 'shadow_flag', ARRAY['LOOKALIKE_DOMAIN'],                       ARRAY['http://dispatchpro-cloud.net/relogin'])
)
INSERT INTO mail_audit (id, received_at, sender, sender_domain, rcpt, subject, score, verdict, matched_rules, urls, raw_headers)
SELECT
    gen_random_uuid(),
    now() - (s.idx * interval '37 minutes'),
    s.sender,
    s.sender_domain,
    ARRAY['user'||s.idx||'@example.com'],
    s.subject,
    s.score,
    s.verdict,
    s.rules,
    s.urls,
    'Received: from '||s.sender_domain||E'\nFrom: '||s.sender||E'\nSubject: '||s.subject
FROM samples s;

-- shadow_pass rows (UI ignores them, but they'll show up in any future "all mail" view)
INSERT INTO mail_audit (received_at, sender, sender_domain, rcpt, subject, score, verdict)
SELECT
    now() - (i * interval '12 minutes'),
    'partner'||i||'@example.com',
    'example.com',
    ARRAY['user'||i||'@example.com'],
    'Re: dispatch update '||i,
    1.5,
    'shadow_pass'
FROM generate_series(1, 10) AS i;

-- A handful of mail_audit rows get held in the quarantine table
INSERT INTO quarantine (audit_id, raw_path, created_at)
SELECT id, '/var/spool/quarantine/'||id||'.eml', received_at
FROM mail_audit
WHERE verdict = 'quarantine'
LIMIT 5
ON CONFLICT DO NOTHING;

-- ─── Phishing-simulation campaigns ─────────────────────────────────────
INSERT INTO sim_campaign (id, name, template, audience, sent_at, landing_domain) VALUES
    ('11111111-1111-1111-1111-111111111111'::uuid, 'Q2 broker wire change drill',  'broker-wire-instruction-change', 'accounting',  now() - interval '14 days', 'phishlab.example'),
    ('22222222-2222-2222-2222-222222222222'::uuid, 'ELD compliance phish (drivers)','eld-compliance-alert',           'drivers',     now() - interval '7 days',  'phishlab.example'),
    ('33333333-3333-3333-3333-333333333333'::uuid, 'Load-board lure (dispatchers)', 'load-board-rate-offer',          'dispatchers', now() - interval '2 days',  'phishlab.example')
ON CONFLICT (id) DO NOTHING;

-- realistic event funnel: sent > opened > clicked > submitted, plus some reported
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'acct'||i||'@example.com', 'sent',      now() - interval '14 days' + (i * interval '20 seconds') FROM generate_series(1, 25) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'acct'||i||'@example.com', 'opened',    now() - interval '14 days' + interval '2 hours'  + (i * interval '20 seconds') FROM generate_series(1, 18) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'acct'||i||'@example.com', 'clicked',   now() - interval '14 days' + interval '4 hours'  + (i * interval '20 seconds') FROM generate_series(1, 6) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'acct'||i||'@example.com', 'submitted', now() - interval '14 days' + interval '4 hours' + (i * interval '40 seconds') FROM generate_series(1, 2) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'acct'||i||'@example.com', 'reported',  now() - interval '14 days' + interval '1 hour'  + (i * interval '15 seconds') FROM generate_series(1, 4) i;

INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '22222222-2222-2222-2222-222222222222'::uuid, 'driver'||i||'@example.com','sent',      now() - interval '7 days' + (i * interval '15 seconds') FROM generate_series(1, 40) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '22222222-2222-2222-2222-222222222222'::uuid, 'driver'||i||'@example.com','opened',    now() - interval '7 days' + interval '3 hours' + (i * interval '15 seconds') FROM generate_series(1, 22) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '22222222-2222-2222-2222-222222222222'::uuid, 'driver'||i||'@example.com','clicked',   now() - interval '7 days' + interval '5 hours' + (i * interval '20 seconds') FROM generate_series(1, 11) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '22222222-2222-2222-2222-222222222222'::uuid, 'driver'||i||'@example.com','submitted', now() - interval '7 days' + interval '5 hours' + (i * interval '40 seconds') FROM generate_series(1, 5) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '22222222-2222-2222-2222-222222222222'::uuid, 'driver'||i||'@example.com','reported',  now() - interval '7 days' + interval '2 hours' + (i * interval '12 seconds') FROM generate_series(1, 3) i;

INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '33333333-3333-3333-3333-333333333333'::uuid, 'disp'||i||'@example.com', 'sent',      now() - interval '2 days' + (i * interval '8 seconds') FROM generate_series(1, 12) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '33333333-3333-3333-3333-333333333333'::uuid, 'disp'||i||'@example.com', 'opened',    now() - interval '2 days' + interval '1 hour' + (i * interval '8 seconds') FROM generate_series(1, 9) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '33333333-3333-3333-3333-333333333333'::uuid, 'disp'||i||'@example.com', 'clicked',   now() - interval '2 days' + interval '2 hours' + (i * interval '15 seconds') FROM generate_series(1, 4) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '33333333-3333-3333-3333-333333333333'::uuid, 'disp'||i||'@example.com', 'submitted', now() - interval '2 days' + interval '2 hours' + (i * interval '40 seconds') FROM generate_series(1, 1) i;
INSERT INTO sim_event (campaign_id, employee_email, event_type, occurred_at)
SELECT '33333333-3333-3333-3333-333333333333'::uuid, 'disp'||i||'@example.com', 'reported',  now() - interval '2 days' + interval '30 minutes' + (i * interval '20 seconds') FROM generate_series(1, 2) i;

COMMIT;
