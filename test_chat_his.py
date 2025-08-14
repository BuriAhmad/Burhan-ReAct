"""
Test script for chat history functionality (updated for multi-session)
Run this after starting the FastAPI server to verify chat history operations
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8000"

def test_chat_history():
    """Test chat history functionality with multi-session support"""
    print("=" * 50)
    print("Testing Chat History Functionality (Multi-Session)")
    print("=" * 50)
    
    # First, create a test session
    print("\n0. Creating test session for chat history tests...")
    payload = {"session_name": "test_history"}
    response = requests.post(f"{API_BASE_URL}/create-session", json=payload)
    if response.status_code != 200:
        print(f"   Failed to create session: {response.json()}")
        return
    
    session_data = response.json()
    test_session_id = session_data["session_id"]
    print(f"   Created session: {test_session_id}")
    
    # Test 1: Clear any existing history for this new session
    print(f"\n1. Clearing history for session {test_session_id}...")
    response = requests.delete(f"{API_BASE_URL}/chat-history/{test_session_id}")
    print(f"   Status: {response.json()}")
    
    # Test 2: Send first message
    print("\n2. Sending first message...")
    payload = {
        "message": "Hello! What's your name?",
        "session_id": test_session_id
    }
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    if response.status_code != 200:
        print(f"   Error: {response.status_code} - {response.json()}")
        return
    
    result = response.json()
    print(f"   Response: {result['response'][:100]}...")
    print(f"   History count: {len(result['chat_history'])}")
    
    time.sleep(1)
    
    # Test 3: Send second message with context
    print("\n3. Sending second message (should remember context)...")
    payload = {
        "message": "Can you remind me what I just asked you?",
        "session_id": test_session_id
    }
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Response: {result['response'][:100]}...")
    print(f"   History count: {len(result['chat_history'])}")
    
    time.sleep(1)
    
    # Test 4: Retrieve chat history
    print(f"\n4. Retrieving chat history for session {test_session_id}...")
    response = requests.get(f"{API_BASE_URL}/chat-history/{test_session_id}")
    result = response.json()
    print(f"   Total exchanges: {len(result['chat_history'])}")
    for i, (user_msg, bot_msg) in enumerate(result['chat_history'], 1):
        print(f"   Exchange {i}:")
        print(f"      User: {user_msg[:50]}...")
        print(f"      Bot: {bot_msg[:50]}...")
    
    # Test 5: Send multiple messages to test 5-message limit
    print("\n5. Testing context limit (sending 5 more messages)...")
    test_messages = [
        "What is 2+2?",
        "What's the capital of France?",
        "Tell me a fun fact",
        "What's the weather like?",
        "How are you today?"
    ]
    
    for msg in test_messages:
        payload = {
            "message": msg,
            "session_id": test_session_id
        }
        response = requests.post(f"{API_BASE_URL}/chat", json=payload)
        print(f"   Sent: {msg}")
        time.sleep(0.5)
    
    # Test 6: Verify context includes only last 5
    print("\n6. Sending message to test context window...")
    payload = {
        "message": "What were the last few things we discussed?",
        "session_id": test_session_id
    }
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Response: {result['response'][:200]}...")
    print(f"   Total history: {len(result['chat_history'])} exchanges")
    
    # Test 7: Clear history
    print(f"\n7. Clearing chat history for session {test_session_id}...")
    response = requests.delete(f"{API_BASE_URL}/chat-history/{test_session_id}")
    print(f"   Status: {response.json()}")
    
    # Test 8: Verify history is cleared
    print("\n8. Verifying history is cleared...")
    response = requests.get(f"{API_BASE_URL}/chat-history/{test_session_id}")
    result = response.json()
    print(f"   History after clear: {len(result['chat_history'])} exchanges")
    
    # Test 9: Test with different session
    print("\n9. Creating and testing a second session...")
    payload = {"session_name": "test_second"}
    response = requests.post(f"{API_BASE_URL}/create-session", json=payload)
    second_session = response.json()
    second_session_id = second_session["session_id"]
    print(f"   Created second session: {second_session_id}")
    
    # Send message to second session
    payload = {
        "message": "This is a different session",
        "session_id": second_session_id
    }
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    print(f"   Sent message to second session")
    
    # Verify sessions are independent
    response1 = requests.get(f"{API_BASE_URL}/chat-history/{test_session_id}")
    response2 = requests.get(f"{API_BASE_URL}/chat-history/{second_session_id}")
    
    history1 = len(response1.json()["chat_history"])
    history2 = len(response2.json()["chat_history"])
    
    print(f"   Session 1 history: {history1} exchanges")
    print(f"   Session 2 history: {history2} exchanges")
    print(f"   Sessions are independent: {history1 != history2}")
    
    # Test 10: Clean up test sessions
    print("\n10. Cleaning up test sessions...")
    for sid in [test_session_id, second_session_id]:
        response = requests.delete(f"{API_BASE_URL}/delete-session/{sid}")
        if response.status_code == 200:
            print(f"   Deleted: {sid}")
    
    print("\n" + "=" * 50)
    print("✅ Chat History Tests Complete (Multi-Session)!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(API_BASE_URL)
        if response.status_code == 200:
            test_chat_history()
        else:
            print("❌ Server not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server")
        print("Please start the server first: python run_servers.py")