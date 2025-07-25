# services/enhanced_document_processor.py - Enhanced document processing with MCP integration

import os
import re
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging

from services.document_processor import DocumentProcessor
from services.mcp_manager import MCPManager
from services.mcp_servers.court_system_mcp import CourtSystemMCPServer
from models import Document
from database import get_db

logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    """Processed document data"""

    id: str
    filename: str
    text: str
    detected_type: str
    page_count: Optional[int]
    summary: str
    created_at: datetime

    def dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "text": self.text,
            "detected_type": self.detected_type,
            "page_count": self.page_count,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EnhancedDocument:
    """Enhanced document with MCP data"""

    id: str
    filename: str
    text: str
    detected_type: str
    page_count: Optional[int]
    summary: str
    created_at: datetime
    mcp_enhancements: Dict[str, Any]


class EnhancedDocumentProcessor(DocumentProcessor):
    """Document processor enhanced with MCP integration"""

    def __init__(self, mcp_manager: MCPManager):
        super().__init__()
        self.mcp_manager = mcp_manager
        self.court_mcp = CourtSystemMCPServer()

        # Regex patterns for extraction
        self.case_citation_pattern = re.compile(
            r"(\d+)\s+([A-Z][a-z]+\.?\s*){1,3}\s*(\d+[a-z]?)\s*(?:\(\w+\.?\s*\d{4}\))?"
        )
        self.party_name_pattern = re.compile(
            r"(?:Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee)(?:s)?[\s:]+([A-Z][a-zA-Z\s&,.\'-]+?)(?:\s*,|\s+v\.|\s+vs\.|\n|$)"
        )
        self.deadline_pattern = re.compile(
            r"(?:within|before|by|no later than|must be filed by)\s+(\d+)\s+(days?|weeks?|months?)|"
            + r"(?:deadline|due date)(?:\s+is)?[\s:]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})"
        )

    async def process_document_with_mcp(
        self, document: Document, organization_id: str
    ) -> EnhancedDocument:
        """Process document with MCP enhancement"""

        # First, do standard processing
        logger.info(f"Processing document {document.id} with MCP enhancement")

        # Extract base information
        base_result = ProcessedDocument(
            id=document.id,
            filename=document.filename,
            text=document.extracted_content or "",
            detected_type=self._detect_document_type(document.extracted_content or ""),
            page_count=document.page_count,
            summary=document.summary or "",
            created_at=document.upload_timestamp,
        )

        # Then enhance with MCP data
        enhancements = await self._enhance_with_mcp(base_result, organization_id)

        # Update document with enhancements
        enhanced_metadata = json.loads(document.legal_metadata or "{}")
        enhanced_metadata["mcp_enhancements"] = enhancements
        enhanced_metadata["mcp_enhanced_at"] = datetime.utcnow().isoformat()

        db = next(get_db())
        document.legal_metadata = json.dumps(enhanced_metadata)
        db.commit()
        db.close()

        return EnhancedDocument(**base_result.dict(), mcp_enhancements=enhancements)

    async def _enhance_with_mcp(
        self, document: ProcessedDocument, organization_id: str
    ) -> Dict[str, Any]:
        """Enhance document with MCP data"""
        enhancements = {}

        # Run all enhancement tasks concurrently
        tasks = []

        # 1. Check if document is a court filing
        if self._is_court_document(document):
            tasks.append(self._enhance_court_filing(document))

        # 2. Extract and validate case references
        case_refs = self._extract_case_references(document.text)
        if case_refs:
            tasks.append(self._validate_case_citations(case_refs))

        # 3. Check for party names against conflicts
        parties = self._extract_party_names(document.text)
        if parties:
            tasks.append(self._check_party_conflicts(parties, organization_id))

        # 4. Identify deadlines mentioned in document
        deadline_refs = self._extract_deadline_references(document.text)
        if deadline_refs:
            tasks.append(self._interpret_deadlines(deadline_refs, document.created_at))

        # Execute all tasks
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            task_names = []
            if self._is_court_document(document):
                task_names.append("court_analysis")
            if case_refs:
                task_names.append("validated_citations")
            if parties:
                task_names.append("potential_conflicts")
            if deadline_refs:
                task_names.append("extracted_deadlines")

            for i, (name, result) in enumerate(zip(task_names, results)):
                if not isinstance(result, Exception):
                    enhancements[name] = result
                else:
                    logger.error(f"Enhancement task {name} failed: {str(result)}")
                    enhancements[name] = {"error": str(result)}

        return enhancements

    def _is_court_document(self, document: ProcessedDocument) -> bool:
        """Check if document is a court filing"""
        court_indicators = [
            "court",
            "judge",
            "docket",
            "case no",
            "plaintiff",
            "defendant",
            "motion",
            "complaint",
            "answer",
            "order",
            "judgment",
            "verdict",
            "filed",
            "civil action",
            "criminal case",
        ]

        text_lower = document.text.lower()
        score = sum(1 for indicator in court_indicators if indicator in text_lower)

        return score >= 3 or document.detected_type in [
            "motion",
            "complaint",
            "court_filing",
        ]

    def _detect_document_type(self, text: str) -> str:
        """Detect document type from content"""
        text_lower = text.lower()

        # Court documents
        if "complaint" in text_lower and "plaintiff" in text_lower:
            return "complaint"
        elif "motion" in text_lower and (
            "court" in text_lower or "judge" in text_lower
        ):
            return "motion"
        elif "answer" in text_lower and "defendant" in text_lower:
            return "answer"
        elif "order" in text_lower and "court" in text_lower:
            return "court_order"

        # Contracts
        elif "agreement" in text_lower and "parties" in text_lower:
            return "contract"
        elif "lease" in text_lower and "tenant" in text_lower:
            return "lease_agreement"

        # Other legal documents
        elif "will" in text_lower and "testament" in text_lower:
            return "will"
        elif "power of attorney" in text_lower:
            return "power_of_attorney"

        return "other"

    async def _enhance_court_filing(
        self, document: ProcessedDocument
    ) -> Dict[str, Any]:
        """Enhance court filing with MCP data"""
        try:
            # Detect jurisdiction from document
            jurisdiction = self._detect_jurisdiction(document.text)

            async with self.court_mcp:
                result = await self.court_mcp.query(
                    "analyze_filing",
                    {
                        "document_text": document.text[:5000],  # Limit text size
                        "document_type": document.detected_type,
                        "jurisdiction": jurisdiction,
                    },
                )

            return result.get("analysis", {})

        except Exception as e:
            logger.error(f"Court filing enhancement failed: {str(e)}")
            return {"error": str(e)}

    def _detect_jurisdiction(self, text: str) -> Dict[str, str]:
        """Detect jurisdiction from document text"""
        jurisdiction = {}

        # State detection
        state_patterns = {
            "OH": ["ohio", "hamilton county", "cuyahoga", "franklin county"],
            "KY": ["kentucky", "campbell county", "kenton county", "jefferson county"],
        }

        text_lower = text.lower()
        for state, patterns in state_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                jurisdiction["state"] = state
                break

        # Court level detection
        if "circuit court" in text_lower:
            jurisdiction["court_level"] = "circuit"
        elif "district court" in text_lower:
            jurisdiction["court_level"] = "district"
        elif "supreme court" in text_lower:
            jurisdiction["court_level"] = "supreme"

        return jurisdiction

    def _extract_case_references(self, text: str) -> List[str]:
        """Extract case citations from text"""
        citations = []

        # Find standard case citations
        matches = self.case_citation_pattern.findall(text)
        for match in matches:
            citation = " ".join(match).strip()
            if citation and len(citation) > 5:
                citations.append(citation)

        # Also look for case numbers
        case_number_pattern = re.compile(
            r"(?:Case No\.|No\.|Case Number)\s*:?\s*([A-Z0-9\-]+)"
        )
        case_numbers = case_number_pattern.findall(text)
        citations.extend(case_numbers)

        return list(set(citations))[:10]  # Limit to 10 citations

    async def _validate_case_citations(self, citations: List[str]) -> Dict[str, Any]:
        """Validate case citations using legal research MCP"""
        try:
            # Use court system MCP to validate citations
            validated = []

            for citation in citations:
                # Simple validation for now - could query legal research MCP
                validated.append(
                    {
                        "citation": citation,
                        "valid": bool(re.match(r"\d+\s+\w+\.?\s*\d+", citation)),
                        "type": (
                            "case_law"
                            if " v. " in citation or " vs. " in citation
                            else "case_number"
                        ),
                    }
                )

            return {"total_citations": len(citations), "validated": validated}

        except Exception as e:
            logger.error(f"Citation validation failed: {str(e)}")
            return {"error": str(e)}

    def _extract_party_names(self, text: str) -> List[Dict[str, str]]:
        """Extract party names from document"""
        parties = []

        # Extract from standard legal format
        matches = self.party_name_pattern.findall(text)

        for match in matches:
            party_name = match.strip().rstrip(",")
            if party_name and len(party_name) > 3:
                # Determine party type
                before_text = text[
                    max(0, text.find(party_name) - 20) : text.find(party_name)
                ]
                party_type = "unknown"

                if "plaintiff" in before_text.lower():
                    party_type = "plaintiff"
                elif "defendant" in before_text.lower():
                    party_type = "defendant"
                elif "petitioner" in before_text.lower():
                    party_type = "petitioner"
                elif "respondent" in before_text.lower():
                    party_type = "respondent"

                parties.append({"name": party_name, "type": party_type})

        # Also check case caption
        caption_pattern = re.compile(
            r"([A-Z][A-Za-z\s&,.\'-]+?)\s+v\.?\s+([A-Z][A-Za-z\s&,.\'-]+?)(?:\s*\n|$)"
        )
        caption_matches = caption_pattern.findall(
            text[:1000]
        )  # Check first part of document

        for plaintiff, defendant in caption_matches:
            parties.extend(
                [
                    {"name": plaintiff.strip(), "type": "plaintiff"},
                    {"name": defendant.strip(), "type": "defendant"},
                ]
            )

        # Deduplicate
        seen = set()
        unique_parties = []
        for party in parties:
            key = (party["name"].lower(), party["type"])
            if key not in seen:
                seen.add(key)
                unique_parties.append(party)

        return unique_parties[:10]  # Limit to 10 parties

    async def _check_party_conflicts(
        self, parties: List[Dict[str, str]], organization_id: str
    ) -> Dict[str, Any]:
        """Check parties for conflicts of interest"""
        try:
            # Extract just the names for conflict checking
            party_names = [p["name"] for p in parties]

            # This would normally query a client database MCP
            # For now, simulate conflict checking
            conflicts = []

            # Simulate checking against existing clients
            for party in parties:
                # In real implementation, would query client database
                if "acme" in party["name"].lower():  # Example conflict
                    conflicts.append(
                        {
                            "party_name": party["name"],
                            "party_type": party["type"],
                            "conflict_type": "existing_client",
                            "conflict_matter": "ACME Corp v. Smith (Case No. 2023-CV-1234)",
                        }
                    )

            return {
                "parties_checked": len(parties),
                "conflicts_found": len(conflicts),
                "conflicts": conflicts,
            }

        except Exception as e:
            logger.error(f"Conflict checking failed: {str(e)}")
            return {"error": str(e)}

    def _extract_deadline_references(self, text: str) -> List[Dict[str, str]]:
        """Extract deadline references from text"""
        deadlines = []

        matches = self.deadline_pattern.findall(text)

        for match in matches:
            if match[0] and match[1]:  # Relative deadline (e.g., "within 30 days")
                deadlines.append(
                    {
                        "type": "relative",
                        "value": match[0],
                        "unit": match[1],
                        "text": f"{match[0]} {match[1]}",
                    }
                )
            elif match[2]:  # Absolute deadline (e.g., "January 15, 2024")
                deadlines.append(
                    {"type": "absolute", "date": match[2], "text": match[2]}
                )

        # Also look for specific deadline keywords
        specific_patterns = [
            r"statute of limitations[:\s]+([^\n.]+)",
            r"response due[:\s]+([^\n.]+)",
            r"discovery deadline[:\s]+([^\n.]+)",
        ]

        for pattern in specific_patterns:
            specific_matches = re.findall(pattern, text, re.IGNORECASE)
            for match in specific_matches:
                deadlines.append({"type": "specific", "text": match.strip()})

        return deadlines[:10]  # Limit to 10 deadlines

    async def _interpret_deadlines(
        self, deadline_refs: List[Dict[str, str]], document_date: datetime
    ) -> Dict[str, Any]:
        """Interpret deadline references using court system MCP"""
        try:
            interpreted_deadlines = []

            async with self.court_mcp:
                for ref in deadline_refs:
                    if ref["type"] == "relative":
                        # Calculate actual date
                        days = int(ref["value"])
                        if "week" in ref["unit"]:
                            days *= 7
                        elif "month" in ref["unit"]:
                            days *= 30

                        deadline_date = document_date + timedelta(days=days)

                        interpreted_deadlines.append(
                            {
                                "original_text": ref["text"],
                                "calculated_date": deadline_date.strftime("%Y-%m-%d"),
                                "type": "calculated",
                                "confidence": "high",
                            }
                        )

                    elif ref["type"] == "absolute":
                        interpreted_deadlines.append(
                            {
                                "original_text": ref["text"],
                                "parsed_date": ref["date"],
                                "type": "explicit",
                                "confidence": "high",
                            }
                        )

                    else:
                        interpreted_deadlines.append(
                            {
                                "original_text": ref["text"],
                                "type": "mentioned",
                                "confidence": "low",
                            }
                        )

            return {
                "deadlines_found": len(deadline_refs),
                "interpreted": interpreted_deadlines,
            }

        except Exception as e:
            logger.error(f"Deadline interpretation failed: {str(e)}")
            return {"error": str(e)}


class MCPDocumentClassifier:
    """Smart document classifier using MCP knowledge"""

    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.court_mcp = CourtSystemMCPServer()

    async def classify_with_court_knowledge(
        self, document_text: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify document using court-specific knowledge"""

        # Query MCP for court-specific document types
        jurisdiction = metadata.get("jurisdiction", {})

        court_types = []
        if jurisdiction:
            async with self.court_mcp:
                types_result = await self.court_mcp.query(
                    "get_document_types", {"jurisdiction": jurisdiction}
                )
                court_types = types_result.get("document_types", [])

        # Perform classification
        classification = await self._ai_classify(
            document_text, valid_types=court_types or self._get_default_types()
        )

        return classification

    async def _ai_classify(
        self, document_text: str, valid_types: List[str]
    ) -> Dict[str, Any]:
        """Use AI to classify document"""
        # This would use the AI service for classification
        # For now, use pattern matching

        text_lower = document_text.lower()
        scores = {}

        # Score each document type
        type_keywords = {
            "complaint": ["plaintiff", "defendant", "cause of action", "wherefore"],
            "motion": ["motion", "movant", "respectfully", "court"],
            "order": ["ordered", "adjudged", "decreed", "court finds"],
            "contract": ["agreement", "parties", "whereas", "consideration"],
            "discovery": ["interrogatories", "request for production", "deposition"],
            "brief": ["argument", "authority", "conclusion", "respectfully submitted"],
        }

        for doc_type, keywords in type_keywords.items():
            if doc_type in valid_types or not valid_types:
                score = sum(1 for keyword in keywords if keyword in text_lower)
                scores[doc_type] = score

        # Get highest scoring type
        if scores:
            best_type = max(scores, key=scores.get)
            confidence = min(scores[best_type] / 4.0, 1.0)  # Normalize confidence
        else:
            best_type = "other"
            confidence = 0.0

        return {
            "document_type": best_type,
            "confidence": confidence,
            "scores": scores,
            "valid_types_used": valid_types,
        }

    def _get_default_types(self) -> List[str]:
        """Get default document types"""
        return [
            "complaint",
            "answer",
            "motion",
            "brief",
            "order",
            "contract",
            "lease",
            "discovery",
            "notice",
            "other",
        ]


class DocumentSearchService:
    """Enhanced document search with MCP context"""

    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager

    async def search_with_mcp_context(
        self, query: str, filters: Dict[str, Any], organization_id: str
    ) -> Dict[str, Any]:
        """Search documents with MCP enhancement"""

        # Parse query for legal concepts
        legal_concepts = await self._extract_legal_concepts(query)

        # Enhance query with MCP data
        enhanced_query = query
        additional_terms = []

        if legal_concepts.get("case_citations"):
            # Get related cases from legal research MCP
            # For now, just add citation terms
            additional_terms.extend(legal_concepts["case_citations"])

        if legal_concepts.get("legal_terms"):
            # Expand with synonyms or related terms
            for term in legal_concepts["legal_terms"]:
                # Would query legal terminology MCP
                if term == "negligence":
                    additional_terms.extend(["breach of duty", "tort", "liability"])
                elif term == "contract":
                    additional_terms.extend(["agreement", "covenant", "terms"])

        # Perform enhanced search
        results = await self._search_documents(
            enhanced_query, additional_terms, filters, organization_id
        )

        # Annotate results with MCP data
        for result in results["documents"]:
            result["mcp_annotations"] = await self._annotate_with_mcp(result)

        return results

    async def _extract_legal_concepts(self, query: str) -> Dict[str, Any]:
        """Extract legal concepts from search query"""
        concepts = {"case_citations": [], "legal_terms": [], "parties": [], "dates": []}

        # Extract case citations
        citation_pattern = re.compile(r"(\d+)\s+([A-Z][a-z]+\.?\s*){1,3}\s*(\d+)")
        citations = citation_pattern.findall(query)
        concepts["case_citations"] = [" ".join(c) for c in citations]

        # Extract legal terms
        legal_terms = [
            "negligence",
            "contract",
            "breach",
            "liability",
            "damages",
            "plaintiff",
            "defendant",
            "motion",
            "discovery",
            "jurisdiction",
        ]
        query_lower = query.lower()
        concepts["legal_terms"] = [term for term in legal_terms if term in query_lower]

        # Extract party names (simplified)
        party_pattern = re.compile(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        )
        party_matches = party_pattern.findall(query)
        for plaintiff, defendant in party_matches:
            concepts["parties"].extend([plaintiff, defendant])

        return concepts

    async def _search_documents(
        self,
        query: str,
        additional_terms: List[str],
        filters: Dict[str, Any],
        organization_id: str,
    ) -> Dict[str, Any]:
        """Perform document search"""
        db = next(get_db())

        try:
            # Build search query
            search_query = db.query(Document).filter(
                Document.organization_id == organization_id
            )

            # Apply filters
            if filters.get("document_type"):
                search_query = search_query.filter(
                    Document.legal_metadata.contains(filters["document_type"])
                )

            if filters.get("date_from"):
                search_query = search_query.filter(
                    Document.upload_timestamp >= filters["date_from"]
                )

            if filters.get("date_to"):
                search_query = search_query.filter(
                    Document.upload_timestamp <= filters["date_to"]
                )

            # Text search (simplified - would use full-text search in production)
            if query:
                search_terms = [query] + additional_terms
                conditions = []
                for term in search_terms:
                    conditions.append(Document.extracted_content.ilike(f"%{term}%"))
                    conditions.append(Document.summary.ilike(f"%{term}%"))

                from sqlalchemy import or_

                search_query = search_query.filter(or_(*conditions))

            # Execute search
            documents = search_query.limit(50).all()

            return {
                "query": query,
                "enhanced_terms": additional_terms,
                "total_results": len(documents),
                "documents": [self._document_to_dict(doc) for doc in documents],
            }

        finally:
            db.close()

    def _document_to_dict(self, document: Document) -> Dict[str, Any]:
        """Convert document to dictionary"""
        return {
            "id": document.id,
            "filename": document.filename,
            "upload_date": document.upload_timestamp.isoformat(),
            "summary": document.summary,
            "status": document.processing_status,
            "metadata": json.loads(document.legal_metadata or "{}"),
        }

    async def _annotate_with_mcp(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate document with MCP data"""
        annotations = {}

        # Add relevance score based on MCP data
        annotations["relevance_score"] = 0.85  # Would calculate based on MCP data

        # Add related documents
        annotations["related_documents"] = []  # Would query for related docs

        # Add jurisdiction info if available
        metadata = document.get("metadata", {})
        if metadata.get("jurisdiction"):
            annotations["jurisdiction_info"] = metadata["jurisdiction"]

        return annotations
