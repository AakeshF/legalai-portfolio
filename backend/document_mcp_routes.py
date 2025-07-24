# document_mcp_routes.py - API endpoints for document MCP operations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from database import get_db
from models import Document, User
from services.enhanced_document_processor import (
    EnhancedDocumentProcessor,
    MCPDocumentClassifier,
    DocumentSearchService
)
from services.mcp_manager import MCPManager
from auth_middleware import get_current_user, get_current_organization
from models import Organization
from schemas import (
    DocumentMCPEnhanceRequest,
    DocumentMCPEnhanceResponse,
    DocumentClassifyRequest,
    DocumentClassifyResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    BulkEnhanceRequest,
    BulkEnhanceResponse,
    MCPDataResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["document-mcp"])
security = HTTPBearer()

# Initialize services
mcp_manager = MCPManager()
enhanced_processor = EnhancedDocumentProcessor(mcp_manager)
classifier = MCPDocumentClassifier(mcp_manager)
search_service = DocumentSearchService(mcp_manager)

@router.post("/{document_id}/enhance-with-mcp", response_model=DocumentMCPEnhanceResponse)
async def enhance_document_with_mcp(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Manually trigger MCP enhancement for a document"""
    organization_id = current_org.id
    try:
        # Get document with organization check
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.organization_id == organization_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
            
        if document.processing_status != "completed":
            raise HTTPException(
                status_code=400,
                detail="Document must be fully processed before MCP enhancement"
            )
            
        # Check if already enhanced
        metadata = json.loads(document.legal_metadata or "{}")
        if metadata.get("mcp_enhanced_at"):
            last_enhanced = datetime.fromisoformat(metadata["mcp_enhanced_at"])
            # Allow re-enhancement after 24 hours
            if (datetime.utcnow() - last_enhanced).total_seconds() < 86400:
                return DocumentMCPEnhanceResponse(
                    document_id=document_id,
                    status="already_enhanced",
                    message=f"Document was enhanced at {last_enhanced.isoformat()}",
                    enhancements=metadata.get("mcp_enhancements", {})
                )
                
        # Perform enhancement
        logger.info(f"Starting MCP enhancement for document {document_id}")
        enhanced_doc = await enhanced_processor.process_document_with_mcp(
            document,
            organization_id
        )
        
        return DocumentMCPEnhanceResponse(
            document_id=document_id,
            status="success",
            message="Document enhanced successfully",
            enhancements=enhanced_doc.mcp_enhancements
        )
        
    except Exception as e:
        logger.error(f"Error enhancing document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/mcp-data", response_model=MCPDataResponse)
async def get_document_mcp_data(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Get all MCP enhancements for a document"""
    organization_id = current_org.id
    # Get document with organization check
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == organization_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Extract MCP data from metadata
    metadata = json.loads(document.legal_metadata or "{}")
    mcp_data = metadata.get("mcp_enhancements", {})
    
    return MCPDataResponse(
        document_id=document_id,
        mcp_enhanced_at=metadata.get("mcp_enhanced_at"),
        mcp_data=mcp_data,
        has_court_analysis=bool(mcp_data.get("court_analysis")),
        has_validated_citations=bool(mcp_data.get("validated_citations")),
        has_conflict_check=bool(mcp_data.get("potential_conflicts")),
        has_extracted_deadlines=bool(mcp_data.get("extracted_deadlines"))
    )

@router.post("/classify", response_model=DocumentClassifyResponse)
async def classify_document_with_mcp(
    request: DocumentClassifyRequest,
    current_user: User = Depends(get_current_user)
):
    """Classify a document using court-specific MCP knowledge"""
    try:
        # Perform classification
        classification = await classifier.classify_with_court_knowledge(
            document_text=request.document_text,
            metadata=request.metadata or {}
        )
        
        return DocumentClassifyResponse(**classification)
        
    except Exception as e:
        logger.error(f"Document classification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents_with_mcp(
    request: DocumentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Search documents with MCP context enhancement"""
    try:
        # Perform enhanced search
        results = await search_service.search_with_mcp_context(
            query=request.query,
            filters=request.filters or {},
            organization_id=organization_id
        )
        
        return DocumentSearchResponse(
            query=results["query"],
            enhanced_terms=results.get("enhanced_terms", []),
            total_results=results["total_results"],
            documents=results["documents"]
        )
        
    except Exception as e:
        logger.error(f"Document search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-enhance", response_model=BulkEnhanceResponse)
async def bulk_enhance_documents(
    request: BulkEnhanceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Enhance multiple documents with MCP data"""
    
    # Validate document IDs
    document_ids = request.document_ids
    if not document_ids:
        # If no IDs provided, enhance all unenhanced documents
        unenhanced_docs = db.query(Document).filter(
            Document.organization_id == organization_id,
            Document.processing_status == "completed",
            ~Document.legal_metadata.contains("mcp_enhanced_at")
        ).limit(request.max_documents or 50).all()
        
        document_ids = [doc.id for doc in unenhanced_docs]
        
    if not document_ids:
        return BulkEnhanceResponse(
            total_documents=0,
            queued=0,
            message="No documents to enhance"
        )
        
    # Queue enhancement tasks
    background_tasks.add_task(
        enhance_documents_batch,
        document_ids,
        organization_id
    )
    
    return BulkEnhanceResponse(
        total_documents=len(document_ids),
        queued=len(document_ids),
        message=f"Queued {len(document_ids)} documents for enhancement"
    )

@router.get("/mcp-enhancement-stats")
async def get_mcp_enhancement_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Get statistics on MCP-enhanced documents"""
    
    # Get total documents
    total_docs = db.query(Document).filter(
        Document.organization_id == organization_id
    ).count()
    
    # Get enhanced documents
    enhanced_docs = db.query(Document).filter(
        Document.organization_id == organization_id,
        Document.legal_metadata.contains("mcp_enhanced_at")
    ).count()
    
    # Get documents by enhancement type
    court_docs = db.query(Document).filter(
        Document.organization_id == organization_id,
        Document.legal_metadata.contains("court_analysis")
    ).count()
    
    citation_docs = db.query(Document).filter(
        Document.organization_id == organization_id,
        Document.legal_metadata.contains("validated_citations")
    ).count()
    
    conflict_docs = db.query(Document).filter(
        Document.organization_id == organization_id,
        Document.legal_metadata.contains("potential_conflicts")
    ).count()
    
    deadline_docs = db.query(Document).filter(
        Document.organization_id == organization_id,
        Document.legal_metadata.contains("extracted_deadlines")
    ).count()
    
    return {
        "total_documents": total_docs,
        "enhanced_documents": enhanced_docs,
        "enhancement_percentage": (enhanced_docs / total_docs * 100) if total_docs > 0 else 0,
        "enhancement_types": {
            "court_analysis": court_docs,
            "validated_citations": citation_docs,
            "potential_conflicts": conflict_docs,
            "extracted_deadlines": deadline_docs
        }
    }

# Background task function
async def enhance_documents_batch(document_ids: List[str], organization_id: str):
    """Background task to enhance multiple documents"""
    logger.info(f"Starting batch enhancement for {len(document_ids)} documents")
    
    db = next(get_db())
    success_count = 0
    error_count = 0
    
    try:
        for doc_id in document_ids:
            try:
                document = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.organization_id == organization_id
                ).first()
                
                if document and document.processing_status == "completed":
                    await enhanced_processor.process_document_with_mcp(
                        document,
                        organization_id
                    )
                    success_count += 1
                    logger.info(f"Enhanced document {doc_id}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to enhance document {doc_id}: {str(e)}")
                
        logger.info(f"Batch enhancement complete: {success_count} success, {error_count} errors")
        
    finally:
        db.close()

@router.get("/search/legal-concepts")
async def extract_legal_concepts_from_query(
    query: str = Query(..., description="Search query to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Extract legal concepts from a search query"""
    try:
        concepts = await search_service._extract_legal_concepts(query)
        
        return {
            "query": query,
            "concepts": concepts
        }
        
    except Exception as e:
        logger.error(f"Legal concept extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))