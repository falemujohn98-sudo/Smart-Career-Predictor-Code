# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim-bullseye

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True

# Set working directory
WORKDIR /app

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install system dependencies using HTTPS package mirrors to avoid HTTP redirect/proxy issues
RUN sed -i 's|http://deb.debian.org/debian|https://deb.debian.org/debian|g; s|http://security.debian.org/debian-security|https://security.debian.org/debian-security|g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set PYTHONPATH so python can resolve modules correctly
ENV PYTHONPATH=/app

# Run the web service on container startup using Uvicorn.
# Render automatically sets the PORT environment variable.
CMD ["sh", "-c", "exec uvicorn backend.fastapi_integration.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
