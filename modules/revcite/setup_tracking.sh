#!/bin/bash

echo "========================================="
echo "RevCite: Citation Tracking Setup"
echo "========================================="
echo ""

# Generate IndexNow key
INDEXNOW_KEY=$(openssl rand -hex 32)

echo "✅ Generated IndexNow Key: $INDEXNOW_KEY"
echo ""

# Update config
CONFIG_FILE="/opt/revcite/config/tracking_config.json"

if [ -f "$CONFIG_FILE" ]; then
    # Update the key in config
    sed -i "s/REPLACE_WITH_GENERATED_KEY/$INDEXNOW_KEY/g" "$CONFIG_FILE"
    echo "✅ Updated config file: $CONFIG_FILE"
fi

echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Get Clarity Project ID:"
echo "   → Go to https://clarity.microsoft.com/"
echo "   → Create a project"
echo "   → Copy the Project ID"
echo ""
echo "2. Update config file:"
echo "   nano $CONFIG_FILE"
echo "   → Replace REPLACE_WITH_YOUR_CLARITY_PROJECT_ID with actual ID"
echo "   → Update default_host with your domain"
echo ""
echo "3. Create IndexNow key files on WordPress sites:"
echo "   For each site, create: https://yoursite.com/$INDEXNOW_KEY.txt"
echo "   File content: $INDEXNOW_KEY"
echo ""
echo "4. Register with RevCore:"
echo "   python3 /opt/shared-api-engine/register_with_revcore.py \\"
echo "       'revcite-citation-tracker' \\"
echo "       'RevCite Citation Optimization' \\"
echo "       8600 \\"
echo "       '1.0.0'"
echo ""
