# RevFlow OS Infrastructure Fix Plan

## Current State (BROKEN)
- 149 systemd service files
- 96+ Python virtual environments
- 159 corrupted venv directories
- Constant service failures and auto-restart loops
- No dependency locking
- Venvs constantly being rebuilt

## Root Cause
Each service has its own venv that can get corrupted independently.
Auto-healing rebuilds venvs but doesn't fix the underlying issues:
1. Package version conflicts
2. Pip install race conditions
3. Disk I/O during concurrent installs
4. No locked dependencies

## Solution: Docker Compose Stack

### Phase 1: Core Services (Week 1)
Containerize the critical path:
- revcore-gateway (API gateway)
- revpublish (content publishing)
- revaudit-v6 (anti-hallucination)
- revscore-iq (scoring)

### Phase 2: Module Groups (Week 2-3)
Group related services into containers:
- Lead Gen Suite (modules 1-10)
- Buyer Intent Suite (modules 11-13)
- Digital Landlord Suite (modules 14-15)
- Tech Efficiency Suite (modules 16-18)

### Phase 3: Cleanup (Week 4)
- Remove redundant systemd services
- Clean up corrupted venvs
- Consolidate to single docker-compose.yml

## Immediate Actions (Today)

### 1. Fix Current Failures
```bash
# Fix revflow-revwins
systemctl restart revflow-revwins.service

# Stop revaudit restart loop
systemctl stop revaudit.service
systemctl disable revaudit.service  # v5 deprecated, use v6
```

### 2. Create Shared Venv for Critical Services
```bash
# One venv for all FastAPI services
python3 -m venv /opt/revflow-os/shared-venv
source /opt/revflow-os/shared-venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic pydantic-settings requests beautifulsoup4
pip freeze > /opt/revflow-os/requirements.locked.txt
```

### 3. Update Critical Services to Use Shared Venv
Update systemd ExecStart to use /opt/revflow-os/shared-venv/bin/python

## Docker Compose Template

```yaml
version: '3.8'

services:
  revcore-gateway:
    build: ./modules/revcore
    ports:
      - "8004:8004"
    env_file:
      - /opt/shared-api-engine/.env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  revpublish:
    build: ./modules/revpublish
    ports:
      - "8550:8550"
    env_file:
      - /opt/shared-api-engine/.env
    depends_on:
      - revcore-gateway
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8550/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Add other services...
```

## Benefits of Docker Approach

1. **Immutable images** - No venv corruption
2. **Locked dependencies** - requirements.txt baked into image
3. **Easy rollback** - Just use previous image tag
4. **Health checks** - Built-in with proper recovery
5. **Resource limits** - Memory/CPU constraints per service
6. **Single source of truth** - docker-compose.yml

## Recommended Timeline

| Week | Action |
|------|--------|
| 1 | Containerize 4 core services |
| 2 | Migrate remaining services to containers |
| 3 | Testing and validation |
| 4 | Cleanup old systemd services and venvs |

## Quick Win (Immediate)

For now, reduce service count by:
1. Disable deprecated services (revaudit v5)
2. Consolidate duplicate venvs
3. Create one shared venv for all FastAPI services
4. Lock all dependencies with pip freeze
