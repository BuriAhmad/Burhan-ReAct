import gradio as gr
import requests
import json
from typing import List, Tuple, Optional
import time

# FastAPI server URL
API_BASE_URL = "http://127.0.0.1:8000"

def load_sessions():
    """Load list of available sessions from server"""
    try:
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        if response.status_code == 200:
            result = response.json()
            sessions = result.get("sessions", [])
            
            # Create choices for dropdown as a dictionary (better format for Gradio)
            choices = {}
            for s in sessions:
                display_text = f"{s['display_name']} ({s['message_count']} msgs)"
                choices[display_text] = s['session_id']
            
            print(f"Loaded {len(choices)} sessions")
            return choices
        else:
            print(f"Error loading sessions: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error loading sessions: {str(e)}")
        return {}

def load_chat_history(session_id: str):
    """Load chat history for a specific session"""
    if not session_id:
        return []
    
    try:
        print(f"Loading chat history for session: {session_id}")
        response = requests.get(f"{API_BASE_URL}/chat-history/{session_id}", timeout=10)
        if response.status_code == 200:
            result = response.json()
            # Convert to format expected by Gradio Chatbot
            history = []
            for user_msg, assistant_msg in result.get("chat_history", []):
                history.append([user_msg, assistant_msg])
            print(f"Loaded {len(history)} message exchanges")
            return history
        else:
            print(f"Error loading chat history: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return []

def create_new_session(session_name: str):
    """Create a new chat session"""
    if not session_name or not session_name.strip():
        return None, None, [], "❌ Please enter a session name"
    
    try:
        payload = {"session_name": session_name.strip()}
        print(f"Creating new session: {session_name}")
        response = requests.post(f"{API_BASE_URL}/create-session", json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            new_session_id = result["session_id"]
            print(f"Created new session with ID: {new_session_id}")
            
            # Reload sessions list
            updated_sessions = load_sessions()
            
            # Return new session ID both for dropdown and state
            return updated_sessions, new_session_id, [], f"✅ Created session: {new_session_id}"
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return None, None, [], f"❌ Failed to create session: {error_detail}"
    except Exception as e:
        return None, None, [], f"❌ Error creating session: {str(e)}"

def delete_current_session(session_id: str):
    """Delete the currently selected session"""
    if not session_id:
        return None, None, [], "❌ No session selected to delete"
    
    try:
        print(f"Deleting session: {session_id}")
        response = requests.delete(f"{API_BASE_URL}/delete-session/{session_id}", timeout=10)
        
        if response.status_code == 200:
            print(f"Successfully deleted session: {session_id}")
            # Reload sessions and clear selection
            updated_sessions = load_sessions()
            return updated_sessions, None, [], f"✅ Deleted session: {session_id}"
        else:
            print(f"Failed to delete session: {response.status_code}")
            return load_sessions(), session_id, load_chat_history(session_id), "❌ Failed to delete session"
    except Exception as e:
        print(f"Error deleting session: {str(e)}")
        return load_sessions(), session_id, load_chat_history(session_id), f"❌ Error deleting session: {str(e)}"

def on_session_change(session_id: str):
    """Handle session selection change"""
    print(f"Session changed to: {session_id}")
    
    if not session_id:
        return [], "No session selected", ""
    
    history = load_chat_history(session_id)
    return history, f"Session: {session_id}", ""

def send_message(message: str, chat_history: List, session_id: str):
    """Send message to FastAPI server and update chat history"""
    if not message or not message.strip():
        return "", chat_history, "❌ Please enter a message"
    
    if not session_id:
        return "", chat_history, "❌ Please select or create a session first"
    
    try:
        # Send chat request with session_id
        payload = {
            "message": message.strip(),
            "session_id": session_id
        }
        print(f"Sending message to session {session_id}: {message[:50]}...")
        
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Successfully received response")
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
            print(f"Error response: {error_msg}")
            return message, chat_history, error_msg
            
    except requests.exceptions.ConnectionError:
        print("Connection error when sending message")
        return message, chat_history, "❌ Cannot connect to server"
    except requests.exceptions.Timeout:
        print("Timeout when sending message")
        return message, chat_history, "❌ Request timed out"
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return message, chat_history, f"❌ Error: {str(e)}"

def clear_session_history(session_id: str):
    """Clear chat history for the current session"""
    if not session_id:
        return [], "❌ No session selected"
    
    try:
        print(f"Clearing history for session: {session_id}")
        response = requests.delete(f"{API_BASE_URL}/chat-history/{session_id}", timeout=10)
        if response.status_code == 200:
            print("Successfully cleared history")
            return [], f"✅ Cleared history for session: {session_id}"
        else:
            print(f"Failed to clear history: {response.status_code}")
            return load_chat_history(session_id), f"❌ Failed to clear history"
    except Exception as e:
        print(f"Error clearing history: {str(e)}")
        return load_chat_history(session_id), f"❌ Error: {str(e)}"

def upload_pdf_file(file):
    """Upload PDF file to FastAPI server"""
    if file is None:
        return "❌ Please select a PDF file to upload"
    
    try:
        print(f"Uploading PDF file: {file.name}")
        # Prepare file for upload
        files = {"file": (file.name, open(file.name, "rb"), "application/pdf")}
        
        # Send upload request
        response = requests.post(f"{API_BASE_URL}/upload-pdf", files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("Successfully uploaded PDF")
            return f"✅ {result['message']}\n📄 File: {result['filename']}\n📊 Chunks: {result['chunks_created']}\n⏱️ Time: {result['processing_time']}"
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            print(f"Upload failed: {error_detail}")
            return f"❌ Upload failed: {error_detail}"
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return f"❌ Upload error: {str(e)}"
    finally:
        try:
            files["file"][1].close()
        except:
            pass

def refresh_interface(session_id):
    """Refresh the entire interface"""
    print("Refreshing interface")
    sessions = load_sessions()
    
    if session_id and session_id in [s_id for s_id in sessions.values()]:
        # Session still exists
        history = load_chat_history(session_id)
        return sessions, session_id, history, "🔄 Refreshed"
    
    if sessions:
        # Auto-select first session if current one doesn't exist
        first_session_id = next(iter(sessions.values()))
        history = load_chat_history(first_session_id)
        return sessions, first_session_id, history, "🔄 Refreshed - Selected first session"
    
    return sessions, None, [], "🔄 Refreshed - No sessions available"

# Create Gradio interface
with gr.Blocks(title="RAG Multi-Session Chat", theme=gr.themes.Soft()) as app:
    # Header
    gr.Markdown("# 🤖 RAG Chat Interface - Multi-Session")
    gr.Markdown("Select an existing chat session or create a new one to start")
    
    # Session state (hidden)
    session_state = gr.State(value=None)
    
    # Session Management Section
    with gr.Row():
        with gr.Column(scale=3):
            with gr.Row():
                session_dropdown = gr.Dropdown(
                    label="Select Session",
                    choices=load_sessions(),
                    value=None,
                    interactive=True,
                    scale=2,
                    allow_custom_value=False
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
    
    # Session selection change - FIXED
    session_dropdown.change(
        fn=on_session_change,
        inputs=[session_dropdown],
        outputs=[chatbot, session_info, status_text]
    ).then(
        fn=lambda x: x,
        inputs=[session_dropdown],
        outputs=[session_state]
    )
    
    # Create new session - FIXED
    create_btn.click(
        fn=create_new_session,
        inputs=[new_session_name],
        outputs=[session_dropdown, session_dropdown, chatbot, status_text]
    ).then(
        fn=lambda: "",
        outputs=[new_session_name]
    ).then(
        fn=lambda x: x,
        inputs=[session_dropdown],
        outputs=[session_state]
    ).then(
        fn=lambda x: f"Session: {x}" if x else "No session selected",
        inputs=[session_state],
        outputs=[session_info]
    )
    
    # Delete session - FIXED
    delete_btn.click(
        fn=delete_current_session,
        inputs=[session_state],
        outputs=[session_dropdown, session_dropdown, chatbot, status_text]
    ).then(
        fn=lambda x: x,
        inputs=[session_dropdown],
        outputs=[session_state]
    ).then(
        fn=lambda x: f"Session: {x}" if x else "No session selected",
        inputs=[session_state],
        outputs=[session_info]
    )
    
    # Send message - FIXED
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot, session_state],
        outputs=[msg_input, chatbot, status_text]
    )
    
    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot, session_state],
        outputs=[msg_input, chatbot, status_text]
    )
    
    # Clear current session history
    clear_history_btn.click(
        fn=clear_session_history,
        inputs=[session_state],
        outputs=[chatbot, status_text]
    )
    
    # Refresh button - FIXED
    refresh_btn.click(
        fn=refresh_interface,
        inputs=[session_state],
        outputs=[session_dropdown, session_dropdown, chatbot, status_text]
    ).then(
        fn=lambda x: x,
        inputs=[session_dropdown],
        outputs=[session_state]
    ).then(
        fn=lambda x: f"Session: {x}" if x else "No session selected",
        inputs=[session_state],
        outputs=[session_info]
    )
    
    # Upload PDF
    upload_btn.click(
        fn=upload_pdf_file,
        inputs=[pdf_file],
        outputs=[upload_status]
    )
    
    # Initial load
    def initial_load():
        sessions = load_sessions()
        
        if sessions:
            # Auto-select the first session
            first_session_id = next(iter(sessions.values()))
            history = load_chat_history(first_session_id)
            return sessions, first_session_id, history, f"Session: {first_session_id}", first_session_id
        
        return {}, None, [], "No sessions available - Create a new one to start", None
    
    app.load(
        fn=initial_load,
        outputs=[session_dropdown, session_dropdown, chatbot, session_info, session_state]
    )

if __name__ == "__main__":
    # Check if server is running first
    try:
        print("Checking if FastAPI server is running...")
        response = requests.get(API_BASE_URL, timeout=5)
        if response.status_code == 200:
            print("FastAPI server is running! Starting Gradio UI...")
            app.launch(server_name="127.0.0.1", server_port=7860, share=False)
        else:
            print(f"⚠️ FastAPI server returned status {response.status_code}. Please make sure it's running correctly.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server!")
        print("Please start the FastAPI server first: python run_servers.py")
    except Exception as e:
        print(f"❌ Error starting Gradio UI: {str(e)}")