"""
Simple API Test - Quick Check
"""
import urllib.request
import json

def test_endpoint(url, name):
    """Test a single endpoint"""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"✓ {name}: {response.status}")
            print(f"  Response: {json.dumps(data, indent=2)[:200]}")
            return True
    except Exception as e:
        print(f"✗ {name}: {e}")
        return False

print("Testing Backend API...")
print("="*60)

results = []
results.append(test_endpoint("http://localhost:8000/", "Root"))
results.append(test_endpoint("http://localhost:8000/health", "Health"))
results.append(test_endpoint("http://localhost:8000/variation-types", "Variation Types"))

print("="*60)
print(f"Results: {sum(results)}/{len(results)} passed")

if sum(results) == len(results):
    print("\n✓ Backend API is working!")
    print("  API Docs: http://localhost:8000/docs")
else:
    print("\n⚠ Some endpoints failed")
