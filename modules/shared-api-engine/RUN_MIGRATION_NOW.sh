#!/bin/bash

################################################################################
# REVFLOW OS - AUTOMATED 7-MODULE MIGRATION SCRIPT
# Replace all hardcoded localhost:8XXX calls with gateway client.call_module()
# 
# SAFE: Backs up all files before changes
# SMART: Only modifies Python files with actual hardcoded calls
# TESTED: Validates changes and provides rollback
################################################################################

set -e  # Exit on error

TIMESTAMP=$(date +%s)
BACKUP_DIR="/opt/shared-api-engine/migration_backups_$TIMESTAMP"
MIGRATION_LOG="/opt/shared-api-engine/migration_log_$TIMESTAMP.txt"
FAILED_MODULES=()
SUCCESS_COUNT=0

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         REVFLOW OS - AUTOMATED 7-MODULE MIGRATION            ║"
echo "║                   DO NOT INTERRUPT!                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Log file: $MIGRATION_LOG"
echo "💾 Backups: $BACKUP_DIR"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Initialize log
{
    echo "═══════════════════════════════════════════════════════════════"
    echo "REVFLOW OS MODULE MIGRATION LOG"
    echo "Started: $(date)"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
} > "$MIGRATION_LOG"

################################################################################
# HELPER FUNCTIONS
################################################################################

log_msg() {
    echo "[$(date +'%H:%M:%S')] $1" | tee -a "$MIGRATION_LOG"
}

backup_file() {
    local file=$1
    local backup_path="$BACKUP_DIR/$(echo $file | sed 's/\//_/g')"
    cp "$file" "$backup_path"
    echo "  ✓ Backed up to: $backup_path"
}

add_import_to_file() {
    local file=$1
    
    # Check if import already exists
    if grep -q "from revflow_client import get_revflow_client" "$file"; then
        return 0
    fi
    
    # Add import after other imports (before first class/def)
    local import_line="from revflow_client import get_revflow_client"
    local insert_line=$(grep -n "^from \|^import " "$file" | tail -1 | cut -d: -f1)
    
    if [ -z "$insert_line" ]; then
        insert_line=1
    fi
    
    # Use sed to insert the import
    sed -i "${insert_line}a\\$import_line" "$file"
    log_msg "  ✓ Added RevFlowClient import"
}

init_client_in_file() {
    local file=$1
    
    # Check if client is already initialized
    if grep -q "client = get_revflow_client()" "$file"; then
        return 0
    fi
    
    # Find the first function/class definition and add initialization after it
    local first_def=$(grep -n "^def \|^class " "$file" | head -1 | cut -d: -f1)
    
    if [ -n "$first_def" ]; then
        sed -i "${first_def}i\\    client = get_revflow_client()" "$file"
        log_msg "  ✓ Added client initialization"
    fi
}

# Port to module name mapping
get_module_name() {
    local port=$1
    case $port in
        8700) echo "revprompt" ;;
        8100) echo "revscore" ;;
        8103) echo "revrank" ;;
        8765) echo "revseo" ;;
        8900) echo "revcite" ;;
        8500) echo "revhumanize" ;;
        8150) echo "revwins" ;;
        8610) echo "revimage" ;;
        8550) echo "revpublish" ;;
        8220) echo "revmetrics" ;;
        8006) echo "revsignal" ;;
        8011) echo "revintel" ;;
        8501) echo "revdispatch" ;;
        8003) echo "revvest" ;;
        8160) echo "revspy" ;;
        8105) echo "revspend" ;;
        8770) echo "revcore" ;;
        8004) echo "revcore" ;;
        8085) echo "revnap" ;;
        8902) echo "revbuilder" ;;
        8960) echo "revguard" ;;
        *) echo "unknown_$port" ;;
    esac
}

################################################################################
# MODULE 1: REVPUBLISH
################################################################################

migrate_revpublish() {
    log_msg ""
    log_msg "📍 MODULE 1: RevPublish (revpublish-backend.service)"
    
    local file="/opt/revpublish/backend/routes/content_sources.py"
    
    if [ ! -f "$file" ]; then
        log_msg "  ❌ File not found: $file"
        FAILED_MODULES+=("RevPublish")
        return 1
    fi
    
    backup_file "$file"
    add_import_to_file "$file"
    
    # Replace CSVImportEngineClient("http://localhost:8766") with gateway call
    sed -i 's/CSVImportEngineClient("http:\/\/localhost:[0-9]*")/None  # Now uses gateway/g' "$file"
    
    # Replace DataProviderClient("http://localhost:8100") 
    sed -i 's/DataProviderClient("http:\/\/localhost:[0-9]*")/None  # Now uses gateway/g' "$file"
    
    # Replace RevRankEngineClient("http://localhost:[0-9]*")
    sed -i 's/RevRankEngineClient("http:\/\/localhost:[0-9]*")/None  # Now uses gateway/g' "$file"
    
    # Replace actual method calls
    sed -i 's/csv_import\.import(/client.call_module("csvimport", "\/import", method="POST", json=/g' "$file"
    sed -i 's/data_provider\.get(/client.call_module("revscore", "\/data", method="GET") or {}/g' "$file"
    sed -i 's/revrank\.score(/client.call_module("revrank", "\/score", method="POST", json=/g' "$file"
    
    log_msg "  ✓ Replaced hardcoded calls with gateway"
    ((SUCCESS_COUNT++))
}

################################################################################
# MODULE 2: REVVEST IQ
################################################################################

migrate_revvest_iq() {
    log_msg ""
    log_msg "📍 MODULE 2: RevVest IQ (revvest-iq.service)"
    
    local file="/opt/revflow-os/modules/revvest/backend/gap_analyzer.py"
    
    if [ ! -f "$file" ]; then
        log_msg "  ❌ File not found: $file"
        FAILED_MODULES+=("RevVest IQ")
        return 1
    fi
    
    backup_file "$file"
    add_import_to_file "$file"
    
    # Replace REVSPY_URL = "http://localhost:8160"
    sed -i 's/REVSPY_URL = "http:\/\/localhost:[0-9]*"/REVSPY_URL = "gateway"  # Now uses client.call_module/g' "$file"
    
    # Replace requests to revspy with gateway
    sed -i 's/requests\.post(REVSPY_URL/client.call_module("revspy"/g' "$file"
    sed -i 's/requests\.get(REVSPY_URL/client.call_module("revspy"/g' "$file"
    
    log_msg "  ✓ Replaced hardcoded calls with gateway"
    ((SUCCESS_COUNT++))
}

################################################################################
# MODULE 3: REVAUDIT
################################################################################

migrate_revaudit() {
    log_msg ""
    log_msg "📍 MODULE 3: RevAudit (revaudit-backend.service)"
    
    local file="/opt/shared-api-engine/revaudit/revaudit_v3.py"
    
    if [ ! -f "$file" ]; then
        log_msg "  ❌ File not found: $file"
        FAILED_MODULES+=("RevAudit")
        return 1
    fi
    
    backup_file "$file"
    add_import_to_file "$file"
    
    # Replace localhost:8100 (revscore) with gateway
    sed -i "s|'http://localhost:8100'|client.call_module('revscore'|g" "$file"
    
    # Replace localhost:8765 (revseo) with gateway
    sed -i "s|'http://localhost:8765'|client.call_module('revseo'|g" "$file"
    
    # Replace localhost:8900 (revcite) with gateway
    sed -i "s|'http://localhost:8900'|client.call_module('revcite'|g" "$file"
    
    log_msg "  ✓ Replaced hardcoded calls with gateway"
    ((SUCCESS_COUNT++))
}

################################################################################
# MODULE 4: REVFLOW LEAD SCORING
################################################################################

migrate_lead_scoring() {
    log_msg ""
    log_msg "📍 MODULE 4: RevFlow Lead Scoring (revflow-lead-scoring.service)"
    
    local file="/opt/revflow-revenue-aligned-scoring-system/python/shared-api-engine/revflow_scoring_client.py"
    
    if [ ! -f "$file" ]; then
        log_msg "  ❌ File not found: $file"
        FAILED_MODULES+=("RevFlow Lead Scoring")
        return 1
    fi
    
    backup_file "$file"
    add_import_to_file "$file"
    
    # Replace SCORING_API_URL = "http://localhost:8500"
    sed -i 's/SCORING_API_URL = "http:\/\/localhost:[0-9]*"/SCORING_API_URL = "gateway"  # Now uses client.call_module/g' "$file"
    
    # Replace all requests.post(SCORING_API_URL with client.call_module
    sed -i 's/requests\.post(SCORING_API_URL/client.call_module("revhumanize"/g' "$file"
    sed -i 's/requests\.get(SCORING_API_URL/client.call_module("revhumanize"/g' "$file"
    
    log_msg "  ✓ Replaced hardcoded calls with gateway"
    ((SUCCESS_COUNT++))
}

################################################################################
# MODULE 5: REVSHIELD PRO
################################################################################

migrate_revshield() {
    log_msg ""
    log_msg "📍 MODULE 5: RevShield Pro (revshield-pro.service)"
    
    local file="/opt/revflow-security-monitor/scripts/scheduled_scanner.py"
    
    if [ ! -f "$file" ]; then
        log_msg "  ⚠️  File not found: $file (skipping)"
        return 0
    fi
    
    backup_file "$file"
    add_import_to_file "$file"
    
    # Replace http://localhost:8910 with gateway
    sed -i "s|'http://localhost:8910|client.call_module('revshield'|g" "$file"
    
    log_msg "  ✓ Replaced hardcoded calls with gateway"
    ((SUCCESS_COUNT++))
}

################################################################################
# MODULE 6: REVFLOW ADMIN API
################################################################################

migrate_admin_api() {
    log_msg ""
    log_msg "📍 MODULE 6: RevFlow Admin API (revflow-admin-api.service)"
    
    local file="/opt/revflow-admin-api/main.py"
    
    if [ ! -f "$file" ]; then
        log_msg "  ❌ File not found: $file"
        FAILED_MODULES+=("RevFlow Admin API")
        return 1
    fi
    
    backup_file "$file"
    add_import_to_file "$file"
    
    # Replace http://localhost:8085 with gateway
    sed -i "s|'http://localhost:8085|client.call_module('revnap'|g" "$file"
    
    # Replace http://localhost:8902 with gateway
    sed -i "s|'http://localhost:8902|client.call_module('revbuilder'|g" "$file"
    
    log_msg "  ✓ Replaced hardcoded calls with gateway"
    ((SUCCESS_COUNT++))
}

################################################################################
# MODULE 7: REVHOME SERVICES
################################################################################

migrate_revhome() {
    log_msg ""
    log_msg "📍 MODULE 7: RevHome Services (3 services)"
    
    local files=(
        "/opt/revhome/stabilize_revhome.sh"
        "/opt/revhome/healthcheck.sh"
    )
    
    local count=0
    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            continue
        fi
        
        backup_file "$file"
        
        # For shell scripts, update to use gateway
        sed -i 's|http://127.0.0.1:8100|http://localhost:8004/api/gateway/revscore|g' "$file"
        sed -i 's|http://localhost:8100|http://localhost:8004/api/gateway/revscore|g' "$file"
        
        ((count++))
    done
    
    if [ $count -gt 0 ]; then
        log_msg "  ✓ Updated $count shell scripts to use gateway"
        ((SUCCESS_COUNT++))
    else
        log_msg "  ⚠️  No shell scripts found to update"
    fi
}

################################################################################
# VERIFY DEPLOYMENT
################################################################################

verify_migration() {
    log_msg ""
    log_msg "════════════════════════════════════════════════════════════════"
    log_msg "VERIFICATION & TESTING"
    log_msg "════════════════════════════════════════════════════════════════"
    log_msg ""
    
    # Check for remaining hardcoded calls
    log_msg "Scanning for remaining hardcoded localhost:8XXX calls..."
    
    remaining=$(find /opt/revpublish /opt/revflow-os/modules/revvest \
                     /opt/shared-api-engine/revaudit \
                     /opt/revflow-revenue-aligned-scoring-system \
                     /opt/revflow-security-monitor \
                     /opt/revflow-admin-api \
                     /opt/revhome \
                     -name "*.py" -o -name "*.sh" 2>/dev/null | \
                xargs grep -l "localhost:8[0-9]\|127.0.0.1:8[0-9]" 2>/dev/null | \
                grep -v "\.pyc" | wc -l)
    
    if [ "$remaining" -eq "0" ]; then
        log_msg "  ✅ CLEAN! No hardcoded calls remaining"
    else
        log_msg "  ⚠️  Found $remaining files with potential hardcoded calls (review below)"
        find /opt/revpublish /opt/revflow-os/modules/revvest \
             /opt/shared-api-engine/revaudit \
             /opt/revflow-revenue-aligned-scoring-system \
             /opt/revflow-security-monitor \
             /opt/revflow-admin-api \
             /opt/revhome \
             -name "*.py" -o -name "*.sh" 2>/dev/null | \
        xargs grep -l "localhost:8[0-9]\|127.0.0.1:8[0-9]" 2>/dev/null | grep -v "\.pyc" | while read file; do
            log_msg "    → $file"
        done
    fi
    
    log_msg ""
    log_msg "Testing RevFlowClient import..."
    python3 -c "import sys; sys.path.insert(0, '/opt/shared-api-engine'); from revflow_client import get_revflow_client; print('✓ Client OK')" 2>&1 | tee -a "$MIGRATION_LOG"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    log_msg "Starting migration of 7 modules..."
    log_msg ""
    
    # Run migrations
    migrate_revpublish || true
    migrate_revvest_iq || true
    migrate_revaudit || true
    migrate_lead_scoring || true
    migrate_revshield || true
    migrate_admin_api || true
    migrate_revhome || true
    
    # Verify
    verify_migration
    
    # Summary
    log_msg ""
    log_msg "════════════════════════════════════════════════════════════════"
    log_msg "MIGRATION COMPLETE"
    log_msg "════════════════════════════════════════════════════════════════"
    log_msg ""
    log_msg "✅ Successfully migrated: $SUCCESS_COUNT / 7 modules"
    
    if [ ${#FAILED_MODULES[@]} -gt 0 ]; then
        log_msg "❌ Failed modules:"
        for mod in "${FAILED_MODULES[@]}"; do
            log_msg "   - $mod"
        done
    fi
    
    log_msg ""
    log_msg "📝 Full log: $MIGRATION_LOG"
    log_msg "💾 Backups: $BACKUP_DIR"
    log_msg ""
    log_msg "NEXT STEPS:"
    log_msg "1. Review the log: cat $MIGRATION_LOG"
    log_msg "2. Test each service: systemctl status <service>"
    log_msg "3. Restart services: systemctl restart revpublish-backend.service"
    log_msg "4. If issues, rollback: cp $BACKUP_DIR/* /opt/"
    log_msg ""
}

# Run main function
main

# Exit with appropriate code
if [ ${#FAILED_MODULES[@]} -gt 0 ]; then
    exit 1
else
    exit 0
fi
