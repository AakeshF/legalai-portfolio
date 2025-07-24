import asyncio
import httpx
from services.ollama_service import OllamaService

async def test_ollama():
    """Test Ollama directly"""
    try:
        # Initialize Ollama service
        ollama = OllamaService()
        print(f"✅ Ollama initialized with model: {ollama.model}")
        print(f"   Base URL: {ollama.base_url}")
        
        # Test generation using the correct method
        print("\n🔄 Testing Ollama generation...")
        response = await ollama.process_chat_message(
            message="Hello, can you help me with legal documents?",
            documents=[],
            chat_history=[]
        )
        print(f"\n🤖 Ollama Response: {response['answer'][:200]}...")
        print(f"   Response Type: {response.get('response_metrics', {}).get('response_type', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_ollama())
