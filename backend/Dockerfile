FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True

WORKDIR /app

# Copy requirements from backend folder
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# Run the application
CMD ["sh", "-c", "exec uvicorn fastapi_integration.main:app --host 0.0.0.0 --port ${PORT:-8000}"]