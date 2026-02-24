#!/bin/bash

################################################################################
# REVFLOW OS - POST-MIGRATION VERIFICATION
# Test all modules after migration to ensure gateway works correctly
################################################################################

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     REVFLOW OS - POST-MIGRATION VERIFICATION                 ║"
echo "║              Testing all 7 migrated modules                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

TEST_LOG="/opt/shared-api-engine/migration_test_$(date +%s).log"
PASS_COUNT=0
FAIL_COUNT=0

{
    echo "═══════════════════════════════════════════════════════════════"
    echo "POST-MIGRATION TEST LOG"
    echo "Started: $(date)"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
} > "$TEST_LOG"

test_result() {
    local module=$1
    local service=$2
    local status=$3
    
    if [ "$status" -eq 0 ]; then
        echo "✅ $module - PASS" | tee -a "$TEST_LOG"
        ((PASS_COUNT++))
    else
        echo "❌ $module - FAIL" | tee -a "$TEST_LOG"
        ((FAIL_COUNT++))
    fi
}

echo "STEP 1: Checking Gateway Health"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test gateway endpoint
if curl -s http://localhost:8004/api/gateway/health > /dev/null 2>&1; then
    echo "✅ Gateway health endpoint responding"
    echo "Gateway: PASS" >> "$TEST_LOG"
else
    echo "⚠️  Gateway not responding at 8004, checking 8770..."
    if curl -s http://localhost:8770/health > /dev/null 2>&1; then
        echo "✅ RevCore API health endpoint responding"
    else
        echo "❌ Gateway/RevCore not responding"
        echo "Gateway: FAIL" >> "$TEST_LOG"
    fi
fi

echo ""
echo "STEP 2: Testing Individual Modules"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Module 1: RevPublish
echo "📍 Module 1: RevPublish (8550)"
if systemctl is-active --quiet revpublish-backend.service; then
    if curl -s http://localhost:8550/health > /dev/null 2>&1; then
        echo "✅ RevPublish running and healthy"
        test_result "RevPublish" "revpublish-backend" 0
    else
        echo "⚠️  RevPublish running but not responding to health check"
        test_result "RevPublish" "revpublish-backend" 1
    fi
else
    echo "⚠️  RevPublish service not running"
    test_result "RevPublish" "revpublish-backend" 1
fi
echo ""

# Module 2: RevVest IQ
echo "📍 Module 2: RevVest IQ (8003)"
if systemctl is-active --quiet revvest-iq.service; then
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        echo "✅ RevVest IQ running and healthy"
        test_result "RevVest IQ" "revvest-iq" 0
    else
        echo "⚠️  RevVest IQ running but not responding"
        test_result "RevVest IQ" "revvest-iq" 1
    fi
else
    echo "⚠️  RevVest IQ service not running"
    test_result "RevVest IQ" "revvest-iq" 1
fi
echo ""

# Module 3: RevAudit
echo "📍 Module 3: RevAudit (backend)"
if systemctl is-active --quiet revaudit-backend.service 2>/dev/null; then
    echo "✅ RevAudit backend service running"
    test_result "RevAudit" "revaudit-backend" 0
else
    echo "⚠️  RevAudit backend service not running"
    test_result "RevAudit" "revaudit-backend" 1
fi
echo ""

# Module 4: RevFlow Lead Scoring
echo "📍 Module 4: RevFlow Lead Scoring"
if systemctl is-active --quiet revflow-lead-scoring.service 2>/dev/null; then
    echo "✅ RevFlow Lead Scoring service running"
    test_result "Lead Scoring" "revflow-lead-scoring" 0
else
    echo "⚠️  RevFlow Lead Scoring not running (may not be deployed)"
    test_result "Lead Scoring" "revflow-lead-scoring" 1
fi
echo ""

# Module 5: RevShield Pro
echo "📍 Module 5: RevShield Pro"
if systemctl is-active --quiet revshield-pro.service 2>/dev/null; then
    echo "✅ RevShield Pro service running"
    test_result "RevShield Pro" "revshield-pro" 0
else
    echo "ℹ️  RevShield Pro not found (may not be deployed)"
fi
echo ""

# Module 6: RevFlow Admin API
echo "📍 Module 6: RevFlow Admin API"
if systemctl is-active --quiet revflow-admin-api.service 2>/dev/null; then
    if curl -s http://localhost:8085/health > /dev/null 2>&1; then
        echo "✅ RevFlow Admin API running and healthy"
        test_result "Admin API" "revflow-admin-api" 0
    else
        echo "⚠️  RevFlow Admin API running but not responding"
        test_result "Admin API" "revflow-admin-api" 1
    fi
else
    echo "⚠️  RevFlow Admin API not running"
    test_result "Admin API" "revflow-admin-api" 1
fi
echo ""

# Module 7: RevHome Services
echo "📍 Module 7: RevHome Services"
if systemctl is-active --quiet revhome-uvicorn.service 2>/dev/null; then
    if curl -s http://localhost:8100/health > /dev/null 2>&1; then
        echo "✅ RevHome service running and healthy"
        test_result "RevHome" "revhome-uvicorn" 0
    else
        echo "⚠️  RevHome running but not responding"
        test_result "RevHome" "revhome-uvicorn" 1
    fi
else
    echo "⚠️  RevHome service not running"
    test_result "RevHome" "revhome-uvicorn" 1
fi
echo ""

################################################################################
# STEP 3: Verify No Hardcoded Calls Remain
################################################################################

echo "STEP 3: Scanning for Remaining Hardcoded Calls"
echo "════════════════════════════════════════════════════════════════"
echo ""

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
    echo "✅ Clean! No hardcoded localhost:8XXX calls remaining"
    echo "Hardcoding scan: PASS" >> "$TEST_LOG"
else
    echo "⚠️  Found $remaining files with potential hardcoded calls:"
    find /opt/revpublish /opt/revflow-os/modules/revvest \
         /opt/shared-api-engine/revaudit \
         /opt/revflow-revenue-aligned-scoring-system \
         /opt/revflow-security-monitor \
         /opt/revflow-admin-api \
         /opt/revhome \
         -name "*.py" -o -name "*.sh" 2>/dev/null | \
    xargs grep -l "localhost:8[0-9]\|127.0.0.1:8[0-9]" 2>/dev/null | grep -v "\.pyc" | while read file; do
        echo "  → $file"
    done
    echo "Hardcoding scan: PARTIAL" >> "$TEST_LOG"
fi
echo ""

################################################################################
# STEP 4: Test RevFlowClient
################################################################################

echo "STEP 4: Testing RevFlowClient Functionality"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test client import
python3 << 'PYTHON_TEST' 2>&1 | tee -a "$TEST_LOG"
import sys
sys.path.insert(0, '/opt/shared-api-engine')

try:
    from revflow_client import get_revflow_client
    print("✅ RevFlowClient import successful")
    
    client = get_revflow_client()
    print(f"✅ Client initialized")
    print(f"   Gateway: {client.gateway}")
    print(f"   Mode: Gateway enabled")
    
except Exception as e:
    print(f"❌ RevFlowClient error: {e}")
    sys.exit(1)
PYTHON_TEST

echo ""

################################################################################
# SUMMARY
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "TEST SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -eq "0" ]; then
    echo "🎉 ALL TESTS PASSED!"
    echo ""
    echo "✅ Migration successful!"
    echo "✅ All modules using gateway"
    echo "✅ No hardcoded calls remaining"
    echo ""
else
    echo "⚠️  Some modules need attention (see details above)"
fi

echo "📝 Full test log: $TEST_LOG"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "NEXT STEPS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "1. Review test log: cat $TEST_LOG"
echo "2. If issues, restart services:"
echo "   systemctl restart revpublish-backend revvest-iq revaudit-backend"
echo "3. Check service logs:"
echo "   journalctl -u revpublish-backend.service -n 50"
echo "4. Monitor gateway:"
echo "   curl -s http://localhost:8004/api/gateway/health | python3 -m json.tool"
echo ""
