# RevFlow Central Control Center - File Installation Guide

## 📋 Files Included

This package contains the complete gateway migration implementation for RevFlow OS.

### 1. **revflow_client.py**
**Purpose:** Universal client for all module-to-module communication  
**File Size:** ~8KB  
**Location:** `/opt/shared-api-engine/revflow_client.py`  
**What it does:**
- Provides `RevFlowClient` class for gateway-based routing
- Implements dual-mode: tries gateway first, falls back to direct
- All 18 modules configured
- Singleton pattern for efficiency

**Usage in code:**
```python
from revflow_client import get_revflow_client
client = get_revflow_client()
result = client.call_module("revspy", "/health")
```

---

### 2. **test_revflow_client.py**
**Purpose:** Test suite to verify client functionality  
**File Size:** ~3KB  
**Location:** `/opt/shared-api-engine/test_revflow_client.py`  
**What it does:**
- Tests gateway mode
- Tests direct mode
- Tests all 18 modules configured
- Tests singleton pattern
- Tests endpoint handling

**Run tests:**
```bash
cd /opt/shared-api-engine
python3 test_revflow_client.py
```

---

### 3. **gateway.py**
**Purpose:** RevCore gateway router for inter-module requests  
**File Size:** ~3KB  
**Location:** `/opt/revcore/backend/app/routers/gateway.py`  
**What it does:**
- Routes requests from modules through RevCore gateway
- Uses service registry to find module endpoints
- Handles GET, POST, PUT, DELETE methods
- Logs all routing

**How it works:**
```
Module Request: POST /api/gateway/revspy/serp-analysis
↓
RevCore Gateway: Looks up revspy in registry
↓
Routes to: http://localhost:8160/api/serp-analysis
↓
Returns response to caller
```

---

### 4. **.env.addon**
**Purpose:** Configuration to add to existing .env file  
**File Size:** ~1KB  
**Location:** Append to `/opt/shared-api-engine/.env`  
**What it contains:**
- Gateway configuration
- Module endpoint mappings
- Request timeout setting

---

## 🚀 Installation Steps

### Step 1: Place Python Files

```bash
# Copy RevFlowClient to shared engine
cp revflow_client.py /opt/shared-api-engine/

# Copy test suite
cp test_revflow_client.py /opt/shared-api-engine/

# Verify permissions
chmod 644 /opt/shared-api-engine/revflow_client.py
chmod 644 /opt/shared-api-engine/test_revflow_client.py
```

### Step 2: Create RevCore Routers Directory

```bash
mkdir -p /opt/revcore/backend/app/routers
```

### Step 3: Place Gateway Router

```bash
# Copy gateway router
cp gateway.py /opt/revcore/backend/app/routers/

# Verify permissions
chmod 644 /opt/revcore/backend/app/routers/gateway.py
```

### Step 4: Update .env Configuration

**Option A: Using .env.addon file**
```bash
# Backup existing .env
cp /opt/shared-api-engine/.env /opt/shared-api-engine/.env.backup.$(date +%s)

# Append new configuration
cat .env.addon >> /opt/shared-api-engine/.env

# Verify
grep "REVCORE_GATEWAY" /opt/shared-api-engine/.env
```

**Option B: Manual update**

Open `/opt/shared-api-engine/.env` and add the contents of `.env.addon` at the end.

### Step 5: Verify Installation

```bash
# Test Python imports
python3 -c "import sys; sys.path.insert(0, '/opt/shared-api-engine'); from revflow_client import get_revflow_client; print('✓ Import successful')"

# Run test suite
cd /opt/shared-api-engine
python3 test_revflow_client.py
```

---

## 📊 File Structure After Installation

```
/opt/shared-api-engine/
├── revflow_client.py          ← New client class
├── test_revflow_client.py     ← Test suite
├── .env                       ← Updated with gateway config
└── .env.backup.*             ← Backup of original

/opt/revcore/backend/app/
├── routers/
│   ├── __init__.py
│   ├── gateway.py            ← New gateway router
│   └── ... (other routers)
└── ... (other files)
```

---

## ✅ Verification Checklist

After installation, verify:

- [ ] `revflow_client.py` exists at `/opt/shared-api-engine/revflow_client.py`
- [ ] `test_revflow_client.py` exists at `/opt/shared-api-engine/test_revflow_client.py`
- [ ] `gateway.py` exists at `/opt/revcore/backend/app/routers/gateway.py`
- [ ] `.env` contains `REVCORE_GATEWAY` configuration
- [ ] `.env` contains `USE_REVCORE_GATEWAY=true`
- [ ] `.env` contains all 18 module endpoints
- [ ] Python imports work: `from revflow_client import get_revflow_client`
- [ ] Test suite passes: `python3 test_revflow_client.py` shows ✅ ALL TESTS PASSED

---

## 🎯 Usage Examples

### Example 1: Module 14 Calling Module 15 (RevSPY)

```python
from revflow_client import get_revflow_client

client = get_revflow_client()

# Call RevSPY for SERP analysis
result = client.call_module(
    "revspy",
    "/serp-analysis",
    method="POST",
    data={
        "keyword": "emergency plumber",
        "location": "Dallas, TX"
    }
)

print(result)
```

### Example 2: Module 14 Calling Module 3 (RevRank)

```python
# Generate content with RevRank
content = client.call_module(
    "revrank",
    "/generate",
    method="POST",
    data={
        "niche": "plumbing",
        "location": "Dallas",
        "page_type": "service"
    }
)
```

### Example 3: Publishing with Module 9 (RevPublish)

```python
# Deploy to WordPress
result = client.call_module(
    "revpublish",
    "/deploy",
    method="POST",
    data={
        "site_id": 123,
        "content": content,
        "status": "publish"
    }
)
```

---

## 🔧 Troubleshooting

### Import Error: "No module named 'revflow_client'"

**Solution:** Make sure `/opt/shared-api-engine` is in Python path:
```python
import sys
sys.path.insert(0, '/opt/shared-api-engine')
from revflow_client import get_revflow_client
```

### Gateway Endpoint Not Found

**Solution:** Verify `gateway.py` is in correct location:
```bash
ls -la /opt/revcore/backend/app/routers/gateway.py
```

### Tests Failing

**Solution:** Run with Python 3 explicitly:
```bash
cd /opt/shared-api-engine
python3 test_revflow_client.py
```

### Module Not in Registry

**Solution:** Check `.env` has all module endpoints. Compare with `.env.addon` file.

---

## 🔄 Rollback Instructions

If you need to undo the changes:

```bash
# Restore .env from backup
cp /opt/shared-api-engine/.env.backup.* /opt/shared-api-engine/.env

# Remove new files
rm /opt/shared-api-engine/revflow_client.py
rm /opt/shared-api-engine/test_revflow_client.py
rm /opt/revcore/backend/app/routers/gateway.py

# Restart services
systemctl restart revcore
```

---

## 📝 Notes

- All files are backwards compatible
- Existing code continues to work
- Gateway mode can be disabled in .env: `USE_REVCORE_GATEWAY=false`
- No breaking changes to existing modules
- All 18 modules supported from day one

---

## 🚀 Next Steps

1. Install all files following the installation steps above
2. Run test suite to verify
3. Update module code to use `RevFlowClient`
4. Example: `client.call_module("revspy", "/health")`
5. Deploy to production

---

**Version:** 1.0  
**Created:** 2026-01-26  
**Status:** Production Ready
