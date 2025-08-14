"""
Test script for multi-session chat functionality
Run this after starting the FastAPI server to verify multi-session operations
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8000"

def test_multi_session():
    """Test multi-session chat functionality"""
    print("=" * 60)
    print("Testing Multi-Session Chat Functionality")
    print("=" * 60)
    
    # Test 1: List existing sessions
    print("\n1. Listing existing sessions...")
    response = requests.get(f"{API_BASE_URL}/list-sessions")
    sessions = response.json()["sessions"]
    print(f"   Found {len(sessions)} existing sessions")
    for s in sessions[:3]:  # Show first 3
        print(f"   - {s['session_id']} ({s['message_count']} messages)")
    
    # Test 2: Create first test session
    print("\n2. Creating first test session...")
    payload = {"session_name": "test_project"}
    response = requests.post(f"{API_BASE_URL}/create-session", json=payload)
    session1 = response.json()
    session1_id = session1["session_id"]
    print(f"   Created: {session1_id}")
    
    # Test 3: Create second test session
    print("\n3. Creating second test session...")
    payload = {"session_name": "test_research"}
    response = requests.post(f"{API_BASE_URL}/create-session", json=payload)
    session2 = response.json()
    session2_id = session2["session_id"]
    print(f"   Created: {session2_id}")
    
    # Test 4: Send messages to first session
    print(f"\n4. Sending messages to session 1 ({session1_id})...")
    messages_session1 = [
        "Hello! I'm working on a project.",
        "Can you help me understand RAG systems?",
        "What are embeddings?"
    ]
    
    for msg in messages_session1:
        payload = {"message": msg, "session_id": session1_id}
        response = requests.post(f"{API_BASE_URL}/chat", json=payload)
        print(f"   Sent: {msg[:40]}...")
        time.sleep(0.5)
    
    # Test 5: Send messages to second session
    print(f"\n5. Sending messages to session 2 ({session2_id})...")
    messages_session2 = [
        "I need help with research.",
        "What's the capital of Japan?",
        "Tell me about machine learning."
    ]
    
    for msg in messages_session2:
        payload = {"message": msg, "session_id": session2_id}
        response = requests.post(f"{API_BASE_URL}/chat", json=payload)
        print(f"   Sent: {msg[:40]}...")
        time.sleep(0.5)
    
    # Test 6: Verify sessions have different histories
    print("\n6. Verifying sessions have separate histories...")
    
    # Get history for session 1
    response = requests.get(f"{API_BASE_URL}/chat-history/{session1_id}")
    history1 = response.json()["chat_history"]
    print(f"   Session 1 has {len(history1)} exchanges")
    
    # Get history for session 2
    response = requests.get(f"{API_BASE_URL}/chat-history/{session2_id}")
    history2 = response.json()["chat_history"]
    print(f"   Session 2 has {len(history2)} exchanges")
    
    # Test 7: Test context awareness - ask about previous messages
    print("\n7. Testing context awareness...")
    
    # Ask session 1 about its context
    payload = {"message": "What was the first thing I asked you about?", "session_id": session1_id}
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Session 1 response: {result['response'][:100]}...")
    
    # Ask session 2 about its context
    payload = {"message": "What was the first thing I asked you about?", "session_id": session2_id}
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Session 2 response: {result['response'][:100]}...")
    
    # Test 8: Get session info
    print("\n8. Getting session information...")
    response = requests.get(f"{API_BASE_URL}/session-info/{session1_id}")
    info = response.json()
    print(f"   Session 1 info:")
    print(f"   - Display name: {info['display_name']}")
    print(f"   - Message count: {info['message_count']}")
    print(f"   - Last updated: {info['last_updated'][:19]}")
    
    # Test 9: Clear history for one session
    print(f"\n9. Clearing history for session 1...")
    response = requests.delete(f"{API_BASE_URL}/chat-history/{session1_id}")
    print(f"   Status: {response.json()['message']}")
    
    # Verify it's cleared
    response = requests.get(f"{API_BASE_URL}/chat-history/{session1_id}")
    history1_after = response.json()["chat_history"]
    print(f"   Session 1 now has {len(history1_after)} exchanges")
    
    # Verify session 2 still has its history
    response = requests.get(f"{API_BASE_URL}/chat-history/{session2_id}")
    history2_after = response.json()["chat_history"]
    print(f"   Session 2 still has {len(history2_after)} exchanges")
    
    # Test 10: Delete a session
    print(f"\n10. Deleting session 2...")
    response = requests.delete(f"{API_BASE_URL}/delete-session/{session2_id}")
    print(f"   Status: {response.json()['message']}")
    
    # Verify it's deleted
    response = requests.get(f"{API_BASE_URL}/list-sessions")
    sessions_after = response.json()["sessions"]
    session2_exists = any(s["session_id"] == session2_id for s in sessions_after)
    print(f"   Session 2 exists: {session2_exists}")
    
    # Test 11: Create session with duplicate name (should get different ID)
    print("\n11. Testing duplicate name handling...")
    payload = {"session_name": "test_project"}
    response = requests.post(f"{API_BASE_URL}/create-session", json=payload)
    duplicate_session = response.json()
    duplicate_id = duplicate_session["session_id"]
    print(f"   Original: {session1_id}")
    print(f"   Duplicate name got: {duplicate_id}")
    print(f"   Different IDs: {session1_id != duplicate_id}")
    
    # Clean up - delete test sessions
    print("\n12. Cleaning up test sessions...")
    for session_id in [session1_id, duplicate_id]:
        try:
            response = requests.delete(f"{API_BASE_URL}/delete-session/{session_id}")
            print(f"   Deleted: {session_id}")
        except:
            pass
    
    print("\n" + "=" * 60)
    print("✅ Multi-Session Tests Complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(API_BASE_URL)
        if response.status_code == 200:
            test_multi_session()
        else:
            print("❌ Server not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server")
        print("Please start the server first: python run_servers.py")