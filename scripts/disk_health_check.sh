#!/bin/bash
# Disk Health Check - Run BEFORE Nuclear Rebuild
# Created: 2026-02-04 08:50:00

echo "========================================================================"
echo "DISK HEALTH DIAGNOSTIC - CRITICAL PRE-REBUILD CHECK"
echo "========================================================================"
echo ""

echo "=== SYSTEM INFORMATION ==="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo "Uptime: $(uptime -p)"
echo ""

echo "=== DISK USAGE ==="
df -h /opt /root /tmp
echo ""

echo "=== CHECKING FOR I/O ERRORS IN KERNEL LOG ==="
echo "Looking for disk errors in last 1000 kernel messages..."
if dmesg | tail -1000 | grep -i "error\|fail\|I/O" | grep -i "sda\|disk\|sector" | tail -20; then
    echo ""
    echo "⚠️  WARNING: Found potential disk errors above!"
else
    echo "✅ No obvious disk errors in recent kernel log"
fi
echo ""

echo "=== FILESYSTEM CHECK STATUS ==="
echo "Checking filesystem errors on /opt partition..."
mount | grep /opt
tune2fs -l $(df /opt | tail -1 | awk '{print $1}') 2>/dev/null | grep -i "errors\|state" || echo "Could not read filesystem info"
echo ""

echo "=== CHECKING FILE WRITE TEST ==="
echo "Testing if we can write files to /opt/revpublish/backend..."
TEST_FILE="/opt/revpublish/backend/.disk_test_$(date +%s)"
if echo "test data" > "$TEST_FILE" 2>/dev/null; then
    if [ "$(cat $TEST_FILE 2>/dev/null)" = "test data" ]; then
        echo "✅ Write test PASSED - can write and read files"
        rm -f "$TEST_FILE"
    else
        echo "❌ Write test FAILED - file corruption detected!"
        echo "   Wrote: 'test data'"
        echo "   Read back: '$(cat $TEST_FILE)'"
    fi
else
    echo "❌ Write test FAILED - cannot write to disk!"
fi
echo ""

echo "=== CHECKING /opt MOUNT OPTIONS ==="
mount | grep /opt
if mount | grep /opt | grep -q "ro,"; then
    echo "❌ CRITICAL: /opt is mounted READ-ONLY!"
else
    echo "✅ /opt is writable"
fi
echo ""

echo "=== CHECKING AVAILABLE INODES ==="
df -i /opt
INODE_USAGE=$(df -i /opt | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$INODE_USAGE" -gt 90 ]; then
    echo "⚠️  WARNING: Inode usage is ${INODE_USAGE}% (may cause file creation issues)"
else
    echo "✅ Inode usage is healthy (${INODE_USAGE}%)"
fi
echo ""

echo "=== CHECKING FOR CORRUPTED VENV FILES ==="
echo "Looking for zero-byte files in venv..."
if [ -d "/opt/revpublish/backend/venv" ]; then
    ZERO_FILES=$(find /opt/revpublish/backend/venv -type f -size 0 2>/dev/null | wc -l)
    if [ "$ZERO_FILES" -gt 0 ]; then
        echo "⚠️  Found $ZERO_FILES zero-byte files (sign of corruption)"
        find /opt/revpublish/backend/venv -type f -size 0 2>/dev/null | head -10
    else
        echo "✅ No zero-byte files found"
    fi
else
    echo "   Venv not found (will be created fresh)"
fi
echo ""

echo "=== SMART STATUS (if available) ==="
if command -v smartctl &> /dev/null; then
    echo "Running SMART health check..."
    DISK=$(df /opt | tail -1 | awk '{print $1}' | sed 's/[0-9]*$//')
    smartctl -H $DISK 2>/dev/null || echo "SMART not available or permission denied"
else
    echo "smartmontools not installed (optional)"
    echo "To install: apt install smartmontools"
fi
echo ""

echo "=== CHECKING SYSTEM PYTHON INTEGRITY ==="
echo "Verifying system Python is not corrupted..."
if /usr/bin/python3 -c "import sys; print(f'✅ Python {sys.version}')"; then
    echo "✅ System Python works"
else
    echo "❌ CRITICAL: System Python is broken!"
fi
echo ""

echo "=== VERIFYING PIP INSTALLATION ==="
if /usr/bin/python3 -m pip --version 2>/dev/null; then
    echo "✅ System pip works"
else
    echo "⚠️  System pip may need reinstall: apt install --reinstall python3-pip"
fi
echo ""

echo "========================================================================"
echo "DIAGNOSTIC SUMMARY"
echo "========================================================================"
echo ""
echo "Review the output above for:"
echo "  ❌ I/O errors in kernel log"
echo "  ❌ Read-only filesystem"
echo "  ❌ File write test failures"
echo "  ❌ High inode usage (>90%)"
echo "  ❌ SMART health failures"
echo ""
echo "If ANY critical issues found above:"
echo "  → DO NOT proceed with nuclear rebuild"
echo "  → Contact Hostinger support immediately"
echo "  → Prepare to migrate to new VPS"
echo ""
echo "If ALL checks passed:"
echo "  → Proceed with nuclear_venv_rebuild.sh"
echo "  → Monitor Step 8 (core.py verification)"
echo ""
echo "========================================================================"
