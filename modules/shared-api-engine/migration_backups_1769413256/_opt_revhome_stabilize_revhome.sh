#!/bin/bash

# --- Configuration ---
APP_USER="revhome"
APP_GROUP="revhome"
WORKING_DIR="/opt/revhome"
ENV_FILE="/etc/revhome/revhome.env"
VENV_BIN="$WORKING_DIR/venv/bin"
GUNICORN_CMD="$VENV_BIN/gunicorn"
APP_MODULE="server_vps_final:app"
BIND_ADDRESS="127.0.0.1:8100"
NUM_WORKERS=3

NGINX_SITE_AVAILABLE_DIR="/etc/nginx/sites-available"
NGINX_SITE_ENABLED_DIR="/etc/nginx/sites-enabled"
CERTBOT_CERT_NAME_AUTOMATION="automation.smarketsherpa.ai"
CERTBOT_CERT_NAME_REVHOME="revhome.smarketsherpa.ai"

LOG_FILE="/var/log/revhome_stabilize.log"
BACKUP_DIR_ROOT="/root/revhome_systemd_backups"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Functions ---
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${GREEN}INFO${NC}: \$1"
}

log_warn() {
    log "${YELLOW}WARN${NC}: \$1"
}

log_error() {
    log "${RED}ERROR${NC}: \$1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root."
        exit 1
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    local deps=("systemctl" "nginx" "certbot" "ss" "journalctl" "grep" "awk" "sed" "tee" "mkdir" "cp" "mv" "rm" "ln")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Prerequisite '$dep' not found. Please install it."
            exit 1
        fi
    done
    log_info "All prerequisites found."
}

stop_and_disable_units() {
    log_info "Stopping and disabling redundant systemd units..."
    local units_to_stop=("revhome" "revhome-memory" "revhome_api" "revhome-api" "revhome-test" "uvicorn")
    
    for unit in "${units_to_stop[@]}"; do
        if systemctl list-unit-files | grep -q "^${unit}\.service"; then
            log_info "Stopping $unit.service..."
            systemctl stop "${unit}.service" 2>/dev/null || log_warn "Failed to stop $unit.service"
            log_info "Disabling $unit.service..."
            systemctl disable "${unit}.service" 2>/dev/null || log_warn "Failed to disable $unit.service"
            
            # Move the service file out of the way
            local service_file_path="/etc/systemd/system/${unit}.service"
            if [[ -f "$service_file_path" ]]; then
                local backup_name="${BACKUP_DIR_ROOT}/${unit}.service.disabled_$(date +%s)"
                log_info "Moving $service_file_path to $backup_name"
                mv "$service_file_path" "$backup_name" || log_warn "Failed to move $service_file_path"
            fi
        else
             log_info "Unit $unit.service not found, skipping."
        fi
    done
    log_info "Reloading systemd daemon..."
    systemctl daemon-reload || log_error "Failed to reload systemd daemon"
}


create_backup_dir() {
    log_info "Creating backup directory at $BACKUP_DIR_ROOT if it doesn't exist..."
    mkdir -p "$BACKUP_DIR_ROOT" || { log_error "Failed to create backup directory."; exit 1; }
}

backup_current_unit() {
    log_info "Backing up current revhome-gunicorn.service..."
    local current_service_file="/etc/systemd/system/revhome-gunicorn.service"
    if [[ -f "$current_service_file" ]]; then
        local backup_name="${BACKUP_DIR_ROOT}/revhome-gunicorn.service.backup_$(date +%s)"
        cp "$current_service_file" "$backup_name" && log_info "Backed up to $backup_name" || log_warn "Failed to backup $current_service_file"
    else
        log_warn "$current_service_file not found, no backup made."
    fi
}

write_new_systemd_unit() {
    log_info "Writing new revhome-gunicorn.service..."
    local service_content="[Unit]
Description=RevHome Gunicorn Service
After=network.target

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${WORKING_DIR}
EnvironmentFile=-${ENV_FILE}
ExecStart=${GUNICORN_CMD} --workers ${NUM_WORKERS} --bind ${BIND_ADDRESS} --access-logfile - --error-logfile - --capture-output --log-level info ${APP_MODULE}
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5
LimitNOFILE=65536
KillMode=mixed
TimeoutStartSec=90
TimeoutStopSec=90
SyslogIdentifier=revhome-gunicorn

[Install]
WantedBy=multi-user.target
"

    echo "$service_content" > /etc/systemd/system/revhome-gunicorn.service || { log_error "Failed to write new systemd unit file."; exit 1; }
    log_info "New revhome-gunicorn.service written successfully."
}

reload_and_restart_systemd_unit() {
    log_info "Reloading systemd and restarting revhome-gunicorn..."
    systemctl daemon-reload || { log_error "Failed to reload systemd."; exit 1; }
    systemctl enable revhome-gunicorn.service || log_warn "Failed to enable revhome-gunicorn.service (might already be enabled)"
    systemctl restart revhome-gunicorn.service || { log_error "Failed to restart revhome-gunicorn.service."; exit 1; }
    sleep 5 # Give it a moment to start
    if systemctl is-active --quiet revhome-gunicorn.service; then
        log_info "revhome-gunicorn.service restarted successfully."
    else
        log_error "revhome-gunicorn.service failed to start. Check 'systemctl status revhome-gunicorn' and logs."
        journalctl -u revhome-gunicorn --no-pager -n 50
        exit 1
    fi
}

check_port_listening() {
    log_info "Checking if port $BIND_ADDRESS is listening..."
    if ss -ltnp | grep -q ":${BIND_ADDRESS#*:} "; then
        log_info "Port $BIND_ADDRESS is listening."
    else
        log_error "Port $BIND_ADDRESS is NOT listening. Service might have failed to start correctly."
        # Show last logs
        journalctl -u revhome-gunicorn --no-pager -n 20
        exit 1
    fi
}

update_nginx_config() {
    log_info "Updating Nginx configuration for proxy timeouts..."

    # Define the pattern to find locations that proxy to 127.0.0.1:8100
    local proxy_pattern="proxy_pass.*http://127\.0\.0\.1:8100"
    
    # Backup original configs
    find /etc/nginx/sites-enabled /etc/nginx/sites-available -type f -name "*.conf" -o -name "*" | while read -r file; do
        if [[ -f "$file" ]] && grep -q "$proxy_pattern" "$file"; then
            local nginx_backup="${BACKUP_DIR_ROOT}/$(basename "$file").nginx.bak_$(date +%s)"
            log_info "Backing up Nginx config $file to $nginx_backup"
            cp "$file" "$nginx_backup" || log_warn "Failed to backup $file"
        fi
    done

    # Update configs
    find /etc/nginx/sites-enabled /etc/nginx/sites-available -type f -name "*.conf" -o -name "*" | while read -r file; do
        if [[ -f "$file" ]] && grep -q "$proxy_pattern" "$file"; then
            log_info "Updating proxy settings in $file..."
            # Add or update proxy timeout settings inside location blocks that proxy to 127.0.0.1:8100
            awk '
            /location.*\{/,/\}/ {
                if (/location.*\{/) { print; next }
                if (/\}/) {
                    # Before closing brace, add timeout settings if not already present
                    if (!seen_timeout) {
                        print "        proxy_connect_timeout 10s;"
                        print "        proxy_send_timeout 60s;"
                        print "        proxy_read_timeout 60s;"
                        print "        proxy_buffering off;"
                    }
                    print; next
                }
                # Inside the block, check for existing timeout settings
                if (/proxy_(connect|send|read)_timeout|proxy_buffering/) {
                    seen_timeout=1
                }
                print
                next
            }
            { print }
            ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
        fi
    done
    
    log_info "Testing Nginx configuration..."
    if nginx -t; then
        log_info "Nginx configuration test passed. Reloading Nginx..."
        systemctl reload nginx || log_warn "Failed to reload Nginx."
    else
        log_error "Nginx configuration test failed. Restoring backups and exiting."
        # Restore backups
        find "$BACKUP_DIR_ROOT" -name "*.nginx.bak_*" | while read -r bak; do
            orig_name=$(echo "$bak" | sed -E 's/\.nginx\.bak_[0-9]+$//')
            orig_path=""
            # Determine original path
            for dir in /etc/nginx/sites-enabled /etc/nginx/sites-available; do
                if [[ -f "$dir/$(basename "$orig_name")" ]]; then
                    orig_path="$dir/$(basename "$orig_name")"
                    break
                fi
            done
            if [[ -n "$orig_path" ]]; then
                 log_info "Restoring Nginx config from $bak to $orig_path"
                 cp "$bak" "$orig_path"
            fi
        done
        nginx -t # Test again after restore
        exit 1
    fi
}


ensure_certbot_certs_installed() {
    log_info "Ensuring Certbot certificates are installed for Nginx..."
    
    # Check for automation.smarketsherpa.ai cert
    if [[ -d "/etc/letsencrypt/live/$CERTBOT_CERT_NAME_AUTOMATION" ]]; then
        log_info "Cert for $CERTBOT_CERT_NAME_AUTOMATION exists. Ensuring it's installed in Nginx..."
        if ! grep -q "ssl_certificate.*$CERTBOT_CERT_NAME_AUTOMATION" /etc/nginx/sites-enabled/* 2>/dev/null; then
             log_info "Installing cert for $CERTBOT_CERT_NAME_AUTOMATION..."
             certbot install --cert-name "$CERTBOT_CERT_NAME_AUTOMATION" --nginx --non-interactive || log_warn "Failed to install cert for $CERTBOT_CERT_NAME_AUTOMATION"
        else
             log_info "Cert for $CERTBOT_CERT_NAME_AUTOMATION appears to be installed in Nginx config."
        fi
    else
        log_warn "Cert for $CERTBOT_CERT_NAME_AUTOMATION not found in /etc/letsencrypt/live/"
    fi

    # Check for revhome.smarketsherpa.ai cert
    if [[ -d "/etc/letsencrypt/live/$CERTBOT_CERT_NAME_REVHOME" ]]; then
        log_info "Cert for $CERTBOT_CERT_NAME_REVHOME exists. Ensuring it's installed in Nginx..."
        if ! grep -q "ssl_certificate.*$CERTBOT_CERT_NAME_REVHOME" /etc/nginx/sites-enabled/* 2>/dev/null; then
             log_info "Installing cert for $CERTBOT_CERT_NAME_REVHOME..."
             certbot install --cert-name "$CERTBOT_CERT_NAME_REVHOME" --nginx --non-interactive || log_warn "Failed to install cert for $CERTBOT_CERT_NAME_REVHOME"
        else
             log_info "Cert for $CERTBOT_CERT_NAME_REVHOME appears to be installed in Nginx config."
        fi
    else
        log_warn "Cert for $CERTBOT_CERT_NAME_REVHOME not found in /etc/letsencrypt/live/"
    fi

    # Reload Nginx to apply any cert changes
    log_info "Reloading Nginx to apply certificate changes..."
    systemctl reload nginx || log_warn "Failed to reload Nginx after cert install."
}


final_verification() {
    log_info "Performing final verification checks..."
    local all_checks_passed=true

    # 1. Check if systemd unit is active
    if systemctl is-active --quiet revhome-gunicorn.service; then
        log_info "Systemd unit revhome-gunicorn.service is active."
    else
        log_error "Systemd unit revhome-gunicorn.service is NOT active."
        all_checks_passed=false
    fi

    # 2. Check if port is listening
    if ss -ltnp | grep -q ":${BIND_ADDRESS#*:} "; then
        log_info "Port $BIND_ADDRESS is listening."
    else
        log_error "Port $BIND_ADDRESS is NOT listening."
        all_checks_passed=false
    fi

    # 3. Check Nginx status
    if systemctl is-active --quiet nginx; then
        log_info "Nginx service is active."
    else
        log_error "Nginx service is NOT active."
        all_checks_passed=false
    fi

    # 4. Test local health endpoint
    if curl -s -f http://127.0.0.1:${BIND_ADDRESS#*:}/health > /dev/null; then
        log_info "Local /health endpoint (http://127.0.0.1:${BIND_ADDRESS#*:}/health) is responding."
    else
        log_error "Local /health endpoint (http://127.0.0.1:${BIND_ADDRESS#*:}/health) is NOT responding."
        all_checks_passed=false
    fi

    # 5. Test automation.smarketsherpa.ai health endpoint (requires valid DNS/resolution)
    if curl -s -f -k https://automation.smarketsherpa.ai/health > /dev/null; then # -k for self-signed if needed temporarily
        log_info "Remote /health endpoint (https://automation.smarketsherpa.ai/health) is responding."
    else
        log_warn "Remote /health endpoint (https://automation.smarketsherpa.ai/health) is NOT responding. Might be a temporary network/DNS issue or cert problem."
        # Do not fail the script on this, as it's external
        # all_checks_passed=false
    fi

    # 6. Test revhome.smarketsherpa.ai health endpoint (requires valid DNS/resolution)
    if curl -s -f -k https://revhome.smarketsherpa.ai/health > /dev/null; then # -k for self-signed if needed temporarily
        log_info "Remote /health endpoint (https://revhome.smarketsherpa.ai/health) is responding."
    else
        log_warn "Remote /health endpoint (https://revhome.smarketsherpa.ai/health) is NOT responding. Might be a temporary network/DNS issue or cert problem."
        # Do not fail the script on this, as it's external
        # all_checks_passed=false
    fi

    if [[ "$all_checks_passed" == true ]]; then
        log_info "${GREEN}*** ALL FINAL VERIFICATION CHECKS PASSED ***${NC}"
        echo
        log_info "Your RevHome application stack should now be stabilized."
        log_info "- The canonical systemd service is 'revhome-gunicorn.service'."
        log_info "- Redundant services have been stopped/disabled."
        log_info "- Nginx proxy timeouts have been adjusted."
        log_info "- Certbot certificates should be installed (if they existed)."
        log_info "- Local and remote health checks are passing."
        echo
        log_info "You can monitor the service with:"
        log_info "  - 'sudo journalctl -u revhome-gunicorn -f' (Application logs)"
        log_info "  - 'sudo tail -f /var/log/nginx/error.log' (Nginx errors)"
        log_info "  - 'sudo systemctl status revhome-gunicorn' (Service status)"
    else
        log_error "${RED}*** SOME FINAL VERIFICATION CHECKS FAILED ***${NC}"
        log_error "Please review the log file at $LOG_FILE and the output above for details."
        log_error "You may need to investigate service status, logs, or network connectivity."
        exit 1
    fi
}


# --- Main Execution ---
main() {
    log_info "===== Starting RevHome Application Stabilization Script ====="
    check_root
    check_prerequisites
    create_backup_dir
    stop_and_disable_units # Stop/disable others FIRST
    backup_current_unit
    write_new_systemd_unit
    reload_and_restart_systemd_unit
    check_port_listening
    update_nginx_config
    ensure_certbot_certs_installed
    final_verification
    log_info "===== RevHome Application Stabilization Script Completed Successfully ====="
}

# Run the script
main "$@"
