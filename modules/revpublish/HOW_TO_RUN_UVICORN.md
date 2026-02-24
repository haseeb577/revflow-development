# How to Run Uvicorn (Backend Server)

## Quick Start

### Option 1: Using the Batch Script (Easiest)

```bash
cd modules\revpublish
start_backend.bat
```

This script will:
- Check if Python is installed
- Create virtual environment if needed
- Install dependencies
- Start uvicorn on port 8550

---

### Option 2: Manual Command

#### Step 1: Navigate to Backend Folder

```bash
cd modules\revpublish\backend
```

#### Step 2: Activate Virtual Environment (if you have one)

```bash
# If virtual environment exists
venv\Scripts\activate

# Or if using different venv name
.\venv\Scripts\activate
```

#### Step 3: Install Dependencies (if not already installed)

```bash
pip install -r requirements.txt
```

Make sure you have:
- `fastapi`
- `uvicorn`
- `psycopg2-binary`
- Other dependencies from requirements.txt

#### Step 4: Run Uvicorn

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload
```

**Command breakdown:**
- `python -m uvicorn` - Run uvicorn via Python module
- `main:app` - Import `app` from `main.py` file
- `--host 0.0.0.0` - Listen on all network interfaces
- `--port 8550` - Use port 8550
- `--reload` - Auto-reload on code changes (development mode)

---

## Expected Output

When uvicorn starts successfully, you should see:

```
INFO:     Will watch for changes in these directories: ['C:\\Users\\...\\modules\\revpublish\\backend']
INFO:     Uvicorn running on http://0.0.0.0:8550 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Verify It's Running

### Test 1: Health Check
Open browser: http://localhost:8550/health

Should return:
```json
{
  "status": "healthy",
  "service": "revpublish",
  "database": "connected",
  "backend_port": 8550
}
```

### Test 2: API Docs
Open browser: http://localhost:8550/docs

Should show FastAPI interactive documentation

### Test 3: Test Database
Open browser: http://localhost:8550/api/test-db

Should return database status

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'uvicorn'"

**Solution:** Install uvicorn
```bash
pip install uvicorn fastapi
```

### Issue: "Address already in use"

**Solution:** Port 8550 is already taken
```bash
# Find what's using the port
netstat -ano | findstr :8550

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different port
python -m uvicorn main:app --host 0.0.0.0 --port 8551 --reload
```

### Issue: "ImportError: cannot import name 'app' from 'main'"

**Solution:** Make sure you're in the backend folder
```bash
cd modules\revpublish\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload
```

### Issue: Database connection errors

**Solution:** Make sure PostgreSQL is running and database is set up
- Start PostgreSQL service
- Run `python setup_db.py` to create tables

---

## Running in Production (Without --reload)

For production, remove `--reload` and add workers:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --workers 4
```

---

## Running in Background (Windows)

### Using start command:
```bash
start /B python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload
```

### Using PowerShell:
```powershell
Start-Process python -ArgumentList "-m","uvicorn","main:app","--host","0.0.0.0","--port","8550","--reload" -WindowStyle Hidden
```

---

## Stop the Server

Press `Ctrl + C` in the terminal where uvicorn is running

---

## Quick Reference

```bash
# Navigate to backend
cd modules\revpublish\backend

# Activate venv (if exists)
venv\Scripts\activate

# Run server
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload
```

---

## Environment Variables

Make sure you have a `.env` file in the project root with:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=revflow
POSTGRES_USER=revflow
POSTGRES_PASSWORD=revflow2026
```

The backend will use these to connect to the database.


