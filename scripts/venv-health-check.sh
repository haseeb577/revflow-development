#!/bin/bash
# RevFlow OS - Virtual Environment Health Check & Auto-Healing
# Runs every 15 minutes via cron to detect and fix venv corruption
# Part of Consul Auto-Healing System

LOG_FILE="/var/log/revflow/venv-health.log"
CRITICAL_PACKAGES="click idna httpx flask flask_cors pydantic fastapi uvicorn"

# Common venvs to monitor
VENVS=(
    "/opt/revflow-os/venv"
    "/opt/revcore/api/venv"
    "/opt/revcite/venv"
    "/opt/revflow_enrichment_service/venv"
    "/opt/quick-wins-api/venv"
    "/opt/revcore-intelligence/venv"
)

# Ensure log directory exists
mkdir -p /var/log/revflow

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== Starting venv health check ==="

fix_package() {
    local venv=$1
    local package=$2
    local site_packages="$venv/lib/python3.12/site-packages"

    log "Fixing $package in $venv"

    # Remove corrupted package
    rm -rf "$site_packages/${package}"* 2>/dev/null
    rm -rf "$site_packages/${package//_/-}"* 2>/dev/null

    # Reinstall
    pip install --target="$site_packages" "$package" --quiet 2>/dev/null

    if [ $? -eq 0 ]; then
        log "  - Fixed $package successfully"
        return 0
    else
        log "  - Failed to fix $package"
        return 1
    fi
}

check_venv() {
    local venv=$1
    local python_bin="$venv/bin/python"

    if [ ! -f "$python_bin" ]; then
        log "SKIP: $venv - python binary not found"
        return 0
    fi

    log "Checking $venv"

    for package in $CRITICAL_PACKAGES; do
        # Test import
        result=$("$python_bin" -c "import $package" 2>&1)
        exit_code=$?

        if [ $exit_code -ne 0 ]; then
            if echo "$result" | grep -q "No module named"; then
                # Package missing or corrupted
                log "  - CORRUPTED: $package"
                fix_package "$venv" "$package"
            fi
        fi
    done
}

# Check pip is working first
pip --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    log "CRITICAL: System pip is broken. Running get-pip.py"
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py --force-reinstall --break-system-packages --ignore-installed 2>/dev/null
fi

# Check each venv
for venv in "${VENVS[@]}"; do
    check_venv "$venv"
done

# Also check any other venvs that have services
for venv_path in $(find /opt -maxdepth 3 -type d -name "venv" 2>/dev/null | grep -v __pycache__); do
    if [[ ! " ${VENVS[*]} " =~ " ${venv_path} " ]]; then
        check_venv "$venv_path"
    fi
done

log "=== Health check complete ==="

# Restart any failed services
failed=$(systemctl list-units --type=service --state=failed 2>/dev/null | grep -E "rev|power" | awk '{print $2}')
if [ -n "$failed" ]; then
    log "Restarting failed services: $failed"
    systemctl reset-failed
    for svc in $failed; do
        systemctl restart "$svc" 2>/dev/null
        log "  - Restarted $svc"
    done
fi
