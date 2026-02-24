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
    RPAD(status::text, 8)
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
    CMD=$(ps -p $PID -o args= 2>/dev/null | head -c 60)
    printf "Port %5s | PID %7s | %-12s | %s\n" "$PORT" "$PID" "$PROGRAM" "$CMD"
done | sort -t'|' -k1 -n
echo ""

# 3. Test Health Endpoints
echo "🏥 STEP 3: Health Check Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d revcore -t -c "SELECT port FROM services ORDER BY port;" | while read port; do
    port=$(echo $port | tr -d ' ')
    if [ ! -z "$port" ]; then
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
        if [ "$response" = "000" ]; then
            printf "❌ Port %5s | %-20s | NOT RESPONDING\n" "$port" "N/A"
        fi
    fi
done
echo ""

# 4. Identify Discrepancies
echo "🔍 STEP 4: Service Status Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d revcore -t -c "
SELECT service_id, name, port 
FROM services 
WHERE status::text = 'active'
ORDER BY port;
" | while read line; do
    port=$(echo "$line" | awk -F'|' '{print $3}' | tr -d ' ')
    service_id=$(echo "$line" | awk -F'|' '{print $1}' | tr -d ' ')
    name=$(echo "$line" | awk -F'|' '{print $2}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # Check if port is listening
    if netstat -tulpn 2>/dev/null | grep -q ":$port "; then
        # Check health
        health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null)
        if [ "$health" = "200" ]; then
            echo "✅ $service_id (port $port) - $name - HEALTHY"
        else
            echo "⚠️  $service_id (port $port) - $name - Running but HTTP $health"
        fi
    else
        echo "❌ $service_id (port $port) - $name - NOT RUNNING"
    fi
done
echo ""

# 5. Final Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                        FINAL STATUS                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"

total=$(sudo -u postgres psql -d revcore -t -c "SELECT COUNT(*) FROM services WHERE status::text = 'active';" | tr -d ' ')
healthy=$(sudo -u postgres psql -d revcore -t -c "SELECT port FROM services WHERE status::text = 'active'" | while read port; do
    port=$(echo $port | tr -d ' ')
    if [ ! -z "$port" ]; then
        if netstat -tulpn 2>/dev/null | grep -q ":$port "; then
            health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null)
            [ "$health" = "200" ] && echo "1"
        fi
    fi
done | wc -l)

echo "📊 Total Active Services: $total"
echo "✅ Healthy (HTTP 200): $healthy"
echo "⚠️  Needs Attention: $((total - healthy))"
echo ""
echo "🎉 SUCCESS RATE: $(( (healthy * 100) / total ))%"
echo ""

