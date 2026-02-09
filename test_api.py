"""
Test API Endpoints
Quick script to test the backend API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("Testing Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\n" + "="*60)
    print("Testing Root Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_variation_types():
    """Test variation types endpoint"""
    print("\n" + "="*60)
    print("Testing Variation Types Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/variation-types")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if 'variation_types' in data:
            print(f"Found {len(data['variation_types'])} variation types:")
            for vtype in data['variation_types']:
                print(f"  - {vtype['code']}: {vtype['name']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_api_docs():
    """Test API documentation"""
    print("\n" + "="*60)
    print("Testing API Documentation")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Status Code: {response.status_code}")
        print(f"API Docs available at: {BASE_URL}/docs")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BACKEND API ENDPOINT TESTS")
    print("="*60)
    print(f"Testing API at: {BASE_URL}")
    
    results = []
    
    results.append(("Root Endpoint", test_root()))
    results.append(("Health Check", test_health()))
    results.append(("Variation Types", test_variation_types()))
    results.append(("API Documentation", test_api_docs()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All API tests passed!")
        print(f"\n📚 API Documentation: {BASE_URL}/docs")
        print(f"📊 Interactive API: {BASE_URL}/redoc")
    else:
        print("\n⚠ Some tests failed. Check if server is running.")
    
    return passed == total

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
