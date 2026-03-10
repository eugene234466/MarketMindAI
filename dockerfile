FROM python:3.12-slim

WORKDIR /app

# Install only necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app/database /app/reports

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Optimized Gunicorn settings
CMD gunicorn \
    --timeout 120 \
    --workers 1 \
    --worker-class sync \
    --max-requests 10 \
    --max-requests-jitter 5 \
    --memory 256 \
    "main:create_app()" \
    --bind 0.0.0.0:$PORT
