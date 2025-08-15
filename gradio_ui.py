import gradio as gr
import requests
import json
from typing import List, Tuple, Optional, Dict
import time
from config import config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate configuration on startup
try:
    config.validate_required_keys()
    print("✅ Gradio UI configuration validation successful")
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    exit(1)

# FastAPI server URL from config
API_BASE_URL = config.get_api_base_url()

def load_sessions():
    """Load list of available sessions from server"""
    logger.info("Loading sessions from server...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        logger.info(f"Server response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            sessions = result.get("sessions", [])
            logger.info(f"Received {len(sessions)} sessions from server")
            
            # Create simple session ID list for dropdown
            session_ids = []
            for s in sessions:
                session_ids.append(s['session_id'])
                logger.debug(f"Session: {s['session_id']} - {s['display_name']} ({s['message_count']} msgs)")
            
            logger.info(f"✅ Loaded {len(session_ids)} sessions")
            return session_ids
        else:
            logger.error(f"❌ Error loading sessions: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error loading sessions: {str(e)}")
        return []

def get_session_display_info(session_id: str) -> str:
    """Get display information for a session"""
    if not session_id:
        return "No session selected"
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        if response.status_code == 200:
            result = response.json()
            sessions = result.get("sessions", [])
            for s in sessions:
                if s['session_id'] == session_id:
                    return f"{s['display_name']} ({s['message_count']} messages)"
        return f"Session: {session_id}"
    except:
        return f"Session: {session_id}"

def load_chat_history(session_id: str):
    """Load chat history for a specific session"""
    if not session_id:
        logger.info("No session ID provided, returning empty history")
        return []
    
    try:
        logger.info(f"Loading chat history for session: {session_id}")
        response = requests.get(f"{API_BASE_URL}/chat-history/{session_id}", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            chat_history = result.get("chat_history", [])
            
            # Convert to format expected by Gradio Chatbot
            history = []
            for user_msg, assistant_msg in chat_history:
                history.append([user_msg, assistant_msg])
                
            logger.info(f"✅ Loaded {len(history)} message exchanges for session {session_id}")
            return history
        else:
            logger.error(f"❌ Error loading chat history: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error loading chat history: {str(e)}")
        return []

def create_new_session(session_name: str):
    """Create a new chat session"""
    if not session_name or not session_name.strip():
        return None, [], "❌ Please enter a session name"
    
    try:
        payload = {"session_name": session_name.strip()}
        logger.info(f"Creating new session: {session_name}")
        response = requests.post(f"{API_BASE_URL}/create-session", json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            new_session_id = result["session_id"]
            logger.info(f"✅ Created new session with ID: {new_session_id}")
            
            # Reload sessions list
            updated_sessions = load_sessions()
            
            return (
                gr.update(choices=updated_sessions, value=new_session_id),  # Update dropdown
                [],  # Empty chat history
                f"✅ Created session: {new_session_id}"
            )
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            logger.error(f"❌ Failed to create session: {error_detail}")
            return gr.update(), [], f"❌ Failed to create session: {error_detail}"
            
    except Exception as e:
        logger.error(f"❌ Error creating session: {str(e)}")
        return gr.update(), [], f"❌ Error creating session: {str(e)}"

def delete_current_session(current_session_id: str):
    """Delete the currently selected session"""
    if not current_session_id:
        return gr.update(), [], "❌ No session selected to delete"
    
    try:
        logger.info(f"Deleting session: {current_session_id}")
        response = requests.delete(f"{API_BASE_URL}/delete-session/{current_session_id}", timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully deleted session: {current_session_id}")
            
            # Reload sessions
            updated_sessions = load_sessions()
            
            # Select first session if available
            new_selection = updated_sessions[0] if updated_sessions else None
            
            return (
                gr.update(choices=updated_sessions, value=new_selection),
                load_chat_history(new_selection) if new_selection else [],
                f"✅ Deleted session: {current_session_id}"
            )
        else:
            logger.error(f"❌ Failed to delete session: {response.status_code}")
            return gr.update(), [], "❌ Failed to delete session"
            
    except Exception as e:
        logger.error(f"❌ Error deleting session: {str(e)}")
        return gr.update(), [], f"❌ Error deleting session: {str(e)}"

def on_session_change(session_id: str):
    """Handle session selection change"""
    logger.info(f"Session changed to: '{session_id}'")
    
    if not session_id:
        logger.info("No session selected")
        return [], "No session selected", ""
    
    history = load_chat_history(session_id)
    display_info = get_session_display_info(session_id)
    return history, display_info, ""

def send_message(message: str, chat_history: List, current_session_id: str):
    """Send message to FastAPI server and update chat history"""
    if not message or not message.strip():
        return "", chat_history, "❌ Please enter a message"
    
    if not current_session_id:
        return "", chat_history, "❌ Please select or create a session first"
    
    try:
        # Send chat request with session_id
        payload = {
            "message": message.strip(),
            "session_id": current_session_id
        }
        logger.info(f"Sending message to session {current_session_id}: {message[:50]}...")
        
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=30)
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ Successfully received response")
            
            # Update chat history with new exchange
            new_history = []
            for user_msg, assistant_msg in result.get("chat_history", []):
                new_history.append([user_msg, assistant_msg])
            return "", new_history, ""
        else:
            # Add error message to status
            try:
                error_detail = response.json().get('detail', 'Unknown error')
                error_msg = f"❌ Error: {response.status_code} - {error_detail}"
            except:
                error_msg = f"❌ Error: {response.status_code}"
            logger.error(f"Error response: {error_msg}")
            return message, chat_history, error_msg
            
    except requests.exceptions.ConnectionError:
        logger.error("Connection error when sending message")
        return message, chat_history, "❌ Cannot connect to server"
    except requests.exceptions.Timeout:
        logger.error("Timeout when sending message")
        return message, chat_history, "❌ Request timed out"
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return message, chat_history, f"❌ Error: {str(e)}"

def clear_session_history(current_session_id: str):
    """Clear chat history for the current session"""
    if not current_session_id:
        return [], "❌ No session selected"
    
    try:
        logger.info(f"Clearing history for session: {current_session_id}")
        response = requests.delete(f"{API_BASE_URL}/chat-history/{current_session_id}", timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Successfully cleared history")
            return [], f"✅ Cleared history for session: {current_session_id}"
        else:
            logger.error(f"❌ Failed to clear history: {response.status_code}")
            return load_chat_history(current_session_id), f"❌ Failed to clear history"
            
    except Exception as e:
        logger.error(f"❌ Error clearing history: {str(e)}")
        return load_chat_history(current_session_id), f"❌ Error: {str(e)}"

def upload_pdf_file(file):
    """Upload PDF file to FastAPI server"""
    if file is None:
        return "❌ Please select a PDF file to upload"
    
    try:
        logger.info(f"Uploading PDF file: {file.name}")
        # Prepare file for upload
        files = {"file": (file.name, open(file.name, "rb"), "application/pdf")}
        
        # Send upload request
        response = requests.post(f"{API_BASE_URL}/upload-pdf", files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ Successfully uploaded PDF")
            return f"✅ {result['message']}\n📄 File: {result['filename']}\n📊 Chunks: {result['chunks_created']}\n⏱️ Time: {result['processing_time']}"
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            logger.error(f"❌ Upload failed: {error_detail}")
            return f"❌ Upload failed: {error_detail}"
            
    except Exception as e:
        logger.error(f"❌ Upload error: {str(e)}")
        return f"❌ Upload error: {str(e)}"
    finally:
        try:
            files["file"][1].close()
        except:
            pass

def refresh_sessions(current_session_id: str):
    """Refresh the session list"""
    logger.info("Refreshing sessions...")
    session_ids = load_sessions()
    
    # Keep current selection if it still exists
    if current_session_id in session_ids:
        history = load_chat_history(current_session_id)
        display_info = get_session_display_info(current_session_id)
        return (
            gr.update(choices=session_ids, value=current_session_id),
            history,
            display_info,
            "🔄 Refreshed"
        )
    elif session_ids:
        # Select first session if current doesn't exist
        first_session = session_ids[0]
        history = load_chat_history(first_session)
        display_info = get_session_display_info(first_session)
        return (
            gr.update(choices=session_ids, value=first_session),
            history,
            display_info,
            "🔄 Refreshed - Selected first session"
        )
    else:
        return (
            gr.update(choices=[], value=None),
            [],
            "No sessions available",
            "🔄 Refreshed - No sessions available"
        )

# Create Gradio interface
with gr.Blocks(title="RAG Multi-Session Chat", theme=gr.themes.Soft()) as app:
    # Header
    gr.Markdown("# 🤖 RAG Chat Interface - Multi-Session")
    gr.Markdown("Select an existing chat session or create a new one to start")
    
    # Session Management Section
    with gr.Row():
        with gr.Column(scale=3):
            with gr.Row():
                session_dropdown = gr.Dropdown(
                    label="Select Session",
                    choices=[],
                    value=None,
                    interactive=True,
                    scale=2
                )
                refresh_btn = gr.Button("🔄", scale=0, min_width=50)
            
        with gr.Column(scale=2):
            with gr.Row():
                new_session_name = gr.Textbox(
                    label="New Session Name",
                    placeholder="Enter name...",
                    scale=2
                )
                create_btn = gr.Button("Create New", variant="primary", scale=1)
                
        with gr.Column(scale=1):
            delete_btn = gr.Button("🗑️ Delete Session", variant="stop")
    
    # Status display
    status_text = gr.Textbox(
        label="Status",
        value="",
        interactive=False,
        max_lines=1
    )
    
    gr.Markdown("---")
    
    # Main Chat Interface
    with gr.Row():
        with gr.Column(scale=3):
            # Chat history display
            chatbot = gr.Chatbot(
                label="Chat History",
                height=450,
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
            
            # Chat control buttons
            with gr.Row():
                clear_history_btn = gr.Button("🗑️ Clear This Chat", variant="secondary")
                session_info = gr.Textbox(
                    label="Current Session",
                    value="No session selected",
                    interactive=False,
                    scale=2
                )
        
        # Right panel for document upload
        with gr.Column(scale=1):
            gr.Markdown("### 📄 Document Upload")
            gr.Markdown("*Documents are shared across all sessions*")
            pdf_file = gr.File(
                label="Upload PDF",
                file_types=[".pdf"],
                file_count="single"
            )
            upload_btn = gr.Button("Upload PDF", variant="primary")
            upload_status = gr.Textbox(
                label="Upload Status",
                interactive=False,
                lines=5
            )
    
    # Event Handlers
    
    # Session selection change
    session_dropdown.change(
        fn=on_session_change,
        inputs=[session_dropdown],
        outputs=[chatbot, session_info, status_text]
    )
    
    # Create new session
    create_btn.click(
        fn=create_new_session,
        inputs=[new_session_name],
        outputs=[session_dropdown, chatbot, status_text]
    ).then(
        fn=lambda: "",
        outputs=[new_session_name]
    )
    
    # Delete session
    delete_btn.click(
        fn=delete_current_session,
        inputs=[session_dropdown],
        outputs=[session_dropdown, chatbot, status_text]
    )
    
    # Send message
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot, session_dropdown],
        outputs=[msg_input, chatbot, status_text]
    )
    
    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot, session_dropdown],
        outputs=[msg_input, chatbot, status_text]
    )
    
    # Clear current session history
    clear_history_btn.click(
        fn=clear_session_history,
        inputs=[session_dropdown],
        outputs=[chatbot, status_text]
    )
    
    # Refresh button
    refresh_btn.click(
        fn=refresh_sessions,
        inputs=[session_dropdown],
        outputs=[session_dropdown, chatbot, session_info, status_text]
    )
    
    # Upload PDF
    upload_btn.click(
        fn=upload_pdf_file,
        inputs=[pdf_file],
        outputs=[upload_status]
    )
    
    # Initial load
    def initial_load():
        logger.info("Performing initial load...")
        session_ids = load_sessions()
        
        if session_ids:
            # Auto-select the first session
            first_session = session_ids[0]
            history = load_chat_history(first_session)
            display_info = get_session_display_info(first_session)
            logger.info(f"✅ Initial load complete, selected session: {first_session}")
            return (
                gr.update(choices=session_ids, value=first_session),
                history,
                display_info
            )
        
        logger.info("No sessions available on initial load")
        return gr.update(choices=[], value=None), [], "No sessions available - Create a new one to start"
    
    app.load(
        fn=initial_load,
        outputs=[session_dropdown, chatbot, session_info]
    )

if __name__ == "__main__":
    # Check if server is running first
    try:
        print("Checking if FastAPI server is running...")
        response = requests.get(API_BASE_URL, timeout=5)
        if response.status_code == 200:
            print("FastAPI server is running! Starting Gradio UI...")
            app.launch(server_name=config.GRADIO_HOST, server_port=config.GRADIO_PORT, share=False)
        else:
            print(f"⚠️ FastAPI server returned status {response.status_code}. Please make sure it's running correctly.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server!")
        print("Please start the FastAPI server first: python run_servers.py")
    except Exception as e:
        print(f"❌ Error starting Gradio UI: {str(e)}")