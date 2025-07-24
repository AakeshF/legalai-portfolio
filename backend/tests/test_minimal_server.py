#!/usr/bin/env python3
"""
Minimal FastAPI server for testing basic functionality
Bypasses heavy AI dependencies to get core system running
"""

import os
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn

# Core imports (should work)
try:
    from database import get_db, engine, Base
    from models import User, Organization, Document, ChatSession, ChatMessage
    from config import settings
    print("✅ Core database imports successful")
except Exception as e:
    print(f"❌ Database import error: {e}")
    sys.exit(1)

# Try auth imports
try:
    from auth_utils import get_current_user_dependency, create_access_token
    print("✅ Auth utilities imported")
except Exception as e:
    print(f"❌ Auth import error: {e}")
    # Create dummy auth for testing
    def get_current_user_dependency():
        def get_current_user():
            return User(id="test-user", email="[email@example.com]")
        return get_current_user

app = FastAPI(
    title="Legal AI - Minimal Test Server",
    description="Basic functionality test server",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock AI service for testing
class MockAIService:
    """Mock AI service that doesn't require heavy dependencies"""
    
    async def process_chat_message(self, message: str, documents=None, chat_history=None, **kwargs):
        return {
            "answer": f"Mock AI Response: I received your message '{message[:50]}...' This is a test response from the minimal server. All AI functionality is working!",
            "sources": [],
            "model": "mock-ai",
            "performance_metrics": {
                "total_response_time_ms": 100,
                "tokens_used": 0,
                "response_source": "mock"
            }
        }

# Global mock AI instance
mock_ai_service = MockAIService()

@app.get("/")
async def root():
    return {
        "message": "Legal AI - Minimal Test Server", 
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": db_status,
            "ai_service": "mock",
            "auth": "enabled"
        }
    }

@app.get("/api/demo-status")
async def get_demo_status():
    return {
        "demo_mode": True,
        "ai_provider": "mock",
        "message": "Running minimal test server with mock AI"
    }

@app.post("/api/chat")
async def chat_with_ai(
    chat_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Mock chat endpoint for testing"""
    try:
        message = chat_request.get("message", "")
        
        # Mock AI response
        response = await mock_ai_service.process_chat_message(message)
        
        return {
            "session_id": "test-session",
            "message": response["answer"],
            "sources": response["sources"],
            "timestamp": datetime.utcnow(),
            "performance_metrics": response["performance_metrics"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/api/documents")
async def list_documents(db: Session = Depends(get_db)):
    """List documents (basic functionality)"""
    try:
        documents = db.query(Document).limit(10).all()
        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.processing_status,
                    "upload_timestamp": doc.upload_timestamp
                }
                for doc in documents
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """Basic WebSocket endpoint"""
    try:
        await websocket.accept()
        await websocket.send_json({
            "type": "connection_established",
            "data": {
                "status": "connected",
                "message": "Mock WebSocket connection established"
            }
        })
        
        while True:
            data = await websocket.receive_text()
            # Echo back with mock response
            await websocket.send_json({
                "type": "chat_response", 
                "data": {
                    "message": f"Mock response to: {data}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
    except Exception as e:
        print(f"WebSocket error: {e}")

# Initialize database tables
print("Creating database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
except Exception as e:
    print(f"❌ Database creation error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Legal AI Minimal Test Server...")
    print("📝 This server provides basic functionality without AI dependencies")
    print("🔗 Frontend should connect to: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    print()
    
    uvicorn.run(
        "test_minimal_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
