#!/bin/bash
#===============================================================================
# REVFLOW OS™ - VERIFICATION SCRIPT
# Version: 1.0.0
# Purpose: Pre/post deployment verification to prevent AI-induced errors
# Usage: ./revflow-verify.sh [--pre-check|--post-check|--status|--audit]
#===============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REVFLOW_ROOT="/opt/revflow-os"
SCHEMAS_DIR="$REVFLOW_ROOT/schemas"
MODULES_DIR="$REVFLOW_ROOT/modules"
ENV_FILE="/opt/shared-api-engine/.env"
SERVICE_REGISTRY="/root/REVFLOW_SERVICE_REGISTRY.md"
DEPLOYMENT_RULES="/root/DEPLOYMENT_RULES.md"
NGINX_ENABLED="/etc/nginx/sites-enabled"
LOG_FILE="/var/log/revflow-verify.log"

# Source environment
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"
fi

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${YELLOW}▸ $1${NC}"
    echo "───────────────────────────────────────────────────────────────"
}

pass() {
    echo -e "  ${GREEN}✓${NC} $1"
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

#-------------------------------------------------------------------------------
# Check Functions
#-------------------------------------------------------------------------------

check_sacred_files() {
    print_section "Sacred Files Check"
    
    local all_pass=true
    
    if [[ -f "$ENV_FILE" ]]; then
        pass "Shared .env exists: $ENV_FILE"
        # Check for critical variables
        if grep -q "POSTGRES_PASSWORD" "$ENV_FILE" 2>/dev/null; then
            pass "POSTGRES_PASSWORD defined"
        else
            fail "POSTGRES_PASSWORD missing from .env"
            all_pass=false
        fi
    else
        fail "Shared .env NOT FOUND: $ENV_FILE"
        all_pass=false
    fi
    
    if [[ -f "$SERVICE_REGISTRY" ]]; then
        pass "Service Registry exists: $SERVICE_REGISTRY"
    else
        fail "Service Registry NOT FOUND: $SERVICE_REGISTRY"
        all_pass=false
    fi
    
    if [[ -f "$DEPLOYMENT_RULES" ]]; then
        pass "Deployment Rules exists: $DEPLOYMENT_RULES"
    else
        fail "Deployment Rules NOT FOUND: $DEPLOYMENT_RULES"
        all_pass=false
    fi
    
    if [[ -d "$SCHEMAS_DIR" ]]; then
        local schema_count=$(find "$SCHEMAS_DIR" -name "*.json" 2>/dev/null | wc -l)
        pass "Schemas directory exists: $SCHEMAS_DIR ($schema_count schemas)"
    else
        warn "Schemas directory NOT FOUND: $SCHEMAS_DIR"
    fi
    
    $all_pass
}

check_database_connection() {
    print_section "Database Connection Check"
    
    if command -v psql &> /dev/null; then
        if PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h localhost -p 5432 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-revflow}" -c "SELECT 1;" &>/dev/null; then
            pass "PostgreSQL connection successful"
            
            # Check service registry table
            local table_exists=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h localhost -p 5432 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-revflow}" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'revflow_service_registry');" 2>/dev/null)
            
            if [[ "$table_exists" == "t" ]]; then
                pass "revflow_service_registry table exists"
                
                # Get module count
                local module_count=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h localhost -p 5432 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-revflow}" -tAc "SELECT COUNT(*) FROM revflow_service_registry;" 2>/dev/null)
                info "Registered modules: $module_count"
            else
                warn "revflow_service_registry table NOT FOUND"
            fi
            return 0
        else
            fail "PostgreSQL connection FAILED"
            return 1
        fi
    else
        warn "psql command not found - skipping database checks"
        return 0
    fi
}

check_chromadb() {
    print_section "ChromaDB Check (RAG)"
    
    if curl -s "http://localhost:8770/api/v1/heartbeat" &>/dev/null; then
        pass "ChromaDB responding on port 8770"
    else
        warn "ChromaDB NOT responding on port 8770"
        info "ChromaDB used by: Module 4 (RevSEO), Module 5 (RevCite), Module 15 (RevSPY)"
    fi
}

check_nginx_configs() {
    print_section "Nginx Configuration Audit"
    
    if [[ -d "$NGINX_ENABLED" ]]; then
        local config_count=$(ls -1 "$NGINX_ENABLED" 2>/dev/null | wc -l)
        info "Total nginx configs in sites-enabled: $config_count"
        
        if [[ $config_count -gt 30 ]]; then
            fail "WARNING: $config_count configs found - possible duplicates!"
            warn "Previous AI sessions created duplicate configs"
        elif [[ $config_count -gt 20 ]]; then
            warn "$config_count configs found - review for duplicates"
        else
            pass "Nginx config count reasonable: $config_count"
        fi
        
        # List RevFlow-related configs
        echo ""
        info "RevFlow-related configs:"
        ls -la "$NGINX_ENABLED" 2>/dev/null | grep -iE "rev|smarket" | while read line; do
            echo "      $line"
        done
        
        # Check for syntax errors
        if nginx -t 2>&1 | grep -q "successful"; then
            pass "Nginx syntax check passed"
        else
            fail "Nginx syntax check FAILED"
            nginx -t 2>&1 | head -5
        fi
    else
        fail "Nginx sites-enabled directory NOT FOUND"
    fi
}

check_running_services() {
    print_section "RevFlow Services Status"
    
    local running=0
    local stopped=0
    
    # Check RevFlow-related systemd services
    while IFS= read -r service; do
        if [[ -n "$service" ]]; then
            if systemctl is-active --quiet "$service" 2>/dev/null; then
                pass "$service: RUNNING"
                ((running++))
            else
                fail "$service: STOPPED"
                ((stopped++))
            fi
        fi
    done < <(systemctl list-unit-files --type=service 2>/dev/null | grep -iE "rev|smarket|query-fanout|guru" | awk '{print $1}')
    
    echo ""
    info "Summary: $running running, $stopped stopped"
}

check_port_allocation() {
    print_section "Port Allocation Audit"
    
    info "Listening ports in RevFlow ranges (3000-3999, 8000-9999):"
    echo ""
    
    netstat -tulpn 2>/dev/null | grep LISTEN | grep -E ":(3[0-9]{3}|8[0-9]{3}|9[0-9]{3})\s" | sort -t: -k2 -n | while read line; do
        local port=$(echo "$line" | grep -oP ':\K\d+(?=\s)')
        local process=$(echo "$line" | awk '{print $NF}')
        echo "      Port $port: $process"
    done
    
    # Check for known conflicts
    echo ""
    info "Checking known port conflicts..."
    
    local port_8600_count=$(netstat -tulpn 2>/dev/null | grep -c ":8600\s" || true)
    if [[ $port_8600_count -gt 1 ]]; then
        fail "PORT 8600 CONFLICT: $port_8600_count processes listening"
        warn "Module 3 (Schema Gen) and Module 8 (RevImage) conflict"
        warn "Resolution: Move Module 8 to port 8610"
    elif [[ $port_8600_count -eq 1 ]]; then
        pass "Port 8600: Single process (check if correct module)"
    else
        info "Port 8600: Not in use"
    fi
}

check_module_directories() {
    print_section "Module Directory Structure"
    
    if [[ -d "$MODULES_DIR" ]]; then
        info "Modules directory: $MODULES_DIR"
        
        for module_dir in "$MODULES_DIR"/*/; do
            if [[ -d "$module_dir" ]]; then
                local module_name=$(basename "$module_dir")
                local has_backend=false
                local has_frontend=false
                local has_schema=false
                
                [[ -f "$module_dir/backend/main.py" ]] && has_backend=true
                [[ -d "$module_dir/frontend/dist" ]] && has_frontend=true
                [[ -f "$SCHEMAS_DIR/${module_name}.json" ]] && has_schema=true
                
                local status=""
                $has_backend && status+="BE " || status+="-- "
                $has_frontend && status+="FE " || status+="-- "
                $has_schema && status+="SC" || status+="--"
                
                if $has_backend && $has_frontend && $has_schema; then
                    pass "$module_name [$status]"
                elif $has_backend; then
                    warn "$module_name [$status] - incomplete"
                else
                    fail "$module_name [$status] - missing backend"
                fi
            fi
        done
    else
        warn "Modules directory NOT FOUND: $MODULES_DIR"
    fi
}

query_service_registry() {
    print_section "Service Registry Query"
    
    if command -v psql &> /dev/null && [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
        echo ""
        PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -p 5432 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-revflow}" -c "
            SELECT 
                module_number as \"#\",
                module_name as \"Module\",
                CASE suite
                    WHEN 'Lead Generation Suite' THEN 'Lead Gen'
                    WHEN 'Digital Landlord Suite' THEN 'Dig Land'
                    WHEN 'Tech Efficiency Suite' THEN 'Tech Eff'
                    ELSE suite
                END as \"Suite\",
                port as \"Port\",
                status as \"Status\"
            FROM revflow_service_registry 
            WHERE status != 'deprecated'
            ORDER BY module_number;
        " 2>/dev/null || warn "Could not query service registry"
    else
        warn "Cannot query database - check credentials"
    fi
}

#-------------------------------------------------------------------------------
# Main Check Functions
#-------------------------------------------------------------------------------

pre_check() {
    print_header "REVFLOW OS - PRE-DEPLOYMENT VERIFICATION"
    
    log "INFO" "Starting pre-check verification"
    
    local all_pass=true
    
    check_sacred_files || all_pass=false
    check_database_connection || all_pass=false
    check_chromadb
    check_nginx_configs
    check_port_allocation
    check_module_directories
    query_service_registry
    
    print_section "Pre-Check Summary"
    
    if $all_pass; then
        pass "All critical checks passed"
        echo ""
        echo -e "${GREEN}✓ SAFE TO PROCEED${NC}"
        echo ""
        info "Remember:"
        info "  1. Query revflow_service_registry before creating new modules"
        info "  2. Check nginx configs before adding new routes"
        info "  3. Use React + JSON Render pattern for frontends"
        info "  4. Create scripts for user to run on server (217.15.168.106)"
        return 0
    else
        fail "Some critical checks failed"
        echo ""
        echo -e "${RED}✗ RESOLVE ISSUES BEFORE PROCEEDING${NC}"
        return 1
    fi
}

post_check() {
    print_header "REVFLOW OS - POST-DEPLOYMENT VERIFICATION"
    
    log "INFO" "Starting post-check verification"
    
    check_sacred_files
    check_database_connection
    check_nginx_configs
    check_running_services
    check_port_allocation
    
    print_section "Post-Check Summary"
    
    echo ""
    warn "IMPORTANT: These results are from Claude's container!"
    warn "User MUST verify on actual server: 217.15.168.106"
    echo ""
    info "Provide these commands for user to run on server:"
    echo ""
    echo "  systemctl status [new-service-name]"
    echo "  curl -s http://localhost:[PORT]/health | jq"
    echo "  nginx -t && systemctl reload nginx"
}

status_check() {
    print_header "REVFLOW OS - SYSTEM STATUS"
    
    check_sacred_files
    check_database_connection
    check_chromadb
    check_running_services
    check_port_allocation
    query_service_registry
}

full_audit() {
    print_header "REVFLOW OS - FULL SYSTEM AUDIT"
    
    log "INFO" "Starting full system audit"
    
    check_sacred_files
    check_database_connection
    check_chromadb
    check_nginx_configs
    check_running_services
    check_port_allocation
    check_module_directories
    query_service_registry
    
    print_section "Audit Complete"
    
    local report_file="/tmp/revflow_audit_$(date +%Y%m%d_%H%M%S).md"
    
    {
        echo "# RevFlow OS Audit Report"
        echo "Generated: $(date)"
        echo ""
        echo "## Summary"
        echo "- Nginx configs: $(ls -1 "$NGINX_ENABLED" 2>/dev/null | wc -l)"
        echo "- Running services: $(systemctl list-units --type=service --state=running 2>/dev/null | grep -ciE 'rev|smarket' || echo 0)"
        echo "- Listening ports: $(netstat -tulpn 2>/dev/null | grep -cE ':(3[0-9]{3}|8[0-9]{3}|9[0-9]{3})\s' || echo 0)"
        echo "- Schema files: $(find "$SCHEMAS_DIR" -name "*.json" 2>/dev/null | wc -l)"
    } > "$report_file"
    
    info "Audit report saved to: $report_file"
}

#-------------------------------------------------------------------------------
# Usage and Main
#-------------------------------------------------------------------------------

usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --pre-check    Run before making any changes (REQUIRED)"
    echo "  --post-check   Run after making changes"
    echo "  --status       Quick system status"
    echo "  --audit        Full system audit"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --pre-check     # Before deployment"
    echo "  $0 --post-check    # After deployment"
    echo "  $0 --status        # Quick check"
}

main() {
    # Create log directory if needed
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    
    case "${1:-}" in
        --pre-check)
            pre_check
            ;;
        --post-check)
            post_check
            ;;
        --status)
            status_check
            ;;
        --audit)
            full_audit
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Error: Unknown option '${1:-}'"
            echo ""
            usage
            exit 1
            ;;
    esac
}

main "$@"
