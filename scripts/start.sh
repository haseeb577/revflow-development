#!/bin/bash
export $(cat /opt/shared-api-engine/.env | xargs)
cd /opt/revflow-os
echo "🚀 Starting RevFlow OS"
if [ -f config/docker-compose.yml ]; then
    docker-compose -f config/docker-compose.yml up -d
    echo "✅ Services started"
else
    echo "⚠️  docker-compose.yml not created yet"
fi
