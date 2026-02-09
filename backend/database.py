from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
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
    accepted_contract_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    boq_items = relationship("BOQItem", back_populates="project")
    rate_breakdowns = relationship("RateBreakdown", back_populates="project")
    variations = relationship("Variation", back_populates="project")
    chat_history = relationship("ChatMessage", back_populates="project")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    role = Column(String) # 'user' or 'ai'
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="chat_history")

class BOQItem(Base):
    __tablename__ = "boq_items"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    item_number = Column(String, index=True)
    description = Column(String)
    unit = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    is_fixed_rate = Column(Integer, default=0) # 0 for false, 1 for true
    
    project = relationship("Project", back_populates="boq_items")

class RateBreakdown(Base):
    __tablename__ = "rate_breakdowns"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    item_ref = Column(String, index=True)
    description = Column(String)
    material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    plant_cost = Column(Float, default=0.0)
    total_rate = Column(Float, default=0.0)
    
    project = relationship("Project", back_populates="rate_breakdowns")

class Variation(Base):
    __tablename__ = "variations"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    description = Column(String)
    status = Column(String, default="Draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="variations")

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
