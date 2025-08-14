from pymongo import MongoClient
from typing import List, Tuple, Optional, Dict
import random
from datetime import datetime

class ChatHistory:
    def __init__(self, mongodb_uri: str, database_name: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.collection = self.db["simple_chats"]
    
    def create_session(self, session_name: str) -> Dict:
        """Create a new chat session with unique ID"""
        # Generate unique 3-digit number
        random_suffix = str(random.randint(100, 999))
        session_id = f"{session_name}_{random_suffix}"
        
        # Check if ID already exists (unlikely but safe)
        while self.collection.find_one({"_id": session_id}):
            random_suffix = str(random.randint(100, 999))
            session_id = f"{session_name}_{random_suffix}"
        
        # Create new session
        session_doc = {
            "_id": session_id,
            "display_name": session_name,
            "messages": [],
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "message_count": 0
        }
        
        try:
            self.collection.insert_one(session_doc)
            return {
                "success": True,
                "session_id": session_id,
                "display_name": session_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_sessions(self) -> List[Dict]:
        """List all available chat sessions"""
        try:
            sessions = []
            for session in self.collection.find({}, {"_id": 1, "display_name": 1, "last_updated": 1, "message_count": 1}):
                sessions.append({
                    "session_id": session["_id"],
                    "display_name": session.get("display_name", session["_id"]),
                    "last_updated": session.get("last_updated", ""),
                    "message_count": session.get("message_count", len(session.get("messages", [])))
                })
            # Sort by last_updated (most recent first)
            sessions.sort(key=lambda x: x["last_updated"], reverse=True)
            return sessions
        except Exception as e:
            print(f"Error listing sessions: {str(e)}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        try:
            result = self.collection.delete_one({"_id": session_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting session: {str(e)}")
            return False
    
    def get_or_create_session(self, session_id: str) -> str:
        """Get existing session or create if it doesn't exist"""
        session = self.collection.find_one({"_id": session_id})
        if not session:
            # Create new session with the given ID
            self.collection.insert_one({
                "_id": session_id,
                "display_name": session_id,
                "messages": [],
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "message_count": 0
            })
        return session_id
    
    def add_message(self, user_message: str, assistant_response: str, session_id: str) -> bool:
        """Add a message exchange to chat history"""
        try:
            # Ensure session exists
            self.get_or_create_session(session_id)
            
            # Add message pair to history and update metadata
            result = self.collection.update_one(
                {"_id": session_id},
                {
                    "$push": {"messages": [user_message, assistant_response]},
                    "$set": {"last_updated": datetime.utcnow().isoformat()},
                    "$inc": {"message_count": 1}
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error adding message: {str(e)}")
            return False
    
    def get_recent_history(self, session_id: str, limit: int = 5) -> List[Tuple[str, str]]:
        """Get recent chat history (last N exchanges)"""
        try:
            session = self.collection.find_one({"_id": session_id})
            if session and "messages" in session:
                messages = session["messages"]
                if len(messages) > limit:
                    return messages[-limit:]
                return messages
            return []
        except Exception as e:
            print(f"Error retrieving history: {str(e)}")
            return []
    
    def get_full_history(self, session_id: str) -> List[Tuple[str, str]]:
        """Get full chat history for a session"""
        try:
            session = self.collection.find_one({"_id": session_id})
            if session and "messages" in session:
                return session["messages"]
            return []
        except Exception as e:
            print(f"Error retrieving full history: {str(e)}")
            return []
    
    def clear_history(self, session_id: str) -> bool:
        """Clear chat history for a specific session"""
        try:
            result = self.collection.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "messages": [],
                        "last_updated": datetime.utcnow().isoformat(),
                        "message_count": 0
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error clearing history: {str(e)}")
            return False
    
    def format_history_for_context(self, session_id: str, limit: int = 5) -> str:
        """Format chat history as context string for RAG pipeline"""
        history = self.get_recent_history(session_id, limit)
        
        if not history:
            return ""
        
        formatted = "Previous conversation:\n"
        for user_msg, assistant_msg in history:
            formatted += f"User: {user_msg}\n"
            formatted += f"Assistant: {assistant_msg}\n"
        formatted += "\n"
        
        return formatted
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        return self.collection.find_one({"_id": session_id}) is not None
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session metadata"""
        try:
            session = self.collection.find_one(
                {"_id": session_id},
                {"display_name": 1, "created_at": 1, "last_updated": 1, "message_count": 1}
            )
            if session:
                return {
                    "session_id": session["_id"],
                    "display_name": session.get("display_name", session["_id"]),
                    "created_at": session.get("created_at", ""),
                    "last_updated": session.get("last_updated", ""),
                    "message_count": session.get("message_count", 0)
                }
            return None
        except Exception as e:
            print(f"Error getting session info: {str(e)}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()