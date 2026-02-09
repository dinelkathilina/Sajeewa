import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class StorageManager:
    def __init__(self, data_dir: str = "backend/data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        self.index_file = os.path.join(self.data_dir, "projects_index.json")
        self._init_index()

    def _init_index(self):
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump({"projects": []}, f, indent=4)

    def _get_project_file(self, project_id: int) -> str:
        return os.path.join(self.data_dir, f"project_{project_id}.json")

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _save_json(self, file_path: str, data: Dict[str, Any]):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4, default=str)

    def create_project(self, name: str, boq_filename: str = None, 
                       rate_breakdown_filename: str = None, 
                       schedule_filename: str = None) -> Dict[str, Any]:
        index = self._load_json(self.index_file)
        project_id = len(index["projects"]) + 1
        
        project_data = {
            "id": project_id,
            "name": name,
            "description": "",
            "boq_filename": boq_filename,
            "rate_breakdown_filename": rate_breakdown_filename,
            "schedule_filename": schedule_filename,
            "accepted_contract_amount": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "sheets": {}, # For multi-sheet Excel
            "boq_items": [],
            "rate_breakdowns": [],
            "activities": [],
            "variations": [],
            "sessions": [],
            "chat_history": []
        }
        
        # Save project file
        self._save_json(self._get_project_file(project_id), project_data)
        
        # Update index
        index["projects"].append({
            "id": project_id,
            "name": name,
            "created_at": project_data["created_at"]
        })
        self._save_json(self.index_file, index)
        
        return project_data

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        file_path = self._get_project_file(project_id)
        if os.path.exists(file_path):
            return self._load_json(file_path)
        return None

    def update_project(self, project_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        project = self.get_project(project_id)
        if project:
            project.update(updates)
            self._save_json(self._get_project_file(project_id), project)
            return project
        return None

    def add_boq_items(self, project_id: int, items: List[Dict[str, Any]], sheet_name: str = "General"):
        project = self.get_project(project_id)
        if project:
            # Add sheet if not exists
            if sheet_name not in project["sheets"]:
                project["sheets"][sheet_name] = []
            
            # Add items to both global list and sheet-specific list
            start_id = len(project["boq_items"]) + 1
            for i, item in enumerate(items):
                item_with_id = {"id": start_id + i, **item, "sheet": sheet_name}
                project["boq_items"].append(item_with_id)
                project["sheets"][sheet_name].append(item_with_id["id"])
            
            self._save_json(self._get_project_file(project_id), project)
            return len(items)
        return 0

    def add_rate_breakdowns(self, project_id: int, items: List[Dict[str, Any]]):
        project = self.get_project(project_id)
        if project:
            start_id = len(project["rate_breakdowns"]) + 1
            for i, item in enumerate(items):
                item_with_id = {"id": start_id + i, **item}
                project["rate_breakdowns"].append(item_with_id)
            self._save_json(self._get_project_file(project_id), project)
            return len(items)
        return 0

    def add_activities(self, project_id: int, items: List[Dict[str, Any]]):
        project = self.get_project(project_id)
        if project:
            start_id = len(project["activities"]) + 1
            for i, item in enumerate(items):
                item_with_id = {"id": start_id + i, **item}
                project["activities"].append(item_with_id)
            self._save_json(self._get_project_file(project_id), project)
            return len(items)
        return 0

    def create_session(self, project_id: int, session_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        project = self.get_project(project_id)
        if project:
            session_id = len(project["sessions"]) + 1
            import uuid
            session = {
                "id": session_id,
                "project_id": project_id,
                "session_key": str(uuid.uuid4()),
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "session_metadata": session_metadata or {},
                "chat_history": []
            }
            project["sessions"].append(session)
            self._save_json(self._get_project_file(project_id), project)
            return session
        return {}

    def update_session_metadata(self, project_id: int, session_id: int, metadata: Dict[str, Any]) -> bool:
        project = self.get_project(project_id)
        if not project: return False
        
        for session in project.get("sessions", []):
            if session["id"] == session_id:
                if "session_metadata" not in session:
                    session["session_metadata"] = {}
                session["session_metadata"].update(metadata)
                session["updated_at"] = datetime.utcnow().isoformat()
                self._save_json(self._get_project_file(project_id), project)
                return True
        return False

    def add_chat_message(self, project_id: int, session_id: int, role: str, content: str, metadata: Dict[str, Any] = None):
        project = self.get_project(project_id)
        if project:
            for session in project.get("sessions", []):
                if session["id"] == session_id:
                    msg_id = len(session.get("chat_history", [])) + 1
                    message = {
                        "id": msg_id,
                        "session_id": session_id,
                        "role": role,
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": metadata or {}
                    }
                    if "chat_history" not in session:
                        session["chat_history"] = []
                    session["chat_history"].append(message)
                    self._save_json(self._get_project_file(project_id), project)
                    return message
        return {}

    def create_variation(self, project_id: int, session_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        project = self.get_project(project_id)
        if project:
            var_id = len(project["variations"]) + 1
            variation = {
                "id": var_id,
                "project_id": project_id,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "status": "Draft",
                **data
            }
            project["variations"].append(variation)
            self._save_json(self._get_project_file(project_id), project)
            return variation
        return {}

    def get_variation(self, project_id: int, variation_id: int) -> Optional[Dict[str, Any]]:
        project = self.get_project(project_id)
        if project:
            for v in project["variations"]:
                if v["id"] == variation_id:
                    return v
        return None

    def get_projects(self) -> List[Dict[str, Any]]:
        index = self._load_json(self.index_file)
        return index.get("projects", [])

    def add_additional_file(self, project_id: int, file_data: Dict[str, Any]):
        project = self.get_project(project_id)
        if project:
            if "additional_files" not in project:
                project["additional_files"] = []
            file_id = len(project["additional_files"]) + 1
            file_record = {"id": file_id, **file_data, "project_id": project_id}
            project["additional_files"].append(file_record)
            self._save_json(self._get_project_file(project_id), project)
            return file_record
        return {}

# Singleton
storage_manager = StorageManager()
