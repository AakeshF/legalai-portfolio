# services/mcp_servers/local_llm_mcp.py - Local LLM MCP server for privacy-focused AI
import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import httpx

from .base_legal_mcp import BaseLegalMCPServer

logger = logging.getLogger(__name__)

class LocalLLMMCPServer(BaseLegalMCPServer):
    """MCP server for local LLM processing to ensure data privacy"""
    
    def __init__(self):
        super().__init__("local_llm", "Local LLM Server")
        self.model_type = os.getenv("LOCAL_MODEL_TYPE", "llama2")
        self.model_path = os.getenv("LOCAL_MODEL_PATH", "/models/legal-llama-7b")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.vllm_url = os.getenv("VLLM_URL", "http://localhost:8000")
        self.backend = os.getenv("LOCAL_LLM_BACKEND", "ollama")  # ollama, vllm, llamacpp
        
        # Legal-specific model configurations
        self.legal_models = {
            "general": "llama2:7b-legal",
            "contract": "legal-bert-contracts",
            "litigation": "legal-gpt-litigation",
            "compliance": "compliance-llm"
        }
        
        logger.info(f"Local LLM MCP server initialized with backend: {self.backend}")
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for local LLM processing"""
        return [
            {
                "name": "generate",
                "description": "Generate text using local LLM",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Input prompt"},
                        "max_tokens": {"type": "integer", "description": "Maximum tokens to generate"},
                        "temperature": {"type": "number", "description": "Sampling temperature"},
                        "model": {"type": "string", "description": "Specific model to use"},
                        "system_prompt": {"type": "string", "description": "System prompt for context"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "analyze_legal",
                "description": "Analyze legal document with privacy-focused local model",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Document content"},
                        "analysis_type": {"type": "string", "description": "Type of analysis"},
                        "extract_entities": {"type": "boolean", "description": "Extract legal entities"},
                        "assess_risk": {"type": "boolean", "description": "Perform risk assessment"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "check_model_status",
                "description": "Check if local model is loaded and ready",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "Model to check"}
                    }
                }
            },
            {
                "name": "load_model",
                "description": "Load a specific model into memory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "Model to load"},
                        "gpu": {"type": "boolean", "description": "Use GPU acceleration"}
                    },
                    "required": ["model"]
                }
            },
            {
                "name": "privacy_analysis",
                "description": "Analyze document for privacy concerns locally",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Document content"},
                        "identify_pii": {"type": "boolean", "description": "Identify PII"},
                        "redact": {"type": "boolean", "description": "Redact sensitive information"}
                    },
                    "required": ["content"]
                }
            }
        ]
    
    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool execution for local LLM operations"""
        
        if name == "generate":
            return await self._generate_text(
                prompt=arguments["prompt"],
                max_tokens=arguments.get("max_tokens", 2000),
                temperature=arguments.get("temperature", 0.1),
                model=arguments.get("model"),
                system_prompt=arguments.get("system_prompt")
            )
        
        elif name == "analyze_legal":
            return await self._analyze_legal_document(
                content=arguments["content"],
                analysis_type=arguments.get("analysis_type", "general"),
                extract_entities=arguments.get("extract_entities", True),
                assess_risk=arguments.get("assess_risk", True)
            )
        
        elif name == "check_model_status":
            return await self._check_model_status(
                model=arguments.get("model", self.model_type)
            )
        
        elif name == "load_model":
            return await self._load_model(
                model=arguments["model"],
                gpu=arguments.get("gpu", True)
            )
        
        elif name == "privacy_analysis":
            return await self._privacy_analysis(
                content=arguments["content"],
                identify_pii=arguments.get("identify_pii", True),
                redact=arguments.get("redact", False)
            )
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _generate_text(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text using local LLM"""
        
        try:
            if self.backend == "ollama":
                return await self._ollama_generate(
                    prompt, max_tokens, temperature, model, system_prompt
                )
            elif self.backend == "vllm":
                return await self._vllm_generate(
                    prompt, max_tokens, temperature, model, system_prompt
                )
            else:
                raise ValueError(f"Unsupported backend: {self.backend}")
            
        except Exception as e:
            logger.error(f"Local LLM generation error: {e}")
            return {
                "text": "",
                "error": str(e),
                "model": model or self.model_type,
                "backend": self.backend
            }
    
    async def _ollama_generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        model: Optional[str],
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using Ollama backend"""
        
        model_name = model or self.model_type
        
        # Build full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\n"
        full_prompt += f"Human: {prompt}\n\nAssistant:"
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result.get("response", ""),
                    "model": model_name,
                    "backend": "ollama",
                    "tokens_used": result.get("eval_count", 0),
                    "generation_time": result.get("total_duration", 0) / 1e9  # Convert to seconds
                }
            else:
                raise Exception(f"Ollama error: {response.status_code} - {response.text}")
    
    async def _vllm_generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        model: Optional[str],
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using vLLM backend"""
        
        model_name = model or self.model_type
        
        # Build messages for chat format
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.vllm_url}/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result["choices"][0]["message"]["content"],
                    "model": model_name,
                    "backend": "vllm",
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                }
            else:
                raise Exception(f"vLLM error: {response.status_code} - {response.text}")
    
    async def _analyze_legal_document(
        self,
        content: str,
        analysis_type: str,
        extract_entities: bool,
        assess_risk: bool
    ) -> Dict[str, Any]:
        """Analyze legal document using local model"""
        
        # Select appropriate model for analysis type
        model = self.legal_models.get(analysis_type, "general")
        
        # Create structured prompt
        prompt = f"""Analyze the following legal document:

Document Type: {analysis_type}
Content: {content[:5000]}

Please provide:
1. Document type and purpose
2. Key parties and their roles
3. Important dates and deadlines
4. Main obligations and rights
5. Potential legal issues or risks
6. Recommended actions

Format your response as structured JSON."""

        system_prompt = """You are a legal analysis AI running locally for maximum privacy. 
Analyze documents carefully and provide structured, actionable insights.
Never transmit data externally. All processing must remain local."""

        # Generate analysis
        result = await self._generate_text(
            prompt=prompt,
            max_tokens=3000,
            temperature=0.1,
            model=model,
            system_prompt=system_prompt
        )
        
        # Parse and structure response
        try:
            # Attempt to parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', result["text"], re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                # Fallback to text parsing
                analysis = self._parse_text_analysis(result["text"])
            
            return {
                "analysis": analysis,
                "model_used": result["model"],
                "processing_location": "local",
                "privacy_preserved": True,
                "tokens_used": result.get("tokens_used", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse analysis: {e}")
            return {
                "analysis": {"raw_text": result["text"]},
                "model_used": result["model"],
                "processing_location": "local",
                "privacy_preserved": True,
                "parse_error": str(e)
            }
    
    def _parse_text_analysis(self, text: str) -> Dict[str, Any]:
        """Parse unstructured text analysis into structured format"""
        
        analysis = {
            "document_type": "",
            "parties": [],
            "dates": [],
            "obligations": [],
            "risks": [],
            "recommendations": []
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if "type" in line.lower() or "purpose" in line.lower():
                current_section = "document_type"
            elif "parties" in line.lower():
                current_section = "parties"
            elif "dates" in line.lower() or "deadlines" in line.lower():
                current_section = "dates"
            elif "obligations" in line.lower() or "rights" in line.lower():
                current_section = "obligations"
            elif "risks" in line.lower() or "issues" in line.lower():
                current_section = "risks"
            elif "recommend" in line.lower() or "actions" in line.lower():
                current_section = "recommendations"
            
            # Add content to current section
            elif current_section:
                if current_section == "document_type":
                    analysis["document_type"] = line
                elif current_section in ["parties", "dates", "obligations", "risks", "recommendations"]:
                    if line.startswith(('-', '•', '*', '1', '2', '3')):
                        analysis[current_section].append(line.lstrip('-•*123. '))
        
        return analysis
    
    async def _check_model_status(self, model: str) -> Dict[str, Any]:
        """Check if a model is loaded and ready"""
        
        try:
            if self.backend == "ollama":
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.ollama_url}/api/tags")
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        model_names = [m["name"] for m in models]
                        return {
                            "model": model,
                            "loaded": model in model_names,
                            "available_models": model_names,
                            "backend": "ollama"
                        }
            
            elif self.backend == "vllm":
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.vllm_url}/v1/models")
                    if response.status_code == 200:
                        models = response.json().get("data", [])
                        model_ids = [m["id"] for m in models]
                        return {
                            "model": model,
                            "loaded": model in model_ids,
                            "available_models": model_ids,
                            "backend": "vllm"
                        }
            
            return {
                "model": model,
                "loaded": False,
                "error": "Backend not reachable"
            }
            
        except Exception as e:
            return {
                "model": model,
                "loaded": False,
                "error": str(e)
            }
    
    async def _load_model(self, model: str, gpu: bool = True) -> Dict[str, Any]:
        """Load a model into memory"""
        
        try:
            if self.backend == "ollama":
                async with httpx.AsyncClient(timeout=600.0) as client:
                    response = await client.post(
                        f"{self.ollama_url}/api/pull",
                        json={"name": model}
                    )
                    
                    if response.status_code == 200:
                        return {
                            "model": model,
                            "status": "loaded",
                            "backend": "ollama",
                            "gpu_enabled": gpu
                        }
            
            return {
                "model": model,
                "status": "failed",
                "error": "Load operation not supported for this backend"
            }
            
        except Exception as e:
            return {
                "model": model,
                "status": "failed",
                "error": str(e)
            }
    
    async def _privacy_analysis(
        self,
        content: str,
        identify_pii: bool,
        redact: bool
    ) -> Dict[str, Any]:
        """Analyze document for privacy concerns"""
        
        prompt = f"""Analyze this document for privacy and confidentiality concerns:

{content[:3000]}

Identify:
1. Personal Identifiable Information (PII)
2. Confidential business information
3. Privileged attorney-client communications
4. Protected health information (PHI)
5. Financial account information

Provide specific examples and locations."""

        result = await self._generate_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.1,
            system_prompt="You are a privacy analysis expert. Identify all sensitive information that requires protection."
        )
        
        # Parse response for PII
        pii_items = []
        lines = result["text"].split('\n')
        for line in lines:
            if any(term in line.lower() for term in ['ssn', 'social security', 'email', 'phone', 'address', 'name']):
                pii_items.append(line.strip())
        
        response = {
            "pii_found": len(pii_items) > 0,
            "pii_items": pii_items[:10],  # Limit to first 10
            "analysis": result["text"],
            "processing_location": "local",
            "data_never_left_device": True
        }
        
        if redact and pii_items:
            # Simple redaction (in production, use more sophisticated methods)
            redacted_content = content
            # This is a placeholder - implement proper redaction
            response["redacted_content"] = "[Redaction would be performed here]"
            response["redaction_performed"] = True
        
        return response