#!/usr/bin/env bash
set -euo pipefail

# Render main.cf from template using env vars (CORP_DOMAIN, GATEWAY_MODE, SHADOW_BCC)
envsubst < /etc/postfix/main.cf.template > /etc/postfix/main.cf

# Build per-mode configuration: shadow appends a BCC of every inbound mail to
# SHADOW_BCC for human review without blocking delivery.
if [ "${GATEWAY_MODE:-shadow}" = "shadow" ] && [ -n "${SHADOW_BCC:-}" ]; then
    echo "always_bcc = ${SHADOW_BCC}" >> /etc/postfix/main.cf
fi

# Postfix wants the chroot dirs prepared
postfix set-permissions || true
postfix check

# Start rsyslog in the foreground for log capture, then postfix in the foreground
rsyslogd
exec postfix start-fg
