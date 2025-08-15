import os
import time
import json
import logging
from typing import List

import gradio as gr
import requests
from config import config

# ──────────────────────────────────────────────────────────────────────────────
# Logging & Config
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradio_ui")

try:
    config.validate_required_keys()
    print("✅ Gradio UI configuration validation successful")
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    raise SystemExit(1)

API_BASE_URL = config.get_api_base_url()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers talking to the FastAPI backend
# ──────────────────────────────────────────────────────────────────────────────
def load_sessions() -> List[str]:
    """Return a flat list of session IDs for the dropdown."""
    try:
        r = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        if r.status_code != 200:
            logger.error("Failed to load sessions: %s", r.text)
            return []
        payload = r.json()
        sessions = payload.get("sessions", [])
        return [s["session_id"] for s in sessions]
    except Exception as e:
        logger.error("Error loading sessions: %s", e)
        return []


def _fetch_sessions_payload() -> list:
    """Full payload access (display_name, message_count, etc.) for labels."""
    try:
        r = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        if r.status_code != 200:
            return []
        return r.json().get("sessions", [])
    except Exception:
        return []


def get_session_display_info(session_id: str) -> str:
    if not session_id:
        return "No session selected"
    for s in _fetch_sessions_payload():
        if s.get("session_id") == session_id:
            return f"{s.get('display_name', session_id)} ({s.get('message_count', 0)} messages)"
    return f"Session: {session_id}"


def load_chat_history(session_id: str):
    """Return history as [[user, assistant], ...] for Gradio Chatbot."""
    if not session_id:
        return []
    try:
        r = requests.get(f"{API_BASE_URL}/chat-history/{session_id}", timeout=10)
        if r.status_code != 200:
            logger.error("Error loading history: %s", r.text)
            return []
        pairs = r.json().get("chat_history", [])
        return [[u, a] for u, a in pairs]
    except Exception as e:
        logger.error("History error: %s", e)
        return []


def create_new_session(session_name: str):
    if not session_name or not session_name.strip():
        return gr.update(), [], "❌ Please enter a session name"

    try:
        payload = {"session_name": session_name.strip()}
        r = requests.post(f"{API_BASE_URL}/create-session", json=payload, timeout=10)
        if r.status_code != 200:
            detail = (r.json().get("detail") if r.headers.get("Content-Type", "").startswith("application/json") else r.text) or "Unknown error"
            return gr.update(), [], f"❌ Failed to create session: {detail}"

        new_session_id = r.json()["session_id"]
        choices = load_sessions()
        return gr.update(choices=choices, value=new_session_id), [], f"✅ Created session: {new_session_id}"
    except Exception as e:
        return gr.update(), [], f"❌ Error creating session: {e}"


def delete_current_session(session_id: str):
    if not session_id:
        return gr.update(), [], "❌ No session selected to delete"
    try:
        r = requests.delete(f"{API_BASE_URL}/delete-session/{session_id}", timeout=10)
        if r.status_code != 200:
            return gr.update(), [], f"❌ Failed to delete session ({r.status_code})"

        choices = load_sessions()
        next_sel = choices[0] if choices else None
        return (
            gr.update(choices=choices, value=next_sel),
            load_chat_history(next_sel) if next_sel else [],
            f"✅ Deleted session: {session_id}",
        )
    except Exception as e:
        return gr.update(), [], f"❌ Error deleting session: {e}"


def on_session_change(session_id: str):
    if not session_id:
        return [], "No session selected", ""
    return load_chat_history(session_id), get_session_display_info(session_id), ""


def send_message(message: str, chat_history: List, session_id: str):
    if not message or not message.strip():
        return "", chat_history, "❌ Please enter a message"
    if not session_id:
        return "", chat_history, "❌ Please select or create a session first"

    try:
        payload = {"message": message.strip(), "session_id": session_id}
        r = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=45)
        if r.status_code != 200:
            detail = (r.json().get("detail") if r.headers.get("Content-Type", "").startswith("application/json") else r.text) or "Unknown error"
            return message, chat_history, f"❌ Error: {r.status_code} - {detail}"

        hist = r.json().get("chat_history", [])
        return "", [[u, a] for u, a in hist], ""
    except requests.exceptions.ConnectionError:
        return message, chat_history, "❌ Cannot connect to server"
    except requests.exceptions.Timeout:
        return message, chat_history, "❌ Request timed out"
    except Exception as e:
        return message, chat_history, f"❌ Error: {e}"


def clear_session_history(session_id: str):
    if not session_id:
        return [], "❌ No session selected"
    try:
        r = requests.delete(f"{API_BASE_URL}/chat-history/{session_id}", timeout=10)
        if r.status_code == 200:
            return [], f"✅ Cleared history for session: {session_id}"
        return load_chat_history(session_id), "❌ Failed to clear history"
    except Exception as e:
        return load_chat_history(session_id), f"❌ Error: {e}"


def upload_pdf_file(file, session_id: str):
    """
    Uploads a PDF to the backend, **scoped to the given session**.
    Assumes the FastAPI /upload-pdf endpoint accepts a form field 'session_id'
    alongside the file (i.e., `session_id: str = Form(None)` on the server).
    """
    if file is None:
        return "❌ Please select a PDF file to upload"
    if not session_id:
        return "❌ Please select a session before uploading"

    files = None
    try:
        filename = os.path.basename(file.name)
        files = {"file": (filename, open(file.name, "rb"), "application/pdf")}
        # Send session_id as additional form data
        data = {"session_id": session_id}

        t0 = time.time()
        r = requests.post(f"{API_BASE_URL}/upload-pdf", files=files, data=data, timeout=120)
        dt = f"{time.time() - t0:.2f}s"

        if r.status_code != 200:
            detail = (r.json().get("detail") if r.headers.get("Content-Type", "").startswith("application/json") else r.text) or "Unknown error"
            return f"❌ Upload failed: {detail}"

        res = r.json()
        return (
            "✅ PDF uploaded and processed\n"
            f"📎 Session: {session_id}\n"
            f"📄 File: {res.get('filename','')}\n"
            f"📊 Chunks: {res.get('chunks_created', 0)}\n"
            f"⏱️ Time: {res.get('processing_time', dt)}"
        )
    except Exception as e:
        return f"❌ Upload error: {e}"
    finally:
        try:
            if files and files["file"][1]:
                files["file"][1].close()
        except Exception:
            pass


def refresh_sessions(current_session_id: str):
    choices = load_sessions()
    if current_session_id in choices:
        return (
            gr.update(choices=choices, value=current_session_id),
            load_chat_history(current_session_id),
            get_session_display_info(current_session_id),
            "🔄 Refreshed",
        )
    elif choices:
        first_sel = choices[0]
        return (
            gr.update(choices=choices, value=first_sel),
            load_chat_history(first_sel),
            get_session_display_info(first_sel),
            "🔄 Refreshed – Selected first session",
        )
    else:
        return gr.update(choices=[], value=None), [], "No sessions available", "🔄 Refreshed – No sessions"


# ──────────────────────────────────────────────────────────────────────────────
# Gradio App
# ──────────────────────────────────────────────────────────────────────────────
with gr.Blocks(title="RAG Chat (Session-Scoped Docs)", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🤖 RAG Chat — Session-Scoped Documents")
    gr.Markdown("Create/select a session. Uploads and retrievals are **isolated per session**.")

    # Session controls
    with gr.Row():
        with gr.Column(scale=3):
            with gr.Row():
                session_dropdown = gr.Dropdown(
                    label="Select Session",
                    choices=[],
                    value=None,
                    interactive=True,
                    scale=2,
                )
                refresh_btn = gr.Button("🔄", scale=0, min_width=56)
        with gr.Column(scale=2):
            with gr.Row():
                new_session_name = gr.Textbox(label="New Session Name", placeholder="e.g., research_aug15", scale=2)
                create_btn = gr.Button("Create New", variant="primary", scale=1)
        with gr.Column(scale=1):
            delete_btn = gr.Button("🗑️ Delete Session", variant="stop")

    status_text = gr.Textbox(label="Status", value="", interactive=False, max_lines=1)

    gr.Markdown("---")

    with gr.Row():
        # Left: Chat
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Chat History",
                height=460,
                bubble_full_width=False,
                show_copy_button=True,
            )

            with gr.Row():
                msg_input = gr.Textbox(
                    label="Message",
                    placeholder="Ask a question...",
                    lines=2,
                    scale=4,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            with gr.Row():
                clear_history_btn = gr.Button("🧹 Clear This Chat", variant="secondary")
                session_info = gr.Textbox(label="Current Session", value="No session selected", interactive=False, scale=2)

        # Right: Upload (session-scoped)
        with gr.Column(scale=1):
            gr.Markdown("### 📄 Upload Documents (Session-Scoped)")
            gr.Markdown("These PDFs will be available **only** to the currently selected session.")
            pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"], file_count="single")
            upload_btn = gr.Button("Upload to Current Session", variant="primary")
            upload_status = gr.Textbox(label="Upload Status", interactive=False, lines=7)

    # ── Wiring ────────────────────────────────────────────────────────────────
    session_dropdown.change(
        fn=on_session_change,
        inputs=[session_dropdown],
        outputs=[chatbot, session_info, status_text],
    )

    create_btn.click(
        fn=create_new_session,
        inputs=[new_session_name],
        outputs=[session_dropdown, chatbot, status_text],
    ).then(fn=lambda: "", outputs=[new_session_name])

    delete_btn.click(
        fn=delete_current_session,
        inputs=[session_dropdown],
        outputs=[session_dropdown, chatbot, status_text],
    )

    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot, session_dropdown],
        outputs=[msg_input, chatbot, status_text],
    )
    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot, session_dropdown],
        outputs=[msg_input, chatbot, status_text],
    )

    clear_history_btn.click(
        fn=clear_session_history,
        inputs=[session_dropdown],
        outputs=[chatbot, status_text],
    )

    refresh_btn.click(
        fn=refresh_sessions,
        inputs=[session_dropdown],
        outputs=[session_dropdown, chatbot, session_info, status_text],
    )

    # Important: pass session_id with upload
    upload_btn.click(
        fn=upload_pdf_file,
        inputs=[pdf_file, session_dropdown],
        outputs=[upload_status],
    )

    # Initial load: fill sessions and select first if present
    def _initial_load():
        choices = load_sessions()
        if choices:
            first = choices[0]
            return gr.update(choices=choices, value=first), load_chat_history(first), get_session_display_info(first)
        return gr.update(choices=[], value=None), [], "No sessions available – create one to start"

    app.load(fn=_initial_load, outputs=[session_dropdown, chatbot, session_info])


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print("Checking FastAPI server…")
        ping = requests.get(API_BASE_URL, timeout=5)
        if ping.status_code == 200:
            print("✅ FastAPI is up. Launching Gradio…")
            app.launch(server_name=config.GRADIO_HOST, server_port=config.GRADIO_PORT, share=False)
        else:
            print(f"⚠️ FastAPI responded with {ping.status_code}. Please ensure it's healthy.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server!")
        print("Start it first (e.g., `python run_servers.py`).")
    except Exception as e:
        print(f"❌ Error starting Gradio UI: {e}")
