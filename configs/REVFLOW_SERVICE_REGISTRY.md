# REVFLOW SERVICE REGISTRY
**Last Updated:** 2026-02-02
**Server:** 217.15.168.106 (srv1078604)

---

## REVFLOW OS DASHBOARD

### Main Dashboard
- **URL:** http://217.15.168.106:3000/
- **Location:** /opt/revflow-os/frontend/
- **Technology:** React + Vite + TypeScript
- **Nginx Config:** /etc/nginx/sites-available/revflow-os

### Level 2 Dashboard (AI-SEO/PPC Pipeline)
- **URL:** http://217.15.168.106:3000/level2
- **Features:**
  - 10-module step-by-step pipeline
  - 30 sub-module actions with real API integrations
  - Progress tracking (module and overall)
  - Locked features panel for Level 3/4 access
- **File:** /opt/revflow-os/frontend/src/Level2Dashboard.tsx

### API Proxy Configuration (Port 3000)
| API Route | Backend Port | Service |
|-----------|--------------|---------|
| /api/revprompt/ | 8401 | RevPrompt/Power Prompts |
| /api/revscore/ | 8100 | RevScore IQ |
| /api/revrank/ | 8103 | RevRank Engine |
| /api/revseo/ | 8765 | RevSEO Intelligence |
| /api/revcite/ | 8900 | RevCite Pro |
| /api/revhumanize/ | 8610 | RevHumanize (via RevImage) |
| /api/revwins/ | 8150 | RevWins |
| /api/revimage/ | 8610 | RevImage Engine |
| /api/revpublish/ | 8550 | RevPublish |
| /api/revmetrics/ | 8220 | RevMetrics |
| /api/revsignal/ | 8006 | RevSignal SDK |
| /api/revintel/ | 8011 | RevIntel |
| /api/revspy/ | 8160 | RevSPY |
| /api/revcore/ | 9000 | RevCore |
| /api/revassist/ | 8105 | RevAssist |

---

## SUITE I: LEAD GENERATION (Modules 1-13)

### Module 1: RevPrompt Unified™
- **Brand Name:** RevPrompt Unified™
- **Ports:** 8700 (planned), 8401 (active via RevRank)
- **Status:** Deployed (via RevRank integration)
- **Backend:** /opt/revflow-power-prompts
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - GET /api/revrank/prompts/ - List prompts
  - POST /api/revrank/prompts/render - Render template
  - GET /api/revrank/rules/content-generation - Content rules

### Module 2: RevScore IQ™
- **Brand Name:** RevScore IQ™
- **Ports:** 8100 (main), 8500, 8501
- **Status:** Deployed
- **Backend:** /opt/revscore_iq
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - POST /api/revscore/run-assessment - Score content
  - GET /api/revscore/health - Service health
  - GET /api/revscore/memory/get - Assessment history

### Module 3: RevRank Engine™
- **Brand Name:** RevRank Engine™
- **Ports:** 8103 (main), 8201, 8220, 8299, 8600, 8800
- **Status:** Deployed
- **Backend:** /opt/revrank_engine
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - POST /api/revrank/analyze - SERP analysis
  - GET /api/revrank/prompts/ - Prompt library
  - GET /api/revrank/knowledge/rules - SEO rules
  - GET /api/revrank/scoring/frameworks - Scoring frameworks

### Module 4: RevSEO Intelligence™
- **Brand Name:** RevSEO Intelligence™
- **Ports:** 8765 (main), 8300, 8766, 8770 (ChromaDB)
- **Status:** Deployed
- **Backend:** /opt/guru-intelligence
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - POST /api/revseo/search - Knowledge base search
  - GET /api/revseo/collections - View collections
  - GET /api/revseo/health - Service health

### Module 5: RevCite Pro™
- **Brand Name:** RevCite Pro™
- **Ports:** 8900 (main), 8901, 8902, 8903
- **Status:** Deployed
- **Backend:** /opt/revflow-citations
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - POST /api/revcite/api/ranking-scan - Local ranking scan
  - POST /api/revcite/api/geocode - Geocode address
  - GET /api/revcite/api/ranking-scan/history/{name} - Scan history

### Module 6: RevHumanize™
- **Brand Name:** RevHumanize™
- **Ports:** N/A (integrated with RevScore/RevImage)
- **Status:** Deployed (via integration)
- **Backend:** /opt/revflow-humanization-pipeline
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints (via RevScore):**
  - POST /api/revscore/run-assessment - Content assessment
  - GET /api/revscore/memory/get - Assessment history

### Module 7: RevWins™
- **Brand Name:** RevWins™
- **Ports:** 8150 (inactive)
- **Status:** Deployed (via RevRank integration)
- **Backend:** /opt/quick-wins-api
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints (via RevRank):**
  - POST /api/revrank/knowledge/assess - Knowledge assessment
  - GET /api/revrank/knowledge/rules - SEO rules
  - GET /api/revrank/scoring/frameworks - Scoring frameworks

### Module 8: RevImage Engine™
- **Brand Name:** RevImage Engine™
- **Ports:** 8610 (main), 8601
- **Status:** Deployed
- **Backend:** /opt/revimage-engine
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - GET /api/revimage/api/v1/sites - List sites
  - POST /api/revimage/api/v1/batch/generate - Batch generation
  - GET /api/revimage/health - Service health

### Module 9: RevPublish™
- **Brand Name:** RevPublish™
- **Ports:** 8550 (backend), 3550 (frontend)
- **Status:** Partial
- **Backend:** /opt/revflow-os/modules/revpublish/backend
- **Frontend:** /opt/revpublish/frontend
- **Dashboard Access:** https://automation.smarketsherpa.ai/revflow_os/revpublish/
- **Features:**
  - WordPress site connection
  - Content queue management
  - Auto-deploy to WordPress

### Module 10: RevMetrics™
- **Brand Name:** RevMetrics™
- **Ports:** 8220 (API), 8401, 8402, 3400 (frontend)
- **Status:** Partial
- **Backend:** /opt/revflow-os/modules/revmetrics
- **Dashboard Access:** http://217.15.168.106:3000/level2
- **API Endpoints:**
  - GET /api/revmetrics/dashboard/kpis - Dashboard KPIs
  - GET /api/revmetrics/stats - System statistics
  - GET /api/revmetrics/customers - Customer data

### Module 11: RevSignal SDK™
- **Brand Name:** RevSignal SDK™
- **Ports:** 8006
- **Status:** Deployed
- **Backend:** /opt/visitor-identification-service
- **Dashboard Access:** Module dashboard via schemas

### Module 12: RevIntel™
- **Brand Name:** RevIntel™
- **Ports:** 8011
- **Status:** Deployed
- **Backend:** /opt/revflow-enrichment-service

### Module 13: RevFlow Dispatch™
- **Brand Name:** RevFlow Dispatch™
- **Ports:** Webhook-based
- **Status:** Deployed
- **Backend:** /opt/smarketsherpa-rr-automation

---

## SUITE II: DIGITAL LANDLORD (Modules 14-15)

### Module 14: RevVest IQ™
- **Brand Name:** RevVest IQ™
- **Ports:** 3013 (reserved)
- **Status:** Planned
- **Schema:** /opt/revflow-os/frontend/public/schemas/revvest.json

### Module 15: RevSPY™
- **Brand Name:** RevSPY™
- **Ports:** 8160, 8162
- **Status:** Deployed
- **Backend:** /opt/revflow-blind-spot-research

---

## SUITE III: TECH EFFICIENCY (Modules 16-18)

### Module 16: RevSpend IQ™
- **Brand Name:** RevSpend IQ™
- **Ports:** TBD
- **Status:** Planned
- **Schema:** /opt/revflow-os/frontend/public/schemas/revspend.json

### Module 17: RevCore™
- **Brand Name:** RevCore™
- **Ports:** 8766, 9000
- **Status:** Deployed
- **Backend:** /opt/shared-api-engine

### Module 18: RevAssist™
- **Brand Name:** RevAssist™
- **Ports:** 8105
- **Status:** Deployed
- **Backend:** /var/www/revhome_assessment_engine_v2

---

## R2S TRACKING SYSTEM

**Revenue-to-Spend Lead Tracking Integration**

### Database Tables
- `r2s_tracking` - Main tracking metrics
- `r2s_weekly_snapshots` - Historical trends
- `r2s_budget_alerts` - Budget alerts and throttling
- `r2s_winning_prompts` - Prompt performance tracking

### Playbooks
- `/opt/revflow-os/playbooks/R2S_END_TO_END_PLAYBOOK.md`

### SOPs
- `/opt/revflow-os/sops/WEEKLY_HIGH_GROWTH_CYCLE.md`

### Module Integration
- **Module 1 (RevPrompt):** Prompt template variations
- **Module 2 (RevScore IQ):** 100-prompt batching, AI mention rate
- **Module 4 (RevSEO):** RAG data injection for prompts
- **Module 10 (RevMetrics):** R2S dashboard and visualization
- **Module 11 (RevSignal SDK):** Visitor identification
- **Module 12 (RevIntel):** Lead enrichment and pipeline value
- **Module 13 (RevFlow Dispatch):** High-intent lead routing
- **Module 16 (RevSpend IQ):** Budget monitoring and alerts

### Key Metrics
- **AI Mention Rate:** % of prompts where brand is recommended
- **R2S Ratio:** Pipeline Value / AI Spend (target: >200)
- **Aggregate Spend:** Total AI infrastructure cost
- **Pipeline Value:** Identified leads × average deal size

### Alert Thresholds
- R2S < 5: CRITICAL - Stop spend
- R2S 5-10: HIGH - Throttle to 50%
- R2S 10-20: MEDIUM - Monitor
- R2S > 20: LOW - Continue

### Weekly Cycle
- **Monday:** Visibility Audit (100-prompt batch)
- **Wednesday:** Content Sync (deployment verification)
- **Friday:** Revenue Review (R2S analysis)

---

## LEVEL 2 DASHBOARD - SUB-MODULE ACTIONS

### Module 1: RevPrompt
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 1.1 | View Prompts | /api/revrank/prompts/ | GET |
| 1.2 | Render Template | /api/revrank/prompts/render | POST |
| 1.3 | Content Rules | /api/revrank/rules/content-generation | GET |

### Module 2: RevScore
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 2.1 | Scoring Rules | /api/revscore/rules | POST |
| 2.2 | Score Content | /api/revscore/run-assessment | POST |
| 2.3 | Quality Thresholds | /api/revscore/thresholds | POST |

### Module 3: RevRank
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 3.1 | Keyword Mapping | /api/revrank/keywords | POST |
| 3.2 | SERP Analysis | /api/revrank/analyze | POST |
| 3.3 | Rank Tracking | /api/revrank/tracking | POST |

### Module 4: RevSEO
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 4.1 | Search Knowledge | /api/revseo/search | POST |
| 4.2 | View Collections | /api/revseo/collections | GET |
| 4.3 | Service Health | /api/revseo/health | GET |

### Module 5: RevCite
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 5.1 | Ranking Scan | /api/revcite/api/ranking-scan | POST |
| 5.2 | Geocode Location | /api/revcite/api/geocode | POST |
| 5.3 | Scan History | /api/revcite/api/ranking-scan/history | GET |

### Module 6: RevHumanize
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 6.1 | Voice Rules | /api/revrank/rules/content-generation | GET |
| 6.2 | Content Assessment | /api/revscore/run-assessment | POST |
| 6.3 | Assessment History | /api/revscore/memory/get | GET |

### Module 7: RevWins
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 7.1 | Knowledge Assessment | /api/revrank/knowledge/assess | POST |
| 7.2 | View Rules | /api/revrank/knowledge/rules | GET |
| 7.3 | Scoring Frameworks | /api/revrank/scoring/frameworks | GET |

### Module 8: RevImage
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 8.1 | View Sites | /api/revimage/api/v1/sites | GET |
| 8.2 | Batch Generate | /api/revimage/api/v1/batch/generate | POST |
| 8.3 | Service Health | /api/revimage/health | GET |

### Module 9: RevPublish
| Step | Action | External URL |
|------|--------|--------------|
| 9.1 | Connect Sites | https://automation.smarketsherpa.ai/revflow_os/revpublish/#sites |
| 9.2 | Content Queue | https://automation.smarketsherpa.ai/revflow_os/revpublish/#queue |
| 9.3 | Deploy Content | https://automation.smarketsherpa.ai/revflow_os/revpublish/#deploy |

### Module 10: RevMetrics
| Step | Action | Endpoint | Method |
|------|--------|----------|--------|
| 10.1 | Dashboard KPIs | /api/revmetrics/dashboard/kpis | GET |
| 10.2 | View Statistics | /api/revmetrics/stats | GET |
| 10.3 | View Customers | /api/revmetrics/customers | GET |

---

## KEY FILES

| File | Purpose |
|------|---------|
| /opt/revflow-os/frontend/src/App.tsx | Main dashboard router |
| /opt/revflow-os/frontend/src/Level2Dashboard.tsx | Level 2 pipeline UI |
| /etc/nginx/sites-available/revflow-os | Nginx proxy config |
| /opt/revflow-os/frontend/public/schemas/*.json | Module UI schemas |
| /opt/revflow-os/frontend/public/api/platform/modules | Module data JSON |
| /opt/shared-api-engine/.env | Shared environment |

---

## DATABASE TABLES

- `revflow_service_registry` - Module registry with ports, status, URLs
- `r2s_tracking` - R2S tracking metrics
- `r2s_weekly_snapshots` - Historical trends
- `r2s_budget_alerts` - Budget alerts

---

**Document Version:** 2.0.0
**Last Health Check:** 2026-02-02

---

## TESTING CAPABILITY: RevScore IQ Testing Suite

**Official Name:** RevScore IQ Testing Suite  
**Type:** Testing & Monitoring Capability  
**Status:** ✅ Deployed  
**Location:** /opt/revflow-testing/revscore-iq  
**CLI Commands:** revscore-test, revscore-health, revscore-assess  
**Service:** revscore-health-check.timer (systemd)  
**Configuration:** /etc/revflow/testing/revscore.json  
**Results:** /var/revflow/testing/results  
**Logs:** /var/log/revflow/testing  
**Dependencies:** Module 2 (RevScore IQ™)

**Purpose & Functionality:**
Permanent testing and monitoring capability for RevScore IQ™ (Module 2). Provides automated health checks, endpoint discovery, full assessments, and module verification.

**Key Features:**
- **Health Monitoring:**
  - Service availability checks
  - Endpoint discovery
  - API response validation
  - RevCore integration verification

- **Assessment Testing:**
  - Full 5-stage pipeline testing
  - All 22 module verification
  - P0-P3 classification validation
  - Report generation testing

- **Automation:**
  - Hourly health checks (systemd timer)
  - Daily health summaries (cron)
  - Configurable schedules
  - Automatic result archival

- **CLI Interface:**
  - revscore-test: Main testing framework
  - revscore-health: Quick health check
  - revscore-assess: Quick assessment
  - Full command-line control

**Technical Details:**
- Python 3 based framework
- JSON configuration system
- Automated result storage
- Comprehensive logging
- systemd integration
- cron job support

**CLI Commands:**
```bash
# Health check
revscore-health

# Endpoint discovery
revscore-test discover

# Run assessment
revscore-assess https://example.com

# Full test suite
revscore-test full --url https://example.com

# Custom options
revscore-test assess --url URL --industry INDUSTRY --location LOCATION
```

**Automation:**
```bash
# Enable hourly health checks
systemctl enable revscore-health-check.timer
systemctl start revscore-health-check.timer

# View timer status
systemctl status revscore-health-check.timer

# View logs
tail -f /var/log/revflow/testing/health-check.log
```

**Configuration:**
Location: `/etc/revflow/testing/revscore.json`
```json
{
  "base_url": "http://localhost:8100",
  "revcore_url": "http://localhost:8950",
  "timeout": 300,
  "save_reports": true,
  "default_industry": "home_services",
  "default_location": "UK"
}
```

**Results & Logs:**
- Test Results: `/var/revflow/testing/results/`
- Health Logs: `/var/log/revflow/testing/health-check.log`
- Daily Logs: `/var/log/revflow/testing/daily-health.log`

**Integration Points:**
- Module 2 (RevScore IQ™): Primary testing target
- Module 17 (RevCore™): Integration verification
- PostgreSQL: Result storage (optional)

**Installation:**
```bash
./install_revscore_testing_20260202_130000.sh
```

**Uninstallation:**
```bash
./uninstall_revscore_testing_20260202_130000.sh
```

**Documentation:**
- Installation Guide: /opt/revflow-testing/revscore-iq/README.md
- Usage Guide: RevScore_Testing_Usage_Guide_20260202_130000.md
- Configuration: /etc/revflow/testing/revscore.json

**Use Cases:**
1. **Development Testing:** Validate RevScore IQ functionality during development
2. **Health Monitoring:** Automated service health checks
3. **QA Testing:** Comprehensive end-to-end testing
4. **Performance Monitoring:** Track API response times
5. **Integration Testing:** Verify RevCore routing
6. **Regression Testing:** Ensure updates don't break functionality
7. **Baseline Establishment:** Create performance baselines
8. **Incident Response:** Quick diagnostics during issues

**Maintenance:**
- Automated health checks run hourly
- Daily summaries at 2 AM
- Results auto-archived
- Logs auto-rotated
- No manual intervention required

