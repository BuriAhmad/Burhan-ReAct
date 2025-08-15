from pymongo import MongoClient
from typing import List, Tuple, Optional, Dict
import random
from datetime import datetime
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHistory:
    def __init__(self, mongodb_uri: str = None, database_name: str = None):
        # Allow override of config values for testing purposes
        from config import config
        self.mongodb_uri = mongodb_uri or config.MONGODB_URI
        self.database_name = database_name or config.DATABASE_NAME
        
        logger.info(f"Initializing ChatHistory with DB: {self.database_name}")
        
        try:
            self.client = MongoClient(self.mongodb_uri)
            self.db = self.client[self.database_name]
            self.collection = self.db["simple_chats"]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def create_session(self, session_name: str) -> Dict:
        """Create a new chat session with unique ID"""
        logger.info(f"Creating new session with name: '{session_name}'")
        
        # Generate unique 3-digit number
        random_suffix = str(random.randint(100, 999))
        session_id = f"{session_name}_{random_suffix}"
        
        # Check if ID already exists (unlikely but safe)
        attempts = 0
        while self.collection.find_one({"_id": session_id}) and attempts < 10:
            random_suffix = str(random.randint(100, 999))
            session_id = f"{session_name}_{random_suffix}"
            attempts += 1
        
        if attempts >= 10:
            logger.error("Failed to generate unique session ID after 10 attempts")
            return {"success": False, "error": "Could not generate unique session ID"}
        
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
            logger.info(f"✅ Created session: {session_id} with display name: {session_name}")
            return {
                "success": True,
                "session_id": session_id,
                "display_name": session_name
            }
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_sessions(self) -> List[Dict]:
        """List all available chat sessions"""
        logger.info("Retrieving list of all sessions")
        
        try:
            sessions = []
            cursor = self.collection.find({}, {
                "_id": 1, 
                "display_name": 1, 
                "last_updated": 1, 
                "message_count": 1,
                "messages": 1  # Include to count if message_count is missing
            })
            
            raw_sessions = list(cursor)
            logger.info(f"Found {len(raw_sessions)} sessions in database")
            
            for session in raw_sessions:
                session_id = session["_id"]
                display_name = session.get("display_name", session_id)
                last_updated = session.get("last_updated", "")
                
                # Handle message count - calculate if not stored
                message_count = session.get("message_count")
                if message_count is None:
                    messages = session.get("messages", [])
                    message_count = len(messages)
                    logger.info(f"Session {session_id}: Calculated message count = {message_count}")
                
                session_info = {
                    "session_id": session_id,
                    "display_name": display_name,
                    "last_updated": last_updated,
                    "message_count": message_count
                }
                
                sessions.append(session_info)
                logger.debug(f"Session: {session_info}")
            
            # Sort by last_updated (most recent first)
            sessions.sort(key=lambda x: x["last_updated"], reverse=True)
            logger.info(f"✅ Successfully retrieved {len(sessions)} sessions")
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error listing sessions: {str(e)}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        logger.info(f"Deleting session: {session_id}")
        
        try:
            # First check if session exists
            existing = self.collection.find_one({"_id": session_id})
            if not existing:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
                
            result = self.collection.delete_one({"_id": session_id})
            success = result.deleted_count > 0
            
            if success:
                logger.info(f"✅ Successfully deleted session: {session_id}")
            else:
                logger.warning(f"❌ Failed to delete session: {session_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error deleting session {session_id}: {str(e)}")
            return False
    
    def get_or_create_session(self, session_id: str) -> str:
        """Get existing session or create if it doesn't exist"""
        logger.info(f"Getting or creating session: {session_id}")
        
        try:
            session = self.collection.find_one({"_id": session_id})
            if not session:
                logger.info(f"Session {session_id} not found, creating new one")
                # Create new session with the given ID
                self.collection.insert_one({
                    "_id": session_id,
                    "display_name": session_id,
                    "messages": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat(),
                    "message_count": 0
                })
                logger.info(f"✅ Created new session: {session_id}")
            else:
                logger.info(f"✅ Found existing session: {session_id}")
                
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Error in get_or_create_session for {session_id}: {e}")
            return session_id
    
    def add_message(self, user_message: str, assistant_response: str, session_id: str) -> bool:
        """Add a message exchange to chat history"""
        logger.info(f"Adding message to session {session_id}: '{user_message[:50]}...'")
        
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
            
            success = result.modified_count > 0
            if success:
                logger.info(f"✅ Added message to session {session_id}")
            else:
                logger.warning(f"❌ Failed to add message to session {session_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error adding message to {session_id}: {str(e)}")
            return False
    
    def get_recent_history(self, session_id: str, limit: int = None) -> List[Tuple[str, str]]:
        """Get recent chat history (last N exchanges)"""
        from config import config
        if limit is None:
            limit = config.CHAT_HISTORY_LIMIT
            
        logger.info(f"Getting recent history for session {session_id} (limit: {limit})")
        
        try:
            session = self.collection.find_one({"_id": session_id})
            if session and "messages" in session:
                messages = session["messages"]
                logger.info(f"Session {session_id} has {len(messages)} total message pairs")
                
                if len(messages) > limit:
                    recent_messages = messages[-limit:]
                    logger.info(f"Returning last {limit} message pairs")
                    return recent_messages
                else:
                    logger.info(f"Returning all {len(messages)} message pairs")
                    return messages
            else:
                logger.info(f"No messages found for session {session_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error retrieving recent history for {session_id}: {str(e)}")
            return []
    
    def get_full_history(self, session_id: str) -> List[Tuple[str, str]]:
        """Get full chat history for a session"""
        logger.info(f"Getting full history for session: {session_id}")
        
        try:
            session = self.collection.find_one({"_id": session_id})
            if session and "messages" in session:
                messages = session["messages"]
                logger.info(f"✅ Retrieved {len(messages)} message pairs for session {session_id}")
                return messages
            else:
                logger.info(f"No messages found for session {session_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error retrieving full history for {session_id}: {str(e)}")
            return []
    
    def clear_history(self, session_id: str) -> bool:
        """Clear chat history for a specific session"""
        logger.info(f"Clearing history for session: {session_id}")
        
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
            
            success = result.modified_count > 0
            if success:
                logger.info(f"✅ Cleared history for session {session_id}")
            else:
                logger.warning(f"❌ Failed to clear history for session {session_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error clearing history for {session_id}: {str(e)}")
            return False
    
    # Add this improved method to your ChatHistory class in chat_history.py

    def format_history_for_context(self, session_id: str, limit: int = None) -> str:
        """Format chat history as context string for RAG pipeline - Enhanced version"""
        history = self.get_recent_history(session_id, limit)
        
        if not history:
            logger.info(f"No history to format for session {session_id}")
            return ""
        
        # More structured format for better LLM understanding
        formatted_parts = []
        
        for i, (user_msg, assistant_msg) in enumerate(history, 1):
            # Add exchange number for clarity
            exchange = f"Exchange {i}:\n"
            exchange += f"User: {user_msg}\n"
            exchange += f"Assistant: {assistant_msg}"
            formatted_parts.append(exchange)
        
        # Join with clear separators
        formatted = "\n---\n".join(formatted_parts)
        
        # Add header for context
        final_formatted = f"=== Previous Conversation ({len(history)} exchanges) ===\n{formatted}\n=== End of Previous Conversation ==="
        
        logger.info(f"Formatted {len(history)} exchanges for context")
        return final_formatted
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        try:
            exists = self.collection.find_one({"_id": session_id}) is not None
            logger.info(f"Session {session_id} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"❌ Error checking if session {session_id} exists: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session metadata"""
        logger.info(f"Getting info for session: {session_id}")
        
        try:
            session = self.collection.find_one(
                {"_id": session_id},
                {"display_name": 1, "created_at": 1, "last_updated": 1, "message_count": 1, "messages": 1}
            )
            
            if session:
                # Calculate message count if not stored
                message_count = session.get("message_count")
                if message_count is None:
                    message_count = len(session.get("messages", []))
                
                info = {
                    "session_id": session["_id"],
                    "display_name": session.get("display_name", session["_id"]),
                    "created_at": session.get("created_at", ""),
                    "last_updated": session.get("last_updated", ""),
                    "message_count": message_count
                }
                logger.info(f"✅ Retrieved info for session {session_id}: {info}")
                return info
            else:
                logger.warning(f"Session {session_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting session info for {session_id}: {str(e)}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("✅ MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing MongoDB connection: {e}")