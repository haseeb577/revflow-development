#!/bin/bash
# RevFlow OS™ - Container Startup Script
# Brings up all 25 containers in the correct order
# Usage: ./revflow-up.sh [--down] [--restart] [--status]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[RevFlow]${NC} $1"; }
warn() { echo -e "${YELLOW}[Warning]${NC} $1"; }
error() { echo -e "${RED}[Error]${NC} $1"; }

# Config
COMPOSE_MAIN="/opt/revflow-os/docker-compose.modules.yml"
COMPOSE_SURFSENSE="/opt/revcore-governance/surfsense/docker-compose.revcore.yml"
NETWORK_NAME="revflow-network"

# Module definitions: port:name:health_path
MODULES=(
    "8015:Gateway:/health"
    "8700:M01-RevPrompt:/health"
    "8100:M02-RevScore:/health"
    "8104:M03-RevRank:/health"
    "8765:M04-RevSEO:/health"
    "8900:M05-RevCite:/health"
    "8620:M06-RevHumanize:/health"
    "8150:M07-RevWins:/health"
    "8610:M08-RevImage:/health"
    "8550:M09-RevPublish:/health"
    "8402:M10-RevMetrics:/health"
    "8012:M11-RevSignal:/health"
    "8011:M12-RevIntel:/health"
    "8501:M13-RevDispatch:/health"
    "8140:M14-RevVest:/health"
    "8160:M15-RevSPY:/health"
    "8016:M16-RevSpend:/health"
    "9000:M17-RevCore:/health"
    "8105:M18-RevAssist:/health"
    "3002:M19-LocalGrid:/"
    "9400:RevSense-Web:/"
)

wait_for_healthy() {
    local container=$1
    local max_wait=${2:-60}
    local count=0
    log "Waiting for $container to be healthy..."
    while [ $count -lt $max_wait ]; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")
        if [ "$status" = "healthy" ]; then
            log "$container is healthy"
            return 0
        fi
        sleep 2
        count=$((count + 2))
    done
    warn "$container did not become healthy within ${max_wait}s (status: $status)"
    return 1
}

check_health() {
    echo ""
    log "Health Endpoints:"
    local ok=0
    local fail=0
    for item in "${MODULES[@]}"; do
        IFS=':' read -r port name path <<< "$item"
        status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$path" --connect-timeout 2 2>/dev/null || echo "000")
        if [ "$status" = "200" ]; then
            printf "  %-18s Port %s: ${GREEN}✓ OK${NC}\n" "$name" "$port"
            ok=$((ok + 1))
        else
            printf "  %-18s Port %s: ${RED}✗ %s${NC}\n" "$name" "$port" "$status"
            fail=$((fail + 1))
        fi
    done
    echo ""
    log "Summary: ${GREEN}$ok OK${NC}, ${RED}$fail Failed${NC}"
}

show_status() {
    log "=========================================="
    log "RevFlow OS™ Status Check"
    log "=========================================="

    echo ""
    log "Container Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "revflow|revcore" | sort

    check_health
}

shutdown_all() {
    log "Stopping all RevFlow containers..."
    docker compose -f "$COMPOSE_SURFSENSE" down 2>/dev/null || true
    docker compose -f "$COMPOSE_MAIN" down 2>/dev/null || true
    log "All containers stopped"
}

startup_all() {
    log "=========================================="
    log "RevFlow OS™ Container Startup"
    log "=========================================="

    # Step 1: Ensure network exists
    log "Step 1: Creating network if needed..."
    docker network create "$NETWORK_NAME" 2>/dev/null || true

    # Step 2: Start Infrastructure (PostgreSQL, Redis, ChromaDB)
    log "Step 2: Starting infrastructure..."
    docker compose -f "$COMPOSE_MAIN" up -d postgres redis chromadb
    wait_for_healthy "revflow-postgres-docker" 90

    # Step 3: Start RevCore Gateway
    log "Step 3: Starting RevCore Gateway..."
    docker compose -f "$COMPOSE_MAIN" up -d revcore-gateway
    wait_for_healthy "revcore-gateway" 60

    # Step 4: Start all 19 modules
    log "Step 4: Starting all 19 modules..."
    docker compose -f "$COMPOSE_MAIN" up -d \
        revprompt \
        revscore \
        revrank \
        revseo \
        revcite \
        revhumanize \
        revwins \
        revimage \
        revpublish \
        revmetrics \
        revsignal \
        revintel \
        revdispatch \
        revvest \
        revspy \
        revspend \
        revcore \
        revassist \
        revlocalgrid

    # Step 5: Start RevSense (SurfSense)
    log "Step 5: Starting RevSense (SurfSense)..."
    docker compose -f "$COMPOSE_SURFSENSE" up -d

    # Step 6: Wait for modules to initialize
    log "Step 6: Waiting for modules to initialize..."
    sleep 45

    # Step 7: Health summary
    log "=========================================="
    log "Startup complete!"
    log "=========================================="

    echo ""
    log "Container Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "revflow|revcore" | sort

    check_health
}

show_help() {
    echo "RevFlow OS™ Container Management"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  (none)      Start all containers in correct order"
    echo "  --down      Stop all containers"
    echo "  --restart   Stop and start all containers"
    echo "  --status    Check health of all modules"
    echo "  --help      Show this help message"
    echo ""
}

case "${1:-}" in
    --down)
        shutdown_all
        ;;
    --restart)
        shutdown_all
        sleep 5
        startup_all
        ;;
    --status)
        show_status
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        startup_all
        ;;
esac

log "Done!"
