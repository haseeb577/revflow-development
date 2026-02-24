#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# RevFlow OS - Venv Guardian (Aggressive Auto-Healing)
# Runs every 5 minutes via cron - detects and fixes ANY venv corruption
# ═══════════════════════════════════════════════════════════════════════════════

LOG_FILE="/var/log/revflow/venv-guardian.log"
ALERT_FILE="/var/log/revflow/venv-alerts.log"
MAX_LOG_SIZE=10485760  # 10MB

# All packages that commonly get corrupted
CRITICAL_PACKAGES=(
    "click"
    "idna"
    "httpx"
    "flask"
    "flask_cors"
    "pydantic"
    "fastapi"
    "uvicorn"
    "requests"
    "starlette"
    "passlib"
    "bcrypt"
    "jose"
    "multipart"
    "dotenv"
    "sqlalchemy"
    "psycopg2"
    "aiohttp"
    "anthropic"
    "reportlab"
)

# Service-to-venv mapping
declare -A SERVICE_VENVS=(
    ["revcore-api"]="/opt/revcore/api/venv"
    ["revcore-intelligence"]="/opt/revcore-intelligence/venv"
    ["revcite"]="/opt/revcite/venv"
    ["revflow-power-prompts"]="/opt/revflow-os/venv"
    ["revflow-revwins"]="/opt/quick-wins-api/venv"
    ["revpublish-backend"]="/opt/revflow-os/venv"
    ["revintel"]="/opt/revflow_enrichment_service/venv"
    ["revassist"]="/opt/revflow-os/venv"
    ["revspy"]="/opt/revflow-os/venv"
    ["revrank-engine"]="/opt/revrank_engine/backend/venv"
    ["guru-intelligence"]="/opt/guru-intelligence/venv"
    ["revhumanize"]="/opt/revflow-humanization-pipeline/venv"
    ["revmetrics-api"]="/opt/revflow-os/venv"
    ["revflow-dispatcher"]="/opt/revflow-lead-engine/venv"
)

mkdir -p /var/log/revflow

# Rotate log if too large
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]; then
    mv "$LOG_FILE" "$LOG_FILE.old"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

alert() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERT: $1" >> "$ALERT_FILE"
    log "ALERT: $1"
}

fix_package() {
    local venv=$1
    local package=$2
    local site_packages="$venv/lib/python3.12/site-packages"

    # Remove corrupted package files
    rm -rf "$site_packages/${package}"* 2>/dev/null
    rm -rf "$site_packages/${package//_/-}"* 2>/dev/null

    # Reinstall using system pip to target location
    pip install --target="$site_packages" "$package" --quiet --no-warn-script-location 2>/dev/null

    return $?
}

check_and_fix_venv() {
    local venv=$1
    local python_bin="$venv/bin/python"
    local fixed=0

    if [ ! -f "$python_bin" ]; then
        return 0
    fi

    for package in "${CRITICAL_PACKAGES[@]}"; do
        # Quick import test
        result=$("$python_bin" -c "import $package" 2>&1)
        if [ $? -ne 0 ]; then
            if echo "$result" | grep -qE "No module named|cannot import|ModuleNotFoundError"; then
                log "CORRUPTED in $venv: $package - fixing..."
                if fix_package "$venv" "$package"; then
                    log "FIXED: $package in $venv"
                    fixed=1
                else
                    alert "FAILED to fix $package in $venv"
                fi
            fi
        fi
    done

    return $fixed
}

restart_failed_services() {
    local restarted=0

    # Get failed services
    failed=$(systemctl list-units --type=service --state=failed 2>/dev/null | grep -E "rev|power|guru" | awk '{print $2}')

    if [ -n "$failed" ]; then
        log "Found failed services: $failed"
        systemctl reset-failed

        for svc in $failed; do
            svc_name="${svc%.service}"
            venv="${SERVICE_VENVS[$svc_name]}"

            if [ -n "$venv" ]; then
                log "Checking venv for $svc_name: $venv"
                check_and_fix_venv "$venv"
            fi

            systemctl restart "$svc" 2>/dev/null
            sleep 2

            if systemctl is-active --quiet "$svc"; then
                log "Restarted $svc successfully"
                restarted=1
            else
                alert "Failed to restart $svc after venv fix"
            fi
        done
    fi

    return $restarted
}

# Main execution
log "=== Venv Guardian Starting ==="

# 1. Check system pip is working
if ! pip --version > /dev/null 2>&1; then
    log "System pip broken - reinstalling..."
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py --force-reinstall --break-system-packages --ignore-installed 2>/dev/null
fi

# 2. Check all known venvs
for svc in "${!SERVICE_VENVS[@]}"; do
    venv="${SERVICE_VENVS[$svc]}"
    if [ -d "$venv" ]; then
        check_and_fix_venv "$venv"
    fi
done

# 3. Find and check any other venvs
for venv_path in $(find /opt -maxdepth 4 -type d -name "venv" 2>/dev/null | grep -v __pycache__ | grep -v ".corrupted"); do
    check_and_fix_venv "$venv_path"
done

# 4. Restart any failed services
restart_failed_services

log "=== Venv Guardian Complete ==="
