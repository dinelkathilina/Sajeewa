import requests
BASE_URL = "http://127.0.0.1:8000"
def test():
    # Attempt to chat with project 1 (assuming it exists from previous tests)
    payload = {"message": "Hello, suggest a variation type for adding a new wall", "project_id": 1}
    try:
        r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=20)
        print(f"STATUS: {r.status_code}")
        if r.status_code == 200:
            print("REPLY START")
            print(r.json().get('reply', 'No reply field'))
            print("REPLY END")
        else:
            print(f"ERROR: {r.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
test()
