import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

def create_dummies():
    os.makedirs("test_data", exist_ok=True)
    with open("test_data/sample_boq.csv", "w") as f:
        f.write("Line Item,Description,Quantity,Unit,Rate,Amount\n")
        f.write("1,Excavation,100,m3,500,50000\n")
    with open("test_data/sample_rate_breakdown.csv", "w") as f:
        f.write("Item Ref,Description,Material Cost,Labor Cost,Plant Cost,Total Rate\n")
        f.write("1,Excavation,0,400,100,500\n")
    with open("test_data/sample_schedule.csv", "w") as f:
        f.write("Activity ID,Activity Name,Duration,Start Date,Finish Date,Predecessors\n")
        f.write("A,Excavation,10,2023-01-01,2023-01-10,\n")

create_dummies()

print("="*60)
print("Testing File Upload on 127.0.0.1:8000")
print("="*60)

files = {
    'boq': ('sample_boq.csv', open("test_data/sample_boq.csv", 'rb'), 'text/csv'),
    'breakdown': ('sample_rate_breakdown.csv', open("test_data/sample_rate_breakdown.csv", 'rb'), 'text/csv'),
    'schedule': ('sample_schedule.csv', open("test_data/sample_schedule.csv", 'rb'), 'text/csv')
}

print("Uploading files...")

try:
    response = requests.post(f"{BASE_URL}/upload/files", files=files, timeout=30)
    
    # Close files
    for key in files:
        files[key][1].close()
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nUpload successful!")
        print(json.dumps(data, indent=2))
    else:
        print(f"\nUpload failed:")
        print(response.text)
        
except Exception as e:
    print(f"\nError: {e}")
