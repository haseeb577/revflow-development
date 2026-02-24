#!/bin/bash
#===============================================================================
# REVFLOW OS™ - HEALTH CHECK SCRIPT
# Version: 1.0.0
# Purpose: Check health of all 18 modules
# Usage: ./revflow-health.sh [--module N] [--json] [--fix]
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
# Module Definitions (from SERVICE_REGISTRY)
#-------------------------------------------------------------------------------

declare -A MODULE_NAMES=(
    [1]="RevPrompt Unified"
    [2]="RevScore IQ"
    [3]="RevRank Engine"
    [4]="RevSEO Intelligence"
    [5]="RevCite Pro"
    [6]="RevHumanize"
    [7]="RevWins"
    [8]="RevImage Engine"
    [9]="RevPublish"
    [10]="RevMetrics"
    [11]="RevSignal SDK"
    [12]="RevIntel"
    [13]="RevFlow Dispatch"
    [14]="RevVest IQ"
    [15]="RevSPY"
    [16]="RevSpend IQ"
    [17]="RevCore"
    [18]="RevAssist"
)

declare -A MODULE_PORTS=(
    [1]="8700"
    [2]="8100,8500,8501"
    [3]="8103,8201,8220,8299,8600,8800"
    [4]="8300,8765,8766,8770"
    [5]="8900,8901,8902,8903"
    [6]="N/A"
    [7]="8150"
    [8]="8610"
    [9]="8550,3550"
    [10]="8401,8402,3400"
    [11]="8006"
    [12]="8011"
    [13]="WEBHOOK"
    [14]="3013"
    [15]="8160,8162"
    [16]="TBD"
    [17]="8766,9000"
    [18]="8105"
)

declare -A MODULE_SUITES=(
    [1]="Lead Gen" [2]="Lead Gen" [3]="Lead Gen" [4]="Lead Gen" [5]="Lead Gen"
    [6]="Lead Gen" [7]="Lead Gen" [8]="Lead Gen" [9]="Lead Gen" [10]="Lead Gen"
    [11]="Lead Gen" [12]="Lead Gen" [13]="Lead Gen"
    [14]="Digital Landlord" [15]="Digital Landlord"
    [16]="Tech Efficiency" [17]="Tech Efficiency" [18]="Tech Efficiency"
)

declare -A MODULE_LOCATIONS=(
    [1]="/opt/revflow-power-prompts"
    [2]="/opt/revscore_iq"
    [3]="/opt/revrank_engine"
    [4]="/opt/guru-intelligence"
    [5]="/opt/revflow-citations"
    [6]="/opt/revflow-humanization-pipeline"
    [7]="/opt/quick-wins-api"
    [8]="/opt/revflow-image-generation"
    [9]="/opt/revflow-os/modules/revpublish"
    [10]="/opt/revflow-os/modules/revmetrics"
    [11]="/opt/visitor-identification-service"
    [12]="/opt/revflow-enrichment-service"
    [13]="/opt/smarketsherpa-rr-automation"
    [14]="TBD"
    [15]="/opt/revflow-blind-spot-research"
    [16]="TBD"
    [17]="/opt/shared-api-engine"
    [18]="/var/www/revhome_assessment_engine_v2"
)

#-------------------------------------------------------------------------------
# Health Check Functions
#-------------------------------------------------------------------------------

check_port() {
    local port=$1
    if netstat -tulpn 2>/dev/null | grep -q ":${port}\s"; then
        return 0
    fi
    return 1
}

check_http() {
    local port=$1
    local endpoint=${2:-"/"}
    if curl -sf --max-time 3 "http://localhost:${port}${endpoint}" &>/dev/null; then
        return 0
    fi
    return 1
}

check_health_endpoint() {
    local port=$1
    if curl -sf --max-time 3 "http://localhost:${port}/health" &>/dev/null; then
        return 0
    fi
    return 1
}

check_directory() {
    local dir=$1
    [[ -d "$dir" ]]
}

check_module() {
    local module_num=$1
    local name="${MODULE_NAMES[$module_num]}"
    local ports="${MODULE_PORTS[$module_num]}"
    local suite="${MODULE_SUITES[$module_num]}"
    local location="${MODULE_LOCATIONS[$module_num]}"
    
    echo ""
    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ MODULE $module_num: $name${NC}"
    echo -e "${CYAN}│ Suite: $suite | Ports: $ports${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────┘${NC}"
    
    local status="HEALTHY"
    local issues=()
    
    # Check directory
    if [[ "$location" != "TBD" ]]; then
        if check_directory "$location"; then
            echo -e "  ${GREEN}✓${NC} Directory exists: $location"
        else
            echo -e "  ${RED}✗${NC} Directory MISSING: $location"
            status="ERROR"
            issues+=("Directory missing")
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Location: Not yet deployed"
        status="PLANNED"
    fi
    
    # Check ports
    if [[ "$ports" != "N/A" && "$ports" != "WEBHOOK" && "$ports" != "TBD" ]]; then
        IFS=',' read -ra PORT_ARRAY <<< "$ports"
        for port in "${PORT_ARRAY[@]}"; do
            port=$(echo "$port" | tr -d ' ')
            if check_port "$port"; then
                echo -e "  ${GREEN}✓${NC} Port $port: LISTENING"
                
                # Try health endpoint
                if check_health_endpoint "$port"; then
                    echo -e "  ${GREEN}✓${NC} Port $port: Health endpoint OK"
                elif check_http "$port"; then
                    echo -e "  ${YELLOW}⚠${NC} Port $port: Responds but no /health endpoint"
                fi
            else
                echo -e "  ${RED}✗${NC} Port $port: NOT LISTENING"
                if [[ "$status" == "HEALTHY" ]]; then
                    status="DEGRADED"
                fi
                issues+=("Port $port not listening")
            fi
        done
    elif [[ "$ports" == "N/A" ]]; then
        echo -e "  ${BLUE}ℹ${NC} Integrated module (no dedicated port)"
    elif [[ "$ports" == "WEBHOOK" ]]; then
        echo -e "  ${BLUE}ℹ${NC} Webhook-based (no dedicated port)"
    fi
    
    # Check for systemd service
    local service_pattern=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    local found_service=""
    while IFS= read -r svc; do
        if [[ -n "$svc" ]]; then
            found_service="$svc"
            if systemctl is-active --quiet "$svc" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Service: $svc (RUNNING)"
            else
                echo -e "  ${YELLOW}⚠${NC} Service: $svc (STOPPED)"
                if [[ "$status" == "HEALTHY" ]]; then
                    status="DEGRADED"
                fi
            fi
        fi
    done < <(systemctl list-unit-files --type=service 2>/dev/null | grep -i "${service_pattern}\|rev${service_pattern}" | awk '{print $1}' | head -3)
    
    if [[ -z "$found_service" && "$ports" != "N/A" && "$ports" != "WEBHOOK" && "$ports" != "TBD" ]]; then
        echo -e "  ${YELLOW}⚠${NC} No systemd service found for this module"
    fi
    
    # Check for schema (frontend modules)
    local schema_name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/-$//')
    if [[ -f "/opt/revflow-os/schemas/${schema_name}.json" ]]; then
        echo -e "  ${GREEN}✓${NC} Schema: /opt/revflow-os/schemas/${schema_name}.json"
    else
        # Try alternate names
        local found_schema=""
        for try_name in "revpublish" "revmetrics" "revaudit" "revcore"; do
            if [[ -f "/opt/revflow-os/schemas/${try_name}.json" ]] && [[ "$name" == *"${try_name^}"* ]]; then
                found_schema="/opt/revflow-os/schemas/${try_name}.json"
                break
            fi
        done
        if [[ -n "$found_schema" ]]; then
            echo -e "  ${GREEN}✓${NC} Schema: $found_schema"
        else
            echo -e "  ${BLUE}ℹ${NC} No UI schema (may not need one)"
        fi
    fi
    
    # Final status
    echo ""
    case "$status" in
        "HEALTHY")
            echo -e "  ${GREEN}STATUS: ✓ HEALTHY${NC}"
            ;;
        "DEGRADED")
            echo -e "  ${YELLOW}STATUS: ⚠ DEGRADED${NC}"
            echo "  Issues: ${issues[*]}"
            ;;
        "PLANNED")
            echo -e "  ${BLUE}STATUS: 📋 PLANNED (Not yet deployed)${NC}"
            ;;
        "ERROR")
            echo -e "  ${RED}STATUS: ✗ ERROR${NC}"
            echo "  Issues: ${issues[*]}"
            ;;
    esac
    
    echo "$status"
}

#-------------------------------------------------------------------------------
# Summary Functions
#-------------------------------------------------------------------------------

print_summary() {
    local healthy=$1
    local degraded=$2
    local error=$3
    local planned=$4
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    REVFLOW OS HEALTH SUMMARY                   ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}■${NC} Healthy:  $healthy modules"
    echo -e "  ${YELLOW}■${NC} Degraded: $degraded modules"
    echo -e "  ${RED}■${NC} Error:    $error modules"
    echo -e "  ${BLUE}■${NC} Planned:  $planned modules"
    echo ""
    
    local total=$((healthy + degraded + error))
    local percent=$((healthy * 100 / total))
    
    echo "  System Health: $percent% ($healthy/$total deployed modules healthy)"
    echo ""
    
    if [[ $error -gt 0 ]]; then
        echo -e "  ${RED}⚠ ACTION REQUIRED: $error modules have errors${NC}"
    elif [[ $degraded -gt 0 ]]; then
        echo -e "  ${YELLOW}⚠ WARNING: $degraded modules are degraded${NC}"
    else
        echo -e "  ${GREEN}✓ All deployed modules are healthy${NC}"
    fi
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    local specific_module=""
    local json_output=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --module|-m)
                specific_module="$2"
                shift 2
                ;;
            --json)
                json_output=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --module N, -m N   Check specific module (1-18)"
                echo "  --json             Output as JSON"
                echo "  --help, -h         Show this help"
                echo ""
                echo "Examples:"
                echo "  $0                 # Check all modules"
                echo "  $0 --module 9      # Check RevPublish only"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}              REVFLOW OS™ - 18 MODULE HEALTH CHECK             ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Server: $(hostname) ($(hostname -I | awk '{print $1}'))"
    echo "  Time:   $(date)"
    echo ""
    
    local healthy=0
    local degraded=0
    local error=0
    local planned=0
    
    if [[ -n "$specific_module" ]]; then
        # Check specific module
        if [[ $specific_module -ge 1 && $specific_module -le 18 ]]; then
            check_module "$specific_module"
        else
            echo "Error: Module number must be 1-18"
            exit 1
        fi
    else
        # Check all modules
        for module_num in {1..18}; do
            result=$(check_module "$module_num" | tail -1)
            case "$result" in
                "HEALTHY") ((healthy++)) ;;
                "DEGRADED") ((degraded++)) ;;
                "ERROR") ((error++)) ;;
                "PLANNED") ((planned++)) ;;
            esac
        done
        
        print_summary $healthy $degraded $error $planned
    fi
}

main "$@"
