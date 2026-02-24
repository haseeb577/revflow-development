#!/bin/bash
# Nuclear Venv Rebuild - Complete Fresh Start
# Created: 2026-02-04 08:45:00

echo "========================================================================"
echo "🔥 NUCLEAR VENV REBUILD - COMPLETE FRESH START 🔥"
echo "========================================================================"
echo ""

cd /opt/revpublish/backend

echo "Step 1: Stopping service..."
systemctl stop revpublish-backend
systemctl reset-failed revpublish-backend 2>/dev/null
echo "   ✅ Service stopped"
echo ""

echo "Step 2: Completely removing corrupted venv..."
if [ -d "venv" ]; then
    mv venv venv.nuclear_backup_$(date +%Y%m%d_%H%M%S)
    echo "   ✅ Old venv backed up"
else
    echo "   ⚠️  No venv found to backup"
fi
echo ""

echo "Step 3: Creating COMPLETELY FRESH venv with system Python..."
/usr/bin/python3 -m venv venv --clear
echo "   ✅ Fresh venv created"
echo ""

echo "Step 4: Ensuring pip is fresh (bypassing cache)..."
venv/bin/python -m ensurepip --upgrade
echo "   ✅ Fresh pip installed"
echo ""

echo "Step 5: Upgrading pip to latest..."
venv/bin/python -m pip install --upgrade pip
echo "   ✅ Pip upgraded"
echo ""

echo "Step 6: Clearing ALL pip caches..."
venv/bin/pip cache purge
rm -rf ~/.cache/pip/* 2>/dev/null
echo "   ✅ All caches cleared"
echo ""

echo "Step 7: Installing packages from scratch (NO CACHE)..."
venv/bin/pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-dotenv \
    httpx \
    psycopg2-binary \
    python-multipart

echo "   ✅ Packages installed"
echo ""

echo "Step 8: Verifying click has core.py..."
if [ -f "venv/lib/python3.12/site-packages/click/core.py" ]; then
    echo "   ✅ core.py EXISTS!"
    ls -lh venv/lib/python3.12/site-packages/click/core.py
else
    echo "   ❌ core.py STILL MISSING - Filesystem corruption suspected!"
    echo ""
    echo "   Files in click directory:"
    ls -la venv/lib/python3.12/site-packages/click/
fi
echo ""

echo "Step 9: Testing Python imports..."
if venv/bin/python -c 'import click, fastapi, uvicorn; print("✅ All imports work!")' 2>/dev/null; then
    echo "   ✅ All packages work!"
else
    echo "   ❌ Import test failed:"
    venv/bin/python -c 'import click, fastapi, uvicorn' 2>&1 | head -20
fi
echo ""

echo "Step 10: Starting service..."
systemctl start revpublish-backend
sleep 5
echo ""

echo "Step 11: Final service check..."
if systemctl is-active --quiet revpublish-backend; then
    echo "   🎉 ✅ SERVICE IS RUNNING!"
    echo ""
    systemctl status revpublish-backend --no-pager | head -15
    echo ""
    echo "   Testing API..."
    sleep 2
    curl -s http://localhost:8550/health 2>&1 | head -5 || echo "   (Health endpoint check)"
else
    echo "   ❌ Service STILL failed"
    echo ""
    echo "   Latest error:"
    journalctl -u revpublish-backend --since "30 seconds ago" -n 30 --no-pager
fi

echo ""
echo "========================================================================"
echo "NUCLEAR REBUILD COMPLETE"
echo "========================================================================"
