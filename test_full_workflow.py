import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    # 1. Create Data
    os.makedirs("test_data", exist_ok=True)
    with open("test_data/test_boq.csv", "w") as f:
        f.write("Line Item,Description,Quantity,Unit,Rate,Amount\n")
        f.write("A1,Reinforced Concrete,50,m3,25000,1250000\n")
        f.write("A2,Plastering,100,m2,1200,120000\n")
    
    with open("test_data/test_rates.csv", "w") as f:
        f.write("Item Ref,Description,Material,Labor,Plant,Total\n")
        f.write("A1,Reinforced Concrete,15000,8000,2000,25000\n")
        f.write("A2,Plastering,400,700,100,1200\n")
    
    with open("test_data/test_schedule.csv", "w") as f:
        f.write("Activity ID,Activity Name,Duration,Start Date,Finish Date,Predecessors\n")
        f.write("T1,Foundations,15,2024-01-01,2024-01-15,\n")
        f.write("T2,Superstructure,30,2024-01-16,2024-02-15,T1\n")

    # 2. Upload
    print("Step 1: Uploading Files...")
    files = {
        'boq': open("test_data/test_boq.csv", 'rb'),
        'breakdown': open("test_data/test_rates.csv", 'rb'),
        'schedule': open("test_data/test_schedule.csv", 'rb')
    }
    
    up_res = requests.post(f"{BASE_URL}/upload/files", files=files, timeout=30)
    for f in files.values(): f.close()
    
    if up_res.status_code != 200:
        print(f"Upload Failed: {up_res.text}")
        return

    data = up_res.json()['data']
    project_id = data['project_id']
    session_id = data['session_id']
    print(f"Upload Success. Project ID: {project_id}, Session ID: {session_id}")

    # 3. Chat
    print("\nStep 2: Testing Chat Interaction...")
    chat_payload = {
        "message": "Increase Reinforced Concrete quantity by 10 units. This is a Quantity Change variation.",
        "project_id": project_id,
        "session_id": session_id
    }
    
    try:
        chat_res = requests.post(f"{BASE_URL}/chat", json=chat_payload, timeout=60)
        if chat_res.status_code == 200:
            chat_data = chat_res.json()
            print("\nAI Reply:")
            print(chat_data['reply'].encode('ascii', 'ignore').decode('ascii'))
            print(f"\nWorkflow State: {chat_data.get('workflow_state')}")
            if chat_data.get('proposal'):
                print("\n✅ PROPOSAL GENERATED!")
                print(json.dumps(chat_data['proposal'], indent=2))
            else:
                print("\n⚠️ No proposal generated in first turn (expected if AI asks for confirmation).")
        else:
            print(f"Chat Failed: {chat_res.text}")
    except Exception as e:
        print(f"Chat Error: {e}")

run_test()
