#!/bin/bash
set -e

# Generate JWT keys if they don't exist
if [ ! -f /app/secrets/private.pem ] || [ ! -f /app/secrets/public.pem ]; then
    echo "Generating JWT RSA key pair..."
    mkdir -p /app/secrets
    openssl genrsa -out /app/secrets/private.pem 2048
    openssl rsa -in /app/secrets/private.pem -pubout -out /app/secrets/public.pem
    echo "JWT keys generated."
fi

# Run database setup script
python /app/setup_db.py

# Start server — use $PORT (Render sets this) or default to 8000
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
