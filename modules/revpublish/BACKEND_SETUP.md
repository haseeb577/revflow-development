# RevPublish Backend Setup Guide

## 🔴 Current Issue: PostgreSQL Not Running

The 500 error is caused by **PostgreSQL not running**. The backend needs PostgreSQL to store data.

## ✅ Solution: Start PostgreSQL

### Step 1: Check if PostgreSQL is Installed

```bash
where psql
```

If not found, download and install from: https://www.postgresql.org/download/windows/

### Step 2: Start PostgreSQL Service

**Option A: Using Windows Services**
1. Press `Win + R`, type `services.msc`, press Enter
2. Find "PostgreSQL" service
3. Right-click → Start
4. Set it to "Automatic" so it starts on boot

**Option B: Using Command Line**
```bash
# Start PostgreSQL service
net start postgresql-x64-XX  # Replace XX with your version number
```

**Option C: Using pg_ctl (if installed)**
```bash
pg_ctl start -D "C:\Program Files\PostgreSQL\XX\data"
```

### Step 3: Verify PostgreSQL is Running

```bash
# Test connection
psql -U postgres -c "SELECT version();"
```

Or check if port 5432 is listening:
```bash
netstat -ano | findstr :5432
```

### Step 4: Set Up Database

Once PostgreSQL is running:

```bash
cd modules\revpublish\backend
python setup_db.py
```

This will:
- Connect to the database
- Create the `wordpress_sites` table
- Set up required indexes

### Step 5: Verify Backend Can Connect

Test the database connection:
```bash
cd modules\revpublish\backend
python test_db.py
```

### Step 6: Restart Backend

After PostgreSQL is running and tables are created, restart the backend:

```bash
cd modules\revpublish
start_backend.bat
```

## 🔍 Troubleshooting

### Error: "Connection refused"
- **Cause:** PostgreSQL service is not running
- **Fix:** Start PostgreSQL service (see Step 2)

### Error: "Authentication failed"
- **Cause:** Wrong password
- **Fix:** Check `.env` file for correct `POSTGRES_PASSWORD`

### Error: "Database does not exist"
- **Cause:** Database `revflow` doesn't exist
- **Fix:** Create database:
  ```sql
  CREATE DATABASE revflow;
  ```

### Error: "Table does not exist"
- **Cause:** Tables weren't created
- **Fix:** Run `python setup_db.py`

## 📋 Quick Checklist

- [ ] PostgreSQL is installed
- [ ] PostgreSQL service is running
- [ ] Database `revflow` exists
- [ ] User `revflow` has access
- [ ] Tables are created (run setup_db.py)
- [ ] Backend is running on port 8550
- [ ] Frontend can connect to backend

## 🎯 Expected Result

Once everything is set up:
- Backend health check: http://localhost:8550/health
- Database test: http://localhost:8550/api/test-db
- Sites endpoint: http://localhost:8550/api/sites

All should return successful responses without 500 errors.


