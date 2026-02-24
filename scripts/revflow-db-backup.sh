#!/bin/bash
# RevFlow OS - Daily Database Backup
# Runs via cron to backup PostgreSQL database

BACKUP_DIR="/opt/revflow-os/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/revflow_backup_${DATE}.sql"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Perform backup
docker exec revflow-postgres-docker pg_dump -U revflow -d revflow > "$BACKUP_FILE" 2>/dev/null

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    gzip "$BACKUP_FILE"
    echo "[$(date)] Backup successful: ${BACKUP_FILE}.gz"
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "revflow_backup_*.sql.gz" -mtime +7 -delete
else
    echo "[$(date)] Backup FAILED"
    rm -f "$BACKUP_FILE"
    exit 1
fi
