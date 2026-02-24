#!/bin/bash

API_URL="http://localhost:8003/api/v1"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Complete System Test Suite - All Features              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

test_endpoint() {
    TEST_NAME=$1
    shift
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST: $TEST_NAME"
    
    RESPONSE=$(curl -s "$@")
    
    if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        echo "Response: $(echo "$RESPONSE" | jq -c .)"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Response: $RESPONSE"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Test 1: Auto-Humanization
test_endpoint "Auto-Humanization" \
    -X POST "$API_URL/auto-humanize" \
    -H "Content-Type: application/json" \
    -d '{"content_id":"test_001","content":"This is a test. This is a test.","target_score":80}'

# Test 2: Webhook Configuration
test_endpoint "Configure Webhook" \
    -X POST "$API_URL/webhooks/configure?customer_id=test_customer&webhook_url=https://example.com/webhook"

# Test 3: Get Webhook Config
test_endpoint "Get Webhook Config" \
    -X GET "$API_URL/webhooks/test_customer"

# Test 4: Batch Submission
test_endpoint "Batch Processing" \
    -X POST "$API_URL/batch/submit?customer_id=test_customer" \
    -H "Content-Type: application/json" \
    -d '{"items":[{"content":"Test 1","title":"Title 1"},{"content":"Test 2","title":"Title 2"}]}'

# Test 5: Review Queue
test_endpoint "Get Review Queue" \
    -X GET "$API_URL/review/queue?status=pending&limit=10"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     TEST SUMMARY                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Tests: 5"
echo -e "${GREEN}✅ Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Failed: $TESTS_FAILED${NC}"
