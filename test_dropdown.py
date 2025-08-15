import gradio as gr
import requests
from config import config

# Test the dropdown component in isolation
API_BASE_URL = config.get_api_base_url()

def test_dropdown_basic():
    """Test if basic dropdown works"""
    return "Basic dropdown works!"

def test_server_connection():
    """Test server connection and session loading"""
    try:
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=5)
        if response.status_code == 200:
            result = response.json()
            sessions = result.get("sessions", [])
            
            if sessions:
                choices = [f"{s['display_name']} (msgs: {s['message_count']})" for s in sessions]
                return f"✅ Server connected. Found {len(sessions)} sessions", choices
            else:
                return "✅ Server connected. No sessions found", ["No sessions available"]
        else:
            return f"❌ Server error: {response.status_code}", ["Server error"]
    except Exception as e:
        return f"❌ Connection error: {str(e)}", ["Connection failed"]

def test_dropdown_selection(choice):
    """Test dropdown selection"""
    return f"Selected: '{choice}'"

# Minimal test interface
with gr.Blocks(title="Dropdown Test") as app:
    gr.Markdown("# 🔍 Dropdown Component Test")
    gr.Markdown("Testing if the dropdown component works at all")
    
    # Test 1: Basic functionality
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Test 1: Basic Dropdown")
            test_dropdown = gr.Dropdown(
                label="Test Dropdown",
                choices=["Option 1", "Option 2", "Option 3"],
                value="Option 1",
                interactive=True
            )
            test_btn = gr.Button("Test Basic Dropdown")
            test_output = gr.Textbox(label="Test Result")
    
    # Test 2: Server connection
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Test 2: Server Connection")
            server_btn = gr.Button("Test Server Connection")
            server_output = gr.Textbox(label="Server Result")
            session_dropdown = gr.Dropdown(
                label="Sessions from Server",
                choices=[],
                interactive=True
            )
    
    # Test 3: Selection handling
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Test 3: Selection Handling")
            selection_output = gr.Textbox(label="Selection Result")
    
    # Event handlers
    test_btn.click(
        fn=test_dropdown_basic,
        outputs=[test_output]
    )
    
    test_dropdown.change(
        fn=test_dropdown_selection,
        inputs=[test_dropdown],
        outputs=[selection_output]
    )
    
    def handle_server_test():
        message, choices = test_server_connection()
        return message, choices
    
    server_btn.click(
        fn=handle_server_test,
        outputs=[server_output, session_dropdown]
    )
    
    session_dropdown.change(
        fn=test_dropdown_selection,
        inputs=[session_dropdown],
        outputs=[selection_output]
    )

if __name__ == "__main__":
    print("🧪 Starting minimal dropdown test...")
    print("This will test if the dropdown component works at all")
    print(f"Server: {API_BASE_URL}")
    
    app.launch(
        server_name="127.0.0.1",
        server_port=7862,  # Different port
        share=False,
        debug=True
    )