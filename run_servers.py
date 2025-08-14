import subprocess
import time
import sys
import os
from config import config

def validate_configuration():
    """Validate configuration before starting servers"""
    try:
        config.validate_required_keys()
        print("✅ Configuration validation successful")
        config.print_config_summary()
        return True
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease:")
        print("1. Create a .env file in the project directory")
        print("2. Copy the contents from .env.example")
        print("3. Replace the placeholder values with your actual API keys")
        return False

def run_fastapi_server():
    """Start FastAPI server using config values"""
    print("🚀 Starting FastAPI server...")
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", 
        "--host", config.API_HOST, 
        "--port", str(config.API_PORT), 
        "--reload"
    ])

def run_gradio_ui():
    """Start Gradio UI"""
    print("🎨 Starting Gradio UI...")
    return subprocess.Popen([sys.executable, "gradio_ui.py"])

if __name__ == "__main__":
    print("🤖 Starting RAG Application with Multi-Session Support...")
    print("=" * 50)
    
    # Validate configuration first
    if not validate_configuration():
        print("\n❌ Cannot start servers due to configuration errors.")
        print("Please fix the configuration and try again.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🔧 Starting servers with configuration:")
    print(f"   FastAPI: http://{config.API_HOST}:{config.API_PORT}")
    print(f"   Gradio UI: http://{config.GRADIO_HOST}:{config.GRADIO_PORT}")
    print("=" * 50)
    
    # Start FastAPI server
    fastapi_process = run_fastapi_server()
    
    # Wait a bit for FastAPI to start
    print("⏳ Waiting for FastAPI server to start...")
    time.sleep(5)
    
    # Start Gradio UI
    gradio_process = run_gradio_ui()
    
    print("\n" + "=" * 50)
    print("✅ Both servers are starting up!")
    print(f"📍 FastAPI Server: http://{config.API_HOST}:{config.API_PORT}")
    print(f"📍 Gradio UI: http://{config.GRADIO_HOST}:{config.GRADIO_PORT}")
    print("\n🎯 Features:")
    print("  • Multiple independent chat sessions")
    print("  • Persistent history for each session")
    print(f"  • Context-aware responses (last {config.CHAT_HISTORY_LIMIT} exchanges)")
    print("  • Session management (create/switch/delete)")
    print("  • PDF document upload and processing")
    print("  • Web search integration with Tavily")
    print("\nPress Ctrl+C to stop both servers")
    print("=" * 50)
    
    try:
        # Keep both processes running
        fastapi_process.wait()
        gradio_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        fastapi_process.terminate()
        gradio_process.terminate()
        print("✅ Servers stopped successfully!")