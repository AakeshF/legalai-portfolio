# services/ollama_service.py - Local Ollama AI service for legal document analysis
import httpx
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from config import settings

class LegalDocumentType(Enum):
    """Types of legal documents for specialized analysis"""
    CONTRACT = "contract"
    IMMIGRATION_FORM = "immigration_form"
    FAMILY_LAW = "family_law"
    CRIMINAL_DEFENSE = "criminal_defense"
    PERSONAL_INJURY = "personal_injury"
    GENERAL = "general"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class OllamaService:
    """Local AI service using Ollama for privacy-first legal document analysis"""
    
    def __init__(self):
        # Ollama runs locally on port 11434 by default
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model  # Use model from settings
        
        # Check if Ollama is running
        self.is_available = self._check_ollama_availability()
        self.demo_mode = not self.is_available  # Set demo mode if Ollama is not available
        
        if self.is_available:
            print(f"✅ Ollama service initialized with model: {self.model}")
        else:
            print("❌ Ollama service not available. Please ensure Ollama is running.")
        
        # Legal-specific prompts (same as before)
        self.system_prompts = {
            "legal_assistant": """You are a professional legal AI assistant designed to help attorneys analyze documents and provide legal insights. 

Your responsibilities:
- Analyze legal documents with precision and attention to detail
- Identify key legal issues, dates, parties, and obligations
- Provide clear, actionable insights for legal professionals
- Cite specific sections of documents when making points
- Flag potential legal risks or compliance issues
- Extract critical information in structured formats
- Identify missing elements or clauses
- Maintain attorney-client privilege and confidentiality

Always provide thorough, professional responses that would be valuable to an experienced attorney.""",
            
            "document_analysis": """Analyze this legal document and provide:
1. Document type and purpose
2. Key parties involved (full names, roles, addresses if available)
3. Important dates and deadlines (with specific dates)
4. Main legal obligations and rights
5. Potential issues or red flags
6. Missing standard clauses or protections
7. Action items for the attorney
8. Risk assessment (low/medium/high/critical)

Be specific and cite relevant sections. Format dates as MM/DD/YYYY.""",
            
            "contract_review": """Review this contract for:
1. Unfavorable terms or unusual clauses
2. Missing standard protections (indemnification, limitation of liability, etc.)
3. Ambiguous language that could cause disputes
4. Compliance issues
5. Payment terms and penalties
6. Termination conditions
7. Intellectual property concerns
8. Recommended modifications

Provide specific clause references and actionable recommendations.""",
            
            "immigration_analysis": """Analyze this immigration document for:
1. Form type and purpose (I-130, I-485, etc.)
2. Applicant and beneficiary information
3. Critical deadlines and priority dates
4. Required supporting documents
5. Potential issues or grounds for denial
6. Missing information or inconsistencies
7. Next steps in the process

Flag any potential red flags that could affect case approval.""",
            
            "family_law_analysis": """Review this family law document for:
1. Type of proceeding (divorce, custody, support, etc.)
2. Parties and their representation
3. Key dates and deadlines
4. Financial obligations and asset division
5. Custody and visitation arrangements
6. Support calculations and modifications
7. Potential areas of dispute
8. Compliance with local rules

Note: Focus on adult parties only.""",
            
            "criminal_defense_analysis": """Analyze this criminal case document for:
1. Charges and potential penalties
2. Key evidence mentioned
3. Constitutional issues
4. Procedural requirements and deadlines
5. Potential defenses
6. Plea options discussed
7. Sentencing considerations
8. Appeal grounds

Identify any violations of defendant's rights.""",
            
            "personal_injury_analysis": """Review this personal injury document for:
1. Type of injury and circumstances
2. Liable parties identified
3. Damages claimed (economic and non-economic)
4. Medical evidence referenced
5. Statute of limitations concerns
6. Insurance coverage issues
7. Settlement discussions
8. Litigation timeline

Calculate potential case value ranges if possible."""
        }
        
        # Legal term patterns for extraction
        self.legal_patterns = {
            "dates": r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            "money": r'\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b',
            "case_citations": r'\b\d+\s+[A-Z][a-z]+\.?\s*(?:2d|3d|4th)?\s*\d+\b',
            "statutes": r'\b\d+\s+U\.?S\.?C\.?\s*§?\s*\d+|§\s*\d+(?:\.\d+)?',
            "parties": r'(?:Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee):\s*([A-Z][a-zA-Z\s,]+?)(?:\n|;|,\s*(?:Plaintiff|Defendant))',
        }
        
        # Query type patterns for classification
        self.query_patterns = {
            "parties": [
                r'\b(who|what|which)\s+(is|are|was|were)\s+the\s+(part|plaintiff|defendant|client|buyer|seller|landlord|tenant)',
                r'\b(part|plaintiff|defendant|client|buyer|seller|landlord|tenant)',
                r'\bnamed\s+in\b',
                r'\binvolved\s+in\b',
                r'\brepresent',
                r'\bparty\s+to\b'
            ],
            "dates": [
                r'\b(when|what\s+date|deadline|due\s+date|expir)',
                r'\b(by|before|after|on)\s+what\s+date',
                r'\b(date|deadline|timeline|schedule)',
                r'\bhappen(ed)?\s+on\b',
                r'\bdue\s+(on|by)\b'
            ],
            "amounts": [
                r'\b(how\s+much|what\s+amount|price|cost|fee|payment|salary|compensation)',
                r'\b(pay|owe|charge|worth|value)',
                r'\b(dollar|amount|sum|total)',
                r'\$\d+',
                r'\bmoney\b'
            ],
            "obligations": [
                r'\b(oblig|duty|duties|respons|require|must|shall|covenant)',
                r'\b(what\s+must|what\s+should|required\s+to)',
                r'\b(comply|perform|deliver)',
                r'\bterms\s+and\s+conditions\b'
            ]
        }
    
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    async def process_chat_message(
        self, 
        message: str, 
        documents: List[Any], 
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """Process a chat message with local Ollama model"""
        
        start_time = time.time()
        
        try:
            if not self.is_available:
                return await self._offline_response(message, documents)
            
            # Classify the query type
            query_type = self._classify_query(message)
            print(f"🔍 Query classified as: {query_type}")
            
            # Check if this is a metadata-related query
            if query_type in ['parties', 'dates', 'amounts', 'obligations'] and documents:
                metadata_response = await self._search_metadata(query_type, message, documents)
                if metadata_response:
                    print(f"✅ Answering from extracted metadata")
                    end_time = time.time()
                    response_time_ms = int((end_time - start_time) * 1000)
                    
                    metadata_response["response_metrics"] = {
                        "response_time_ms": response_time_ms,
                        "tokens_used": 0,
                        "response_type": "instant_metadata",
                        "cost_saved": 0,
                        "tokens_saved": 0
                    }
                    return metadata_response
            
            # Detect document type if not specified
            if analysis_type == "general" and documents:
                analysis_type = await self._detect_document_type(documents[0])
            
            # Build enhanced context from documents
            document_context = self._build_enhanced_document_context(documents, query_type)
            
            # Extract key legal information
            extracted_info = self._extract_legal_entities(documents)
            
            # Build conversation messages
            messages = self._build_conversation_messages(
                message, document_context, chat_history, analysis_type, extracted_info
            )
            
            # Call Ollama API
            response = await self._call_ollama_api(messages)
            
            # Post-process response
            structured_data = self._extract_structured_data(response, documents)
            risk_assessment = self._assess_risk_level(response, extracted_info)
            
            # Calculate response metrics
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            return {
                "answer": response,
                "sources": self._extract_sources(response, documents),
                "timestamp": datetime.utcnow(),
                "model": self.model,
                "analysis_type": analysis_type,
                "structured_data": structured_data,
                "risk_assessment": risk_assessment,
                "extracted_entities": extracted_info,
                "response_metrics": {
                    "response_time_ms": response_time_ms,
                    "tokens_used": 0,  # Local model, no token tracking
                    "response_type": "local_ai_analysis",
                    "cost_saved": 0,
                    "tokens_saved": 0
                }
            }
            
        except Exception as e:
            print(f"❌ Ollama Service Error: {str(e)}")
            return await self._offline_response(message, documents, error=str(e))
    
    async def _call_ollama_api(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to local Ollama service"""
        
        # Combine messages into a single prompt
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += f"System: {msg['content']}\n\n"
            elif msg["role"] == "user":
                prompt += f"User: {msg['content']}\n\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content']}\n\n"
        
        # Add final instruction
        prompt += "Assistant: "
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent legal analysis
                "top_p": 0.95,
                "num_predict": 4000  # Max tokens
            }
        }
        
        print(f"🔄 Making Ollama API call for legal analysis...")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # Longer timeout for local models
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API call failed: {response.status_code}")
            
            result = response.json()
            answer = result.get("response", "")
            
            print(f"✅ Ollama response received ({len(answer)} chars)")
            return answer
    
    async def _offline_response(self, message: str, documents: List[Any], error: str = None) -> Dict[str, Any]:
        """Response when Ollama is not available"""
        
        if error:
            error_msg = f"⚠️ Ollama Error: {error}. Please ensure Ollama is installed and running."
        else:
            error_msg = "🔧 Ollama Not Available: Please install and start Ollama service for AI features."
        
        response = f"""{error_msg}

To enable AI features:
1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3:8b`
3. Start Ollama service
4. Restart this application

Currently, you can:
- Upload and manage documents
- View document content
- Use basic search features"""
        
        return {
            "answer": response,
            "sources": [],
            "timestamp": datetime.utcnow(),
            "model": "offline",
            "analysis_type": "offline",
            "structured_data": {},
            "risk_assessment": {
                "level": "unknown",
                "high_risk_indicators": 0,
                "medium_risk_indicators": 0,
                "recommendation": "AI analysis unavailable"
            },
            "extracted_entities": {},
            "response_metrics": {
                "response_time_ms": 50,
                "tokens_used": 0,
                "response_type": "offline",
                "cost_saved": 0,
                "tokens_saved": 0
            }
        }
    
    async def analyze_document(self, document: Any, analysis_type: str = None) -> Dict[str, Any]:
        """Perform comprehensive analysis on a single document"""
        
        if not document.extracted_content:
            return {"error": "No content extracted from document"}
        
        # Auto-detect document type if not specified
        if not analysis_type:
            analysis_type = await self._detect_document_type(document)
        
        # Get appropriate prompt for document type
        prompt_key = f"{analysis_type}_analysis"
        if prompt_key not in self.system_prompts:
            prompt_key = "document_analysis"
        
        # Create analysis request
        analysis_prompt = f"""Please analyze the following document:

Document Name: {document.filename}
Document Type: {analysis_type}

Content:
{document.extracted_content[:10000]}  # Limit for performance

{self.system_prompts[prompt_key]}"""
        
        # Process through chat message handler
        return await self.process_chat_message(
            analysis_prompt,
            [document],
            analysis_type=analysis_type
        )
    
    # Include all the helper methods from the original service
    # (Same implementations as in ai_service.py, just without [AI Provider]-specific code)
    
    def _classify_query(self, message: str) -> str:
        """Classify the type of query for optimized processing"""
        message_lower = message.lower()
        
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return query_type
        
        return "general"
    
    def _extract_legal_entities(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract legal entities and information from documents"""
        
        all_entities = {
            "dates": [],
            "monetary_amounts": [],
            "parties": [],
            "case_citations": [],
            "statutes": []
        }
        
        for doc in documents:
            if doc.extracted_content:
                content = doc.extracted_content
                
                all_entities["dates"].extend(self._extract_dates(content))
                all_entities["monetary_amounts"].extend(self._extract_money(content))
                all_entities["parties"].extend(self._extract_parties(content))
                all_entities["case_citations"].extend(re.findall(self.legal_patterns["case_citations"], content))
                all_entities["statutes"].extend(re.findall(self.legal_patterns["statutes"], content))
        
        # Remove duplicates
        for key in all_entities:
            all_entities[key] = list(set(all_entities[key]))
        
        return all_entities
    
    def _extract_dates(self, content: str) -> List[str]:
        """Extract dates from content"""
        dates = re.findall(self.legal_patterns["dates"], content)
        return list(set(dates))
    
    def _extract_money(self, content: str) -> List[str]:
        """Extract monetary amounts from content"""
        amounts = re.findall(self.legal_patterns["money"], content)
        return list(set(amounts))
    
    def _extract_parties(self, content: str) -> List[str]:
        """Extract party names from content"""
        parties = re.findall(self.legal_patterns["parties"], content)
        cleaned_parties = []
        for party in parties:
            cleaned = party.strip().rstrip(',')
            if len(cleaned) > 3:
                cleaned_parties.append(cleaned)
        return list(set(cleaned_parties))
    
    async def _detect_document_type(self, document: Any) -> str:
        """Detect the type of legal document"""
        
        if not document.extracted_content:
            return "general"
        
        content_lower = document.extracted_content.lower()[:2000]
        
        if any(term in content_lower for term in ["i-130", "i-485", "uscis", "immigration", "visa", "green card"]):
            return "immigration_form"
        elif any(term in content_lower for term in ["divorce", "custody", "child support", "alimony", "marital"]):
            return "family_law"
        elif any(term in content_lower for term in ["defendant", "prosecutor", "criminal", "plea", "conviction"]):
            return "criminal_defense"
        elif any(term in content_lower for term in ["injury", "damages", "negligence", "accident", "medical bills"]):
            return "personal_injury"
        elif any(term in content_lower for term in ["agreement", "contract", "party", "terms", "obligations"]):
            return "contract"
        
        return "general"
    
    def _assess_risk_level(self, response: str, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk level based on AI response and extracted information"""
        
        response_lower = response.lower()
        
        high_risk_terms = ["urgent", "deadline passed", "missing", "violation", "breach", 
                          "non-compliant", "invalid", "rejected", "denied", "critical"]
        medium_risk_terms = ["concern", "issue", "unclear", "ambiguous", "review needed", 
                           "potential", "may", "could", "should consider"]
        
        high_risk_count = sum(1 for term in high_risk_terms if term in response_lower)
        medium_risk_count = sum(1 for term in medium_risk_terms if term in response_lower)
        
        if high_risk_count >= 3:
            risk_level = RiskLevel.CRITICAL
        elif high_risk_count >= 1:
            risk_level = RiskLevel.HIGH
        elif medium_risk_count >= 3:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return {
            "level": risk_level.value,
            "high_risk_indicators": high_risk_count,
            "medium_risk_indicators": medium_risk_count,
            "recommendation": self._get_risk_recommendation(risk_level)
        }
    
    def _get_risk_recommendation(self, risk_level: RiskLevel) -> str:
        """Get recommendation based on risk level"""
        
        recommendations = {
            RiskLevel.CRITICAL: "Immediate attorney review required. Multiple critical issues identified.",
            RiskLevel.HIGH: "Priority review recommended. Significant legal risks identified.",
            RiskLevel.MEDIUM: "Standard review recommended. Some areas need attention.",
            RiskLevel.LOW: "Routine review sufficient. No major concerns identified."
        }
        
        return recommendations.get(risk_level, "Review recommended.")
    
    def _extract_structured_data(self, response: str, documents: List[Any]) -> Dict[str, Any]:
        """Extract structured data from AI response"""
        
        return {
            "summary": self._extract_summary(response),
            "action_items": self._extract_action_items(response),
            "key_findings": self._extract_key_findings(response),
            "recommendations": self._extract_recommendations(response)
        }
    
    def _extract_summary(self, response: str) -> str:
        """Extract summary from response"""
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if 'summary' in line.lower() and i + 1 < len(lines):
                return lines[i + 1].strip()
        
        for line in lines:
            if len(line.strip()) > 50:
                return line.strip()
        
        return "See full analysis above."
    
    def _extract_action_items(self, response: str) -> List[str]:
        """Extract action items from response"""
        action_items = []
        lines = response.split('\n')
        
        in_action_section = False
        for line in lines:
            line_lower = line.lower()
            
            if 'action item' in line_lower or 'next step' in line_lower:
                in_action_section = True
                continue
            
            if in_action_section:
                if re.match(r'^[\d•\-\*]\s*\w', line.strip()):
                    action_items.append(line.strip())
                elif line.strip() == '' and len(action_items) > 0:
                    break
        
        return action_items
    
    def _extract_key_findings(self, response: str) -> List[str]:
        """Extract key findings from response"""
        findings = []
        lines = response.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            if any(indicator in line_stripped.lower() for indicator in 
                   ['found that', 'identified', 'discovered', 'noted that', 'observed']):
                findings.append(line_stripped)
        
        return findings[:5]
    
    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from response"""
        recommendations = []
        lines = response.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            if any(indicator in line_lower for indicator in 
                   ['recommend', 'suggest', 'advise', 'should', 'must', 'need to']):
                recommendations.append(line_stripped)
        
        return recommendations[:5]
    
    def _build_enhanced_document_context(self, documents: List[Any], query_type: str = None) -> str:
        """Build enhanced context string from documents"""
        if not documents:
            return "No documents are currently loaded for context."
        
        context = "Documents provided for analysis:\n\n"
        
        max_docs = 5
        if len(documents) > max_docs:
            print(f"⚠️ Limiting context to first {max_docs} documents out of {len(documents)}")
            documents = documents[:max_docs]
        
        for i, doc in enumerate(documents, 1):
            context += f"Document {i}: {doc.filename}\n"
            context += f"Upload Date: {doc.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(doc, 'upload_timestamp') else 'Unknown'}\n"
            
            if doc.summary:
                context += f"AI Summary: {doc.summary}\n"
            
            if hasattr(doc, 'legal_metadata') and doc.legal_metadata:
                try:
                    metadata = json.loads(doc.legal_metadata)
                    context += "\n📊 Extracted Legal Information:\n"
                    
                    if metadata.get('document_type'):
                        context += f"   • Document Type: {metadata['document_type']}\n"
                    
                    if query_type == "parties" and metadata.get('parties'):
                        context += "   • Parties:\n"
                        for party in metadata['parties']:
                            if isinstance(party, dict):
                                context += f"      - {party.get('role', 'Party')}: {party.get('name', 'Unknown')}\n"
                            else:
                                context += f"      - {party}\n"
                    
                    elif query_type == "dates" and metadata.get('dates'):
                        context += "   • Key Dates:\n"
                        for date in metadata['dates']:
                            if isinstance(date, dict):
                                context += f"      - {date.get('event', 'Date')}: {date.get('date', 'Unknown')}\n"
                            else:
                                context += f"      - {date}\n"
                    
                    elif query_type == "amounts" and metadata.get('monetary_amounts'):
                        context += "   • Monetary Amounts:\n"
                        for amount in metadata['monetary_amounts']:
                            if isinstance(amount, dict):
                                context += f"      - {amount.get('description', 'Amount')}: {amount.get('amount', 'Unknown')}\n"
                            else:
                                context += f"      - {amount}\n"
                    
                    elif query_type == "obligations" and metadata.get('key_obligations'):
                        context += "   • Key Obligations:\n"
                        for obligation in metadata['key_obligations']:
                            context += f"      - {obligation}\n"
                    
                    elif query_type == "general" or query_type is None:
                        if metadata.get('parties'):
                            context += f"   • Parties: {len(metadata['parties'])} identified\n"
                        if metadata.get('dates'):
                            context += f"   • Dates: {len(metadata['dates'])} important dates found\n"
                        if metadata.get('monetary_amounts'):
                            context += f"   • Amounts: {len(metadata['monetary_amounts'])} monetary values\n"
                        if metadata.get('jurisdiction'):
                            context += f"   • Jurisdiction: {metadata['jurisdiction']}\n"
                        if metadata.get('governing_law'):
                            context += f"   • Governing Law: {metadata['governing_law']}\n"
                    
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            if doc.extracted_content:
                content_length = len(doc.extracted_content)
                max_content_size = 10000
                
                if query_type in ['parties', 'dates', 'amounts', 'obligations']:
                    relevant_sections = self._find_relevant_sections(doc.extracted_content[:max_content_size], query_type)
                    if relevant_sections:
                        context += f"\nRelevant Content Sections:\n{relevant_sections}\n"
                    else:
                        content_preview = doc.extracted_content[:1000] if content_length > 1000 else doc.extracted_content
                        context += f"\nContent Preview:\n{content_preview}\n"
                else:
                    if content_length <= 3000:
                        content_preview = doc.extracted_content[:min(content_length, max_content_size)]
                    else:
                        start_size = min(1500, max_content_size // 2)
                        end_size = min(1000, max_content_size // 2)
                        content_preview = doc.extracted_content[:start_size] + "\n\n[... middle section truncated ...]\n\n" + doc.extracted_content[-end_size:]
                    context += f"\nContent:\n{content_preview}\n"
            
            context += "\n" + "="*60 + "\n\n"
        
        return context
    
    def _build_conversation_messages(
        self, 
        current_message: str, 
        document_context: str, 
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general",
        extracted_info: Dict[str, Any] = None
    ) -> List[Dict[str, str]]:
        """Build enhanced message array for API call"""
        
        prompt_key = f"{analysis_type}_analysis"
        if prompt_key not in self.system_prompts:
            prompt_key = "legal_assistant"
        
        messages = [
            {"role": "system", "content": self.system_prompts[prompt_key]}
        ]
        
        enhanced_context = document_context
        if extracted_info and any(extracted_info.values()):
            enhanced_context += "\n\nExtracted Legal Information:\n"
            if extracted_info.get("dates"):
                enhanced_context += f"Key Dates: {', '.join(extracted_info['dates'][:5])}\n"
            if extracted_info.get("monetary_amounts"):
                enhanced_context += f"Monetary Amounts: {', '.join(extracted_info['monetary_amounts'][:5])}\n"
            if extracted_info.get("parties"):
                enhanced_context += f"Parties: {', '.join(extracted_info['parties'][:5])}\n"
        
        messages.append({
            "role": "system", 
            "content": enhanced_context
        })
        
        if chat_history:
            for msg in chat_history[-6:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        return messages
    
    def _extract_sources(self, response: str, documents: List[Any]) -> List[Dict[str, Any]]:
        """Enhanced source extraction with relevance scoring"""
        sources = []
        response_lower = response.lower()
        
        for doc in documents:
            relevance_score = 0
            relevance_type = "mentioned"
            
            doc_name_lower = doc.filename.lower()
            
            if doc_name_lower in response_lower:
                relevance_score += 3
                relevance_type = "directly_referenced"
            
            if doc.extracted_content and len(doc.extracted_content) > 100:
                sample_phrase = doc.extracted_content[100:150].lower()
                if sample_phrase in response_lower:
                    relevance_score += 5
                    relevance_type = "content_quoted"
            
            doc_type = doc.filename.split('.')[-1].lower()
            if f"{doc_type} document" in response_lower or f"{doc_type} file" in response_lower:
                relevance_score += 1
            
            if relevance_score > 0:
                sources.append({
                    "document_id": doc.id,
                    "document_name": doc.filename,
                    "relevance": relevance_type,
                    "relevance_score": relevance_score
                })
        
        sources.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return sources
    
    async def _search_metadata(self, query_type: str, message: str, documents: List[Any]) -> Optional[Dict[str, Any]]:
        """Search extracted metadata to answer queries without API calls"""
        
        results = []
        
        for doc in documents:
            if not hasattr(doc, 'legal_metadata') or not doc.legal_metadata:
                continue
            
            try:
                metadata = json.loads(doc.legal_metadata)
                
                if query_type == "parties":
                    parties = metadata.get('parties', [])
                    if parties:
                        results.append({
                            'document': doc.filename,
                            'parties': parties
                        })
                
                elif query_type == "dates":
                    dates = metadata.get('dates', [])
                    if dates:
                        results.append({
                            'document': doc.filename,
                            'dates': dates
                        })
                
                elif query_type == "amounts":
                    amounts = metadata.get('monetary_amounts', [])
                    if amounts:
                        results.append({
                            'document': doc.filename,
                            'amounts': amounts
                        })
                
                elif query_type == "obligations":
                    obligations = metadata.get('key_obligations', [])
                    if obligations:
                        results.append({
                            'document': doc.filename,
                            'obligations': obligations
                        })
                        
            except (json.JSONDecodeError, AttributeError):
                continue
        
        if results:
            return self._format_metadata_response(query_type, results, message)
        
        return None
    
    def _format_metadata_response(self, query_type: str, results: List[Dict], original_query: str) -> Dict[str, Any]:
        """Format metadata results into a structured response"""
        
        response_text = ""
        
        if query_type == "parties":
            response_text = "**🏢 Parties Identified:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for party in result['parties']:
                    if isinstance(party, dict):
                        response_text += f"   • **{party.get('role', 'Party')}**: {party.get('name', 'Unknown')}\n"
                    else:
                        response_text += f"   • {party}\n"
                response_text += "\n"
        
        elif query_type == "dates":
            response_text = "**📅 Important Dates:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for date in result['dates']:
                    if isinstance(date, dict):
                        response_text += f"   • **{date.get('event', 'Date')}**: {date.get('date', 'Unknown')}\n"
                    else:
                        response_text += f"   • {date}\n"
                response_text += "\n"
        
        elif query_type == "amounts":
            response_text = "**💰 Monetary Amounts:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for amount in result['amounts']:
                    if isinstance(amount, dict):
                        response_text += f"   • **{amount.get('description', 'Amount')}**: {amount.get('amount', 'Unknown')}\n"
                    else:
                        response_text += f"   • {amount}\n"
                response_text += "\n"
        
        elif query_type == "obligations":
            response_text = "**📋 Key Obligations:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for obligation in result['obligations']:
                    response_text += f"   • {obligation}\n"
                response_text += "\n"
        
        response_text += "\n---\n*📊 This information was extracted from document metadata for quick reference.*"
        
        return {
            "answer": response_text,
            "sources": [],
            "metadata_used": True,
            "query_type": query_type,
            "documents_searched": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _find_relevant_sections(self, content: str, query_type: str, max_sections: int = 3) -> str:
        """Find and extract relevant sections from content based on query type"""
        
        relevant_sections = []
        lines = content.split('\n')
        
        keywords = {
            'parties': ['party', 'parties', 'plaintiff', 'defendant', 'buyer', 'seller', 'landlord', 'tenant', 'client', 'contractor'],
            'dates': ['date', 'deadline', 'due', 'expire', 'effective', 'termination', 'commencement'],
            'amounts': ['amount', 'payment', 'price', 'fee', 'cost', 'compensation', 'salary', '$'],
            'obligations': ['shall', 'must', 'obligation', 'duty', 'required', 'responsible', 'covenant', 'undertake']
        }
        
        query_keywords = keywords.get(query_type, [])
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in query_keywords):
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                section = '\n'.join(lines[start:end])
                
                if section not in relevant_sections:
                    relevant_sections.append(section)
                    
                if len(relevant_sections) >= max_sections:
                    break
        
        if relevant_sections:
            return '\n\n[...]\n\n'.join(relevant_sections)
        
        return ""
