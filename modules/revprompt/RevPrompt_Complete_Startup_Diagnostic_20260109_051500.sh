#!/bin/bash
# RevPrompt_Complete_Startup_Diagnostic_20260109_051500.sh
# Comprehensive diagnostic and startup for RevPrompt Unified

set -e

echo "=========================================="
echo "🔍 REVPROMPT STARTUP DIAGNOSTIC"
echo "=========================================="
echo ""

cd /opt/revprompt-unified

# Step 1: Find what's using port 8700
echo "1️⃣ Checking port 8700..."
PORT_USER=$(lsof -ti:8700 2>/dev/null || echo "")
if [ -n "$PORT_USER" ]; then
    echo "   ⚠️  Port 8700 is in use by PID: $PORT_USER"
    ps -p $PORT_USER -o pid,cmd,start || true
    echo "   Killing process..."
    kill -9 $PORT_USER 2>/dev/null || true
    sleep 2
    echo "   ✅ Port cleared"
else
    echo "   ✅ Port 8700 is free"
fi
echo ""

# Step 2: Kill any zombie RevPrompt processes
echo "2️⃣ Cleaning up zombie processes..."
pkill -9 -f "python.*run-api.py" 2>/dev/null || true
sleep 1
echo "   ✅ Cleanup complete"
echo ""

# Step 3: Create necessary directories
echo "3️⃣ Creating directories..."
mkdir -p logs ui/templates ui/static database core content/page_templates content/field_prompts validation generation portfolio
echo "   ✅ Directories ready"
echo ""

# Step 4: Start service
echo "4️⃣ Starting RevPrompt service..."
python3 -u run-api.py > logs/revprompt.log 2>&1 &
PID=$!
echo $PID > revprompt.pid
echo "   Started with PID: $PID"
echo ""

# Step 5: Wait and verify
echo "5️⃣ Waiting for service to initialize..."
sleep 5

if ! ps -p $PID > /dev/null 2>&1; then
    echo "   ❌ Service died immediately"
    echo ""
    echo "Last 30 lines of log:"
    tail -30 logs/revprompt.log
    exit 1
fi

echo "   ✅ Process is alive"
echo ""

# Step 6: Health check
echo "6️⃣ Testing health endpoint..."
for i in {1..10}; do
    HEALTH=$(curl -s -m 2 http://localhost:8700/api/health 2>/dev/null || echo "")
    if [ -n "$HEALTH" ]; then
        echo "   ✅ Health check PASSED"
        echo ""
        echo "$HEALTH" | python3 -m json.tool
        echo ""
        echo "=========================================="
        echo "✅ REVPROMPT IS OPERATIONAL"
        echo "=========================================="
        echo ""
        echo "PID: $PID"
        echo "Port: 8700"
        echo "URL: http://217.15.168.106:8700"
        echo "Logs: tail -f /opt/revprompt-unified/logs/revprompt.log"
        echo ""
        echo "Stop: kill $PID"
        exit 0
    fi
    echo "   Attempt $i/10 failed, retrying..."
    sleep 1
done

echo "   ❌ Health check failed after 10 attempts"
echo ""
echo "Process status:"
ps -p $PID -o pid,stat,cmd || echo "Process not found"
echo ""
echo "Last 20 lines of log:"
tail -20 logs/revprompt.log
exit 1
