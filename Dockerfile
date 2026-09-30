FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY . .

VOLUME ["/app/configs", "/app/logs", "/app/storage", "/app/plugins"]

CMD ["python", "main.py"]
