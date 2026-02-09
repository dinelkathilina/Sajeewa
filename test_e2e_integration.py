import requests
import os
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def create_dummy_files():
    # BOQ
    with open("dummy_boq.csv", "w") as f:
        f.write("Line Item,Description,Quantity,Unit,Rate,Amount\n")
        f.write("1,Excavation,100,m3,500,50000\n")
        f.write("2,Concrete,50,m3,15000,750000\n")
        f.write("3,Brickwork,200,m2,2500,500000\n")

    # Rate Breakdown
    with open("dummy_rates.csv", "w") as f:
        f.write("Item Ref,Description,Material Cost,Labor Cost,Plant Cost,Total Rate\n")
        f.write("1,Excavation,0,400,100,500\n")
        f.write("2,Concrete,10000,4000,1000,15000\n")
        f.write("3,Brickwork,1500,800,200,2500\n")

    # Schedule
    with open("dummy_schedule.csv", "w") as f:
        f.write("Activity ID,Activity Name,Duration,Start Date,Finish Date,Predecessors\n")
        f.write("A,Excavation,10,2023-01-01,2023-01-10,\n")
        f.write("B,Concrete,15,2023-01-11,2023-01-25,A\n")
        f.write("C,Brickwork,20,2023-01-26,2023-02-15,B\n")

def test_health():
    print("Testing Health...")
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200
    print("Health OK")

def test_upload_flow():
    print("Testing Upload...")
    create_dummy_files()
    files = {
        'boq': open('dummy_boq.csv', 'rb'),
        'breakdown': open('dummy_rates.csv', 'rb'),
        'schedule': open('dummy_schedule.csv', 'rb')
    }
    r = requests.post(f"{BASE_URL}/upload/files", files=files, timeout=30)
    if r.status_code != 200:
        print(r.text)
    assert r.status_code == 200
    data = r.json()
    print(f"Upload OK. Project ID: {data['data']['project_id']}")
    
    # Cleanup
    files['boq'].close()
    files['breakdown'].close()
    files['schedule'].close()
    os.remove('dummy_boq.csv')
    os.remove('dummy_rates.csv')
    os.remove('dummy_schedule.csv')
    
    return data['data']['project_id'], data['data']['session_id']

def test_chat_variation(project_id, session_id):
    print("Testing Chat Variation...")
    # Simulate a variation request
    payload = {
        "message": "Change Brickwork quantity by +50",
        "project_id": project_id,
        "session_id": session_id
    }
    r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=60) # Chat might take longer
    if r.status_code != 200:
        print(r.json())
    assert r.status_code == 200
    data = r.json()
    
    # Check if proposal is returned
    if data.get('proposal'):
        print("Proposal Generated via Chat!")
        return data['proposal']
    else:
        print("Chat response:", data['reply'])
        return data.get('proposal')

def test_review_loop(variation_id):
    print(f"Testing Review Loop for Variation {variation_id}...")
    
    # 1. Get Details
    r = requests.get(f"{BASE_URL}/variation/{variation_id}", timeout=10)
    assert r.status_code == 200
    var_data = r.json()
    detail_id = var_data['details'][0]['id']
    original_cost = var_data['cost_impact']
    print(f"Original Cost: {original_cost}")
    
    # 2. Update Detail (Change Rate)
    updates = {"new_rate": 3000}
    r = requests.put(f"{BASE_URL}/variation/{variation_id}/details/{detail_id}", json=updates, timeout=10)
    assert r.status_code == 200
    
    # 3. Verify Recalculation
    r = requests.get(f"{BASE_URL}/variation/{variation_id}", timeout=10)
    new_cost = r.json()['cost_impact']
    print(f"New Cost: {new_cost}")
    assert new_cost != original_cost
    
    # 4. Approve
    r = requests.post(f"{BASE_URL}/variation/{variation_id}/status", json={"status": "Approved"}, timeout=10)
    assert r.status_code == 200
    assert r.json()['new_status'] == "Approved"
    print("Variation Approved")

def test_pdf_generation(variation_id):
    print("Testing PDF Generation...")
    payload = {"variation_id": variation_id}
    r = requests.post(f"{BASE_URL}/generate-pdf", json=payload, timeout=30)
    if r.status_code != 200:
        print(f"PDF Error: {r.text}")
    assert r.status_code == 200
    assert r.headers['content-type'] == 'application/pdf'
    print("PDF Generated Successfully")

if __name__ == "__main__":
    try:
        test_health()
        pid, sid = test_upload_flow()
        proposal = test_chat_variation(pid, sid)
        
        if proposal and 'variation_id' in proposal:
            test_review_loop(proposal['variation_id'])
            test_pdf_generation(proposal['variation_id'])
            print("\n✅ E2E INTEGRATION TEST PASSED!")
        else:
            print("\n⚠️ Chat did not generate a proposal. E2E incomplete.")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
