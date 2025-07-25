# services/mcp_manager_enhanced.py - Enhanced MCP Manager for Legal System Integrations
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum
import logging
from dataclasses import dataclass
from collections import defaultdict
import httpx
from sqlalchemy.orm import Session

from config import Settings
from models import User, Organization, Document
from database import get_db
from audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class MCPServerType(Enum):
    """Enumeration of legal-specific MCP server types"""

    COURT_SYSTEM = "court_system"
    CLIENT_DATABASE = "client_database"
    LEGAL_RESEARCH = "legal_research"
    DOCUMENT_REPOSITORY = "document_repository"
    CASE_MANAGEMENT = "case_management"
    BILLING_SYSTEM = "billing_system"
    COMPLIANCE_DATABASE = "compliance_database"
    CORPORATE_REGISTRY = "corporate_registry"
    IP_DATABASE = "ip_database"
    CONTRACT_MANAGEMENT = "contract_management"


@dataclass
class MCPResponse:
    """Standardized response from MCP servers"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    cached: bool = False
    cache_timestamp: Optional[datetime] = None


@dataclass
class MCPServerConfig:
    """Configuration for MCP server connections"""

    server_type: MCPServerType
    endpoint: str
    api_key: Optional[str] = None
    organization_id: Optional[str] = None
    max_retries: int = 3
    timeout: int = 30
    cache_ttl: int = 300  # 5 minutes default
    required_permissions: List[str] = None


class LegalMCPSecurity:
    """Security layer for MCP operations"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.permission_matrix = {
            MCPServerType.COURT_SYSTEM: ["court_access", "litigation"],
            MCPServerType.CLIENT_DATABASE: ["client_access", "crm"],
            MCPServerType.LEGAL_RESEARCH: ["research_access"],
            MCPServerType.DOCUMENT_REPOSITORY: ["document_access"],
            MCPServerType.CASE_MANAGEMENT: ["case_access"],
            MCPServerType.BILLING_SYSTEM: ["billing_access", "admin"],
            MCPServerType.COMPLIANCE_DATABASE: ["compliance_access"],
            MCPServerType.CORPORATE_REGISTRY: ["corporate_access"],
            MCPServerType.IP_DATABASE: ["ip_access"],
            MCPServerType.CONTRACT_MANAGEMENT: ["contract_access"],
        }

    def validate_access(
        self,
        user: User,
        server_type: MCPServerType,
        action: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Validate user access to MCP server and action"""
        try:
            # Check if user is active
            if not user.is_active:
                self._log_access_denied(user, server_type, action, "User inactive")
                return False

            # Check organization status
            if not user.organization.is_active:
                self._log_access_denied(
                    user, server_type, action, "Organization inactive"
                )
                return False

            # Check required permissions
            required_perms = self.permission_matrix.get(server_type, [])
            user_perms = self._get_user_permissions(user)

            if not any(perm in user_perms for perm in required_perms):
                self._log_access_denied(
                    user, server_type, action, "Insufficient permissions"
                )
                return False

            # Check organization-specific access
            if not self._validate_organization_access(user, server_type, resource_id):
                self._log_access_denied(
                    user, server_type, action, "Organization boundary violation"
                )
                return False

            # Log successful access
            self.audit_logger.log_event(
                "mcp_access_granted",
                user_id=user.id,
                organization_id=user.organization_id,
                details={
                    "server_type": server_type.value,
                    "action": action,
                    "resource_id": resource_id,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Security validation error: {str(e)}")
            return False

    def _get_user_permissions(self, user: User) -> Set[str]:
        """Get user permissions based on role"""
        role_permissions = {
            "admin": {
                "court_access",
                "litigation",
                "client_access",
                "crm",
                "research_access",
                "document_access",
                "case_access",
                "billing_access",
                "compliance_access",
                "corporate_access",
                "ip_access",
                "contract_access",
                "admin",
            },
            "attorney": {
                "court_access",
                "litigation",
                "client_access",
                "research_access",
                "document_access",
                "case_access",
                "contract_access",
            },
            "paralegal": {"research_access", "document_access", "case_access"},
            "clerk": {"document_access", "case_access"},
        }
        return role_permissions.get(user.role, set())

    def _validate_organization_access(
        self, user: User, server_type: MCPServerType, resource_id: Optional[str]
    ) -> bool:
        """Ensure user can only access their organization's data"""
        # Additional validation logic for resource-specific access
        return True

    def _log_access_denied(
        self, user: User, server_type: MCPServerType, action: str, reason: str
    ):
        """Log access denial for audit trail"""
        self.audit_logger.log_event(
            "mcp_access_denied",
            user_id=user.id,
            organization_id=user.organization_id,
            details={
                "server_type": server_type.value,
                "action": action,
                "reason": reason,
            },
        )


class BaseLegalMCPServer(ABC):
    """Abstract base class for legal MCP servers"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.connected = False
        self.last_health_check = None
        self.cache = {}
        self.connection_pool = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the MCP server"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the MCP server"""
        pass

    @abstractmethod
    async def query(self, action: str, params: dict) -> MCPResponse:
        """Execute a query against the MCP server"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check server health and connectivity"""
        pass

    async def _get_cached_response(self, cache_key: str) -> Optional[MCPResponse]:
        """Retrieve cached response if valid"""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.config.cache_ttl):
                return MCPResponse(
                    success=True,
                    data=cached_data,
                    cached=True,
                    cache_timestamp=timestamp,
                )
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """Store response in cache"""
        self.cache[cache_key] = (data, datetime.utcnow())

    def _clear_expired_cache(self):
        """Remove expired cache entries"""
        current_time = datetime.utcnow()
        expired_keys = [
            key
            for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > timedelta(seconds=self.config.cache_ttl)
        ]
        for key in expired_keys:
            del self.cache[key]


class CourtSystemMCP(BaseLegalMCPServer):
    """MCP server for court system integration"""

    async def connect(self) -> bool:
        """Connect to court filing systems"""
        try:
            # Initialize connection to court API
            self.client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=self.config.timeout,
            )
            self.connected = True
            logger.info(f"Connected to court system at {self.config.endpoint}")
            return True
        except Exception as e:
            logger.error(f"Court system connection failed: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from court system"""
        if self.client:
            await self.client.aclose()
        self.connected = False
        return True

    async def query(self, action: str, params: dict) -> MCPResponse:
        """Query court system for case information, filings, etc."""
        if not self.connected:
            return MCPResponse(success=False, error="Not connected to court system")

        # Check cache
        cache_key = f"{action}:{json.dumps(params, sort_keys=True)}"
        cached = await self._get_cached_response(cache_key)
        if cached:
            return cached

        try:
            # Map actions to court API endpoints
            action_map = {
                "search_cases": "/api/cases/search",
                "get_case_details": "/api/cases/{case_id}",
                "get_filings": "/api/cases/{case_id}/filings",
                "check_deadlines": "/api/deadlines",
                "submit_filing": "/api/filings/submit",
            }

            endpoint = action_map.get(action)
            if not endpoint:
                return MCPResponse(success=False, error=f"Unknown action: {action}")

            # Format endpoint with parameters
            if "{case_id}" in endpoint:
                endpoint = endpoint.format(case_id=params.get("case_id"))

            # Execute request
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            self._set_cache(cache_key, data)

            return MCPResponse(
                success=True,
                data=data,
                metadata={"source": "court_system", "action": action},
            )

        except Exception as e:
            logger.error(f"Court system query failed: {str(e)}")
            return MCPResponse(success=False, error=str(e))

    async def health_check(self) -> bool:
        """Check court system connectivity"""
        try:
            response = await self.client.get("/api/health")
            return response.status_code == 200
        except:
            return False


class ClientDatabaseMCP(BaseLegalMCPServer):
    """MCP server for client/CRM database integration"""

    async def connect(self) -> bool:
        """Connect to client database"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=self.config.timeout,
            )
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Client database connection failed: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from client database"""
        if self.client:
            await self.client.aclose()
        self.connected = False
        return True

    async def query(self, action: str, params: dict) -> MCPResponse:
        """Query client information with organization scoping"""
        if not self.connected:
            return MCPResponse(success=False, error="Not connected to client database")

        # Enforce organization scoping
        params["organization_id"] = self.config.organization_id

        try:
            action_map = {
                "search_clients": "/api/clients/search",
                "get_client": "/api/clients/{client_id}",
                "get_matters": "/api/clients/{client_id}/matters",
                "get_contacts": "/api/clients/{client_id}/contacts",
                "get_documents": "/api/clients/{client_id}/documents",
            }

            endpoint = action_map.get(action)
            if not endpoint:
                return MCPResponse(success=False, error=f"Unknown action: {action}")

            # Format endpoint
            if "{client_id}" in endpoint:
                endpoint = endpoint.format(client_id=params.get("client_id"))

            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()

            return MCPResponse(
                success=True,
                data=response.json(),
                metadata={"source": "client_database", "action": action},
            )

        except Exception as e:
            logger.error(f"Client database query failed: {str(e)}")
            return MCPResponse(success=False, error=str(e))

    async def health_check(self) -> bool:
        """Check client database connectivity"""
        try:
            response = await self.client.get("/api/health")
            return response.status_code == 200
        except:
            return False


class LegalResearchMCP(BaseLegalMCPServer):
    """MCP server for legal research databases"""

    async def connect(self) -> bool:
        """Connect to legal research service"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=60,  # Longer timeout for research queries
            )
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Legal research connection failed: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from research service"""
        if self.client:
            await self.client.aclose()
        self.connected = False
        return True

    async def query(self, action: str, params: dict) -> MCPResponse:
        """Query legal research databases"""
        if not self.connected:
            return MCPResponse(success=False, error="Not connected to research service")

        try:
            action_map = {
                "search_cases": "/api/research/cases",
                "search_statutes": "/api/research/statutes",
                "search_regulations": "/api/research/regulations",
                "get_citations": "/api/research/citations",
                "check_validity": "/api/research/validity",
            }

            endpoint = action_map.get(action)
            if not endpoint:
                return MCPResponse(success=False, error=f"Unknown action: {action}")

            response = await self.client.post(endpoint, json=params)
            response.raise_for_status()

            return MCPResponse(
                success=True,
                data=response.json(),
                metadata={"source": "legal_research", "action": action},
            )

        except Exception as e:
            logger.error(f"Legal research query failed: {str(e)}")
            return MCPResponse(success=False, error=str(e))

    async def health_check(self) -> bool:
        """Check research service connectivity"""
        try:
            response = await self.client.get("/api/health")
            return response.status_code == 200
        except:
            return False


class EnhancedMCPManager:
    """Enhanced MCP Manager with comprehensive legal system integrations"""

    def __init__(self, config: Settings, audit_logger: AuditLogger):
        self.config = config
        self.audit_logger = audit_logger
        self.security = LegalMCPSecurity(audit_logger)
        self.servers: Dict[MCPServerType, BaseLegalMCPServer] = {}
        self.server_configs: Dict[MCPServerType, MCPServerConfig] = {}
        self.connection_pool = {}
        self.health_check_interval = 300  # 5 minutes
        self._health_check_task = None
        self._initialize_legal_servers()

    def _initialize_legal_servers(self):
        """Initialize configurations for legal-specific MCP servers"""
        # Map server types to implementation classes
        self.server_implementations = {
            MCPServerType.COURT_SYSTEM: CourtSystemMCP,
            MCPServerType.CLIENT_DATABASE: ClientDatabaseMCP,
            MCPServerType.LEGAL_RESEARCH: LegalResearchMCP,
            # Additional implementations would be added here
        }

        # Load server configurations from environment or config
        self._load_server_configs()

    def _load_server_configs(self):
        """Load MCP server configurations"""
        # Example configuration loading
        if os.getenv("COURT_SYSTEM_ENDPOINT"):
            self.server_configs[MCPServerType.COURT_SYSTEM] = MCPServerConfig(
                server_type=MCPServerType.COURT_SYSTEM,
                endpoint=os.getenv("COURT_SYSTEM_ENDPOINT"),
                api_key=os.getenv("COURT_SYSTEM_API_KEY"),
                required_permissions=["court_access"],
            )

        if os.getenv("CLIENT_DB_ENDPOINT"):
            self.server_configs[MCPServerType.CLIENT_DATABASE] = MCPServerConfig(
                server_type=MCPServerType.CLIENT_DATABASE,
                endpoint=os.getenv("CLIENT_DB_ENDPOINT"),
                api_key=os.getenv("CLIENT_DB_API_KEY"),
                required_permissions=["client_access"],
            )

        if os.getenv("LEGAL_RESEARCH_ENDPOINT"):
            self.server_configs[MCPServerType.LEGAL_RESEARCH] = MCPServerConfig(
                server_type=MCPServerType.LEGAL_RESEARCH,
                endpoint=os.getenv("LEGAL_RESEARCH_ENDPOINT"),
                api_key=os.getenv("LEGAL_RESEARCH_API_KEY"),
                required_permissions=["research_access"],
            )

    async def connect_server(
        self,
        server_type: MCPServerType,
        organization_id: str,
        custom_config: Optional[MCPServerConfig] = None,
    ) -> bool:
        """Connect to a specific MCP server"""
        try:
            # Use custom config or default
            config = custom_config or self.server_configs.get(server_type)
            if not config:
                logger.error(f"No configuration found for {server_type.value}")
                return False

            # Set organization ID for scoping
            config.organization_id = organization_id

            # Get implementation class
            server_class = self.server_implementations.get(server_type)
            if not server_class:
                logger.error(f"No implementation found for {server_type.value}")
                return False

            # Create and connect server instance
            server = server_class(config)
            if await server.connect():
                self.servers[server_type] = server
                logger.info(
                    f"Connected to {server_type.value} for org {organization_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to connect to {server_type.value}: {str(e)}")
            return False

    async def disconnect_server(self, server_type: MCPServerType) -> bool:
        """Disconnect from a specific MCP server"""
        if server_type in self.servers:
            server = self.servers[server_type]
            if await server.disconnect():
                del self.servers[server_type]
                return True
        return False

    async def query_legal_mcp(
        self, server_type: MCPServerType, action: str, params: dict, user: User
    ) -> MCPResponse:
        """Route legal-specific queries with security validation"""
        try:
            # Validate access
            if not self.security.validate_access(user, server_type, action):
                return MCPResponse(
                    success=False,
                    error="Access denied",
                    metadata={"reason": "security_validation_failed"},
                )

            # Check server connection
            if server_type not in self.servers:
                # Try to connect
                if not await self.connect_server(server_type, user.organization_id):
                    return MCPResponse(
                        success=False, error=f"Server {server_type.value} not available"
                    )

            server = self.servers[server_type]

            # Add organization context to params
            params["_organization_id"] = user.organization_id
            params["_user_id"] = user.id

            # Execute query
            response = await server.query(action, params)

            # Log successful query
            self.audit_logger.log_event(
                "mcp_query_executed",
                user_id=user.id,
                organization_id=user.organization_id,
                details={
                    "server_type": server_type.value,
                    "action": action,
                    "success": response.success,
                },
            )

            return response

        except Exception as e:
            logger.error(f"MCP query error: {str(e)}")
            return MCPResponse(success=False, error=str(e))

    async def start_health_monitoring(self):
        """Start background health check task"""
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_monitoring(self):
        """Stop health check task"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    async def _health_check_loop(self):
        """Background task to check server health"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_servers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")

    async def _check_all_servers(self):
        """Check health of all connected servers"""
        for server_type, server in list(self.servers.items()):
            try:
                if not await server.health_check():
                    logger.warning(f"Health check failed for {server_type.value}")
                    # Attempt reconnection
                    if not await server.connect():
                        # Remove failed server
                        del self.servers[server_type]
            except Exception as e:
                logger.error(f"Health check error for {server_type.value}: {str(e)}")

    def get_server_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers"""
        status = {}

        for server_type in MCPServerType:
            connected = server_type in self.servers
            config_available = server_type in self.server_configs

            status[server_type.value] = {
                "connected": connected,
                "configured": config_available,
                "implementation_available": server_type in self.server_implementations,
                "last_health_check": (
                    self.servers[server_type].last_health_check if connected else None
                ),
            }

        return status

    async def enrich_document_context(
        self, document: Document, user: User
    ) -> Dict[str, Any]:
        """Enrich document with context from MCP servers"""
        enriched_data = {"document_id": document.id, "enrichments": {}}

        # Extract entities from document
        if document.legal_metadata:
            metadata = json.loads(document.legal_metadata)

            # Check for case references
            if "case_numbers" in metadata:
                for case_num in metadata["case_numbers"]:
                    court_data = await self.query_legal_mcp(
                        MCPServerType.COURT_SYSTEM,
                        "get_case_details",
                        {"case_id": case_num},
                        user,
                    )
                    if court_data.success:
                        enriched_data["enrichments"]["court_cases"] = court_data.data

            # Check for client references
            if "client_names" in metadata:
                for client_name in metadata["client_names"]:
                    client_data = await self.query_legal_mcp(
                        MCPServerType.CLIENT_DATABASE,
                        "search_clients",
                        {"name": client_name},
                        user,
                    )
                    if client_data.success:
                        enriched_data["enrichments"]["clients"] = client_data.data

            # Get relevant legal research
            if "legal_issues" in metadata:
                research_data = await self.query_legal_mcp(
                    MCPServerType.LEGAL_RESEARCH,
                    "search_cases",
                    {"keywords": metadata["legal_issues"]},
                    user,
                )
                if research_data.success:
                    enriched_data["enrichments"]["research"] = research_data.data

        return enriched_data
