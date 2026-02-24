# RevPrompt Unified™ - Quick Start Guide

## 🚀 Start the Service

```bash
# Navigate to directory
cd /opt/revprompt-unified

# Start service in background
python3 run-api.py > logs/startup.log 2>&1 &

# Save PID for later
echo $! > revprompt.pid
```

## ✅ Verify It's Running

```bash
# Check process
ps aux | grep "python3 run-api.py" | grep -v grep

# Test health endpoint
curl http://localhost:8700/api/health

# Should return:
# {
#   "status": "healthy",
#   "service": "RevPrompt Unified™",
#   "version": "1.0.0",
#   "port": 8700
# }
```

## 🌐 Access Points

- **API Base:** http://217.15.168.106:8700
- **Admin UI:** http://217.15.168.106:8700/
- **Health Check:** http://localhost:8700/api/health

## 📊 Available Endpoints

### Configuration
- `GET /api/health` - Service health
- `GET /api/page-types` - List 11 page types
- `GET /api/enhancement-layers` - List 18 enhancement layers
- `GET /api/voice-profiles` - List 3 voice profiles

### Content Generation
- `POST /api/generate` - Generate content
- `POST /api/validate` - Validate content
- `GET /api/portfolio/stats` - Portfolio statistics

## 🧪 Test Generation

```bash
curl -X POST http://localhost:8700/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "page_type": "homepage",
    "business_data": {
      "business_name": "Acme Plumbing",
      "industry": "plumbing",
      "location": "Dallas, TX"
    },
    "voice_profile": "authority"
  }'
```

## 🛑 Stop the Service

```bash
# Kill by PID
kill $(cat /opt/revprompt-unified/revprompt.pid)

# Or kill all instances
pkill -f "python3 run-api.py"
```

## 📝 View Logs

```bash
# Real-time logs
tail -f /opt/revprompt-unified/logs/revprompt.log

# Startup logs
cat /opt/revprompt-unified/logs/startup.log
```

## 🔗 Nginx Integration (Optional)

Add to `/etc/nginx/sites-available/automation.smarketsherpa.ai`:

```nginx
location /revprompt/ {
    proxy_pass http://localhost:8700/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_read_timeout 90;
}
```

Then reload nginx:
```bash
nginx -t
service nginx reload
```

Access via: https://automation.smarketsherpa.ai/revprompt/

## 📁 Files Included

1. **run-api.py** (654 lines) - Main Flask API server
2. **index.html** (903 lines) - Admin UI interface
3. **schema.sql** (180 lines) - PostgreSQL database schema

## 🎯 Current Status

- ✅ API server code complete (654 lines)
- ✅ Admin UI complete (903 lines)
- ✅ Database schema ready
- ✅ 11 page types defined
- ✅ 18 enhancement layers configured
- ✅ 3 voice profiles implemented
- ⏳ AI integration pending (demo mode active)
- ⏳ Database connection pending (schema ready)

## 🔧 Troubleshooting

**Service won't start:**
```bash
# Check for errors
tail -50 /opt/revprompt-unified/logs/startup.log

# Check port availability
lsof -i :8700  # or: ss -tuln | grep 8700

# Restart
cd /opt/revprompt-unified
pkill -f run-api.py
python3 run-api.py > logs/startup.log 2>&1 &
```

**Port already in use:**
```bash
# Find what's using port 8700
lsof -i :8700

# Kill that process
kill <PID>
```

**Database errors:**
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Test connection
psql -U postgres -d postgres -c "SELECT 1;"
```

---

**Everything is ready to run!**
