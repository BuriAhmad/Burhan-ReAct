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

    ENABLE_QUERY_CLASSIFICATION = os.getenv("ENABLE_QUERY_CLASSIFICATION", "true").lower() == "true"
    CASUAL_TEMPERATURE = float(os.getenv("CASUAL_TEMPERATURE", "0.7"))
    HISTORY_TEMPERATURE = float(os.getenv("HISTORY_TEMPERATURE", "0.3"))
    RETRIEVAL_TEMPERATURE = float(os.getenv("RETRIEVAL_TEMPERATURE", "0.2"))
    
    # Enhanced Chat History Configuration (NEW)
    CHECK_HISTORY_FOR_ANSWERS = os.getenv("CHECK_HISTORY_FOR_ANSWERS", "true").lower() == "true"
    HISTORY_CONTEXT_FORMAT = os.getenv("HISTORY_CONTEXT_FORMAT", "structured")  # "structured" or "simple"
    
    # Debug Configuration (NEW)
    DEBUG_PIPELINE_DECISIONS = os.getenv("DEBUG_PIPELINE_DECISIONS", "true").lower() == "true"
    LOG_QUERY_CLASSIFICATION = os.getenv("LOG_QUERY_CLASSIFICATION", "true").lower() == "true"

    VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "vector_search")
    
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

        print("\n--- Enhanced Features ---")
        print(f"Query Classification: {'✅ Enabled' if cls.ENABLE_QUERY_CLASSIFICATION else '❌ Disabled'}")
        print(f"History Answer Check: {'✅ Enabled' if cls.CHECK_HISTORY_FOR_ANSWERS else '❌ Disabled'}")
        print(f"Temperature Settings:")
        print(f"  - Casual: {cls.CASUAL_TEMPERATURE}")
        print(f"  - History: {cls.HISTORY_TEMPERATURE}")
        print(f"  - Retrieval: {cls.RETRIEVAL_TEMPERATURE}")
        print(f"Debug Pipeline: {'✅ On' if cls.DEBUG_PIPELINE_DECISIONS else '❌ Off'}")
        
        print("\n--- API Keys ---")
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