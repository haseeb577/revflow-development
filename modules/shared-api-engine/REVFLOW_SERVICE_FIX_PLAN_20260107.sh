#!/bin/bash
# RevFlow Service Fix Script
# Generated: 2026-01-07
# This script fixes and starts all RevFlow services

set -e

echo "=========================================="
echo "RevFlow Service Fix Script"
echo "=========================================="
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local port=$1
    local name=$2
    local status=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 http://localhost:$port/health 2>/dev/null)
    if [ "$status" = "200" ]; then
        echo -e "${GREEN}✓${NC} $name (port $port): healthy"
        return 0
    else
        local root_status=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 http://localhost:$port/ 2>/dev/null)
        if [ "$root_status" = "200" ] || [ "$root_status" = "302" ]; then
            echo -e "${YELLOW}~${NC} $name (port $port): responding (no /health)"
            return 0
        else
            echo -e "${RED}✗${NC} $name (port $port): down"
            return 1
        fi
    fi
}

# ============================================================
# TASK 1: Ensure Content Service (8006)
# ============================================================
echo "--- Content Service (8006) ---"
if ! check_service 8006 "Content Service"; then
    echo "Starting Content Service..."
    pkill -f 'uvicorn app.main:app.*8006' 2>/dev/null || true
    sleep 1
    cd /opt/revrank-admin/backend
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8006 > /tmp/content-service.log 2>&1 &
    sleep 3
    check_service 8006 "Content Service"
fi
echo

# ============================================================
# TASK 2: Ensure Scoring Engine (8005)
# ============================================================
echo "--- Scoring Engine (8005) ---"
if ! check_service 8005 "Scoring Engine"; then
    echo "Starting Scoring Engine..."
    pkill -f 'python.*api_server.py' 2>/dev/null || true
    sleep 1
    cd /opt/revflow-revenue-aligned-scoring-system
    source venv/bin/activate
    nohup python api_server.py >> /var/log/revflow-lead-scoring-api.log 2>&1 &
    sleep 3
    check_service 8005 "Scoring Engine"
fi
echo

# ============================================================
# TASK 3: Ensure RevCite (8600)
# ============================================================
echo "--- RevCite Service (8600) ---"
if ! check_service 8600 "RevCite"; then
    echo "Starting RevCite..."
    pkill -f 'python.*revcite.*api' 2>/dev/null || true
    sleep 1
    cd /opt/revcite
    nohup python3 api.py > logs/api.log 2>&1 &
    sleep 3
    check_service 8600 "RevCite"
fi
echo

# ============================================================
# Citation Services (8900-8903)
# ============================================================
echo "--- Citation Services ---"
check_service 8900 "Citation Geo"
check_service 8901 "Citation Pricing"
check_service 8902 "Citation Builder"
check_service 8903 "Citation Monitor"
echo

# ============================================================
# Other Services
# ============================================================
echo "--- Other Services ---"
check_service 3000 "Grafana"
check_service 3001 "Intelligence Modules"
check_service 8001 "Portfolio API"
check_service 8299 "Query Fanout"
echo

# ============================================================
# Docker Services Check
# ============================================================
echo "--- Docker Services ---"
docker_services=("revflow_revintel" "revflow_revsignal" "revflow_postgres")
for svc in "${docker_services[@]}"; do
    status=$(docker inspect -f '{{.State.Health.Status}}' $svc 2>/dev/null || echo "not_found")
    if [ "$status" = "healthy" ]; then
        echo -e "${GREEN}✓${NC} $svc: healthy"
    elif [ "$status" = "not_found" ]; then
        echo -e "${RED}✗${NC} $svc: not found"
    else
        echo -e "${YELLOW}~${NC} $svc: $status"
    fi
done
echo

# Check RevIntel and RevSignal database connections
echo "--- Docker API Health ---"
revintel_db=$(curl -s http://localhost:8011/health 2>/dev/null | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
revsignal_db=$(curl -s http://localhost:8007/health 2>/dev/null | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
echo "RevIntel (8011) database: $revintel_db"
echo "RevSignal (8007) database: $revsignal_db"
echo

# ============================================================
# Summary
# ============================================================
echo "=========================================="
echo "Service Status Summary"
echo "=========================================="
echo
total=0
healthy=0
for port in 8005 8006 8600 8900 8901 8902 8903; do
    ((total++))
    status=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 http://localhost:$port/health 2>/dev/null)
    if [ "$status" = "200" ]; then
        ((healthy++))
    fi
done

echo "Core Services: $healthy/$total healthy"
echo
echo "RevCore Registry:"
sudo -u postgres psql -d revcore -t -c "SELECT service_id || ' (' || port || ')' FROM services WHERE status = 'active' ORDER BY port;"
echo
echo "Done!"
