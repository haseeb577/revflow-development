#!/bin/bash

################################################################################
# REVFLOW OS - ROLLBACK SCRIPT
# Restore modules to pre-migration state from backups
################################################################################

if [ -z "$1" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║             REVFLOW OS - MIGRATION ROLLBACK                  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Usage: bash rollback_migration.sh <backup_timestamp>"
    echo ""
    echo "Available backups:"
    ls -dt /opt/shared-api-engine/migration_backups_* 2>/dev/null | head -5 | while read dir; do
        echo "  • $dir"
    done
    echo ""
    echo "Example: bash rollback_migration.sh 1738001234"
    exit 1
fi

TIMESTAMP=$1
BACKUP_DIR="/opt/shared-api-engine/migration_backups_$TIMESTAMP"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "⚠️  ROLLING BACK TO TIMESTAMP: $TIMESTAMP"
echo ""
echo "This will restore:"
echo "  • RevPublish"
echo "  • RevVest IQ"
echo "  • RevAudit"
echo "  • RevFlow Lead Scoring"
echo "  • RevShield Pro"
echo "  • RevFlow Admin API"
echo "  • RevHome Services"
echo ""
read -p "Continue? (yes/no) " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Restore files from backup
echo "Restoring files..."
for backup_file in "$BACKUP_DIR"/*; do
    if [ -f "$backup_file" ]; then
        # Convert backup filename back to original path
        original_path=$(echo $(basename "$backup_file") | sed 's/_/\//g')
        
        # Handle special case for nested paths
        if [[ "$backup_file" == *"_opt_revpublish_"* ]]; then
            cp "$backup_file" "/opt/revpublish/backend/routes/content_sources.py"
            echo "  ✓ Restored /opt/revpublish/backend/routes/content_sources.py"
        elif [[ "$backup_file" == *"_opt_revflow-os_"* ]]; then
            cp "$backup_file" "/opt/revflow-os/modules/revvest/backend/gap_analyzer.py"
            echo "  ✓ Restored /opt/revflow-os/modules/revvest/backend/gap_analyzer.py"
        elif [[ "$backup_file" == *"_opt_shared-api-engine_revaudit_"* ]]; then
            cp "$backup_file" "/opt/shared-api-engine/revaudit/revaudit_v3.py"
            echo "  ✓ Restored /opt/shared-api-engine/revaudit/revaudit_v3.py"
        elif [[ "$backup_file" == *"_opt_revflow-revenue-aligned-scoring-system_"* ]]; then
            cp "$backup_file" "/opt/revflow-revenue-aligned-scoring-system/python/shared-api-engine/revflow_scoring_client.py"
            echo "  ✓ Restored revflow_scoring_client.py"
        elif [[ "$backup_file" == *"_opt_revflow-security-monitor_"* ]]; then
            cp "$backup_file" "/opt/revflow-security-monitor/scripts/scheduled_scanner.py"
            echo "  ✓ Restored scheduled_scanner.py"
        elif [[ "$backup_file" == *"_opt_revflow-admin-api_"* ]]; then
            cp "$backup_file" "/opt/revflow-admin-api/main.py"
            echo "  ✓ Restored /opt/revflow-admin-api/main.py"
        elif [[ "$backup_file" == *"_opt_revhome_"* ]]; then
            cp "$backup_file" "/opt/revhome/$(basename $backup_file | sed 's/_.*_//')"
            echo "  ✓ Restored /opt/revhome/$(basename $backup_file)"
        fi
    fi
done

echo ""
echo "✅ Rollback complete!"
echo ""
echo "Next steps:"
echo "1. Verify restored files are correct"
echo "2. Restart services: systemctl restart revpublish-backend.service revvest-iq.service etc."
echo "3. Check service health: systemctl status <service>"
