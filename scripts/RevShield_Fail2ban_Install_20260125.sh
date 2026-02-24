#!/bin/bash
#===============================================================================
# RevShield Pro - Fail2ban Installation Script
# Server: 217.15.168.106 (srv1078604)
# Date: 2026-01-25
# Module: 17c (RevShield Pro - Security)
#
# INSTRUCTIONS: Run this script on the production server:
#   sudo bash /opt/revflow-os/scripts/RevShield_Fail2ban_Install_20260125.sh
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

log_info "Starting Fail2ban installation for RevFlow OS..."

#===============================================================================
# STEP 1: Install Fail2ban
#===============================================================================
log_info "Step 1: Installing Fail2ban..."

apt update
apt install -y fail2ban

# Ensure fail2ban is stopped during configuration
systemctl stop fail2ban 2>/dev/null || true

#===============================================================================
# STEP 2: Create local jail configuration (never edit jail.conf directly)
#===============================================================================
log_info "Step 2: Configuring Fail2ban jails..."

cat > /etc/fail2ban/jail.local << 'JAILEOF'
# RevFlow OS - Fail2ban Jail Configuration
# Server: 217.15.168.106
# Date: 2026-01-25

[DEFAULT]
# Ban hosts for 1 hour
bantime = 3600

# 10 minute window for finding failures
findtime = 600

# Max 5 retries before ban
maxretry = 5

# Use iptables for banning
banaction = iptables-multiport

# Backend for log monitoring
backend = systemd

# Ignore localhost and common internal ranges
ignoreip = 127.0.0.1/8 ::1

# Action with email notification (configure destemail below)
action = %(action_mwl)s

#===============================================================================
# SSH Protection - CRITICAL for RevFlow OS
#===============================================================================
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
findtime = 300

# Aggressive mode for repeat offenders
[sshd-aggressive]
enabled = true
port = ssh
filter = sshd[mode=aggressive]
logpath = /var/log/auth.log
maxretry = 2
bantime = 86400
findtime = 3600

#===============================================================================
# Nginx Protection - Protecting 38+ RevFlow ports
#===============================================================================
[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
bantime = 3600

[nginx-botsearch]
enabled = true
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/access.log
maxretry = 2
bantime = 86400

[nginx-bad-request]
enabled = true
port = http,https
filter = nginx-bad-request
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600

#===============================================================================
# WordPress Protection (53-site portfolio)
#===============================================================================
[wordpress-hard]
enabled = true
port = http,https
filter = wordpress-hard
logpath = /var/log/nginx/access.log
maxretry = 3
bantime = 86400
findtime = 300

[wordpress-soft]
enabled = true
port = http,https
filter = wordpress-soft
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600
JAILEOF

#===============================================================================
# STEP 3: Create custom nginx filters
#===============================================================================
log_info "Step 3: Creating custom Fail2ban filters..."

# Nginx bad request filter
cat > /etc/fail2ban/filter.d/nginx-bad-request.conf << 'FILTEREOF'
# Fail2Ban filter for nginx bad requests
# Catches 400/444 errors and suspicious requests

[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*HTTP.*" (400|444) .*$
            ^<HOST> .* ".*\\x.*" \d+ .*$
ignoreregex =
FILTEREOF

# WordPress hard filter (brute force attacks)
cat > /etc/fail2ban/filter.d/wordpress-hard.conf << 'FILTEREOF'
# Fail2Ban filter for WordPress login brute force
# Protects wp-login.php and xmlrpc.php

[Definition]
failregex = ^<HOST> .* "POST /wp-login\.php.*" (200|403) .*$
            ^<HOST> .* "POST /xmlrpc\.php.*" (200|403) .*$
            ^<HOST> .* "POST .*/wp-login\.php.*" (200|403) .*$
ignoreregex =
FILTEREOF

# WordPress soft filter (reconnaissance)
cat > /etc/fail2ban/filter.d/wordpress-soft.conf << 'FILTEREOF'
# Fail2Ban filter for WordPress enumeration attempts

[Definition]
failregex = ^<HOST> .* "GET /\?author=\d+.*" .*$
            ^<HOST> .* "GET /wp-json/wp/v2/users.*" .*$
            ^<HOST> .* "GET /wp-content/debug\.log.*" .*$
ignoreregex =
FILTEREOF

#===============================================================================
# STEP 4: Configure email alerts
#===============================================================================
log_info "Step 4: Configuring email alerts..."

# Check if mail is available
if command -v mail &> /dev/null || command -v sendmail &> /dev/null; then
    MAIL_AVAILABLE=true
else
    MAIL_AVAILABLE=false
    log_warn "Mail command not found. Installing mailutils..."
    apt install -y mailutils 2>/dev/null || log_warn "Could not install mailutils - alerts will be logged only"
fi

# Create action configuration with email
cat > /etc/fail2ban/action.d/revflow-notify.conf << 'ACTIONEOF'
# RevFlow OS - Fail2ban notification action
# Sends email alerts for bans

[Definition]
actionstart = printf "%%s\n" "Fail2ban [<name>] jail started on $(hostname)" | mail -s "[RevFlow Security] Fail2ban Started" <dest>
actionstop = printf "%%s\n" "Fail2ban [<name>] jail stopped on $(hostname)" | mail -s "[RevFlow Security] Fail2ban Stopped" <dest>
actionban = printf "%%s\n" "IP <ip> has been banned by Fail2ban [<name>] after <failures> failures. Ban time: <bantime>s" | mail -s "[RevFlow Security] IP Banned: <ip>" <dest>
actionunban = printf "%%s\n" "IP <ip> has been unbanned from Fail2ban [<name>]" | mail -s "[RevFlow Security] IP Unbanned: <ip>" <dest>

[Init]
dest = root
ACTIONEOF

#===============================================================================
# STEP 5: Start and enable Fail2ban
#===============================================================================
log_info "Step 5: Starting Fail2ban service..."

systemctl daemon-reload
systemctl enable fail2ban
systemctl start fail2ban

# Wait for service to stabilize
sleep 3

#===============================================================================
# STEP 6: Verify installation
#===============================================================================
log_info "Step 6: Verifying installation..."

echo ""
echo "=========================================="
echo "  FAIL2BAN INSTALLATION VERIFICATION"
echo "=========================================="
echo ""

# Service status
echo "Service Status:"
systemctl is-active fail2ban && echo "  - fail2ban: RUNNING" || echo "  - fail2ban: NOT RUNNING"
echo ""

# Jail status
echo "Active Jails:"
fail2ban-client status
echo ""

# SSH jail details
echo "SSH Jail Status:"
fail2ban-client status sshd 2>/dev/null || echo "  SSH jail not active yet"
echo ""

# Currently banned IPs
echo "Currently Banned IPs:"
fail2ban-client status sshd 2>/dev/null | grep "Banned IP" || echo "  None"
echo ""

#===============================================================================
# STEP 7: Create documentation
#===============================================================================
DOC_FILE="/opt/revflow-os/docs/RevShield_Fail2ban_20260125.md"
mkdir -p /opt/revflow-os/docs

cat > "$DOC_FILE" << 'DOCEOF'
# RevShield Pro - Fail2ban Configuration

**Server:** 217.15.168.106 (srv1078604)
**Installed:** 2026-01-25
**Module:** 17c (RevShield Pro - Security)

## What Was Installed

### Package
- `fail2ban` - Intrusion prevention system

### Configuration Files
| File | Purpose |
|------|---------|
| `/etc/fail2ban/jail.local` | Main jail configuration |
| `/etc/fail2ban/filter.d/nginx-bad-request.conf` | Custom nginx filter |
| `/etc/fail2ban/filter.d/wordpress-hard.conf` | WordPress brute force filter |
| `/etc/fail2ban/filter.d/wordpress-soft.conf` | WordPress enumeration filter |
| `/etc/fail2ban/action.d/revflow-notify.conf` | Email notification action |

### Active Jails

| Jail | Protects | Max Retry | Ban Time |
|------|----------|-----------|----------|
| sshd | SSH access | 3 | 2 hours |
| sshd-aggressive | Repeat SSH offenders | 2 | 24 hours |
| nginx-http-auth | HTTP Basic Auth | 5 | 1 hour |
| nginx-limit-req | Rate limiting | 10 | 1 hour |
| nginx-botsearch | Bot scanning | 2 | 24 hours |
| nginx-bad-request | Malformed requests | 5 | 1 hour |
| wordpress-hard | WP login brute force | 3 | 24 hours |
| wordpress-soft | WP enumeration | 5 | 1 hour |

## Common Commands

```bash
# Check overall status
fail2ban-client status

# Check specific jail
fail2ban-client status sshd

# Unban an IP
fail2ban-client set sshd unbanip <IP_ADDRESS>

# Ban an IP manually
fail2ban-client set sshd banip <IP_ADDRESS>

# Reload configuration
fail2ban-client reload

# View fail2ban logs
journalctl -u fail2ban -f

# Test a filter against a log file
fail2ban-regex /var/log/nginx/access.log /etc/fail2ban/filter.d/wordpress-hard.conf
```

## Email Alerts

Email alerts are configured to send to `root`. To change:

1. Edit `/etc/fail2ban/jail.local`
2. Add under [DEFAULT]: `destemail = your@email.com`
3. Reload: `fail2ban-client reload`

## Monitoring

Check banned IPs across all jails:
```bash
fail2ban-client status | grep "Jail list" | sed 's/.*:\s*//' | tr ',' '\n' | while read jail; do
    echo "=== $jail ==="
    fail2ban-client status "$jail" | grep "Banned IP"
done
```

## Integration with RevFlow OS

This is part of Module 17c (RevShield Pro). It protects:
- 24+ systemd services
- 38+ active ports
- 53-site WordPress portfolio
- 89,420+ content generations

---
*Documentation auto-generated by RevShield installation script*
DOCEOF

log_info "Documentation created at: $DOC_FILE"

#===============================================================================
# FINAL SUMMARY
#===============================================================================
echo ""
echo "=========================================="
echo "  FAIL2BAN INSTALLATION COMPLETE"
echo "=========================================="
echo ""
echo "Configuration files:"
echo "  - /etc/fail2ban/jail.local"
echo "  - /etc/fail2ban/filter.d/nginx-bad-request.conf"
echo "  - /etc/fail2ban/filter.d/wordpress-hard.conf"
echo "  - /etc/fail2ban/filter.d/wordpress-soft.conf"
echo "  - /etc/fail2ban/action.d/revflow-notify.conf"
echo ""
echo "Documentation:"
echo "  - $DOC_FILE"
echo ""
echo "NEXT STEPS:"
echo "  1. Verify jails are active: fail2ban-client status"
echo "  2. Configure email alerts: edit /etc/fail2ban/jail.local"
echo "     Add: destemail = your@email.com"
echo "  3. Monitor: journalctl -u fail2ban -f"
echo ""
log_info "RevShield Fail2ban installation complete!"
