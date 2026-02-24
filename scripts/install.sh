#!/bin/bash
set -e
echo "🚀 RevFlow OS Installation"
if [ ! -f /opt/shared-api-engine/.env ]; then
    echo "❌ Shared .env not found"
    exit 1
fi
export $(cat /opt/shared-api-engine/.env | xargs)
command -v python3 >/dev/null || { echo "❌ Python3 required"; exit 1; }
command -v docker >/dev/null || { echo "❌ Docker required"; exit 1; }
command -v psql >/dev/null || { echo "❌ PostgreSQL required"; exit 1; }
echo "✓ Prerequisites installed"
createdb ${DB_NAME} 2>/dev/null || echo "Database already exists"
echo "✅ Installation complete"
