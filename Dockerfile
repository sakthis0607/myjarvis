FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# This makes sure Python finds config.py and core/ from /app
ENV PYTHONPATH=/app

EXPOSE 10000

CMD gunicorn "web.app:app" --bind "0.0.0.0:${PORT:-10000}" --workers 1 --timeout 120
