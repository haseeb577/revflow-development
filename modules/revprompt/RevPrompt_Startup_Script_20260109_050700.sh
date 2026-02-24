#!/bin/bash
# RevPrompt_Startup_Script_20260109_050700.sh
# Simple, reliable startup script for RevPrompt Unified

cd /opt/revprompt-unified

# Create necessary directories
mkdir -p logs ui/templates ui/static database

# Kill any existing processes
pkill -9 -f "python3 run-api.py" 2>/dev/null
sleep 2

# Start service
echo "Starting RevPrompt on port 8700..."
python3 -u run-api.py > logs/revprompt.log 2>&1 &
PID=$!

# Save PID
echo $PID > revprompt.pid
echo "Started with PID: $PID"

# Wait and verify
sleep 3

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Service is running"
    echo "   PID: $PID"
    echo "   Port: 8700"
    echo "   Logs: /opt/revprompt-unified/logs/revprompt.log"
    echo ""
    echo "Test with: curl http://localhost:8700/api/health"
else
    echo "❌ Service failed to start"
    echo "Check logs: tail -50 /opt/revprompt-unified/logs/revprompt.log"
    exit 1
fi
