from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import google.generativeai as genai
import os
from rag_pipeline import RAGPipeline
from pdf_processor import PDFProcessor
from vector_store import VectorStore

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyAfBQ_-bI2qhiyhXo2UhWQBCtD--y7rJHs"
genai.configure(api_key=GEMINI_API_KEY)

# Initialize FastAPI app
app = FastAPI(title="RAG Server", description="FastAPI server with RAG functionality using MongoDB and Gemini API")

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize RAG pipeline
rag_pipeline = RAGPipeline(model)

# Initialize PDF processor and vector store
pdf_processor = PDFProcessor()
vector_store = VectorStore()

# Request/Response models
class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    response: str
    status: str
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

@app.post("/chat", response_model=QueryResponse)
async def chat_with_rag(request: QueryRequest):
    """Main chat endpoint with RAG functionality"""
    try:
        result = rag_pipeline.run(request.message)
        
        return QueryResponse(
            response=result["response"],
            status=result["status"],
            retrieved_docs_count=result["retrieved_docs_count"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in RAG pipeline: {str(e)}")

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
        result = rag_pipeline.run(request.message)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)