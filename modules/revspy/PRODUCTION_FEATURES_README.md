# RevSPY™ GBP Intelligence - Production Features

## Deployed Components

### 1. Report Generator (`/reports/`)
**Location:** `/opt/revflow-blind-spot-research/reports/`

**Purpose:** Automated competitive analysis report generation

**Features:**
- Prospect competitive analysis
- Monthly client progress reports
- Market opportunity briefings
- Competitive benchmark tracking

**Usage:**
```python
from reports.generator import ReportGenerator

generator = ReportGenerator()

# Generate prospect report
report = generator.generate_prospect_report(
    prospect_place_id="ChIJ...",
    market="electrician chicago"
)

# Generate monthly client report
report = generator.generate_monthly_client_report(
    client_place_id="ChIJ...",
    market="electrician chicago"
)
```

**API Endpoints:**
```bash
# Generate prospect report
POST /api/v1/revspy/reports/prospect
{
  "place_id": "ChIJ...",
  "market": "electrician chicago"
}

# Generate monthly client report
POST /api/v1/revspy/reports/client/monthly
{
  "place_id": "ChIJ...",
  "market": "electrician chicago"
}

# Get market summary
GET /api/v1/revspy/reports/markets/{market}/summary
```

### 2. Module 2 (RevScore IQ) Integration
**Location:** `/opt/revflow-assessment/integrations/`

**Purpose:** Cross-reference GBP data with assessment scores

**Features:**
- GBP benchmark retrieval
- Market position analysis
- Assessment enrichment with competitive data

**API Endpoints:**
```bash
# Get GBP benchmark
GET /api/v1/revscore/gbp/benchmark/{place_id}

# Get market position
GET /api/v1/revscore/gbp/position/{place_id}
```

### 3. UI Components (JSON Render)
**Location:** `/opt/revflow-os/schemas/revspy/`

**Purpose:** Dynamic UI generation for RevSPY features

**Components:**
- `market_intelligence_dashboard.json` - Main dashboard
- `competitive_analysis_generator.json` - Report generation form
- `navigation.json` - Menu integration

**Usage:**
The RevFlow UI automatically loads these schemas and renders components dynamically.

## Testing

### Test Report Generation
```bash
cd /opt/revflow-blind-spot-research
source venv/bin/activate
python3 -c "
from reports.generator import ReportGenerator
generator = ReportGenerator()
print('Report generator ready')
"
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8160/health

# List markets
curl http://localhost:8160/api/v1/revspy/gbp/markets

# Get market summary
curl http://localhost:8160/api/v1/revspy/reports/markets/electrician%20chicago/summary
```

### Test UI Schemas
```bash
# View dashboard schema
cat /opt/revflow-os/schemas/revspy/market_intelligence_dashboard.json | jq .
```

## Next Steps

1. **Populate with real data:**
   - Configure GMB Everywhere webhook
   - Ingest competitor data for your markets

2. **Generate first reports:**
   - Use API endpoints or UI
   - Test prospect and client reports

3. **Integrate with sales process:**
   - Use reports in outreach emails
   - Track client progress monthly

4. **Expand UI:**
   - Add custom visualizations
   - Build client portal

## Support

- **Report Generator:** `/opt/revflow-blind-spot-research/reports/`
- **API Docs:** `http://localhost:8160/docs`
- **Logs:** `/var/log/revspy.log`
- **Service:** `systemctl status revspy.service`
