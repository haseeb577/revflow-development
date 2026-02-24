#!/bin/bash

# RevFlow Enrichment Service - Quick Start Script
# This script automates the setup and deployment process

set -e  # Exit on error

echo "=================================================="
echo "RevFlow Enrichment Service - Quick Start"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Don't run this script as root${NC}"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env and add your API keys before continuing${NC}"
    echo ""
    read -p "Press Enter to edit .env now, or Ctrl+C to exit and edit manually..."
    ${EDITOR:-nano} .env
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check if Docker is available
echo ""
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker found${NC}"
    DOCKER_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Docker not found (optional)${NC}"
    DOCKER_AVAILABLE=false
fi

# Ask deployment method
echo ""
echo "=================================================="
echo "Choose deployment method:"
echo "=================================================="
echo "1. Python (Development - run in foreground)"
echo "2. Python (Background - using nohup)"
echo "3. Docker Compose (Recommended for production)"
echo "4. Skip deployment (just setup)"
echo ""
read -p "Enter choice [1-4]: " DEPLOY_CHOICE

case $DEPLOY_CHOICE in
    1)
        echo ""
        echo "Starting service in development mode..."
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        uvicorn main:app --reload --host 0.0.0.0 --port 8500
        ;;
    2)
        echo ""
        echo "Starting service in background..."
        nohup uvicorn main:app --host 0.0.0.0 --port 8500 --workers 4 > enrichment.log 2>&1 &
        PID=$!
        echo -e "${GREEN}✓ Service started with PID: $PID${NC}"
        echo "View logs: tail -f enrichment.log"
        echo "Stop service: kill $PID"
        ;;
    3)
        if [ "$DOCKER_AVAILABLE" = false ]; then
            echo -e "${RED}❌ Docker not available${NC}"
            exit 1
        fi
        echo ""
        echo "Starting with Docker Compose..."
        docker-compose up -d
        echo -e "${GREEN}✓ Service started with Docker${NC}"
        echo "View logs: docker-compose logs -f"
        echo "Stop service: docker-compose down"
        ;;
    4)
        echo ""
        echo -e "${GREEN}✓ Setup complete (no deployment)${NC}"
        echo ""
        echo "To start manually:"
        echo "  source venv/bin/activate"
        echo "  uvicorn main:app --host 0.0.0.0 --port 8500"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac

# Wait for service to start
echo ""
echo "Waiting for service to start..."
sleep 5

# Health check
echo ""
echo "Testing health endpoint..."
if curl -f http://localhost:8500/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Service is healthy!${NC}"
else
    echo -e "${RED}❌ Service health check failed${NC}"
    echo "Check logs for errors"
    exit 1
fi

# Test email endpoint
echo ""
echo "Testing email enrichment endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8500/api/v1/enrich/email \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "company_domain": "example.com"
  }')

if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ Email endpoint working${NC}"
else
    echo -e "${YELLOW}⚠️  Email endpoint returned response but may need API keys configured${NC}"
fi

# Show summary
echo ""
echo "=================================================="
echo "🎉 RevFlow Enrichment Service - Ready!"
echo "=================================================="
echo ""
echo "Service URL: http://localhost:8500"
echo "API Docs: http://localhost:8500/docs"
echo "Health Check: http://localhost:8500/health"
echo ""
echo "Next steps:"
echo "1. Configure API keys in .env file"
echo "2. Test endpoints with: python test_endpoints.py"
echo "3. View API documentation at /docs"
echo "4. Integrate with backend (see DEPLOYMENT.md)"
echo ""
echo "Cost Tracking:"
echo "  View costs: curl http://217.15.168.106:5000/api/v1/costs/summary"
echo ""
echo "Support:"
echo "  README.md - Full documentation"
echo "  DEPLOYMENT.md - Deployment guide"
echo "  test_endpoints.py - Test all endpoints"
echo ""
echo "=================================================="
