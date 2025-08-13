import gradio as gr
import requests
import json

# FastAPI server URL
API_BASE_URL = "http://127.0.0.1:8000"

def load_chat_history():
    """Load existing chat history from server"""
    try:
        response = requests.get(f"{API_BASE_URL}/chat-history", timeout=10)
        if response.status_code == 200:
            result = response.json()
            # Convert to format expected by Gradio Chatbot
            history = []
            for user_msg, assistant_msg in result.get("chat_history", []):
                history.append([user_msg, assistant_msg])
            return history
        return []
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return []

def send_message(message, chat_history):
    """Send message to FastAPI server and update chat history"""
    if not message:
        return "", chat_history
    
    try:
        # Send chat request
        payload = {"message": message}
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # Update chat history with new exchange
            new_history = []
            for user_msg, assistant_msg in result.get("chat_history", []):
                new_history.append([user_msg, assistant_msg])
            return "", new_history
        else:
            # Add error message to chat
            error_msg = f"Error: {response.status_code} - {response.text}"
            chat_history.append([message, error_msg])
            return "", chat_history
            
    except requests.exceptions.ConnectionError:
        error_msg = "Cannot connect to server. Make sure FastAPI server is running."
        chat_history.append([message, error_msg])
        return "", chat_history
    except requests.exceptions.Timeout:
        error_msg = "Request timed out. The server might be busy."
        chat_history.append([message, error_msg])
        return "", chat_history
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        chat_history.append([message, error_msg])
        return "", chat_history

def clear_chat_history():
    """Clear chat history on server and UI"""
    try:
        response = requests.delete(f"{API_BASE_URL}/chat-history", timeout=10)
        if response.status_code == 200:
            return [], "✅ Chat history cleared successfully"
        else:
            return [], f"❌ Failed to clear history: {response.text}"
    except Exception as e:
        return [], f"❌ Error clearing history: {str(e)}"

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
    
    # Chat Interface
    with gr.Row():
        with gr.Column(scale=3):
            # Chat history display
            chatbot = gr.Chatbot(
                label="Chat History",
                height=500,
                bubble_full_width=False,
                show_copy_button=True
            )
            
            # Message input row
            with gr.Row():
                msg_input = gr.Textbox(
                    label="Message",
                    placeholder="Type your message here...",
                    lines=2,
                    scale=4
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)
            
            # Control buttons
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear History", variant="stop")
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
                status_text = gr.Textbox(
                    label="Status",
                    interactive=False,
                    visible=False,
                    max_lines=1
                )
        
        # Right panel for document upload
        with gr.Column(scale=1):
            gr.Markdown("### 📄 Document Upload")
            pdf_file = gr.File(
                label="Upload PDF",
                file_types=[".pdf"],
                file_count="single"
            )
            upload_btn = gr.Button("Upload PDF", variant="primary")
            upload_status = gr.Textbox(
                label="Upload Status",
                interactive=False,
                lines=6
            )
    
    # Event handlers
    def refresh_chat():
        """Refresh chat history from server"""
        history = load_chat_history()
        return history
    
    # Send message on button click or Enter key
    send_btn.click(
        send_message,
        inputs=[msg_input, chatbot],
        outputs=[msg_input, chatbot]
    )
    
    msg_input.submit(
        send_message,
        inputs=[msg_input, chatbot],
        outputs=[msg_input, chatbot]
    )
    
    # Clear history
    clear_btn.click(
        clear_chat_history,
        outputs=[chatbot, status_text]
    ).then(
        lambda: gr.update(visible=True),
        outputs=[status_text]
    ).then(
        lambda: gr.update(visible=False),
        outputs=[status_text]
    )
    
    # Refresh chat history
    refresh_btn.click(
        refresh_chat,
        outputs=[chatbot]
    )
    
    # Upload PDF
    upload_btn.click(
        upload_pdf_file,
        inputs=pdf_file,
        outputs=upload_status
    )
    
    # Load existing chat history on startup
    app.load(refresh_chat, outputs=[chatbot])

if __name__ == "__main__":
    app.launch(server_name="127.0.0.1", server_port=7860, share=False)