"""
Test script for chat history functionality
Run this after starting the FastAPI server to verify chat history operations
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8000"

def test_chat_history():
    """Test chat history functionality"""
    print("=" * 50)
    print("Testing Chat History Functionality")
    print("=" * 50)
    
    # Test 1: Clear any existing history
    print("\n1. Clearing existing chat history...")
    response = requests.delete(f"{API_BASE_URL}/chat-history")
    print(f"   Status: {response.json()}")
    
    # Test 2: Send first message
    print("\n2. Sending first message...")
    payload = {"message": "Hello! What's your name?"}
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Response: {result['response'][:100]}...")
    print(f"   History count: {len(result['chat_history'])}")
    
    time.sleep(1)
    
    # Test 3: Send second message with context
    print("\n3. Sending second message (should remember context)...")
    payload = {"message": "Can you remind me what I just asked you?"}
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Response: {result['response'][:100]}...")
    print(f"   History count: {len(result['chat_history'])}")
    
    time.sleep(1)
    
    # Test 4: Retrieve chat history
    print("\n4. Retrieving chat history...")
    response = requests.get(f"{API_BASE_URL}/chat-history")
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
        payload = {"message": msg}
        response = requests.post(f"{API_BASE_URL}/chat", json=payload)
        print(f"   Sent: {msg}")
        time.sleep(0.5)
    
    # Test 6: Verify context includes only last 5
    print("\n6. Sending message to test context window...")
    payload = {"message": "What were the last few things we discussed?"}
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    result = response.json()
    print(f"   Response: {result['response'][:200]}...")
    print(f"   Total history: {len(result['chat_history'])} exchanges")
    
    # Test 7: Clear history
    print("\n7. Clearing chat history...")
    response = requests.delete(f"{API_BASE_URL}/chat-history")
    print(f"   Status: {response.json()}")
    
    # Test 8: Verify history is cleared
    print("\n8. Verifying history is cleared...")
    response = requests.get(f"{API_BASE_URL}/chat-history")
    result = response.json()
    print(f"   History after clear: {len(result['chat_history'])} exchanges")
    
    print("\n" + "=" * 50)
    print("✅ Chat History Tests Complete!")
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