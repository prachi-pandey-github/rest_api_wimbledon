#!/bin/bash
# Render startup script

echo "Starting Wimbledon API on Render..."
echo "Environment: $FLASK_ENV"
echo "Port: $PORT"

# Start the application with gunicorn
exec gunicorn --bind 0.0.0.0:$PORT \
              --workers 4 \
              --worker-class sync \
              --timeout 120 \
              --keep-alive 2 \
              --max-requests 1000 \
              --max-requests-jitter 100 \
              --access-logfile - \
              --error-logfile - \
              --log-level info \
              main:app
