# services/local_ai_service.py - Wrapper to use Ollama service as primary AI
from services.ollama_service import OllamaService

# Create a global instance that can be imported
local_ai_service = OllamaService()

# For backward compatibility, export the service class as AIService
AIService = OllamaService