FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads static/reports logs

EXPOSE 10000

CMD ["sh", "-c", "gunicorn wsgi:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-10000}"]
