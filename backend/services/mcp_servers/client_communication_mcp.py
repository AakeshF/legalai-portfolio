# services/mcp_servers/client_communication_mcp.py - Client Communication MCP Server

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
import logging
from collections import defaultdict

from .base_legal_mcp import BaseLegalMCPServer
from .communication_integrations import (
    EmailIntegration,
    PhoneSystemIntegration,
    SMSIntegration,
    CalendarIntegration
)

logger = logging.getLogger(__name__)

class CommunicationType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    MEETING = "meeting"
    LETTER = "letter"
    FAX = "fax"
    PORTAL_MESSAGE = "portal_message"

class PrivilegeType(Enum):
    ATTORNEY_CLIENT = "attorney_client"
    WORK_PRODUCT = "work_product"
    CONFIDENTIAL = "confidential"
    NOT_PRIVILEGED = "not_privileged"

@dataclass
class Communication:
    id: str
    matter_id: str
    client_id: str
    communication_type: CommunicationType
    direction: str  # inbound/outbound
    date: datetime
    participants: List[Dict[str, Any]]
    subject: Optional[str]
    content: Optional[str]
    attachments: List[Dict[str, Any]]
    privilege_type: PrivilegeType
    is_privileged: bool
    tags: List[str]
    follow_up_required: bool
    metadata: Dict[str, Any]

@dataclass
class FollowUp:
    id: str
    matter_id: str
    communication_id: str
    due_date: datetime
    description: str
    priority: str  # low, medium, high, critical
    assigned_to: Optional[str]
    auto_escalate: bool
    completed: bool = False
    completed_date: Optional[datetime] = None

@dataclass
class PrivilegeLog:
    matter_id: str
    entries: List[Dict[str, Any]]
    generated_date: datetime
    date_range: Tuple[date, date]
    total_entries: int
    privileged_count: int

@dataclass
class DateRange:
    start_date: date
    end_date: date

class ClientCommunicationMCPServer(BaseLegalMCPServer):
    """MCP Server for comprehensive client communication tracking"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize integrations
        self.integrations = {
            "email": EmailIntegration(),
            "phone": PhoneSystemIntegration(),
            "sms": SMSIntegration(),
            "calendar": CalendarIntegration()
        }
        
        # Initialize managers
        self.privilege_generator = PrivilegeLogGenerator()
        self.follow_up_manager = FollowUpManager()
        
        # Communication storage (in production, this would be a database)
        self.communications: Dict[str, Communication] = {}
        self.follow_ups: Dict[str, FollowUp] = {}
        
    async def query(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute communication-related queries"""
        actions = {
            "log_communication": self._log_communication,
            "get_communication_history": self._get_history,
            "generate_privilege_log": self._generate_privilege_log,
            "set_follow_up": self._set_follow_up,
            "search_communications": self._search_communications,
            "sync_emails": self._sync_emails,
            "send_tracked_email": self._send_tracked_email,
            "get_follow_ups": self._get_follow_ups,
            "mark_follow_up_complete": self._mark_follow_up_complete,
            "get_communication_stats": self._get_communication_stats
        }
        
        if action not in actions:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
            
        try:
            return await actions[action](params)
        except Exception as e:
            logger.error(f"Communication MCP error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities"""
        return {
            "server_name": "Client Communication MCP Server",
            "version": "1.0.0",
            "supported_types": [t.value for t in CommunicationType],
            "integrations": list(self.integrations.keys()),
            "actions": {
                "log_communication": {
                    "description": "Log a client communication",
                    "params": ["matter_id", "client_id", "type", "content"]
                },
                "get_communication_history": {
                    "description": "Get communication history for a matter",
                    "params": ["matter_id", "date_range", "type_filter"]
                },
                "generate_privilege_log": {
                    "description": "Generate privilege log for court",
                    "params": ["matter_id", "date_range"]
                },
                "set_follow_up": {
                    "description": "Set a follow-up for communication",
                    "params": ["communication_id", "due_date", "description"]
                },
                "search_communications": {
                    "description": "Search communications",
                    "params": ["query", "filters"]
                }
            }
        }
        
    async def _log_communication(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Log a new client communication"""
        self.validate_params(params, ["matter_id", "client_id", "type"])
        
        # Create communication record
        comm_id = f"comm_{datetime.utcnow().timestamp()}"
        
        # Determine privilege status
        privilege_type = self._determine_privilege(params)
        
        communication = Communication(
            id=comm_id,
            matter_id=params["matter_id"],
            client_id=params["client_id"],
            communication_type=CommunicationType(params["type"]),
            direction=params.get("direction", "outbound"),
            date=datetime.fromisoformat(params.get("date", datetime.utcnow().isoformat())),
            participants=params.get("participants", []),
            subject=params.get("subject"),
            content=params.get("content"),
            attachments=params.get("attachments", []),
            privilege_type=privilege_type,
            is_privileged=privilege_type != PrivilegeType.NOT_PRIVILEGED,
            tags=params.get("tags", []),
            follow_up_required=params.get("follow_up_required", False),
            metadata=params.get("metadata", {})
        )
        
        # Store communication
        self.communications[comm_id] = communication
        
        # Check for auto follow-ups
        if communication.follow_up_required:
            follow_ups = await self.follow_up_manager.create_smart_follow_ups(communication)
            for follow_up in follow_ups:
                self.follow_ups[follow_up.id] = follow_up
                
        # Log audit trail
        self._log_audit_trail(communication, "created")
        
        return {
            "success": True,
            "communication_id": comm_id,
            "privileged": communication.is_privileged,
            "follow_ups_created": len(follow_ups) if communication.follow_up_required else 0
        }
        
    async def _get_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get communication history for a matter"""
        self.validate_params(params, ["matter_id"])
        
        matter_id = params["matter_id"]
        date_range = self._parse_date_range(params.get("date_range"))
        type_filter = params.get("type_filter")
        
        # Filter communications
        communications = []
        for comm in self.communications.values():
            if comm.matter_id != matter_id:
                continue
                
            if date_range and not (date_range.start_date <= comm.date.date() <= date_range.end_date):
                continue
                
            if type_filter and comm.communication_type.value not in type_filter:
                continue
                
            communications.append(self._communication_to_dict(comm))
            
        # Sort by date
        communications.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "success": True,
            "matter_id": matter_id,
            "communications": communications,
            "total": len(communications),
            "date_range": {
                "start": date_range.start_date.isoformat() if date_range else None,
                "end": date_range.end_date.isoformat() if date_range else None
            }
        }
        
    async def _generate_privilege_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate privilege log for court requirements"""
        self.validate_params(params, ["matter_id"])
        
        matter_id = params["matter_id"]
        date_range = self._parse_date_range(params.get("date_range"))
        
        # Generate privilege log
        privilege_log = await self.privilege_generator.generate_privilege_log(
            matter_id=matter_id,
            date_range=date_range,
            communications=self.communications
        )
        
        return {
            "success": True,
            "privilege_log": {
                "matter_id": privilege_log.matter_id,
                "generated_date": privilege_log.generated_date.isoformat(),
                "date_range": {
                    "start": privilege_log.date_range[0].isoformat(),
                    "end": privilege_log.date_range[1].isoformat()
                },
                "total_entries": privilege_log.total_entries,
                "privileged_count": privilege_log.privileged_count,
                "entries": privilege_log.entries
            }
        }
        
    async def _set_follow_up(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set a follow-up for a communication"""
        self.validate_params(params, ["communication_id", "due_date", "description"])
        
        comm_id = params["communication_id"]
        if comm_id not in self.communications:
            raise ValueError(f"Communication {comm_id} not found")
            
        communication = self.communications[comm_id]
        
        follow_up = FollowUp(
            id=f"followup_{datetime.utcnow().timestamp()}",
            matter_id=communication.matter_id,
            communication_id=comm_id,
            due_date=datetime.fromisoformat(params["due_date"]),
            description=params["description"],
            priority=params.get("priority", "medium"),
            assigned_to=params.get("assigned_to"),
            auto_escalate=params.get("auto_escalate", True)
        )
        
        self.follow_ups[follow_up.id] = follow_up
        
        return {
            "success": True,
            "follow_up_id": follow_up.id,
            "due_date": follow_up.due_date.isoformat()
        }
        
    async def _search_communications(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search communications with various filters"""
        query = params.get("query", "")
        filters = params.get("filters", {})
        
        results = []
        
        for comm in self.communications.values():
            # Text search
            if query:
                searchable_text = " ".join([
                    comm.subject or "",
                    comm.content or "",
                    " ".join(comm.tags)
                ]).lower()
                
                if query.lower() not in searchable_text:
                    continue
                    
            # Apply filters
            if filters.get("matter_id") and comm.matter_id != filters["matter_id"]:
                continue
                
            if filters.get("client_id") and comm.client_id != filters["client_id"]:
                continue
                
            if filters.get("privileged_only") and not comm.is_privileged:
                continue
                
            if filters.get("type") and comm.communication_type.value != filters["type"]:
                continue
                
            results.append(self._communication_to_dict(comm))
            
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results)
        }
        
    async def _sync_emails(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sync emails from configured email service"""
        self.validate_params(params, ["mailbox_config"])
        
        mailbox_config = params["mailbox_config"]
        matter_id = params.get("matter_id")
        
        # Sync emails using integration
        emails = await self.integrations["email"].sync_emails(mailbox_config)
        
        # Process and log emails
        logged_count = 0
        for email in emails:
            if matter_id and not self._email_matches_matter(email, matter_id):
                continue
                
            # Create communication from email
            await self._log_communication({
                "matter_id": matter_id or email.get("matter_id"),
                "client_id": email.get("client_id"),
                "type": "email",
                "direction": email.get("direction", "inbound"),
                "date": email.get("date"),
                "participants": email.get("participants"),
                "subject": email.get("subject"),
                "content": email.get("content"),
                "attachments": email.get("attachments", [])
            })
            logged_count += 1
            
        return {
            "success": True,
            "emails_synced": len(emails),
            "emails_logged": logged_count
        }
        
    async def _send_tracked_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send and track an email"""
        self.validate_params(params, ["email_data", "matter_id"])
        
        email_data = params["email_data"]
        matter_id = params["matter_id"]
        
        # Send email via integration
        result = await self.integrations["email"].send_tracked_email(email_data)
        
        if result["success"]:
            # Log the sent email
            await self._log_communication({
                "matter_id": matter_id,
                "client_id": email_data.get("client_id"),
                "type": "email",
                "direction": "outbound",
                "participants": email_data.get("to", []),
                "subject": email_data.get("subject"),
                "content": email_data.get("body"),
                "attachments": email_data.get("attachments", []),
                "metadata": {
                    "message_id": result.get("message_id"),
                    "sent_timestamp": result.get("timestamp")
                }
            })
            
        return result
        
    async def _get_follow_ups(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get follow-ups for a matter or user"""
        matter_id = params.get("matter_id")
        assigned_to = params.get("assigned_to")
        include_completed = params.get("include_completed", False)
        
        follow_ups = []
        
        for follow_up in self.follow_ups.values():
            if matter_id and follow_up.matter_id != matter_id:
                continue
                
            if assigned_to and follow_up.assigned_to != assigned_to:
                continue
                
            if not include_completed and follow_up.completed:
                continue
                
            follow_ups.append(self._follow_up_to_dict(follow_up))
            
        # Sort by due date
        follow_ups.sort(key=lambda x: x["due_date"])
        
        return {
            "success": True,
            "follow_ups": follow_ups,
            "total": len(follow_ups)
        }
        
    async def _mark_follow_up_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a follow-up as complete"""
        self.validate_params(params, ["follow_up_id"])
        
        follow_up_id = params["follow_up_id"]
        if follow_up_id not in self.follow_ups:
            raise ValueError(f"Follow-up {follow_up_id} not found")
            
        follow_up = self.follow_ups[follow_up_id]
        follow_up.completed = True
        follow_up.completed_date = datetime.utcnow()
        
        return {
            "success": True,
            "follow_up_id": follow_up_id,
            "completed_date": follow_up.completed_date.isoformat()
        }
        
    async def _get_communication_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get communication statistics"""
        matter_id = params.get("matter_id")
        date_range = self._parse_date_range(params.get("date_range"))
        
        stats = defaultdict(int)
        privileged_count = 0
        
        for comm in self.communications.values():
            if matter_id and comm.matter_id != matter_id:
                continue
                
            if date_range and not (date_range.start_date <= comm.date.date() <= date_range.end_date):
                continue
                
            stats[comm.communication_type.value] += 1
            stats[f"{comm.direction}_count"] += 1
            
            if comm.is_privileged:
                privileged_count += 1
                
        return {
            "success": True,
            "stats": dict(stats),
            "total_communications": sum(v for k, v in stats.items() if not k.endswith("_count")),
            "privileged_count": privileged_count
        }
        
    def _determine_privilege(self, params: Dict[str, Any]) -> PrivilegeType:
        """Determine privilege type for communication"""
        # Check if attorney is participant
        participants = params.get("participants", [])
        has_attorney = any(p.get("role") == "attorney" for p in participants)
        
        # Check communication type
        comm_type = params.get("type")
        
        # Apply privilege rules
        if has_attorney and comm_type in ["email", "phone", "meeting"]:
            # Check if work product
            if params.get("tags") and "work_product" in params["tags"]:
                return PrivilegeType.WORK_PRODUCT
            else:
                return PrivilegeType.ATTORNEY_CLIENT
                
        elif params.get("confidential", False):
            return PrivilegeType.CONFIDENTIAL
            
        return PrivilegeType.NOT_PRIVILEGED
        
    def _parse_date_range(self, date_range_param: Optional[Dict]) -> Optional[DateRange]:
        """Parse date range from parameters"""
        if not date_range_param:
            return None
            
        return DateRange(
            start_date=date.fromisoformat(date_range_param["start"]),
            end_date=date.fromisoformat(date_range_param["end"])
        )
        
    def _communication_to_dict(self, comm: Communication) -> Dict[str, Any]:
        """Convert communication to dictionary"""
        return {
            "id": comm.id,
            "matter_id": comm.matter_id,
            "client_id": comm.client_id,
            "type": comm.communication_type.value,
            "direction": comm.direction,
            "date": comm.date.isoformat(),
            "participants": comm.participants,
            "subject": comm.subject,
            "content": comm.content if not comm.is_privileged else "[PRIVILEGED]",
            "attachments": comm.attachments,
            "privilege_type": comm.privilege_type.value,
            "is_privileged": comm.is_privileged,
            "tags": comm.tags,
            "follow_up_required": comm.follow_up_required
        }
        
    def _follow_up_to_dict(self, follow_up: FollowUp) -> Dict[str, Any]:
        """Convert follow-up to dictionary"""
        return {
            "id": follow_up.id,
            "matter_id": follow_up.matter_id,
            "communication_id": follow_up.communication_id,
            "due_date": follow_up.due_date.isoformat(),
            "description": follow_up.description,
            "priority": follow_up.priority,
            "assigned_to": follow_up.assigned_to,
            "auto_escalate": follow_up.auto_escalate,
            "completed": follow_up.completed,
            "completed_date": follow_up.completed_date.isoformat() if follow_up.completed_date else None
        }
        
    def _email_matches_matter(self, email: Dict[str, Any], matter_id: str) -> bool:
        """Check if email belongs to a matter"""
        # Simple implementation - in production would use more sophisticated matching
        return True
        
    def _log_audit_trail(self, communication: Communication, action: str):
        """Log audit trail for communication"""
        logger.info(f"Audit: {action} communication {communication.id} for matter {communication.matter_id}")


class PrivilegeLogGenerator:
    """Generate privilege logs for court requirements"""
    
    async def generate_privilege_log(
        self,
        matter_id: str,
        date_range: Optional[DateRange],
        communications: Dict[str, Communication]
    ) -> PrivilegeLog:
        """Generate formatted privilege log"""
        
        # Filter communications for matter
        matter_comms = [
            comm for comm in communications.values()
            if comm.matter_id == matter_id
        ]
        
        # Apply date range filter
        if date_range:
            matter_comms = [
                comm for comm in matter_comms
                if date_range.start_date <= comm.date.date() <= date_range.end_date
            ]
            
        # Format log entries
        log_entries = []
        privileged_count = 0
        
        for comm in sorted(matter_comms, key=lambda x: x.date):
            if comm.is_privileged:
                privileged_count += 1
                
                entry = {
                    "entry_number": len(log_entries) + 1,
                    "date": comm.date.strftime("%Y-%m-%d"),
                    "type": comm.communication_type.value,
                    "direction": comm.direction,
                    "parties": self._format_parties(comm.participants),
                    "description": self._create_privilege_description(comm),
                    "privilege_basis": self._get_privilege_basis(comm.privilege_type),
                    "redacted": True,
                    "bates_range": f"PRIV_{comm.id[:8]}"
                }
                log_entries.append(entry)
                
        return PrivilegeLog(
            matter_id=matter_id,
            entries=log_entries,
            generated_date=datetime.utcnow(),
            date_range=(
                date_range.start_date if date_range else matter_comms[0].date.date() if matter_comms else date.today(),
                date_range.end_date if date_range else matter_comms[-1].date.date() if matter_comms else date.today()
            ),
            total_entries=len(log_entries),
            privileged_count=privileged_count
        )
        
    def _format_parties(self, participants: List[Dict[str, Any]]) -> str:
        """Format participant list for privilege log"""
        parties = []
        
        for participant in participants:
            name = participant.get("name", "Unknown")
            role = participant.get("role", "")
            
            if role:
                parties.append(f"{name} ({role})")
            else:
                parties.append(name)
                
        return "; ".join(parties)
        
    def _create_privilege_description(self, comm: Communication) -> str:
        """Create generic description preserving privilege"""
        if comm.privilege_type == PrivilegeType.ATTORNEY_CLIENT:
            return "Attorney-client communication regarding legal advice"
        elif comm.privilege_type == PrivilegeType.WORK_PRODUCT:
            return "Attorney work product prepared in anticipation of litigation"
        elif comm.privilege_type == PrivilegeType.CONFIDENTIAL:
            return "Confidential communication"
        else:
            return "Communication"
            
    def _get_privilege_basis(self, privilege_type: PrivilegeType) -> str:
        """Get legal basis for privilege claim"""
        bases = {
            PrivilegeType.ATTORNEY_CLIENT: "Attorney-Client Privilege",
            PrivilegeType.WORK_PRODUCT: "Work Product Doctrine",
            PrivilegeType.CONFIDENTIAL: "Confidentiality Agreement",
            PrivilegeType.NOT_PRIVILEGED: "N/A"
        }
        return bases.get(privilege_type, "Unknown")


class FollowUpManager:
    """Manage follow-ups with smart scheduling"""
    
    async def create_smart_follow_ups(self, communication: Communication) -> List[FollowUp]:
        """Create follow-ups based on communication analysis"""
        follow_ups = []
        
        # Extract commitments from communication
        commitments = await self._extract_commitments(communication.content or "")
        
        for commitment in commitments:
            follow_up = FollowUp(
                id=f"followup_{datetime.utcnow().timestamp()}_{len(follow_ups)}",
                matter_id=communication.matter_id,
                communication_id=communication.id,
                due_date=self._calculate_follow_up_date(commitment),
                description=commitment["description"],
                priority=self._assess_priority(commitment),
                assigned_to=None,  # Would be determined by workflow rules
                auto_escalate=True
            )
            follow_ups.append(follow_up)
            
        return follow_ups
        
    async def _extract_commitments(self, content: str) -> List[Dict[str, Any]]:
        """Extract commitments from communication content"""
        commitments = []
        
        # Pattern matching for commitments
        commitment_patterns = [
            r"(?:I will|We will|Will)\s+([^.]+)",
            r"(?:by|before|no later than)\s+([^.]+)",
            r"(?:deadline|due date)(?:\s+is)?\s+([^.]+)",
            r"(?:follow up|get back to you)(?:\s+(?:by|on))?\s+([^.]+)"
        ]
        
        for pattern in commitment_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                commitments.append({
                    "description": match.strip(),
                    "pattern": pattern,
                    "urgency": self._assess_urgency(match)
                })
                
        return commitments
        
    def _calculate_follow_up_date(self, commitment: Dict[str, Any]) -> datetime:
        """Calculate appropriate follow-up date"""
        base_date = datetime.utcnow()
        
        # Parse time references
        text = commitment["description"].lower()
        
        if "tomorrow" in text:
            return base_date + timedelta(days=1)
        elif "next week" in text:
            return base_date + timedelta(weeks=1)
        elif "end of week" in text:
            days_until_friday = (4 - base_date.weekday()) % 7
            return base_date + timedelta(days=days_until_friday or 7)
        elif re.search(r"(\d+)\s*days?", text):
            match = re.search(r"(\d+)\s*days?", text)
            days = int(match.group(1))
            return base_date + timedelta(days=days)
        else:
            # Default to 3 business days
            return base_date + timedelta(days=3)
            
    def _assess_priority(self, commitment: Dict[str, Any]) -> str:
        """Assess priority of commitment"""
        urgency = commitment.get("urgency", "medium")
        
        if urgency == "high":
            return "high"
        elif urgency == "low":
            return "low"
        else:
            return "medium"
            
    def _assess_urgency(self, text: str) -> str:
        """Assess urgency from text"""
        text_lower = text.lower()
        
        high_urgency_keywords = ["urgent", "asap", "immediately", "critical", "emergency"]
        low_urgency_keywords = ["when possible", "eventually", "no rush"]
        
        for keyword in high_urgency_keywords:
            if keyword in text_lower:
                return "high"
                
        for keyword in low_urgency_keywords:
            if keyword in text_lower:
                return "low"
                
        return "medium"