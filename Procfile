web: gunicorn main:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120 --worker-class sync --max-requests 500 --max-requests-jitter 50 --preload
