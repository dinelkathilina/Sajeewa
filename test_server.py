import uvicorn
from backend.main import app

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    print(f"DEBUG: GROQ_API_KEY present: {bool(key)}")
    if key:
        print(f"DEBUG: Key starts with: {key[:5]}...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
