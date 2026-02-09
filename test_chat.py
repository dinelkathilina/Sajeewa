"""
Test Chat Endpoint with FIDIC Workflow
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("="*60)
print("Testing Chat Endpoint")
print("="*60)

# First, upload files to get project and session
print("\n1. Uploading test files...")
files = {
    'boq': ('sample_boq.csv', open('test_data/sample_boq.csv', 'rb'), 'text/csv'),
    'breakdown': ('sample_rate_breakdown.csv', open('test_data/sample_rate_breakdown.csv', 'rb'), 'text/csv'),
    'schedule': ('sample_schedule.csv', open('test_data/sample_schedule.csv', 'rb'), 'text/csv')
}

response = requests.post(f"{BASE_URL}/upload/files", files=files)
for file_tuple in files.values():
    file_tuple[1].close()

if response.status_code != 200:
    print("Upload failed!")
    print(response.text)
    exit(1)

data = response.json()['data']
project_id = data['project_id']
session_id = data['session_id']

print(f"Project ID: {project_id}")
print(f"Session ID: {session_id}")
print(f"BOQ Items: {data['boq_items']}")
print(f"Schedule Tasks: {data['schedule_tasks']}")

# Test chat messages
test_conversations = [
    {
        "message": "I need to evaluate a variation for Guard Stones",
        "description": "Initial variation request"
    },
    {
        "message": "Increase quantity from 150 to 200 units",
        "description": "Quantity change specification"
    },
    {
        "message": "What is the cost impact?",
        "description": "Cost impact query"
    }
]

print("\n" + "="*60)
print("Chat Conversation")
print("="*60)

for i, conv in enumerate(test_conversations, 1):
    print(f"\n--- Message {i}: {conv['description']} ---")
    print(f"User: {conv['message']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": conv['message'],
                "project_id": project_id,
                "session_id": session_id
            }
        )
        
        if response.status_code == 200:
            chat_data = response.json()
            
            # Display AI response
            ai_reply = chat_data.get('reply', 'No response')
            print(f"\nAI: {ai_reply[:300]}...")
            
            # Display workflow state
            if 'workflow_state' in chat_data:
                print(f"Workflow State: {chat_data['workflow_state']}")
            
            # Display proposal if generated
            if chat_data.get('proposal'):
                print("\n*** PROPOSAL GENERATED ***")
                proposal = chat_data['proposal']
                print(f"Item ID: {proposal.get('item_id')}")
                print(f"Original Item: {proposal.get('original_item')}")
                print(f"New Item: {proposal.get('new_item')}")
                print(f"Cost Impact: ${proposal.get('cost_impact', 0):.2f}")
                print(f"Time Impact: {proposal.get('time_impact', 0)} days")
                
                # Save for PDF generation
                if i == len(test_conversations):
                    final_proposal = proposal
                    final_proposal['project_id'] = project_id
                    final_proposal['session_id'] = session_id
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*60)
print("Chat Testing Complete")
print("="*60)
