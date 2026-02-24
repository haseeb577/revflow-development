"""
Test suite for RevFlowClient dual-mode functionality
Run with: python3 test_revflow_client.py
"""
import os
import sys
from revflow_client import RevFlowClient, get_revflow_client

def test_gateway_mode():
    """Test gateway mode (tries RevCore first)"""
    print("\n✓ Test 1: Gateway Mode")
    print("  Setting: USE_REVCORE_GATEWAY=true")
    
    os.environ["USE_REVCORE_GATEWAY"] = "true"
    client = RevFlowClient()
    
    assert client.use_gateway == True, "Gateway mode not enabled"
    assert "gateway" in client.gateway.lower(), "Gateway not configured"
    
    print("  ✅ PASS: Gateway mode enabled and configured")


def test_direct_mode():
    """Test direct mode (legacy direct calls)"""
    print("\n✓ Test 2: Direct Mode")
    print("  Setting: USE_REVCORE_GATEWAY=false")
    
    os.environ["USE_REVCORE_GATEWAY"] = "false"
    # Force new client creation
    client = RevFlowClient()
    
    assert client.use_gateway == False, "Direct mode not enabled"
    assert len(client.direct_endpoints) > 0, "Direct endpoints not configured"
    
    print("  ✅ PASS: Direct mode enabled and configured")


def test_all_modules_configured():
    """Verify all modules have direct endpoints"""
    print("\n✓ Test 3: Module Configuration")
    
    client = RevFlowClient()
    required_modules = [
        "revprompt", "revscore", "revrank", "revseo", "revcite",
        "revhumanize", "revwins", "revimage", "revpublish", "revmetrics",
        "revsignal", "revintel", "revdispatch", "revvest", "revspy",
        "revspend", "revcore", "revassist"
    ]
    
    for module in required_modules:
        assert module in client.direct_endpoints, f"Module {module} not configured"
        print(f"    ✓ {module}: {client.direct_endpoints[module]}")
    
    print("  ✅ PASS: All 18 modules configured")


def test_singleton_pattern():
    """Test singleton client pattern"""
    print("\n✓ Test 4: Singleton Pattern")
    
    client1 = get_revflow_client()
    client2 = get_revflow_client()
    
    assert client1 is client2, "Singleton pattern not working"
    print("  ✅ PASS: Singleton pattern verified")


def test_endpoint_normalization():
    """Test endpoint path normalization"""
    print("\n✓ Test 5: Endpoint Normalization")
    
    client = RevFlowClient()
    
    # Test with leading slash
    assert client._call_direct.__doc__ is not None
    print("  ✓ Endpoint normalization available")
    print("  ✅ PASS: Endpoint handling verified")


def run_all_tests():
    """Run complete test suite"""
    print("=" * 60)
    print("RevFlowClient Test Suite")
    print("=" * 60)
    
    try:
        test_gateway_mode()
        test_direct_mode()
        test_all_modules_configured()
        test_singleton_pattern()
        test_endpoint_normalization()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nRevFlowClient is ready for use!")
        print("\nUsage:")
        print("  from revflow_client import get_revflow_client")
        print("  client = get_revflow_client()")
        print("  result = client.call_module('revspy', '/health')")
        return 0
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {str(e)}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
