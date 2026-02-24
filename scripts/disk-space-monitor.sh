#!/bin/bash
# Disk Space Monitor - Alerts and auto-cleanup at 80%

THRESHOLD=80
CRITICAL=90
LOG_FILE="/var/log/revflow/disk-monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_usage() {
    df / | tail -1 | awk '{print $5}' | tr -d '%'
}

cleanup() {
    log "Running cleanup..."
    
    # Clean pip cache
    rm -rf /root/.cache/pip/* 2>/dev/null
    rm -rf /home/*/.cache/pip/* 2>/dev/null
    
    # Clean old journals (keep 3 days)
    journalctl --vacuum-time=3d 2>/dev/null
    
    # Clean apt cache
    apt-get clean 2>/dev/null
    
    # Remove old backups (older than 14 days)
    find /opt/backups -type d -mtime +14 -exec rm -rf {} + 2>/dev/null
    
    # Clean tmp files older than 7 days
    find /tmp -type f -mtime +7 -delete 2>/dev/null
    
    log "Cleanup complete. New usage: $(get_usage)%"
}

usage=$(get_usage)
log "Disk usage: ${usage}%"

if [ "$usage" -ge "$CRITICAL" ]; then
    log "CRITICAL: Disk at ${usage}% - Running emergency cleanup"
    cleanup
elif [ "$usage" -ge "$THRESHOLD" ]; then
    log "WARNING: Disk at ${usage}% - Running cleanup"
    cleanup
fi
