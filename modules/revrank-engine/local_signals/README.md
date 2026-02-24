# REVFLOW LOCAL SIGNALS - DEPLOYMENT PACKAGE
## Full 53 City Bootstrap - Component 1

**Created:** February 8, 2026  
**Server:** 217.15.168.106  
**Database:** revflow_db  
**Timeline:** 6-7 hours total

---

## 📦 PACKAGE CONTENTS

This deployment package contains:

1. **schema.sql** - PostgreSQL schema (4 tables)
2. **cities.csv** - 53 Texas cities with GPS coordinates
3. **bootstrap_all_cities.py** - Main bootstrap script
4. **test_quality.py** - Quality verification script
5. **deploy.sh** - Master deployment script
6. **README.md** - This file

---

## 🚀 QUICK START (3 COMMANDS)

```bash
# 1. Upload files to server
scp *.{sql,csv,py,sh} root@217.15.168.106:/opt/revrank_engine/local_signals/

# 2. SSH to server
ssh root@217.15.168.106

# 3. Run deployment
cd /opt/revrank_engine/local_signals
bash deploy.sh
```

**That's it!** The script handles everything.

---

## 📋 DETAILED INSTRUCTIONS

### Step 1: Upload Files (2 minutes)

From your local machine where you downloaded these files:

```bash
# Create directory on server
ssh root@217.15.168.106 "mkdir -p /opt/revrank_engine/local_signals"

# Upload all files
scp schema.sql cities.csv bootstrap_all_cities.py test_quality.py deploy.sh \
    root@217.15.168.106:/opt/revrank_engine/local_signals/

# Verify upload
ssh root@217.15.168.106 "ls -lh /opt/revrank_engine/local_signals/"
```

### Step 2: Run Deployment (30 min setup + 6 hours bootstrap)

```bash
# SSH to server
ssh root@217.15.168.106

# Navigate to directory
cd /opt/revrank_engine/local_signals

# Make deploy script executable
chmod +x deploy.sh

# Run deployment
bash deploy.sh
```

The script will:
1. ✅ Check prerequisites (PostgreSQL, Python, database)
2. ✅ Install Python packages (requests, beautifulsoup4, psycopg2)
3. ✅ Create directory structure
4. ✅ Initialize database schema (4 tables)
5. ✅ Verify cities.csv (53 cities)
6. ✅ Confirm before starting bootstrap
7. ✅ Start bootstrap (runs 6+ hours in background)

### Step 3: Monitor Progress

```bash
# Watch progress in real-time
tail -f bootstrap_log.txt

# OR: Check summary every 30 minutes
watch -n 1800 "tail -n 50 bootstrap_log.txt"

# Check if still running
ps aux | grep bootstrap_all_cities.py

# See last checkpoint
grep "CHECKPOINT" bootstrap_log.txt | tail -1
```

### Step 4: Verify Results (After bootstrap completes)

```bash
# Run quality test
python3 test_quality.py

# Check database
psql -U revflow -d revflow_db -c "
SELECT 
    (SELECT COUNT(*) FROM local_landmarks) as landmarks,
    (SELECT COUNT(*) FROM local_neighborhoods) as neighborhoods,
    (SELECT COUNT(DISTINCT city) FROM local_landmarks) as cities_with_landmarks;
"
```

**Expected Results:**
- ✅ 2,000-2,500 landmarks
- ✅ 800-1,200 neighborhoods
- ✅ 53 cities with data
- ✅ Quality test passes (75%+ score)

---

## ⏱️ TIMELINE

| Phase | Duration | When |
|-------|----------|------|
| Upload files | 2 min | Now |
| Run deploy.sh | 5 min | Now |
| Setup checks | 5 min | Automated |
| Confirmation prompt | 1 min | Manual |
| Bootstrap start | Instant | Automated |
| **Bootstrap running** | **4-6 hours** | **Background** |
| Quality test | 5 min | After bootstrap |
| **Total** | **6-7 hours** | **Mostly unattended** |

---

## 📊 PROGRESS CHECKPOINTS

The bootstrap shows progress every 10 cities:

```
[10/53] ⏱️ CHECKPOINT [10/53 cities]
   Elapsed: 60.0 min | Remaining: 258.0 min
   Success: 10/10 cities

[20/53] ⏱️ CHECKPOINT [20/53 cities]
   Elapsed: 120.0 min | Remaining: 198.0 min
   Success: 20/20 cities

[30/53] ⏱️ CHECKPOINT [30/53 cities]
   Elapsed: 180.0 min | Remaining: 138.0 min
   Success: 30/30 cities
```

---

## 🔧 MANUAL EXECUTION (If deploy.sh fails)

If you prefer to run commands manually:

```bash
# 1. Install dependencies
pip install requests beautifulsoup4 psycopg2-binary --break-system-packages

# 2. Create directory
mkdir -p /opt/revrank_engine/local_signals
cd /opt/revrank_engine/local_signals

# 3. Initialize database
psql -U revflow -d revflow_db -f schema.sql

# 4. Run bootstrap
python3 bootstrap_all_cities.py > bootstrap_log.txt 2>&1 &
echo $! > bootstrap.pid

# 5. Monitor
tail -f bootstrap_log.txt

# 6. After completion, test quality
python3 test_quality.py
```

---

## 📈 WHAT GETS CREATED

### Database Tables

1. **local_landmarks** - Tourist attractions, parks, museums, stadiums
   - Stores: name, category, GPS coordinates, importance score
   - Source: OpenStreetMap Overpass API
   - Expected: 40-50 per city, 2,000-2,500 total

2. **local_neighborhoods** - Neighborhoods and districts
   - Stores: name, admin level, center GPS coordinates
   - Source: OpenStreetMap Overpass API
   - Expected: 15-25 per city, 800-1,200 total

3. **local_climate** - Monthly climate averages + risks
   - Stores: temps (high/low), precipitation, freeze/heat risks
   - Source: Open-Meteo Historical API
   - Expected: 12 months per city + 1 annual summary

4. **local_events** - Major city events
   - Stores: title, dates, venue, event type
   - Source: Hardcoded for major cities (State Fair, SXSW, rodeos)
   - Expected: 10-20 major events total

### Example Data for Dallas

**Landmarks (Top 5):**
- Reunion Tower (importance: 95)
- Fair Park (importance: 90)
- Dallas Museum of Art (importance: 88)
- American Airlines Center (importance: 87)
- Klyde Warren Park (importance: 85)

**Neighborhoods (Sample):**
- Uptown
- Highland Park
- Oak Lawn
- Design District
- Deep Ellum
- Bishop Arts District
- Lakewood
- East Dallas
- Old East Dallas
- Preston Hollow

**Climate Summary:**
"Dallas experiences extreme summer heat (96°F+) and occasional hard freezes (avg 37°F in winter)"

**Events:**
- State Fair of Texas (Sept 15 - Oct 15)
- Dallas Cowboys Training Camp (July 20 - Aug 15)

---

## ✅ SUCCESS CRITERIA

After deployment, you should have:

- [ ] 4 database tables created
- [ ] 2,000-2,500 landmarks stored
- [ ] 800-1,200 neighborhoods stored
- [ ] 53 cities with climate data
- [ ] 10-20 major events
- [ ] Quality test passes (75%+ score)
- [ ] Test content shows local signals

---

## 🔄 ROLLBACK (If needed)

If something goes wrong:

```bash
# Drop all tables
psql -U revflow -d revflow_db << 'SQL'
DROP TABLE IF EXISTS local_events;
DROP TABLE IF EXISTS local_climate;
DROP TABLE IF EXISTS local_neighborhoods;
DROP TABLE IF EXISTS local_landmarks;
SQL

# Clean up directory
rm -rf /opt/revrank_engine/local_signals/*

# No harm done - existing content untouched
```

---

## 🐛 TROUBLESHOOTING

### Issue: "Cannot connect to database"

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify credentials
psql -U revflow -d revflow_db -c "SELECT 1;"
```

### Issue: "OpenStreetMap API timeout"

**Normal for first run.** Script includes 2-second delays between API calls. If timeouts persist:

```bash
# Increase timeout in bootstrap_all_cities.py
# Line ~50: timeout=90 → timeout=120
```

### Issue: "No data for [city]"

Some smaller cities may have limited OpenStreetMap data. This is expected. Check:

```bash
# See which cities have data
psql -U revflow -d revflow_db -c "
SELECT city, COUNT(*) as landmark_count 
FROM local_landmarks 
GROUP BY city 
ORDER BY landmark_count DESC;
"
```

---

## 📞 NEXT STEPS

### After Bootstrap Completes:

1. **Run quality test:**
   ```bash
   python3 test_quality.py
   ```

2. **If quality passes (75%+):**
   - Integrate with Module 3 (next week)
   - Deploy Components 2-4 (weeks 2-3)

3. **If quality needs work:**
   - Review test output
   - Adjust templates
   - Re-run specific cities

---

## 📚 ADDITIONAL FILES

**All implementation documents are available:**
- Component 1: Local Signals (this deployment)
- Component 2: GBP Competitor Analysis
- Component 3: Review Response AI
- Component 4: Local Trending Topics
- Master Guide: Complete roadmap
- Demo: Before/After examples

---

## 💰 COST & SAVINGS

**Setup Cost:** ~$3,000 one-time (developer time)  
**Monthly Cost:** $0 (all APIs free)  
**3-Year Savings:** $13,812 vs BrightLocal+Localo+Jasper

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] Files uploaded to server
- [ ] SSH access confirmed
- [ ] deploy.sh executed
- [ ] Bootstrap started
- [ ] Progress monitored
- [ ] Bootstrap completed (6+ hours)
- [ ] Quality test run
- [ ] Results verified
- [ ] Ready for Module 3 integration

---

**Questions?** Review the full implementation docs or contact your development team.

**Ready to deploy?** Upload files and run `bash deploy.sh`! 🚀
