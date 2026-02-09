"""
Session Manager for Conversation and Context Tracking
Handles session lifecycle, conversation history, and memory persistence
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import uuid
from sqlalchemy.orm import Session as DBSession
from .database import Session, ChatMessage, Variation, Project


class SessionManager:
    """Manages conversation sessions and context"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    def create_session(self, project_id: int, metadata: Optional[Dict] = None) -> Session:
        """
        Create a new session for a project
        
        Args:
            project_id: ID of the project
            metadata: Optional metadata dictionary
            
        Returns:
            Created Session object
        """
        session_key = str(uuid.uuid4())
        
        session = Session(
            project_id=project_id,
            session_key=session_key,
            status="active",
            session_metadata=metadata or {}
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_session(self, session_id: int) -> Optional[Session]:
        """Get session by ID"""
        return self.db.query(Session).filter(Session.id == session_id).first()
    
    def get_session_by_key(self, session_key: str) -> Optional[Session]:
        """Get session by unique key"""
        return self.db.query(Session).filter(Session.session_key == session_key).first()
    
    def get_active_session(self, project_id: int) -> Optional[Session]:
        """Get the most recent active session for a project"""
        return self.db.query(Session).filter(
            Session.project_id == project_id,
            Session.status == "active"
        ).order_by(Session.updated_at.desc()).first()
    
    def update_session_metadata(self, session_id: int, metadata: Dict) -> bool:
        """
        Update session metadata (merges with existing)
        
        Args:
            session_id: ID of the session
            metadata: Dictionary to merge with existing metadata
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Merge metadata
        current_metadata = session.session_metadata or {}
        current_metadata.update(metadata)
        session.session_metadata = current_metadata
        session.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def add_message(self, session_id: int, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> ChatMessage:
        """
        Add a message to the session
        
        Args:
            session_id: ID of the session
            role: 'user' or 'ai'
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            Created ChatMessage object
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message = ChatMessage(
            project_id=session.project_id,
            session_id=session_id,
            role=role,
            content=content,
            message_metadata=metadata or {}
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # Update session timestamp
        session.updated_at = datetime.utcnow()
        self.db.commit()
        
        return message
    
    def get_conversation_history(self, session_id: int, limit: int = 50) -> List[Dict]:
        """
        Get conversation history for a session
        
        Args:
            session_id: ID of the session
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        return [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'metadata': msg.message_metadata
            }
            for msg in messages
        ]
    
    def get_session_context(self, session_id: int) -> Optional[Dict]:
        """
        Get complete session context including history and metadata
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dictionary with session context or None
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Get conversation history
        history = self.get_conversation_history(session_id)
        
        # Get variations in this session
        variations = self.db.query(Variation).filter(
            Variation.session_id == session_id
        ).all()
        
        return {
            "session_id": session.id,
            "session_key": session.session_key,
            "project_id": session.project_id,
            "status": session.status,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "metadata": session.session_metadata or {},
            "conversation_history": history,
            'variations_count': len(variations),
            'variations': [
                {
                    'id': v.id,
                    'description': v.description,
                    'status': v.status,
                    'cost_impact': v.cost_impact,
                    'time_impact': v.time_impact
                }
                for v in variations
            ]
        }
    
    def close_session(self, session_id: int) -> bool:
        """
        Close/complete a session
        
        Args:
            session_id: ID of the session
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = "completed"
        session.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def archive_session(self, session_id: int) -> bool:
        """
        Archive a session
        
        Args:
            session_id: ID of the session
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = "archived"
        session.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def continue_session(self, session_id: int) -> Dict[str, Any]:
        """
        Continue an existing session
        
        Args:
            session_id: ID of the session to continue
            
        Returns:
            Session context dictionary
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Reactivate if needed
        if session.status != "active":
            session.status = "active"
            session.updated_at = datetime.utcnow()
            self.db.commit()
        
        return self.get_session_context(session_id)
    
    def store_variation_state(self, session_id: int, metadata: Dict) -> bool:
        """
        Store variation state in session metadata
        
        Args:
            session_id: ID of the session
            metadata: Variation state dictionary
            
        Returns:
            True if successful
        """
        session = Session(
            project_id=0,  # Placeholder, will be updated
            session_key="temp",
            session_metadata=metadata or {}
        )
        return self.update_session_metadata(session_id, {"variation_state": metadata})
    
    def get_variation_state(self, session_id: int) -> Optional[Dict]:
        """
        Get variation state from session metadata
        
        Args:
            session_id: ID of the session
            
        Returns:
            Variation state dictionary or None
        """
        session = self.get_session(session_id)
        if not session or not session.session_metadata:
            return None
        
        return session.session_metadata.get("variation_state")
