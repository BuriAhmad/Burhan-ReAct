import gradio as gr
import requests
import json

# FastAPI server URL
API_BASE_URL = "http://127.0.0.1:8000"

def query_fastapi_server(message):
    """Send message to FastAPI server and get response"""
    try:
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

def upload_pdf_file(file):
    """Upload PDF file to FastAPI server"""
    if file is None:
        return "❌ Please select a PDF file to upload"
    
    try:
        # Prepare file for upload
        files = {"file": (file.name, open(file.name, "rb"), "application/pdf")}
        
        # Send upload request
        response = requests.post(f"{API_BASE_URL}/upload-pdf", files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return f"✅ {result['message']}\n📄 File: {result['filename']}\n📊 Chunks created: {result['chunks_created']}\n⏱️ Processing time: {result['processing_time']}"
        else:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            return f"❌ Upload failed: {error_detail}"
            
    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to server. Make sure FastAPI server is running."
    except requests.exceptions.Timeout:
        return "⏰ Upload timed out. Large files may take longer to process."
    except Exception as e:
        return f"❌ Upload error: {str(e)}"
    finally:
        # Clean up file handle
        try:
            files["file"][1].close()
        except:
            pass

# Create Gradio interface
with gr.Blocks(title="RAG Chat Interface", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🤖 RAG Chat Interface")
    gr.Markdown("Chat interface with document upload and retrieval-augmented generation")
    
    # PDF Upload section
    with gr.Row():
        gr.Markdown("## 📄 Document Upload")
    
    with gr.Row():
        with gr.Column():
            pdf_file = gr.File(
                label="Upload PDF Document",
                file_types=[".pdf"],
                file_count="single"
            )
            upload_btn = gr.Button("Upload PDF", variant="primary")
        
        with gr.Column():
            upload_status = gr.Textbox(
                label="Upload Status",
                interactive=False,
                lines=4
            )
    
    gr.Markdown("---")
    
    # Chat section
    with gr.Row():
        gr.Markdown("## 💬 Chat")
    
    with gr.Row():
        with gr.Column():
            message_input = gr.Textbox(
                label="Your Message",
                placeholder="Ask questions about your uploaded documents...",
                lines=3
            )
            with gr.Row():
                submit_btn = gr.Button("Send Message", variant="primary")
                clear_btn = gr.Button("Clear", variant="secondary")
    
    with gr.Row():
        response_output = gr.Textbox(
            label="AI Response",
            lines=10,
            interactive=False
        )
    
    # Event handlers
    upload_btn.click(
        upload_pdf_file,
        inputs=pdf_file,
        outputs=upload_status
    )
    
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