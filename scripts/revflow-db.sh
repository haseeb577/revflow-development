#!/bin/bash
#===============================================================================
# REVFLOW OS™ - DATABASE REGISTRY QUERY
# Version: 1.0.0
# Purpose: Query and manage the revflow_service_registry
# Usage: ./revflow-db.sh [--list] [--module N] [--update] [--add]
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
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"
else
    echo -e "${RED}Error: Cannot find $ENV_FILE${NC}"
    echo "This file is required for database credentials."
    exit 1
fi

# Database connection
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-revflow}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASS="${POSTGRES_PASSWORD:-}"

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

run_query() {
    local query=$1
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$query" 2>/dev/null
}

run_query_quiet() {
    local query=$1
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "$query" 2>/dev/null
}

check_connection() {
    if ! PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
        echo -e "${RED}Error: Cannot connect to PostgreSQL${NC}"
        echo "Host: $DB_HOST:$DB_PORT"
        echo "Database: $DB_NAME"
        echo "User: $DB_USER"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Registry Functions
#-------------------------------------------------------------------------------

list_all_modules() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                      REVFLOW SERVICE REGISTRY                                  ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    run_query "
        SELECT 
            module_number as \"#\",
            module_name as \"Module Name\",
            CASE suite
                WHEN 'Lead Generation Suite' THEN 'Lead Gen'
                WHEN 'Digital Landlord Suite' THEN 'Dig Land'
                WHEN 'Tech Efficiency Suite' THEN 'Tech Eff'
                ELSE COALESCE(suite, 'Unknown')
            END as \"Suite\",
            COALESCE(port::text, 'N/A') as \"Port\",
            COALESCE(status, 'unknown') as \"Status\",
            COALESCE(location, 'TBD') as \"Location\"
        FROM revflow_service_registry 
        ORDER BY module_number;
    "
}

show_module_details() {
    local module_num=$1
    
    echo ""
    echo -e "${BLUE}Module $module_num Details:${NC}"
    echo ""
    
    run_query "
        SELECT *
        FROM revflow_service_registry 
        WHERE module_number = $module_num;
    "
}

show_by_status() {
    local status=$1
    
    echo ""
    echo -e "${BLUE}Modules with status: $status${NC}"
    echo ""
    
    run_query "
        SELECT 
            module_number as \"#\",
            module_name as \"Module\",
            port as \"Port\",
            location as \"Location\"
        FROM revflow_service_registry 
        WHERE LOWER(status) = LOWER('$status')
        ORDER BY module_number;
    "
}

show_by_suite() {
    local suite=$1
    
    echo ""
    echo -e "${BLUE}Modules in suite: $suite${NC}"
    echo ""
    
    run_query "
        SELECT 
            module_number as \"#\",
            module_name as \"Module\",
            port as \"Port\",
            status as \"Status\"
        FROM revflow_service_registry 
        WHERE LOWER(suite) LIKE LOWER('%$suite%')
        ORDER BY module_number;
    "
}

show_port_allocations() {
    echo ""
    echo -e "${BLUE}Port Allocations from Registry:${NC}"
    echo ""
    
    run_query "
        SELECT 
            port as \"Port\",
            module_number as \"Module #\",
            module_name as \"Module Name\",
            status as \"Status\"
        FROM revflow_service_registry 
        WHERE port IS NOT NULL
        ORDER BY port;
    "
}

check_port_available() {
    local port=$1
    
    local exists=$(run_query_quiet "SELECT COUNT(*) FROM revflow_service_registry WHERE port = $port;")
    
    if [[ "$exists" == "0" ]]; then
        echo -e "${GREEN}✓ Port $port is not assigned in registry${NC}"
    else
        echo -e "${YELLOW}⚠ Port $port is already assigned:${NC}"
        run_query "SELECT module_number, module_name FROM revflow_service_registry WHERE port = $port;"
    fi
}

update_module_status() {
    local module_num=$1
    local new_status=$2
    
    echo -e "${CYAN}Updating module $module_num status to: $new_status${NC}"
    
    run_query "
        UPDATE revflow_service_registry 
        SET status = '$new_status', updated_at = NOW()
        WHERE module_number = $module_num;
    "
    
    echo -e "${GREEN}✓ Updated${NC}"
    show_module_details "$module_num"
}

update_module_port() {
    local module_num=$1
    local new_port=$2
    
    # Check if port is already used
    local existing=$(run_query_quiet "SELECT module_number FROM revflow_service_registry WHERE port = $new_port AND module_number != $module_num;")
    
    if [[ -n "$existing" ]]; then
        echo -e "${RED}Error: Port $new_port is already assigned to module $existing${NC}"
        return 1
    fi
    
    echo -e "${CYAN}Updating module $module_num port to: $new_port${NC}"
    
    run_query "
        UPDATE revflow_service_registry 
        SET port = $new_port, updated_at = NOW()
        WHERE module_number = $module_num;
    "
    
    echo -e "${GREEN}✓ Updated${NC}"
    show_module_details "$module_num"
}

create_registry_table() {
    echo -e "${CYAN}Creating revflow_service_registry table...${NC}"
    
    run_query "
        CREATE TABLE IF NOT EXISTS revflow_service_registry (
            id SERIAL PRIMARY KEY,
            module_number INTEGER UNIQUE NOT NULL,
            module_name VARCHAR(100) NOT NULL,
            suite VARCHAR(100),
            port INTEGER,
            status VARCHAR(50) DEFAULT 'planned',
            location VARCHAR(255),
            service_name VARCHAR(100),
            description TEXT,
            dependencies TEXT[],
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_registry_module_number ON revflow_service_registry(module_number);
        CREATE INDEX IF NOT EXISTS idx_registry_port ON revflow_service_registry(port);
        CREATE INDEX IF NOT EXISTS idx_registry_status ON revflow_service_registry(status);
    "
    
    echo -e "${GREEN}✓ Table created${NC}"
}

seed_registry() {
    echo -e "${CYAN}Seeding registry with 18-module architecture...${NC}"
    
    run_query "
        INSERT INTO revflow_service_registry (module_number, module_name, suite, port, status, location) VALUES
        (1, 'RevPrompt Unified', 'Lead Generation Suite', 8700, 'deployed', '/opt/revflow-power-prompts'),
        (2, 'RevScore IQ', 'Lead Generation Suite', 8100, 'deployed', '/opt/revscore_iq'),
        (3, 'RevRank Engine', 'Lead Generation Suite', 8299, 'deployed', '/opt/revrank_engine'),
        (4, 'RevSEO Intelligence', 'Lead Generation Suite', 8770, 'deployed', '/opt/guru-intelligence'),
        (5, 'RevCite Pro', 'Lead Generation Suite', 8900, 'deployed', '/opt/revflow-citations'),
        (6, 'RevHumanize', 'Lead Generation Suite', NULL, 'deployed', '/opt/revflow-humanization-pipeline'),
        (7, 'RevWins', 'Lead Generation Suite', 8150, 'deployed', '/opt/quick-wins-api'),
        (8, 'RevImage Engine', 'Lead Generation Suite', 8610, 'deployed', '/opt/revflow-image-generation'),
        (9, 'RevPublish', 'Lead Generation Suite', 8550, 'partial', '/opt/revflow-os/modules/revpublish'),
        (10, 'RevMetrics', 'Lead Generation Suite', 8401, 'partial', '/opt/revflow-os/modules/revmetrics'),
        (11, 'RevSignal SDK', 'Lead Generation Suite', 8006, 'deployed', '/opt/visitor-identification-service'),
        (12, 'RevIntel', 'Lead Generation Suite', 8011, 'deployed', '/opt/revflow-enrichment-service'),
        (13, 'RevFlow Dispatch', 'Lead Generation Suite', NULL, 'deployed', '/opt/smarketsherpa-rr-automation'),
        (14, 'RevVest IQ', 'Digital Landlord Suite', 3013, 'planned', NULL),
        (15, 'RevSPY', 'Digital Landlord Suite', 8160, 'deployed', '/opt/revflow-blind-spot-research'),
        (16, 'RevSpend IQ', 'Tech Efficiency Suite', NULL, 'planned', NULL),
        (17, 'RevCore', 'Tech Efficiency Suite', 9000, 'deployed', '/opt/shared-api-engine'),
        (18, 'RevAssist', 'Tech Efficiency Suite', 8105, 'deployed', '/var/www/revhome_assessment_engine_v2')
        ON CONFLICT (module_number) DO UPDATE SET
            module_name = EXCLUDED.module_name,
            suite = EXCLUDED.suite,
            port = EXCLUDED.port,
            status = EXCLUDED.status,
            location = EXCLUDED.location,
            updated_at = NOW();
    "
    
    echo -e "${GREEN}✓ Registry seeded with 18 modules${NC}"
    list_all_modules
}

export_to_markdown() {
    local output_file=${1:-"/tmp/revflow_registry_$(date +%Y%m%d).md"}
    
    echo -e "${CYAN}Exporting registry to: $output_file${NC}"
    
    {
        echo "# RevFlow OS Service Registry"
        echo "Generated: $(date)"
        echo ""
        echo "## All Modules"
        echo ""
        echo "| # | Module | Suite | Port | Status | Location |"
        echo "|---|--------|-------|------|--------|----------|"
        
        run_query_quiet "
            SELECT 
                module_number || '|' || 
                module_name || '|' ||
                COALESCE(suite, 'N/A') || '|' ||
                COALESCE(port::text, 'N/A') || '|' ||
                COALESCE(status, 'unknown') || '|' ||
                COALESCE(location, 'TBD')
            FROM revflow_service_registry 
            ORDER BY module_number;
        " | while read line; do
            echo "| $line |"
        done
        
        echo ""
        echo "## Statistics"
        echo ""
        echo "- Total modules: $(run_query_quiet "SELECT COUNT(*) FROM revflow_service_registry;")"
        echo "- Deployed: $(run_query_quiet "SELECT COUNT(*) FROM revflow_service_registry WHERE status='deployed';")"
        echo "- Partial: $(run_query_quiet "SELECT COUNT(*) FROM revflow_service_registry WHERE status='partial';")"
        echo "- Planned: $(run_query_quiet "SELECT COUNT(*) FROM revflow_service_registry WHERE status='planned';")"
    } > "$output_file"
    
    echo -e "${GREEN}✓ Exported to: $output_file${NC}"
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --list, -l              List all modules"
    echo "  --module N, -m N        Show details for module N"
    echo "  --status STATUS         Show modules with status"
    echo "  --suite SUITE           Show modules in suite"
    echo "  --ports                 Show port allocations"
    echo "  --check-port PORT       Check if port is available"
    echo "  --update-status N ST    Update module N status to ST"
    echo "  --update-port N PORT    Update module N port"
    echo "  --create-table          Create registry table"
    echo "  --seed                  Seed with 18-module data"
    echo "  --export [FILE]         Export to markdown"
    echo "  --help, -h              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --list               # List all modules"
    echo "  $0 --module 9           # Show RevPublish details"
    echo "  $0 --status deployed    # Show deployed modules"
    echo "  $0 --check-port 8650    # Check port availability"
}

main() {
    check_connection
    
    case "${1:-}" in
        --list|-l)
            list_all_modules
            ;;
        --module|-m)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --module requires a module number"
                exit 1
            fi
            show_module_details "$2"
            ;;
        --status)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --status requires a status value"
                exit 1
            fi
            show_by_status "$2"
            ;;
        --suite)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --suite requires a suite name"
                exit 1
            fi
            show_by_suite "$2"
            ;;
        --ports)
            show_port_allocations
            ;;
        --check-port)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --check-port requires a port number"
                exit 1
            fi
            check_port_available "$2"
            ;;
        --update-status)
            if [[ -z "${2:-}" || -z "${3:-}" ]]; then
                echo "Error: --update-status requires MODULE_NUMBER and STATUS"
                exit 1
            fi
            update_module_status "$2" "$3"
            ;;
        --update-port)
            if [[ -z "${2:-}" || -z "${3:-}" ]]; then
                echo "Error: --update-port requires MODULE_NUMBER and PORT"
                exit 1
            fi
            update_module_port "$2" "$3"
            ;;
        --create-table)
            create_registry_table
            ;;
        --seed)
            seed_registry
            ;;
        --export)
            export_to_markdown "${2:-}"
            ;;
        --help|-h)
            usage
            ;;
        "")
            list_all_modules
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
