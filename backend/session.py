import threading
from typing import Dict, List

class SessionStore:
    _instance = None
    _lock = threading.Lock()
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._sessions: Dict[str, Dict] = {}
        return cls._instance
    def create(self, session_id):
        self._sessions[session_id] = {"docs": []}
    def exists(self, session_id):
        return session_id in self._sessions
    def add_doc(self, session_id, doc_meta):
        if session_id in self._sessions:
            self._sessions[session_id]["docs"].append(doc_meta)
    def get_docs(self, session_id):
        return self._sessions.get(session_id, {}).get("docs", [])
