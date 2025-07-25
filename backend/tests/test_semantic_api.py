#!/usr/bin/env python3
"""Test semantic search API directly without auth dependencies"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_semantic_search():
    """Test semantic search endpoint"""
    print("🔍 Testing Semantic Search API")
    print("=" * 50)

    # Test semantic search endpoint
    search_data = {"query": "termination clauses in contracts", "top_k": 5}

    response = requests.post(
        f"{BASE_URL}/api/documents/semantic-search", json=search_data
    )

    print(f"\n📍 POST /api/documents/semantic-search")
    print(f"Request: {json.dumps(search_data, indent=2)}")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Results: {json.dumps(result, indent=2)}")
    else:
        print(f"Error: {response.text}")

    # Test RAG chat endpoint
    print("\n📍 POST /api/chat/rag")

    chat_data = {
        "message": "What are the key risks in contract termination?",
        "use_context": True,
    }

    response = requests.post(f"{BASE_URL}/api/chat/rag", json=chat_data)

    print(f"Request: {json.dumps(chat_data, indent=2)}")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response', '')[:200]}...")
        if result.get("sources"):
            print(f"Sources: {len(result.get('sources', []))} documents")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_semantic_search()
