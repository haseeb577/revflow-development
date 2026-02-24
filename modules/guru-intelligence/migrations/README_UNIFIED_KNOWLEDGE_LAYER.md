# Guru Intelligence - Unified Knowledge Layer

**Version:** 1.0  
**Date:** December 28, 2025  
**Status:** Ready for Deployment

---

## Executive Summary

The **Unified Knowledge Layer** transforms Guru Intelligence from a basic rule checker into a comprehensive knowledge management and validation platform serving all SmarketSherpa modules.

### What Changed

**Before (8 Rules):**
```python
# Only 8 hardcoded checks
if word_count < 40: fail
if "we are" in content: fail  
# ... 6 more basic checks
```

**After (359 Rules + Multi-Tiered Engine):**
```python
# Intelligent 3-tier system
Tier 1: 215 rules (regex) - Free, <100ms
Tier 2: 90 rules (NLP) - Free, <500ms  
Tier 3: 54 rules (LLM) - $0.01, <3s (batched)

# Short-circuit logic prevents waste
if critical_failures: skip_expensive_tiers()
```

### Key Benefits

| Metric | Before | After | Impact |
|--------|--------|-------|--------|
| **Rules Validated** | 8 | 359 | 45x increase |
| **Cost per Page** | N/A | <$0.005 | Within budget |
| **Processing Time** | ~200ms | ~600ms (no LLM) | Minimal impact |
| **Modules Served** | R&R only | All (RevFlow, Prompt Lab, etc.) | Cross-platform |
| **Prompt Library** | 0 | 15+ templates | Reusable prompts |

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                   UNIFIED KNOWLEDGE LAYER                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  Multi-Tiered │  │    Prompt    │  │     Scoring      │    │
│  │   Assessor    │  │   Library    │  │   Frameworks     │    │
│  │               │  │              │  │                  │    │
│  │  Tier 1 (215) │  │  15+ prompts │  │  E-E-A-T, GEO   │    │
│  │  Tier 2 (90)  │  │  Meta-prompts│  │  Tier Scanner   │    │
│  │  Tier 3 (54)  │  │  Validators  │  │  RevFlow        │    │
│  └───────────────┘  └──────────────┘  └──────────────────┘    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      DATABASE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  • extracted_rules (359 rows)    • knowledge_items             │
│  • prompt_templates (15+)        • scoring_frameworks          │
│  • validation_history            • industry_configs            │
└─────────────────────────────────────────────────────────────────┘
```

### Multi-Tiered Assessment Flow

```
┌─────────────────────────────────────────────────────────────┐
│  CONTENT SUBMISSION                                          │
│  "Phoenix plumbers charge $150-$450..."                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  TIER 1: Deterministic       │
        │  - Word count ✓              │
        │  - Phone number ✓            │
        │  - City mentions ✓           │
        │  - Price range ✓             │
        │  Cost: $0.00 | Time: 50ms    │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  SHORT-CIRCUIT CHECK         │
        │  Critical failures? → STOP   │
        └──────────┬───────────────────┘
                   │ No critical issues
                   ▼
        ┌──────────────────────────────┐
        │  TIER 2: NLP/spaCy           │
        │  - Passive voice check ✓     │
        │  - Readability score ✓       │
        │  - Sentence structure ✓      │
        │  Cost: $0.00 | Time: 200ms   │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  SHORT-CIRCUIT CHECK         │
        │  Failure rate >50%? → STOP   │
        └──────────┬───────────────────┘
                   │ Low failure rate
                   ▼
        ┌──────────────────────────────┐
        │  TIER 3: LLM/Claude (BATCHED)│
        │  - BLUF compliance ✓         │
        │  - Tone assessment ✓         │
        │  - Context appropriateness ✓ │
        │  Cost: $0.003 | Time: 2.5s   │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  RESULT: Score 87/100        │
        │  ✅ Passed (70+ threshold)   │
        │  Total Cost: $0.003          │
        │  Total Time: 2.75s           │
        └──────────────────────────────┘
```

---

## Files & Directory Structure

### Deployment Package

```
/home/claude/
├── guru-unified-schema-migration.sql    # Database schema (7 new tables)
├── categorize_rules.py                  # Auto-categorize 359 rules
├── multi_tiered_assessor.py            # Core validation engine
├── unified_knowledge_routes.py          # FastAPI routes
├── seed_prompt_library.sql             # Prompt templates
├── deploy_unified_knowledge_layer.sh   # Master deployment script
├── test_unified_knowledge_layer.py     # Comprehensive tests
└── README_UNIFIED_KNOWLEDGE_LAYER.md   # This file
```

### VPS Deployment Paths

```
/opt/guru-intelligence/
├── src/
│   ├── main.py                         # FastAPI app (update this)
│   ├── multi_tiered_assessor.py        # NEW: Core engine
│   ├── api/
│   │   ├── knowledge_routes.py.backup  # Backup of old routes
│   │   └── unified_knowledge_routes.py # NEW: Enhanced routes
├── migrations/
│   ├── guru-unified-schema-migration.sql
│   └── seed_prompt_library.sql
├── scripts/
│   └── categorize_rules.py
└── logs/
    └── app.log
```

---

## Deployment Instructions

### Prerequisites

1. **SSH access to VPS**: `ssh root@217.15.168.106`
2. **Guru Intelligence running**: `systemctl status guru-intelligence`
3. **Database accessible**: `docker ps | grep knowledge-postgres`
4. **Backup recent**: Before major changes

### Step-by-Step Deployment

#### 1. Upload Files to VPS

```bash
# From your local machine
scp -r /home/claude/* root@217.15.168.106:/opt/guru-intelligence/migrations/

# SSH to VPS
ssh root@217.15.168.106
cd /opt/guru-intelligence
```

#### 2. Run Deployment Script

```bash
# Make executable
chmod +x migrations/deploy_unified_knowledge_layer.sh

# Dry run (preview changes)
./migrations/deploy_unified_knowledge_layer.sh --dry-run

# Actual deployment
./migrations/deploy_unified_knowledge_layer.sh
```

#### 3. Verify Deployment

```bash
# Run test suite
cd /opt/guru-intelligence
source venv/bin/activate
python migrations/test_unified_knowledge_layer.py --verbose
```

#### 4. Update main.py (Manual Step)

Edit `/opt/guru-intelligence/src/main.py`:

```python
# Add these imports
from api.unified_knowledge_routes import (
    knowledge_router, 
    prompts_router, 
    scoring_router
)

# Add these routes
app.include_router(knowledge_router)
app.include_router(prompts_router)
app.include_router(scoring_router)
```

#### 5. Restart Service

```bash
systemctl restart guru-intelligence
systemctl status guru-intelligence

# Check logs
tail -f /opt/guru-intelligence/logs/app.log
```

---

## API Reference

### Knowledge Endpoints

#### POST /knowledge/assess

**Multi-Tiered Content Assessment**

Request:
```json
{
  "content": "Your content here...",
  "page_type": "service",
  "industry": "plumbing",
  "options": {
    "run_tier3": true,
    "short_circuit": true,
    "max_tier3_rules": 10
  }
}
```

Response:
```json
{
  "overall_score": 85,
  "passed": true,
  "tiers_run": [1, 2, 3],
  "tier_results": {
    "1": {"rules_checked": 120, "rules_passed": 118, "violations": [...]},
    "2": {"rules_checked": 45, "rules_passed": 44, "violations": [...]},
    "3": {"rules_checked": 8, "rules_passed": 7, "violations": [...]}
  },
  "violations": [...],
  "passed_rules_count": 169,
  "auto_fixes": [...],
  "recommendations": [...],
  "api_cost": 0.003,
  "tokens_used": 1250,
  "total_processing_time_ms": 2750
}
```

#### POST /knowledge/rules

**Query Rules by Filters**

Request:
```json
{
  "category": "BLUF",
  "complexity_level": 1,
  "page_type": "service",
  "enforcement_level": "required",
  "limit": 50
}
```

Response:
```json
{
  "count": 21,
  "rules": [
    {
      "rule_id": "BLUF-001",
      "rule_name": "First Sentence Answer",
      "complexity_level": 3,
      "validation_type": "llm",
      "enforcement_level": "required",
      "priority_score": 95
    }
  ]
}
```

#### GET /knowledge/stats

**System Statistics**

Response:
```json
{
  "rules": {
    "total": 359,
    "by_tier": {"1": 215, "2": 90, "3": 54},
    "by_category": {
      "Local Proof": 88,
      "E-E-A-T Signals": 50,
      "BLUF & Answer-First": 21
    }
  },
  "prompts": {"total": 15},
  "frameworks": {"total": 3},
  "recent_validations": {
    "total": 1247,
    "passed": 1089,
    "avg_score": 82.5,
    "total_cost": 3.47
  }
}
```

### Prompt Library Endpoints

#### GET /prompts/

**List All Prompts**

Response:
```json
{
  "count": 15,
  "prompts": [
    {
      "prompt_id": "GEN-SERVICE-001",
      "name": "Service Page Content Generator",
      "prompt_type": "generation",
      "category": "Page Generation",
      "usage_count": 847
    }
  ]
}
```

#### GET /prompts/{prompt_id}

**Get Specific Prompt**

Response:
```json
{
  "prompt_id": "GEN-SERVICE-001",
  "name": "Service Page Content Generator",
  "system_prompt": "You are an expert...",
  "user_prompt_template": "Create content for...",
  "required_variables": ["company_name", "service_name", "location"],
  "preferred_model": "claude-sonnet-4-20250514",
  "max_tokens": 2500,
  "temperature": 0.7
}
```

#### POST /prompts/render

**Render Prompt with Variables**

Request:
```json
{
  "prompt_id": "GEN-SERVICE-001",
  "variables": {
    "company_name": "ABC Plumbing",
    "service_name": "Drain Cleaning",
    "location": "Phoenix"
  }
}
```

Response:
```json
{
  "prompt_id": "GEN-SERVICE-001",
  "rendered_system_prompt": "You are an expert...",
  "rendered_user_prompt": "Create content for ABC Plumbing's Drain Cleaning service in Phoenix...",
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 2500,
  "temperature": 0.7
}
```

---

## Integration Guide

### R&R Automation Integration

Update `/opt/smarketsherpa/rr-automation/validators/guru_validator.py`:

```python
class GuruValidator:
    def validate(self, content: str, page_type: str = "service") -> GuruScore:
        # NEW: Use enhanced /assess endpoint
        resp = requests.post(
            f"{self.api_base}/assess",
            json={
                "content": content,
                "page_type": page_type,
                "options": {
                    "run_tier3": True,        # Enable LLM validation
                    "short_circuit": True,     # Save cost on bad content
                    "max_tier3_rules": 10      # Limit LLM batch size
                }
            },
            timeout=10
        )
        
        data = resp.json()
        
        return GuruScore(
            overall_score=data['overall_score'],
            passed=data['passed'],
            rules_checked=sum(tr['rules_checked'] for tr in data['tier_results'].values()),
            rules_passed=data['passed_rules_count'],
            violations=data['violations'],
            passed_rules=data.get('passed_rules', []),
            recommendations=data.get('recommendations', []),
            api_cost=data.get('api_cost', 0),  # NEW: Cost tracking
            processing_time_ms=data.get('total_processing_time_ms', 0)
        )
```

### RevFlow Integration

Use prompt library for assessment generation:

```python
import requests

# Get RevFlow assessment prompt
prompt = requests.get("http://localhost:8103/prompts/ANALYZE-REVFLOW-001").json()

# Render with business data
rendered = requests.post(
    "http://localhost:8103/prompts/render",
    json={
        "prompt_id": "ANALYZE-REVFLOW-001",
        "variables": {
            "business_name": "ABC Plumbing",
            "industry": "plumbing",
            "location": "Phoenix",
            "website_data": website_analysis,
            "local_seo_data": seo_metrics,
            "reputation_data": reviews,
            "competitor_data": competitors
        }
    }
).json()

# Use rendered prompt with Claude
assessment = anthropic_client.messages.create(
    model=rendered['model'],
    max_tokens=rendered['max_tokens'],
    messages=[
        {"role": "system", "content": rendered['rendered_system_prompt']},
        {"role": "user", "content": rendered['rendered_user_prompt']}
    ]
)
```

---

## Cost Analysis

### Per-Page Validation Costs

| Scenario | Tier 1 | Tier 2 | Tier 3 | Total Cost | Total Time |
|----------|--------|--------|--------|------------|------------|
| **Good Content** | ✓ | ✓ | ✓ | $0.003 | ~2.8s |
| **Minor Issues** | ✓ | ✓ | ✓ | $0.003 | ~2.8s |
| **Bad Content (Short-Circuit)** | ✓ | ✗ | ✗ | $0.000 | ~0.1s |
| **Tier 3 Disabled** | ✓ | ✓ | ✗ | $0.000 | ~0.3s |

### Monthly Cost Projections

Assuming 1,590 pages across 53 sites:

- **Initial Generation**: 1,590 × $0.003 = **$4.77**
- **Monthly Refreshes** (20% refresh rate): 318 × $0.003 = **$0.95/month**
- **Ad-hoc Validations** (10/day): 300 × $0.003 = **$0.90/month**

**Total Monthly**: ~**$1.85** (well within $0.03/page budget)

---

## Troubleshooting

### Common Issues

#### 1. "Tier 3 always returns empty results"

**Cause**: Claude API key not configured  
**Fix**:
```bash
# Add to environment
export ANTHROPIC_API_KEY="sk-ant-..."

# Or add to systemd service
vi /etc/systemd/system/guru-intelligence.service

[Service]
Environment="ANTHROPIC_API_KEY=sk-ant-..."

systemctl daemon-reload
systemctl restart guru-intelligence
```

#### 2. "spaCy model not found"

**Cause**: Tier 2 NLP dependencies missing  
**Fix**:
```bash
cd /opt/guru-intelligence
source venv/bin/activate
pip install spacy textstat
python -m spacy download en_core_web_sm
```

#### 3. "Rules show NULL complexity_level"

**Cause**: Categorization script not run  
**Fix**:
```bash
python /opt/guru-intelligence/scripts/categorize_rules.py
```

#### 4. "Assessment takes >10 seconds"

**Cause**: Not using short-circuit logic  
**Fix**: Enable short-circuit in request:
```json
{"options": {"short_circuit": true}}
```

---

## Monitoring & Metrics

### Key Metrics to Track

#### Performance Metrics

```sql
-- Average processing time by tier
SELECT 
    tier,
    AVG(processing_time_ms) as avg_ms,
    MIN(processing_time_ms) as min_ms,
    MAX(processing_time_ms) as max_ms
FROM (
    SELECT 1 as tier, tier1_processing_ms as processing_time_ms FROM validation_history
    UNION ALL
    SELECT 2, tier2_processing_ms FROM validation_history
    UNION ALL
    SELECT 3, tier3_processing_ms FROM validation_history
) t
GROUP BY tier;
```

#### Cost Metrics

```sql
-- Daily API costs
SELECT 
    DATE(assessed_at) as date,
    COUNT(*) as validations,
    SUM(api_cost) as total_cost,
    AVG(api_cost) as avg_cost_per_validation
FROM validation_history
WHERE assessed_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(assessed_at)
ORDER BY date DESC;
```

#### Quality Metrics

```sql
-- Pass rate by module
SELECT 
    module,
    COUNT(*) as total,
    SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed,
    ROUND(AVG(overall_score), 2) as avg_score
FROM validation_history
WHERE assessed_at >= NOW() - INTERVAL '7 days'
GROUP BY module;
```

---

## Future Enhancements

### Phase 2 Roadmap

1. **Scoring Frameworks**
   - E-E-A-T Scorer (fully automated)
   - GEO Optimizer (AI citation readiness)
   - Tier Scanner (Mandatory/Enhanced/Excellence)

2. **Industry Configurations**
   - Plumbing, HVAC, Legal presets
   - Backstory templates
   - Regional terminology databases

3. **Auto-Fix Engine**
   - Simple violations auto-corrected
   - Suggestions for complex issues
   - Before/after comparison

4. **Configuration UI**
   - Web dashboard for rule management
   - Prompt template editor
   - Real-time validation preview

---

## Support & Contact

**Questions?** Reference the handoff documents:
- `GURU_UNIFIED_KNOWLEDGE_LAYER_HANDOFF.md`
- `GURU_MULTITIERED_ENGINE_HANDOFF.md`

**Issues?** Check logs:
```bash
tail -f /opt/guru-intelligence/logs/app.log
journalctl -u guru-intelligence -n 100
```

---

## Changelog

### Version 1.0 (December 28, 2025)

**Added:**
- Multi-Tiered Assessment Engine (Tier 1/2/3)
- 7 new database tables
- Prompt library with 15+ templates
- Auto-categorization for 359 rules
- Short-circuit logic for cost optimization
- Comprehensive API endpoints
- Test suite with 20+ tests

**Changed:**
- Replaced hardcoded 8-rule checker with 359-rule engine
- Enhanced /assess endpoint with tier results
- Added cost and performance tracking

**Fixed:**
- N/A (initial release)

---

**✅ SYSTEM READY FOR DEPLOYMENT**
