from pymongo import MongoClient
from typing import List, Tuple, Optional
import uuid
from datetime import datetime

class ChatHistory:
    def __init__(self, mongodb_uri: str, database_name: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.collection = self.db["simple_chats"]
        # Using fixed session ID for single-session implementation
        self.default_session_id = "default_session"
    
    def get_or_create_session(self, session_id: str = None) -> str:
        """Get existing session or create new one"""
        if not session_id:
            session_id = self.default_session_id
        
        # Check if session exists
        session = self.collection.find_one({"_id": session_id})
        if not session:
            # Create new session
            self.collection.insert_one({
                "_id": session_id,
                "messages": [],
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat()
            })
        
        return session_id
    
    def add_message(self, user_message: str, assistant_response: str, session_id: str = None) -> bool:
        """Add a message exchange to chat history"""
        if not session_id:
            session_id = self.default_session_id
        
        try:
            # Ensure session exists
            self.get_or_create_session(session_id)
            
            # Add message pair to history
            result = self.collection.update_one(
                {"_id": session_id},
                {
                    "$push": {"messages": [user_message, assistant_response]},
                    "$set": {"last_updated": datetime.utcnow().isoformat()}
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error adding message: {str(e)}")
            return False
    
    def get_recent_history(self, session_id: str = None, limit: int = 5) -> List[Tuple[str, str]]:
        """Get recent chat history (last N exchanges)"""
        if not session_id:
            session_id = self.default_session_id
        
        try:
            session = self.collection.find_one({"_id": session_id})
            if session and "messages" in session:
                # Get last 'limit' message pairs
                messages = session["messages"]
                if len(messages) > limit:
                    return messages[-limit:]
                return messages
            return []
        except Exception as e:
            print(f"Error retrieving history: {str(e)}")
            return []
    
    def get_full_history(self, session_id: str = None) -> List[Tuple[str, str]]:
        """Get full chat history for a session"""
        if not session_id:
            session_id = self.default_session_id
        
        try:
            session = self.collection.find_one({"_id": session_id})
            if session and "messages" in session:
                return session["messages"]
            return []
        except Exception as e:
            print(f"Error retrieving full history: {str(e)}")
            return []
    
    def clear_history(self, session_id: str = None) -> bool:
        """Clear chat history for a session"""
        if not session_id:
            session_id = self.default_session_id
        
        try:
            result = self.collection.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "messages": [],
                        "last_updated": datetime.utcnow().isoformat()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error clearing history: {str(e)}")
            return False
    
    def format_history_for_context(self, session_id: str = None, limit: int = 5) -> str:
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
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()