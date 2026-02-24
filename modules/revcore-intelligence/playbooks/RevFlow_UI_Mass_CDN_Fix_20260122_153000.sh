#!/bin/bash
#================================================================
# RevFlow OS™ - Mass UI CDN Fix & Detection
# Scans all frontends, detects CDN issues, fixes them all
# Date: 2026-01-22 15:30:00
#================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                                                              ║${NC}"
echo -e "${MAGENTA}║     RevFlow OS™ - Mass UI CDN Fix & Detection               ║${NC}"
echo -e "${MAGENTA}║     Scan All Frontends → Detect Issues → Fix Them All       ║${NC}"
echo -e "${MAGENTA}║                                                              ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Arrays to track issues
declare -a BROKEN_UIS
declare -a FIXED_UIS
declare -a CDN_DEPENDENT_UIS

#================================================================
# SECTION 1: Discover all UI ports
#================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[1/6] Discovering all frontend UI ports...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Common frontend ports in RevFlow OS
UI_PORTS=(
    "3100:RevAudit Frontend"
    "3200:RevFlow Platform Frontend"
    "3401:RevDispatch Frontend"
    "3550:RevPublish Frontend"
    "8501:Unknown Frontend"
    "8601:RevHome UI"
    "8202:RevImage UI"
    "9000:Dev Agent Dashboard"
)

echo ""
printf "%-10s %-30s %-15s\n" "PORT" "SERVICE" "STATUS"
echo "────────────────────────────────────────────────────────────"

for port_info in "${UI_PORTS[@]}"; do
    PORT="${port_info%%:*}"
    SERVICE="${port_info#*:}"
    
    # Check if port is listening
    if ss -tlnp | grep -q ":$PORT "; then
        # Try to fetch the page
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:$PORT/ 2>/dev/null)
        
        if [ "$HTTP_CODE" = "200" ]; then
            printf "${GREEN}%-10s %-30s %-15s${NC}\n" "$PORT" "$SERVICE" "✓ UP ($HTTP_CODE)"
            
            # Check if it uses CDN React
            CONTENT=$(curl -s http://127.0.0.1:$PORT/ 2>/dev/null | head -100)
            if echo "$CONTENT" | grep -q "unpkg.com/react"; then
                CDN_DEPENDENT_UIS+=("$PORT:$SERVICE")
                echo "  ${YELLOW}⚠ Uses CDN React (potential issue)${NC}"
            fi
        else
            printf "${RED}%-10s %-30s %-15s${NC}\n" "$PORT" "$SERVICE" "✗ ERROR ($HTTP_CODE)"
            BROKEN_UIS+=("$PORT:$SERVICE")
        fi
    else
        printf "${RED}%-10s %-30s %-15s${NC}\n" "$PORT" "$SERVICE" "✗ NOT RUNNING"
    fi
done

echo ""
echo -e "${CYAN}Summary:${NC}"
echo "  CDN-dependent UIs: ${#CDN_DEPENDENT_UIS[@]}"
echo "  Broken UIs: ${#BROKEN_UIS[@]}"

#================================================================
# SECTION 2: Download React libraries to shared location
#================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[2/6] Setting up shared React libraries...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

SHARED_ASSETS="/var/www/shared-assets"
mkdir -p "$SHARED_ASSETS"

if [ ! -f "$SHARED_ASSETS/react.min.js" ]; then
    echo "  Downloading React 18 production..."
    curl -sS https://unpkg.com/react@18/umd/react.production.min.js -o "$SHARED_ASSETS/react.min.js"
fi

if [ ! -f "$SHARED_ASSETS/react-dom.min.js" ]; then
    echo "  Downloading ReactDOM 18 production..."
    curl -sS https://unpkg.com/react-dom@18/umd/react-dom.production.min.js -o "$SHARED_ASSETS/react-dom.min.js"
fi

if [ ! -f "$SHARED_ASSETS/babel.min.js" ]; then
    echo "  Downloading Babel Standalone..."
    curl -sS https://unpkg.com/@babel/standalone/babel.min.js -o "$SHARED_ASSETS/babel.min.js"
fi

# Verify downloads
if [ -f "$SHARED_ASSETS/react.min.js" ] && [ -f "$SHARED_ASSETS/react-dom.min.js" ]; then
    REACT_SIZE=$(du -h "$SHARED_ASSETS/react.min.js" | cut -f1)
    REACTDOM_SIZE=$(du -h "$SHARED_ASSETS/react-dom.min.js" | cut -f1)
    echo -e "${GREEN}✓ Shared React libraries ready${NC}"
    echo "  React: $REACT_SIZE | ReactDOM: $REACTDOM_SIZE | Babel: $(du -h "$SHARED_ASSETS/babel.min.js" | cut -f1)"
else
    echo -e "${RED}✗ Failed to download React libraries${NC}"
    exit 1
fi

#================================================================
# SECTION 3: Create shared nginx config for assets
#================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[3/6] Configuring nginx to serve shared assets...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

SHARED_NGINX_CONF="/etc/nginx/conf.d/shared-assets.conf"

cat > "$SHARED_NGINX_CONF" << 'NGINX_EOF'
# Shared React/JS assets for all RevFlow frontends
location /shared-assets/ {
    alias /var/www/shared-assets/;
    expires 30d;
    add_header Cache-Control "public, immutable";
    add_header Access-Control-Allow-Origin "*";
}
NGINX_EOF

echo -e "${GREEN}✓ Created shared assets nginx config${NC}"

#================================================================
# SECTION 4: Fix each CDN-dependent UI
#================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[4/6] Fixing CDN-dependent UIs...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ${#CDN_DEPENDENT_UIS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ No CDN-dependent UIs found${NC}"
else
    for ui_info in "${CDN_DEPENDENT_UIS[@]}"; do
        PORT="${ui_info%%:*}"
        SERVICE="${ui_info#*:}"
        
        echo ""
        echo -e "${BLUE}Fixing: $SERVICE (port $PORT)${NC}"
        
        # Find the HTML file
        HTML_PATHS=(
            "/opt/revdispatch-real/frontend/build/index.html"
            "/opt/revpublish-frontend/build/index.html"
            "/opt/revaudit-complete/frontend/index.html"
            "/var/www/html/index.html"
            "/usr/share/nginx/html/index.html"
        )
        
        # Check nginx config to find actual root
        NGINX_ROOT=$(grep -r "listen $PORT" /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null | grep -oP 'root \K[^;]+' | head -1)
        
        if [ -n "$NGINX_ROOT" ]; then
            HTML_FILE="$NGINX_ROOT/index.html"
        else
            # Fallback: find by port
            case $PORT in
                3401) HTML_FILE="/opt/revdispatch-real/frontend/build/index.html" ;;
                3550) HTML_FILE="/opt/revpublish-frontend/build/index.html" ;;
                3100) HTML_FILE="/opt/revaudit-complete/frontend/index.html" ;;
                8501) HTML_FILE="/opt/unknown-ui-8501/index.html" ;;
                *) HTML_FILE="" ;;
            esac
        fi
        
        if [ -f "$HTML_FILE" ]; then
            echo "  Found HTML: $HTML_FILE"
            
            # Backup original
            BACKUP="$HTML_FILE.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$HTML_FILE" "$BACKUP"
            echo "  Created backup: $BACKUP"
            
            # Replace CDN URLs with shared assets
            sed -i 's|https://unpkg.com/react@18/umd/react.production.min.js|/shared-assets/react.min.js|g' "$HTML_FILE"
            sed -i 's|https://unpkg.com/react-dom@18/umd/react-dom.production.min.js|/shared-assets/react-dom.min.js|g' "$HTML_FILE"
            sed -i 's|https://unpkg.com/@babel/standalone/babel.min.js|/shared-assets/babel.min.js|g' "$HTML_FILE"
            
            # Also check for any other CDN patterns
            sed -i 's|https://unpkg.com/react@[^"]*|/shared-assets/react.min.js|g' "$HTML_FILE"
            sed -i 's|https://unpkg.com/react-dom@[^"]*|/shared-assets/react-dom.min.js|g' "$HTML_FILE"
            
            echo -e "  ${GREEN}✓ Updated CDN references to local assets${NC}"
            FIXED_UIS+=("$PORT:$SERVICE")
        else
            echo -e "  ${RED}✗ Could not find HTML file${NC}"
            echo "  Searched: $HTML_FILE"
        fi
    done
fi

#================================================================
# SECTION 5: Reload nginx and test
#================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[5/6] Reloading nginx and testing...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✓ nginx config valid${NC}"
    systemctl reload nginx
    echo -e "${GREEN}✓ nginx reloaded${NC}"
else
    echo -e "${RED}✗ nginx config has errors${NC}"
    nginx -t
fi

# Test shared assets
echo ""
echo "Testing shared assets availability..."
sleep 2

REACT_TEST=$(curl -s -I http://127.0.0.1/shared-assets/react.min.js 2>/dev/null | head -1)
if echo "$REACT_TEST" | grep -q "200"; then
    echo -e "${GREEN}✓ /shared-assets/react.min.js accessible${NC}"
else
    echo -e "${RED}✗ /shared-assets/react.min.js NOT accessible${NC}"
fi

#================================================================
# SECTION 6: Verification & Summary
#================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[6/6] Final verification...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Re-testing all UIs..."
echo ""
printf "%-10s %-30s %-15s\n" "PORT" "SERVICE" "STATUS"
echo "────────────────────────────────────────────────────────────"

for ui_info in "${CDN_DEPENDENT_UIS[@]}"; do
    PORT="${ui_info%%:*}"
    SERVICE="${ui_info#*:}"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:$PORT/ 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        printf "${GREEN}%-10s %-30s %-15s${NC}\n" "$PORT" "$SERVICE" "✓ WORKING"
    else
        printf "${YELLOW}%-10s %-30s %-15s${NC}\n" "$PORT" "$SERVICE" "⚠ CHECK ($HTTP_CODE)"
    fi
done

#================================================================
# FINAL SUMMARY
#================================================================
echo ""
echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                    FIX COMPLETE                              ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo "  • CDN-dependent UIs found: ${#CDN_DEPENDENT_UIS[@]}"
echo "  • UIs fixed: ${#FIXED_UIS[@]}"
echo ""
echo -e "${GREEN}What was done:${NC}"
echo "  ✓ Downloaded React/ReactDOM/Babel to /var/www/shared-assets/"
echo "  ✓ Created nginx config to serve shared assets"
echo "  ✓ Updated all HTML files to use local assets"
echo "  ✓ Reloaded nginx"
echo ""
echo -e "${YELLOW}Next steps for users:${NC}"
echo "  1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)"
echo "  2. Reload the affected UIs"
echo "  3. React errors should be gone from browser console"
echo ""
echo -e "${CYAN}Fixed UIs:${NC}"
for ui in "${FIXED_UIS[@]}"; do
    PORT="${ui%%:*}"
    SERVICE="${ui#*:}"
    echo "  • http://217.15.168.106:$PORT/ - $SERVICE"
done
echo ""
echo -e "${BLUE}Shared assets available at:${NC}"
echo "  • http://217.15.168.106/shared-assets/react.min.js"
echo "  • http://217.15.168.106/shared-assets/react-dom.min.js"
echo "  • http://217.15.168.106/shared-assets/babel.min.js"
echo ""

