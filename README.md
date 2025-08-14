# RAG Chat Application with Persistent Chat History

A FastAPI-based RAG (Retrieval-Augmented Generation) application using MongoDB for document storage, chat history persistence, and Google Gemini for AI responses.

## 🔒 Security & Configuration

### Environment Variables Setup (REQUIRED)

**⚠️ IMPORTANT: Never commit API keys to version control!**

1. **Create your environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual credentials:**
   ```bash
   # API Keys - Replace with your actual keys
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   TAVILY_API_KEY=your_actual_tavily_api_key_here
   
   # MongoDB Configuration - Replace with your actual connection string
   MONGODB_URI=your_actual_mongodb_connection_string_here
   
   # Database Configuration
   DATABASE_NAME=knowledge_base
   COLLECTION_NAME=documents
   ```

3. **Verify configuration:**
   ```bash
   python -c "from config import config; config.print_config_summary()"
   ```

### Getting API Keys

- **Google Gemini API**: Get your key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Tavily API**: Get your key from [Tavily Dashboard](https://app.tavily.com)
- **MongoDB Atlas**: Get connection string from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

### Configuration Options

All settings can be customized in your `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Google Gemini API key (required) |
| `TAVILY_API_KEY` | - | Tavily search API key (required) |
| `MONGODB_URI` | - | MongoDB connection string (required) |
| `DATABASE_NAME` | `knowledge_base` | MongoDB database name |
| `COLLECTION_NAME` | `documents` | MongoDB collection for documents |
| `API_HOST` | `127.0.0.1` | FastAPI server host |
| `API_PORT` | `8000` | FastAPI server port |
| `GRADIO_HOST` | `127.0.0.1` | Gradio UI host |
| `GRADIO_PORT` | `7860` | Gradio UI port |
| `CHUNK_SIZE` | `3500` | PDF text chunk size |
| `CHUNK_OVERLAP` | `150` | PDF text chunk overlap |
| `SIMILARITY_SEARCH_LIMIT` | `5` | Number of similar documents to retrieve |
| `CHAT_HISTORY_LIMIT` | `5` | Number of recent exchanges to maintain as context |

## Features

- **Persistent Chat History**: Conversations are saved and restored across sessions
- **Context-Aware Responses**: Bot remembers last 5 exchanges for continuity
- **Two-Way Chat Interface**: Interactive chat UI with message history display
- **RAG Chat**: AI responses augmented with relevant documents from MongoDB
- **PDF Upload**: Upload and process PDF documents for knowledge base
- **Web Search Integration**: Automatic web search when local documents insufficient
- **MongoDB Integration**: Connect to MongoDB Atlas for document and chat storage
- **Multi-Session Support**: Create and manage multiple independent chat sessions
- **Secure Configuration**: Environment-based configuration with no hardcoded secrets

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Follow the [Security & Configuration](#-security--configuration) section above.

### 3. MongoDB Configuration

The chat history is stored in MongoDB with the following structure:
- Database: Configurable via `DATABASE_NAME` (default: `knowledge_base`)
- Collection: `simple_chats`
- Schema:
```json
{
  "_id": "session_name_123",
  "display_name": "session_name",
  "messages": [
    ["user message 1", "assistant response 1"],
    ["user message 2", "assistant response 2"]
  ],
  "created_at": "2024-01-01T00:00:00",
  "last_updated": "2024-01-01T00:00:00",
  "message_count": 2
}
```

### 4. Start the Application

**Option 1: Use the startup script (recommended):**
```bash
python run_servers.py
```

**Option 2: Start manually:**
```bash
# Terminal 1 - Start FastAPI server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 - Start Gradio UI
python gradio_ui.py
```

## Usage

### First Time Setup
1. Create your `.env` file with your API keys
2. Run `python run_servers.py`
3. Open the Gradio UI (default: http://127.0.0.1:7860)
4. Create your first chat session

### Chat Interface
1. Select an existing session or create a new one
2. Type messages in the input box and press Enter or click Send
3. Chat history is automatically saved and will persist across sessions
4. The bot maintains context of the last 5 exchanges

### Document Upload
1. Use the right panel to upload PDF documents
2. Documents are processed and stored in MongoDB vector store
3. Future queries will retrieve relevant information from uploaded documents

### Session Management
- **Create**: Use the "Create New" button with a session name
- **Switch**: Use the dropdown to select different sessions
- **Delete**: Use the "Delete Session" button to remove a session
- **Clear History**: Clear messages for the current session only

## API Endpoints

- `GET /` - Health check and configuration status
- `POST /create-session` - Create a new chat session
- `GET /list-sessions` - List all available sessions
- `DELETE /delete-session/{session_id}` - Delete a specific session
- `POST /chat` - Main chat endpoint with RAG and history
- `GET /chat-history/{session_id}` - Retrieve chat history for a session
- `DELETE /chat-history/{session_id}` - Clear chat history for a session
- `GET /session-info/{session_id}` - Get session metadata
- `POST /upload-pdf` - Upload and process PDF documents

## Security Best Practices

1. **Never commit `.env` files** - Already configured in `.gitignore`
2. **Use strong, unique API keys** - Regenerate keys if compromised
3. **Restrict MongoDB access** - Use MongoDB Atlas IP whitelist
4. **Regular key rotation** - Update API keys periodically
5. **Monitor API usage** - Watch for unusual activity
6. **Backup your data** - Regular MongoDB backups

## Migration from Single-Session

If you have existing chat data from an older version:

```bash
python migrate.py
```

This will convert your old `default_session` data to the new multi-session format.

## Troubleshooting

### Configuration Issues
```bash
# Check configuration status
python -c "from config import config; config.print_config_summary()"

# Test specific components
python config.py
```

### Missing API Keys
- Error: `Configuration Error: Missing required environment variables`
- Solution: Ensure all required variables are set in your `.env` file

### MongoDB Connection Issues
- Verify MongoDB URI in `.env` file
- Check network connectivity and IP whitelist
- Ensure database and collection permissions

### Server Connection Errors
- Verify no other services are using the configured ports
- Check firewall settings
- Wait for servers to fully start before using

## File Structure

```
├── .env                 # Your environment variables (create this)
├── .env.example         # Template for environment variables
├── .gitignore          # Git ignore file (includes .env)
├── config.py           # Configuration management
├── main.py             # FastAPI server
├── gradio_ui.py        # Gradio user interface
├── rag_pipeline.py     # RAG pipeline logic
├── vector_store.py     # MongoDB vector operations
├── chat_history.py     # Chat session management
├── pdf_processor.py    # PDF processing utilities
├── run_servers.py      # Server startup script
├── migrate.py          # Migration utility
├── requirements.txt    # Python dependencies
└── test_*.py          # Test scripts
```

## Future Enhancements
- User authentication and authorization
- Export chat history functionality
- Advanced search within chat history
- Conversation summarization for long chats
- Role-based access control
- API rate limiting and usage analytics