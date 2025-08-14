import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for managing environment variables"""
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")
    
    # Vector Store Configuration
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
    EMBEDDING_FIELD_NAME = os.getenv("EMBEDDING_FIELD_NAME", "embedding")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "thenlper/gte-small")
    
    # Server Configuration
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    GRADIO_HOST = os.getenv("GRADIO_HOST", "127.0.0.1")
    GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))
    
    # PDF Processing Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "3500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
    
    # RAG Configuration
    SIMILARITY_SEARCH_LIMIT = int(os.getenv("SIMILARITY_SEARCH_LIMIT", "5"))
    CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "5"))
    
    @classmethod
    def validate_required_keys(cls):
        """Validate that all required environment variables are set"""
        required_keys = [
            ("GEMINI_API_KEY", cls.GEMINI_API_KEY),
            ("TAVILY_API_KEY", cls.TAVILY_API_KEY),
            ("MONGODB_URI", cls.MONGODB_URI),
        ]
        
        missing_keys = []
        for key_name, key_value in required_keys:
            if not key_value:
                missing_keys.append(key_name)
        
        if missing_keys:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_keys)}\n"
                f"Please check your .env file and ensure these variables are set."
            )
        
        return True
    
    @classmethod
    def get_api_base_url(cls):
        """Get the FastAPI base URL"""
        return f"http://{cls.API_HOST}:{cls.API_PORT}"
    
    @classmethod
    def print_config_summary(cls):
        """Print configuration summary (without sensitive data)"""
        print("=" * 50)
        print("Configuration Summary")
        print("=" * 50)
        print(f"Database Name: {cls.DATABASE_NAME}")
        print(f"Collection Name: {cls.COLLECTION_NAME}")
        print(f"Embedding Model: {cls.EMBEDDING_MODEL_NAME}")
        print(f"API Server: {cls.API_HOST}:{cls.API_PORT}")
        print(f"Gradio UI: {cls.GRADIO_HOST}:{cls.GRADIO_PORT}")
        print(f"Chunk Size: {cls.CHUNK_SIZE}")
        print(f"Chat History Limit: {cls.CHAT_HISTORY_LIMIT}")
        print(f"Gemini API Key: {'✅ Set' if cls.GEMINI_API_KEY else '❌ Missing'}")
        print(f"Tavily API Key: {'✅ Set' if cls.TAVILY_API_KEY else '❌ Missing'}")
        print(f"MongoDB URI: {'✅ Set' if cls.MONGODB_URI else '❌ Missing'}")
        print("=" * 50)

# Create a global config instance
config = Config()

# Validate configuration on import
if __name__ != "__main__":
    try:
        config.validate_required_keys()
    except ValueError as e:
        print(f"⚠️ Configuration Error: {e}")
        print("Please create a .env file with the required environment variables.")