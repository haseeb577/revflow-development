#!/bin/bash
# RevFlow Local Signals - Master Deployment Script
# Run this on your server: bash deploy.sh
# Server: 217.15.168.106
# Location: /opt/revrank_engine/local_signals/

set -e  # Exit on any error

# Load shared environment
source /opt/shared-api-engine/.env
export PGPASSWORD="$POSTGRES_PASSWORD"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "================================================================"
echo "🚀 REVFLOW LOCAL SIGNALS - FULL DEPLOYMENT"
echo "================================================================"
echo ""

# Step 1: Check prerequisites
echo -e "${BLUE}[STEP 1/7]${NC} Checking prerequisites..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo -e "${RED}❌ ERROR: PostgreSQL is not running${NC}"
    echo "   Start it with: sudo systemctl start postgresql"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is running${NC}"

# Check if database exists
if ! psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: Cannot connect to revflow_db${NC}"
    echo "   Check database credentials"
    exit 1
fi
echo -e "${GREEN}✅ Database connection verified${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python version: ${PYTHON_VERSION}${NC}"

echo ""

# Step 2: Install Python dependencies
echo -e "${BLUE}[STEP 2/7]${NC} Installing Python dependencies..."
pip install requests beautifulsoup4 psycopg2-binary --break-system-packages --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ ERROR: Failed to install dependencies${NC}"
    exit 1
fi

echo ""

# Step 3: Create directory structure
echo -e "${BLUE}[STEP 3/7]${NC} Creating directory structure..."
mkdir -p /opt/revrank_engine/local_signals
cd /opt/revrank_engine/local_signals

# Copy files to deployment directory (if running from elsewhere)
if [ -f "$PWD/schema.sql" ]; then
    echo -e "${GREEN}✅ Already in deployment directory${NC}"
else
    echo -e "${YELLOW}⚠️  Assuming files are in current directory${NC}"
fi

echo ""

# Step 4: Initialize database
echo -e "${BLUE}[STEP 4/7]${NC} Initializing database schema..."
psql -U $POSTGRES_USER -d $POSTGRES_DB -f schema.sql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database schema created${NC}"
    
    # Verify tables
    TABLE_COUNT=$(psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'local_%'")
    echo "   Created tables: ${TABLE_COUNT}"
else
    echo -e "${RED}❌ ERROR: Failed to create schema${NC}"
    exit 1
fi

echo ""

# Step 5: Verify cities.csv
echo -e "${BLUE}[STEP 5/7]${NC} Verifying cities.csv..."
if [ ! -f "cities.csv" ]; then
    echo -e "${RED}❌ ERROR: cities.csv not found${NC}"
    exit 1
fi

CITY_COUNT=$(wc -l < cities.csv)
CITY_COUNT=$((CITY_COUNT - 1))  # Subtract header
echo -e "${GREEN}✅ Found ${CITY_COUNT} cities in CSV${NC}"

echo ""

# Step 6: Confirm before bootstrap
echo -e "${BLUE}[STEP 6/7]${NC} Ready to bootstrap ${CITY_COUNT} cities"
echo ""
echo -e "${YELLOW}⏱️  Estimated time: $(echo "scale=1; $CITY_COUNT * 6 / 60" | bc) hours${NC}"
echo ""
echo "This will:"
echo "  • Fetch landmarks from OpenStreetMap"
echo "  • Fetch neighborhoods from OpenStreetMap"
echo "  • Fetch climate data from Open-Meteo"
echo "  • Add major city events"
echo ""
echo -n "Proceed with bootstrap? (y/n): "
read -r CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${YELLOW}❌ Deployment cancelled by user${NC}"
    exit 0
fi

echo ""

# Step 7: Run bootstrap
echo -e "${BLUE}[STEP 7/7]${NC} Starting bootstrap..."
echo ""
echo "🚀 Bootstrap running... (this will take several hours)"
echo "   Log file: bootstrap_log.txt"
echo "   Monitor: tail -f bootstrap_log.txt"
echo ""

# Make scripts executable
chmod +x bootstrap_all_cities.py
chmod +x test_quality.py

# Run bootstrap in background
python3 bootstrap_all_cities.py > bootstrap_log.txt 2>&1 &
BOOTSTRAP_PID=$!
echo $BOOTSTRAP_PID > bootstrap.pid

echo -e "${GREEN}✅ Bootstrap started (PID: ${BOOTSTRAP_PID})${NC}"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "📊 DEPLOYMENT IN PROGRESS"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "To monitor progress:"
echo "  tail -f bootstrap_log.txt"
echo ""
echo "To check if still running:"
echo "  ps aux | grep bootstrap_all_cities.py"
echo ""
echo "To stop bootstrap:"
echo "  kill ${BOOTSTRAP_PID}"
echo ""
echo "After completion, run quality test:"
echo "  python3 test_quality.py"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
