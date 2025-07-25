# services/ai_service_with_mcp.py - AI Service integrated with MCP Manager
import os
import httpx
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
import asyncio

from services.ollama_service import (
    OllamaService as AIService,
    LegalDocumentType,
    RiskLevel,
)
from services.mcp_manager_enhanced import EnhancedMCPManager, MCPServerType
from models import User, Document
from audit_logger import AuditLogger
from config import Settings

# Load environment variables
load_dotenv()


class MCPEnhancedAIService(AIService):
    """AI Service enhanced with MCP context enrichment"""

    def __init__(self, config: Settings, audit_logger: AuditLogger):
        super().__init__()
        self.config = config
        self.audit_logger = audit_logger
        self.mcp_manager = EnhancedMCPManager(config, audit_logger)

        # Start health monitoring
        asyncio.create_task(self.mcp_manager.start_health_monitoring())

    async def analyze_document_with_context(
        self,
        content: str,
        filename: str,
        document: Document,
        user: User,
        include_mcp_context: bool = True,
    ) -> Dict[str, Any]:
        """Analyze document with MCP context enrichment"""

        # First, perform standard analysis
        base_analysis = await self.analyze_document(content, filename)

        if not include_mcp_context or self.demo_mode:
            return base_analysis

        try:
            # Enrich with MCP context
            mcp_context = await self.mcp_manager.enrich_document_context(document, user)

            # If we have enrichment data, enhance the analysis
            if mcp_context.get("enrichments"):
                enhanced_analysis = await self._enhance_with_mcp_data(
                    base_analysis, mcp_context["enrichments"], content, user
                )

                # Add metadata about enrichment
                enhanced_analysis["mcp_enriched"] = True
                enhanced_analysis["enrichment_sources"] = list(
                    mcp_context["enrichments"].keys()
                )

                return enhanced_analysis

        except Exception as e:
            print(f"⚠️ MCP enrichment failed: {str(e)}")
            # Fall back to base analysis

        return base_analysis

    async def _enhance_with_mcp_data(
        self,
        base_analysis: Dict[str, Any],
        enrichments: Dict[str, Any],
        content: str,
        user: User,
    ) -> Dict[str, Any]:
        """Enhance analysis with MCP-sourced data"""

        enhanced = base_analysis.copy()

        # Add court case information if available
        if "court_cases" in enrichments:
            enhanced["court_context"] = self._process_court_data(
                enrichments["court_cases"]
            )

            # Update risk assessment based on court data
            if enhanced["court_context"].get("pending_deadlines"):
                enhanced["risk_assessment"]["level"] = "high"
                enhanced["risk_assessment"]["court_deadlines"] = True

        # Add client information if available
        if "clients" in enrichments:
            enhanced["client_context"] = self._process_client_data(
                enrichments["clients"]
            )

            # Add client-specific recommendations
            if enhanced["client_context"].get("client_history"):
                enhanced["recommendations"].append(
                    f"Review client history: {len(enhanced['client_context']['client_history'])} related matters found"
                )

        # Add legal research if available
        if "research" in enrichments:
            enhanced["legal_research"] = self._process_research_data(
                enrichments["research"]
            )

            # Add research-based insights
            if enhanced["legal_research"].get("relevant_cases"):
                enhanced["insights"]["precedent_analysis"] = {
                    "relevant_cases_found": len(
                        enhanced["legal_research"]["relevant_cases"]
                    ),
                    "jurisdictions": enhanced["legal_research"].get(
                        "jurisdictions", []
                    ),
                }

        # Re-analyze with enriched context if significant data was added
        if any(k in enrichments for k in ["court_cases", "clients", "research"]):
            enhanced_prompt = self._build_enriched_prompt(content, enrichments)

            try:
                # Get enhanced analysis from AI with additional context
                enhanced_response = await self._make_api_request(
                    self.system_prompts["legal_assistant"], enhanced_prompt
                )

                if enhanced_response:
                    # Merge enhanced insights
                    enhanced["enhanced_analysis"] = enhanced_response
                    enhanced["insights"]["mcp_enhanced"] = True

            except Exception as e:
                print(f"⚠️ Enhanced analysis failed: {str(e)}")

        return enhanced

    def _build_enriched_prompt(self, content: str, enrichments: Dict[str, Any]) -> str:
        """Build an enriched prompt with MCP context"""

        prompt = f"Analyze this document with the following additional context:\n\n"
        prompt += f"Document Content:\n{content[:3000]}...\n\n"

        if "court_cases" in enrichments:
            prompt += "Related Court Cases:\n"
            for case in enrichments["court_cases"][:3]:  # Limit to 3 cases
                prompt += f"- {case.get('case_name', 'Unknown')} ({case.get('case_number', 'N/A')})\n"
                prompt += f"  Status: {case.get('status', 'Unknown')}\n"
                if case.get("next_deadline"):
                    prompt += f"  Next Deadline: {case['next_deadline']}\n"
            prompt += "\n"

        if "clients" in enrichments:
            prompt += "Client Information:\n"
            client_data = enrichments["clients"]
            if isinstance(client_data, list) and client_data:
                client = client_data[0]  # Primary client
                prompt += f"- Name: {client.get('name', 'Unknown')}\n"
                prompt += f"- Type: {client.get('client_type', 'Unknown')}\n"
                prompt += f"- Active Matters: {client.get('active_matters', 0)}\n"
            prompt += "\n"

        if "research" in enrichments:
            prompt += "Relevant Legal Research:\n"
            research = enrichments["research"]
            if research.get("relevant_cases"):
                prompt += f"- Found {len(research['relevant_cases'])} relevant cases\n"
                prompt += f"- Key precedent: {research.get('key_precedent', 'None identified')}\n"
            prompt += "\n"

        prompt += """
Please provide an enhanced analysis considering this additional context. 
Focus on how the external information impacts the document's interpretation, 
risks, and recommended actions."""

        return prompt

    def _process_court_data(self, court_data: Any) -> Dict[str, Any]:
        """Process court data from MCP"""
        processed = {"cases": [], "pending_deadlines": [], "filing_requirements": []}

        if isinstance(court_data, list):
            for case in court_data:
                case_info = {
                    "case_number": case.get("case_number"),
                    "case_name": case.get("case_name"),
                    "status": case.get("status"),
                    "court": case.get("court_name"),
                    "judge": case.get("judge_name"),
                }
                processed["cases"].append(case_info)

                # Extract deadlines
                if case.get("deadlines"):
                    for deadline in case["deadlines"]:
                        if deadline.get("status") == "pending":
                            processed["pending_deadlines"].append(
                                {
                                    "case": case_info["case_number"],
                                    "type": deadline.get("type"),
                                    "date": deadline.get("date"),
                                    "description": deadline.get("description"),
                                }
                            )

        return processed

    def _process_client_data(self, client_data: Any) -> Dict[str, Any]:
        """Process client data from MCP"""
        processed = {"client_info": {}, "client_history": [], "related_matters": []}

        if isinstance(client_data, list) and client_data:
            # Process primary client
            primary_client = client_data[0]
            processed["client_info"] = {
                "name": primary_client.get("name"),
                "type": primary_client.get("client_type"),
                "id": primary_client.get("client_id"),
                "since": primary_client.get("client_since"),
            }

            # Process matters
            if primary_client.get("matters"):
                for matter in primary_client["matters"]:
                    processed["related_matters"].append(
                        {
                            "matter_id": matter.get("id"),
                            "type": matter.get("matter_type"),
                            "status": matter.get("status"),
                            "opened": matter.get("date_opened"),
                        }
                    )

        return processed

    def _process_research_data(self, research_data: Any) -> Dict[str, Any]:
        """Process legal research data from MCP"""
        processed = {
            "relevant_cases": [],
            "statutes": [],
            "jurisdictions": set(),
            "key_precedent": None,
        }

        if research_data.get("cases"):
            for case in research_data["cases"][:10]:  # Limit to top 10
                case_info = {
                    "citation": case.get("citation"),
                    "name": case.get("case_name"),
                    "year": case.get("year"),
                    "court": case.get("court"),
                    "relevance_score": case.get("relevance_score", 0),
                    "summary": case.get("summary", "")[:200],  # Truncate summary
                }
                processed["relevant_cases"].append(case_info)

                if case.get("jurisdiction"):
                    processed["jurisdictions"].add(case["jurisdiction"])

                # Identify key precedent (highest relevance)
                if (
                    not processed["key_precedent"]
                    or case_info["relevance_score"]
                    > processed["key_precedent"]["relevance_score"]
                ):
                    processed["key_precedent"] = case_info

        # Convert set to list for JSON serialization
        processed["jurisdictions"] = list(processed["jurisdictions"])

        return processed

    async def chat_with_mcp_context(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        documents: List[Any],
        user: User,
    ) -> str:
        """Process chat message with MCP context"""

        # Check if message references legal entities
        entities = self._extract_legal_entities(message)

        # Gather relevant MCP context
        mcp_context = {}

        if entities.get("case_numbers"):
            for case_num in entities["case_numbers"]:
                court_data = await self.mcp_manager.query_legal_mcp(
                    MCPServerType.COURT_SYSTEM,
                    "get_case_details",
                    {"case_id": case_num},
                    user,
                )
                if court_data.success:
                    mcp_context[f"case_{case_num}"] = court_data.data

        if entities.get("client_names"):
            for client_name in entities["client_names"]:
                client_data = await self.mcp_manager.query_legal_mcp(
                    MCPServerType.CLIENT_DATABASE,
                    "search_clients",
                    {"name": client_name},
                    user,
                )
                if client_data.success:
                    mcp_context[f"client_{client_name}"] = client_data.data

        # Build enhanced context
        enhanced_context = self._build_chat_context(chat_history, documents)

        if mcp_context:
            enhanced_context += "\n\nAdditional MCP Context:\n"
            enhanced_context += json.dumps(mcp_context, indent=2)[:2000]  # Limit size

        # Process with AI
        return await self._process_chat_message(message, enhanced_context)

    def _extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract legal entities from text"""
        entities = {"case_numbers": [], "client_names": [], "statutes": []}

        # Extract case numbers (various formats)
        case_patterns = [
            r"\b\d{4}-[A-Z]{2}-\d{4,6}\b",  # 2024-CV-12345
            r"\b[A-Z]{2}\d{4,6}\b",  # CV12345
            r"\b\d{2}-\d{4,6}\b",  # 24-12345
        ]

        for pattern in case_patterns:
            matches = re.findall(pattern, text)
            entities["case_numbers"].extend(matches)

        # Extract statute references
        statute_pattern = r"\b\d+\s+U\.S\.C\.\s+§\s*\d+\b|\b\d+\s+C\.F\.R\.\s+§\s*\d+\b"
        entities["statutes"] = re.findall(statute_pattern, text)

        # Client names would require more sophisticated NER
        # For now, look for quoted company names
        client_pattern = (
            r'"([A-Z][A-Za-z\s&,.\'-]+(?:Inc\.|LLC|Corp\.|Company|Co\.|Ltd\.))"'
        )
        entities["client_names"] = re.findall(client_pattern, text)

        return entities

    async def cleanup(self):
        """Clean up resources"""
        await self.mcp_manager.stop_health_monitoring()
        # Disconnect all MCP servers
        for server_type in list(self.mcp_manager.servers.keys()):
            await self.mcp_manager.disconnect_server(server_type)
