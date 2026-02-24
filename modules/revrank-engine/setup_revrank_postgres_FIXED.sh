#!/bin/bash
# PostgreSQL Setup for RevRank Portfolio - 53 Published Sites
# FIXED: Handles Ubuntu 24.04 externally-managed Python environment

set -e  # Exit on any error

echo "================================================================================"
echo "REVRANK PORTFOLIO - POSTGRESQL SETUP (FIXED)"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Create PostgreSQL database 'revrank_portfolio'"
echo "  2. Install Python dependencies (with virtual environment)"
echo "  3. Import 53 published sites from Excel"
echo "  4. Calculate tier assignments and scores"
echo "  5. Deploy new API backend"
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
# STEP 2: Setup Python Virtual Environment
# ============================================================================
echo ""
echo "STEP 2: Setting up Python virtual environment..."
echo "────────────────────────────────────────"

cd /opt/revrank_engine

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
echo "   Installing dependencies..."
pip install -q --upgrade pip
pip install -q pandas openpyxl psycopg2-binary python-dotenv fastapi uvicorn

echo "✅ Virtual environment ready"

# ============================================================================
# STEP 3: Upload Excel File (if not present)
# ============================================================================
echo ""
echo "STEP 3: Checking for Excel file..."
echo "────────────────────────────────────────"

EXCEL_FILE="/opt/revrank_engine/SmarketSherpa_Digital_Landlord_websites__Shimon_and_Gianina_Sites_.xlsx"

if [ ! -f "$EXCEL_FILE" ]; then
    echo "   ⚠️  Excel file not found at: $EXCEL_FILE"
    echo "   Please upload the Excel file and run this script again:"
    echo "   scp SmarketSherpa_Digital_Landlord_websites__Shimon_and_Gianina_Sites_.xlsx root@217.15.168.106:/opt/revrank_engine/"
    exit 1
fi

echo "✅ Excel file found ($(stat -f%z "$EXCEL_FILE" 2>/dev/null || stat -c%s "$EXCEL_FILE") bytes)"

# ============================================================================
# STEP 4: Run Import Script
# ============================================================================
echo ""
echo "STEP 4: Importing 53 published sites..."
echo "────────────────────────────────────────"

# Make sure we're using the venv Python
source venv/bin/activate
python3 /opt/revrank_engine/import_excel_to_postgres_UPDATED.py

if [ $? -ne 0 ]; then
    echo "   ❌ Import failed. Check error messages above."
    exit 1
fi

echo "✅ Import complete"

# ============================================================================
# STEP 5: Deploy New API
# ============================================================================
echo ""
echo "STEP 5: Deploying PostgreSQL-backed API..."
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

# Create backend directory if it doesn't exist
mkdir -p /opt/revrank_engine/backend

# Copy the new API to the backend directory
cp /opt/revrank_engine/revrank_api_postgres.py /opt/revrank_engine/backend/

# Start new API
cd /opt/revrank_engine
source venv/bin/activate

nohup python3 backend/revrank_api_postgres.py > /opt/revrank_engine/backend/revrank_api.log 2>&1 &
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
# STEP 6: Verification
# ============================================================================
echo ""
echo "STEP 6: Verifying deployment..."
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

# Test RevFlow OS proxy (optional)
PROXY_COUNT=$(curl -s http://localhost:7000/revrank/api/portfolio 2>/dev/null | jq -r '.total_sites' 2>/dev/null || echo "SKIP")

if [ "$PROXY_COUNT" = "53" ]; then
    echo "   ✅ RevFlow OS proxy working"
elif [ "$PROXY_COUNT" = "SKIP" ]; then
    echo "   ℹ️  RevFlow OS proxy test skipped (service may not be running)"
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
echo "  • ACTIVATE Tier: 20 sites (\$35,500/month)"
echo "  • WATCHLIST Tier: 13 sites (\$13,000/month)"
echo "  • SUNSET Tier: 20 sites (\$10,000/month)"
echo "  • Total Revenue Potential: \$58,500/month (\$702K/year)"
echo ""
echo "QUICK TESTS:"
echo "  curl http://localhost:8001/api/portfolio | jq '.total_sites'"
echo "  curl http://localhost:8001/api/sites?tier=ACTIVATE | jq '.count'"
echo "  psql -U revrank -d revrank_portfolio -c 'SELECT tier, COUNT(*) FROM rr_sites GROUP BY tier;'"
echo ""
echo "API LOGS:"
echo "  tail -f /opt/revrank_engine/backend/revrank_api.log"
echo ""
echo "VIRTUAL ENVIRONMENT:"
echo "  To activate: source /opt/revrank_engine/venv/bin/activate"
echo ""
echo "================================================================================"
