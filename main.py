from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import google.generativeai as genai
import os
from rag_pipeline import RAGPipeline
from pdf_processor import PDFProcessor
from vector_store import VectorStore
from chat_history import ChatHistory
from config import config
from typing import List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Validate configuration on startup
try:
    config.validate_required_keys()
    logger.info("✅ Configuration validation successful")
    config.print_config_summary()
except ValueError as e:
    logger.error(f"❌ Configuration Error: {e}")
    exit(1)

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)

# Initialize FastAPI app
app = FastAPI(title="RAG Server", description="FastAPI server with RAG functionality using MongoDB and Gemini API")

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize RAG pipeline
rag_pipeline = RAGPipeline(model, tavily_api_key=config.TAVILY_API_KEY)

# Initialize PDF processor and vector store
pdf_processor = PDFProcessor()
vector_store = VectorStore()

# Initialize Chat History Manager with error handling
try:
    chat_history = ChatHistory(config.MONGODB_URI, config.DATABASE_NAME)
    logger.info("✅ Chat history manager initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize chat history manager: {e}")
    raise

# Request/Response models
class QueryRequest(BaseModel):
    message: str
    session_id: str

class QueryResponse(BaseModel):
    response: str
    status: str
    retrieved_docs_count: int = 0

class ChatResponse(BaseModel):
    response: str
    status: str
    chat_history: List[List[str]]
    retrieved_docs_count: int = 0
    session_id: str

class CreateSessionRequest(BaseModel):
    session_name: str

class SessionInfo(BaseModel):
    session_id: str
    display_name: str
    last_updated: str
    message_count: int

class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]
    status: str

class ChatHistoryResponse(BaseModel):
    chat_history: List[List[str]]
    status: str
    session_id: str

class UploadResponse(BaseModel):
    status: str
    message: str
    filename: str
    chunks_created: int = 0
    processing_time: str = ""

@app.get("/")
async def root():
    """Health check and configuration status"""
    try:
        # Test MongoDB connection
        chat_history.session_exists("test")  # Simple connectivity test
        mongodb_status = "connected"
    except Exception as e:
        mongodb_status = f"error: {str(e)}"
    
    return {
        "message": "RAG Server is running!",
        "status": "healthy",
        "configuration": {
            "database": config.DATABASE_NAME,
            "collection": config.COLLECTION_NAME,
            "mongodb_status": mongodb_status,
            "gemini_configured": bool(config.GEMINI_API_KEY),
            "tavily_configured": bool(config.TAVILY_API_KEY)
        }
    }

@app.post("/create-session")
async def create_session(request: CreateSessionRequest):
    """Create a new chat session"""
    logger.info(f"Creating session with name: '{request.session_name}'")
    
    try:
        # Validate session name
        if not request.session_name or len(request.session_name.strip()) == 0:
            logger.warning("Empty session name provided")
            raise HTTPException(status_code=400, detail="Session name cannot be empty")
        
        # Remove special characters and limit length
        clean_name = "".join(c for c in request.session_name if c.isalnum() or c in ['_', '-', ' '])
        clean_name = clean_name.replace(' ', '_').lower()[:30]
        
        if not clean_name:
            logger.warning(f"Invalid session name after cleaning: '{request.session_name}'")
            raise HTTPException(status_code=400, detail="Invalid session name")
        
        logger.info(f"Cleaned session name: '{clean_name}'")
        
        result = chat_history.create_session(clean_name)
        
        if result["success"]:
            logger.info(f"✅ Successfully created session: {result['session_id']}")
            return {
                "status": "success",
                "session_id": result["session_id"],
                "display_name": result["display_name"]
            }
        else:
            logger.error(f"Failed to create session: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create session"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@app.get("/list-sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all available chat sessions"""
    logger.info("Listing all sessions")
    
    try:
        sessions = chat_history.list_sessions()
        logger.info(f"Retrieved {len(sessions)} sessions")
        
        return SessionListResponse(
            sessions=[SessionInfo(**s) for s in sessions],
            status="success"
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")

@app.delete("/delete-session/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific chat session"""
    logger.info(f"Deleting session: {session_id}")
    
    try:
        # Check if session exists first
        if not chat_history.session_exists(session_id):
            logger.warning(f"Session {session_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = chat_history.delete_session(session_id)
        if success:
            logger.info(f"✅ Successfully deleted session: {session_id}")
            return {"status": "success", "message": f"Session {session_id} deleted"}
        else:
            logger.error(f"Failed to delete session: {session_id}")
            return {"status": "error", "message": "Session could not be deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF file"""
    import time
    start_time = time.time()
    
    logger.info(f"Processing PDF upload: {file.filename}")
    
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            logger.warning("Empty file uploaded")
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        logger.info(f"Read {len(file_content)} bytes from PDF")
        
        # Process PDF
        processing_result = pdf_processor.process_pdf(file_content, file.filename)
        
        if not processing_result['success']:
            logger.error(f"PDF processing failed: {processing_result['error']}")
            raise HTTPException(status_code=400, detail=processing_result['error'])
        
        logger.info(f"PDF processed into {len(processing_result['chunks'])} chunks")
        
        # Store chunks in MongoDB
        storage_result = vector_store.store_pdf_chunks(processing_result['chunks'])
        
        if not storage_result['success']:
            logger.error(f"Database storage failed: {storage_result['error']}")
            raise HTTPException(status_code=500, detail=f"Database error: {storage_result['error']}")
        
        processing_time = f"{time.time() - start_time:.2f} seconds"
        logger.info(f"✅ PDF upload complete in {processing_time}")
        
        return UploadResponse(
            status="success",
            message="PDF uploaded and processed successfully",
            filename=file.filename,
            chunks_created=storage_result['inserted_count'],
            processing_time=processing_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_rag(request: QueryRequest):
    """Enhanced chat endpoint with query classification-style logging (compatible with ChatResponse)"""
    try:
        # Get chat history context (last N exchanges)
        history_context = chat_history.format_history_for_context(
            request.session_id,
            limit=config.CHAT_HISTORY_LIMIT
        )

        print("\n" + "="*60)
        print(f"📝 New Query from session '{request.session_id}':")
        print(f"   Query: '{request.message[:100]}...'")
        print(f"   History context length: {len(history_context)} chars")

        # Run RAG pipeline
        result = rag_pipeline.run(
            user_query=request.message,
            chat_history_context=history_context
        )

        print("\n🤖 Pipeline Analysis:")
        print(f"   Query Type: {result.get('query_type', 'unknown')}")
        print(f"   Temperature: {result.get('temperature', 0.2)}")
        print(f"   Answered from History: {result.get('answered_from_history', False)}")
        print(f"   Retrieved Docs: {result.get('retrieved_docs_count', 0)}")
        print(f"   Web Search Used: {result.get('web_search_used', False)}")
        print(f"   Status: {result['status']}")

        response_text = result["response"]

        # Save message to history
        save_ok = chat_history.add_message(
            user_message=request.message,
            assistant_response=response_text,
            session_id=request.session_id
        )
        if not save_ok:
            print("   ⚠️ Warning: Failed to save to chat history")

        # IMPORTANT: your UI expects the full history list here
        updated_history = chat_history.get_full_history(request.session_id)

        print("="*60 + "\n")

        # Return exactly what ChatResponse defines; extra metadata is fine to log, but not returned
        return ChatResponse(
            response=response_text,
            status=result["status"],
            chat_history=updated_history,
            retrieved_docs_count=result.get("retrieved_docs_count", 0),
            session_id=request.session_id
        )

    except Exception as e:
        print(f"❌ Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get full chat history for a specific session"""
    logger.info(f"Retrieving chat history for session: {session_id}")
    
    try:
        if not chat_history.session_exists(session_id):
            logger.warning(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        history = chat_history.get_full_history(session_id)
        logger.info(f"Retrieved {len(history)} message exchanges for session {session_id}")
        
        return ChatHistoryResponse(
            chat_history=history,
            status="success",
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chat history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")

@app.delete("/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a specific session"""
    logger.info(f"Clearing chat history for session: {session_id}")
    
    try:
        if not chat_history.session_exists(session_id):
            logger.warning(f"Session {session_id} not found for history clearing")
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = chat_history.clear_history(session_id)
        if success:
            logger.info(f"✅ Cleared history for session {session_id}")
            return {"status": "success", "message": f"Chat history cleared for session {session_id}"}
        else:
            logger.error(f"Failed to clear history for session {session_id}")
            return {"status": "error", "message": "Failed to clear chat history"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing chat history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {str(e)}")

@app.get("/session-info/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    logger.info(f"Getting info for session: {session_id}")
    
    try:
        info = chat_history.get_session_info(session_id)
        if info:
            logger.info(f"Retrieved info for session {session_id}")
            return info
        else:
            logger.warning(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting session info: {str(e)}")

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down server...")
    try:
        rag_pipeline.close()
        vector_store.close()
        chat_history.close()
        logger.info("✅ All resources closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.API_HOST}:{config.API_PORT}")
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)