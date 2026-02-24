#!/bin/bash
#===============================================================================
# REVFLOW OS™ - NGINX CONFIGURATION AUDIT
# Version: 1.0.0
# Purpose: Audit nginx configs, detect duplicates, verify routes
# Usage: ./revflow-nginx.sh [--routes] [--duplicates] [--test] [--module NAME]
#===============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

NGINX_ENABLED="/etc/nginx/sites-enabled"
NGINX_AVAILABLE="/etc/nginx/sites-available"

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

count_configs() {
    ls -1 "$NGINX_ENABLED" 2>/dev/null | wc -l
}

list_configs() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}              NGINX CONFIGURATION FILES                        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local count=$(count_configs)
    echo -e "Total configs in sites-enabled: ${CYAN}$count${NC}"
    echo ""
    
    if [[ $count -gt 25 ]]; then
        echo -e "${RED}⚠ WARNING: Too many configs! Likely duplicates from AI sessions.${NC}"
        echo ""
    fi
    
    echo "Files:"
    echo "───────────────────────────────────────────────────────────────"
    ls -la "$NGINX_ENABLED" 2>/dev/null | tail -n +2 | while read line; do
        echo "  $line"
    done
}

extract_routes() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    NGINX ROUTE MAP                            ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    printf "%-30s %-15s %-30s\n" "ROUTE" "TYPE" "TARGET"
    echo "─────────────────────────────────────────────────────────────────────────────"
    
    # Extract location blocks from all configs
    for config in "$NGINX_ENABLED"/*; do
        if [[ -f "$config" ]]; then
            local filename=$(basename "$config")
            
            # Extract proxy_pass locations
            grep -E "location\s+[^\{]+\{" "$config" 2>/dev/null | while read location_line; do
                local route=$(echo "$location_line" | grep -oP "location\s+\K[^\s{]+")
                
                # Find the proxy_pass for this location
                local target=$(awk -v loc="$route" '
                    /location.*'"$route"'/ {found=1}
                    found && /proxy_pass/ {print $2; exit}
                    found && /alias/ {print "alias:" $2; exit}
                    found && /root/ {print "root:" $2; exit}
                    found && /}/ {found=0}
                ' "$config" 2>/dev/null | tr -d ';')
                
                if [[ -n "$target" ]]; then
                    local type="proxy"
                    [[ "$target" == alias:* ]] && type="static"
                    [[ "$target" == root:* ]] && type="static"
                    
                    printf "%-30s %-15s %-30s\n" "$route" "$type" "${target:-N/A}"
                fi
            done
        fi
    done | sort -u
}

find_duplicates() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                 DUPLICATE ROUTE DETECTION                     ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local duplicates_found=0
    
    # Find duplicate location blocks across all configs
    echo -e "${CYAN}Checking for duplicate routes...${NC}"
    echo ""
    
    # Extract all location definitions
    local locations_file=$(mktemp)
    for config in "$NGINX_ENABLED"/*; do
        if [[ -f "$config" ]]; then
            grep -oP "location\s+\K[^\s{]+" "$config" 2>/dev/null | while read loc; do
                echo "$loc|$(basename "$config")"
            done
        fi
    done > "$locations_file"
    
    # Find duplicates
    cut -d'|' -f1 "$locations_file" | sort | uniq -d | while read dup_route; do
        if [[ -n "$dup_route" ]]; then
            echo -e "${RED}⚠ DUPLICATE: $dup_route${NC}"
            echo "   Defined in:"
            grep "^${dup_route}|" "$locations_file" | cut -d'|' -f2 | while read file; do
                echo "      - $file"
            done
            echo ""
            ((duplicates_found++)) || true
        fi
    done
    
    rm -f "$locations_file"
    
    # Check for multiple configs for same module
    echo -e "${CYAN}Checking for duplicate module configs...${NC}"
    echo ""
    
    for module in revpublish revmetrics revaudit revimage revcore revintel revsignal revwins revrank; do
        local count=$(ls -1 "$NGINX_ENABLED" 2>/dev/null | grep -ci "$module" || echo 0)
        if [[ $count -gt 1 ]]; then
            echo -e "${RED}⚠ Module '$module' has $count nginx configs!${NC}"
            ls -la "$NGINX_ENABLED" 2>/dev/null | grep -i "$module"
            echo ""
            ((duplicates_found++)) || true
        fi
    done
    
    if [[ $duplicates_found -eq 0 ]]; then
        echo -e "${GREEN}✓ No duplicate routes or configs detected${NC}"
    else
        echo ""
        echo -e "${RED}Found $duplicates_found potential duplicate(s)${NC}"
        echo ""
        echo "Recommendation: Review and remove duplicate configs"
        echo "Keep only the canonical config for each module"
    fi
}

test_routes() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    ROUTE HEALTH CHECK                         ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Test nginx syntax first
    echo -e "${CYAN}Testing nginx syntax...${NC}"
    if nginx -t 2>&1 | grep -q "successful"; then
        echo -e "${GREEN}✓ Nginx syntax OK${NC}"
    else
        echo -e "${RED}✗ Nginx syntax errors:${NC}"
        nginx -t 2>&1 | head -10
        return 1
    fi
    
    echo ""
    echo -e "${CYAN}Testing API routes (via localhost)...${NC}"
    echo ""
    
    printf "%-30s %-10s %-20s\n" "ROUTE" "STATUS" "RESPONSE"
    echo "─────────────────────────────────────────────────────────────────────────────"
    
    # Test known API routes
    local routes=(
        "/api/fanout/"
        "/api/revpublish/"
        "/api/revmetrics/"
        "/api/revcore/"
        "/api/revintel/"
        "/api/signal/"
        "/api/chat/"
        "/api/prompt/"
        "/api/geo/"
        "/api/nap/"
        "/api/shield/"
        "/schemas/"
    )
    
    for route in "${routes[@]}"; do
        local status=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost${route}" 2>/dev/null || echo "ERR")
        local response=""
        
        case "$status" in
            200|201)
                response="${GREEN}OK${NC}"
                ;;
            502)
                response="${RED}Backend down${NC}"
                ;;
            404)
                response="${YELLOW}Not found${NC}"
                ;;
            ERR)
                response="${RED}Connection failed${NC}"
                status="---"
                ;;
            *)
                response="${YELLOW}HTTP $status${NC}"
                ;;
        esac
        
        printf "%-30s %-10s %-20b\n" "$route" "$status" "$response"
    done
}

check_module_config() {
    local module=$1
    
    echo ""
    echo -e "${BLUE}Checking nginx config for module: $module${NC}"
    echo ""
    
    # Find configs mentioning this module
    local found=false
    for config in "$NGINX_ENABLED"/*; do
        if [[ -f "$config" ]] && grep -qi "$module" "$config" 2>/dev/null; then
            found=true
            echo -e "${CYAN}Found in: $(basename "$config")${NC}"
            echo "───────────────────────────────────────────────────────────────"
            grep -A10 -B2 "$module" "$config" 2>/dev/null || true
            echo ""
        fi
    done
    
    if ! $found; then
        echo -e "${YELLOW}⚠ No nginx config found for module: $module${NC}"
        echo ""
        echo "This module may need a config added to nginx."
        echo "Standard pattern:"
        echo ""
        cat << 'EOF'
    # Frontend
    location /MODULE_NAME/ {
        alias /opt/revflow-os/modules/MODULE_NAME/frontend/dist/;
        try_files $uri $uri/ /MODULE_NAME/index.html;
    }

    # API
    location /api/MODULE_NAME/ {
        proxy_pass http://localhost:PORT/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
EOF
    fi
}

generate_standard_config() {
    local module=$1
    local backend_port=$2
    local frontend_port=${3:-""}
    
    echo ""
    echo -e "${BLUE}Generating standard nginx config for: $module${NC}"
    echo ""
    
    cat << EOF
# RevFlow OS - $module Module
# Generated: $(date)
# Backend Port: $backend_port
# Frontend Port: ${frontend_port:-N/A}

# API Backend
location /api/$module/ {
    proxy_pass http://localhost:$backend_port/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

# Frontend (React + JSON Render)
location /$module/ {
    alias /opt/revflow-os/modules/$module/frontend/dist/;
    try_files \$uri \$uri/ /$module/index.html;
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --list, -l              List all nginx configs"
    echo "  --routes, -r            Show route map"
    echo "  --duplicates, -d        Find duplicate routes/configs"
    echo "  --test, -t              Test route health"
    echo "  --module NAME, -m       Check config for specific module"
    echo "  --generate MOD PORT     Generate standard config"
    echo "  --help, -h              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --list               # List all configs"
    echo "  $0 --duplicates         # Find duplicates"
    echo "  $0 --module revpublish  # Check revpublish config"
    echo "  $0 --generate revnew 8650  # Generate config"
}

main() {
    case "${1:-}" in
        --list|-l)
            list_configs
            ;;
        --routes|-r)
            extract_routes
            ;;
        --duplicates|-d)
            find_duplicates
            ;;
        --test|-t)
            test_routes
            ;;
        --module|-m)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --module requires a module name"
                exit 1
            fi
            check_module_config "$2"
            ;;
        --generate)
            if [[ -z "${2:-}" || -z "${3:-}" ]]; then
                echo "Error: --generate requires MODULE and PORT"
                echo "Usage: $0 --generate MODULE_NAME PORT"
                exit 1
            fi
            generate_standard_config "$2" "$3" "${4:-}"
            ;;
        --help|-h)
            usage
            ;;
        "")
            # Default: list, routes, and check for duplicates
            list_configs
            extract_routes
            find_duplicates
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
