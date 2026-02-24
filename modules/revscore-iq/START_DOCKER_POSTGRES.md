# How to Start Docker PostgreSQL

## Quick Start

The PostgreSQL database needs to be running before you can run the setup script.

### Step 1: Start Docker PostgreSQL

Open PowerShell or Command Prompt in the project root:

```powershell
# Navigate to project root
cd C:\Users\LENOVO\Documents\revflow-os-config-main\revflow-os-config-main

# Start PostgreSQL container
docker-compose -f docker-compose.modules.yml up -d postgres
```

### Step 2: Verify PostgreSQL is Running

```powershell
# Check if container is running
docker ps | findstr postgres

# Should show: revflow-postgres-docker
```

### Step 3: Run Database Setup

```powershell
# Run setup script
python modules\revscore-iq\backend\setup_db.py
```

## Alternative: Check if PostgreSQL is Already Running

If you're not sure if PostgreSQL is running:

```powershell
# Check Docker containers
docker ps -a | findstr postgres

# If container exists but is stopped, start it:
docker start revflow-postgres-docker

# If container doesn't exist, create it:
docker-compose -f docker-compose.modules.yml up -d postgres
```

## Troubleshooting

### Docker is not installed
- Install Docker Desktop for Windows
- Download from: https://www.docker.com/products/docker-desktop

### Docker is not running
- Start Docker Desktop application
- Wait for it to fully start (whale icon in system tray)

### Port 5433 is already in use
- Check what's using the port: `netstat -ano | findstr :5433`
- Stop the conflicting service or change Docker port mapping

### Connection still fails
- Check Docker logs: `docker logs revflow-postgres-docker`
- Verify container is healthy: `docker ps` (should show "healthy" status)

