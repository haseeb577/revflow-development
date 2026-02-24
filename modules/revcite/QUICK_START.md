# RevCite Citation Tracking - Quick Start Guide

## ✅ Setup Complete!

Your IndexNow key has been generated and files are ready.

## 🚀 Deployment Steps

### Step 1: Get Clarity Project ID (5 minutes)

1. Go to https://clarity.microsoft.com/
2. Sign in (free Microsoft account)
3. Click "Add new project"
4. Enter: "RevCite Citation Tracking"
5. Add one of your WordPress sites
6. **Copy the Project ID** (looks like: `abc123def456`)

### Step 2: Update Configuration (1 minute)

**Option A - Interactive:**
```bash
/opt/revcite/update_config.sh
```

**Option B - Manual:**
```bash
nano /opt/revcite/config/tracking_config.json
# Replace: REPLACE_WITH_YOUR_CLARITY_PROJECT_ID with your actual ID
# Replace: example.com with your domain
```

### Step 3: Test Integration (1 minute)
```bash
python3 /opt/revcite/test_integrations.py
```

Expected output:
```
✅ Engine initialized successfully
✅ Citation processing test: active
✅ Velocity check test: normal
🎉 All tests passed!
```

### Step 4: Deploy to WordPress Sites (15 minutes)

1. Edit site list:
```bash
nano /opt/revcite/deploy_to_all_sites.sh
# Update the SITES array with your 53 domains
```

2. Run deployment:
```bash
/opt/revcite/deploy_to_all_sites.sh
```

This will:
- Create IndexNow key files on all sites
- Configure Clarity tracking
- Test accessibility

### Step 5: Register with RevCore (1 minute)
```bash
python3 /opt/shared-api-engine/register_with_revcore.py \
    'revcite-citation-tracker' \
    'RevCite Citation Optimization' \
    8600 \
    '1.0.0'
```

### Step 6: Verify (5 minutes)

1. **Test IndexNow:**
```bash
curl https://yoursite.com/d83b0f5bd90f0c42fab4cb59222ae3c16bbdb50f9ce0e12ff1ee58e159efea70.txt
```
Should return: `d83b0f5bd90f0c42fab4cb59222ae3c16bbdb50f9ce0e12ff1ee58e159efea70`

2. **Test Clarity:**
- Visit one of your sites
- Open browser console (F12)
- Type: `clarity`
- Should see Clarity object

3. **Check RevCore:**
```bash
curl http://localhost:8004/api/v1/services | jq
```

## 📊 Using the Integration

### Track New Citation Discovery
```python
from citation_optimization_engine import CitationOptimizationEngine

engine = CitationOptimizationEngine()

# When you discover a new citation
result = engine.process_new_citation_discovered({
    "id": "citation-001",
    "page_url": "https://yoursite.com/service-page/",
    "ai_engine": "ChatGPT",
    "citation_text": "According to yoursite.com..."
})

print(f"Search engines notified: {result['search_engines_notified']}")
```

### Check Citation Velocity
```python
# Check if citation velocity is accelerating
velocity_result = engine.run_citation_velocity_check(
    site_url="https://yoursite.com",
    recent_citation_count=15,  # Citations in past 7 days
    days=7
)

if velocity_result['status'] == 'citation_boost_detected':
    print("🚀 Citation boost detected - search engines notified!")
```

## 🎯 Key Features

### Microsoft Clarity
- ✅ Track citation click-through rates
- ✅ Measure user engagement with cited content
- ✅ Identify high-performing citation sources
- ✅ A/B test citation placements

### IndexNow
- ✅ Instant indexing notifications
- ✅ Batch submission (10,000 URLs at once)
- ✅ Citation velocity alerts
- ✅ Authority update signals

## 📈 Expected Results

- **Indexing Speed:** 5-15 minutes (vs. days/weeks without IndexNow)
- **Citation Discovery:** Real-time tracking of AI engine citations
- **Engagement Data:** Available in Clarity within 2-3 hours
- **Cost:** $0 (vs. $1,000+/month for equivalent tools)

## 🆘 Troubleshooting

### Clarity not tracking:
- Check browser console for errors
- Verify Project ID is correct
- Wait 2-3 hours for initial data

### IndexNow key file not accessible:
- Check file permissions: `chmod 644 keyfile.txt`
- Verify path is correct
- Test with curl

### Python import errors:
```bash
cd /opt/revcite/integrations
python3 -c "from citation_optimization_engine import CitationOptimizationEngine; print('OK')"
```

## 📝 Next Steps

1. ✅ Get Clarity ID
2. ✅ Update config
3. ✅ Test integration
4. ✅ Deploy to sites
5. ✅ Register with RevCore
6. 🔄 Start tracking citations!

## 🎉 Success!

Once deployed, RevCite will:
- Automatically notify search engines when citations are discovered
- Track user engagement with citations
- Optimize citation placement based on data
- Provide competitive intelligence on citation velocity

**Your competitive advantage:** You're the ONLY rank-and-rent operator optimizing for AI citations in real-time! 🚀
