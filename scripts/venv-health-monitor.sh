#!/bin/bash
# RevFlow Venv Health Monitor v2
# Checks all service venvs and auto-repairs corrupted ones

LOG_FILE="/var/log/revflow/venv-health.log"

# All known venv locations
VENV_PATHS=(
    "/opt/revflow-os/modules/revimage/backend"
    "/opt/revflow-os/modules/revpublish/backend"
    "/opt/revflow-os/modules/revmetrics/backend"
    "/opt/revflow-os/modules/revvest-iq/backend"
    "/opt/revflow-citations"
    "/opt/revflow-power-prompts"
    "/opt/quick-wins-api"
    "/opt/revflow-enrichment-service"
    "/opt/visitor-identification-service"
    "/opt/guru-intelligence"
    "/opt/revrank_engine"
    "/opt/revscore_iq"
    "/opt/revspy"
    "/opt/revflow-humanization-pipeline"
    "/opt/shared-api-engine"
    "/var/www/revhome_assessment_engine_v2"
)

log() {
    mkdir -p "$(dirname $LOG_FILE)"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_venv() {
    local service_path="$1"
    local service_name=$(basename "$service_path")
    local venv_path="$service_path/venv"
    local req_file="$service_path/requirements.txt"
    
    if [ ! -d "$venv_path" ]; then
        log "SKIP: $service_name - no venv found"
        return 0
    fi
    
    # Test if venv Python interpreter works
    if ! "$venv_path/bin/python" -c "import sys; sys.exit(0)" 2>/dev/null; then
        log "CORRUPTED: $service_name - Python interpreter broken"
        repair_venv "$service_path" "$service_name"
        return 1
    fi
    
    # Test key imports (uvicorn, click are common failure points)
    if ! "$venv_path/bin/python" -c "import click" 2>/dev/null; then
        log "CORRUPTED: $service_name - click module broken"
        repair_venv "$service_path" "$service_name"
        return 1
    fi
    
    log "OK: $service_name venv healthy"
    return 0
}

repair_venv() {
    local service_path="$1"
    local service_name="$2"
    local venv_path="$service_path/venv"
    local req_file="$service_path/requirements.txt"
    
    # Find associated systemd service
    local systemd_service=$(systemctl list-units --type=service --state=running | grep -i "${service_name}" | awk '{print $1}' | head -1)
    
    log "REPAIRING: $service_name venv"
    
    # Stop service if found
    if [ -n "$systemd_service" ]; then
        systemctl stop "$systemd_service" 2>/dev/null
        log "Stopped $systemd_service"
    fi
    
    # Backup corrupted venv
    if [ -d "$venv_path" ]; then
        mv "$venv_path" "${venv_path}.corrupted.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create fresh venv
    python3 -m venv "$venv_path"
    
    # Install requirements
    if [ -f "$req_file" ]; then
        "$venv_path/bin/pip" install -q -r "$req_file" 2>/dev/null
        log "Installed requirements from $req_file"
    fi
    
    # Restart service
    if [ -n "$systemd_service" ]; then
        systemctl start "$systemd_service" 2>/dev/null
        log "Restarted $systemd_service"
    fi
    
    log "REPAIRED: $service_name venv restored"
}

check_disk_space() {
    local usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    if [ "$usage" -gt 85 ]; then
        log "WARNING: Disk usage at ${usage}% - venv corruption risk!"
        rm -rf /root/.cache/pip/* 2>/dev/null
        journalctl --vacuum-time=3d 2>/dev/null
    else
        log "Disk usage: ${usage}%"
    fi
}

main() {
    log "=== Venv Health Check Started ==="
    
    check_disk_space
    
    local total=0
    local healthy=0
    local repaired=0
    local skipped=0
    
    for path in "${VENV_PATHS[@]}"; do
        if [ -d "$path" ]; then
            ((total++))
            if [ -d "$path/venv" ]; then
                if check_venv "$path"; then
                    ((healthy++))
                else
                    ((repaired++))
                fi
            else
                ((skipped++))
                log "SKIP: $(basename $path) - no venv"
            fi
        fi
    done
    
    log "=== Summary: $healthy healthy, $repaired repaired, $skipped skipped of $total checked ==="
}

main "$@"
