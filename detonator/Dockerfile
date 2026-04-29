FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=7000 \
    SCREENSHOT_DIR=/tmp/screenshots

EXPOSE 7000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7000"]
