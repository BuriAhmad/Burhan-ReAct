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

# Validate configuration on startup
try:
    config.validate_required_keys()
    print("✅ Configuration validation successful")
    config.print_config_summary()
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
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

# Initialize Chat History Manager
chat_history = ChatHistory(config.MONGODB_URI, config.DATABASE_NAME)

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
    return {"message": "RAG Server is running!", "status": "healthy"}

@app.post("/create-session")
async def create_session(request: CreateSessionRequest):
    """Create a new chat session"""
    try:
        # Validate session name
        if not request.session_name or len(request.session_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Session name cannot be empty")
        
        # Remove special characters and limit length
        clean_name = "".join(c for c in request.session_name if c.isalnum() or c in ['_', '-', ' '])
        clean_name = clean_name.replace(' ', '_').lower()[:30]
        
        if not clean_name:
            raise HTTPException(status_code=400, detail="Invalid session name")
        
        result = chat_history.create_session(clean_name)
        
        if result["success"]:
            return {
                "status": "success",
                "session_id": result["session_id"],
                "display_name": result["display_name"]
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create session"))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@app.get("/list-sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all available chat sessions"""
    try:
        sessions = chat_history.list_sessions()
        return SessionListResponse(
            sessions=[SessionInfo(**s) for s in sessions],
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")

@app.delete("/delete-session/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific chat session"""
    try:
        success = chat_history.delete_session(session_id)
        if success:
            return {"status": "success", "message": f"Session {session_id} deleted"}
        else:
            return {"status": "error", "message": "Session not found or could not be deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF file"""
    import time
    start_time = time.time()
    
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Process PDF
        processing_result = pdf_processor.process_pdf(file_content, file.filename)
        
        if not processing_result['success']:
            raise HTTPException(status_code=400, detail=processing_result['error'])
        
        # Store chunks in MongoDB
        storage_result = vector_store.store_pdf_chunks(processing_result['chunks'])
        
        if not storage_result['success']:
            raise HTTPException(status_code=500, detail=f"Database error: {storage_result['error']}")
        
        processing_time = f"{time.time() - start_time:.2f} seconds"
        
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
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_rag(request: QueryRequest):
    """Main chat endpoint with RAG functionality and chat history"""
    try:
        # Validate session_id
        if not request.session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        # Get chat history context for this session
        history_context = chat_history.format_history_for_context(request.session_id, limit=config.CHAT_HISTORY_LIMIT)
        
        # Run RAG pipeline with history context
        result = rag_pipeline.run(request.message, chat_history_context=history_context)
        
        # Save the new exchange to history for this session
        chat_history.add_message(request.message, result["response"], request.session_id)
        
        # Get full history for UI for this session
        full_history = chat_history.get_full_history(request.session_id)
        
        return ChatResponse(
            response=result["response"],
            status=result["status"],
            chat_history=full_history,
            retrieved_docs_count=result["retrieved_docs_count"],
            session_id=request.session_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in RAG pipeline: {str(e)}")

@app.get("/chat-history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get full chat history for a specific session"""
    try:
        if not chat_history.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        history = chat_history.get_full_history(session_id)
        return ChatHistoryResponse(
            chat_history=history,
            status="success",
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")

@app.delete("/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a specific session"""
    try:
        if not chat_history.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = chat_history.clear_history(session_id)
        if success:
            return {"status": "success", "message": f"Chat history cleared for session {session_id}"}
        else:
            return {"status": "error", "message": "Failed to clear chat history"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {str(e)}")

@app.get("/session-info/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    try:
        info = chat_history.get_session_info(session_id)
        if info:
            return info
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting session info: {str(e)}")

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    rag_pipeline.close()
    vector_store.close()
    chat_history.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)