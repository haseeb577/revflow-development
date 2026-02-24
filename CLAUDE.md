# CLAUDE.md - RevFlow OS™ Development Instructions
**Version:** 3.2.0
**Last Updated:** 2026-02-18
**For Use With:** Claude Code CLI (running directly on server)
**Server:** 217.15.168.106 (srv1078604)
**Deployment:** All 20 modules (19 Docker + 1 Virtual Composite)

---

## ⚠️ YOU ARE RUNNING DIRECTLY ON THE PRODUCTION SERVER

**You are Claude Code running directly on 217.15.168.106.**

- ✅ Execute all commands yourself
- ✅ Create/edit files directly
- ✅ Start/stop services directly
- ✅ Run scripts directly
- ❌ Do NOT create scripts "for user to run separately"
- ❌ Do NOT say "run this on your server" - YOU are on the server

---

## I. THE GOLDEN RULES

### 1. 🚨 VERIFY BEFORE MODIFY
```bash
# Run before ANY major change:
/opt/revflow-os/scripts/revflow-verify.sh --pre-check
```

### 2. 🚨 NO HARDCODING - EVER
```python
# ❌ FORBIDDEN
MODULES = ["revimage", "revpublish"]
PORTS = {"revimage": 3008}

# ✅ REQUIRED - Query from database
def get_modules():
    cursor.execute("SELECT * FROM revflow_service_registry WHERE status='deployed'")
    return cursor.fetchall()
```

### 3. 🚨 ONE NGINX CONFIG PER MODULE
- Check existing configs BEFORE creating new ones
- Run: `ls -la /etc/nginx/sites-enabled/ | wc -l`

### 4. 🚨 REACT + JSON RENDER PATTERN
- All frontends MUST use the JSON Render pattern
- NO hardcoded React components
- Schema location: `/opt/revflow-os/schemas/[module].json`

### 5. 🚨 EXECUTE DIRECTLY
- You ARE on the server - run commands yourself
- Don't ask user to run things in a separate terminal
- Complete tasks end-to-end

---

## II. SACRED FILES - ALWAYS CONSULT

| File | Location | Purpose |
|------|----------|---------|
| Service Registry | `/root/REVFLOW_SERVICE_REGISTRY.md` | All 20 modules documented |
| Deployment Rules | `/root/DEPLOYMENT_RULES.md` | Canonical procedures |
| Shared Environment | `/opt/shared-api-engine/.env` | ALL services use this |
| UI Schemas | `/opt/revflow-os/schemas/*.json` | Frontend configurations |

### Database Registry Query (Run First)
```sql
SELECT module_number, module_name, suite, port, status 
FROM revflow_service_registry 
WHERE status != 'deprecated'
ORDER BY module_number;
```

---

## III. THE 20-MODULE ARCHITECTURE (19 Docker + 1 Virtual)

### SUITE I: LEAD GENERATION (13 Modules)

#### AI-SEO/PPC Subsection (Modules 1-10)
| # | Module | Docker Port | Container | Status |
|---|--------|-------------|-----------|--------|
| 1 | RevPrompt Unified™ | 8700 | revflow-module01-revprompt | ✅ Docker |
| 2 | RevScore IQ™ | 8100 | revflow-module02-revscore | ✅ Docker |
| 3 | RevRank Engine™ | 8104 | revflow-module03-revrank | ✅ Docker |
| 4 | RevSEO Intelligence™ | 8765 | revflow-module04-revseo | ✅ Docker |
| 5 | RevCite Pro™ | 8900 | revflow-module05-revcite | ✅ Docker |
| 6 | RevHumanize™ | 8620 | revflow-module06-revhumanize | ✅ Docker |
| 7 | RevWins™ | 8150 | revflow-module07-revwins | ✅ Docker |
| 8 | RevImage Engine™ | 8610 | revflow-module08-revimage | ✅ Docker |
| 9 | RevPublish™ | 8550 | revflow-module09-revpublish | ✅ Docker |
| 10 | RevMetrics™ | 8402 | revflow-module10-revmetrics | ✅ Docker |

#### Buyer Intent Subsection (Modules 11-13)
| # | Module | Docker Port | Container | Status |
|---|--------|-------------|-----------|--------|
| 11 | RevSignal SDK™ | 8012 | revflow-module11-revsignal | ✅ Docker |
| 12 | RevIntel™ | 8011 | revflow-module12-revintel | ✅ Docker |
| 13 | RevFlow Dispatch™ | 8501 | revflow-module13-revdispatch | ✅ Docker |

### SUITE II: DIGITAL LANDLORD (2 Modules)
| # | Module | Docker Port | Container | Status |
|---|--------|-------------|-----------|--------|
| 14 | RevVest IQ™ | 8140 | revvest-iq | ✅ Docker |
| 15 | RevSPY™ | 8160 | revflow-module15-revspy | ✅ Docker |

### SUITE III: TECH EFFICIENCY (4 Modules)
| # | Module | Docker Port | Container | Status |
|---|--------|-------------|-----------|--------|
| 16 | RevSpend IQ™ | 8016 | revflow-module16-revspend | ✅ Docker |
| 17 | RevCore™ | 9000 | revflow-module17-revcore | ✅ Docker |
| 18 | RevAssist™ | 8105 | revflow-module18-revassist | ✅ Docker |
| 19 | RevRank Grid™ | 3002 | revflow-module19-revlocalgrid | ✅ Docker |

### SUITE IV: VIRTUAL COMPOSITE MODULES
| # | Module | Type | Components | Status |
|---|--------|------|------------|--------|
| 20 | RevGBP™ | Virtual | Modules 4, 5, 19 | ✅ Active |

**Module 20 (RevGBP)** combines GBP functionality from:
- Module 4 (RevSEO): GBP knowledge base, local SEO rules
- Module 5 (RevCite): Local ranking scans, geo-grid, citations
- Module 19 (RevRank Grid): Geo-grid SERP tracking, local pack

### Infrastructure (Docker)
| Service | Docker Port | Container |
|---------|-------------|-----------|
| RevCore Gateway | 8015 | revcore-gateway |
| PostgreSQL | 5433 | revflow-postgres-docker |
| Redis | 6380 | revflow-redis-docker |
| ChromaDB | 8770 | revflow-chromadb-docker |
| SurfSense Backend | 9401 | surfsense-backend |
| SurfSense Frontend | 9400 | surfsense-frontend |

---

## IV. DATABASE ARCHITECTURE

### Three-Tier System
```
PostgreSQL (localhost:5432) - Primary transactional data
ChromaDB (port 8770) - Vector DB for RAG (Modules 4, 5, 15)
JSON Files (LEGACY) - /opt/revrank_engine - Do NOT create new
```

### PostgreSQL Connection
```bash
source /opt/shared-api-engine/.env
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5432 -U $POSTGRES_USER -d revflow
```

---

## V. PORT ALLOCATION

### Reserved Ranges
- **3000-3999:** Frontend React apps
- **8000-8999:** FastAPI backend services
- **9000-9999:** Infrastructure/Security services

### Known Free Ports (verified 2026-02-17)
Available in 8000-9000 range: 8050, 8075, 8175, 8225, 8250, 8275, 8325, 8350, 8375, 8425, 8450, 8475, 8525, 8575, 8625

### Historical Port Conflict (Resolved)
**PORT 8600:** Was conflicting between Module 3 (Schema Gen) and Module 8 (RevImage)
**RESOLUTION:** Module 8 now runs on port 8610

### Before Assigning ANY New Port
```bash
# Check what's listening
netstat -tulpn | grep LISTEN | grep -E ":(8[0-9]{3}|3[0-9]{3})"

# Check database
source /opt/shared-api-engine/.env
PGPASSWORD="$POSTGRES_PASSWORD" psql -d revflow -c "SELECT module_number, port FROM revflow_service_registry ORDER BY port;"
```

---

## VI. WORKFLOW FOR ANY TASK

```
1. Read relevant docs (this file, SERVICE_REGISTRY, DEPLOYMENT_RULES)
2. Run pre-check: /opt/revflow-os/scripts/revflow-verify.sh --pre-check
3. Check existing configs (nginx, systemd) before creating new
4. EXECUTE the work directly (don't create scripts for user)
5. Test that it works (curl, systemctl status, etc.)
6. Update database registry if needed
7. Report what was done
```

---

## VII. NGINX CONFIGURATION

### Check Before Creating
```bash
# Count existing configs
ls -la /etc/nginx/sites-enabled/ | wc -l

# Search for module
grep -r "revpublish" /etc/nginx/sites-enabled/

# Test config validity
nginx -t
```

### Standard Module Pattern
```nginx
# Frontend (React + JSON Render)
location /[module-name]/ {
    alias /opt/revflow-os/modules/[module-name]/frontend/dist/;
    try_files $uri $uri/ /[module-name]/index.html;
}

# API Backend
location /api/[module-name]/ {
    proxy_pass http://localhost:[PORT]/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## VIII. SYSTEMD SERVICE PATTERN

```ini
[Unit]
Description=RevFlow [MODULE_NAME] Service
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/revflow-os/modules/[module-name]/backend
EnvironmentFile=/opt/shared-api-engine/.env
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port [PORT]
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**CRITICAL:** Always use `EnvironmentFile=/opt/shared-api-engine/.env`

---

## VIII-B. DOCKER DEPLOYMENT (PRIMARY)

All 19 modules now run in Docker containers.

### Docker Compose Files
```
/opt/revflow-os/docker-compose.modules.yml   # Master compose for all 19 modules
/opt/revflow-docker/docker-compose.yml       # Alternative compose
```

### Docker Images
- `revflow/python-base:latest` - Python/FastAPI modules (1-18)
- `revflow/node-base:latest` - Node.js modules (19)

### Common Docker Commands
```bash
# View all RevFlow containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep revflow

# Check module health
curl -s http://localhost:[PORT]/health

# View container logs
docker logs revflow-module[XX]-[name]

# Restart a container
docker restart revflow-module[XX]-[name]

# Check all module health endpoints (verified ports as of 2026-02-17)
for port in 8700 8100 8104 8765 8900 8620 8150 8610 8550 8402 8012 8011 8501 8140 8160 8016 9000 8105 3002; do
  curl -s http://localhost:$port/health | jq -r '.module // .service'
done
```

### Adding New Code to Docker
When modifying module code:
1. Code is volume-mounted from host to container
2. Changes take effect immediately (no rebuild needed for Python)
3. For Node.js, may need `docker restart` after code changes

---

## IX. REACT + JSON RENDER ARCHITECTURE

### The Pattern
- UI is driven by JSON schemas, not hardcoded React
- One generic renderer serves all modules
- New module = new schema file, not new React code
- Schema location: `/opt/revflow-os/schemas/[module].json`

### See Full Spec
`/opt/revflow-os/docs/REACT_JSON_RENDER_ARCHITECTURE.md`

---

## X. VERIFICATION SCRIPTS

Located in `/opt/revflow-os/scripts/`:

| Script | Purpose | Usage |
|--------|---------|-------|
| `revflow-verify.sh` | Pre/post checks | `--pre-check`, `--post-check`, `--status` |
| `revflow-health.sh` | Module health | `--module 9` or all modules |
| `revflow-ports.sh` | Port audit | `--conflicts`, `--check 8550` |
| `revflow-nginx.sh` | Nginx audit | `--duplicates`, `--routes` |
| `revflow-db.sh` | Database query | `--list`, `--module 9` |

---

## XI. FORBIDDEN ACTIONS

1. ❌ Hardcode module lists, ports, or configurations
2. ❌ Create new .env files (use `/opt/shared-api-engine/.env`)
3. ❌ Create nginx config without checking existing ones first
4. ❌ Create hardcoded React components (use JSON Render)
5. ❌ Use JSON files for new storage (use PostgreSQL)
6. ❌ Say "run this command" - YOU run the command
7. ❌ Create scripts "for user to execute" - YOU execute them

---

## XII. REQUIRED ACTIONS

1. ✅ Execute commands directly - you're on the server
2. ✅ Run verification before major changes
3. ✅ Query database before deployment
4. ✅ Check existing nginx configs before creating
5. ✅ Use React + JSON Render pattern
6. ✅ Update database registry after changes
7. ✅ Test that changes work before reporting success

---

## XIII. KEY PATHS

```
/opt/revflow-os/                           # Main directory
/opt/revflow-os/modules/                   # 19 modules
/opt/revflow-os/schemas/                   # UI schemas (JSON Render)
/opt/revflow-os/scripts/                   # Verification scripts
/opt/revflow-os/docker-compose.modules.yml # Docker compose for all modules
/opt/revflow-docker/                       # Docker deployment directory
/opt/shared-api-engine/.env                # SACRED - Shared environment
/opt/guru-intelligence/                    # ChromaDB location
/root/REVFLOW_SERVICE_REGISTRY.md          # Module registry docs (20 modules)
/root/DEPLOYMENT_RULES.md                  # Canonical rules
/etc/nginx/sites-enabled/                  # Nginx configs
/etc/systemd/system/                # Service files
```

---

## XIV. QUICK COMMANDS

```bash
# Docker container status (PRIMARY)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep revflow

# Count running modules
docker ps --format "{{.Names}}" | grep -E "module[0-9]|revcore" | wc -l

# Check all 19 module health endpoints (verified ports as of 2026-02-17)
for port in 8700 8100 8104 8765 8900 8620 8150 8610 8550 8402 8012 8011 8501 8140 8160 8016 9000 8105 3002; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" --connect-timeout 2)
  echo "Port $port: $status"
done

# View container logs
docker logs revflow-module[XX]-[name] --tail 50

# Restart a container
docker restart revflow-module[XX]-[name]

# Port check
netstat -tulpn | grep -E ":(8[0-9]{3}|3[0-9]{3})"

# Nginx test
nginx -t

# Database query
source /opt/shared-api-engine/.env
PGPASSWORD="$POSTGRES_PASSWORD" psql -d revflow -c "SELECT module_number, module_name, port, status FROM revflow_service_registry ORDER BY module_number;"

# Legacy systemd status (some services still use this)
systemctl list-units --type=service --state=running | grep -i rev
```

---

## XV. COMMUNICATION STYLE

When reporting progress:
- **DONE:** [what was completed]
- **VERIFIED:** [test that confirmed it works]
- **ISSUE:** [any problems found]
- **NEXT:** [what to do next, if applicable]

Do NOT say:
- "Run this command..." (you run it)
- "On your server..." (you're on the server)
- "Please execute..." (you execute)

---

**Remember: You ARE the server. Execute directly. Complete tasks end-to-end.**

## CONSUL VENV AUTO-HEALING SYSTEM
### Infrastructure
- 96 venv services monitored 24/7
- Auto-healing on corruption
- Location: http://217.15.168.106:8500/ui
### Critical: Requirements.txt must be Python-only (no system packages)

## DOCKER DEPLOYMENT STATUS (Feb 2026)
### All 20 Modules (19 Docker + 1 Virtual)
- 18 Python modules using `revflow/python-base:latest`
- 1 Node.js module (19) using `revflow/node-base:latest`
- 1 Virtual composite module (20 - RevGBP) combining Modules 4, 5, 19
- Infrastructure: PostgreSQL, Redis, ChromaDB
### Master Compose: `/opt/revflow-os/docker-compose.modules.yml`
### Module Locations:
- Modules 1-18: Various /opt directories (volume mounted)
- Module 19: `/opt/revflow-docker/modules/19-revrankgrid`
- Module 20: Virtual (uses Modules 4, 5, 19)

---

## CHANGELOG

### 2026-02-18 (v3.2.0)

#### Module 9 (RevPublish) - Animation Template Manager
- **NEW:** Animation Template Manager feature added
- **Database:** Created `animation_templates` table (626 templates)
- **Database:** Created `animation_deployments` table
- **API:** Added `/api/animation/templates` endpoints
- **API:** Added `/api/animation/deploy` endpoint
- **API:** Added `/api/animation/stats` endpoint
- **API:** Added `/api/analytics/animation-performance` endpoint
- **Frontend:** Added Animation tab to RevPublish UI schema
- **Schema:** Created `/opt/revpublish/frontend/public/schemas/revpublish-animation.json`
- **SOP:** Created `/opt/revpublish/docs/ANIMATION_MANAGER_SOP.md`
- **JSONRender:** Enhanced to support element-level data fetching (DataTableElement, StatsGridElement)

#### Module 15 (RevSPY) - Database Connection Fix
- **FIX:** Updated database connection to prefer `DATABASE_URL` environment variable
- **FIX:** Fixed password authentication issue (env_file override)
- **Database:** Created `revspy_gbp_profiles` table
- **Database:** Created `revspy_webhook_log` table
- **Files Updated:**
  - `/opt/revflow-blind-spot-research/gbp_intelligence/api.py`
  - `/opt/revflow-blind-spot-research/sov/sov_calculator.py`
  - `/opt/revflow-blind-spot-research/reports/generator.py`
  - `/opt/revflow-blind-spot-research/revspy_gbp_query_library.py`
- **Requirements:** Added `psycopg2-binary>=2.9.9` and `reportlab>=4.0.0`

#### Health Check Results (2026-02-18)
All 19 module ports verified:
- Ports 8700, 8100, 8104, 8765, 8900, 8620, 8150, 8610, 8550, 8402: OK
- Ports 8012, 8011, 8501, 8140, 8160, 8016, 9000, 8105: OK
- Port 3002 (Module 19): OK (no /health endpoint, but container healthy)
