import subprocess
import time
import sys
import os

def run_fastapi_server():
    """Start FastAPI server"""
    print("🚀 Starting FastAPI server...")
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", 
        "--host", "127.0.0.1", "--port", "8000", "--reload"
    ])

def run_gradio_ui():
    """Start Gradio UI"""
    print("🎨 Starting Gradio UI...")
    return subprocess.Popen([sys.executable, "gradio_ui.py"])

if __name__ == "__main__":
    print("🤖 Starting RAG Application...")
    print("=" * 50)
    
    # Start FastAPI server
    fastapi_process = run_fastapi_server()
    
    # Wait a bit for FastAPI to start
    print("⏳ Waiting for FastAPI server to start...")
    time.sleep(3)
    
    # Start Gradio UI
    gradio_process = run_gradio_ui()
    
    print("\n" + "=" * 50)
    print("✅ Both servers are starting up!")
    print("📍 FastAPI Server: http://127.0.0.1:8000")
    print("📍 Gradio UI: http://127.0.0.1:7860")
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