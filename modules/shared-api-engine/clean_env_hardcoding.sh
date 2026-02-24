#!/bin/bash

###############################################################################
# Clean .env File - Remove All Hardcoded Module Endpoints
# 
# This removes the 18 hardcoded module port mappings from .env
# Keeps ONLY the gateway endpoint (which is dynamic via PostgreSQL)
# 
# NO HARDCODING - All module discovery happens in PostgreSQL
###############################################################################

set -e

ENV_FILE="/opt/shared-api-engine/.env"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            Cleaning .env - Removing Hardcoded Ports            ║"
echo "║        All module discovery will use PostgreSQL registry       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Backup current .env
echo "📋 Backing up current .env..."
cp "$ENV_FILE" "${ENV_FILE}.backup.before-hardcoding-removal.$(date +%s)"
echo "✓ Backup created"
echo ""

# Remove ALL hardcoded module endpoints
echo "🔨 Removing hardcoded endpoints..."

# Create a clean .env with only non-module-endpoint configs
grep -v "^REV.*_API=" "$ENV_FILE" | \
grep -v "^REVFLOW_REQUEST_TIMEOUT=" > "${ENV_FILE}.temp"

# Move cleaned version
mv "${ENV_FILE}.temp" "$ENV_FILE"

echo "✓ Removed all hardcoded REV*_API endpoints"
echo "✓ Removed REVFLOW_REQUEST_TIMEOUT"
echo ""

# Add back ONLY the gateway config
echo "🔧 Adding gateway configuration..."
cat >> "$ENV_FILE" << 'EOF'

# ============================================
# REVCORE GATEWAY - Single Source of Truth
# ============================================
# Gateway loads module endpoints from PostgreSQL at startup
# NO HARDCODING - All ports defined in revflow_service_registry table
REVCORE_GATEWAY=http://localhost:8004/api/gateway
USE_REVCORE_GATEWAY=true

# Request timeout (used by client)
REVFLOW_REQUEST_TIMEOUT=30
EOF

echo "✓ Added gateway configuration"
echo ""

# Verify
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                       VERIFICATION                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "Checking for removed endpoints:"
if grep -q "^REV.*_API=" "$ENV_FILE"; then
    echo "❌ ERROR: Found hardcoded endpoints - cleanup failed"
    exit 1
else
    echo "✓ All hardcoded endpoints removed"
fi

echo ""
echo "Checking for gateway config:"
if grep -q "REVCORE_GATEWAY" "$ENV_FILE"; then
    echo "✓ Gateway endpoint present"
else
    echo "❌ ERROR: Gateway endpoint missing"
    exit 1
fi

echo ""
echo "Current config (last 10 lines):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -10 "$ENV_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "✅ SUCCESS!"
echo ""
echo "Changes made:"
echo "  ✓ Removed 18 hardcoded module endpoints"
echo "  ✓ Removed REVFLOW_REQUEST_TIMEOUT"
echo "  ✓ Kept gateway configuration"
echo ""
echo "Benefits:"
echo "  • NO HARDCODING - Follows canonical rules"
echo "  • Single source of truth: PostgreSQL revflow_service_registry"
echo "  • Add/remove modules without touching .env"
echo "  • Gateway auto-discovers ports at startup"
echo "  • Scales to any number of modules"
echo ""
echo "Gateway will query PostgreSQL table:"
echo "  SELECT module_name, port FROM revflow_service_registry"
echo "  WHERE status = 'deployed'"
echo ""

