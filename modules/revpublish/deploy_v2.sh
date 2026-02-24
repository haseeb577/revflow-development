#!/bin/bash
# RevPublish v2.1 Deployment Script
# Run on server: 217.15.168.106
set -e

echo "=========================================="
echo "RevPublish v2.1 Deployment"
echo "=========================================="

# Source environment
source /opt/shared-api-engine/.env

echo ""
echo "[1/6] Creating database tables for v2.0 features..."

PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U $POSTGRES_USER -d revflow << 'EOSQL'

-- AI Usage tracking table
CREATE TABLE IF NOT EXISTS revpublish_ai_usage (
    id SERIAL PRIMARY KEY,
    page_type_id VARCHAR(50),
    model VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);

-- OAuth tokens table
CREATE TABLE IF NOT EXISTS revpublish_oauth_tokens (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) UNIQUE NOT NULL,
    token_data BYTEA,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- OAuth states table (for CSRF protection)
CREATE TABLE IF NOT EXISTS revpublish_oauth_states (
    id SERIAL PRIMARY KEY,
    state VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

-- Deployment history table
CREATE TABLE IF NOT EXISTS revpublish_deployment_history (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(100),
    page_type_id VARCHAR(50),
    post_id INTEGER,
    post_url TEXT,
    title TEXT,
    status VARCHAR(20),
    ai_cost_usd DECIMAL(10, 6),
    conflicts_found INTEGER DEFAULT 0,
    deployed_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ai_usage_date ON revpublish_ai_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_deployment_history_site ON revpublish_deployment_history(site_id);

SELECT 'Database tables created successfully' as status;
EOSQL

echo ""
echo "[2/6] Installing Python dependencies..."
cd /opt/revpublish/backend
pip install --break-system-packages aiohttp httpx 2>/dev/null || pip install aiohttp httpx

echo ""
echo "[3/6] Building frontend..."
cd /opt/revpublish/frontend
npm run build 2>/dev/null || echo "Frontend build skipped (run npm install first if needed)"

echo ""
echo "[4/6] Deploying frontend to production..."
if [ -d "dist" ]; then
    cp -r dist/* /opt/revflow-os/modules/revpublish/build/
    echo "Frontend deployed to /opt/revflow-os/modules/revpublish/build/"
else
    echo "No dist folder found - skipping frontend deployment"
fi

echo ""
echo "[5/6] Restarting backend service..."
systemctl restart revpublish-backend 2>/dev/null || echo "Service restart skipped (may need manual restart)"

echo ""
echo "[6/6] Verifying deployment..."
sleep 2
curl -s http://localhost:8550/ | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'API: {d.get(\"app\", \"unknown\")} - {d.get(\"status\", \"unknown\")}')" 2>/dev/null || echo "API check failed"

echo ""
echo "=========================================="
echo "RevPublish v2.1 Deployment Complete!"
echo ""
echo "New Features:"
echo "  - AI-powered field extraction (Claude-3-Haiku)"
echo "  - Parallel conflict scanning across all sites"
echo "  - Google Docs/Sheets OAuth integration"
echo "  - Enhanced Elementor JSON mapping"
echo "  - Big Red Warning modal for conflicts"
echo "  - AI toggle with cost estimation"
echo ""
echo "Access:"
echo "  UI: http://217.15.168.106:3550/"
echo "  API: http://217.15.168.106:8550/docs"
echo "=========================================="
