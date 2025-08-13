from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import google.generativeai as genai
import os
from rag_pipeline import RAGPipeline
from pdf_processor import PDFProcessor
from vector_store import VectorStore
from chat_history import ChatHistory
from typing import List, Tuple

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyAfBQ_-bI2qhiyhXo2UhWQBCtD--y7rJHs"
TAVILY_API_KEY = "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"
genai.configure(api_key=GEMINI_API_KEY)

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://buri:buri_password@cluster0.gtzff0e.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "your_database_name"

# Initialize FastAPI app
app = FastAPI(title="RAG Server", description="FastAPI server with RAG functionality using MongoDB and Gemini API")

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize RAG pipeline
rag_pipeline = RAGPipeline(model, tavily_api_key=TAVILY_API_KEY)

# Initialize PDF processor and vector store
pdf_processor = PDFProcessor()
vector_store = VectorStore()

# Initialize Chat History Manager
chat_history = ChatHistory(MONGODB_URI, DATABASE_NAME)

# Request/Response models
class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    response: str
    status: str
    retrieved_docs_count: int = 0

class ChatResponse(BaseModel):
    response: str
    status: str
    chat_history: List[List[str]]
    retrieved_docs_count: int = 0

class SimpleQueryResponse(BaseModel):
    response: str
    status: str

class UploadResponse(BaseModel):
    status: str
    message: str
    filename: str
    chunks_created: int = 0
    processing_time: str = ""

class ChatHistoryResponse(BaseModel):
    chat_history: List[List[str]]
    status: str

@app.get("/")
async def root():
    return {"message": "RAG Server is running!", "status": "healthy"}

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
        # Get chat history context
        history_context = chat_history.format_history_for_context(limit=5)
        
        # Run RAG pipeline with history context
        result = rag_pipeline.run(request.message, chat_history_context=history_context)
        
        # Save the new exchange to history
        chat_history.add_message(request.message, result["response"])
        
        # Get full history for UI
        full_history = chat_history.get_full_history()
        
        return ChatResponse(
            response=result["response"],
            status=result["status"],
            chat_history=full_history,
            retrieved_docs_count=result["retrieved_docs_count"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in RAG pipeline: {str(e)}")

@app.get("/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history():
    """Get full chat history"""
    try:
        history = chat_history.get_full_history()
        return ChatHistoryResponse(
            chat_history=history,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")

@app.delete("/chat-history")
async def clear_chat_history():
    """Clear chat history"""
    try:
        success = chat_history.clear_history()
        if success:
            return {"status": "success", "message": "Chat history cleared"}
        else:
            return {"status": "error", "message": "Failed to clear chat history"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {str(e)}")

@app.post("/chat-simple", response_model=SimpleQueryResponse)
async def chat_simple(request: QueryRequest):
    """Simple chat endpoint without RAG (direct Gemini)"""
    try:
        # Generate response using Gemini directly
        response = model.generate_content(request.message)
        
        return SimpleQueryResponse(
            response=response.text,
            status="success"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.post("/query")
async def query_gemini(request: QueryRequest):
    """Alternative endpoint for querying with RAG"""
    try:
        # Get chat history context
        history_context = chat_history.format_history_for_context(limit=5)
        
        result = rag_pipeline.run(request.message, chat_history_context=history_context)
        return {
            "query": request.message,
            "response": result["response"],
            "status": result["status"],
            "retrieved_docs_count": result["retrieved_docs_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    rag_pipeline.close()
    vector_store.close()
    chat_history.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)