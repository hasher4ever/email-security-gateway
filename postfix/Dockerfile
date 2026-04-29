FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postfix \
        postfix-pcre \
        ca-certificates \
        rsyslog \
        gettext-base && \
    rm -rf /var/lib/apt/lists/*

COPY main.cf.template /etc/postfix/main.cf.template
COPY master.cf /etc/postfix/master.cf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 25 587

CMD ["/entrypoint.sh"]
