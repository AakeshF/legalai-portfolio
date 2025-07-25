# services/ai_service.py - Enhanced [AI Provider] AI service for legal document analysis
import os
import httpx
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from config import settings

# Explicitly load .env file
load_dotenv()


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


class AIService:
    """Enhanced AI service for comprehensive legal document analysis using AI providers"""

    def __init__(self):
        # Check if demo mode is enabled
        self.is_demo_mode = (
            settings.demo_mode or os.getenv("DEMO_MODE", "false").lower() == "true"
        )

        if self.is_demo_mode:
            print("🎮 Demo Mode Active - Using AI provider exclusively")
            # In demo mode, always use configured AI provider
            self.api_key = getattr(settings, "ai_api_key", None)
            self.base_url = getattr(
                settings, "ai_base_url", "https://api.openai.com/v1"
            )
            self.model = settings.ai_model
            self.api_provider = "ai_provider"
        else:
            # Production mode - can use multiple providers
            print("🚀 Production Mode - Multiple AI providers available")
            # Default to configured provider but allow switching
            self.api_key = getattr(settings, "ai_api_key", None)
            self.base_url = getattr(
                settings, "ai_base_url", "https://api.openai.com/v1"
            )
            self.model = settings.ai_model
            self.api_provider = "ai_provider"

            # Store other API keys for production use
            self.openai_api_key = settings.openai_api_key
            self.anthropic_api_key = settings.anthropic_api_key

        # Check if we have a valid API key
        if not self.api_key:
            print("❌ No AI_API_KEY configured")
            self.demo_mode = True
        elif not self.api_key.startswith("sk-"):
            print(f"❌ Invalid API key format")
            self.demo_mode = True
        else:
            self.demo_mode = False
            print(f"✅ {self.api_provider.upper()} API initialized")

        # Enhanced legal-specific prompts
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

Calculate potential case value ranges if possible.""",
        }

        # Legal term patterns for extraction
        self.legal_patterns = {
            "dates": r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "money": r"\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b",
            "case_citations": r"\b\d+\s+[A-Z][a-z]+\.?\s*(?:2d|3d|4th)?\s*\d+\b",
            "statutes": r"\b\d+\s+U\.?S\.?C\.?\s*§?\s*\d+|§\s*\d+(?:\.\d+)?",
            "parties": r"(?:Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee):\s*([A-Z][a-zA-Z\s,]+?)(?:\n|;|,\s*(?:Plaintiff|Defendant))",
        }

        # Query type patterns for classification
        self.query_patterns = {
            "parties": [
                r"\b(who|what|which)\s+(is|are|was|were)\s+the\s+(part|plaintiff|defendant|client|buyer|seller|landlord|tenant)",
                r"\b(part|plaintiff|defendant|client|buyer|seller|landlord|tenant)",
                r"\bnamed\s+in\b",
                r"\binvolved\s+in\b",
                r"\brepresent",
                r"\bparty\s+to\b",
            ],
            "dates": [
                r"\b(when|what\s+date|deadline|due\s+date|expir)",
                r"\b(by|before|after|on)\s+what\s+date",
                r"\b(date|deadline|timeline|schedule)",
                r"\bhappen(ed)?\s+on\b",
                r"\bdue\s+(on|by)\b",
            ],
            "amounts": [
                r"\b(how\s+much|what\s+amount|price|cost|fee|payment|salary|compensation)",
                r"\b(pay|owe|charge|worth|value)",
                r"\b(dollar|amount|sum|total)",
                r"\$\d+",
                r"\bmoney\b",
            ],
            "obligations": [
                r"\b(oblig|duty|duties|respons|require|must|shall|covenant)",
                r"\b(what\s+must|what\s+should|required\s+to)",
                r"\b(comply|perform|deliver)",
                r"\bterms\s+and\s+conditions\b",
            ],
        }

    async def process_chat_message(
        self,
        message: str,
        documents: List[Any],
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general",
    ) -> Dict[str, Any]:
        """Process a chat message with enhanced legal document context and metadata awareness"""

        # Start timing
        start_time = time.time()

        try:
            # Use demo mode if no valid API key or in demo mode
            if self.demo_mode or self.is_demo_mode:
                # In demo mode, enforce configured AI provider only
                if self.is_demo_mode and self.api_provider != "ai_provider":
                    self.api_provider = "ai_provider"
                    self.api_key = getattr(settings, "ai_api_key", None)
                    self.base_url = getattr(
                        settings, "ai_base_url", "https://api.openai.com/v1"
                    )
                    self.model = settings.ai_model

                # If we have a valid AI key in demo mode, use it
                if (
                    self.is_demo_mode
                    and self.api_key
                    and self.api_key.startswith("sk-")
                ):
                    # Continue with normal API call
                    pass
                else:
                    return await self._demo_response(message, documents)

            # Classify the query type
            query_type = self._classify_query(message)
            print(f"🔍 Query classified as: {query_type}")

            # Check if this is a metadata-related query
            if (
                query_type in ["parties", "dates", "amounts", "obligations"]
                and documents
            ):
                # Try to answer from extracted metadata first
                metadata_response = await self._search_metadata(
                    query_type, message, documents
                )
                if metadata_response:
                    print(f"✅ Answering from extracted metadata")
                    # Add response metrics
                    end_time = time.time()
                    response_time_ms = int((end_time - start_time) * 1000)

                    # Calculate estimated tokens saved
                    estimated_tokens_saved = self._estimate_tokens_saved(
                        message, documents, query_type
                    )
                    cost_saved = self._calculate_cost_saved(estimated_tokens_saved)

                    metadata_response["response_metrics"] = {
                        "response_time_ms": response_time_ms,
                        "tokens_used": 0,  # No API tokens used
                        "response_type": "instant_metadata",
                        "cost_saved": cost_saved,
                        "tokens_saved": estimated_tokens_saved,
                    }
                    return metadata_response

            # Detect document type if not specified
            if analysis_type == "general" and documents:
                analysis_type = await self._detect_document_type(documents[0])

            # Build enhanced context from documents (now metadata-aware)
            document_context = self._build_enhanced_document_context(
                documents, query_type
            )

            # Extract key legal information
            extracted_info = self._extract_legal_entities(documents)

            # Build conversation messages with appropriate prompt
            messages = self._build_conversation_messages(
                message, document_context, chat_history, analysis_type, extracted_info
            )

            # Call AI API
            response = await self._call_ai_api(messages)

            # Post-process response for structured data
            structured_data = self._extract_structured_data(response, documents)

            # Assess risk level
            risk_assessment = self._assess_risk_level(response, extracted_info)

            # Calculate response metrics
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            # Estimate tokens used (rough calculation)
            tokens_used = self._estimate_tokens_used(messages, response)

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
                    "tokens_used": tokens_used,
                    "response_type": "ai_analysis",
                    "cost_saved": 0,  # No cost saved for API calls
                    "tokens_saved": 0,
                },
            }

        except Exception as e:
            print(f"❌ AI Service Error: {str(e)}")
            # Fallback to demo response on any error
            return await self._demo_response(message, documents, error=str(e))

    async def analyze_document(
        self, document: Any, analysis_type: str = None
    ) -> Dict[str, Any]:
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
{document.extracted_content[:10000]}  # Limit for API

{self.system_prompts[prompt_key]}"""

        # Process through chat message handler
        return await self.process_chat_message(
            analysis_prompt, [document], analysis_type=analysis_type
        )

    async def compare_documents(
        self, documents: List[Any], comparison_type: str = "general"
    ) -> Dict[str, Any]:
        """Compare multiple documents for differences, conflicts, or patterns"""

        if len(documents) < 2:
            return {"error": "Need at least 2 documents to compare"}

        comparison_prompt = f"""Compare the following {len(documents)} documents:

{chr(10).join([f"Document {i+1}: {doc.filename}" for i, doc in enumerate(documents)])}

Please identify:
1. Key differences between documents
2. Conflicting terms or provisions
3. Common patterns or standard clauses
4. Missing elements in any document
5. Recommendations for reconciliation

Focus on legally significant differences."""

        return await self.process_chat_message(
            comparison_prompt, documents, analysis_type="comparison"
        )

    async def extract_key_terms(self, document: Any) -> Dict[str, List[Any]]:
        """Extract key legal terms, dates, parties, and amounts from document"""

        content = document.extracted_content or ""

        extracted = {
            "dates": self._extract_dates(content),
            "monetary_amounts": self._extract_money(content),
            "parties": self._extract_parties(content),
            "case_citations": re.findall(
                self.legal_patterns["case_citations"], content
            ),
            "statutes": re.findall(self.legal_patterns["statutes"], content),
            "key_terms": await self._extract_key_legal_terms(content),
        }

        return extracted

    def _extract_legal_entities(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract legal entities and information from documents"""

        all_entities = {
            "dates": [],
            "monetary_amounts": [],
            "parties": [],
            "case_citations": [],
            "statutes": [],
        }

        for doc in documents:
            if doc.extracted_content:
                content = doc.extracted_content

                # Extract various entities
                all_entities["dates"].extend(self._extract_dates(content))
                all_entities["monetary_amounts"].extend(self._extract_money(content))
                all_entities["parties"].extend(self._extract_parties(content))
                all_entities["case_citations"].extend(
                    re.findall(self.legal_patterns["case_citations"], content)
                )
                all_entities["statutes"].extend(
                    re.findall(self.legal_patterns["statutes"], content)
                )

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
        # Clean up party names
        cleaned_parties = []
        for party in parties:
            cleaned = party.strip().rstrip(",")
            if len(cleaned) > 3:  # Filter out short matches
                cleaned_parties.append(cleaned)
        return list(set(cleaned_parties))

    async def _extract_key_legal_terms(self, content: str) -> List[str]:
        """Extract key legal terms using AI"""

        if self.demo_mode:
            # Return common legal terms in demo mode
            return [
                "agreement",
                "liability",
                "indemnification",
                "breach",
                "damages",
                "termination",
                "jurisdiction",
                "confidentiality",
            ]

        prompt = """Extract the 10 most important legal terms or concepts from this document. 
        Return only the terms as a comma-separated list, no explanations."""

        try:
            messages = [
                {"role": "system", "content": "You are a legal term extractor."},
                {"role": "user", "content": f"{prompt}\n\nContent: {content[:3000]}"},
            ]

            response = await self._call_deepseek_api(messages)
            terms = [term.strip() for term in response.split(",")]
            return terms[:10]  # Limit to 10 terms

        except:
            return []

    async def _detect_document_type(self, document: Any) -> str:
        """Detect the type of legal document"""

        if not document.extracted_content:
            return "general"

        content_lower = document.extracted_content.lower()[
            :2000
        ]  # Check first 2000 chars
        filename_lower = document.filename.lower()

        # Simple keyword-based detection
        if any(
            term in content_lower
            for term in ["i-130", "i-485", "uscis", "immigration", "visa", "green card"]
        ):
            return "immigration_form"
        elif any(
            term in content_lower
            for term in ["divorce", "custody", "child support", "alimony", "marital"]
        ):
            return "family_law"
        elif any(
            term in content_lower
            for term in ["defendant", "prosecutor", "criminal", "plea", "conviction"]
        ):
            return "criminal_defense"
        elif any(
            term in content_lower
            for term in ["injury", "damages", "negligence", "accident", "medical bills"]
        ):
            return "personal_injury"
        elif any(
            term in content_lower
            for term in ["agreement", "contract", "party", "terms", "obligations"]
        ):
            return "contract"

        return "general"

    def _assess_risk_level(
        self, response: str, extracted_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk level based on AI response and extracted information"""

        response_lower = response.lower()

        # Risk indicators
        high_risk_terms = [
            "urgent",
            "deadline passed",
            "missing",
            "violation",
            "breach",
            "non-compliant",
            "invalid",
            "rejected",
            "denied",
            "critical",
        ]
        medium_risk_terms = [
            "concern",
            "issue",
            "unclear",
            "ambiguous",
            "review needed",
            "potential",
            "may",
            "could",
            "should consider",
        ]

        # Count risk indicators
        high_risk_count = sum(1 for term in high_risk_terms if term in response_lower)
        medium_risk_count = sum(
            1 for term in medium_risk_terms if term in response_lower
        )

        # Determine risk level
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
            "recommendation": self._get_risk_recommendation(risk_level),
        }

    def _get_risk_recommendation(self, risk_level: RiskLevel) -> str:
        """Get recommendation based on risk level"""

        recommendations = {
            RiskLevel.CRITICAL: "Immediate attorney review required. Multiple critical issues identified.",
            RiskLevel.HIGH: "Priority review recommended. Significant legal risks identified.",
            RiskLevel.MEDIUM: "Standard review recommended. Some areas need attention.",
            RiskLevel.LOW: "Routine review sufficient. No major concerns identified.",
        }

        return recommendations.get(risk_level, "Review recommended.")

    def _extract_structured_data(
        self, response: str, documents: List[Any]
    ) -> Dict[str, Any]:
        """Extract structured data from AI response"""

        structured = {
            "summary": self._extract_summary(response),
            "action_items": self._extract_action_items(response),
            "key_findings": self._extract_key_findings(response),
            "recommendations": self._extract_recommendations(response),
        }

        return structured

    def _extract_summary(self, response: str) -> str:
        """Extract summary from response"""
        # Look for summary section or first paragraph
        lines = response.split("\n")
        for i, line in enumerate(lines):
            if "summary" in line.lower() and i + 1 < len(lines):
                return lines[i + 1].strip()

        # Return first substantial paragraph
        for line in lines:
            if len(line.strip()) > 50:
                return line.strip()

        return "See full analysis above."

    def _extract_action_items(self, response: str) -> List[str]:
        """Extract action items from response"""
        action_items = []
        lines = response.split("\n")

        in_action_section = False
        for line in lines:
            line_lower = line.lower()

            # Check if we're in action items section
            if "action item" in line_lower or "next step" in line_lower:
                in_action_section = True
                continue

            # Extract numbered or bulleted items
            if in_action_section:
                if re.match(r"^[\d•\-\*]\s*\w", line.strip()):
                    action_items.append(line.strip())
                elif line.strip() == "" and len(action_items) > 0:
                    break  # End of action items section

        return action_items

    def _extract_key_findings(self, response: str) -> List[str]:
        """Extract key findings from response"""
        findings = []
        lines = response.split("\n")

        # Look for findings patterns
        for line in lines:
            line_stripped = line.strip()
            if any(
                indicator in line_stripped.lower()
                for indicator in [
                    "found that",
                    "identified",
                    "discovered",
                    "noted that",
                    "observed",
                ]
            ):
                findings.append(line_stripped)

        return findings[:5]  # Limit to top 5 findings

    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from response"""
        recommendations = []
        lines = response.split("\n")

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            if any(
                indicator in line_lower
                for indicator in [
                    "recommend",
                    "suggest",
                    "advise",
                    "should",
                    "must",
                    "need to",
                ]
            ):
                recommendations.append(line_stripped)

        return recommendations[:5]  # Limit to top 5 recommendations

    def _build_enhanced_document_context(
        self, documents: List[Any], query_type: str = None
    ) -> str:
        """Build enhanced context string from documents, optimized for query type"""
        if not documents:
            return "No documents are currently loaded for context."

        context = "Documents provided for analysis:\n\n"

        # Limit number of documents to prevent memory issues
        max_docs = 5
        if len(documents) > max_docs:
            print(
                f"⚠️ Limiting context to first {max_docs} documents out of {len(documents)}"
            )
            documents = documents[:max_docs]

        for i, doc in enumerate(documents, 1):
            context += f"Document {i}: {doc.filename}\n"
            context += f"Upload Date: {doc.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(doc, 'upload_timestamp') else 'Unknown'}\n"

            if doc.summary:
                context += f"AI Summary: {doc.summary}\n"

            # Include extracted legal metadata if available
            if hasattr(doc, "legal_metadata") and doc.legal_metadata:
                try:
                    metadata = json.loads(doc.legal_metadata)
                    context += "\n📊 Extracted Legal Information:\n"

                    # Always include document type
                    if metadata.get("document_type"):
                        context += f"   • Document Type: {metadata['document_type']}\n"

                    # Include metadata based on query type for optimization
                    if query_type == "parties" and metadata.get("parties"):
                        context += "   • Parties:\n"
                        for party in metadata["parties"]:
                            if isinstance(party, dict):
                                context += f"      - {party.get('role', 'Party')}: {party.get('name', 'Unknown')}\n"
                            else:
                                context += f"      - {party}\n"

                    elif query_type == "dates" and metadata.get("dates"):
                        context += "   • Key Dates:\n"
                        for date in metadata["dates"]:
                            if isinstance(date, dict):
                                context += f"      - {date.get('event', 'Date')}: {date.get('date', 'Unknown')}\n"
                            else:
                                context += f"      - {date}\n"

                    elif query_type == "amounts" and metadata.get("monetary_amounts"):
                        context += "   • Monetary Amounts:\n"
                        for amount in metadata["monetary_amounts"]:
                            if isinstance(amount, dict):
                                context += f"      - {amount.get('description', 'Amount')}: {amount.get('amount', 'Unknown')}\n"
                            else:
                                context += f"      - {amount}\n"

                    elif query_type == "obligations" and metadata.get(
                        "key_obligations"
                    ):
                        context += "   • Key Obligations:\n"
                        for obligation in metadata["key_obligations"]:
                            context += f"      - {obligation}\n"

                    # For general queries, include a summary of all metadata
                    elif query_type == "general" or query_type is None:
                        if metadata.get("parties"):
                            context += (
                                f"   • Parties: {len(metadata['parties'])} identified\n"
                            )
                        if metadata.get("dates"):
                            context += f"   • Dates: {len(metadata['dates'])} important dates found\n"
                        if metadata.get("monetary_amounts"):
                            context += f"   • Amounts: {len(metadata['monetary_amounts'])} monetary values\n"
                        if metadata.get("jurisdiction"):
                            context += (
                                f"   • Jurisdiction: {metadata['jurisdiction']}\n"
                            )
                        if metadata.get("governing_law"):
                            context += (
                                f"   • Governing Law: {metadata['governing_law']}\n"
                            )

                except (json.JSONDecodeError, AttributeError):
                    pass

            # Include relevant portions of content (optimized by query type)
            if doc.extracted_content:
                content_length = len(doc.extracted_content)

                # Limit content size to prevent memory issues
                max_content_size = 10000  # 10KB per document

                # For metadata queries, try to find relevant sections
                if query_type in ["parties", "dates", "amounts", "obligations"]:
                    # Search for relevant sections in the content
                    relevant_sections = self._find_relevant_sections(
                        doc.extracted_content[:max_content_size], query_type
                    )
                    if relevant_sections:
                        context += (
                            f"\nRelevant Content Sections:\n{relevant_sections}\n"
                        )
                    else:
                        # Fall back to standard preview
                        content_preview = (
                            doc.extracted_content[:1000]
                            if content_length > 1000
                            else doc.extracted_content
                        )
                        context += f"\nContent Preview:\n{content_preview}\n"
                else:
                    # Standard content preview for general queries
                    if content_length <= 3000:
                        content_preview = doc.extracted_content[
                            : min(content_length, max_content_size)
                        ]
                    else:
                        # Smart truncation for large documents
                        start_size = min(1500, max_content_size // 2)
                        end_size = min(1000, max_content_size // 2)
                        content_preview = (
                            doc.extracted_content[:start_size]
                            + "\n\n[... middle section truncated ...]\n\n"
                            + doc.extracted_content[-end_size:]
                        )
                    context += f"\nContent:\n{content_preview}\n"

            context += "\n" + "=" * 60 + "\n\n"

        return context

    def _build_conversation_messages(
        self,
        current_message: str,
        document_context: str,
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general",
        extracted_info: Dict[str, Any] = None,
    ) -> List[Dict[str, str]]:
        """Build enhanced message array for API call"""

        # Select appropriate system prompt
        prompt_key = f"{analysis_type}_analysis"
        if prompt_key not in self.system_prompts:
            prompt_key = "legal_assistant"

        messages = [{"role": "system", "content": self.system_prompts[prompt_key]}]

        # Add document context with extracted information
        enhanced_context = document_context
        if extracted_info and any(extracted_info.values()):
            enhanced_context += "\n\nExtracted Legal Information:\n"
            if extracted_info.get("dates"):
                enhanced_context += (
                    f"Key Dates: {', '.join(extracted_info['dates'][:5])}\n"
                )
            if extracted_info.get("monetary_amounts"):
                enhanced_context += f"Monetary Amounts: {', '.join(extracted_info['monetary_amounts'][:5])}\n"
            if extracted_info.get("parties"):
                enhanced_context += (
                    f"Parties: {', '.join(extracted_info['parties'][:5])}\n"
                )

        messages.append({"role": "system", "content": enhanced_context})

        # Add chat history for context
        if chat_history:
            for msg in chat_history[-6:]:  # Last 6 messages for context
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    async def _call_ai_api(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to AI provider with enhanced parameters"""

        # Limit message content to prevent token overflow
        limited_messages = []
        for msg in messages:
            content = msg.get("content", "")
            # Limit each message to 20K characters
            if len(content) > 20000:
                content = (
                    content[:19000] + "\n\n[... Content truncated due to length ...]"
                )
            limited_messages.append({"role": msg["role"], "content": content})

        payload = {
            "model": self.model,
            "messages": limited_messages,
            "temperature": 0.1,  # Low temperature for consistent legal analysis
            "max_tokens": 4000,
            "stream": False,
            "top_p": 0.95,  # Slightly limit randomness
            "frequency_penalty": 0.1,  # Reduce repetition
            "presence_penalty": 0.1,  # Encourage covering all topics
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        print(f"🔄 Making AI API call for legal analysis...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )

            print(f"📡 AI API Response: {response.status_code}")

            if response.status_code != 200:
                error_detail = response.text
                raise Exception(
                    f"API call failed: {response.status_code} - {error_detail}"
                )

            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                print(f"✅ AI response received ({len(answer)} chars)")
                return answer
            else:
                raise Exception("No response from AI model")

    async def _demo_response(
        self, message: str, documents: List[Any], error: str = None
    ) -> Dict[str, Any]:
        """Enhanced demo response when API is unavailable"""

        if self.is_demo_mode and not error:
            demo_msg = "🎮 Demo Mode Active: This system is configured for demonstration purposes using AI provider."
        elif error and "401" in error:
            demo_msg = "🔑 API Authentication Error: Invalid AI API key. Please update your .env file with a valid AI_API_KEY."
        elif error:
            demo_msg = f"⚠️ API Error: {error}. Running in fallback mode."
        else:
            demo_msg = "🔧 Demo Mode: No valid AI API key configured."

        # Generate contextual legal responses
        legal_responses = {
            "greeting": """Hello! I'm your Legal AI Assistant powered by AI, specializing in comprehensive legal document analysis.

I can help with:
• **Contract Review** - Identify risks, missing clauses, unfavorable terms
• **Immigration Forms** - Verify completeness, flag potential issues
• **Family Law** - Analyze agreements, calculate support, review orders
• **Criminal Defense** - Review charges, identify defenses, check procedures
• **Personal Injury** - Assess damages, review medical records, calculate values

My analysis includes risk assessment, action items, and specific recommendations tailored to your practice area.""",
            "analysis": """I provide comprehensive legal document analysis including:

📋 **Document Intelligence**
- Key party identification and role analysis
- Critical date and deadline extraction
- Financial obligation calculations
- Risk assessment (Low/Medium/High/Critical)

🔍 **Deep Legal Analysis**
- Missing standard clauses detection
- Ambiguous language identification
- Compliance verification
- Jurisdiction-specific requirements

📊 **Actionable Insights**
- Prioritized action items
- Specific modification recommendations
- Strategic considerations
- Next steps in legal process""",
            "documents": f"""I can see you have {len(documents)} document(s) ready for analysis:

{chr(10).join([f'📄 {doc.filename} - Status: {doc.processing_status}' for doc in documents[:5]])}

Once API access is configured, I'll provide:
- Comprehensive legal analysis with risk assessment
- Extracted key terms, dates, and parties
- Specific recommendations for your practice area
- Comparison analysis if multiple documents
- Action items prioritized by urgency""",
            "features": """My advanced legal analysis features include:

**Tier 1 - Document Analysis**
- Extract parties, dates, obligations
- Summarize key provisions
- Identify document type and purpose

**Tier 2 - Legal Intelligence**
- Risk assessment and scoring
- Missing clause detection
- Compliance verification
- Multi-document comparison

**Tier 3 - Enterprise Features**
- Custom legal templates
- Jurisdiction-specific analysis
- Practice area specialization
- Bulk document processing""",
        }

        # Smart response selection based on message content
        message_lower = message.lower()

        if any(word in message_lower for word in ["hello", "hi", "hey", "start"]):
            response = legal_responses["greeting"]
        elif any(
            word in message_lower for word in ["analyze", "analysis", "review", "check"]
        ):
            response = legal_responses["analysis"]
        elif any(
            word in message_lower
            for word in ["feature", "can you", "what do", "capabilities"]
        ):
            response = legal_responses["features"]
        elif documents:
            response = legal_responses["documents"]
        else:
            response = legal_responses["greeting"]

        # Add demo notice
        full_response = f"{demo_msg}\n\n{response}"

        # Mock structured data for demo
        mock_structured_data = {
            "summary": "Demo mode - Full analysis available with API key",
            "action_items": ["Configure AI API key", "Upload documents for analysis"],
            "key_findings": ["System ready for legal document processing"],
            "recommendations": ["Start with contract analysis for best results"],
        }

        # Mock risk assessment
        mock_risk = {
            "level": "low",
            "high_risk_indicators": 0,
            "medium_risk_indicators": 0,
            "recommendation": "Demo mode - Real risk assessment requires API access",
        }

        return {
            "answer": full_response,
            "sources": [
                {
                    "document_id": doc.id,
                    "document_name": doc.filename,
                    "relevance": "available",
                }
                for doc in documents[:3]
            ],
            "timestamp": datetime.utcnow(),
            "model": "demo-mode",
            "analysis_type": "demo",
            "structured_data": mock_structured_data,
            "risk_assessment": mock_risk,
            "extracted_entities": {
                "dates": ["Demo mode"],
                "monetary_amounts": [],
                "parties": [],
                "case_citations": [],
                "statutes": [],
            },
            "response_metrics": {
                "response_time_ms": 50,  # Simulated fast response
                "tokens_used": 0,  # No API tokens in demo mode
                "response_type": "demo_mode",
                "cost_saved": 0,
                "tokens_saved": 0,
            },
        }

    def _extract_sources(
        self, response: str, documents: List[Any]
    ) -> List[Dict[str, Any]]:
        """Enhanced source extraction with relevance scoring"""
        sources = []
        response_lower = response.lower()

        for doc in documents:
            relevance_score = 0
            relevance_type = "mentioned"

            # Check different ways document might be referenced
            doc_name_lower = doc.filename.lower()

            # Direct filename mention
            if doc_name_lower in response_lower:
                relevance_score += 3
                relevance_type = "directly_referenced"

            # Check if document content is quoted
            if doc.extracted_content and len(doc.extracted_content) > 100:
                # Check for unique phrases from document
                sample_phrase = doc.extracted_content[100:150].lower()
                if sample_phrase in response_lower:
                    relevance_score += 5
                    relevance_type = "content_quoted"

            # Check for document type references
            doc_type = doc.filename.split(".")[-1].lower()
            if (
                f"{doc_type} document" in response_lower
                or f"{doc_type} file" in response_lower
            ):
                relevance_score += 1

            if relevance_score > 0:
                sources.append(
                    {
                        "document_id": doc.id,
                        "document_name": doc.filename,
                        "relevance": relevance_type,
                        "relevance_score": relevance_score,
                    }
                )

        # Sort by relevance score
        sources.sort(key=lambda x: x["relevance_score"], reverse=True)

        return sources

    def _classify_query(self, message: str) -> str:
        """Classify the type of query for optimized processing"""
        message_lower = message.lower()

        # Check each query type pattern
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return query_type

        return "general"

    async def _search_metadata(
        self, query_type: str, message: str, documents: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """Search extracted metadata to answer queries without API calls"""

        results = []

        for doc in documents:
            # Check if document has legal_metadata
            if not hasattr(doc, "legal_metadata") or not doc.legal_metadata:
                continue

            try:
                metadata = json.loads(doc.legal_metadata)

                if query_type == "parties":
                    parties = metadata.get("parties", [])
                    if parties:
                        results.append({"document": doc.filename, "parties": parties})

                elif query_type == "dates":
                    dates = metadata.get("dates", [])
                    if dates:
                        results.append({"document": doc.filename, "dates": dates})

                elif query_type == "amounts":
                    amounts = metadata.get("monetary_amounts", [])
                    if amounts:
                        results.append({"document": doc.filename, "amounts": amounts})

                elif query_type == "obligations":
                    obligations = metadata.get("key_obligations", [])
                    if obligations:
                        results.append(
                            {"document": doc.filename, "obligations": obligations}
                        )

            except (json.JSONDecodeError, AttributeError):
                continue

        # If we found metadata, format a response
        if results:
            return self._format_metadata_response(query_type, results, message)

        return None

    def _format_metadata_response(
        self, query_type: str, results: List[Dict], original_query: str
    ) -> Dict[str, Any]:
        """Format metadata results into a structured response"""

        response_text = ""

        if query_type == "parties":
            response_text = "**🏢 Parties Identified:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for party in result["parties"]:
                    if isinstance(party, dict):
                        response_text += f"   • **{party.get('role', 'Party')}**: {party.get('name', 'Unknown')}\n"
                    else:
                        response_text += f"   • {party}\n"
                response_text += "\n"

        elif query_type == "dates":
            response_text = "**📅 Important Dates:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for date in result["dates"]:
                    if isinstance(date, dict):
                        response_text += f"   • **{date.get('event', 'Date')}**: {date.get('date', 'Unknown')}\n"
                    else:
                        response_text += f"   • {date}\n"
                response_text += "\n"

        elif query_type == "amounts":
            response_text = "**💰 Monetary Amounts:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for amount in result["amounts"]:
                    if isinstance(amount, dict):
                        response_text += f"   • **{amount.get('description', 'Amount')}**: {amount.get('amount', 'Unknown')}\n"
                    else:
                        response_text += f"   • {amount}\n"
                response_text += "\n"

        elif query_type == "obligations":
            response_text = "**📋 Key Obligations:**\n\n"
            for result in results:
                response_text += f"📄 **{result['document']}**\n"
                for obligation in result["obligations"]:
                    response_text += f"   • {obligation}\n"
                response_text += "\n"

        # Add a note about the source
        response_text += "\n---\n*📊 This information was extracted from document metadata for quick reference.*"

        return {
            "answer": response_text,  # Match expected format
            "sources": [],  # No specific document sources for metadata
            "metadata_used": True,
            "query_type": query_type,
            "documents_searched": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _find_relevant_sections(
        self, content: str, query_type: str, max_sections: int = 3
    ) -> str:
        """Find and extract relevant sections from content based on query type"""

        relevant_sections = []
        lines = content.split("\n")

        # Define keywords to search for based on query type
        keywords = {
            "parties": [
                "party",
                "parties",
                "plaintiff",
                "defendant",
                "buyer",
                "seller",
                "landlord",
                "tenant",
                "client",
                "contractor",
            ],
            "dates": [
                "date",
                "deadline",
                "due",
                "expire",
                "effective",
                "termination",
                "commencement",
            ],
            "amounts": [
                "amount",
                "payment",
                "price",
                "fee",
                "cost",
                "compensation",
                "salary",
                "$",
            ],
            "obligations": [
                "shall",
                "must",
                "obligation",
                "duty",
                "required",
                "responsible",
                "covenant",
                "undertake",
            ],
        }

        query_keywords = keywords.get(query_type, [])

        # Find lines containing relevant keywords
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in query_keywords):
                # Extract context (2 lines before and after)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                section = "\n".join(lines[start:end])

                # Avoid duplicates
                if section not in relevant_sections:
                    relevant_sections.append(section)

                if len(relevant_sections) >= max_sections:
                    break

        if relevant_sections:
            return "\n\n[...]\n\n".join(relevant_sections)

        return ""

    def _estimate_tokens_used(
        self, messages: List[Dict[str, str]], response: str
    ) -> int:
        """Estimate tokens used in API call"""
        # Rough estimation: 1 token ≈ 4 characters
        total_chars = 0

        # Count message tokens
        for msg in messages:
            total_chars += len(msg.get("content", ""))

        # Count response tokens
        total_chars += len(response)

        # Estimate tokens (1 token ≈ 4 characters on average)
        estimated_tokens = total_chars // 4

        return estimated_tokens

    def _estimate_tokens_saved(
        self, message: str, documents: List[Any], query_type: str
    ) -> int:
        """Estimate tokens saved by using metadata instead of full API call"""
        # Calculate what would have been sent to API
        tokens_that_would_be_used = 0

        # System prompt tokens
        tokens_that_would_be_used += (
            len(self.system_prompts.get("legal_assistant", "")) // 4
        )

        # Document context tokens
        for doc in documents:
            if doc.extracted_content:
                # Would send at least 3000 chars per document
                tokens_that_would_be_used += min(len(doc.extracted_content), 3000) // 4

        # Query tokens
        tokens_that_would_be_used += len(message) // 4

        # Expected response tokens (average legal response)
        tokens_that_would_be_used += 500  # Conservative estimate for response

        return tokens_that_would_be_used

    def _calculate_cost_saved(self, tokens_saved: int) -> float:
        """Calculate cost saved based on tokens saved"""
        # AI provider pricing (approximate):
        # Input: $0.14 per 1M tokens
        # Output: $0.28 per 1M tokens
        # Average: $0.21 per 1M tokens

        cost_per_million_tokens = 0.21
        cost_saved = (tokens_saved / 1_000_000) * cost_per_million_tokens

        return round(cost_saved, 6)  # Return in dollars with 6 decimal places
