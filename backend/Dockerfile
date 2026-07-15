# Use Python 3.11 (pandas==3.0.2 requires >=3.11)
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in logs
ENV PYTHONUNBUFFERED=True

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Run the web service (adjusted to your project structure)
CMD ["sh", "-c", "exec uvicorn backend.fastapi_integration.main:app --host 0.0.0.0 --port ${PORT:-8000}"]