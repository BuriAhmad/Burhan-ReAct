"""
Diagnostic script to identify dropdown issues
Run this to check what's happening with your sessions and dropdown data
"""

import requests
import json
from config import config
import sys

API_BASE_URL = config.get_api_base_url()

def check_server_status():
    """Check if the FastAPI server is running and responsive"""
    print("=" * 50)
    print("🔍 CHECKING SERVER STATUS")
    print("=" * 50)
    
    try:
        print(f"Testing connection to: {API_BASE_URL}")
        response = requests.get(API_BASE_URL, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Server is running")
            print(f"   Message: {result.get('message', 'N/A')}")
            print(f"   Status: {result.get('status', 'N/A')}")
            
            # Check configuration
            config_info = result.get('configuration', {})
            print(f"   Database: {config_info.get('database', 'N/A')}")
            print(f"   MongoDB: {config_info.get('mongodb_status', 'N/A')}")
            
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {API_BASE_URL}")
        print("   Make sure the FastAPI server is running with: python run_servers.py")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False

def check_sessions_endpoint():
    """Check the sessions endpoint and data format"""
    print("\n" + "=" * 50)
    print("🔍 CHECKING SESSIONS ENDPOINT")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        
        print(f"Endpoint: GET {API_BASE_URL}/list-sessions")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ Valid JSON response")
                
                sessions = result.get("sessions", [])
                print(f"✅ Found {len(sessions)} sessions")
                
                if sessions:
                    print("\n📋 Session Data:")
                    for i, session in enumerate(sessions, 1):
                        print(f"   Session {i}:")
                        print(f"     ID: {session.get('session_id', 'MISSING')}")
                        print(f"     Display Name: {session.get('display_name', 'MISSING')}")
                        print(f"     Message Count: {session.get('message_count', 'MISSING')}")
                        print(f"     Last Updated: {session.get('last_updated', 'MISSING')}")
                        
                        # Test what dropdown choices would look like
                        session_id = session.get('session_id', '')
                        display_name = session.get('display_name', '')
                        message_count = session.get('message_count', 0)
                        
                        choice = f"{display_name} ({message_count} msgs)"
                        print(f"     Dropdown Choice: '{choice}'")
                        print(f"     Maps to ID: '{session_id}'")
                else:
                    print("ℹ️  No sessions found")
                    print("   This means the dropdown will be empty")
                    print("   Try creating a session first")
                
                return True
                
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
                print(f"   Raw response: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Error response: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error detail: {error_detail}")
            except:
                print(f"   Raw response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Exception checking sessions: {e}")
        return False

def simulate_dropdown_creation():
    """Simulate how the dropdown choices would be created"""
    print("\n" + "=" * 50)
    print("🔍 SIMULATING DROPDOWN CREATION")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            sessions = result.get("sessions", [])
            
            print(f"Input: {len(sessions)} sessions from API")
            
            if not sessions:
                print("⚠️  No sessions available")
                print("   Dropdown choices: []")
                print("   Session map: {}")
                return
            
            # Simulate dropdown creation logic
            choices = []
            session_map = {}
            
            print("\n🔧 Creating dropdown choices:")
            for i, session in enumerate(sessions, 1):
                session_id = session.get('session_id', f'missing_id_{i}')
                display_name = session.get('display_name', f'missing_name_{i}')
                message_count = session.get('message_count', 0)
                
                # Create choice text
                choice = f"{display_name} ({message_count} msgs)"
                choices.append(choice)
                session_map[choice] = session_id
                
                print(f"   {i}. '{choice}' -> '{session_id}'")
            
            print(f"\n📋 Final Results:")
            print(f"   Choices list: {choices}")
            print(f"   Session map: {session_map}")
            print(f"   Choices count: {len(choices)}")
            print(f"   Map count: {len(session_map)}")
            
            # Test first selection
            if choices:
                first_choice = choices[0]
                mapped_id = session_map.get(first_choice)
                print(f"\n🎯 First choice test:")
                print(f"   First choice: '{first_choice}'")
                print(f"   Maps to ID: '{mapped_id}'")
                print(f"   Mapping successful: {mapped_id is not None}")
        else:
            print(f"❌ Cannot get sessions (status {response.status_code})")
            
    except Exception as e:
        print(f"❌ Exception in simulation: {e}")

def test_session_history():
    """Test loading history for a session"""
    print("\n" + "=" * 50)
    print("🔍 TESTING SESSION HISTORY LOADING")
    print("=" * 50)
    
    try:
        # Get sessions first
        response = requests.get(f"{API_BASE_URL}/list-sessions", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            sessions = result.get("sessions", [])
            
            if sessions:
                # Test with first session
                first_session = sessions[0]
                session_id = first_session.get('session_id')
                
                print(f"Testing history for session: {session_id}")
                
                history_response = requests.get(f"{API_BASE_URL}/chat-history/{session_id}", timeout=10)
                
                if history_response.status_code == 200:
                    history_result = history_response.json()
                    chat_history = history_result.get("chat_history", [])
                    
                    print(f"✅ History loaded successfully")
                    print(f"   Message exchanges: {len(chat_history)}")
                    
                    if chat_history:
                        print(f"   Sample exchange:")
                        first_exchange = chat_history[0]
                        if len(first_exchange) >= 2:
                            print(f"     User: {first_exchange[0][:60]}...")
                            print(f"     Assistant: {first_exchange[1][:60]}...")
                    else:
                        print(f"   (No messages in this session)")
                else:
                    print(f"❌ Failed to load history: {history_response.status_code}")
            else:
                print("ℹ️  No sessions to test history with")
        else:
            print(f"❌ Cannot get sessions for history test")
            
    except Exception as e:
        print(f"❌ Exception testing history: {e}")

def check_gradio_environment():
    """Check if Gradio environment might be causing issues"""
    print("\n" + "=" * 50)
    print("🔍 CHECKING GRADIO ENVIRONMENT")
    print("=" * 50)
    
    try:
        import gradio as gr
        print(f"✅ Gradio version: {gr.__version__}")
        
        # Test basic dropdown creation
        try:
            test_choices = ["Test 1", "Test 2", "Test 3"]
            test_dropdown = gr.Dropdown(choices=test_choices, value="Test 1")
            print("✅ Basic dropdown creation works")
        except Exception as e:
            print(f"❌ Basic dropdown creation failed: {e}")
        
        # Check for common issues
        print("\n🔧 Environment checks:")
        print(f"   Python version: {sys.version}")
        
        # Check for conflicting packages
        try:
            import requests
            print(f"   Requests version: {requests.__version__}")
        except:
            print("   ❌ Requests not available")
        
    except ImportError:
        print("❌ Gradio not installed or importable")
    except Exception as e:
        print(f"❌ Error checking Gradio: {e}")

def main():
    """Run all diagnostic tests"""
    print("🔍 DROPDOWN DIAGNOSTIC TOOL")
    print("This will help identify why the dropdown is not working")
    
    # Run all checks
    server_ok = check_server_status()
    
    if server_ok:
        sessions_ok = check_sessions_endpoint()
        simulate_dropdown_creation()
        test_session_history()
    else:
        print("\n⚠️  Skipping other tests due to server connection issues")
        print("   Start the server with: python run_servers.py")
    
    check_gradio_environment()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS SUMMARY")
    print("=" * 50)
    
    if not server_ok:
        print("❌ PRIMARY ISSUE: Server not running or not accessible")
        print("   SOLUTION: Start the FastAPI server")
    else:
        print("✅ Server is accessible")
        print("\nIf the dropdown still doesn't work:")
        print("1. Try the minimal test: python test_dropdown_minimal.py")
        print("2. Try the debug UI: python gradio_ui_simple_fix.py")
        print("3. Check browser console for JavaScript errors")
        print("4. Try a different browser")
    
    print(f"\nNext steps:")
    print("1. Fix any issues shown above")
    print("2. Run: python test_dropdown_minimal.py")
    print("3. Run: python gradio_ui_simple_fix.py")

if __name__ == "__main__":
    try:
        config.validate_required_keys()
        main()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)