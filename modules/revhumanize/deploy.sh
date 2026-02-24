#!/bin/bash
set -e

echo "🚀 Starting Deployment with Guardrails..."
echo ""

# Run validation first
./pre_deploy_validation.sh || exit 1

echo ""
echo "🔧 Building and deploying..."
docker-compose down
docker-compose up --build -d

echo ""
echo "⏳ Waiting for startup..."
sleep 10

echo ""
echo "🧪 Running health check..."
curl -sf http://localhost:8003/health || {
    echo "❌ HEALTH CHECK FAILED"
    docker logs revflow-humanization-pipeline --tail 50
    exit 1
}

echo ""
echo "✅ DEPLOYMENT SUCCESSFUL"
