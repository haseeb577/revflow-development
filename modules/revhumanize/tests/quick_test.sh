#!/bin/bash
# Quick Test Script for RevFlow Humanization Pipeline

echo "🧪 RevFlow Humanization Pipeline - Quick Test"
echo "=============================================="
echo ""

BASE_URL="http://localhost:8003"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
if curl -s "$BASE_URL/health" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${RED}✗ Service health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: AI Detection
echo -e "${YELLOW}Test 2: AI Detection${NC}"
AI_TEST='In todays fast-paced digital landscape, we delve into the realm of comprehensive AI solutions.'
RESULT=$(curl -s -X POST "$BASE_URL/api/v1/detect-ai" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$AI_TEST\"}")

if echo "$RESULT" | grep -q "ai_probability"; then
    echo -e "${GREEN}✓ AI Detection working${NC}"
    echo "   Verdict: $(echo $RESULT | jq -r '.verdict')"
    echo "   Probability: $(echo $RESULT | jq -r '.ai_probability')"
else
    echo -e "${RED}✗ AI Detection failed${NC}"
fi
echo ""

# Test 3: Validation (with Tier 1 violations)
echo -e "${YELLOW}Test 3: Validation (Tier 1 Violations Expected)${NC}"
TIER1_TEST='We delve into the realm of comprehensive solutions that unlock unprecedented value.'
RESULT=$(curl -s -X POST "$BASE_URL/api/v1/validate" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$TIER1_TEST\", \"enable_auto_fix\": false}")

if echo "$RESULT" | grep -q "tier1_issues"; then
    echo -e "${GREEN}✓ Validation working${NC}"
    TIER1_COUNT=$(echo $RESULT | jq '.tier1_issues | length')
    echo "   Tier 1 Issues: $TIER1_COUNT"
    echo "   Status: $(echo $RESULT | jq -r '.status')"
    echo "   Score: $(echo $RESULT | jq -r '.final_score')"
else
    echo -e "${RED}✗ Validation failed${NC}"
fi
echo ""

# Test 4: Auto-Humanization (Tier 3 patterns)
echo -e "${YELLOW}Test 4: Auto-Humanization (Tier 3 Patterns)${NC}"
TIER3_TEST='In todays world, whether you are a startup or enterprise, we offer solutions from basic to premium.'
RESULT=$(curl -s -X POST "$BASE_URL/api/v1/process" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$TIER3_TEST\", \"enable_auto_fix\": true}")

if echo "$RESULT" | grep -q "status"; then
    echo -e "${GREEN}✓ Auto-Humanization working${NC}"
    echo "   Status: $(echo $RESULT | jq -r '.status')"
    if [ "$(echo $RESULT | jq -r '.status')" = "AUTO_FIXED" ]; then
        echo -e "   ${GREEN}Content was auto-fixed!${NC}"
        IMPROVEMENT=$(echo $RESULT | jq -r '.humanized_result.improvement_score')
        echo "   Score Improvement: +$IMPROVEMENT points"
    fi
else
    echo -e "${RED}✗ Auto-Humanization failed${NC}"
fi
echo ""

# Test 5: Complete Pipeline (Good Content)
echo -e "${YELLOW}Test 5: Complete Pipeline (Good Content)${NC}"
GOOD_CONTENT="Emergency Plumber in Dallas

I've been fixing plumbing emergencies in Dallas for 15 years. When a pipe bursts at 2 AM, you need help fast.

Our response time averages 23 minutes. We fixed 847 emergencies last year, with 94% resolved within 2 hours.

**What causes most emergencies?**
Frozen pipes account for 43% of winter calls.

**How much does emergency service cost?**
Prices start at \$150 for the service call."

RESULT=$(curl -s -X POST "$BASE_URL/api/v1/process" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$GOOD_CONTENT\", \"enable_auto_fix\": true, \"ai_detection_enabled\": true}")

if echo "$RESULT" | grep -q "status"; then
    echo -e "${GREEN}✓ Pipeline working${NC}"
    STATUS=$(echo $RESULT | jq -r '.status')
    echo "   Status: $STATUS"
    
    if [ "$STATUS" = "PASSED" ] || [ "$STATUS" = "AUTO_FIXED" ]; then
        echo -e "   ${GREEN}Quality content!${NC}"
        SCORE=$(echo $RESULT | jq -r '.validation.final_score // .original_validation.final_score')
        echo "   Quality Score: $SCORE/100"
    fi
else
    echo -e "${RED}✗ Pipeline failed${NC}"
fi
echo ""

# Summary
echo ""
echo "=============================================="
echo -e "${GREEN}✅ All Tests Complete!${NC}"
echo "=============================================="
echo ""
echo "API Documentation: $BASE_URL/docs"
echo "Health Check: $BASE_URL/health"
echo ""
echo "Next Steps:"
echo "  1. Check the API docs at $BASE_URL/docs"
echo "  2. Configure email/Slack in .env"
echo "  3. Test manual review workflow"
echo "  4. Integrate with RevFlow OS"
echo ""
