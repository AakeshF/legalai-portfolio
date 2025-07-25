# main.py - FastAPI Legal AI Assistant Backend
from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    BackgroundTasks,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import json
from typing import List, Optional
from sqlalchemy import func, or_, and_, cast, String, text
import math
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

# Local imports
from database import get_db, engine, Base, SessionLocal
from models import Document, ChatSession, ChatMessage, User, Organization
from schemas import (
    DocumentResponse,
    ChatRequest,
    ChatResponse,
    DocumentUpload,
    HealthResponse,
    DocumentSearchParams,
    DocumentListResponse,
    PaginationMetadata,
    DocumentType,
    DocumentStatus,
    SortField,
    SortOrder,
    PerformanceMetrics,
    IntelligenceFlags,
)
from services.document_processor import (
    document_processor,
)  # Import the instance, not class
from services.hybrid_ai_service import hybrid_ai_service  # Use hybrid AI service
from services.mcp_manager import MCPManager
from services.semantic_search import SemanticSearchEngine
from services.rag_service import RAGService
from config import settings
from memory_config import MemoryConfig  # Import memory configuration
from auth_routes import router as auth_router, get_current_user_dependency
from auth_middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware as AuthRateLimitMiddleware,
    get_current_user,
    get_current_organization,
)
from organization_middleware import (
    OrganizationQueryFilter,
    OrganizationSecurityLogger,
    OrganizationSecurityViolation,
    get_org_filtered_query,
)
from logger import setup_logging, log_event, log_metric
import logging

# Production imports
from error_handler import (
    global_exception_handler,
    with_error_handling,
    UserFriendlyError,
    ErrorCategory,
)
from monitoring import system_monitor, metrics_collector, request_tracker
from audit_logger import AuditLogger, AuditLog, AuditEventType, AuditEvent
from rate_limiter import rate_limiter, RateLimitMiddleware

# Setup logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# Import all models to ensure they're registered
from models import Organization, User, Document, ChatSession, ChatMessage
from audit_logger import AuditLog
from session_manager import SecureSession, SessionActivity
from two_factor_auth import TwoFactorAuth
from security_monitor import SecurityIncidentDB

# Create database tables - DISABLED: Using init scripts instead
# Base.metadata.create_all(bind=engine)

# Initialize services
audit_logger = AuditLogger(SessionLocal)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Legal AI Backend...")

    # Start monitoring
    await system_monitor.start()

    # Set audit logger on rate limiter (will be accessed by middleware)
    rate_limiter.audit_logger = audit_logger

    yield

    # Shutdown
    logger.info("Shutting down Legal AI Backend...")

    # Stop monitoring
    await system_monitor.stop()

    # Flush audit logs
    audit_logger._flush_buffer()


# Initialize FastAPI app
app = FastAPI(
    title="Legal AI Assistant",
    description="Professional AI-powered legal document analysis system",
    version="1.0.0",
    lifespan=lifespan,
)

# Check if demo mode is active
if settings.demo_mode or os.getenv("DEMO_MODE", "false").lower() == "true":
    logger.info("🎮 DEMO MODE ACTIVE - Using [AI Provider] AI exclusively")


# Add middleware in correct order
# Request tracking middleware (outermost)
@app.middleware("http")
async def track_requests(request: Request, call_next):
    return await request_tracker.track_request(request, call_next)


# Rate limiting middleware
# Temporarily disabled for debugging
# app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# Authentication middleware - DISABLED FOR NO-AUTH MODE
# app.add_middleware(AuthenticationMiddleware)
logger.info("� Authentication middleware DISABLED - No-auth mode active")

# CORS middleware (must be after auth for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(UserFriendlyError, global_exception_handler)

# Security
security = HTTPBearer(auto_error=False)

# Initialize services
# ai_service is now hybrid_ai_service imported above
mcp_manager = MCPManager()

# Include routers
app.include_router(auth_router)

# Import and include organization routes
from organization_routes import router as org_router

app.include_router(org_router)

# Import and include health monitoring routes
from health_routes import router as health_router

app.include_router(health_router)

# Import and include AI management routes
from ai_routes import router as ai_router

app.include_router(ai_router)

# Import and include AI provider management routes
from ai_management_routes import router as ai_management_router

app.include_router(ai_management_router)

# Import and include AI provider testing routes
from ai_provider_test_routes import router as ai_provider_test_router

app.include_router(ai_provider_test_router)

# Import and include enhanced AI chat routes
from ai_chat_routes import router as ai_chat_router

app.include_router(ai_chat_router)

# Import and include MCP management routes
from mcp_routes import router as mcp_router

app.include_router(mcp_router)

# Import and include matter management routes
from matter_routes import router as matter_router

app.include_router(matter_router)

# Import and include document MCP routes
from document_mcp_routes import router as document_mcp_router

app.include_router(document_mcp_router)

# Import and include communication routes
from communication_routes import router as communication_router

app.include_router(communication_router)

# Import and include MCP monitoring routes
from mcp_monitoring_routes import router as mcp_monitoring_router, set_mcp_manager

app.include_router(mcp_monitoring_router)

# Import and include anonymization routes
from api.anonymization_routes import router as anonymization_router

app.include_router(anonymization_router)

# Import and include prompt management routes
from api.prompt_routes import router as prompt_router

app.include_router(prompt_router)

# Import and include consent management routes
from api.consent_routes import router as consent_router

app.include_router(consent_router)

# Import and include security enforcement routes
from api.security_routes import router as security_router

app.include_router(security_router)

# Import and include integrated AI routes
from api.integrated_ai_routes import router as integrated_ai_router

app.include_router(integrated_ai_router)

# Import WebSocket handler
from websocket_handler import manager, authenticate_websocket_token, WebSocketHandler


# Main WebSocket endpoint - This is what the frontend expects
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """Main WebSocket endpoint for real-time communication - NO AUTH"""
    try:
        # No authentication - create anonymous user session
        anonymous_user_id = "anonymous-user"
        anonymous_org_id = "anonymous-org"

        user_data = {
            "email": "[email@example.com]",
            "username": "Demo User",
            "role": "user",
        }

        await manager.connect(websocket, anonymous_user_id, anonymous_org_id, user_data)

        # Initialize message handler
        handler = WebSocketHandler(db)

        # Send connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "data": {
                        "userId": anonymous_user_id,
                        "organizationId": anonymous_org_id,
                        "status": "connected",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            )
        )

        try:
            # Listen for messages
            while True:
                # Receive message from client
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)

                    # Create anonymous user/org objects for handler
                    class AnonymousUser:
                        def __init__(self):
                            self.id = anonymous_user_id
                            self.email = "[email@example.com]"

                    class AnonymousOrg:
                        def __init__(self):
                            self.id = anonymous_org_id
                            self.name = "Demo Organization"

                    await handler.handle_message(
                        websocket, AnonymousUser(), AnonymousOrg(), message
                    )
                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "data": {
                                    "message": "Invalid JSON format",
                                    "timestamp": datetime.utcnow().isoformat(),
                                },
                            }
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing WebSocket message",
                        extra={
                            "error": str(e),
                            "user_id": anonymous_user_id,
                            "organization_id": anonymous_org_id,
                        },
                    )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "data": {
                                    "message": "Message processing failed",
                                    "timestamp": datetime.utcnow().isoformat(),
                                },
                            }
                        )
                    )

        except WebSocketDisconnect:
            logger.info(
                f"WebSocket client disconnected normally",
                extra={
                    "user_id": anonymous_user_id,
                    "organization_id": anonymous_org_id,
                },
            )
        except Exception as e:
            logger.error(
                f"WebSocket connection error",
                extra={
                    "error": str(e),
                    "user_id": anonymous_user_id,
                    "organization_id": anonymous_org_id,
                },
            )
        finally:
            # Clean up connection
            await manager.disconnect(anonymous_user_id)

    except HTTPException as e:
        # Authentication failed
        logger.warning(f"WebSocket authentication failed: {e.detail}")
        await websocket.close(code=1008, reason=e.detail)
    except Exception as e:
        # Unexpected error
        logger.error(f"WebSocket endpoint error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


# WebSocket status endpoint
@app.get("/api/websocket/status")
async def websocket_status():
    """Get WebSocket connection status and statistics"""
    stats = manager.get_connection_stats()
    anonymous_org_id = "anonymous-org"
    anonymous_user_id = "anonymous-user"

    return {
        "websocket_enabled": True,
        "total_connections": stats["total_connections"],
        "organization_connections": stats["organization_counts"].get(
            anonymous_org_id, 0
        ),
        "organization_users": [],
        "user_connected": anonymous_user_id in manager.active_connections,
        "user_presence": manager.user_presence.get(anonymous_user_id, "offline"),
    }


# Removed insecure simple AI test endpoint

# Initialize MCP monitoring with the manager
from services.mcp_manager_enhanced import EnhancedMCPManager

if hasattr(mcp_manager, "servers"):
    set_mcp_manager(mcp_manager)


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Legal AI Backend API", "version": "1.0.0", "docs": "/docs"}


@app.get("/api")
async def api_root():
    return {
        "message": "Legal AI Backend API",
        "version": "1.0.0",
        "endpoints": {
            "documents": "/api/documents",
            "chat": "/api/chat",
            "health": "/api/health",
        },
    }


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connectivity
        db.execute(text("SELECT 1")).scalar()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "error"

    # Check memory usage
    memory_status = "healthy"
    try:
        import psutil

        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)

        if memory_mb > MemoryConfig.MEMORY_CRITICAL_THRESHOLD_MB:
            memory_status = "critical"
        elif memory_mb > MemoryConfig.MEMORY_WARNING_THRESHOLD_MB:
            memory_status = "warning"

        logger.info(f"Memory usage: {memory_mb:.2f}MB")
    except:
        memory_status = "unknown"

    return HealthResponse(
        status=(
            "healthy"
            if db_status == "connected" and memory_status != "critical"
            else "degraded"
        ),
        timestamp=datetime.utcnow(),
        services={
            "database": db_status,
            "ai_service": "ready",
            "document_processor": "ready",
            "memory": memory_status,
        },
    )


# Memory Status Endpoint
@app.get("/api/memory-status")
async def get_memory_status():
    """Get current memory usage and limits"""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        # Get system memory
        virtual_memory = psutil.virtual_memory()

        # Calculate usage
        process_memory_mb = memory_info.rss / (1024 * 1024)
        process_memory_percent = (memory_info.rss / virtual_memory.total) * 100

        # Determine status
        if process_memory_mb > MemoryConfig.MEMORY_CRITICAL_THRESHOLD_MB:
            status = "critical"
        elif process_memory_mb > MemoryConfig.MEMORY_WARNING_THRESHOLD_MB:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "process_memory_mb": round(process_memory_mb, 2),
            "process_memory_percent": round(process_memory_percent, 2),
            "system_memory_available_mb": round(
                virtual_memory.available / (1024 * 1024), 2
            ),
            "system_memory_percent": round(virtual_memory.percent, 2),
            "limits": MemoryConfig.get_memory_limits(),
            "thresholds": {
                "warning_mb": MemoryConfig.MEMORY_WARNING_THRESHOLD_MB,
                "critical_mb": MemoryConfig.MEMORY_CRITICAL_THRESHOLD_MB,
            },
        }
    except ImportError:
        return {
            "status": "unknown",
            "error": "psutil not installed",
            "limits": MemoryConfig.get_memory_limits(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "limits": MemoryConfig.get_memory_limits(),
        }


# Demo Mode Endpoints
@app.get("/api/demo-status")
async def get_demo_status(current_user: User = Depends(get_current_user)):
    """Get current demo mode status"""
    is_demo = settings.demo_mode or os.getenv("DEMO_MODE", "false").lower() == "true"
    return {
        "demo_mode": is_demo,
        "ai_provider": "openai" if is_demo else "multi-provider",
        "message": (
            "Demo mode active - Using AI provider exclusively"
            if is_demo
            else "Production mode - Multiple AI providers available"
        ),
    }


@app.post("/api/toggle-demo-mode")
async def toggle_demo_mode(
    enable: bool, current_user: User = Depends(get_current_user)
):
    """Toggle demo mode (admin only)"""
    # Check if user is admin (you may want to add proper admin check)
    if current_user.email not in ["[ADMIN-EMAIL]", "[DEMO-EMAIL]"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Update environment variable
    os.environ["DEMO_MODE"] = "true" if enable else "false"

    # Reinitialize AI service
    from services.ollama_service import OllamaService as AIService

    hybrid_ai_service.ai_service = AIService()

    return {
        "demo_mode": enable,
        "message": f"Demo mode {'enabled' if enable else 'disabled'}",
    }


# Document Management Endpoints
@app.post("/api/documents/upload", response_model=DocumentResponse)
@with_error_handling(category=ErrorCategory.FILE_PROCESSING)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Upload and process a legal document"""
    try:
        # Log document upload
        audit_logger.log_document_access(
            user=current_user,
            document_id="pending",
            action="upload",
            ip_address=getattr(current_user, "_request_ip", "unknown"),
        )
        logger.info(
            f"Document upload initiated",
            extra={
                "filename": file.filename,
                "content_type": file.content_type,
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )

        # Validate file type
        allowed_extensions = (".pdf", ".docx", ".txt")
        if not file.filename.lower().endswith(allowed_extensions):
            raise UserFriendlyError(
                status_code=400,
                user_message=f"This file type is not supported. Please upload PDF, DOCX, or TXT files.",
                technical_details=f"File: {file.filename}, Type: {file.content_type}",
                error_category=ErrorCategory.VALIDATION,
            )

        # Validate file size using memory config
        content = await file.read()
        file_size = len(content)
        max_size_bytes = MemoryConfig.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size_bytes:
            raise UserFriendlyError(
                status_code=400,
                user_message=f"The file is too large. Maximum allowed size is {MemoryConfig.MAX_FILE_SIZE_MB}MB.",
                technical_details=f"File size: {file_size / (1024*1024):.2f}MB",
                error_category=ErrorCategory.VALIDATION,
            )

        if file_size == 0:
            raise UserFriendlyError(
                status_code=400,
                user_message="The uploaded file is empty. Please select a valid document.",
                error_category=ErrorCategory.VALIDATION,
            )

        # Generate unique document ID
        doc_id = str(uuid.uuid4())

        # Save uploaded file
        upload_dir = settings.upload_directory
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename to prevent conflicts
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{doc_id}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Write file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        logger.info(f"File saved to: {file_path}", extra={"file_size": file_size})
        log_metric(
            logger, "document_uploaded", 1, unit="count", file_type=file_extension
        )

        # Create database record with organization context
        db_document = Document(
            id=doc_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            content_type=file.content_type,
            upload_timestamp=datetime.utcnow(),
            processing_status="pending",
            organization_id=current_org.id,
            uploaded_by_id=current_user.id,
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        logger.info(f"Database record created with ID: {doc_id}")

        # Process document in background with organization context
        background_tasks.add_task(
            process_document_background, doc_id, file_path, current_org.id
        )

        logger.info(
            f"Background processing scheduled",
            extra={
                "filename": file.filename,
                "document_id": doc_id,
                "organization_id": current_org.id,
            },
        )

        # Return response matching your DocumentResponse schema
        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            status="pending",  # Using 'status' to match your schema
            upload_timestamp=db_document.upload_timestamp,
            file_size=file_size,
            page_count=None,  # Will be updated after processing
            summary=None,  # Will be updated after processing
            content=None,  # Will be updated after processing
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Document upload failed",
            extra={
                "error": str(e),
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
    params: DocumentSearchParams = Depends(),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get list of documents with advanced search, filtering, and sorting"""
    try:
        # Start with base query filtered by organization
        query = db.query(Document).filter(Document.organization_id == current_org.id)

        # Apply full-text search if provided
        if params.search:
            search_term = f"%{params.search}%"
            query = query.filter(
                or_(
                    Document.filename.ilike(search_term),
                    Document.extracted_content.ilike(search_term),
                    Document.summary.ilike(search_term),
                    Document.legal_metadata.ilike(search_term),
                )
            )

        # Apply filters
        if params.document_type:
            # Search for document type in legal_metadata JSON
            type_filter = f'%"document_type": "{params.document_type}"%'
            query = query.filter(Document.legal_metadata.like(type_filter))

        if params.status:
            query = query.filter(Document.processing_status == params.status)

        if params.date_from:
            query = query.filter(Document.upload_timestamp >= params.date_from)

        if params.date_to:
            query = query.filter(Document.upload_timestamp <= params.date_to)

        if params.min_file_size:
            query = query.filter(Document.file_size >= params.min_file_size)

        if params.max_file_size:
            query = query.filter(Document.file_size <= params.max_file_size)

        # Apply risk score filters (assuming risk_score is stored in legal_metadata)
        if params.min_risk_score is not None or params.max_risk_score is not None:
            # Filter documents that have risk_score in metadata
            if params.min_risk_score is not None:
                risk_filter = f'%"risk_score": {params.min_risk_score}%'
                query = query.filter(
                    and_(
                        Document.legal_metadata.is_not(None),
                        Document.legal_metadata.like('%"risk_score":%'),
                    )
                )
            if params.max_risk_score is not None:
                # This is a simplified filter - in production, you'd want to parse JSON properly
                query = query.filter(Document.legal_metadata.is_not(None))

        # Get total count before pagination
        total_items = query.count()

        # Apply sorting
        if params.sort_by == SortField.UPLOAD_DATE:
            order_column = Document.upload_timestamp
        elif params.sort_by == SortField.FILE_SIZE:
            order_column = Document.file_size
        elif params.sort_by == SortField.FILENAME:
            order_column = Document.filename
        elif params.sort_by == SortField.STATUS:
            order_column = Document.processing_status
        elif params.sort_by == SortField.RISK_SCORE:
            # For risk score, we'd need to extract from JSON - simplified here
            order_column = Document.legal_metadata
        else:
            order_column = Document.upload_timestamp

        # Apply sort order
        if params.sort_order == SortOrder.ASC:
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())

        # Apply pagination
        query = query.limit(params.limit).offset(params.offset)

        # Execute query
        documents = query.all()

        # Convert to response models
        document_responses = [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                status=doc.processing_status,
                upload_timestamp=doc.upload_timestamp,
                file_size=doc.file_size,
                page_count=getattr(doc, "page_count", None),
                summary=getattr(doc, "summary", None),
                content=getattr(doc, "extracted_content", None),
                metadata=(
                    json.loads(doc.legal_metadata)
                    if getattr(doc, "legal_metadata", None)
                    else None
                ),
            )
            for doc in documents
        ]

        # Calculate pagination metadata
        total_pages = math.ceil(total_items / params.limit) if params.limit > 0 else 1
        current_page = (params.offset // params.limit) + 1 if params.limit > 0 else 1

        pagination = PaginationMetadata(
            total_items=total_items,
            page_size=params.limit,
            current_page=current_page,
            total_pages=total_pages,
            has_next=current_page < total_pages,
            has_previous=current_page > 1,
        )

        # Build filters applied dictionary
        filters_applied = {}
        if params.document_type:
            filters_applied["document_type"] = params.document_type
        if params.status:
            filters_applied["status"] = params.status
        if params.date_from:
            filters_applied["date_from"] = params.date_from.isoformat()
        if params.date_to:
            filters_applied["date_to"] = params.date_to.isoformat()
        if params.min_risk_score is not None:
            filters_applied["min_risk_score"] = params.min_risk_score
        if params.max_risk_score is not None:
            filters_applied["max_risk_score"] = params.max_risk_score
        if params.min_file_size:
            filters_applied["min_file_size"] = params.min_file_size
        if params.max_file_size:
            filters_applied["max_file_size"] = params.max_file_size
        filters_applied["sort_by"] = params.sort_by
        filters_applied["sort_order"] = params.sort_order

        return DocumentListResponse(
            documents=document_responses,
            pagination=pagination,
            filters_applied=filters_applied,
            search_query=params.search,
        )

    except Exception as e:
        logger.error(
            f"Error fetching documents",
            extra={"error": str(e), "organization_id": current_org.id},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch documents: {str(e)}"
        )


@app.get("/api/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get specific document details"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.organization_id == current_org.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.processing_status,  # Map processing_status to status
        upload_timestamp=document.upload_timestamp,
        file_size=document.file_size,
        page_count=getattr(document, "page_count", None),
        summary=getattr(document, "summary", None),
        content=getattr(
            document, "extracted_content", None
        ),  # Map extracted_content to content
        metadata=(
            json.loads(document.legal_metadata)
            if getattr(document, "legal_metadata", None)
            else None
        ),
    )


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Delete a document and its associated data"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.organization_id == current_org.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Delete file from filesystem
        if os.path.exists(document.file_path):
            os.remove(document.file_path)

        # Delete from database
        db.delete(document)
        db.commit()

        return {"message": f"Document {document.filename} deleted successfully"}
    except Exception as e:
        logger.error(
            f"Error deleting document",
            extra={
                "document_id": document_id,
                "error": str(e),
                "organization_id": current_org.id,
            },
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to delete document: {str(e)}"
        )


@app.post("/api/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Reprocess a document"""

    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.organization_id == current_org.id)
        .first()
    )

    if not document:
        # Log access attempt for non-existent or unauthorized document
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="document",
            resource_id=document_id,
            action="reprocess",
            success=False,
            reason="Document not found or unauthorized",
        )
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=400, detail="Original file not found")

    # Log successful access
    OrganizationSecurityLogger.log_access_attempt(
        user_id=current_user.id,
        organization_id=current_org.id,
        resource_type="document",
        resource_id=document_id,
        action="reprocess",
        success=True,
    )

    # Reset status
    document.processing_status = "pending"
    document.error_message = None
    document.extracted_content = None
    document.summary = None
    db.commit()

    # Schedule reprocessing with organization context
    background_tasks.add_task(
        process_document_background,
        document.id,
        document.file_path,
        current_org.id,  # Pass organization context
    )

    return {"message": f"Reprocessing started for {document.filename}"}


# Advanced Search Endpoint
@app.post("/api/documents/search", response_model=DocumentListResponse)
async def search_documents(
    search_params: DocumentSearchParams,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Advanced document search endpoint with complex filtering.
    This endpoint accepts search parameters via POST body for more complex queries.
    """
    try:
        # Start with organization-filtered base query
        query = get_org_filtered_query(Document, current_org.id, db)

        # Apply full-text search with relevance scoring
        if search_params.search:
            search_term = f"%{search_params.search}%"

            # Create subqueries for relevance scoring
            filename_match = Document.filename.ilike(search_term)
            content_match = Document.extracted_content.ilike(search_term)
            summary_match = Document.summary.ilike(search_term)
            metadata_match = Document.legal_metadata.ilike(search_term)

            # Apply search with OR condition
            query = query.filter(
                or_(filename_match, content_match, summary_match, metadata_match)
            )

            # Order by relevance (filename matches first, then summary, then content)
            query = query.order_by(
                filename_match.desc(), summary_match.desc(), content_match.desc()
            )

        # Apply filters with improved risk score handling
        if search_params.document_type:
            type_filter = f'%"document_type": "{search_params.document_type}"%'
            query = query.filter(Document.legal_metadata.like(type_filter))

        if search_params.status:
            query = query.filter(Document.processing_status == search_params.status)

        if search_params.date_from:
            query = query.filter(Document.upload_timestamp >= search_params.date_from)

        if search_params.date_to:
            query = query.filter(Document.upload_timestamp <= search_params.date_to)

        if search_params.min_file_size:
            query = query.filter(Document.file_size >= search_params.min_file_size)

        if search_params.max_file_size:
            query = query.filter(Document.file_size <= search_params.max_file_size)

        # Improved risk score filtering
        if (
            search_params.min_risk_score is not None
            or search_params.max_risk_score is not None
        ):
            # Only filter documents that have legal_metadata
            query = query.filter(Document.legal_metadata.is_not(None))

            if search_params.min_risk_score is not None:
                # Use JSON path extraction for PostgreSQL or filter in Python for SQLite
                min_risk = search_params.min_risk_score
                query = query.filter(Document.legal_metadata.like(f'%"risk_score":%'))

            # Note: For production, consider using PostgreSQL with proper JSON operators
            # or adding a dedicated risk_score column to the Document model

        # Get total count before pagination
        total_items = query.count()

        # Apply sorting (if not already sorted by relevance)
        if not search_params.search:
            if search_params.sort_by == SortField.UPLOAD_DATE:
                order_column = Document.upload_timestamp
            elif search_params.sort_by == SortField.FILE_SIZE:
                order_column = Document.file_size
            elif search_params.sort_by == SortField.FILENAME:
                order_column = Document.filename
            elif search_params.sort_by == SortField.STATUS:
                order_column = Document.processing_status
            elif search_params.sort_by == SortField.RISK_SCORE:
                order_column = Document.legal_metadata
            else:
                order_column = Document.upload_timestamp

            if search_params.sort_order == SortOrder.ASC:
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

        # Apply pagination
        query = query.limit(search_params.limit).offset(search_params.offset)

        # Execute query
        documents = query.all()

        # Post-process for risk score filtering if needed
        if (
            search_params.min_risk_score is not None
            or search_params.max_risk_score is not None
        ):
            filtered_docs = []
            for doc in documents:
                if doc.legal_metadata:
                    try:
                        metadata = json.loads(doc.legal_metadata)
                        risk_score = metadata.get("risk_score", 0)

                        if (
                            search_params.min_risk_score is not None
                            and risk_score < search_params.min_risk_score
                        ):
                            continue
                        if (
                            search_params.max_risk_score is not None
                            and risk_score > search_params.max_risk_score
                        ):
                            continue

                        filtered_docs.append(doc)
                    except:
                        continue
            documents = filtered_docs

        # Convert to response models
        document_responses = [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                status=doc.processing_status,
                upload_timestamp=doc.upload_timestamp,
                file_size=doc.file_size,
                page_count=getattr(doc, "page_count", None),
                summary=getattr(doc, "summary", None),
                content=getattr(doc, "extracted_content", None),
                metadata=(
                    json.loads(doc.legal_metadata)
                    if getattr(doc, "legal_metadata", None)
                    else None
                ),
            )
            for doc in documents
        ]

        # Calculate pagination metadata
        total_pages = (
            math.ceil(total_items / search_params.limit)
            if search_params.limit > 0
            else 1
        )
        current_page = (
            (search_params.offset // search_params.limit) + 1
            if search_params.limit > 0
            else 1
        )

        pagination = PaginationMetadata(
            total_items=total_items,
            page_size=search_params.limit,
            current_page=current_page,
            total_pages=total_pages,
            has_next=current_page < total_pages,
            has_previous=current_page > 1,
        )

        # Build comprehensive filters applied dictionary
        filters_applied = {
            "search_query": search_params.search,
            "document_type": search_params.document_type,
            "status": search_params.status,
            "date_range": {
                "from": (
                    search_params.date_from.isoformat()
                    if search_params.date_from
                    else None
                ),
                "to": (
                    search_params.date_to.isoformat() if search_params.date_to else None
                ),
            },
            "risk_score_range": {
                "min": search_params.min_risk_score,
                "max": search_params.max_risk_score,
            },
            "file_size_range": {
                "min": search_params.min_file_size,
                "max": search_params.max_file_size,
            },
            "sorting": {
                "field": search_params.sort_by,
                "order": search_params.sort_order,
            },
        }

        # Remove None values from filters_applied
        filters_applied = {k: v for k, v in filters_applied.items() if v is not None}

        return DocumentListResponse(
            documents=document_responses,
            pagination=pagination,
            filters_applied=filters_applied,
            search_query=search_params.search,
        )

    except Exception as e:
        logger.error(
            f"Error searching documents",
            extra={"error": str(e), "organization_id": current_org.id},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to search documents: {str(e)}"
        )


# Chat Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Process a chat message with AI assistant"""
    try:
        # Generate session ID if not provided
        session_id = chat_request.session_id or str(uuid.uuid4())

        # Get or create chat session
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.organization_id == current_org.id,
            )
            .first()
        )

        if not session:
            try:
                session = ChatSession(
                    id=session_id,
                    created_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    organization_id=current_org.id,
                    user_id=current_user.id,
                )
                db.add(session)
                db.commit()
            except Exception as e:
                # Session might already exist, rollback and try to fetch it
                db.rollback()
                session = (
                    db.query(ChatSession).filter(ChatSession.id == session_id).first()
                )
                if not session:
                    # If still not found, generate a new session ID
                    session_id = str(uuid.uuid4())
                    session = ChatSession(
                        id=session_id,
                        created_at=datetime.utcnow(),
                        last_activity=datetime.utcnow(),
                        organization_id=current_org.id,
                        user_id=current_user.id,
                    )
                    db.add(session)
                    db.commit()
        else:
            # Update last activity
            session.last_activity = datetime.utcnow()
            db.commit()

        # Get relevant documents for context
        documents = []
        if chat_request.document_ids:
            documents = (
                db.query(Document)
                .filter(
                    Document.id.in_(chat_request.document_ids),
                    Document.processing_status == "completed",
                    Document.organization_id == current_org.id,
                )
                .all()
            )
        else:
            # Use all processed documents as context from the organization
            documents = (
                db.query(Document)
                .filter(
                    Document.processing_status == "completed",
                    Document.organization_id == current_org.id,
                )
                .all()
            )

        # Convert your ChatMessage schema to simple dict for ai_service
        history = []
        if chat_request.history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in chat_request.history
            ]

        # Generate AI response with performance tracking using hybrid AI
        response = await hybrid_ai_service.process_chat_message(
            message=chat_request.message,
            documents=documents,
            chat_history=history,
            organization=current_org,  # Pass org for backend selection
        )

        # Extract performance metrics and intelligence flags
        perf_metrics = response.get("performance_metrics", {})
        intel_flags = response.get("intelligence_flags", {})

        # For backward compatibility, also check response_metrics
        if not perf_metrics and "response_metrics" in response:
            old_metrics = response["response_metrics"]
            perf_metrics = {
                "total_response_time_ms": old_metrics.get("response_time_ms", 0),
                "metadata_lookup_time_ms": None,
                "ai_processing_time_ms": old_metrics.get("response_time_ms", 0),
                "tokens_used": old_metrics.get("tokens_used", 0),
                "tokens_saved_via_cache": old_metrics.get("tokens_saved", 0),
                "cache_hit": old_metrics.get("response_type") == "instant_metadata",
                "response_source": (
                    "metadata_cache"
                    if old_metrics.get("response_type") == "instant_metadata"
                    else "ai_analysis"
                ),
                "cost_savings_estimate": (
                    f"${old_metrics.get('cost_saved', 0):.3f}"
                    if old_metrics.get("cost_saved")
                    else "$0.00"
                ),
                "query_classification": (
                    "metadata_query"
                    if old_metrics.get("response_type") == "instant_metadata"
                    else "analysis_request"
                ),
            }

        # Save chat message to database
        user_message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            role="user",
            content=chat_request.message,
            timestamp=datetime.utcnow(),
        )

        # Include performance metrics in AI message for analytics
        ai_message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            role="assistant",
            content=response["answer"],
            timestamp=datetime.utcnow(),
            model_used=response.get("model", "unknown"),
            processing_time=(
                perf_metrics.get("total_response_time_ms") if perf_metrics else None
            ),
        )

        db.add(user_message)
        db.add(ai_message)
        db.commit()

        # Build enhanced response with performance metrics
        performance_metrics = PerformanceMetrics(
            total_response_time_ms=perf_metrics.get("total_response_time_ms", 0),
            metadata_lookup_time_ms=perf_metrics.get("metadata_lookup_time_ms"),
            ai_processing_time_ms=perf_metrics.get("ai_processing_time_ms"),
            tokens_used=perf_metrics.get("tokens_used", 0),
            tokens_saved_via_cache=perf_metrics.get("tokens_saved_via_cache", 0),
            cache_hit=perf_metrics.get("cache_hit", False),
            response_source=perf_metrics.get("response_source", "ai_analysis"),
            cost_savings_estimate=perf_metrics.get("cost_savings_estimate", "$0.00"),
            query_classification=perf_metrics.get(
                "query_classification", "conversational"
            ),
        )

        intelligence_flags = IntelligenceFlags(
            instant_response=intel_flags.get("instant_response", False),
            context_utilized=intel_flags.get("context_utilized", []),
            optimization_applied=intel_flags.get("optimization_applied"),
            confidence_score=intel_flags.get("confidence_score"),
        )

        chat_response = ChatResponse(
            session_id=session.id,
            message=response.get("answer", ""),
            sources=response.get("sources", []),
            timestamp=datetime.utcnow(),
            performance_metrics=performance_metrics,
            intelligence_flags=intelligence_flags,
            # Legacy fields for backward compatibility
            response_metrics=perf_metrics,
            response_type=perf_metrics.get("response_source"),
            tokens_used=perf_metrics.get("tokens_used"),
            response_time_ms=perf_metrics.get("total_response_time_ms"),
            cost_saved=(
                float(perf_metrics.get("cost_savings_estimate", "0").replace("$", ""))
                if perf_metrics.get("cost_savings_estimate")
                else 0
            ),
        )

        # Enhanced logging with structured metrics
        if perf_metrics:
            log_event(
                logger,
                "chat_response_generated",
                f"Chat response generated - Source: {perf_metrics.get('response_source')}",
                session_id=session_id,
                response_source=perf_metrics.get("response_source"),
                total_time_ms=perf_metrics.get("total_response_time_ms"),
                tokens_used=perf_metrics.get("tokens_used"),
                tokens_saved=perf_metrics.get("tokens_saved_via_cache"),
                cache_hit=perf_metrics.get("cache_hit"),
                query_type=perf_metrics.get("query_classification"),
                cost_saved=perf_metrics.get("cost_savings_estimate"),
            )

            # Log cost savings metric
            if perf_metrics.get("tokens_saved_via_cache", 0) > 0:
                log_metric(
                    logger,
                    "tokens_saved",
                    perf_metrics.get("tokens_saved_via_cache", 0),
                    unit="tokens",
                    source="metadata_cache",
                )

        return chat_response

    except Exception as e:
        logger.error(
            f"Chat processing error",
            extra={
                "error": str(e),
                "organization_id": current_org.id,
                "session_id": session_id if "session_id" in locals() else None,
            },
        )
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.get("/api/chat/{session_id}/history")
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get chat history for a session"""
    # First verify that the session belongs to the organization
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id, ChatSession.organization_id == current_org.id
        )
        .first()
    )

    if not session:
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="chat_session",
            resource_id=session_id,
            action="read_history",
            success=False,
            reason="Session not found or unauthorized",
        )
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )

    return [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "metadata": getattr(msg, "metadata", {}),
        }
        for msg in messages
    ]


# Semantic Search Endpoints
@app.post("/api/documents/semantic-search")
async def semantic_search(
    query: str,
    document_ids: Optional[List[str]] = None,
    document_types: Optional[List[str]] = None,
    top_k: int = 10,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Perform semantic search across documents using vector embeddings.

    Args:
        query: Search query
        document_ids: Optional list of document IDs to search within
        document_types: Optional list of document types to filter
        top_k: Number of results to return
    """
    try:
        # Initialize search engine
        search_engine = SemanticSearchEngine()

        # Perform search
        results = await search_engine.search(
            query=query,
            organization_id=current_org.id,
            document_ids=document_ids,
            document_types=document_types,
            top_k=top_k,
            user_id=current_user.id,
        )

        # Log search
        logger.info(
            "Semantic search performed",
            extra={
                "query": query[:100],
                "results_count": len(results),
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )

        # Format results
        return {
            "query": query,
            "results": [result.to_dict() for result in results],
            "total_results": len(results),
        }

    except Exception as e:
        logger.error(
            "Semantic search failed",
            extra={
                "error": str(e),
                "query": query,
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@app.get("/api/documents/{document_id}/similar")
async def find_similar_documents(
    document_id: str,
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Find documents similar to a given document using embeddings."""
    try:
        # Verify document access
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id, Document.organization_id == current_org.id
            )
            .first()
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Initialize search engine
        search_engine = SemanticSearchEngine()

        # Find similar documents
        similar_docs = await search_engine.find_similar_documents(
            document_id=document_id, organization_id=current_org.id, top_k=top_k
        )

        logger.info(
            "Similar documents found",
            extra={
                "source_document_id": document_id,
                "similar_count": len(similar_docs),
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )

        return {
            "source_document": {
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
            },
            "similar_documents": similar_docs,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Find similar documents failed",
            extra={
                "error": str(e),
                "document_id": document_id,
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to find similar documents: {str(e)}"
        )


@app.post("/api/chat/rag")
async def rag_chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Enhanced chat using Retrieval-Augmented Generation (RAG).
    Automatically retrieves relevant document context for better answers.
    """
    try:
        # Initialize services
        from services.ollama_service import OllamaService

        ollama_service = OllamaService()

        rag_service = RAGService(
            ai_service=hybrid_ai_service.ai_service,
            ollama_service=ollama_service,
            use_local_llm=True,  # Prefer local for privacy
        )

        # Get conversation history if session exists
        conversation_history = []
        if hasattr(chat_request, "session_id") and chat_request.session_id:
            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == chat_request.session_id)
                .order_by(ChatMessage.timestamp.desc())
                .limit(10)
                .all()
            )

            conversation_history = [
                {"role": msg.role, "content": msg.content} for msg in reversed(messages)
            ]

        # Perform RAG query
        rag_response = await rag_service.query(
            query=chat_request.message,
            organization_id=current_org.id,
            document_ids=(
                chat_request.document_ids
                if hasattr(chat_request, "document_ids")
                else None
            ),
            user_id=current_user.id,
            conversation_history=conversation_history,
        )

        # Save to chat history
        session_id = (
            chat_request.session_id
            if hasattr(chat_request, "session_id")
            else str(uuid.uuid4())
        )

        # User message
        user_msg = ChatMessage(
            session_id=session_id, role="user", content=chat_request.message
        )
        db.add(user_msg)

        # Assistant response with sources
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=rag_response.answer,
            metadata={"sources": rag_response.sources},
        )
        db.add(assistant_msg)
        db.commit()

        logger.info(
            "RAG chat completed",
            extra={
                "session_id": session_id,
                "sources_used": len(rag_response.sources),
                "confidence": rag_response.confidence,
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )

        return {
            "response": rag_response.answer,
            "sources": rag_response.sources,
            "confidence": rag_response.confidence,
            "session_id": session_id,
            "search_time_ms": rag_response.search_time_ms,
            "generation_time_ms": rag_response.generation_time_ms,
        }

    except Exception as e:
        logger.error(
            "RAG chat failed",
            extra={
                "error": str(e),
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )
        raise HTTPException(status_code=500, detail=f"RAG chat failed: {str(e)}")


# Test Endpoints (No Auth Required)
@app.post("/api/test/semantic-search")
async def test_semantic_search(
    query: str,
    document_ids: Optional[List[str]] = None,
    document_types: Optional[List[str]] = None,
    top_k: int = 10,
    db: Session = Depends(get_db),
):
    """Test semantic search without authentication"""
    try:
        # Initialize SQLite-compatible search engine
        from services.semantic_search_sqlite import SQLiteSemanticSearchEngine

        search_engine = SQLiteSemanticSearchEngine()

        # Use dev organization ID
        org_id = "dev-org-id"

        # Perform search
        results = await search_engine.search(
            query=query,
            organization_id=org_id,
            document_ids=document_ids,
            document_types=document_types,
            top_k=top_k,
            user_id="test-user",
        )

        # Format results
        return {
            "query": query,
            "results": [r.to_dict() for r in results],
            "total": len(results),
        }
    except Exception as e:
        logger.error(f"Test semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/rag-chat")
async def test_rag_chat(chat_request: ChatRequest, db: Session = Depends(get_db)):
    """Test RAG chat without authentication"""
    try:
        # Initialize RAG service with SQLite-compatible search
        from services.semantic_search_sqlite import SQLiteSemanticSearchEngine

        rag_service = RAGService(
            ai_service=hybrid_ai_service, search_engine=SQLiteSemanticSearchEngine()
        )

        # Use dev organization ID
        org_id = "dev-org-id"

        # Generate response with RAG
        rag_response = await rag_service.query(
            query=chat_request.message, organization_id=org_id, conversation_history=[]
        )

        return {
            "response": rag_response.answer,
            "sources": [
                {
                    "document_id": s.document_id,
                    "title": s.title,
                    "content": s.content,
                    "relevance": s.relevance,
                }
                for s in rag_response.sources
            ],
            "confidence": rag_response.confidence,
            "tokens_used": rag_response.tokens_used,
            "search_time_ms": rag_response.search_time_ms,
            "generation_time_ms": rag_response.generation_time_ms,
        }
    except Exception as e:
        logger.error(f"Test RAG chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# MCP Integration Endpoints
@app.get("/api/mcp/servers")
async def list_mcp_servers(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """List available MCP servers"""
    try:
        # TODO: Filter servers by organization if needed
        return mcp_manager.list_servers()
    except Exception as e:
        logger.error(
            f"MCP list servers error",
            extra={
                "error": str(e),
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )
        return []


@app.post("/api/mcp/servers/{server_name}/connect")
async def connect_mcp_server(
    server_name: str,
    config: dict,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Connect to an MCP server"""
    try:
        # TODO: Add organization context to MCP connections if needed
        await mcp_manager.connect_server(server_name, config)

        # Log the connection attempt
        logger.info(
            f"MCP server connection",
            extra={
                "server_name": server_name,
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )

        return {"message": f"Connected to {server_name} successfully"}
    except Exception as e:
        logger.error(
            f"MCP connection failed",
            extra={
                "error": str(e),
                "server_name": server_name,
                "user_id": current_user.id,
                "organization_id": current_org.id,
            },
        )
        raise HTTPException(status_code=500, detail=f"MCP connection failed: {str(e)}")


# Background task for document processing
async def process_document_background(
    doc_id: str, file_path: str, organization_id: str = None
):
    """Process document in background with organization context"""
    try:
        logger.info(
            f"Starting background processing for document",
            extra={"document_id": doc_id, "organization_id": organization_id},
        )

        # Use the document processor instance with correct parameters
        # Enable metadata extraction by default (can be made configurable)
        extract_metadata = True
        success = await document_processor.process_document(
            doc_id,
            file_path,
            extract_metadata=extract_metadata,
            organization_id=organization_id,
        )

        if success:
            logger.info(
                f"Background processing completed successfully",
                extra={"document_id": doc_id, "organization_id": organization_id},
            )
        else:
            logger.error(
                f"Background processing failed",
                extra={"document_id": doc_id, "organization_id": organization_id},
            )

    except Exception as e:
        logger.error(
            f"Background processing error",
            extra={
                "document_id": doc_id,
                "organization_id": organization_id,
                "error": str(e),
            },
        )

        # Try to update the document status to failed
        try:
            from database import get_db

            db = next(get_db())

            # Verify document belongs to organization before updating
            query = db.query(Document).filter(Document.id == doc_id)
            if organization_id:
                query = query.filter(Document.organization_id == organization_id)

            document = query.first()
            if document:
                document.processing_status = "failed"
                document.error_message = str(e)
                db.commit()
            db.close()
        except Exception as db_error:
            logger.error(
                f"Failed to update document status",
                extra={"document_id": doc_id, "error": str(db_error)},
            )


# AI Preferences and Provider Endpoints
@app.get("/api/ai/preferences")
async def get_ai_preferences(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get AI preferences for current user/organization"""
    return {
        "user_preferences": {
            "provider": current_user.ai_provider_preference or "openai",
            "model_preferences": current_user.ai_model_preferences
            or {"openai": "gpt-4"},
            "consent_given": current_user.ai_consent_given or True,
        },
        "organization_settings": {
            "ai_backend": current_org.ai_backend or "cloud",
            "monthly_budget": current_org.ai_monthly_budget,
            "current_month_cost": current_org.ai_current_month_cost or 0.0,
            "rate_limit_per_minute": current_org.ai_rate_limit_per_minute or 10,
        },
    }


@app.get("/api/ai/provider")
async def get_ai_provider(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get current AI provider information"""
    return {
        "provider": "openai",
        "model": "gpt-4",
        "status": "active",
        "backend": current_org.ai_backend or "cloud",
        "demo_mode": settings.demo_mode
        or os.getenv("DEMO_MODE", "false").lower() == "true",
    }


@app.get("/api/ai/status")
async def get_ai_status(current_user: User = Depends(get_current_user)):
    """Get AI service status"""
    return {
        "status": "operational",
        "provider": "openai",
        "model": "gpt-4",
        "demo_mode": settings.demo_mode
        or os.getenv("DEMO_MODE", "false").lower() == "true",
        "last_check": datetime.utcnow().isoformat(),
    }
