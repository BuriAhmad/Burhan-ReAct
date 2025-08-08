from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyAfBQ_-bI2qhiyhXo2UhWQBCtD--y7rJHs"
genai.configure(api_key=GEMINI_API_KEY)

# Initialize FastAPI app
app = FastAPI(title="RAG Server", description="Basic FastAPI server with Gemini API")

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# Request/Response models
class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    response: str
    status: str

@app.get("/")
async def root():
    return {"message": "RAG Server is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "RAG Server"}

@app.post("/chat", response_model=QueryResponse)
async def chat_with_gemini(request: QueryRequest):
    try:
        # Generate response using Gemini
        response = model.generate_content(request.message)
        
        return QueryResponse(
            response=response.text,
            status="success"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.post("/query")
async def query_gemini(request: QueryRequest):
    """Alternative endpoint for querying"""
    try:
        response = model.generate_content(request.message)
        return {
            "query": request.message,
            "response": response.text,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)