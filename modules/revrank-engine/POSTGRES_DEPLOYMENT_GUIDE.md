# RevRank PostgreSQL Deployment - Step by Step
## Deploy 53 Published Sites to Your Existing Dashboard

**Current Status:**
- ✅ You have 53 published sites in Excel
- ✅ Your R&R Automation dashboard exists at `/opt/revrank_engine/`
- ✅ Current API shows mock data (old 53-site JSON)

**Goal:** Replace with real data from your Excel file

---

## Pre-Deployment Checklist

Upload these files to your server at `/opt/revrank_engine/`:

```bash
# From your local machine:
scp setup_revrank_postgres.sh root@217.15.168.106:/opt/revrank_engine/
scp import_excel_to_postgres.py root@217.15.168.106:/opt/revrank_engine/
scp revrank_api_postgres.py root@217.15.168.106:/opt/revrank_engine/backend/
scp SmarketSherpa_Digital_Landlord_websites__Shimon_and_Gianina_Sites_.xlsx root@217.15.168.106:/opt/revrank_engine/
```

---

## Option A: Automated Deployment (Recommended)

This single script does everything:

```bash
# SSH into your server
ssh root@217.15.168.106

# Run the setup script
cd /opt/revrank_engine
bash setup_revrank_postgres.sh
```

**That's it!** The script will:
1. Create PostgreSQL database
2. Import your 53 published sites
3. Calculate tier assignments
4. Deploy new API
5. Verify everything works

Expected output:
```
================================================================================
✅ DEPLOYMENT COMPLETE!
================================================================================

Your RevRank Portfolio Dashboard is now live with 53 published sites!

PORTFOLIO STATS:
  • Total Sites: 53 (published only)
  • ACTIVATE Tier: 20 sites ($35,500/month)
  • WATCHLIST Tier: 13 sites ($13,000/month)
  • SUNSET Tier: 20 sites ($10,000/month)
  • Total Revenue Potential: $58,500/month ($702K/year)
```

---

## Option B: Manual Step-by-Step

If you prefer to run each step manually:

### Step 1: Create PostgreSQL Database

```bash
# Generate a secure password
DB_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)
echo "Your DB Password: $DB_PASSWORD"

# Create database
sudo -u postgres psql << EOF
CREATE DATABASE revrank_portfolio;
CREATE USER revrank WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE revrank_portfolio TO revrank;
\c revrank_portfolio
GRANT ALL ON SCHEMA public TO revrank;
EOF
```

### Step 2: Save Database Credentials

```bash
cat > /opt/revrank_engine/.env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=revrank_portfolio
DB_USER=revrank
DB_PASSWORD=$DB_PASSWORD
EOF

chmod 600 /opt/revrank_engine/.env
```

### Step 3: Install Python Dependencies

```bash
cd /opt/revrank_engine/backend
source venv/bin/activate
pip install pandas openpyxl psycopg2-binary python-dotenv
```

### Step 4: Update Import Script Path

```bash
# Edit import script
nano /opt/revrank_engine/import_excel_to_postgres.py

# Update EXCEL_FILE path (around line 25):
EXCEL_FILE = '/opt/revrank_engine/SmarketSherpa_Digital_Landlord_websites__Shimon_and_Gianina_Sites_.xlsx'

# Update DB_CONFIG with your password (around line 15):
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'revrank_portfolio',
    'user': 'revrank',
    'password': 'YOUR_PASSWORD_FROM_STEP_1'
}
```

### Step 5: Run Import

```bash
cd /opt/revrank_engine
python3 import_excel_to_postgres.py
```

Expected output:
```
================================================================================
SMARKETSHERPA R&R AUTOMATION - EXCEL IMPORT
================================================================================

📊 Reading Excel file...
   Found 65 sites
   Filtering to 53 published sites (out of 65 total)

🔌 Connecting to PostgreSQL...

🏗️  Creating schema...
✅ Schema created

📥 Importing sites...
✅ Imported 53 sites

🎯 Calculating scores...
✅ Scores and tiers calculated
   ACTIVATE: 20 sites ($35,500/month)
   SUNSET: 20 sites ($10,000/month)
   WATCHLIST: 13 sites ($13,000/month)

================================================================================
IMPORT COMPLETE!
================================================================================
```

### Step 6: Deploy New API

```bash
# Stop old API
sudo kill $(sudo lsof -t -i:8001)

# Backup old API
cp /opt/revrank_engine/backend/main_enhanced.py \
   /opt/revrank_engine/backend/main_enhanced.py.backup

# Start new API
cd /opt/revrank_engine/backend
source venv/bin/activate
nohup python3 revrank_api_postgres.py > revrank_api.log 2>&1 &

# Wait for startup
sleep 3
```

### Step 7: Verify Deployment

```bash
# Test API
curl http://localhost:8001/api/portfolio | jq '.total_sites'
# Should output: 53

curl http://localhost:8001/api/portfolio | jq '.tier_distribution'
# Should output: {"activate": 20, "watchlist": 13, "sunset": 20}

# Test specific site
curl http://localhost:8001/api/site/site_016 | jq '.name'
# Should output: "Duncanville Concrete Driveway Pros"

# Test tier filtering
curl http://localhost:8001/api/sites?tier=ACTIVATE | jq '.count'
# Should output: 20
```

---

## Verification Checklist

After deployment, verify everything:

```bash
# 1. Database has 53 sites
psql -U revrank -d revrank_portfolio -c "SELECT COUNT(*) FROM rr_sites;"

# 2. Tier distribution is correct
psql -U revrank -d revrank_portfolio -c \
  "SELECT tier, COUNT(*), SUM(monthly_potential) FROM rr_sites GROUP BY tier;"

# Expected output:
#    tier    | count |  sum   
# -----------+-------+--------
#  ACTIVATE  |    20 |  35500
#  SUNSET    |    20 |  10000
#  WATCHLIST |    13 |  13000

# 3. API responds
curl http://localhost:8001/api/portfolio | jq -r '.total_sites'

# 4. RevFlow OS proxy works
curl http://localhost:7000/revrank/api/portfolio | jq -r '.total_sites'

# 5. Dashboard loads
curl -I http://localhost:8080/
```

---

## Access Your Dashboard

Once deployed, access at:

**Direct API:**
- http://217.15.168.106:8001/api/portfolio
- http://217.15.168.106:8001/api/sites
- http://217.15.168.106:8001/api/site/site_016

**Via RevFlow OS Proxy:**
- http://217.15.168.106:7000/revrank/api/portfolio
- http://217.15.168.106:7000/revrank/dashboard

**React Dashboard:**
- http://217.15.168.106:8080/

---

## What You Can Do Now

Your dashboard now shows:

### Portfolio Overview
- 53 published sites (accurate count)
- Tier distribution (20/13/20)
- $58,500/month revenue potential
- Category breakdowns

### Site Management
- View all sites by tier
- Filter by category
- See technical status (published, indexed, SSL)
- Access contact info (phone, email, owner)

### Content Generation Integration
Your sites are ready for V3.0 content generation:

```bash
# Trigger content generation for a site
curl -X POST http://localhost:7000/revflow/generate \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "site_016",
    "framework_version": "V3.0",
    "use_guru_rules": true
  }'
```

### Database Management

```bash
# View all ACTIVATE tier sites
psql -U revrank -d revrank_portfolio -c \
  "SELECT site_id, business_name, category, score, monthly_potential 
   FROM rr_sites WHERE tier = 'ACTIVATE' ORDER BY score DESC;"

# Update a site's tier
psql -U revrank -d revrank_portfolio -c \
  "UPDATE rr_sites SET tier = 'WATCHLIST' WHERE site_id = 'site_044';"

# Mark content as generated
psql -U revrank -d revrank_portfolio -c \
  "UPDATE rr_sites SET content_generated = TRUE, 
   last_content_update = NOW() WHERE site_id = 'site_016';"
```

---

## Troubleshooting

### API won't start
```bash
# Check logs
tail -50 /opt/revrank_engine/backend/revrank_api.log

# Check if port is in use
sudo lsof -i :8001

# Check if process is running
ps aux | grep revrank_api_postgres
```

### Database connection fails
```bash
# Test connection
psql -U revrank -d revrank_portfolio -c "SELECT 1;"

# Check credentials
cat /opt/revrank_engine/.env

# Check PostgreSQL is running
sudo systemctl status postgresql
```

### Dashboard shows no data
```bash
# Verify API is accessible
curl http://localhost:8001/api/portfolio

# Check CORS headers
curl -I http://localhost:8001/api/portfolio

# Restart RevFlow OS proxy
docker restart revflow-os-platform
```

### Site count is wrong
```bash
# Check database
psql -U revrank -d revrank_portfolio -c \
  "SELECT COUNT(*) as total_sites FROM rr_sites;"

# Re-run import if needed
python3 /opt/revrank_engine/import_excel_to_postgres.py
```

---

## Next Steps

1. **Content Generation**: Integrate with RevFlow OS to generate V3.0 framework content
2. **GEO Scoring**: Track AI-SEO quality scores for each site
3. **Performance Tracking**: Add Google Search Console data
4. **Lead Routing**: Connect to SimpleAudience for buyer intent leads
5. **Contractor Management**: Track which sites have active contractors

---

## Support

Your infrastructure is now:
- ✅ PostgreSQL database with 53 sites
- ✅ FastAPI backend (port 8001)
- ✅ RevFlow OS proxy (port 7000)
- ✅ React dashboard (port 8080)
- ✅ Ready for V3.0 content generation

**Database Credentials:** Stored in `/opt/revrank_engine/.env`

**Need Help?** Check logs:
- API: `/opt/revrank_engine/backend/revrank_api.log`
- RevFlow OS: `docker logs revflow-os-platform`
