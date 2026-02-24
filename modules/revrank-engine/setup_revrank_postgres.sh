#!/bin/bash
# PostgreSQL Setup for RevRank Portfolio - 53 Published Sites
# Run this on your server: bash setup_revrank_postgres.sh

set -e  # Exit on any error

echo "================================================================================"
echo "REVRANK PORTFOLIO - POSTGRESQL SETUP"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Create PostgreSQL database 'revrank_portfolio'"
echo "  2. Import 53 published sites from Excel"
echo "  3. Calculate tier assignments and scores"
echo "  4. Deploy new API backend"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# ============================================================================
# STEP 1: Create PostgreSQL Database
# ============================================================================
echo ""
echo "STEP 1: Creating PostgreSQL database..."
echo "────────────────────────────────────────"

# Generate random password
DB_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)

sudo -u postgres psql << EOF
-- Create database
DROP DATABASE IF EXISTS revrank_portfolio;
CREATE DATABASE revrank_portfolio;

-- Create user
DROP USER IF EXISTS revrank;
CREATE USER revrank WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE revrank_portfolio TO revrank;
\c revrank_portfolio
GRANT ALL ON SCHEMA public TO revrank;

-- Verify
SELECT current_database();
EOF

echo "✅ Database created"
echo "   Database: revrank_portfolio"
echo "   User: revrank"
echo "   Password: $DB_PASSWORD"
echo ""
echo "   ⚠️  SAVE THIS PASSWORD! Writing to /opt/revrank_engine/.env"

# Save credentials
cat > /opt/revrank_engine/.env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=revrank_portfolio
DB_USER=revrank
DB_PASSWORD=$DB_PASSWORD
EOF

chmod 600 /opt/revrank_engine/.env

# ============================================================================
# STEP 2: Install Python Dependencies
# ============================================================================
echo ""
echo "STEP 2: Installing Python dependencies..."
echo "────────────────────────────────────────"

cd /opt/revrank_engine/backend
source venv/bin/activate
pip install -q pandas openpyxl psycopg2-binary python-dotenv

echo "✅ Dependencies installed"

# ============================================================================
# STEP 3: Run Import Script
# ============================================================================
echo ""
echo "STEP 3: Importing 53 published sites..."
echo "────────────────────────────────────────"

python3 /opt/revrank_engine/import_excel_to_postgres.py

echo "✅ Import complete"

# ============================================================================
# STEP 4: Deploy New API
# ============================================================================
echo ""
echo "STEP 4: Deploying PostgreSQL-backed API..."
echo "────────────────────────────────────────"

# Stop old API
OLD_PID=$(sudo lsof -t -i:8001 2>/dev/null || echo "")
if [ ! -z "$OLD_PID" ]; then
    echo "   Stopping old API (PID: $OLD_PID)..."
    sudo kill $OLD_PID
    sleep 2
fi

# Backup old API
if [ -f /opt/revrank_engine/backend/main_enhanced.py ]; then
    cp /opt/revrank_engine/backend/main_enhanced.py \
       /opt/revrank_engine/backend/main_enhanced.py.backup_$(date +%Y%m%d_%H%M%S)
    echo "   ✅ Backed up old API"
fi

# Start new API
cd /opt/revrank_engine/backend
source venv/bin/activate

nohup python3 revrank_api_postgres.py > /opt/revrank_engine/backend/revrank_api.log 2>&1 &
NEW_PID=$!

sleep 3

# Verify
if kill -0 $NEW_PID 2>/dev/null; then
    echo "   ✅ New API started (PID: $NEW_PID)"
else
    echo "   ❌ API failed to start. Check logs:"
    echo "      tail -50 /opt/revrank_engine/backend/revrank_api.log"
    exit 1
fi

# ============================================================================
# STEP 5: Verification
# ============================================================================
echo ""
echo "STEP 5: Verifying deployment..."
echo "────────────────────────────────────────"

# Test API
SITE_COUNT=$(curl -s http://localhost:8001/api/portfolio | jq -r '.total_sites' 2>/dev/null || echo "ERROR")

if [ "$SITE_COUNT" = "53" ]; then
    echo "   ✅ API responding correctly (53 sites)"
else
    echo "   ❌ API verification failed (got: $SITE_COUNT, expected: 53)"
    echo "      Check logs: tail -50 /opt/revrank_engine/backend/revrank_api.log"
    exit 1
fi

# Test RevFlow OS proxy
PROXY_COUNT=$(curl -s http://localhost:7000/revrank/api/portfolio | jq -r '.total_sites' 2>/dev/null || echo "ERROR")

if [ "$PROXY_COUNT" = "53" ]; then
    echo "   ✅ RevFlow OS proxy working"
else
    echo "   ⚠️  RevFlow OS proxy may need restart"
fi

# ============================================================================
# COMPLETION SUMMARY
# ============================================================================
echo ""
echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""
echo "Your RevRank Portfolio Dashboard is now live with 53 published sites!"
echo ""
echo "ACCESS POINTS:"
echo "  • API Direct:    http://217.15.168.106:8001/api/portfolio"
echo "  • RevFlow Proxy: http://217.15.168.106:7000/revrank/api/portfolio"
echo "  • Dashboard:     http://217.15.168.106:8080/"
echo ""
echo "DATABASE:"
echo "  • Host: localhost"
echo "  • Database: revrank_portfolio"
echo "  • User: revrank"
echo "  • Password: $DB_PASSWORD"
echo "  • Credentials saved to: /opt/revrank_engine/.env"
echo ""
echo "PORTFOLIO STATS:"
echo "  • Total Sites: 53 (published only)"
echo "  • ACTIVATE Tier: 20 sites ($35,500/month)"
echo "  • WATCHLIST Tier: 13 sites ($13,000/month)"
echo "  • SUNSET Tier: 20 sites ($10,000/month)"
echo "  • Total Revenue Potential: $58,500/month ($702K/year)"
echo ""
echo "QUICK TESTS:"
echo "  curl http://localhost:8001/api/portfolio | jq '.total_sites'"
echo "  curl http://localhost:8001/api/sites?tier=ACTIVATE | jq '.count'"
echo "  psql -U revrank -d revrank_portfolio -c 'SELECT tier, COUNT(*) FROM rr_sites GROUP BY tier;'"
echo ""
echo "API LOGS:"
echo "  tail -f /opt/revrank_engine/backend/revrank_api.log"
echo ""
echo "================================================================================"
