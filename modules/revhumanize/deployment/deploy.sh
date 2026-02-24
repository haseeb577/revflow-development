#!/bin/bash
# RevFlow Humanization Pipeline - Deployment Script for Ubuntu Server 217.15.168.106

set -e

echo "🚀 RevFlow Humanization Pipeline Deployment"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP="217.15.168.106"
DEPLOY_DIR="/opt/revflow-humanization-pipeline"
SERVICE_PORT="8003"

echo -e "${YELLOW}📦 Step 1: Checking prerequisites...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose not found. Installing...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

echo -e "${YELLOW}📁 Step 2: Setting up deployment directory...${NC}"

# Create deployment directory
sudo mkdir -p $DEPLOY_DIR
sudo chown $USER:$USER $DEPLOY_DIR

# Copy files to deployment directory
echo -e "${YELLOW}Copying application files...${NC}"
cp -r . $DEPLOY_DIR/

cd $DEPLOY_DIR

echo -e "${GREEN}✓ Files copied to $DEPLOY_DIR${NC}"

echo -e "${YELLOW}⚙️  Step 3: Configuring environment...${NC}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your configuration${NC}"
    echo -e "${YELLOW}   Example: nano .env${NC}"
    read -p "Press enter to continue after editing .env..."
fi

echo -e "${GREEN}✓ Environment configured${NC}"

echo -e "${YELLOW}🐳 Step 4: Building Docker containers...${NC}"

# Build containers
docker-compose build

echo -e "${GREEN}✓ Containers built${NC}"

echo -e "${YELLOW}🚀 Step 5: Starting services...${NC}"

# Start services
docker-compose up -d

echo -e "${GREEN}✓ Services started${NC}"

echo -e "${YELLOW}⏳ Step 6: Waiting for services to be ready...${NC}"

# Wait for service to be healthy
sleep 10

# Check if service is running
if curl -f http://localhost:$SERVICE_PORT/health &> /dev/null; then
    echo -e "${GREEN}✓ Service is healthy and running${NC}"
else
    echo -e "${RED}✗ Service health check failed${NC}"
    docker-compose logs
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service Information:"
echo "  • API URL: http://$SERVER_IP:$SERVICE_PORT"
echo "  • Health Check: http://$SERVER_IP:$SERVICE_PORT/health"
echo "  • API Docs: http://$SERVER_IP:$SERVICE_PORT/docs"
echo ""
echo "Useful Commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop service: docker-compose down"
echo "  • Restart service: docker-compose restart"
echo "  • View status: docker-compose ps"
echo ""
echo "Test the service:"
echo "  curl http://localhost:$SERVICE_PORT/health"
echo ""
echo -e "${YELLOW}Don't forget to configure your .env file!${NC}"
