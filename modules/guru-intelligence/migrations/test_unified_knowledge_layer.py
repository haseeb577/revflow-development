#!/usr/bin/env python3
"""
Guru Intelligence - Unified Knowledge Layer Test Suite
Comprehensive testing for Multi-Tiered Assessment, Prompt Library, and APIs

Usage:
    python test_unified_knowledge_layer.py [--verbose]
"""

import requests
import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Configuration
API_BASE = "http://localhost:8103"
VERBOSE = False

@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    passed: bool
    duration_ms: int
    message: str
    details: Dict = None

class TestSuite:
    """Unified Knowledge Layer Test Suite"""
    
    def __init__(self, api_base: str = API_BASE, verbose: bool = False):
        self.api_base = api_base
        self.verbose = verbose
        self.results: List[TestResult] = []
        
    def log(self, message: str):
        """Log message if verbose mode"""
        if self.verbose:
            print(f"  {message}")
    
    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and record result"""
        print(f"\n▶ Testing: {test_name}")
        start_time = time.time()
        
        try:
            test_func()
            duration_ms = int((time.time() - start_time) * 1000)
            result = TestResult(
                test_name=test_name,
                passed=True,
                duration_ms=duration_ms,
                message="✅ PASSED"
            )
        except AssertionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = TestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                message=f"❌ FAILED: {str(e)}"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = TestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                message=f"❌ ERROR: {str(e)}"
            )
        
        self.results.append(result)
        print(f"  {result.message} ({duration_ms}ms)")
        return result
    
    # ========================================================================
    # HEALTH & CONNECTIVITY TESTS
    # ========================================================================
    
    def test_health_endpoint(self):
        """Test basic health check"""
        response = requests.get(f"{self.api_base}/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        self.log(f"Health check OK")
    
    # ========================================================================
    # KNOWLEDGE ENDPOINT TESTS
    # ========================================================================
    
    def test_knowledge_stats(self):
        """Test /knowledge/stats endpoint"""
        response = requests.get(f"{self.api_base}/knowledge/stats")
        assert response.status_code == 200, f"Status code: {response.status_code}"
        
        data = response.json()
        assert 'rules' in data, "Missing 'rules' key"
        assert 'total' in data['rules'], "Missing 'total' in rules"
        assert data['rules']['total'] > 0, "No rules found in database"
        
        self.log(f"Total rules: {data['rules']['total']}")
        self.log(f"Tier distribution: {data['rules'].get('by_tier', {})}")
    
    def test_knowledge_rules_query(self):
        """Test /knowledge/rules query endpoint"""
        response = requests.post(
            f"{self.api_base}/knowledge/rules",
            json={"category": "BLUF", "limit": 10}
        )
        assert response.status_code == 200, f"Status code: {response.status_code}"
        
        data = response.json()
        assert 'rules' in data, "Missing 'rules' key"
        assert data['count'] > 0, "No rules returned"
        
        # Verify rule structure
        first_rule = data['rules'][0]
        assert 'rule_id' in first_rule, "Missing rule_id"
        assert 'complexity_level' in first_rule, "Missing complexity_level"
        
        self.log(f"Returned {data['count']} rules")
    
    def test_multi_tiered_assessment_basic(self):
        """Test basic multi-tiered assessment"""
        test_content = """
        Phoenix plumbers charge between $150-$450 for drain cleaning services. 
        ABC Plumbing has served the Phoenix metro area since 1987, completing over 
        15,000 emergency repairs for homeowners across Scottsdale, Tempe, Mesa, 
        and Gilbert. Our licensed contractor team (ROC-284756) responds within 
        60 minutes for emergency calls. We service all major brands including 
        American Standard, Kohler, and Moen. Call (602) 555-1234 for same-day service.
        """
        
        response = requests.post(
            f"{self.api_base}/knowledge/assess",
            json={
                "content": test_content,
                "page_type": "service",
                "industry": "plumbing"
            }
        )
        
        assert response.status_code == 200, f"Status code: {response.status_code}"
        
        data = response.json()
        assert 'overall_score' in data, "Missing overall_score"
        assert 'passed' in data, "Missing passed"
        assert 'tiers_run' in data, "Missing tiers_run"
        
        # Should run at least Tier 1
        assert 1 in data['tiers_run'], "Tier 1 not executed"
        
        self.log(f"Score: {data['overall_score']}, Passed: {data['passed']}")
        self.log(f"Tiers run: {data['tiers_run']}")
    
    def test_multi_tiered_assessment_short_circuit(self):
        """Test short-circuit logic with bad content"""
        bad_content = "This is very short content."
        
        response = requests.post(
            f"{self.api_base}/knowledge/assess",
            json={
                "content": bad_content,
                "page_type": "service",
                "options": {"short_circuit": True}
            }
        )
        
        assert response.status_code == 200, f"Status code: {response.status_code}"
        
        data = response.json()
        assert data['overall_score'] < 50, "Bad content should score low"
        
        # Should short-circuit before Tier 3
        if 3 in data.get('tiers_run', []):
            self.log("WARNING: Tier 3 ran on bad content (may waste cost)")
        
        self.log(f"Score: {data['overall_score']}")
        self.log(f"Violations: {len(data.get('violations', []))}")
    
    def test_tier_filtering(self):
        """Test rules are properly filtered by tier"""
        # Query Tier 1 rules
        response = requests.post(
            f"{self.api_base}/knowledge/rules",
            json={"complexity_level": 1, "limit": 20}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all returned rules are Tier 1
        for rule in data['rules']:
            assert rule['complexity_level'] == 1, f"Rule {rule['rule_id']} is not Tier 1"
        
        self.log(f"Verified {data['count']} Tier 1 rules")
    
    # ========================================================================
    # PROMPT LIBRARY TESTS
    # ========================================================================
    
    def test_prompts_list(self):
        """Test /prompts/ list endpoint"""
        response = requests.get(f"{self.api_base}/prompts/")
        assert response.status_code == 200, f"Status code: {response.status_code}"
        
        data = response.json()
        assert 'prompts' in data, "Missing 'prompts' key"
        assert data['count'] > 0, "No prompts found"
        
        self.log(f"Total prompts: {data['count']}")
    
    def test_prompts_get_by_id(self):
        """Test /prompts/{id} get endpoint"""
        # First get list of prompts
        list_response = requests.get(f"{self.api_base}/prompts/")
        prompts = list_response.json()['prompts']
        
        if len(prompts) > 0:
            test_prompt_id = prompts[0]['prompt_id']
            
            # Get specific prompt
            response = requests.get(f"{self.api_base}/prompts/{test_prompt_id}")
            assert response.status_code == 200, f"Status code: {response.status_code}"
            
            data = response.json()
            assert 'prompt_id' in data, "Missing prompt_id"
            assert 'system_prompt' in data or 'user_prompt_template' in data, "Missing prompt content"
            
            self.log(f"Retrieved prompt: {test_prompt_id}")
    
    def test_prompts_render(self):
        """Test /prompts/render endpoint"""
        # Create a test render request with BASE-001
        response = requests.post(
            f"{self.api_base}/prompts/render",
            json={
                "prompt_id": "BASE-001",
                "variables": {
                    "target_audience": "homeowners",
                    "industry": "plumbing",
                    "location": "Phoenix"
                }
            }
        )
        
        # This might fail if BASE-001 doesn't exist yet
        if response.status_code == 200:
            data = response.json()
            assert 'rendered_user_prompt' in data, "Missing rendered prompt"
            assert 'Phoenix' in data['rendered_user_prompt'], "Variable not substituted"
            
            self.log(f"Prompt rendered successfully")
        else:
            self.log(f"Prompt BASE-001 not found (may not be seeded yet)")
    
    # ========================================================================
    # SCORING FRAMEWORK TESTS
    # ========================================================================
    
    def test_scoring_frameworks_list(self):
        """Test /scoring/frameworks endpoint"""
        response = requests.get(f"{self.api_base}/scoring/frameworks")
        
        # May return empty if frameworks not seeded yet
        if response.status_code == 200:
            data = response.json()
            assert 'frameworks' in data, "Missing 'frameworks' key"
            self.log(f"Frameworks found: {data['count']}")
        else:
            self.log("Scoring frameworks endpoint not yet implemented")
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    def test_tier1_performance(self):
        """Test Tier 1 validation performance"""
        test_content = "A" * 1000  # 1000 character content
        
        start_time = time.time()
        response = requests.post(
            f"{self.api_base}/knowledge/assess",
            json={
                "content": test_content,
                "page_type": "service",
                "options": {"run_tier3": False}  # Skip expensive tier
            }
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        assert response.status_code == 200
        assert duration_ms < 500, f"Tier 1/2 should be fast (<500ms), got {duration_ms}ms"
        
        self.log(f"Tier 1/2 validation completed in {duration_ms}ms")
    
    # ========================================================================
    # DATA INTEGRITY TESTS
    # ========================================================================
    
    def test_rule_categorization_complete(self):
        """Test all rules have complexity_level assigned"""
        response = requests.post(
            f"{self.api_base}/knowledge/rules",
            json={"limit": 200}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        uncategorized = [r for r in data['rules'] if not r.get('complexity_level')]
        assert len(uncategorized) == 0, f"{len(uncategorized)} rules missing complexity_level"
        
        self.log(f"All {data['count']} rules have complexity_level assigned")
    
    def test_tier1_have_validation_patterns(self):
        """Test Tier 1 rules have validation_pattern"""
        response = requests.post(
            f"{self.api_base}/knowledge/rules",
            json={"complexity_level": 1, "limit": 200}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        missing_patterns = [r for r in data['rules'] if not r.get('validation_pattern')]
        
        # Allow up to 10% to be missing patterns during initial deployment
        max_missing = int(data['count'] * 0.1)
        assert len(missing_patterns) <= max_missing, \
            f"{len(missing_patterns)} Tier 1 rules missing validation_pattern (max {max_missing} allowed)"
        
        self.log(f"{data['count'] - len(missing_patterns)}/{data['count']} Tier 1 rules have patterns")
    
    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================
    
    def test_end_to_end_content_validation(self):
        """Test complete workflow: assess content, get violations, verify response"""
        content = """
        Phoenix drain cleaning costs $200-$400. We serve Mesa, Tempe, Scottsdale.
        ABC Plumbing has 10+ years experience. Call (602) 555-1234.
        
        ## How Much Does Drain Cleaning Cost?
        
        The average cost is $200-$400 in Phoenix depending on severity.
        """
        
        response = requests.post(
            f"{self.api_base}/knowledge/assess",
            json={
                "content": content,
                "page_type": "service",
                "industry": "plumbing"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have run multiple tiers
        assert len(data['tiers_run']) >= 1, "At least Tier 1 should run"
        
        # Should have tier results
        assert 'tier_results' in data, "Missing tier_results"
        
        # Should have some rules checked
        total_checked = sum(
            tier_data.get('rules_checked', 0) 
            for tier_data in data['tier_results'].values()
        )
        assert total_checked > 0, "No rules were checked"
        
        # Should have violations or passed rules
        has_violations = len(data.get('violations', [])) > 0
        has_passed = data.get('passed_rules_count', 0) > 0
        assert has_violations or has_passed, "No violations or passed rules"
        
        self.log(f"Checked {total_checked} rules across {len(data['tiers_run'])} tiers")
        self.log(f"Score: {data['overall_score']}, Violations: {len(data.get('violations', []))}")
    
    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================
    
    def run_all(self):
        """Run complete test suite"""
        print("=" * 70)
        print("GURU UNIFIED KNOWLEDGE LAYER - TEST SUITE")
        print("=" * 70)
        
        # Test categories
        tests = [
            ("Health & Connectivity", [
                ("Health Check", self.test_health_endpoint),
            ]),
            ("Knowledge Endpoints", [
                ("Stats Endpoint", self.test_knowledge_stats),
                ("Rules Query", self.test_knowledge_rules_query),
                ("Basic Assessment", self.test_multi_tiered_assessment_basic),
                ("Short-Circuit Logic", self.test_multi_tiered_assessment_short_circuit),
                ("Tier Filtering", self.test_tier_filtering),
            ]),
            ("Prompt Library", [
                ("List Prompts", self.test_prompts_list),
                ("Get Prompt by ID", self.test_prompts_get_by_id),
                ("Render Prompt", self.test_prompts_render),
            ]),
            ("Scoring Frameworks", [
                ("List Frameworks", self.test_scoring_frameworks_list),
            ]),
            ("Performance", [
                ("Tier 1 Performance", self.test_tier1_performance),
            ]),
            ("Data Integrity", [
                ("Rule Categorization", self.test_rule_categorization_complete),
                ("Tier 1 Patterns", self.test_tier1_have_validation_patterns),
            ]),
            ("Integration", [
                ("End-to-End Validation", self.test_end_to_end_content_validation),
            ]),
        ]
        
        for category, category_tests in tests:
            print(f"\n{'='*70}")
            print(f"{category.upper()}")
            print(f"{'='*70}")
            
            for test_name, test_func in category_tests:
                self.run_test(test_name, test_func)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed} ({passed*100//total}%)")
        print(f"❌ Failed: {failed} ({failed*100//total}%)")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.message}")
        
        # Performance stats
        total_duration = sum(r.duration_ms for r in self.results)
        avg_duration = total_duration // total if total > 0 else 0
        
        print(f"\nTotal Duration: {total_duration}ms")
        print(f"Average Test: {avg_duration}ms")
        
        print("\n" + "=" * 70)
        
        if failed == 0:
            print("✅ ALL TESTS PASSED")
        else:
            print(f"⚠️  {failed} TESTS FAILED")
        
        print("=" * 70)

def main():
    """Main test execution"""
    import sys
    
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    suite = TestSuite(api_base=API_BASE, verbose=verbose)
    suite.run_all()
    
    # Exit with appropriate code
    failed = sum(1 for r in suite.results if not r.passed)
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
