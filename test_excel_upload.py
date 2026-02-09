import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def test_excel():
    excel_path = "test_data/valid.xlsx"
    if not os.path.exists(excel_path):
        print(f"File not found: {excel_path}")
        return

    files = {
        'boq': ('valid.xlsx', open(excel_path, 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    }
    
    print(f"Uploading {excel_path}...")
    try:
        r = requests.post(f"{BASE_URL}/upload/files", files=files, timeout=30)
        for f in files.values(): f[1].close()
        
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Excel Upload Successful!")
            print(r.json()['data']['processing_notes'])
        else:
            print(f"Excel Upload Failed: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

test_excel()
