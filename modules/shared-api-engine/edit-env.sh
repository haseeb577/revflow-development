#!/bin/bash
# Safe .env editing script

ENV_FILE="/opt/shared-api-engine/.env"
TEMP_FILE="/tmp/.env.editing.$$"

echo "=========================================="
echo "📝 SAFE .ENV EDITOR"
echo "=========================================="
echo ""

# Remove immutable flag
chattr -i "$ENV_FILE" 2>/dev/null || true

# Create backup
cp "$ENV_FILE" "$ENV_FILE.before-edit.$(date +%Y%m%d_%H%M%S)"

# Copy to temp file
cp "$ENV_FILE" "$TEMP_FILE"

# Open in editor
${EDITOR:-nano} "$TEMP_FILE"

# Validate file
echo ""
echo "Validating changes..."

if [ ! -s "$TEMP_FILE" ]; then
    echo "❌ File is empty! Aborting."
    rm "$TEMP_FILE"
    chattr +i "$ENV_FILE" 2>/dev/null || true
    exit 1
fi

if ! grep -q "POSTGRES_PASSWORD" "$TEMP_FILE"; then
    echo "❌ POSTGRES_PASSWORD is missing! Aborting."
    rm "$TEMP_FILE"
    chattr +i "$ENV_FILE" 2>/dev/null || true
    exit 1
fi

# Apply changes
cp "$TEMP_FILE" "$ENV_FILE"
rm "$TEMP_FILE"
chmod 640 "$ENV_FILE"

# Restore immutable flag
chattr +i "$ENV_FILE" 2>/dev/null || true

# Backup
/opt/shared-api-engine/backup-env.sh

echo "✅ Changes saved and protected"
