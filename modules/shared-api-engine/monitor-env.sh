#!/bin/bash
# Monitor .env file integrity
# Runs every hour via cron

ENV_FILE="/opt/shared-api-engine/.env"
PROTECTED_BACKUP="/opt/shared-api-engine/.env.protected"

# Check if file exists
if [ ! -f "$ENV_FILE" ]; then
    logger "RevFlow ALERT: .env file is MISSING! Attempting recovery..."
    /opt/shared-api-engine/recover-env.sh
    exit 1
fi

# Check if file is empty
if [ ! -s "$ENV_FILE" ]; then
    logger "RevFlow ALERT: .env file is EMPTY! Attempting recovery..."
    /opt/shared-api-engine/recover-env.sh
    exit 1
fi

# Check if POSTGRES_PASSWORD exists
if ! grep -q "POSTGRES_PASSWORD" "$ENV_FILE"; then
    logger "RevFlow ALERT: .env file is CORRUPTED (no POSTGRES_PASSWORD)! Attempting recovery..."
    /opt/shared-api-engine/recover-env.sh
    exit 1
fi

# Check immutable flag
if ! lsattr "$ENV_FILE" 2>/dev/null | grep -q "i"; then
    logger "RevFlow WARNING: .env file is not immutable! Restoring protection..."
    chattr +i "$ENV_FILE" 2>/dev/null || true
fi
