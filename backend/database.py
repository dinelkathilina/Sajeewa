from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./construction_data.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    boq_filename = Column(String, nullable=True)
    rate_breakdown_filename = Column(String, nullable=True)
    schedule_filename = Column(String, nullable=True)
    accepted_contract_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    boq_items = relationship("BOQItem", back_populates="project", cascade="all, delete-orphan")
    rate_breakdowns = relationship("RateBreakdown", back_populates="project", cascade="all, delete-orphan")
    variations = relationship("Variation", back_populates="project", cascade="all, delete-orphan")
    chat_history = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan")
    additional_files = relationship("AdditionalFile", back_populates="project", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    session_key = Column(String, unique=True, index=True)
    status = Column(String, default="active")  # active, completed, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_metadata = Column(JSON, nullable=True)  # Store session context
    
    project = relationship("Project", back_populates="sessions")
    variations = relationship("Variation", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class VariationType(Base):
    __tablename__ = "variation_types"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # TYPE1, TYPE2, etc.
    name = Column(String)
    description = Column(Text)
    
    variations = relationship("Variation", back_populates="variation_type")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    role = Column(String)  # 'user' or 'ai'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(JSON, nullable=True)  # Store additional context
    
    project = relationship("Project", back_populates="chat_history")
    session = relationship("Session", back_populates="chat_messages")

class BOQItem(Base):
    __tablename__ = "boq_items"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    item_number = Column(String, index=True)
    description = Column(Text)
    unit = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    is_fixed_rate = Column(Integer, default=0)  # 0 for false, 1 for true
    
    project = relationship("Project", back_populates="boq_items")

class RateBreakdown(Base):
    __tablename__ = "rate_breakdowns"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    item_ref = Column(String, index=True)
    description = Column(Text)
    material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    plant_cost = Column(Float, default=0.0)
    total_rate = Column(Float, default=0.0)
    source_type = Column(String, nullable=True)  # 'original', 'bsr', 'hsr', 'quotation'
    source_reference = Column(String, nullable=True)  # e.g., 'BSR 2023', 'Quotation Q-001'
    
    project = relationship("Project", back_populates="rate_breakdowns")

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    activity_id = Column(String, index=True)  # Original ID from schedule
    name = Column(String)
    duration = Column(Float, default=0.0)  # in days
    predecessors = Column(String, nullable=True)  # Comma-separated IDs
    early_start = Column(Float, nullable=True)
    early_finish = Column(Float, nullable=True)
    late_start = Column(Float, nullable=True)
    late_finish = Column(Float, nullable=True)
    total_float = Column(Float, nullable=True)
    is_critical = Column(Integer, default=0)  # 0 for false, 1 for true
    
    project = relationship("Project", back_populates="activities")

class AdditionalFile(Base):
    __tablename__ = "additional_files"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    variation_id = Column(Integer, ForeignKey("variations.id"), nullable=True)
    filename = Column(String)
    file_type = Column(String)  # 'bsr', 'hsr', 'quotation', 'specification', 'drawing'
    file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0 for false, 1 for true
    
    project = relationship("Project", back_populates="additional_files")
    variation = relationship("Variation", back_populates="additional_files")

class Variation(Base):
    __tablename__ = "variations"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    variation_type_id = Column(Integer, ForeignKey("variation_types.id"), nullable=True)
    description = Column(Text)
    status = Column(String, default="Draft")  # Draft, Under Review, Approved, Rejected
    
    # Variation details
    affected_boq_items = Column(JSON, nullable=True)  # List of BOQ item IDs
    affected_activities = Column(JSON, nullable=True)  # List of activity IDs
    quantity_changes = Column(JSON, nullable=True)  # Dict of item_id: new_quantity
    specification_changes = Column(Text, nullable=True)
    method_changes = Column(Text, nullable=True)
    location_changes = Column(Text, nullable=True)
    
    # Evaluation results
    cost_impact = Column(Float, default=0.0)
    time_impact = Column(Float, default=0.0)  # EOT in days
    ml_predicted_cost = Column(Float, nullable=True)
    ml_predicted_time = Column(Float, nullable=True)
    
    # Validation
    validation_status = Column(String, nullable=True)  # 'passed', 'warnings', 'failed'
    validation_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="variations")
    session = relationship("Session", back_populates="variations")
    variation_type = relationship("VariationType", back_populates="variations")
    additional_files = relationship("AdditionalFile", back_populates="variation", cascade="all, delete-orphan")
    details = relationship("VariationDetail", back_populates="variation", cascade="all, delete-orphan")

class VariationDetail(Base):
    __tablename__ = "variation_details"
    id = Column(Integer, primary_key=True, index=True)
    variation_id = Column(Integer, ForeignKey("variations.id"))
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=True)
    original_description = Column(Text)
    new_description = Column(Text, nullable=True)
    original_quantity = Column(Float, default=0.0)
    new_quantity = Column(Float, default=0.0)
    original_rate = Column(Float, default=0.0)
    new_rate = Column(Float, default=0.0)
    rate_source = Column(String, nullable=True)  # 'original', 'similar', 'bsr', 'hsr', 'quotation', 'derived'
    cost_impact = Column(Float, default=0.0)
    justification = Column(Text, nullable=True)
    
    variation = relationship("Variation", back_populates="details")

def init_db():
    """Initialize database and create all tables"""
    Base.metadata.create_all(bind=engine)
    
    # Seed FIDIC variation types
    db = SessionLocal()
    try:
        if db.query(VariationType).count() == 0:
            variation_types = [
                VariationType(
                    code="TYPE1",
                    name="Quantity Changes",
                    description="Changes in the quantity of any item of work included in the Contract"
                ),
                VariationType(
                    code="TYPE2",
                    name="Quality/Characteristics Changes",
                    description="Changes in the quality or other characteristics of any item of work"
                ),
                VariationType(
                    code="TYPE3",
                    name="Levels/Positions/Dimensions Changes",
                    description="Changes in the levels, positions and/or dimensions of any part of the Works"
                ),
                VariationType(
                    code="TYPE4",
                    name="Omission of Work",
                    description="Omission of any work unless it is to be carried out by others"
                ),
                VariationType(
                    code="TYPE5",
                    name="Additional Work/Plant/Materials",
                    description="Any additional work, Plant, Materials or services necessary for the Works"
                ),
                VariationType(
                    code="TYPE6",
                    name="Sequence/Timing Changes",
                    description="Changes to the sequence or timing of the execution of the Works"
                )
            ]
            db.add_all(variation_types)
            db.commit()
            print("Seeded FIDIC variation types")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
