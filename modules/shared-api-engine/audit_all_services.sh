#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          REVFLOW SERVICE COMPREHENSIVE AUDIT                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 1. Check RevCore Database Registry
echo "📋 STEP 1: Services Registered in RevCore Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d revcore -t -c "
SELECT 
    RPAD(service_id, 25) || ' | ' || 
    RPAD(name, 30) || ' | ' || 
    LPAD(port::text, 5) || ' | ' || 
    RPAD(status, 8)
FROM services 
ORDER BY port;
"
echo ""

# 2. Check Actually Running Services
echo "🔌 STEP 2: Ports Actually Listening (8000-9000 range)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
netstat -tulpn | grep -E "80[0-9]{2}|90[0-9]{2}" | grep LISTEN | while read line; do
    PORT=$(echo "$line" | awk '{print $4}' | grep -oP ':\K\d+$')
    PID=$(echo "$line" | awk '{print $7}' | cut -d'/' -f1)
    PROGRAM=$(echo "$line" | awk '{print $7}' | cut -d'/' -f2)
    
    # Get process command
    CMD=$(ps -p $PID -o args= 2>/dev/null | head -c 60)
    
    printf "Port %5s | PID %7s | %-12s | %s\n" "$PORT" "$PID" "$PROGRAM" "$CMD"
done | sort -t'|' -k1 -n
echo ""

# 3. Test Health Endpoints
echo "🏥 STEP 3: Health Check Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Get ports from database
sudo -u postgres psql -d revcore -t -c "SELECT port FROM services ORDER BY port;" | while read port; do
    port=$(echo $port | tr -d ' ')
    if [ ! -z "$port" ]; then
        # Try common health endpoints
        for endpoint in "/health" "/api/health" "/api/v1/health" ""; do
            response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port$endpoint 2>/dev/null)
            if [ "$response" = "200" ]; then
                printf "✅ Port %5s | %-20s | HTTP %s\n" "$port" "$endpoint" "$response"
                break
            elif [ "$response" != "000" ]; then
                printf "⚠️  Port %5s | %-20s | HTTP %s\n" "$port" "$endpoint" "$response"
                break
            fi
        done
        
        # If no response, port is closed
        if [ "$response" = "000" ]; then
            printf "❌ Port %5s | %-20s | NOT RESPONDING\n" "$port" "N/A"
        fi
    fi
done
echo ""

# 4. Check Systemd Services
echo "⚙️  STEP 4: RevFlow Systemd Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
systemctl list-units --all "rev*.service" "citation*.service" --no-pager | grep -E "service|UNIT" | head -20
echo ""

# 5. Identify Discrepancies
echo "🔍 STEP 5: Registered but NOT Running (Phantom Services)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d revcore -t -c "
SELECT service_id, name, port 
FROM services 
WHERE status = 'active'
ORDER BY port;
" | while read line; do
    port=$(echo "$line" | awk -F'|' '{print $3}' | tr -d ' ')
    service_id=$(echo "$line" | awk -F'|' '{print $1}' | tr -d ' ')
    name=$(echo "$line" | awk -F'|' '{print $2}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # Check if port is listening
    if ! netstat -tulpn 2>/dev/null | grep -q ":$port "; then
        echo "❌ $service_id (port $port) - $name"
    fi
done
echo ""

# 6. Check for Services on Wrong Ports
echo "🔄 STEP 6: Port Mismatches (Registered vs Actual)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking if services registered on one port are actually on another..."
# Citation services check
for port in 8900 8901 8902 8903; do
    if netstat -tulpn 2>/dev/null | grep -q ":$port "; then
        registered=$(sudo -u postgres psql -d revcore -t -c "SELECT name FROM services WHERE port = $port;" | tr -d ' ')
        if [ -z "$registered" ]; then
            pid=$(lsof -ti :$port 2>/dev/null)
            cmd=$(ps -p $pid -o args= 2>/dev/null | head -c 50)
            echo "⚠️  Port $port is ACTIVE but NOT REGISTERED: $cmd"
        fi
    fi
done
echo ""

# 7. Check Citation Service Files
echo "📁 STEP 7: Citation Service API Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lh /opt/revflow-citations/*api*.py 2>/dev/null || echo "No API files found"
ls -lh /opt/revcite/integrations/*api*.py 2>/dev/null || echo "No RevCite API files found"
echo ""

# 8. Final Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                        SUMMARY                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"

total_registered=$(sudo -u postgres psql -d revcore -t -c "SELECT COUNT(*) FROM services WHERE status = 'active';" | tr -d ' ')
total_healthy=$(python3 /opt/shared-api-engine/check_service_health.py 2>/dev/null | grep "✅" | wc -l)
total_issues=$(python3 /opt/shared-api-engine/check_service_health.py 2>/dev/null | grep -E "❌|⚠️" | wc -l)

echo "📊 Total Registered Services: $total_registered"
echo "✅ Healthy Services: $total_healthy"
echo "❌ Services with Issues: $total_issues"
echo ""

