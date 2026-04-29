FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY feed_pull.py dnstwist_runner.py crontab /app/
RUN crontab /app/crontab

CMD ["cron", "-f"]
