#!/bin/bash
echo "🔍 Service Discovery & Registration"
echo "===================================="

# Check citation-builder port
if systemctl is-active citation-builder-api > /dev/null; then
    PORT=$(grep -oP 'port[= ]\K\d+' /etc/systemd/system/citation-builder-api.service | head -1)
    echo "✅ Citation Builder running on port: $PORT"
fi

# Check citation-monitor port  
if systemctl is-active citation-monitor-api > /dev/null; then
    PORT=$(grep -oP 'port[= ]\K\d+' /etc/systemd/system/citation-monitor-api.service | head -1)
    echo "✅ Citation Monitor running on port: $PORT"
fi

# Show all active Python services with ports
echo -e "\n📊 All Active Python Services:"
ps aux | grep python | grep -E "port|uvicorn" | grep -v grep | while read line; do
    echo "  $line"
done

echo -e "\n🔌 All Listening Ports in 8000-9000 range:"
netstat -tulpn | grep -E "80[0-9]{2}|90[0-9]{2}" | grep LISTEN

