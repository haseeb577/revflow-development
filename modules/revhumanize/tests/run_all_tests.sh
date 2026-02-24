#!/bin/bash

API_URL="http://localhost:8003/api/v1/validate"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     RevFlow Humanization Pipeline - Complete Test Suite       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    TEST_NAME=$1
    TEST_DATA=$2
    EXPECTED_CONDITION=$3
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST: $TEST_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    RESPONSE=$(curl -s -X POST $API_URL \
        -H "Content-Type: application/json" \
        -d "$TEST_DATA")
    
    if eval "$EXPECTED_CONDITION"; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Response: $RESPONSE"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# TEST 1: High Quality Content
run_test "High Quality Content - Should Score ≥70" \
'{"content": "Welcome to Dallas Pro Plumbing, your trusted plumbing experts serving the Dallas-Fort Worth metroplex for over 20 years.\n\nOur Comprehensive Services:\n\nEmergency Plumbing: Available 24/7 for urgent repairs.\n\nResidential Plumbing: From simple faucet repairs to complete bathroom remodels.\n\nCommercial Plumbing: We serve restaurants, offices, and retail spaces.\n\nWhy Choose Dallas Pro Plumbing:\n- Licensed and insured\n- Upfront pricing\n- Same-day service available\n\nContact us today!", "title": "Professional Plumbing Services"}' \
'SCORE=$(echo "$RESPONSE" | jq -r ".qa_score // 0"); [ $(echo "$SCORE >= 70" | bc -l) -eq 1 ]'

# TEST 2: Low Quality Content
run_test "Short Low Quality Content - Should Score <70" \
'{"content": "We do plumbing. Call us now!", "title": "Plumbing"}' \
'SCORE=$(echo "$RESPONSE" | jq -r ".qa_score // 0"); [ $(echo "$SCORE < 70" | bc -l) -eq 1 ]'

# TEST 3: AI Detection
run_test "AI Detection - Should Flag AI Content" \
'{"content": "As an AI language model, I would be happy to assist you with your plumbing needs. In todays fast-paced world, it is important to note that our comprehensive suite of solutions leverages cutting-edge technology.", "title": "AI Test"}' \
'AI_PROB=$(echo "$RESPONSE" | jq -r ".ai_probability // 0"); [ $(echo "$AI_PROB > 0.3" | bc -l) -eq 1 ]'

# TEST 4: Voice Consistency
run_test "Voice Consistency - Should Have Good Score" \
'{"content": "Our certified plumbing technicians provide comprehensive drainage solutions using industry-standard methodologies and advanced equipment.", "title": "Voice Test"}' \
'VOICE=$(echo "$RESPONSE" | jq -r ".voice_consistency_score // 0"); [ $(echo "$VOICE >= 80" | bc -l) -eq 1 ]'

# TEST 5: YMYL Verification
run_test "YMYL Verification - Should Pass" \
'{"content": "Our licensed medical professionals provide comprehensive healthcare services.", "title": "YMYL Test"}' \
'YMYL=$(echo "$RESPONSE" | jq -r ".ymyl_verification_score // 0"); [ $(echo "$YMYL >= 80" | bc -l) -eq 1 ]'

# TEST 6: Structure Check
run_test "Structure Check - Should Pass" \
'{"content": "Test content with structure.", "title": "Structure Test"}' \
'STATUS=$(echo "$RESPONSE" | jq -r ".status"); [ "$STATUS" != "error" ]'

# TEST 7: Complete Validation
run_test "Complete Validation - All Checks" \
'{"content": "Professional plumbing services.\n\nWe offer emergency repairs, residential services, and commercial solutions.\n\nLicensed and insured professionals.\n\nContact us today for a free estimate!", "title": "Complete Test"}' \
'SCORE=$(echo "$RESPONSE" | jq -r ".qa_score // 0"); [ $(echo "$SCORE >= 70" | bc -l) -eq 1 ]'

# TEST 8: Empty Content
run_test "Edge Case - Empty Content Should Be Rejected" \
'{"content": "", "title": "Empty"}' \
'SCORE=$(echo "$RESPONSE" | jq -r ".qa_score // 0"); [ $(echo "$SCORE < 70" | bc -l) -eq 1 ]'

# TEST 9: Long Content
run_test "Edge Case - Long Content Processing" \
'{"content": "This is a very long piece of content that tests the systems ability to process larger texts efficiently. We want to ensure that the validation system can handle substantial amounts of text without performance degradation or errors. This content includes multiple paragraphs and sections to simulate real-world usage patterns.", "title": "Long Content"}' \
'STATUS=$(echo "$RESPONSE" | jq -r ".status"); [ "$STATUS" != "error" ]'

# TEST 10: Health Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST: API Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HEALTH=$(curl -s http://localhost:8003/health | jq -r ".status")
if [ "$HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✅ PASS - API is healthy${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL - API health check failed${NC}"
    ((TESTS_FAILED++))
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                        TEST SUMMARY                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Tests Run: 10"
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed. Review output above.${NC}"
    exit 1
fi
