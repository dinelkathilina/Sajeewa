from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import shutil
import os
from .database import engine, init_db, SessionLocal
from sqlalchemy.orm import Session

# Initialize DB
init_db()

app = FastAPI(title="Construction Variation Chatbot")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Construction Variation Chatbot API is running"}

@app.post("/upload/files")
async def upload_files(
    boq: UploadFile = File(None),
    breakdown: UploadFile = File(None),
    schedule: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    upload_dir = "uploaded_files"
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_files = {}
    
    for file, name in [(boq, "boq"), (breakdown, "breakdown"), (schedule, "schedule")]:
        if file:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files[name] = file_path
            
    return {"status": "success", "files": saved_files}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
