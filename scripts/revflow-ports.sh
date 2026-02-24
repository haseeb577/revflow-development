#!/bin/bash
#===============================================================================
# REVFLOW OS™ - PORT ALLOCATION AUDIT
# Version: 1.0.0
# Purpose: Audit port usage and detect conflicts
# Usage: ./revflow-ports.sh [--check PORT] [--find-free] [--conflicts]
#===============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Source environment
ENV_FILE="/opt/shared-api-engine/.env"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

#-------------------------------------------------------------------------------
# Known Port Allocations (from SERVICE_REGISTRY)
#-------------------------------------------------------------------------------

declare -A KNOWN_PORTS=(
    # Suite I: Lead Generation
    [8700]="Module 1: RevPrompt Unified"
    [8100]="Module 2: RevScore IQ (RevHome Chat)"
    [8500]="Module 2: RevScore IQ (Main API)"
    [8501]="Module 2: RevScore IQ (Secondary)"
    [8103]="Module 3: RevRank Engine (Pipeline 1)"
    [8201]="Module 3: RevRank Engine (Pipeline 2)"
    [8220]="Module 3: RevRank Engine (Pipeline 3)"
    [8299]="Module 3: RevRank Engine (Query Fanout)"
    [8600]="Module 3: RevRank Engine (Schema Gen) ⚠️ CONFLICT"
    [8800]="Module 3: RevRank Engine (Outline Gen)"
    [8300]="Module 4: RevSEO Intelligence (Knowledge Graph)"
    [8765]="Module 4: RevSEO Intelligence (API 1)"
    [8766]="Module 4: RevSEO Intelligence (API 2)"
    [8770]="Module 4: RevSEO Intelligence (ChromaDB)"
    [8900]="Module 5: RevCite Pro (GEO Blindspot)"
    [8901]="Module 5: RevCite Pro (NAP API)"
    [8902]="Module 5: RevCite Pro (Citation Builder)"
    [8903]="Module 5: RevCite Pro (Citation Monitor)"
    [8150]="Module 7: RevWins"
    [8610]="Module 8: RevImage Engine (moved from 8600)"
    [8601]="Module 8: RevImage Engine (UI)"
    [8550]="Module 9: RevPublish (Backend)"
    [3550]="Module 9: RevPublish (Frontend)"
    [8401]="Module 10: RevMetrics (API)"
    [8402]="Module 10: RevMetrics (Backend)"
    [3400]="Module 10: RevMetrics (Frontend)"
    [8006]="Module 11: RevSignal SDK"
    [8011]="Module 12: RevIntel"
    # Suite II: Digital Landlord
    [3013]="Module 14: RevVest IQ (Reserved)"
    [8160]="Module 15: RevSPY (Query API)"
    [8162]="Module 15: RevSPY (SOV API)"
    # Suite III: Tech Efficiency
    [9000]="Module 17: RevCore (Shield)"
    [8105]="Module 18: RevAssist"
    # Infrastructure
    [5432]="PostgreSQL"
    [80]="Nginx HTTP"
    [443]="Nginx HTTPS"
)

# Known conflicts
declare -A KNOWN_CONFLICTS=(
    [8600]="Module 3 (Schema Gen) AND Module 8 (RevImage) - Move Module 8 to 8610"
)

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

get_listening_ports() {
    netstat -tulpn 2>/dev/null | grep LISTEN | awk '{print $4}' | grep -oP '\d+$' | sort -n | uniq
}

get_port_process() {
    local port=$1
    netstat -tulpn 2>/dev/null | grep ":${port}\s" | awk '{print $NF}' | head -1
}

check_port_available() {
    local port=$1
    if netstat -tulpn 2>/dev/null | grep -q ":${port}\s"; then
        return 1  # In use
    fi
    return 0  # Available
}

print_port_table() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                      REVFLOW OS PORT ALLOCATION MAP                        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    printf "%-8s %-12s %-45s %-15s\n" "PORT" "STATUS" "ASSIGNED TO" "PROCESS"
    echo "─────────────────────────────────────────────────────────────────────────────"
    
    # Get all listening ports in RevFlow ranges
    local all_ports=()
    
    # Add known ports
    for port in "${!KNOWN_PORTS[@]}"; do
        all_ports+=("$port")
    done
    
    # Add actually listening ports
    while read -r port; do
        if [[ $port -ge 3000 && $port -le 9999 ]]; then
            if [[ ! " ${all_ports[*]} " =~ " ${port} " ]]; then
                all_ports+=("$port")
            fi
        fi
    done < <(get_listening_ports)
    
    # Sort and display
    IFS=$'\n' sorted_ports=($(sort -n <<<"${all_ports[*]}")); unset IFS
    
    for port in "${sorted_ports[@]}"; do
        local status=""
        local assigned="${KNOWN_PORTS[$port]:-UNKNOWN}"
        local process=$(get_port_process "$port")
        
        if check_port_available "$port"; then
            status="${YELLOW}FREE${NC}"
            process="-"
        else
            status="${GREEN}ACTIVE${NC}"
        fi
        
        # Check for conflicts
        if [[ -n "${KNOWN_CONFLICTS[$port]:-}" ]]; then
            status="${RED}CONFLICT${NC}"
            assigned="${RED}${assigned}${NC}"
        fi
        
        printf "%-8s %-20b %-45s %-15s\n" "$port" "$status" "$assigned" "${process:--}"
    done
}

find_free_ports() {
    local count=${1:-5}
    local range_start=${2:-8000}
    local range_end=${3:-8999}
    
    echo ""
    echo -e "${BLUE}Finding $count free ports in range $range_start-$range_end...${NC}"
    echo ""
    
    local found=0
    for ((port=range_start; port<=range_end && found<count; port++)); do
        # Skip known assigned ports
        if [[ -z "${KNOWN_PORTS[$port]:-}" ]]; then
            if check_port_available "$port"; then
                echo -e "  ${GREEN}✓${NC} Port $port is available"
                ((found++))
            fi
        fi
    done
    
    if [[ $found -lt $count ]]; then
        echo ""
        echo -e "${YELLOW}⚠ Only found $found free ports in specified range${NC}"
    fi
}

check_specific_port() {
    local port=$1
    
    echo ""
    echo -e "${BLUE}Checking port $port...${NC}"
    echo ""
    
    if [[ -n "${KNOWN_PORTS[$port]:-}" ]]; then
        echo -e "  ${BLUE}ℹ${NC} Assigned to: ${KNOWN_PORTS[$port]}"
    else
        echo -e "  ${BLUE}ℹ${NC} Not in known allocations"
    fi
    
    if [[ -n "${KNOWN_CONFLICTS[$port]:-}" ]]; then
        echo -e "  ${RED}⚠ CONFLICT: ${KNOWN_CONFLICTS[$port]}${NC}"
    fi
    
    if check_port_available "$port"; then
        echo -e "  ${GREEN}✓${NC} Port is FREE (not listening)"
    else
        local process=$(get_port_process "$port")
        echo -e "  ${YELLOW}●${NC} Port is IN USE by: $process"
        
        # Try to curl it
        if curl -sf --max-time 2 "http://localhost:$port/" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} HTTP responds on port"
        elif curl -sf --max-time 2 "http://localhost:$port/health" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Health endpoint responds"
        else
            echo -e "  ${YELLOW}⚠${NC} Port listening but HTTP not responding"
        fi
    fi
}

check_conflicts() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    PORT CONFLICT ANALYSIS                      ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local conflicts_found=0
    
    # Check known conflicts
    echo -e "${CYAN}Known Conflicts:${NC}"
    for port in "${!KNOWN_CONFLICTS[@]}"; do
        echo -e "  ${RED}⚠${NC} Port $port: ${KNOWN_CONFLICTS[$port]}"
        ((conflicts_found++))
    done
    
    echo ""
    echo -e "${CYAN}Checking for duplicate listeners...${NC}"
    
    # Check for multiple processes on same port (shouldn't happen but check anyway)
    while read -r port; do
        local count=$(netstat -tulpn 2>/dev/null | grep -c ":${port}\s" || echo 0)
        if [[ $count -gt 1 ]]; then
            echo -e "  ${RED}⚠${NC} Port $port has $count listeners!"
            netstat -tulpn 2>/dev/null | grep ":${port}\s" | awk '{print "      " $NF}'
            ((conflicts_found++))
        fi
    done < <(get_listening_ports)
    
    echo ""
    if [[ $conflicts_found -eq 0 ]]; then
        echo -e "${GREEN}✓ No active port conflicts detected${NC}"
    else
        echo -e "${RED}⚠ $conflicts_found conflict(s) found - review above${NC}"
    fi
}

query_database_ports() {
    echo ""
    echo -e "${BLUE}Querying port allocations from database...${NC}"
    echo ""
    
    if command -v psql &> /dev/null && [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
        PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -p 5432 \
            -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-revflow}" \
            -c "SELECT module_number, module_name, port, status FROM revflow_service_registry ORDER BY port;" \
            2>/dev/null || echo "Could not query database"
    else
        echo "Database query not available - check credentials"
    fi
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --table, -t         Show full port allocation table"
    echo "  --check PORT, -c    Check specific port"
    echo "  --find-free [N]     Find N free ports (default: 5)"
    echo "  --conflicts         Check for port conflicts"
    echo "  --database, -d      Query database for port allocations"
    echo "  --help, -h          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --table          # Show all port allocations"
    echo "  $0 --check 8550     # Check if port 8550 is available"
    echo "  $0 --find-free 10   # Find 10 free ports"
    echo "  $0 --conflicts      # Check for conflicts"
}

main() {
    case "${1:-}" in
        --table|-t)
            print_port_table
            ;;
        --check|-c)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --check requires a port number"
                exit 1
            fi
            check_specific_port "$2"
            ;;
        --find-free)
            find_free_ports "${2:-5}"
            ;;
        --conflicts)
            check_conflicts
            ;;
        --database|-d)
            query_database_ports
            ;;
        --help|-h)
            usage
            ;;
        "")
            # Default: show table and conflicts
            print_port_table
            echo ""
            check_conflicts
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
