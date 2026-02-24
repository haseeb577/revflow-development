# Database Setup Guide for RevScore IQ

## Issue: PostgreSQL Connection Error

If you see `Connection refused` error, PostgreSQL is not running or not accessible.

## Solution 1: Use Docker PostgreSQL (Recommended)

The RevFlow OS uses Docker for PostgreSQL. The container runs on port **5433** (not 5432).

### Step 1: Start Docker PostgreSQL

```bash
# From project root
cd C:\Users\LENOVO\Documents\revflow-os-config-main\revflow-os-config-main

# Start PostgreSQL container
docker-compose -f docker-compose.modules.yml up -d postgres
```

### Step 2: Verify PostgreSQL is Running

```bash
# Check if container is running
docker ps | findstr postgres

# Should show: revflow-postgres-docker
```

### Step 3: Run Setup Script

```bash
cd modules/revscore-iq/backend
python setup_db.py
```

The script now automatically uses port **5433** (Docker port).

## Solution 2: Use Local PostgreSQL

If you have PostgreSQL installed locally on port 5432:

### Step 1: Create .env file

Create `modules/revscore-iq/backend/.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=revflow
POSTGRES_USER=revflow
POSTGRES_PASSWORD=revflow2026
```

### Step 2: Ensure PostgreSQL is Running

```bash
# Windows: Check if PostgreSQL service is running
# Services app -> PostgreSQL -> Start
```

### Step 3: Run Setup Script

```bash
cd modules/revscore-iq/backend
python setup_db.py
```

## Connection Details

**Docker PostgreSQL:**
- Host: `localhost`
- Port: `5433` (mapped from container port 5432)
- Database: `revflow`
- User: `revflow`
- Password: `revflow2026`

**Local PostgreSQL:**
- Host: `localhost`
- Port: `5432`
- Database: `revflow`
- User: `revflow` (or your local user)
- Password: `revflow2026` (or your local password)

## Environment Variables

The setup script reads from environment variables (in order of priority):

1. `.env` file in `backend/` directory
2. `.env` file in `modules/revscore-iq/` directory
3. `.env` file in project root
4. System environment variables
5. Default values (Docker settings)

## Troubleshooting

### Error: Connection refused
- **Docker**: Run `docker-compose -f docker-compose.modules.yml up -d postgres`
- **Local**: Start PostgreSQL service

### Error: Authentication failed
- Check `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`
- Default Docker credentials: `revflow` / `revflow2026`

### Error: Database does not exist
- Create database: `CREATE DATABASE revflow;`
- Or let the script create it (if user has permissions)

## Quick Test

Test database connection:

```bash
python -c "from setup_db import DATABASE_URL; from sqlalchemy import create_engine; engine = create_engine(DATABASE_URL); conn = engine.connect(); print('✅ Connected!'); conn.close()"
```

