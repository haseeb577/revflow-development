# Quick Start: PostgreSQL Setup for RevPublish

## Step-by-Step Guide

### Step 1: Check if PostgreSQL is Installed

Open PowerShell or Command Prompt and run:
```bash
where psql
```

**If you see a path** → PostgreSQL is installed, go to Step 2
**If you see "not found"** → Install PostgreSQL first (see Installation section below)

---

### Step 2: Start PostgreSQL Service

#### Method A: Using Windows Services (Easiest)

1. Press `Windows Key + R`
2. Type: `services.msc` and press Enter
3. In the Services window, look for:
   - `postgresql-x64-XX` (where XX is version number like 15, 16, etc.)
   - OR `PostgreSQL XX Server`
4. Right-click on the PostgreSQL service
5. Click **Start**
6. (Optional) Right-click → Properties → Set "Startup type" to **Automatic** (so it starts on boot)

#### Method B: Using Command Prompt (as Administrator)

1. Open Command Prompt as Administrator (Right-click → Run as administrator)
2. Find your PostgreSQL service name:
   ```bash
   sc query | findstr postgresql
   ```
3. Start the service (replace `postgresql-x64-15` with your actual service name):
   ```bash
   net start postgresql-x64-15
   ```

#### Method C: Using PowerShell (as Administrator)

```powershell
# Find PostgreSQL service
Get-Service -Name postgresql*

# Start the service (replace with your actual service name)
Start-Service postgresql-x64-15
```

---

### Step 3: Verify PostgreSQL is Running

Run this command:
```bash
netstat -ano | findstr :5432
```

**If you see output** → PostgreSQL is running ✓
**If no output** → PostgreSQL is not running, try Step 2 again

---

### Step 4: Create Database and User (If Not Already Done)

Open Command Prompt or PowerShell and run:

```bash
# Connect to PostgreSQL (you'll be prompted for postgres user password)
psql -U postgres
```

Then run these SQL commands:

```sql
-- Create user (if it doesn't exist)
CREATE USER revflow WITH PASSWORD 'revflow2026';

-- Create database
CREATE DATABASE revflow OWNER revflow;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE revflow TO revflow;

-- Connect to the new database
\c revflow

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO revflow;

-- Exit
\q
```

**OR** use the setup script we created earlier (if you have it):
```bash
cd modules\revpublish
python setup_database.py
```

---

### Step 5: Create Required Tables

Navigate to the backend folder and run the setup script:

```bash
cd modules\revpublish\backend
python setup_db.py
```

This will:
- Connect to the database
- Create the `wordpress_sites` table
- Create indexes
- Verify everything is set up correctly

**Expected output:**
```
✅ Connected to database
✅ Tables created successfully
✅ wordpress_sites table exists
✅ Database setup complete!
```

---

### Step 6: Test Database Connection

Verify everything works:

```bash
cd modules\revpublish\backend
python test_db.py
```

**Expected output:**
```
✅ Database connection successful!
✅ wordpress_sites table exists
```

---

### Step 7: Restart Backend Server

Now restart your backend:

```bash
cd modules\revpublish
start_backend.bat
```

Or manually:
```bash
cd modules\revpublish\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload
```

---

### Step 8: Test the API

Open your browser and test:

1. **Health Check:** http://localhost:8550/health
   - Should show: `{"status": "healthy", "database": "connected"}`

2. **Database Test:** http://localhost:8550/api/test-db
   - Should show: `{"status": "success", "table_exists": true}`

3. **Sites Endpoint:** http://localhost:8550/api/sites
   - Should return: `{"status": "success", "sites": [], "total": 0}` (empty list is normal)

---

## 🔧 Troubleshooting

### Problem: "Connection refused" when running setup_db.py

**Solution:** PostgreSQL service is not running
- Go back to Step 2 and start the PostgreSQL service

### Problem: "Authentication failed"

**Solution:** Wrong password or user doesn't exist
- Check your `.env` file for correct `POSTGRES_PASSWORD`
- Or create the user as shown in Step 4

### Problem: "Database does not exist"

**Solution:** Database wasn't created
- Run the SQL commands in Step 4 to create the database

### Problem: "Table does not exist" error

**Solution:** Tables weren't created
- Run `python setup_db.py` again (Step 5)

### Problem: Can't find PostgreSQL service

**Solution:** PostgreSQL might not be installed
- See Installation section below

---

## 📥 Installation: If PostgreSQL is Not Installed

1. **Download PostgreSQL:**
   - Go to: https://www.postgresql.org/download/windows/
   - Click "Download the installer"
   - Download PostgreSQL 15 or 16 (latest stable)

2. **Install PostgreSQL:**
   - Run the installer
   - **Important:** Remember the password you set for the `postgres` superuser
   - Default port: 5432 (keep this)
   - Default installation location is fine

3. **After Installation:**
   - PostgreSQL service should start automatically
   - Go back to Step 2 to verify it's running

---

## ✅ Success Checklist

After completing all steps, you should have:

- [x] PostgreSQL service running
- [x] Database `revflow` created
- [x] User `revflow` with password `revflow2026`
- [x] `wordpress_sites` table created
- [x] Backend can connect to database
- [x] `/api/sites` endpoint returns 200 (not 500)
- [x] Frontend can load dashboard data

---

## 🎯 Quick Command Summary

```bash
# 1. Start PostgreSQL (as Administrator)
net start postgresql-x64-15

# 2. Verify it's running
netstat -ano | findstr :5432

# 3. Setup database tables
cd modules\revpublish\backend
python setup_db.py

# 4. Test connection
python test_db.py

# 5. Start backend
cd ..
start_backend.bat
```

---

**Need Help?** Check the error messages - they usually tell you exactly what's wrong!


