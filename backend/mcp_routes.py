# mcp_routes.py - API routes for MCP server management
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from auth_middleware import get_current_user, get_current_organization
from models import User, Organization
from database import get_db
from sqlalchemy.orm import Session
from services.mcp_manager_enhanced import (
    EnhancedMCPManager, 
    MCPServerType, 
    MCPServerConfig,
    MCPResponse
)
from audit_logger import AuditLogger
from config import settings
from database import SessionLocal

# Initialize dependencies
config = settings
audit_logger = AuditLogger(SessionLocal)
mcp_manager = EnhancedMCPManager(config, audit_logger)

# Create router
router = APIRouter(prefix="/api/mcp", tags=["MCP Management"])

# Request/Response models
class MCPServerStatusResponse(BaseModel):
    """Response model for server status"""
    server_type: str
    connected: bool
    configured: bool
    implementation_available: bool
    last_health_check: Optional[datetime]

class MCPServerListResponse(BaseModel):
    """Response model for listing MCP servers"""
    servers: List[MCPServerStatusResponse]
    total_count: int

class MCPConnectRequest(BaseModel):
    """Request model for connecting to MCP server"""
    server_type: str
    config: Optional[Dict[str, Any]] = None

class MCPQueryRequest(BaseModel):
    """Request model for MCP queries"""
    server_type: str
    action: str
    params: Dict[str, Any] = {}

class MCPQueryResponse(BaseModel):
    """Response model for MCP queries"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
    cached: bool = False

@router.get("/servers", response_model=MCPServerListResponse)
async def list_mcp_servers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all available MCP servers and their status"""
    try:
        # Check user permissions
        if current_user.role not in ["admin", "attorney"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view MCP servers"
            )
        
        # Get server status
        server_status = mcp_manager.get_server_status()
        
        # Format response
        servers = []
        for server_type, status_info in server_status.items():
            servers.append(MCPServerStatusResponse(
                server_type=server_type,
                connected=status_info["connected"],
                configured=status_info["configured"],
                implementation_available=status_info["implementation_available"],
                last_health_check=status_info["last_health_check"]
            ))
        
        # Log access
        audit_logger.log_event(
            "mcp_servers_listed",
            user_id=current_user.id,
            organization_id=current_user.organization_id
        )
        
        return MCPServerListResponse(
            servers=servers,
            total_count=len(servers)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list MCP servers: {str(e)}"
        )

@router.get("/servers/{server_type}/health")
async def check_server_health(
    server_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check health of a specific MCP server"""
    try:
        # Validate server type
        try:
            server_enum = MCPServerType(server_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid server type: {server_type}"
            )
        
        # Check if server is connected
        if server_enum not in mcp_manager.servers:
            return {
                "server_type": server_type,
                "healthy": False,
                "connected": False,
                "message": "Server not connected"
            }
        
        # Perform health check
        server = mcp_manager.servers[server_enum]
        is_healthy = await server.health_check()
        
        return {
            "server_type": server_type,
            "healthy": is_healthy,
            "connected": True,
            "last_check": datetime.utcnow(),
            "message": "Server is healthy" if is_healthy else "Health check failed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

@router.post("/connect")
async def connect_mcp_server(
    request: MCPConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect to a specific MCP server"""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage MCP connections"
            )
        
        # Validate server type
        try:
            server_enum = MCPServerType(request.server_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid server type: {request.server_type}"
            )
        
        # Connect to server
        custom_config = None
        if request.config:
            custom_config = MCPServerConfig(
                server_type=server_enum,
                endpoint=request.config.get("endpoint"),
                api_key=request.config.get("api_key"),
                organization_id=current_user.organization_id
            )
        
        success = await mcp_manager.connect_server(
            server_enum,
            current_user.organization_id,
            custom_config
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to {request.server_type}"
            )
        
        # Log connection
        audit_logger.log_event(
            "mcp_server_connected",
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            details={"server_type": request.server_type}
        )
        
        return {
            "success": True,
            "message": f"Successfully connected to {request.server_type}",
            "server_type": request.server_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection failed: {str(e)}"
        )

@router.post("/disconnect/{server_type}")
async def disconnect_mcp_server(
    server_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect from a specific MCP server"""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage MCP connections"
            )
        
        # Validate server type
        try:
            server_enum = MCPServerType(server_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid server type: {server_type}"
            )
        
        # Disconnect from server
        success = await mcp_manager.disconnect_server(server_enum)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server {server_type} not connected"
            )
        
        # Log disconnection
        audit_logger.log_event(
            "mcp_server_disconnected",
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            details={"server_type": server_type}
        )
        
        return {
            "success": True,
            "message": f"Successfully disconnected from {server_type}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disconnection failed: {str(e)}"
        )

@router.post("/query", response_model=MCPQueryResponse)
async def query_mcp_server(
    request: MCPQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a query against an MCP server with security validation"""
    try:
        # Validate server type
        try:
            server_enum = MCPServerType(request.server_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid server type: {request.server_type}"
            )
        
        # Execute query with security validation
        response = await mcp_manager.query_legal_mcp(
            server_enum,
            request.action,
            request.params,
            current_user
        )
        
        # Check for access denied
        if not response.success and response.metadata and response.metadata.get("reason") == "security_validation_failed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to MCP resource"
            )
        
        return MCPQueryResponse(
            success=response.success,
            data=response.data,
            error=response.error,
            metadata=response.metadata,
            cached=response.cached
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )

@router.get("/document/{document_id}/context")
async def get_document_mcp_context(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get MCP context enrichment for a specific document"""
    try:
        # Get document
        from models import Document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get enriched context
        context = await mcp_manager.enrich_document_context(document, current_user)
        
        return {
            "document_id": document_id,
            "enrichments": context.get("enrichments", {}),
            "enrichment_timestamp": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context enrichment failed: {str(e)}"
        )

# Add router to main application
def include_mcp_routes(app):
    """Include MCP routes in the main FastAPI application"""
    app.include_router(router)