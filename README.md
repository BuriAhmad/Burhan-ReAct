# RAG Chat Application with Persistent Chat History

A FastAPI-based RAG (Retrieval-Augmented Generation) application using MongoDB for document storage, chat history persistence, and Google Gemini for AI responses.

## Features

- **Persistent Chat History**: Conversations are saved and restored across sessions
- **Context-Aware Responses**: Bot remembers last 5 exchanges for continuity
- **Two-Way Chat Interface**: Interactive chat UI with message history display
- **RAG Chat**: AI responses augmented with relevant documents from MongoDB
- **PDF Upload**: Upload and process PDF documents for knowledge base
- **Web Search Integration**: Automatic web search when local documents insufficient
- **MongoDB Integration**: Connect to MongoDB Atlas for document and chat storage

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. MongoDB Configuration

The chat history is stored in MongoDB with the following structure:
- Database: `your_database_name`
- Collection: `simple_chats`
- Schema:
```json
{
  "_id": "default_session",
  "messages": [
    ["user message 1", "assistant response 1"],
    ["user message 2", "assistant response 2"]
  ],
  "created_at": "2024-01-01T00:00:00",
  "last_updated": "2024-01-01T00:00:00"
}
```

### 3. Start the Application

Run both servers using the provided script:
```bash
python run_servers.py
```

Or start them individually:
```bash
# Terminal 1 - Start FastAPI server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 - Start Gradio UI
python gradio_ui.py
```

## Usage

### Chat Interface
1. Open http://127.0.0.1:7860 in your browser
2. Type messages in the input box and press Enter or click Send
3. Chat history is automatically saved and will persist across sessions
4. The bot maintains context of the last 5 exchanges

### Document Upload
1. Use the right panel to upload PDF documents
2. Documents are processed and stored in MongoDB vector store
3. Future queries will retrieve relevant information from uploaded documents

### Clear History
- Click the "🗑️ Clear History" button to delete all chat history
- This removes history from both the UI and database

### Refresh
- Click the "🔄 Refresh" button to reload chat history from the database
- Useful if you have multiple sessions or need to sync

## API Endpoints

- `GET /` - Health check
- `POST /chat` - Main chat endpoint with RAG and history
- `GET /chat-history` - Retrieve full chat history
- `DELETE /chat-history` - Clear chat history
- `POST /upload-pdf` - Upload and process PDF documents
- `POST /chat-simple` - Direct Gemini chat without RAG

## Architecture

### Components
1. **FastAPI Backend** (`main.py`)
   - Handles HTTP requests
   - Manages chat sessions
   - Coordinates RAG pipeline

2. **Chat History Manager** (`chat_history.py`)
   - MongoDB operations for chat storage
   - Session management
   - History formatting for context

3. **RAG Pipeline** (`rag_pipeline.py`)
   - Document retrieval from vector store
   - LLM-based sufficiency evaluation
   - Web search integration
   - Context-aware response generation

4. **Gradio UI** (`gradio_ui.py`)
   - Two-way chat interface
   - Real-time message display
   - PDF upload interface
   - History management controls

5. **Vector Store** (`vector_store.py`)
   - MongoDB vector search
   - Document embedding generation
   - Similarity search

6. **PDF Processor** (`pdf_processor.py`)
   - PDF text extraction
   - Document chunking
   - Metadata management

## Configuration

### Environment Variables
Update these in the respective files:
- `GEMINI_API_KEY`: Google Gemini API key
- `TAVILY_API_KEY`: Tavily search API key
- `MONGODB_URI`: MongoDB connection string
- `DATABASE_NAME`: MongoDB database name

### Session Management
- Currently uses a fixed session ID: `default_session`
- Future enhancement: Multi-user session support

## Features in Detail

### Context Preservation
- The bot remembers the last 5 exchanges (10 messages total)
- Context is included in every query to maintain conversation flow
- References previous discussions when relevant

### Intelligent Document Retrieval
- LLM evaluates if local documents are sufficient
- Automatically searches web if more information needed
- Combines local and web sources for comprehensive answers

### Persistence
- Chat history survives application restarts
- Automatically loads previous conversation on startup
- No data loss when closing the application

## Troubleshooting

### MongoDB Connection Issues
- Verify MongoDB URI is correct
- Check network connectivity
- Ensure database and collection exist

### Chat History Not Loading
- Check MongoDB connection
- Verify `simple_chats` collection exists
- Use Refresh button to reload

### Server Connection Errors
- Ensure FastAPI server is running on port 8000
- Check no other services are using the ports
- Wait for servers to fully start before using

## Future Enhancements
- Multi-user session support with unique session IDs
- User authentication and authorization
- Export chat history functionality
- Advanced search within chat history
- Conversation summarization for long chats