FROM rspamd/rspamd:3.10

USER root

# Custom configuration overrides
COPY local.d/ /etc/rspamd/local.d/
COPY lua/     /etc/rspamd/lua.local.d/
COPY lists/   /etc/rspamd/lists/

# Sanity check on container build
RUN rspamadm configtest

EXPOSE 11332 11333 11334
