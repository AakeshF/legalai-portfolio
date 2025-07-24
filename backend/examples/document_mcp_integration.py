#!/usr/bin/env python3
"""
Example: Using Enhanced Document Processing with MCP Integration
"""

import asyncio
import json
from datetime import datetime
from services.enhanced_document_processor import (
    EnhancedDocumentProcessor,
    MCPDocumentClassifier,
    DocumentSearchService
)
from services.mcp_manager import MCPManager
from models import Document
from database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_document_enhancement():
    """Demonstrate document enhancement with MCP"""
    
    # Initialize services
    mcp_manager = MCPManager()
    processor = EnhancedDocumentProcessor(mcp_manager)
    classifier = MCPDocumentClassifier(mcp_manager)
    search_service = DocumentSearchService(mcp_manager)
    
    # Sample document text (court filing)
    sample_document_text = """
    IN THE CIRCUIT COURT OF HAMILTON COUNTY, OHIO
    CIVIL DIVISION
    
    JOHN SMITH,
        Plaintiff,
    
    v.                                      Case No. A2024001234
    
    ACME CORPORATION,
        Defendant.
    
    COMPLAINT FOR NEGLIGENCE
    
    NOW COMES the Plaintiff, John Smith, by and through undersigned counsel,
    and for his Complaint against Defendant states as follows:
    
    1. This is an action for damages in excess of $25,000.
    
    2. Plaintiff is a resident of Hamilton County, Ohio.
    
    3. Defendant ACME Corporation is a corporation organized under the laws
    of Ohio with its principal place of business in Hamilton County.
    
    4. On January 15, 2024, Plaintiff was lawfully present at Defendant's
    premises located at 123 Main Street, Cincinnati, Ohio.
    
    5. Defendant negligently maintained its premises, creating a dangerous
    condition that caused Plaintiff to slip and fall.
    
    6. As a direct and proximate result of Defendant's negligence, Plaintiff
    suffered severe injuries including a fractured hip.
    
    WHEREFORE, Plaintiff demands judgment against Defendant for compensatory
    damages in excess of $25,000, costs, and such other relief as the Court
    deems just and proper.
    
    Respectfully submitted,
    
    /s/ Jane Attorney
    Jane Attorney (0012345)
    Attorney for Plaintiff
    456 Legal Street
    Cincinnati, OH 45202
    (XXX) XXX-XXXX
    [email@example.com]
    
    JURY DEMAND
    Plaintiff hereby demands a trial by jury on all issues so triable.
    """
    
    # Create a mock document
    db = SessionLocal()
    
    try:
        # 1. Document Classification Demo
        logger.info("=== Document Classification Demo ===")
        
        classification = await classifier.classify_with_court_knowledge(
            document_text=sample_document_text,
            metadata={"jurisdiction": {"state": "OH", "county": "Hamilton"}}
        )
        
        logger.info(f"Document Type: {classification['document_type']} "
                   f"(Confidence: {classification['confidence']:.2%})")
        logger.info(f"Classification Scores: {classification['scores']}")
        
        # 2. Document Enhancement Demo
        logger.info("\n=== Document Enhancement Demo ===")
        
        # Create a mock document for enhancement
        mock_doc = Document(
            id="test-doc-123",
            filename="smith_v_acme_complaint.pdf",
            organization_id="test-org",
            extracted_content=sample_document_text,
            page_count=3,
            summary="Complaint for negligence filed by John Smith against ACME Corporation",
            processing_status="completed",
            upload_timestamp=datetime.utcnow()
        )
        
        # Enhance the document
        from services.enhanced_document_processor import ProcessedDocument
        processed_doc = ProcessedDocument(
            id=mock_doc.id,
            filename=mock_doc.filename,
            text=mock_doc.extracted_content,
            detected_type="complaint",
            page_count=mock_doc.page_count,
            summary=mock_doc.summary,
            created_at=mock_doc.upload_timestamp
        )
        
        enhancements = await processor._enhance_with_mcp(processed_doc, "test-org")
        
        logger.info("MCP Enhancements:")
        
        # Court Analysis
        if "court_analysis" in enhancements:
            logger.info(f"\n📊 Court Analysis: {json.dumps(enhancements['court_analysis'], indent=2)}")
            
        # Validated Citations
        if "validated_citations" in enhancements:
            citations = enhancements["validated_citations"]
            logger.info(f"\n📚 Found {citations['total_citations']} citations")
            for cite in citations.get("validated", [])[:3]:
                logger.info(f"  - {cite['citation']} ({cite['type']})")
                
        # Conflict Check
        if "potential_conflicts" in enhancements:
            conflicts = enhancements["potential_conflicts"]
            logger.info(f"\n⚠️  Conflict Check: {conflicts['parties_checked']} parties checked")
            if conflicts["conflicts_found"] > 0:
                logger.warning(f"  Found {conflicts['conflicts_found']} potential conflicts!")
                for conflict in conflicts["conflicts"]:
                    logger.warning(f"  - {conflict['party_name']}: {conflict['conflict_type']}")
                    
        # Extracted Deadlines
        if "extracted_deadlines" in enhancements:
            deadlines = enhancements["extracted_deadlines"]
            logger.info(f"\n📅 Found {deadlines['deadlines_found']} deadline references")
            for deadline in deadlines.get("interpreted", [])[:3]:
                logger.info(f"  - {deadline['original_text']} → {deadline.get('calculated_date', 'TBD')}")
                
        # 3. Smart Search Demo
        logger.info("\n=== Smart Search Demo ===")
        
        # Example search queries
        search_queries = [
            "negligence slip and fall 25000",
            "Smith v. ACME",
            "Hamilton County premises liability"
        ]
        
        for query in search_queries:
            logger.info(f"\nSearching for: '{query}'")
            
            # Extract legal concepts
            concepts = await search_service._extract_legal_concepts(query)
            logger.info(f"Legal concepts extracted:")
            logger.info(f"  - Case citations: {concepts['case_citations']}")
            logger.info(f"  - Legal terms: {concepts['legal_terms']}")
            logger.info(f"  - Parties: {concepts['parties']}")
            
        # 4. Party Extraction Demo
        logger.info("\n=== Party Extraction Demo ===")
        
        parties = processor._extract_party_names(sample_document_text)
        logger.info(f"Extracted {len(parties)} parties:")
        for party in parties:
            logger.info(f"  - {party['name']} ({party['type']})")
            
        # 5. Deadline Extraction Demo
        logger.info("\n=== Deadline Extraction Demo ===")
        
        # Add some deadline text
        deadline_text = """
        Defendant shall file an Answer within 28 days of service.
        Discovery must be completed by March 15, 2024.
        All dispositive motions must be filed no later than 30 days before trial.
        The statute of limitations for this claim is 2 years.
        """
        
        deadline_refs = processor._extract_deadline_references(deadline_text)
        logger.info(f"Extracted {len(deadline_refs)} deadline references:")
        for ref in deadline_refs:
            logger.info(f"  - {ref['text']} (Type: {ref['type']})")
            
        # 6. Jurisdiction Detection Demo
        logger.info("\n=== Jurisdiction Detection Demo ===")
        
        jurisdiction = processor._detect_jurisdiction(sample_document_text)
        logger.info(f"Detected jurisdiction: {jurisdiction}")
        
        # 7. Document Type Detection
        logger.info("\n=== Document Type Detection ===")
        
        doc_types = [
            ("This is a complaint filed by plaintiff...", "complaint"),
            ("Motion to dismiss pursuant to Rule 12(b)(6)...", "motion"),
            ("This lease agreement is entered into...", "lease_agreement"),
            ("Last will and testament of John Doe...", "will")
        ]
        
        for text, expected in doc_types:
            detected = processor._detect_document_type(text)
            logger.info(f"  '{text[:30]}...' → {detected} (expected: {expected})")
            
    finally:
        db.close()

async def demo_bulk_enhancement():
    """Demonstrate bulk document enhancement"""
    logger.info("\n=== Bulk Enhancement Demo ===")
    
    # Simulate queueing documents for enhancement
    from background_tasks import queue_document_enhancement
    
    document_ids = ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5"]
    organization_id = "test-org"
    
    logger.info(f"Queueing {len(document_ids)} documents for enhancement...")
    queue_document_enhancement(document_ids, organization_id)
    
    logger.info("Documents queued successfully!")
    logger.info("In production, these would be processed in the background")

async def demo_conflict_scenarios():
    """Demonstrate various conflict checking scenarios"""
    logger.info("\n=== Conflict Checking Scenarios ===")
    
    processor = EnhancedDocumentProcessor(MCPManager())
    
    # Test different party configurations
    test_cases = [
        {
            "parties": [
                {"name": "ACME Corporation", "type": "defendant"},
                {"name": "John Smith", "type": "plaintiff"}
            ],
            "description": "ACME as defendant (potential conflict)"
        },
        {
            "parties": [
                {"name": "Jane Doe", "type": "plaintiff"},
                {"name": "XYZ Company", "type": "defendant"}
            ],
            "description": "No known conflicts"
        },
        {
            "parties": [
                {"name": "Smith & Associates", "type": "plaintiff"},
                {"name": "ACME Industries", "type": "defendant"}
            ],
            "description": "Related entity conflict check"
        }
    ]
    
    for test in test_cases:
        logger.info(f"\nTesting: {test['description']}")
        result = await processor._check_party_conflicts(
            test["parties"],
            "test-org"
        )
        
        if result["conflicts_found"] > 0:
            logger.warning(f"  ⚠️  Found conflicts!")
        else:
            logger.info(f"  ✓ No conflicts found")

if __name__ == "__main__":
    # Run demonstrations
    asyncio.run(demo_document_enhancement())
    asyncio.run(demo_bulk_enhancement())
    asyncio.run(demo_conflict_scenarios())