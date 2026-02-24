FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8100/health || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8100", "--workers", "2", "app:app"]
