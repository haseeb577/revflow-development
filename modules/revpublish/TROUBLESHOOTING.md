# RevPublish Troubleshooting Guide

## Issue: "Response is not JSON. Backend may not be running"

### Step 1: Check if Backend is Running

Open a new terminal and run:
```bash
# Check if port 8550 is in use
netstat -ano | findstr :8550
```

Or test the backend directly:
```bash
# In PowerShell:
Invoke-WebRequest -Uri http://localhost:8550/api/test -UseBasicParsing

# Should return JSON like: {"status": "success", "message": "API routing is working"}
```

### Step 2: Start Backend if Not Running

```bash
cd modules\revpublish\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8550 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8550
INFO:     Application startup complete.
```

### Step 3: Test Backend Endpoints

Open in browser:
- `http://localhost:8550/` - Should show: `{"app": "RevPublish™ v2.1", ...}`
- `http://localhost:8550/health` - Should show health status
- `http://localhost:8550/api/test` - Should show: `{"status": "success", ...}`
- `http://localhost:8550/api/sites` - Should show: `{"status": "success", "sites": [], ...}`

### Step 4: Check Frontend Dev Server

Make sure frontend is running:
```bash
cd modules\revpublish\frontend
npm run dev
```

Should show:
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:3550/
```

### Step 5: Check Browser Console

1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for:
   - `📥 DynamicSelect fetching from: /api/sites?per_page=100`
   - `❌ DynamicSelect error: ...`
4. Go to Network tab
5. Find the `/api/sites` request
6. Check:
   - Status code (should be 200)
   - Response headers (should have `content-type: application/json`)
   - Response body (should be JSON)

### Step 6: Verify Vite Proxy

The `vite.config.js` should have:
```javascript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8550',
    changeOrigin: true
  }
}
```

This means:
- Frontend requests: `http://localhost:3550/api/sites`
- Vite proxy forwards to: `http://127.0.0.1:8550/api/sites`

### Step 7: Common Issues

**Issue: Backend returns HTML instead of JSON**
- Backend might be showing an error page
- Check backend terminal for error messages
- Restart backend: `Ctrl+C` then restart

**Issue: 404 Not Found**
- Backend not running
- Wrong port (should be 8550)
- Route not registered correctly

**Issue: CORS Error**
- Backend CORS middleware should allow all origins
- Check `main.py` has `allow_origins=["*"]`

**Issue: Sites not showing in selector**
- Backend is working but database is empty
- Add a site first using the Sites tab form
- Check database: `SELECT * FROM wordpress_sites;`

### Step 8: Database Check

If backend is running but sites aren't showing:

```bash
# Connect to database (if using Docker PostgreSQL on port 5433)
psql -h localhost -p 5433 -U revflow -d revflow

# Or if using local PostgreSQL on port 5432
psql -h localhost -p 5432 -U revflow -d revflow

# Then run:
SELECT id, site_name, site_url FROM wordpress_sites;
```

If table doesn't exist:
```bash
cd modules\revpublish\backend
python setup_db.py
```

## Quick Fix Checklist

- [ ] Backend running on port 8550?
- [ ] Frontend running on port 3550?
- [ ] Can access `http://localhost:8550/api/sites` directly?
- [ ] Response is JSON (not HTML)?
- [ ] Database has sites in `wordpress_sites` table?
- [ ] Browser console shows no errors?
- [ ] Network tab shows successful `/api/sites` request?

## Still Not Working?

1. Check backend logs for errors
2. Check browser console for detailed error messages
3. Verify database connection in backend
4. Test backend endpoint directly in browser
5. Check if firewall is blocking ports 8550 or 3550

