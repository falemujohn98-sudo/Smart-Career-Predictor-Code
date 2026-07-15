FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True

WORKDIR /app

# Copy requirements from backend folder
COPY backend/requirements.txt .

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc g++ \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ backend/

# Copy other necessary files (app.py, data, etc.)
COPY . .

ENV PYTHONPATH=/app

# Run the application
CMD ["sh", "-c", "exec uvicorn backend.fastapi_integration.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir /app"]