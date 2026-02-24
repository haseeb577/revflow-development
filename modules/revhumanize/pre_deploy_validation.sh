#!/bin/bash
set -e

echo "🛡️ RUNNING PRE-DEPLOYMENT VALIDATION..."
echo ""

# Check 1: Python Syntax
echo "✓ Checking Python syntax..."
python3 -m py_compile app/**/*.py 2>&1 | grep -i "SyntaxError" && {
    echo "❌ SYNTAX ERROR DETECTED - DEPLOYMENT BLOCKED"
    exit 1
} || echo "  ✅ No syntax errors"

# Check 2: F-string validation
echo "✓ Checking for dangerous f-string patterns..."
grep -r "__import__.*uuid.*\.hex" app/ && {
    echo "❌ DANGEROUS F-STRING PATTERN DETECTED - DEPLOYMENT BLOCKED"
    echo "   Use: content_id = content_id or str(uuid.uuid4())"
    exit 1
} || echo "  ✅ No dangerous f-string patterns"

# Check 3: Database config
echo "✓ Checking database configuration..."
grep "localhost.*5432" app/database.py && {
    echo "⚠️  WARNING: Using localhost for PostgreSQL from Docker"
    echo "   This will fail. Use host.docker.internal or make DB optional"
}

echo ""
echo "✅ ALL GUARDRAILS PASSED"
