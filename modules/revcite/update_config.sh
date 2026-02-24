#!/bin/bash

echo "RevCite Configuration Updater"
echo "=============================="
echo ""

# Prompt for Clarity ID
read -p "Enter Clarity Project ID: " CLARITY_ID

if [ -z "$CLARITY_ID" ]; then
    echo "❌ Clarity ID is required"
    exit 1
fi

# Prompt for domain
read -p "Enter your main domain (e.g., example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ Domain is required"
    exit 1
fi

CONFIG_FILE="/opt/revcite/config/tracking_config.json"

# Update config
sed -i "s/REPLACE_WITH_YOUR_CLARITY_PROJECT_ID/$CLARITY_ID/g" "$CONFIG_FILE"
sed -i "s/example.com/$DOMAIN/g" "$CONFIG_FILE"

echo ""
echo "✅ Configuration updated!"
echo ""
echo "Current config:"
cat "$CONFIG_FILE"
echo ""
echo "Next: Test the integration"
echo "  python3 /opt/revcite/test_integrations.py"

