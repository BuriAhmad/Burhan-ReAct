import gradio as gr
import requests
import json

# FastAPI server URL
API_BASE_URL = "http://127.0.0.1:8000"

def query_fastapi_server(message):
    """Send message to FastAPI server and get response"""
    try:
        # Check if server is running
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            return "❌ FastAPI server is not responding"
        
        # Send chat request
        payload = {"message": message}
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response received")
        else:
            return f"❌ Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to FastAPI server. Make sure it's running on http://127.0.0.1:8000"
    except requests.exceptions.Timeout:
        return "⏰ Request timed out. The server might be busy."
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

def check_server_status():
    """Check if FastAPI server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return "✅ FastAPI server is running and healthy"
        else:
            return "❌ FastAPI server responded with error"
    except:
        return "❌ FastAPI server is not accessible"

# Create Gradio interface
with gr.Blocks(title="RAG Chat Interface", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🤖 RAG Chat Interface")
    gr.Markdown("Basic chat interface connected to FastAPI server with Gemini API")
    
    # Server status section
    with gr.Row():
        status_btn = gr.Button("Check Server Status", variant="secondary")
        status_output = gr.Textbox(label="Server Status", interactive=False)
    
    status_btn.click(check_server_status, outputs=status_output)
    
    # Chat section
    with gr.Row():
        with gr.Column():
            message_input = gr.Textbox(
                label="Your Message",
                placeholder="Type your message here...",
                lines=3
            )
            submit_btn = gr.Button("Send Message", variant="primary")
            clear_btn = gr.Button("Clear", variant="secondary")
    
    with gr.Row():
        response_output = gr.Textbox(
            label="AI Response",
            lines=10,
            interactive=False
        )
    
    # Event handlers
    submit_btn.click(
        query_fastapi_server,
        inputs=message_input,
        outputs=response_output
    )
    
    clear_btn.click(
        lambda: ("", ""),
        outputs=[message_input, response_output]
    )
    
    # Allow Enter key to submit
    message_input.submit(
        query_fastapi_server,
        inputs=message_input,
        outputs=response_output
    )

if __name__ == "__main__":
    app.launch(server_name="127.0.0.1", server_port=7860, share=False)