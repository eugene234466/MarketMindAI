FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create directories for persistent storage
RUN mkdir -p /app/database /app/reports

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure proper permissions
RUN chmod -R 755 /app/database /app/reports

# Optimized for long-running AI analysis (10 minute timeout)
# - timeout 600 = 10 minutes (600 seconds)
# - workers 1 = single worker to reduce memory pressure
# - max-requests limited to prevent memory leaks
# - preload = load app before forking workers
CMD gunicorn \
    --timeout 600 \
    --workers 1 \
    --worker-class sync \
    --max-requests 10 \
    --max-requests-jitter 5 \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    "main:create_app()" \
    --bind 0.0.0.0:$PORT
