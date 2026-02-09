"""
Debug Upload - Capture Full Error
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing file upload with detailed error capture...")

files = {
    'boq': ('sample_boq.csv', open('test_data/sample_boq.csv', 'rb'), 'text/csv')
}

try:
    response = requests.post(f"{BASE_URL}/upload/files", files=files)
    files['boq'][1].close()
    
    print(f"Status: {response.status_code}")
    print(f"\nResponse:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
