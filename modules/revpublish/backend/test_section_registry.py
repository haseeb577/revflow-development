#!/usr/bin/env python3
"""
Validation Test for Section Registry Implementation
Tests that the entire pipeline works end-to-end
"""

import json
import sys
from converters.elementor_mapper import elementor_mapper

# Test data - one row from CSV
TEST_DATA = {
    'site_url': 'dallasgaragedoor.com/spring-replacement',
    'business_name': 'Dallas Garage Door Experts',
    'niche': 'Garage Door Repair',
    'page_type_id': 'service_page',
    'city': 'Dallas',
    'state': 'TX',
    'zip_code': '75201',
    'phone': '214-555-0100',
    'address': '5678 Main Street, Suite 200',
    'email': 'info@dallasgaragedoor.com',
    'service_area': 'Dallas and Fort Worth Metro',
    'hero_slider_images': 'hero-spring-1.jpg|||hero-spring-2.jpg|||hero-spring-3.jpg',
    'testimonial_names': 'John Smith|||Sarah Johnson|||Mike Wilson',
    'testimonial_texts': 'Fixed my broken spring!|||Same day service!|||Professional work!',
    'testimonial_ratings': '5|||5|||5',
    'certification_logos': 'bbb-logo.png|||angi-logo.png|||idea-certified.png'
}

def run_test():
    print("═" * 70)
    print("  REVPUBLISH SECTION REGISTRY VALIDATION TEST")
    print("═" * 70)
    print()
    
    try:
        # Test config
        config = {
            'page_type_id': 'service_page',
            'color_scheme': 'professional',
            'animation_style': 'subtle',
            'field_data': TEST_DATA
        }
        
        print("[1/4] Testing mapper initialization...")
        print("✅ Mapper initialized")
        print()
        
        print("[2/4] Generating Elementor JSON...")
        result = elementor_mapper.map_to_elementor(config)
        print("✅ JSON generated")
        print()
        
        print("[3/4] Validating structure...")
        assert 'content' in result, "Missing 'content' key"
        assert isinstance(result['content'], list), "'content' should be a list"
        assert len(result['content']) > 0, "No sections generated"
        print(f"✅ Generated {len(result['content'])} sections")
        print()
        
        print("[4/4] Checking section types...")
        for i, section in enumerate(result['content']):
            assert 'elType' in section, f"Section {i} missing elType"
            assert 'id' in section, f"Section {i} missing unique ID"
            print(f"  ✅ Section {i+1}: {section.get('elType')}")
        print()
        
        print("═" * 70)
        print("  ✅ ALL TESTS PASSED")
        print("═" * 70)
        print()
        print("Sample output (first 500 chars):")
        print(json.dumps(result, indent=2)[:500])
        print("...")
        
        # Save full output
        with open('/tmp/revpublish_test_output.json', 'w') as f:
            json.dump(result, f, indent=2)
        print()
        print("Full output saved to: /tmp/revpublish_test_output.json")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
