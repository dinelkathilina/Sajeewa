"""
Test File Upload Endpoint
Tests uploading BOQ, Rate Breakdown, and Schedule files
"""
import requests
import json
import os

BASE_URL = "http://localhost:8000"

def test_file_upload():
    """Test file upload endpoint"""
    print("\n" + "="*60)
    print("Testing File Upload Endpoint")
    print("="*60)
    
    # Prepare files
    files = {}
    
    boq_path = "test_data/sample_boq.csv"
    breakdown_path = "test_data/sample_rate_breakdown.csv"
    schedule_path = "test_data/sample_schedule.csv"
    
    if os.path.exists(boq_path):
        files['boq'] = ('sample_boq.csv', open(boq_path, 'rb'), 'text/csv')
        print(f"✓ BOQ file ready: {boq_path}")
    
    if os.path.exists(breakdown_path):
        files['breakdown'] = ('sample_rate_breakdown.csv', open(breakdown_path, 'rb'), 'text/csv')
        print(f"✓ Rate breakdown file ready: {breakdown_path}")
    
    if os.path.exists(schedule_path):
        files['schedule'] = ('sample_schedule.csv', open(schedule_path, 'rb'), 'text/csv')
        print(f"✓ Schedule file ready: {schedule_path}")
    
    if not files:
        print("✗ No test files found in test_data/ directory")
        return None
    
    try:
        print("\nUploading files...")
        response = requests.post(f"{BASE_URL}/upload/files", files=files)
        
        # Close file handles
        for file_tuple in files.values():
            file_tuple[1].close()
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Upload successful!")
            print(json.dumps(data, indent=2))
            
            if 'data' in data:
                project_data = data['data']
                print(f"\nProject ID: {project_data.get('project_id')}")
                print(f"Session ID: {project_data.get('session_id')}")
                print(f"BOQ Items: {project_data.get('boq_items')}")
                print(f"Rate Breakdowns: {project_data.get('rate_breakdowns')}")
                print(f"Schedule Tasks: {project_data.get('schedule_tasks')}")
                
                if 'critical_path_activities' in project_data:
                    print(f"Critical Path Activities: {project_data.get('critical_path_activities')}")
                
                if 'processing_notes' in project_data:
                    print("\nProcessing Notes:")
                    for note in project_data['processing_notes']:
                        print(f"  {note}")
                
                return project_data
        else:
            print(f"✗ Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_chat_endpoint(project_id, session_id):
    """Test chat endpoint with FIDIC workflow"""
    print("\n" + "="*60)
    print("Testing Chat Endpoint")
    print("="*60)
    
    # Test messages
    test_messages = [
        "I need to evaluate a variation for Guard Stones",
        "Increase quantity from 150 to 200 units",
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"User: {message}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "message": message,
                    "project_id": project_id,
                    "session_id": session_id
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"AI: {data.get('reply', 'No response')[:200]}...")
                
                if 'workflow_state' in data:
                    print(f"Workflow State: {data['workflow_state']}")
                
                if data.get('proposal'):
                    print("\n✓ Proposal generated!")
                    proposal = data['proposal']
                    print(f"  Cost Impact: ${proposal.get('cost_impact', 0)}")
                    print(f"  Time Impact: {proposal.get('time_impact', 0)} days")
            else:
                print(f"✗ Chat failed: {response.text}")
                
        except Exception as e:
            print(f"✗ Error: {e}")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BACKEND ENDPOINT TESTING")
    print("="*60)
    
    # Test file upload
    upload_result = test_file_upload()
    
    if upload_result:
        project_id = upload_result.get('project_id')
        session_id = upload_result.get('session_id')
        
        if project_id and session_id:
            # Test chat endpoint
            test_chat_endpoint(project_id, session_id)
        else:
            print("\n⚠ No project/session ID returned, skipping chat test")
    else:
        print("\n⚠ File upload failed, skipping further tests")
    
    print("\n" + "="*60)
    print("Testing Complete")
    print("="*60)

if __name__ == "__main__":
    main()
