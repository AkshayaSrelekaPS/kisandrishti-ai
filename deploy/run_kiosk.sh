#!/bin/bash
# ==============================================================================
# KisanDrishti AI: Raspberry Pi 5 Kiosk Launcher (HTTP :8000 or HTTPS :8443)
# Use HTTP on localhost (Chromium kiosk on Pi display).
# Use `--https` when accessing live microphone Voice Q&A from another device over LAN.
# ==============================================================================
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4

if [ "$1" = "--https" ]; then
    CERT="deploy/certs/cert.pem"
    KEY="deploy/certs/key.pem"
    if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
        mkdir -p deploy/certs
        openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
            -keyout "$KEY" -out "$CERT" -subj "/CN=kisandrishti.local"
    fi
    echo "Starting KisanDrishti AI (HTTPS) on https://0.0.0.0:8443"
    exec python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8443 \
        --ssl-keyfile "$KEY" --ssl-certfile "$CERT"
else
    echo "Starting KisanDrishti AI (HTTP) on http://0.0.0.0:8000"
    exec python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8000
fi
