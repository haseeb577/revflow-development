#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# RevFlow OS - Master Virtual Environment Rebuild Script
# Creates a consolidated, healthy venv with ALL required packages
# Run this when venvs are corrupted beyond quick fixes
# ═══════════════════════════════════════════════════════════════════════════════

set -e

MASTER_VENV="/opt/revflow-os/master-venv"
REQUIREMENTS_FILE="/opt/revflow-os/master-requirements.txt"
LOG_FILE="/var/log/revflow/venv-rebuild.log"
BACKUP_DIR="/opt/revflow-os/venv-backups"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

mkdir -p /var/log/revflow
mkdir -p "$BACKUP_DIR"

log "═══════════════════════════════════════════════════════════════"
log "Starting Master Venv Rebuild"
log "═══════════════════════════════════════════════════════════════"

# Step 1: Create master requirements file with ALL dependencies
log "Creating master requirements file..."
cat > "$REQUIREMENTS_FILE" << 'EOF'
# Core Web Frameworks
fastapi>=0.100.0
flask>=3.0.0
flask-cors>=4.0.0
uvicorn>=0.30.0
starlette>=0.30.0

# HTTP Clients
httpx>=0.27.0
requests>=2.31.0
aiohttp>=3.9.0

# Database
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.0

# Data Processing
pandas>=2.0.0
numpy>=1.26.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Authentication
python-jose>=3.3.0
passlib>=1.7.4
bcrypt>=4.0.0

# Document Generation
reportlab>=4.0.0
Jinja2>=3.1.0
beautifulsoup4>=4.12.0
lxml>=5.0.0

# Utilities
python-dotenv>=1.0.0
python-multipart>=0.0.6
click>=8.1.0
idna>=3.6

# AI Libraries
anthropic>=0.20.0
openai>=1.0.0

# Async
aiofiles>=23.0.0

# Validation
email-validator>=2.0.0
EOF

# Step 2: Backup existing venv if it exists
if [ -d "$MASTER_VENV" ]; then
    backup_name="master-venv-backup-$(date +%Y%m%d_%H%M%S)"
    log "Backing up existing master venv to $BACKUP_DIR/$backup_name"
    mv "$MASTER_VENV" "$BACKUP_DIR/$backup_name"
fi

# Step 3: Create fresh master venv
log "Creating fresh master venv at $MASTER_VENV"
python3 -m venv "$MASTER_VENV"

# Step 4: Upgrade pip in the new venv
log "Upgrading pip..."
"$MASTER_VENV/bin/pip" install --upgrade pip wheel setuptools

# Step 5: Install all requirements
log "Installing all requirements..."
"$MASTER_VENV/bin/pip" install -r "$REQUIREMENTS_FILE" 2>&1 | tail -20

# Step 6: Verify installation
log "Verifying installation..."
"$MASTER_VENV/bin/python" -c "
import click, idna, httpx, flask, fastapi, uvicorn, requests
import pydantic, sqlalchemy, pandas, numpy, Jinja2
print('All core packages verified successfully')
"

# Step 7: Create symlinks for services to use master venv
log "Master venv created successfully at $MASTER_VENV"
log ""
log "To use this venv, update service files to use:"
log "  ExecStart=$MASTER_VENV/bin/python -m uvicorn ..."
log ""
log "Or create symlink in individual module directories:"
log "  ln -sf $MASTER_VENV /opt/MODULE/venv"

log "═══════════════════════════════════════════════════════════════"
log "Master Venv Rebuild Complete"
log "═══════════════════════════════════════════════════════════════"
