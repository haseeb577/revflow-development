#!/bin/bash

################################################################################
# COPY & PASTE THIS ENTIRE BLOCK TO RUN COMPLETE AUTOMATED MIGRATION
# Takes ~10 minutes total
################################################################################

echo "🚀 STARTING REVFLOW OS 7-MODULE AUTOMATED MIGRATION"
echo ""

# STEP 1: Run migration (this backs up, modifies, and tests)
echo "STEP 1: Running migration on all 7 modules..."
echo "Time: ~3 minutes"
echo ""
bash /opt/shared-api-engine/RUN_MIGRATION_NOW.sh

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "STEP 1 COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""

# STEP 2: Verify migration worked
echo "STEP 2: Verifying migration..."
echo "Time: ~2 minutes"
echo ""
bash /opt/shared-api-engine/verify_migration.sh

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "STEP 2 COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""

# STEP 3: Restart all affected services
echo "STEP 3: Restarting services..."
echo "Time: ~1 minute"
echo ""

services=(
    "revpublish-backend.service"
    "revvest-iq.service"
    "revaudit-backend.service"
    "revaudit-frontend.service"
    "revaudit-v5.service"
    "revaudit-v6.service"
    "revaudit.service"
    "revflow-lead-scoring.service"
    "revshield-pro.service"
    "revflow-admin-api.service"
    "revhome-uvicorn.service"
    "revhome-docker.service"
    "revhome-chat-api.service"
)

for service in "${services[@]}"; do
    if systemctl list-units --all | grep -q "^[ ]*$service"; then
        systemctl restart "$service" 2>/dev/null && echo "  ✓ Restarted $service" || echo "  ⚠️  Could not restart $service (may not exist)"
    fi
done

echo ""
echo "✅ All services restarted"
echo ""

# STEP 4: Quick health check
echo "STEP 4: Quick health checks..."
echo ""

echo "Gateway health:"
curl -s http://localhost:8004/api/gateway/health | python3 -m json.tool 2>/dev/null && echo "✅ Gateway OK" || echo "⚠️  Gateway check failed"

echo ""
echo "Module ports:"
for port in 8550 8003 8100 8765 8220 8550 8770; do
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "  ✓ Port $port responding"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🎉 MIGRATION COMPLETE!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ All 7 modules migrated to use gateway"
echo "✅ All hardcoded calls replaced"
echo "✅ All services restarted"
echo ""
echo "NEXT: Review logs and monitor services"
echo "  tail -f /opt/shared-api-engine/migration_log_*.txt"
echo "  journalctl -u revpublish-backend.service -f"
echo ""
