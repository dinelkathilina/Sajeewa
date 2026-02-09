from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
import uvicorn
import shutil
import pydantic
import os
from datetime import datetime
from .database import engine, init_db, SessionLocal
from sqlalchemy.orm import Session as DBSession
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Initialize DB
init_db()

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
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import engines and managers
from .engine import CostEngine, TimeEngine
from .database import Project, BOQItem, ChatMessage, VariationType, Variation
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
def get_variation_types(db: DBSession = Depends(get_db)):
    """Get all FIDIC variation types"""
    types = db.query(VariationType).all()
    return {
        "variation_types": [
            {
                "id": t.id,
                "code": t.code,
                "name": t.name,
                "description": t.description
            }
            for t in types
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
    db: DBSession = Depends(get_db)
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
        project = Project(
            name=proj_name,
            boq_filename=boq.filename if boq else None,
            rate_breakdown_filename=breakdown.filename if breakdown else None,
            schedule_filename=schedule.filename if schedule else None
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Initialize engines
        cost_engine = CostEngine(db)
        time_engine = TimeEngine(db_session=db)
        
        # Initialize session manager and create default session
        session_manager = SessionManager(db)
        session = session_manager.create_session(
            project_id=project.id,
            metadata={"created_via": "file_upload", "files_uploaded": []}
        )
        
        results = {
            "project_id": project.id,
            "session_id": session.id,
            "session_key": session.session_key,
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

            results["boq_items"] = cost_engine.load_boq(path, project.id)
            results["processing_notes"].append(f"✓ BOQ processed: {results['boq_items']} items")
            
            # Update session metadata
            session_manager.update_session_metadata(session.id, {
                "files_uploaded": ["boq"]
            })
        
        # Process Rate Breakdown (with OCR support for PDF)
        if breakdown:
            path = os.path.join(upload_dir, breakdown.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(breakdown.file, buffer)
            
            # Check if PDF
            if ocr_processor.is_pdf(path):
                results["processing_notes"].append("📄 PDF detected - Starting OCR processing...")
                
                # Process with OCR
                df = ocr_processor.process_pdf(
                    path,
                    progress_callback=lambda msg: print(f"OCR: {msg}")
                )
                
                if df is not None and not df.empty:
                    # Validate OCR results
                    validation = ocr_processor.validate_extracted_data(df)
                    
                    if validation['valid']:
                        # Convert DataFrame to rate breakdown format and save
                        results["rate_breakdowns"] = cost_engine.save_rate_breakdown_df(df, project.id)
                        results["processing_notes"].append(f"✓ OCR successful: {results['rate_breakdowns']} items extracted")
                        
                        if validation['warnings']:
                            results["processing_notes"].extend([f"⚠ {w}" for w in validation['warnings']])
                    else:
                        results["processing_notes"].append(f"✗ OCR validation failed: {validation['errors']}")
                else:
                    results["processing_notes"].append("⚠ OCR returned no data - trying standard parser")
                    results["rate_breakdowns"] = cost_engine.load_rate_breakdown(path, project.id)
            else:
                # Standard Excel/CSV processing
                results["rate_breakdowns"] = cost_engine.load_rate_breakdown(path, project.id)
                results["processing_notes"].append(f"✓ Rate breakdown processed: {results['rate_breakdowns']} items")
            
            session_manager.update_session_metadata(session.id, {
                "files_uploaded": ["boq", "breakdown"]
            })
        
        # Process Schedule
        if schedule:
            path = os.path.join(upload_dir, schedule.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(schedule.file, buffer)
            
            results["schedule_tasks"] = time_engine.parse_schedule(path, project_id=project.id)
            results["processing_notes"].append(f"✓ Schedule processed: {results['schedule_tasks']} activities")
            
            # Calculate CPM
            if results["schedule_tasks"] > 0:
                cpm_data = time_engine.calculate_cpm_full()
                critical_activities = time_engine.identify_critical_path()
                results["critical_path_activities"] = len(critical_activities)
                results["processing_notes"].append(f"✓ CPM calculated: {len(critical_activities)} critical activities")
            
            session_manager.update_session_metadata(session.id, {
                "files_uploaded": ["boq", "breakdown", "schedule"]
            })
        
        return {"status": "success", "data": results}
        
    except Exception as e:
        print(f"UPLOAD ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/quotation")
async def upload_quotation(
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db)
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
    db: DBSession = Depends(get_db)
):
    """Upload additional supporting files (BSR, HSR, Quotations, etc.)"""
    try:
        from .database import AdditionalFile
        
        upload_dir = "uploaded_files/additional"
        os.makedirs(upload_dir, exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            # Save file
            file_path = os.path.join(upload_dir, f"{project_id}_{file.filename}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Create database record
            additional_file = AdditionalFile(
                project_id=project_id,
                variation_id=variation_id,
                filename=file.filename,
                file_type=file_type,
                file_path=file_path
            )
            db.add(additional_file)
            uploaded_files.append({
                "filename": file.filename,
                "type": file_type,
                "size": os.path.getsize(file_path)
            })
        
        db.commit()
        
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
    db: DBSession = Depends(get_db)
):
    """Create a new conversation session"""
    session_manager = SessionManager(db)
    session = session_manager.create_session(project_id, metadata)
    
    return {
        "session_id": session.id,
        "session_key": session.session_key,
        "project_id": session.project_id,
        "status": session.status
    }

@app.get("/session/{session_id}")
def get_session(session_id: int, db: DBSession = Depends(get_db)):
    """Get session context"""
    session_manager = SessionManager(db)
    context = session_manager.get_session_context(session_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return context

@app.post("/session/{session_id}/continue")
def continue_session(session_id: int, db: DBSession = Depends(get_db)):
    """Continue an existing session"""
    session_manager = SessionManager(db)
    try:
        context = session_manager.continue_session(session_id)
        return {"status": "success", "context": context}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/session/{session_id}/close")
def close_session(session_id: int, db: DBSession = Depends(get_db)):
    """Close/complete a session"""
    session_manager = SessionManager(db)
    success = session_manager.close_session(session_id)
    
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
async def chat(request: ChatRequest, db: DBSession = Depends(get_db)):
    """
    Enhanced chat endpoint with FIDIC workflow support
    Handles variation type selection, details collection, and evaluation
    """
    try:
        # Initialize managers and engines
        session_manager = SessionManager(db)
        cost_engine = CostEngine(db)
        time_engine = TimeEngine(db_session=db)
        
        # Get or create session
        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Create new session
            session = session_manager.create_session(request.project_id)
        
        print(f"DEBUG: Chat request for project {request.project_id}, session {session.id}: {request.message}")
        
        # Save user message
        session_manager.add_message(session.id, "user", request.message)
        
        # Get conversation history
        history = session_manager.get_conversation_history(session.id, limit=10)
        
        # Train model and get context
        cost_engine.train_model(request.project_id)
        
        project = db.query(Project).filter(Project.id == request.project_id).first()
        proj_name = project.name if project else "Unknown Project"
        
        # Get relevant BOQ items
        relevant_matches = cost_engine.ml_model.find_similar_item(request.message, top_n=15)
        if not isinstance(relevant_matches, list):
            relevant_matches = [relevant_matches] if relevant_matches else []
        
        context_str = f"PROJECT NAME: {proj_name}\\n"
        context_str += "\\n".join([f"- {i['description']} (Rate: {i['rate']}, Qty: {i['quantity']})" for i in relevant_matches if i])
        
        # Get session metadata for workflow state
        session_metadata = session.session_metadata or {}
        
        # Parse instruction with workflow support
        ai_result = cost_engine.ml_model.parse_instruction(
            request.message,
            project_context=context_str,
            chat_history=history,
            session_metadata=session_metadata
        )
        
        if not ai_result:
            return {"reply": "Connection error with AI service.", "proposal": None, "session_id": session.id}
        
        response_text = ai_result.get('reply', "How can I help you today?")
        workflow_state = ai_result.get('workflow_state')
        proposal_data = None
        
        # Handle workflow states
        if workflow_state == "type_selection":
            # User is selecting variation type
            suggested_type = ai_result.get('suggested_type')
            if suggested_type:
                session_manager.update_session_metadata(session.id, {
                    "variation_type": suggested_type
                })
        
        elif workflow_state == "collecting_details":
            # Collecting variation details
            extracted_data = ai_result.get('extracted_data', {})
            current_details = session_metadata.get('collected_details', {})
            current_details.update(extracted_data)
            
            session_manager.update_session_metadata(session.id, {
                "collected_details": current_details
            })
        
        elif workflow_state == "requesting_files":
            # Mark that files have been requested
            proceed = ai_result.get('proceed_to_evaluation', False)
            current_details = session_metadata.get('collected_details', {})
            current_details['additional_files_asked'] = True
            
            session_manager.update_session_metadata(session.id, {
                "collected_details": current_details,
                "proceed_to_evaluation": proceed
            })
        
        elif workflow_state == "evaluation":
            # Execute evaluation command
            cmd = ai_result.get('command')
            
            if cmd and cmd.get('intent'):
                intent = cmd['intent']
                desc_query = cmd.get('description')
                
                if intent in ['change_spec', 'change_qty']:
                    qty_change = cmd.get('quantity', 0) if intent == 'change_qty' else 0
                    new_mat = cmd.get('new_material') if intent == 'change_spec' else None
                    
                    variation_result = cost_engine.evaluate_variation(
                        desc_query,
                        new_material=new_mat,
                        qty_change=qty_change
                    )
                    
                    if variation_result:
                        # Save to Database as Draft Variation
                        new_variation = Variation(
                            project_id=request.project_id,
                            session_id=session.id,
                            description=f"Variation: {desc_query}",
                            status="Draft",
                            cost_impact=variation_result.get('cost_impact', 0),
                            time_impact=0
                        )
                        db.add(new_variation)
                        db.commit()
                        db.refresh(new_variation)
                        
                        # Save Detail
                        new_detail = VariationDetail(
                            variation_id=new_variation.id,
                            boq_item_id=variation_result.get('item_id'),
                            original_description=variation_result.get('original_item'),
                            new_description=variation_result.get('new_item'),
                            original_quantity=variation_result.get('original_qty', 0),
                            new_quantity=variation_result.get('new_qty', 0) if intent == 'change_spec' else (variation_result.get('original_qty', 0) + qty_change),
                            original_rate=variation_result.get('original_rate', 0),
                            new_rate=variation_result.get('new_rate', 0),
                            rate_source=variation_result.get('rate_source'),
                            cost_impact=variation_result.get('cost_impact', 0)
                        )
                        db.add(new_detail)
                        db.commit()
                        
                        proposal_data = variation_result
                        proposal_data['variation_id'] = new_variation.id
                    else:
                        response_text += f"\\n(Note: I couldn't find an exact match for '{desc_query}' in the database to calculate costs.)"
                
                elif intent == 'delay':
                    # Time Impact Analysis
                    task_name_query = cmd.get('description')
                    delay_days = cmd.get('quantity', 0)
                    
                    # Parse schedule if not already done
                    if not time_engine.graph.nodes:
                        schedule_path = None
                        if os.path.exists("uploaded_files"):
                            for f in os.listdir("uploaded_files"):
                                if f.endswith((".xml", ".csv", ".xlsx")) and ("plan" in f.lower() or "schedule" in f.lower()):
                                    schedule_path = os.path.join("uploaded_files", f)
                                    break
                        
                        if schedule_path:
                            time_engine.parse_schedule(schedule_path, project_id=request.project_id)
                    
                    if time_engine.graph.nodes:
                        eot, breakdown = time_engine.calculate_eot(task_name_query, delay_days)
                        
                        if eot is not None:
                            proposal_data = {
                                "item_id": "TIME",
                                "original_item": "Original Schedule",
                                "new_item": f"Revised Schedule (+{eot} days)",
                                "original_rate": 0,
                                "new_rate": 0,
                                "cost_impact": 0,
                                "time_impact": eot,
                                "eot_breakdown": breakdown,
                                "gantt_chart_data": time_engine.generate_gantt_data()
                            }
                        else:
                            response_text += f"\\n(Note: I couldn't find task '{task_name_query}' in the project schedule.)"
                    else:
                        response_text += "\\n(Note: No project schedule found to evaluate time impact.)"
        
        # Save AI response
        session_manager.add_message(session.id, "ai", response_text, metadata={
            "workflow_state": workflow_state,
            "has_proposal": proposal_data is not None
        })
        
        return {
            "reply": response_text,
            "proposal": proposal_data,
            "session_id": session.id,
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

@app.get("/variation/{variation_id}")
def get_variation(variation_id: int, db: DBSession = Depends(get_db)):
    """Get variation details"""
    from sqlalchemy.orm import joinedload
    variation = db.query(Variation).options(joinedload(Variation.details)).filter(Variation.id == variation_id).first()
    if not variation:
        raise HTTPException(status_code=404, detail="Variation not found")
    return variation

@app.post("/variation/validate/{variation_id}")
def validate_variation(variation_id: int, db: DBSession = Depends(get_db)):
    """Run QS validation checks on a variation"""
    validator = ValidationEngine(db)
    results = validator.validate_variation(variation_id)
    return results

@app.get("/variation/validation-report/{variation_id}")
def get_validation_report(variation_id: int, db: DBSession = Depends(get_db)):
    """Get formatted validation report"""
    validator = ValidationEngine(db)
    report = validator.generate_validation_report(variation_id)
    return {"report": report}

@app.put("/variation/{variation_id}/details/{detail_id}")
def update_variation_detail_endpoint(
    variation_id: int, 
    detail_id: int, 
    updates: dict,
    db: DBSession = Depends(get_db)
):
    """
    Update a specific variation detail line item.
    Updates: {new_rate, new_quantity, justification, new_description}
    """
    cost_engine = CostEngine(db)
    updated_detail = cost_engine.update_variation_detail(detail_id, updates)
    
    if not updated_detail:
        raise HTTPException(status_code=404, detail="Variation detail not found")
        
    return {"status": "success", "detail_id": detail_id, "message": "Detail updated"}

@app.post("/variation/{variation_id}/status")
def update_variation_status(
    variation_id: int,
    status: str = Body(..., embed=True), # keys: status
    db: DBSession = Depends(get_db)
):
    """Update variation status (Approved, Rejected, Under Review)"""
    variation = db.query(Variation).filter(Variation.id == variation_id).first()
    if not variation:
        raise HTTPException(status_code=404, detail="Variation not found")
        
    if status not in ["Draft", "Under Review", "Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    variation.status = status
    variation.updated_at = datetime.utcnow()
    db.commit()
    
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

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
