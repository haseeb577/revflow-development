#!/bin/bash
# Automated .env backup script
# Runs daily via cron

ENV_FILE="/opt/shared-api-engine/.env"
BACKUP_DIR="/opt/shared-api-engine/env-backups"
PROTECTED_BACKUP="/opt/shared-api-engine/.env.protected"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Only backup if file exists and has content
if [ -f "$ENV_FILE" ] && [ -s "$ENV_FILE" ]; then
    # Remove immutable flag temporarily
    chattr -i "$ENV_FILE" 2>/dev/null || true
    
    # Create timestamped backup
    cp "$ENV_FILE" "$BACKUP_DIR/.env.backup.$TIMESTAMP"
    
    # Update protected backup
    cp "$ENV_FILE" "$PROTECTED_BACKUP"
    chmod 400 "$PROTECTED_BACKUP"
    
    # Keep only last 30 backups
    ls -t "$BACKUP_DIR"/.env.backup.* 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null || true
    
    # Restore immutable flag
    chattr +i "$ENV_FILE" 2>/dev/null || true
    
    logger "RevFlow: .env file backed up successfully"
else
    logger "RevFlow: .env file is empty or missing - attempting recovery"
    
    # Auto-recovery from protected backup
    if [ -f "$PROTECTED_BACKUP" ] && [ -s "$PROTECTED_BACKUP" ]; then
        cp "$PROTECTED_BACKUP" "$ENV_FILE"
        chmod 640 "$ENV_FILE"
        chattr +i "$ENV_FILE" 2>/dev/null || true
        logger "RevFlow: .env file auto-recovered from protected backup"
    fi
fi
