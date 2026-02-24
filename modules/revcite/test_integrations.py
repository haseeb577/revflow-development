#!/usr/bin/env python3
"""Test RevCite integrations"""

import sys
sys.path.insert(0, '/opt/revcite/integrations')

from citation_optimization_engine import CitationOptimizationEngine

print("🧪 Testing RevCite Citation Optimization Engine...")
print("")

try:
    # Initialize engine
    engine = CitationOptimizationEngine()
    print("✅ Engine initialized successfully")
    
    # Test citation discovery
    test_citation = {
        "id": "test-001",
        "page_url": "https://example.com/test-page/",
        "ai_engine": "ChatGPT",
        "citation_text": "According to example.com..."
    }
    
    result = engine.process_new_citation_discovered(test_citation)
    print(f"✅ Citation processing test: {result['geo_optimization_status']}")
    
    # Test velocity check
    velocity_result = engine.run_citation_velocity_check(
        site_url="https://example.com",
        recent_citation_count=15,
        days=7
    )
    print(f"✅ Velocity check test: {velocity_result['status']}")
    print(f"   Velocity: {velocity_result['velocity']:.2f} citations/day")
    
    print("")
    print("🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("")
    print("Make sure you've updated the config file with:")
    print("1. Your Clarity Project ID")
    print("2. Your domain name")

