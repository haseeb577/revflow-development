#!/bin/bash
# Emergency .env recovery script

ENV_FILE="/opt/shared-api-engine/.env"
PROTECTED_BACKUP="/opt/shared-api-engine/.env.protected"
BACKUP_DIR="/opt/shared-api-engine/env-backups"

echo "=========================================="
echo "🚨 .ENV FILE RECOVERY"
echo "=========================================="
echo ""

# Remove immutable flag
chattr -i "$ENV_FILE" 2>/dev/null || true

# Check if protected backup exists
if [ -f "$PROTECTED_BACKUP" ] && [ -s "$PROTECTED_BACKUP" ]; then
    echo "Recovering from protected backup..."
    cp "$PROTECTED_BACKUP" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    chattr +i "$ENV_FILE"
    echo "✅ Recovered from protected backup"
    exit 0
fi

# Check for timestamped backups
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/.env.backup.* 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
    echo "Recovering from latest backup: $(basename $LATEST_BACKUP)"
    cp "$LATEST_BACKUP" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    chattr +i "$ENV_FILE"
    echo "✅ Recovered from timestamped backup"
    exit 0
fi

echo "❌ No valid backups found!"
echo "You need to manually restore the .env file"
exit 1
