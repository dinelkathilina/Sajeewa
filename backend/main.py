from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import shutil
import pydantic
import os
from datetime import datetime
from .database import engine, init_db, SessionLocal
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load .env
load_dotenv()

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
from .database import Project, BOQItem

@app.post("/upload/files")
async def upload_files(
    boq: UploadFile = File(None),
    breakdown: UploadFile = File(None),
    schedule: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Create Project (Use BOQ filename as name)
        proj_name = boq.filename.split('.')[0] if boq else f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project = Project(name=proj_name, boq_filename=boq.filename if boq else None)
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
    except Exception as e:
        print(f"UPLOAD CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

class ChatRequest(pydantic.BaseModel):
    message: str
    project_id: int

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    cost_engine = CostEngine(db)
    # Ensure model is trained on this project (optimization: cache this)
    # 1. Get Context (Search for relevant items first to help AI)
    project = db.query(Project).filter(Project.id == request.project_id).first()
    proj_name = project.name if project else "Unknown Project"
    
    # Simple keyword search for relevant items to provide as context
    search_query = request.message.split()[-1]
    relevant_items = db.query(BOQItem).filter(BOQItem.project_id == request.project_id).filter(BOQItem.description.like(f"%{search_query}%")).limit(10).all()
    if not relevant_items:
        relevant_items = db.query(BOQItem).filter(BOQItem.project_id == request.project_id).limit(10).all()
    
    context_str = f"PROJECT NAME: {proj_name}\n"
    context_str += "\n".join([f"- {i.description} (Rate: {i.rate}, Qty: {i.quantity})" for i in relevant_items])

    # 2. Parse/Reason with Context
    ai_result = cost_engine.ml_model.parse_instruction(request.message, project_context=context_str)
    
    if not ai_result:
        return {"reply": "Connection error with AI service.", "proposal": None}

    response_text = ai_result.get('reply', "How can I help you today?")
    proposal_data = None
    cmd = ai_result.get('command')

    # 3. Handle Command if detected
    if cmd and cmd.get('intent'):
        intent = cmd['intent']
        desc_query = cmd.get('description')
        
        if intent in ['change_spec', 'change_qty']:
            item_ref = cost_engine.ml_model.find_similar_item(desc_query)
            if item_ref:
                original_rate = item_ref['rate']
                if intent == 'change_spec':
                    new_mat = cmd.get('new_material', 'New Material')
                    new_rate = cost_engine.calculate_new_rate(new_mat, original_rate, 100.0, 0.05, 50.0)
                else:
                    new_rate = original_rate

                diff = new_rate - original_rate
                impact = diff * item_ref.get('quantity', 0)
                
                proposal_data = {
                    "item_id": item_ref['id'],
                    "original_item": item_ref['description'],
                    "new_item": cmd.get('new_material') or item_ref['description'],
                    "original_rate": original_rate,
                    "new_rate": round(new_rate, 2),
                    "cost_impact": round(impact, 2)
                }
            else:
                response_text += f"\n(Note: I couldn't find an exact match for '{desc_query}' in the database to calculate costs.)"

        elif intent == 'delay':
            # Time Impact Analysis
            task_name_query = cmd.get('description')
            delay_days = cmd.get('quantity', 0)
            
            time_engine = TimeEngine()
            # Iteratively look for schedule files
            schedule_path = None
            if os.path.exists("uploaded_files"):
                for f in os.listdir("uploaded_files"):
                    if f.endswith(".xml") or f.endswith(".csv") or "plan" in f.lower() or "schedule" in f.lower():
                        schedule_path = os.path.join("uploaded_files", f)
                        break
            
            if schedule_path:
                nodes_count = time_engine.parse_schedule(schedule_path)
                if nodes_count > 0:
                    eot, reason = time_engine.calculate_eot(task_name_query, delay_days)
                    if eot is not None:
                        proposal_data = {
                            "item_id": "TIME",
                            "original_item": "Original Schedule",
                            "new_item": f"Revised Schedule (+{eot} days)",
                            "original_rate": 0,
                            "new_rate": 0,
                            "cost_impact": 0,
                            "time_impact": eot
                        }
                    else:
                        response_text += f"\n(Note: I couldn't find task '{task_name_query}' in the project schedule.)"
                else:
                    response_text += "\n(Note: The schedule file was found but couldn't be parsed.)"
            else:
                response_text += "\n(Note: No project schedule (MSP/Excel) found to evaluate time impact.)"

    return {
        "reply": response_text,
        "proposal": proposal_data
    }

from .pdf_utils import PDFGenerator
from fastapi.responses import FileResponse

@app.post("/generate-pdf")
async def generate_pdf(request: dict):
    # For now, just a temporary file path
    output_path = "variation_proposal.pdf"
    PDFGenerator.generate_variation_proposal(request, output_path)
    return FileResponse(output_path, media_type="application/pdf", filename="Variation_Proposal.pdf")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
