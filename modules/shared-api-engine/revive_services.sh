#!/bin/bash
set -e

echo "🔍 Discovering and Starting RevFlow Services"
echo "=============================================="

# 1. Check Citation Services
if [ -d "/opt/revcite" ]; then
    echo "✅ Found RevCite at /opt/revcite"
    
    # Check if systemd service exists
    if [ -f "/etc/systemd/system/citation-builder-api.service" ]; then
        echo "   Starting citation-builder-api..."
        systemctl start citation-builder-api 2>/dev/null || echo "   ⚠️ Failed to start"
        systemctl status citation-builder-api --no-pager | head -5
    fi
    
    if [ -f "/etc/systemd/system/citation-monitor-api.service" ]; then
        echo "   Starting citation-monitor-api..."
        systemctl start citation-monitor-api 2>/dev/null || echo "   ⚠️ Failed to start"
        systemctl status citation-monitor-api --no-pager | head -5
    fi
fi

# 2. Check Scoring Service
if [ -f "/opt/revflow-revenue-aligned-scoring-system/python/revflow_scoring_engine.py" ]; then
    echo "✅ Found Scoring Engine"
    echo "   Need to create service for this..."
fi

# 3. Check Citations Service
if [ -d "/opt/revflow-citations" ]; then
    echo "✅ Found Citations at /opt/revflow-citations"
    ls -la /opt/revflow-citations/
fi

echo ""
echo "🔍 Checking what's actually running now:"
netstat -tulpn | grep -E "8005|8007|8600"

