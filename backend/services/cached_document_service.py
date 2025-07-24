"""
Document service with caching integration
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from models import Document
from services.cache_service import DocumentCache
from services.document_processor import DocumentProcessor


class CachedDocumentService:
    """Document service with caching layer."""
    
    def __init__(self, db: Session):
        self.db = db
        self.processor = DocumentProcessor()
    
    async def get_document(self, doc_id: int, org_id: int) -> Optional[dict]:
        """Get document with caching."""
        # Try cache first
        cached = DocumentCache.get_document(doc_id, org_id)
        if cached:
            return cached
        
        # Get from database
        doc = self.db.query(Document).filter(
            Document.id == doc_id,
            Document.organization_id == org_id
        ).first()
        
        if not doc:
            return None
        
        # Convert to dict
        doc_data = {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "document_type": doc.document_type,
            "status": doc.status,
            "content_extracted": doc.content_extracted,
            "ai_analysis": doc.ai_analysis,
            "metadata": doc.metadata,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
            "uploaded_by_id": doc.uploaded_by_id
        }
        
        # Cache it
        DocumentCache.set_document(doc_id, org_id, doc_data)
        
        return doc_data
    
    async def get_documents(self, org_id: int, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get documents list with caching."""
        # Try cache first
        cached = DocumentCache.get_document_list(org_id, skip, limit)
        if cached is not None:
            return cached
        
        # Get from database
        docs = self.db.query(Document).filter(
            Document.organization_id == org_id
        ).offset(skip).limit(limit).all()
        
        # Convert to list of dicts
        doc_list = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "document_type": doc.document_type,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            }
            for doc in docs
        ]
        
        # Cache it
        DocumentCache.set_document_list(org_id, doc_list, skip, limit)
        
        return doc_list
    
    async def update_document(self, doc_id: int, org_id: int, **kwargs):
        """Update document and invalidate cache."""
        doc = self.db.query(Document).filter(
            Document.id == doc_id,
            Document.organization_id == org_id
        ).first()
        
        if not doc:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        
        self.db.commit()
        
        # Invalidate cache
        DocumentCache.invalidate_document(doc_id, org_id)
        
        return doc
    
    async def delete_document(self, doc_id: int, org_id: int) -> bool:
        """Delete document and invalidate cache."""
        doc = self.db.query(Document).filter(
            Document.id == doc_id,
            Document.organization_id == org_id
        ).first()
        
        if not doc:
            return False
        
        self.db.delete(doc)
        self.db.commit()
        
        # Invalidate cache
        DocumentCache.invalidate_document(doc_id, org_id)
        
        return True