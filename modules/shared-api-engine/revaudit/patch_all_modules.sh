#!/bin/bash
# RevAudit Integration Patcher
# Adds anti-hallucination framework to all RevFlow modules

set -e

echo "============================================"
echo "RevAudit Universal Integration"
echo "============================================"
echo ""

REVAUDIT_IMPORT='import sys; sys.path.insert(0, "/opt/shared-api-engine")'
REVAUDIT_INTEGRATE='from revaudit.integrate import integrate_revaudit'

# Function to patch a Python file
patch_module() {
    local file=$1
    local module_name=$2

    if [ ! -f "$file" ]; then
        echo "❌ File not found: $file"
        return 1
    fi

    # Check if already patched
    if grep -q "integrate_revaudit" "$file" 2>/dev/null; then
        echo "⏭️  Already integrated: $module_name"
        return 0
    fi

    # Create backup
    cp "$file" "${file}.pre-revaudit.bak"

    # Add import at the top (after existing imports)
    # Find the line with "from fastapi import" and add after it
    if grep -q "from fastapi import\|from fastapi import" "$file"; then
        sed -i '/^from fastapi import\|^from fastapi import/a\
\
# RevAudit Anti-Hallucination Integration\
import sys\
sys.path.insert(0, "/opt/shared-api-engine")\
try:\
    from revaudit.integrate import integrate_revaudit\
    REVAUDIT_AVAILABLE = True\
except ImportError:\
    REVAUDIT_AVAILABLE = False' "$file"

        # Find app = FastAPI(...) and add integration after it
        # This is tricky, so we'll add it after the CORS middleware typically
        if grep -q "app.add_middleware" "$file"; then
            # Add after last middleware
            sed -i '/^app.add_middleware.*CORSMiddleware/a\
\
# Integrate RevAudit\
if REVAUDIT_AVAILABLE:\
    integrate_revaudit(app, "'"$module_name"'")' "$file"
        else
            # Add after app = FastAPI
            sed -i '/^app = FastAPI/a\
\
# Integrate RevAudit\
if REVAUDIT_AVAILABLE:\
    integrate_revaudit(app, "'"$module_name"'")' "$file"
        fi

        echo "✅ Patched: $module_name ($file)"
        return 0
    else
        echo "⚠️  No FastAPI found in: $file"
        return 1
    fi
}

# Patch each module
echo "Patching modules..."
echo ""

# RevCore API
patch_module "/opt/revcore/api/main.py" "RevCore_API"

# RevCore Intelligence
patch_module "/opt/revcore-intelligence/main.py" "RevCore_Intelligence"

# RevCite
patch_module "/opt/revcite/api.py" "RevCite_Pro"

# RevAssist
patch_module "/var/www/revhome_assessment_engine_v2/revhome_api.py" "RevAssist"

# RevIntel
patch_module "/opt/revflow_enrichment_service/main.py" "RevIntel"

# RevSPY
patch_module "/opt/revflow-blind-spot-research/api.py" "RevSPY"

# RevImage
patch_module "/opt/revflow-os/modules/revimage/backend/main.py" "RevImage_Engine"

# RevPublish
patch_module "/opt/revpublish/backend/main.py" "RevPublish"

# RevPrompt
patch_module "/opt/revprompt-unified/api.py" "RevPrompt_Unified"

# RevWins
patch_module "/opt/quick-wins-api/app.py" "RevWins"

# RevRank (already done but verify)
patch_module "/opt/revrank_engine/backend/main.py" "RevRank_Engine"

# RevMetrics
patch_module "/opt/revflow-os/modules/revmetrics/main.py" "RevMetrics"

echo ""
echo "============================================"
echo "Integration complete!"
echo "Restart services with: systemctl restart <service>"
echo "============================================"
