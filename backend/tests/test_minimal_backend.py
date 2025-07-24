#!/usr/bin/env python3
"""Minimal backend for testing - no auth required"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime

app = FastAPI(title="Legal AI Test Backend")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
mock_documents = []

class Document(BaseModel):
    id: str
    filename: str
    processing_status: str = "completed"
    upload_timestamp: str
    file_size: int = 1024
    summary: Optional[str] = "This is a test document"

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    context_document_ids: Optional[List[str]] = []

class ChatResponse(BaseModel):
    message: str
    session_id: str
    timestamp: str
    sources: List[dict] = []

@app.get("/")
async def root():
    return {"message": "Test backend is running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "ai_service": "ready",
            "document_processor": "ready"
        }
    }

@app.get("/api/documents")
async def get_documents():
    return {
        "documents": mock_documents,
        "total": len(mock_documents),
        "page": 1,
        "page_size": 50,
        "pagination": {
            "current_page": 1,
            "page_size": 50,
            "total_pages": 1,
            "total_items": len(mock_documents)
        }
    }

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    doc_id = f"doc-{len(mock_documents) + 1}"
    doc = Document(
        id=doc_id,
        filename=file.filename,
        processing_status="completed",
        upload_timestamp=datetime.datetime.now().isoformat(),
        file_size=1024
    )
    mock_documents.append(doc.dict())
    return doc

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return ChatResponse(
        message=f"I received your message: '{request.message}'. This is a test response.",
        session_id=request.session_id,
        timestamp=datetime.datetime.now().isoformat(),
        sources=[]
    )

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    global mock_documents
    mock_documents = [d for d in mock_documents if d["id"] != document_id]
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    print("Starting minimal test backend on port 8000...")
    print("This backend requires NO authentication")
    uvicorn.run(app, host="0.0.0.0", port=8000)