#!/usr/bin/env python3
"""Test RAG API endpoints"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_TOKEN = None  # Don't send auth header when DISABLE_AUTH is true

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_api_endpoints():
    """Test the new RAG API endpoints"""
    
    # Test 1: Semantic Search endpoint
    print("\n📍 Testing POST /api/documents/semantic-search")
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}
    
    search_data = {
        "query": "termination clauses",
        "top_k": 5
    }
    
    response = requests.post(
        f"{BASE_URL}/api/documents/semantic-search",
        json=search_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"Found {len(results.get('results', []))} results")
        print("✅ Semantic search endpoint working")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 2: RAG Chat endpoint
    print("\n📍 Testing POST /api/chat/rag")
    
    chat_data = {
        "message": "What are the key risks in our contracts?",
        "use_context": True
    }
    
    response = requests.post(
        f"{BASE_URL}/api/chat/rag",
        json=chat_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response', '')[:200]}...")
        print("✅ RAG chat endpoint working")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 3: Similar Documents endpoint
    print("\n📍 Testing POST /api/documents/{document_id}/similar")
    
    # This would need a real document ID, so we'll skip for now
    print("⚠️  Skipping similar documents test (needs document ID)")

if __name__ == "__main__":
    print("🔍 Testing Legal AI RAG Endpoints")
    print("=" * 50)
    
    # Check if server is running
    try:
        if test_health():
            print("✅ Server is running")
            test_api_endpoints()
        else:
            print("❌ Server health check failed")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server at", BASE_URL)
        print("Please ensure the server is running: python3 start.py")
        sys.exit(1)