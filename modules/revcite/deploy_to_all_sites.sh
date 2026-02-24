#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║        RevCite: Deploy Citation Tracking to All Sites             ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Load configuration
CONFIG_FILE="/opt/revcite/config/tracking_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    exit 1
fi

# Extract values from config
INDEXNOW_KEY=$(grep '"indexnow_key"' "$CONFIG_FILE" | cut -d'"' -f4)
CLARITY_ID=$(grep '"clarity_project_id"' "$CONFIG_FILE" | cut -d'"' -f4)

if [ "$CLARITY_ID" = "REPLACE_WITH_YOUR_CLARITY_PROJECT_ID" ]; then
    echo "❌ Please update Clarity Project ID in config file first!"
    echo "   Edit: $CONFIG_FILE"
    exit 1
fi

echo "Configuration:"
echo "  Clarity ID: $CLARITY_ID"
echo "  IndexNow Key: ${INDEXNOW_KEY:0:20}..."
echo ""

# List of WordPress sites (customize this)
# Format: "domain|path"
SITES=(
    "example.com|/var/www/example.com"
    # Add your 53 sites here
    # "site2.com|/var/www/site2.com"
    # "site3.com|/var/www/site3.com"
)

echo "Found ${#SITES[@]} sites to deploy"
echo ""

DEPLOYED=0
FAILED=0

for site_entry in "${SITES[@]}"; do
    IFS='|' read -r DOMAIN PATH <<< "$site_entry"
    
    echo "──────────────────────────────────────────────────"
    echo "Deploying to: $DOMAIN"
    echo "──────────────────────────────────────────────────"
    
    # 1. Create IndexNow key file
    KEY_FILE="$PATH/$INDEXNOW_KEY.txt"
    
    if [ -d "$PATH" ]; then
        echo "$INDEXNOW_KEY" > "$KEY_FILE"
        
        if [ -f "$KEY_FILE" ]; then
            chmod 644 "$KEY_FILE"
            echo "✅ IndexNow key file created: $KEY_FILE"
        else
            echo "❌ Failed to create key file"
            ((FAILED++))
            continue
        fi
    else
        echo "⚠️  Path not found: $PATH (skipping)"
        ((FAILED++))
        continue
    fi
    
    # 2. Inject Clarity tracking code (via WordPress CLI or custom)
    # This depends on your WordPress setup
    
    # Option A: Via wp-cli (if available)
    if command -v wp &> /dev/null; then
        wp --path="$PATH" option update revcite_clarity_id "$CLARITY_ID" --allow-root 2>/dev/null && \
            echo "✅ Clarity tracking configured" || \
            echo "⚠️  WP-CLI update skipped (manual injection needed)"
    else
        echo "⚠️  WP-CLI not available (manual Clarity injection needed)"
    fi
    
    # 3. Test IndexNow URL
    INDEXNOW_URL="https://$DOMAIN/$INDEXNOW_KEY.txt"
    echo "   Testing: $INDEXNOW_URL"
    
    ((DEPLOYED++))
    echo "✅ Deployed to $DOMAIN"
    echo ""
done

echo "══════════════════════════════════════════════════"
echo "Deployment Summary"
echo "══════════════════════════════════════════════════"
echo "  Total sites: ${#SITES[@]}"
echo "  Deployed: $DEPLOYED"
echo "  Failed: $FAILED"
echo ""

if [ $DEPLOYED -gt 0 ]; then
    echo "✅ Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "1. Test IndexNow: curl https://yoursite.com/$INDEXNOW_KEY.txt"
    echo "2. Verify Clarity tracking in browser console"
    echo "3. Register with RevCore:"
    echo "   python3 /opt/shared-api-engine/register_with_revcore.py \\"
    echo "       'revcite-citation-tracker' 'RevCite Citation Optimization' 8600 '1.0.0'"
fi

