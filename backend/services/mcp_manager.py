# services/mcp_manager.py - MCP (Model Context Protocol) server management
# Enhanced version with legal-specific integrations
import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import email
import imaplib
from email.mime.text import MIMEText
import glob

# Import Court System MCP Server
try:
    from services.mcp_servers.court_system_mcp import CourtSystemMCPServer
except ImportError:
    CourtSystemMCPServer = None

# Note: For enhanced legal-specific MCP functionality, see mcp_manager_enhanced.py
# This base implementation provides general MCP server management


class MCPManager:
    """Manages MCP server connections for data source integration"""

    def __init__(self):
        self.active_servers = {}
        self.server_configs = {}

        # Available MCP server types
        self.available_servers = {
            "filesystem": FileSystemMCP,
            "email": EmailMCP,
            "calendar": CalendarMCP,
            "documents": DocumentsMCP,
            "court_system": self._get_court_system_mcp(),
        }

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all available MCP server types"""
        servers = []

        for server_type, server_class in self.available_servers.items():
            servers.append(
                {
                    "name": server_type,
                    "description": server_class.get_description(),
                    "status": (
                        "active" if server_type in self.active_servers else "available"
                    ),
                    "capabilities": server_class.get_capabilities(),
                }
            )

        return servers

    async def connect_server(self, server_name: str, config: Dict[str, Any]):
        """Connect to an MCP server"""
        if server_name not in self.available_servers:
            raise ValueError(f"Unknown server type: {server_name}")

        server_class = self.available_servers[server_name]
        server_instance = server_class(config)

        # Test connection
        await server_instance.connect()

        # Store active connection
        self.active_servers[server_name] = server_instance
        self.server_configs[server_name] = config

        return True

    async def disconnect_server(self, server_name: str):
        """Disconnect from an MCP server"""
        if server_name in self.active_servers:
            await self.active_servers[server_name].disconnect()
            del self.active_servers[server_name]
            if server_name in self.server_configs:
                del self.server_configs[server_name]

    async def sync_data(self, server_name: str) -> Dict[str, Any]:
        """Sync data from a specific MCP server"""
        if server_name not in self.active_servers:
            raise ValueError(f"Server {server_name} is not connected")

        server = self.active_servers[server_name]
        return await server.sync_data()

    async def query_server(
        self, server_name: str, query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Query a specific MCP server"""
        if server_name not in self.active_servers:
            raise ValueError(f"Server {server_name} is not connected")

        server = self.active_servers[server_name]
        return await server.query(query)

    def _get_court_system_mcp(self):
        """Get Court System MCP Server if available"""
        if CourtSystemMCPServer:
            return CourtSystemMCPServer
        else:
            # Return a placeholder class if not available
            class PlaceholderCourtMCP(BaseMCPServer):
                @classmethod
                def get_description(cls):
                    return "Court System MCP (not installed)"

                @classmethod
                def get_capabilities(cls):
                    return ["court_data_access"]

            return PlaceholderCourtMCP


class BaseMCPServer:
    """Base class for MCP servers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False

    async def connect(self):
        """Connect to the data source"""
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the data source"""
        self.connected = False

    async def sync_data(self) -> Dict[str, Any]:
        """Sync data from the source"""
        raise NotImplementedError

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query the data source"""
        raise NotImplementedError

    @classmethod
    def get_description(cls) -> str:
        """Get server description"""
        return "Base MCP server"

    @classmethod
    def get_capabilities(cls) -> List[str]:
        """Get server capabilities"""
        return []


class FileSystemMCP(BaseMCPServer):
    """File system MCP server for accessing local documents"""

    async def connect(self):
        """Connect to file system"""
        self.base_path = self.config.get("base_path", ".")
        if not os.path.exists(self.base_path):
            raise ValueError(f"Path does not exist: {self.base_path}")
        self.connected = True

    async def sync_data(self) -> Dict[str, Any]:
        """Scan file system for documents"""
        if not self.connected:
            raise ValueError("Not connected to file system")

        file_extensions = self.config.get("extensions", [".pdf", ".docx", ".txt"])
        files = []

        for ext in file_extensions:
            pattern = os.path.join(self.base_path, f"**/*{ext}")
            found_files = glob.glob(pattern, recursive=True)

            for file_path in found_files:
                stat = os.stat(file_path)
                files.append(
                    {
                        "path": file_path,
                        "name": os.path.basename(file_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": ext,
                    }
                )

        return {
            "files": files,
            "total_count": len(files),
            "scanned_at": datetime.utcnow().isoformat(),
        }

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query files based on criteria"""
        sync_result = await self.sync_data()
        files = sync_result["files"]

        # Apply filters
        if "name_pattern" in query:
            pattern = query["name_pattern"].lower()
            files = [f for f in files if pattern in f["name"].lower()]

        if "extension" in query:
            ext = query["extension"]
            files = [f for f in files if f["extension"] == ext]

        if "modified_after" in query:
            after_date = datetime.fromisoformat(query["modified_after"])
            files = [
                f for f in files if datetime.fromisoformat(f["modified"]) > after_date
            ]

        return files

    @classmethod
    def get_description(cls) -> str:
        return "Access local file system documents"

    @classmethod
    def get_capabilities(cls) -> List[str]:
        return ["scan_files", "filter_by_type", "filter_by_date", "read_content"]


class EmailMCP(BaseMCPServer):
    """Email MCP server for accessing email accounts"""

    async def connect(self):
        """Connect to email server"""
        self.email_server = self.config.get("server", "imap.gmail.com")
        self.email_port = self.config.get("port", 993)
        self.username = self.config.get("username")
        self.password = self.config.get("password")

        if not self.username or not self.password:
            raise ValueError("Email credentials required")

        # Test connection
        try:
            mail = imaplib.IMAP4_SSL(self.email_server, self.email_port)
            mail.login(self.username, self.password)
            mail.logout()
            self.connected = True
        except Exception as e:
            raise ValueError(f"Email connection failed: {str(e)}")

    async def sync_data(self) -> Dict[str, Any]:
        """Sync recent emails"""
        if not self.connected:
            raise ValueError("Not connected to email")

        try:
            mail = imaplib.IMAP4_SSL(self.email_server, self.email_port)
            mail.login(self.username, self.password)
            mail.select("INBOX")

            # Get recent emails
            days_back = self.config.get("days_back", 30)
            search_criteria = f'(SINCE "{(datetime.now() - datetime.timedelta(days=days_back)).strftime("%d-%b-%Y")}")'

            status, message_ids = mail.search(None, search_criteria)
            emails = []

            if status == "OK":
                for msg_id in message_ids[0].split()[-50:]:  # Last 50 emails
                    status, msg_data = mail.fetch(msg_id, "(RFC822)")
                    if status == "OK":
                        email_msg = email.message_from_bytes(msg_data[0][1])
                        emails.append(
                            {
                                "id": msg_id.decode(),
                                "subject": email_msg["Subject"],
                                "from": email_msg["From"],
                                "date": email_msg["Date"],
                                "body": self._extract_email_body(email_msg),
                            }
                        )

            mail.logout()

            return {
                "emails": emails,
                "total_count": len(emails),
                "synced_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            raise Exception(f"Email sync failed: {str(e)}")

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query emails based on criteria"""
        sync_result = await self.sync_data()
        emails = sync_result["emails"]

        # Apply filters
        if "subject_contains" in query:
            pattern = query["subject_contains"].lower()
            emails = [e for e in emails if pattern in e["subject"].lower()]

        if "from_contains" in query:
            pattern = query["from_contains"].lower()
            emails = [e for e in emails if pattern in e["from"].lower()]

        return emails

    def _extract_email_body(self, email_msg) -> str:
        """Extract plain text body from email"""
        body = ""

        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = email_msg.get_payload(decode=True).decode()

        return body

    @classmethod
    def get_description(cls) -> str:
        return "Access email accounts for legal correspondence"

    @classmethod
    def get_capabilities(cls) -> List[str]:
        return ["sync_emails", "search_emails", "extract_attachments"]


class CalendarMCP(BaseMCPServer):
    """Calendar MCP server for deadline management"""

    async def connect(self):
        """Connect to calendar service"""
        # Placeholder for calendar connection
        # Could integrate with Google Calendar, Outlook, etc.
        self.calendar_type = self.config.get("type", "google")
        self.connected = True

    async def sync_data(self) -> Dict[str, Any]:
        """Sync calendar events"""
        # Placeholder implementation
        return {"events": [], "synced_at": datetime.utcnow().isoformat()}

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query calendar events"""
        return []

    @classmethod
    def get_description(cls) -> str:
        return "Access calendar for deadline tracking"

    @classmethod
    def get_capabilities(cls) -> List[str]:
        return ["sync_events", "deadline_alerts", "schedule_management"]


class DocumentsMCP(BaseMCPServer):
    """Documents MCP server for practice management integration"""

    async def connect(self):
        """Connect to document management system"""
        self.system_type = self.config.get("system_type", "generic")
        self.connected = True

    async def sync_data(self) -> Dict[str, Any]:
        """Sync documents from practice management system"""
        return {"documents": [], "synced_at": datetime.utcnow().isoformat()}

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query practice management documents"""
        return []

    @classmethod
    def get_description(cls) -> str:
        return "Integration with practice management systems"

    @classmethod
    def get_capabilities(cls) -> List[str]:
        return ["case_documents", "client_files", "billing_records"]
