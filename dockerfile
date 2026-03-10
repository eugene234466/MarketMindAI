FROM python:3.12-slim

WORKDIR /app

# Create directories for persistent storage
RUN mkdir -p /app/database /app/reports

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure proper permissions
RUN chmod -R 755 /app/database /app/reports

# Replace the CMD line with:
CMD gunicorn --timeout 200 --workers 2 "main:create_app()" --bind 0.0.0.0:$PORT


