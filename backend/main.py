from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
import uvicorn
import shutil
import pydantic
import os
from datetime import datetime
from .storage_manager import StorageManager, storage_manager
from dotenv import load_dotenv

# Load .env
load_dotenv()

# storage_manager is initialized in its own module

app = FastAPI(
    title="ML Construction Variation Evaluation System",
    description="FIDIC-compliant variation assessment with ML predictions",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_storage() -> StorageManager:
    return storage_manager

# Import engines and managers
from .engine import CostEngine, TimeEngine
from .session_manager import SessionManager
from .validation_engine import ValidationEngine
from .ocr_processor import ocr_processor
from .pdf_utils import PDFGenerator

@app.get("/")
def read_root():
    return {
        "message": "ML Construction Variation Evaluation System API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/variation-types")
def get_variation_types():
    """Get all FIDIC variation types (Static for now)"""
    return {
        "variation_types": [
            {"id": 1, "code": "TYPE1", "name": "Quantity Changes", "description": "Changes in the quantity of any item of work included in the Contract"},
            {"id": 2, "code": "TYPE2", "name": "Quality/Characteristics Changes", "description": "Changes in the quality or other characteristics of any item of work"},
            {"id": 3, "code": "TYPE3", "name": "Levels/Positions/Dimensions Changes", "description": "Changes in the levels, positions and/or dimensions of any part of the Works"},
            {"id": 4, "code": "TYPE4", "name": "Omission of Work", "description": "Omission of any work unless it is to be carried out by others"},
            {"id": 5, "code": "TYPE5", "name": "Additional Work/Plant/Materials", "description": "Any additional work, Plant, Materials or services necessary for the Works"},
            {"id": 6, "code": "TYPE6", "name": "Sequence/Timing Changes", "description": "Changes to the sequence or timing of the execution of the Works"}
        ]
    }

# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================

@app.post("/upload/files")
async def upload_files(
    boq: UploadFile = File(None),
    breakdown: UploadFile = File(None),
    schedule: UploadFile = File(None),
    storage: StorageManager = Depends(get_storage)
):
    """
    Upload core project files (BOQ, Rate Breakdown, Schedule)
    Supports Excel and CSV for BOQ/Schedule, PDF/Excel/CSV for Rate Breakdown
    """
    try:
        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Create Project
        proj_name = boq.filename.split('.')[0] if boq else f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project = storage.create_project(
            name=proj_name,
            boq_filename=boq.filename if boq else None,
            rate_breakdown_filename=breakdown.filename if breakdown else None,
            schedule_filename=schedule.filename if schedule else None
        )
        project_id = project["id"]
        
        # Initialize engines
        cost_engine = CostEngine(storage)
        time_engine = TimeEngine(storage=storage)
        
        # Initialize session manager and create default session
        session_manager = SessionManager(storage)
        session = session_manager.create_session(
            project_id=project_id,
            metadata={"created_via": "file_upload", "files_uploaded": []}
        )
        
        results = {
            "project_id": project_id,
            "session_id": session["id"],
            "session_key": session["session_key"],
            "boq_items": 0,
            "rate_breakdowns": 0,
            "schedule_tasks": 0,
            "processing_notes": []
        }
        
        # Process BOQ
        if boq:
            path = os.path.join(upload_dir, boq.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(boq.file, buffer)
            
            # Validate BOQ
            validation = cost_engine.validate_boq_file(path)
            if not validation['valid']:
                os.remove(path)
                raise HTTPException(status_code=400, detail={
                    "message": f"BOQ Validation Failed for '{boq.filename}'",
                    "errors": validation['errors']
                })

            boq_data = cost_engine.load_boq(path, project_id) # Returns dict of sheets
            total_items = 0
            for sheet_name, items in boq_data.items():
                count = storage.add_boq_items(project_id, items, sheet_name)
                total_items += count
            
            results["boq_items"] = total_items
            results["processing_notes"].append(f"✓ BOQ processed: {total_items} items across {len(boq_data)} sheets")
            
            # Update session metadata
            session_manager.update_session_metadata(project_id, session["id"], {
                "files_uploaded": ["boq"]
            })
        
        # Process Rate Breakdown
        if breakdown:
            path = os.path.join(upload_dir, breakdown.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(breakdown.file, buffer)
            
            # Rate breakdown processing
            if ocr_processor.is_pdf(path):
                df = ocr_processor.process_pdf(path)
                if df is not None:
                    items = cost_engine.save_rate_breakdown_df(df, project_id)
                    results["rate_breakdowns"] = storage.add_rate_breakdowns(project_id, items)
            else:
                items = cost_engine.load_rate_breakdown(path, project_id)
                results["rate_breakdowns"] = storage.add_rate_breakdowns(project_id, items)
            
            results["processing_notes"].append(f"✓ Rate breakdown processed: {results['rate_breakdowns']} items")
        
        # Process Schedule
        if schedule:
            path = os.path.join(upload_dir, schedule.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(schedule.file, buffer)
            
            activities = time_engine.parse_schedule(path, project_id=project_id)
            results["schedule_tasks"] = storage.add_activities(project_id, activities)
            results["processing_notes"].append(f"✓ Schedule processed: {results['schedule_tasks']} activities")
        
        return {"status": "success", "data": results}
        
    except Exception as e:
        print(f"UPLOAD ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
def get_projects(storage: StorageManager = Depends(get_storage)):
    """List all projects"""
    return {"projects": storage.get_projects()}

@app.post("/upload/quotation")
async def upload_quotation(
    file: UploadFile = File(...)
):
    """
    Upload a vendor quotation (PDF, Excel, CSV)
    Extracts rates for use in Star Rate derivation.
    """
    try:
        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"quotation_{int(datetime.now().timestamp())}_{file.filename}"
        path = os.path.join(upload_dir, filename)
        
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        extracted_data = []
        
        # Process based on file type
        if ocr_processor.is_pdf(path):
            df = ocr_processor.process_pdf(path, mode='quotation')
            if df is not None and not df.empty:
                extracted_data = df.to_dict('records')
        
        return {
            "status": "success",
            "filename": filename,
            "extracted_items_count": len(extracted_data),
            "preview": extracted_data[:5] if extracted_data else []
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/additional-files")
async def upload_additional_files(
    project_id: int = Form(...),
    variation_id: Optional[int] = Form(None),
    file_type: str = Form(...),  # 'bsr', 'hsr', 'quotation', 'specification', 'drawing'
    files: List[UploadFile] = File(...),
    storage: StorageManager = Depends(get_storage)
):
    """Upload additional supporting files (BSR, HSR, Quotations, etc.)"""
    try:
        upload_dir = "uploaded_files/additional"
        os.makedirs(upload_dir, exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            # Save file
            file_path = os.path.join(upload_dir, f"{project_id}_{file.filename}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Create record in storage
            file_data = {
                "variation_id": variation_id,
                "filename": file.filename,
                "file_type": file_type,
                "file_path": file_path
            }
            storage.add_additional_file(project_id, file_data)
            
            uploaded_files.append({
                "filename": file.filename,
                "type": file_type,
                "size": os.path.getsize(file_path)
            })
        
        return {
            "status": "success",
            "files_uploaded": len(uploaded_files),
            "files": uploaded_files
        }
        
    except Exception as e:
        print(f"ADDITIONAL FILES UPLOAD ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/session/create")
def create_session(
    project_id: int,
    metadata: Optional[Dict] = None,
    storage: StorageManager = Depends(get_storage)
):
    """Create a new conversation session"""
    session_manager = SessionManager(storage)
    session = session_manager.create_session(project_id, metadata)
    return session

@app.get("/session/{project_id}/{session_id}")
def get_session(project_id: int, session_id: int, storage: StorageManager = Depends(get_storage)):
    """Get session context"""
    session_manager = SessionManager(storage)
    context = session_manager.get_session_context(project_id, session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    return context

@app.post("/session/{project_id}/{session_id}/continue")
def continue_session(project_id: int, session_id: int, storage: StorageManager = Depends(get_storage)):
    """Continue an existing session"""
    session_manager = SessionManager(storage)
    try:
        context = session_manager.continue_session(project_id, session_id)
        return {"status": "success", "context": context}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/session/{project_id}/{session_id}/close")
def close_session(project_id: int, session_id: int, storage: StorageManager = Depends(get_storage)):
    """Close/complete a session"""
    session_manager = SessionManager(storage)
    success = session_manager.close_session(project_id, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Session closed"}

# ============================================================================
# CHAT ENDPOINT (Enhanced with FIDIC Workflow)
# ============================================================================

class ChatRequest(pydantic.BaseModel):
    message: str
    project_id: int
    session_id: Optional[int] = None

@app.post("/chat")
async def chat(request: ChatRequest, storage: StorageManager = Depends(get_storage)):
    """
    Enhanced chat endpoint with FIDIC workflow support
    """
    try:
        # Initialize managers and engines
        session_manager = SessionManager(storage)
        cost_engine = CostEngine(storage)
        time_engine = TimeEngine(storage=storage)
        
        # Get or create session
        project_id = request.project_id
        if request.session_id:
            session = session_manager.get_session(project_id, request.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = session_manager.create_session(project_id)
        
        session_id = session["id"]
        
        # Save user message
        session_manager.add_message(project_id, session_id, "user", request.message)
        
        # Get conversation history
        history = session_manager.get_conversation_history(project_id, session_id, limit=10)
        
        # 2. Enrich Context for AI
        cost_engine.train_model(project_id)
        session_metadata = session.get("session_metadata", {})
        collected_details = session_metadata.get('collected_details', {})
        
        search_query = request.message
        if len(request.message.split()) < 4:
            affected_items = collected_details.get('affected_items', [])
            if affected_items:
                search_query += " " + " ".join(affected_items)
            user_history = [m['content'] for m in history if m['role'] == 'user'][-3:]
            search_query += " " + " ".join(user_history)

        # Get relevant BOQ items
        relevant_matches = cost_engine.ml_model.find_similar_item(search_query, top_n=20)
        
        project = storage.get_project(project_id)
        proj_name = project.get("name", "Unknown Project")
        
        context_str = f"PROJECT NAME: {proj_name}\n"
        context_str += "AVAIALBLE BOQ ITEMS (Top Matches):\n"
        context_str += "\n".join([f"- {i['description']} (Ref: {i['item_number']}, Rate: {i['rate']}, Qty: {i['quantity']})" for i in relevant_matches if i])
        
        # Get relevant activities
        activities = project.get("activities", [])
        keywords = search_query.lower().split()
        relevant_activities = [a for a in activities if any(k in a.get('name', '').lower() for k in keywords)]
        
        context_str += "\n\nAVAIALBLE ACTIVITIES (Top Matches):\n"
        if relevant_activities:
            context_str += "\n".join([f"- {a.get('name')} (Duration: {a.get('duration')}d, Critical: {a.get('is_critical')})" for a in relevant_activities[:10]])
        else:
            context_str += "\n".join([f"- {a.get('name')} (Duration: {a.get('duration')}d, Critical: {a.get('is_critical')})" for a in activities[:5]])
        
        # 3. Parse instruction with workflow support
        ai_result = cost_engine.ml_model.parse_instruction(
            request.message,
            project_context=context_str,
            chat_history=history,
            session_metadata=session_metadata
        )
        
        if not ai_result:
            return {"reply": "Connection error with AI service.", "proposal": None, "session_id": session_id}
        
        response_text = ai_result.get('reply', "How can I help you today?")
        workflow_state = ai_result.get('workflow_state')
        proposal_data = None
        
        # Handle workflow states
        if workflow_state == "type_selection":
            suggested_type = ai_result.get('suggested_type')
            if suggested_type:
                session_manager.update_session_metadata(project_id, session_id, {"variation_type": suggested_type})
        
        elif workflow_state == "collecting_details":
            extracted_data = ai_result.get('extracted_data', {})
            current_details = session_metadata.get('collected_details', {})
            current_details.update({k: v for k, v in extracted_data.items() if v is not None})
            
            session_manager.update_session_metadata(project_id, session_id, {"collected_details": current_details})
            
            if extracted_data.get('complete'):
                eval_result = cost_engine.evaluate_variation_full(current_details, project_id, session_id)
                if eval_result:
                    proposal_data = eval_result
                    from .pdf_utils import PDFGenerator
                    pdf_gen = PDFGenerator()
                    output_path = f"variation_proposal_{eval_result['variation_id']}.pdf"
                    try:
                        pdf_path = pdf_gen.generate_variation_proposal(eval_result, output_path)
                        proposal_data['pdf_url'] = f"http://localhost:8000/download/{os.path.basename(pdf_path)}"
                        response_text += f"\n\nEvaluation complete! I've calculated a cost impact of ${eval_result['cost_impact']:,.2f} and a time impact of {eval_result['time_impact']} days. You can download the report here: {proposal_data['pdf_url']}"
                    except Exception as e:
                        response_text += "\n\nEvaluation complete, but I couldn't generate the PDF report."

        # Save AI response
        session_manager.add_message(project_id, session_id, "ai", response_text, metadata={
            "workflow_state": workflow_state,
            "has_proposal": proposal_data is not None
        })
        
        return {
            "reply": response_text,
            "proposal": proposal_data,
            "session_id": session_id,
            "workflow_state": workflow_state
        }
        
    except Exception as e:
        print(f"CHAT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

# ============================================================================
# VARIATION MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/variation/{project_id}/{variation_id}")
def get_variation(project_id: int, variation_id: int, storage: StorageManager = Depends(get_storage)):
    """Get variation details"""
    variation = storage.get_variation(project_id, variation_id)
    if not variation:
        raise HTTPException(status_code=404, detail="Variation not found")
    return variation

@app.post("/variation/validate/{project_id}/{variation_id}")
def validate_variation(project_id: int, variation_id: int, storage: StorageManager = Depends(get_storage)):
    """Run QS validation checks on a variation"""
    validator = ValidationEngine(storage)
    results = validator.validate_variation(project_id, variation_id)
    return results

@app.get("/variation/validation-report/{project_id}/{variation_id}")
def get_validation_report(project_id: int, variation_id: int, storage: StorageManager = Depends(get_storage)):
    """Get formatted validation report"""
    validator = ValidationEngine(storage)
    report = validator.generate_validation_report(project_id, variation_id)
    return {"report": report}

@app.put("/variation/{project_id}/{variation_id}/details/{detail_id}")
def update_variation_detail_endpoint(
    project_id: int,
    variation_id: int, 
    detail_id: int, 
    updates: dict,
    storage: StorageManager = Depends(get_storage)
):
    """Update a specific variation detail line item"""
    cost_engine = CostEngine(storage)
    updated_detail = cost_engine.update_variation_detail(project_id, variation_id, detail_id, updates)
    
    if not updated_detail:
        raise HTTPException(status_code=404, detail="Variation detail not found")
        
    return {"status": "success", "detail_id": detail_id, "message": "Detail updated"}

@app.post("/variation/{project_id}/{variation_id}/status")
def update_variation_status(
    project_id: int,
    variation_id: int,
    status: str = Body(..., embed=True),
    storage: StorageManager = Depends(get_storage)
):
    """Update variation status (Approved, Rejected, Under Review)"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    found = False
    for v in project.get("variations", []):
        if v["id"] == variation_id:
            if status not in ["Draft", "Under Review", "Approved", "Rejected"]:
                raise HTTPException(status_code=400, detail="Invalid status")
            v["status"] = status
            v["updated_at"] = datetime.utcnow().isoformat()
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Variation not found")
        
    storage.update_project(project_id, {"variations": project["variations"]})
    return {"status": "success", "variation_id": variation_id, "new_status": status}

# ============================================================================
# PDF GENERATION ENDPOINT
# ============================================================================

@app.post("/generate-pdf")
async def generate_pdf(request: dict):
    """Generate variation proposal PDF"""
    try:
        output_path = f"variation_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        PDFGenerator.generate_variation_proposal(request, output_path)
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=f"Variation_Proposal_{request.get('variation_id', 'draft')}.pdf"
        )
    except Exception as e:
        print(f"PDF GENERATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Serve generated PDF files for download"""
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF downloads allowed")
    
    file_path = filename # Assuming it's in the CWD as per current logic
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
