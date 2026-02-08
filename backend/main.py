from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import shutil
import pydantic
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

from .engine import CostEngine, TimeEngine
from .database import Project

@app.post("/upload/files")
async def upload_files(
    boq: UploadFile = File(None),
    breakdown: UploadFile = File(None),
    schedule: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    upload_dir = "uploaded_files"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Create Project
    project = Project(name=f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    db.add(project)
    db.commit()
    db.refresh(project)
    
    cost_engine = CostEngine(db)
    time_engine = TimeEngine()
    
    results = {"project_id": project.id, "boq_items": 0, "rate_breakdowns": 0, "schedule_tasks": 0}
    
    # Process BOQ
    if boq:
        path = os.path.join(upload_dir, boq.filename)
        with open(path, "wb") as buffer: shutil.copyfileobj(boq.file, buffer)
        results["boq_items"] = cost_engine.load_boq(path, project.id)

    # Process Rate Breakdown
    if breakdown:
        path = os.path.join(upload_dir, breakdown.filename)
        with open(path, "wb") as buffer: shutil.copyfileobj(breakdown.file, buffer)
        results["rate_breakdowns"] = cost_engine.load_rate_breakdown(path, project.id)

    # Process Schedule
    if schedule:
        path = os.path.join(upload_dir, schedule.filename)
        with open(path, "wb") as buffer: shutil.copyfileobj(schedule.file, buffer)
        results["schedule_tasks"] = time_engine.parse_schedule(path)
            
    return {"status": "success", "data": results}

class ChatRequest(pydantic.BaseModel):
    message: str
    project_id: int

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    cost_engine = CostEngine(db)
    # Ensure model is trained on this project (optimization: cache this)
    cost_engine.train_model(request.project_id)
    
    # Parse Instruction
    parsed = cost_engine.ml_model.parse_instruction(request.message)
    
    response_text = "I didn't understand that command. Try 'Change [Item] to [New Material]'."
    proposal_data = None
    
    if parsed['intent'] == 'change_spec':
        # ... (Existing Change Spec Logic) ...
        # [I will keep the existing logic and just append the else if block for delay]
        # BUT replace_file_content replaces the whole block. I must be careful.
        # Since I cannot see the full file content easily in my head, I will assume the previous content.
        # Wait, I can see it from previous turns.
        
        old_desc = parsed['description']
        new_mat = parsed['new_material']
        
        # Find item in BOQ
        item_ref = cost_engine.ml_model.find_similar_item(old_desc)
        
        if item_ref:
            original_rate = item_ref['rate']
            new_rate = cost_engine.calculate_new_rate(new_mat, original_rate, 100.0, 0.05, 50.0)
            diff = new_rate - original_rate
            impact = diff * item_ref.get('quantity', 0)
            
            response_text = (
                f"I found item '{item_ref['description']}' (Rate: {original_rate}). "
                f"Evaluation suggests a Star Rate for '{new_mat}'."
            )
            
            proposal_data = {
                "item_id": item_ref['id'],
                "original_item": item_ref['description'],
                "new_item": new_mat,
                "original_rate": original_rate,
                "new_rate": round(new_rate, 2),
                "cost_impact": round(impact, 2)
            }
        else:
            response_text = f"I could not find '{old_desc}' in the BOQ."

    elif parsed['intent'] == 'delay':
        # Time Impact Analysis
        task_name = parsed['description']
        delay_days = parsed['quantity']
        
        # We need the TimeEngine instance. Ideally, we should persist it or rebuild it.
        # For this prototype, we rebuild it from the uploaded schedule file.
        # We need to find the schedule file path for this project.
        # Simplification: Assume 'schedule.xml' in uploaded_files
        # In a real app, we query Project table for file paths.
        
        time_engine = TimeEngine()
        # Look for the file. 
        # Hack: We know the upload directory.
        schedule_path = f"uploaded_files/schedule.xml" # Assuming user uploaded this specific name or we find it
        # Better: iterate dir
        import os
        if os.path.exists("uploaded_files"):
            for f in os.listdir("uploaded_files"):
                if f.endswith(".xml"):
                    schedule_path = os.path.join("uploaded_files", f)
                    break
        
        nodes_count = time_engine.parse_schedule(schedule_path)
        
        if nodes_count > 0:
            eot, reason = time_engine.calculate_eot(task_name, delay_days)
            
            if eot is not None:
                response_text = f"Analyzed Schedule ({nodes_count} tasks). {reason}"
                proposal_data = {
                    "item_id": "TIME",
                    "original_item": f"Original Completion Date",
                    "new_item": f"New Completion Date (+{eot} days)",
                    "original_rate": 0,
                    "new_rate": 0,
                    "cost_impact": 0, # Could be Liquidated Damages
                    "time_impact": eot
                }
            else:
                response_text = f"Could not find task '{task_name}' in the schedule."
        else:
             response_text = "No schedule file found or failed to parse."

    return {
        "reply": response_text,
        "proposal": proposal_data
    }

    return {
        "reply": response_text,
        "proposal": proposal_data
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
