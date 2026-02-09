"""
Session Manager for Conversation and Context Tracking
Handles session lifecycle, conversation history, and memory persistence
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import uuid
from .storage_manager import StorageManager


class SessionManager:
    """Manages conversation sessions and context using StorageManager"""
    
    def __init__(self, storage: StorageManager):
        self.storage = storage
    
    def create_session(self, project_id: int, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new session for a project"""
        return self.storage.create_session(project_id, metadata)
    
    def get_session(self, project_id: int, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        project = self.storage.get_project(project_id)
        if not project: return None
        return next((s for s in project.get("sessions", []) if s["id"] == session_id), None)
    
    def get_session_by_key(self, project_id: int, session_key: str) -> Optional[Dict[str, Any]]:
        """Get session by unique key"""
        project = self.storage.get_project(project_id)
        if not project: return None
        return next((s for s in project.get("sessions", []) if s["session_key"] == session_key), None)
    
    def update_session_metadata(self, project_id: int, session_id: int, metadata: Dict) -> bool:
        """Update session metadata"""
        return self.storage.update_session_metadata(project_id, session_id, metadata)
    
    def add_message(self, project_id: int, session_id: int, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Add a message to the session"""
        return self.storage.add_chat_message(project_id, session_id, role, content, metadata)
    
    def get_conversation_history(self, project_id: int, session_id: int, limit: int = 50) -> List[Dict]:
        """Get conversation history for a session"""
        project = self.storage.get_project(project_id)
        if not project: return []
        session = next((s for s in project.get("sessions", []) if s["id"] == session_id), None)
        if not session: return []
        
        messages = session.get("chat_history", [])
        return messages[-limit:]
    
    def get_session_context(self, project_id: int, session_id: int) -> Optional[Dict]:
        """Get complete session context"""
        project = self.storage.get_project(project_id)
        if not project: return None
        session = next((s for s in project.get("sessions", []) if s["id"] == session_id), None)
        if not session: return None
        
        # Get variations for this session
        variations = [v for v in project.get("variations", []) if v.get("session_id") == session_id]
        
        return {
            "session_id": session["id"],
            "session_key": session.get("session_key"),
            "project_id": project_id,
            "status": session.get("status"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "metadata": session.get("session_metadata", {}),
            "conversation_history": session.get("chat_history", []),
            'variations_count': len(variations),
            'variations': variations
        }
    
    def close_session(self, project_id: int, session_id: int) -> bool:
        """Close/complete a session"""
        project = self.storage.get_project(project_id)
        if not project: return False
        for s in project.get("sessions", []):
            if s["id"] == session_id:
                s["status"] = "completed"
                s["updated_at"] = datetime.utcnow().isoformat()
                break
        self.storage.update_project(project_id, {"sessions": project["sessions"]})
        return True
    
    def archive_session(self, project_id: int, session_id: int) -> bool:
        """Archive a session"""
        project = self.storage.get_project(project_id)
        if not project: return False
        for s in project.get("sessions", []):
            if s["id"] == session_id:
                s["status"] = "archived"
                s["updated_at"] = datetime.utcnow().isoformat()
                break
        self.storage.update_project(project_id, {"sessions": project["sessions"]})
        return True
    
    def continue_session(self, project_id: int, session_id: int) -> Dict[str, Any]:
        """Continue an existing session"""
        session = self.get_session(project_id, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found in project {project_id}")
        
        # Reactivate if needed
        if session.get("status") != "active":
            project = self.storage.get_project(project_id)
            for s in project.get("sessions", []):
                if s["id"] == session_id:
                    s["status"] = "active"
                    s["updated_at"] = datetime.utcnow().isoformat()
                    break
            self.storage.update_project(project_id, {"sessions": project["sessions"]})
        
        return self.get_session_context(project_id, session_id)
    
    def store_variation_state(self, project_id: int, session_id: int, metadata: Dict) -> bool:
        """Store variation state in session metadata"""
        return self.update_session_metadata(project_id, session_id, {"variation_state": metadata})
    
    def get_variation_state(self, project_id: int, session_id: int) -> Optional[Dict]:
        """Get variation state from session metadata"""
        session = self.get_session(project_id, session_id)
        if not session or not session.get("session_metadata"):
            return None
        
        return session.get("session_metadata", {}).get("variation_state")
