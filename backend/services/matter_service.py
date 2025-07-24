# services/matter_service.py - Matter management service with MCP integration

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import hashlib
import json
from uuid import uuid4

from models import Matter, MatterType, MatterStatus, MCPQueryCache, Deadline, Communication, Organization, User
from services.mcp_manager import MCPManager
from database import get_db
import logging

logger = logging.getLogger(__name__)

class ConflictException(Exception):
    """Raised when a conflict of interest is detected"""
    def __init__(self, conflicts: List[Dict[str, Any]]):
        self.conflicts = conflicts
        super().__init__(f"Conflict of interest detected: {len(conflicts)} conflicts found")

class MatterService:
    def __init__(self, db: Session, mcp_manager: MCPManager):
        self.db = db
        self.mcp_manager = mcp_manager
        
    async def create_matter_with_conflict_check(self, matter_data: dict, organization_id: str) -> Matter:
        """Create a new matter with integrated conflict checking via MCP"""
        try:
            # Extract client and opposing party information
            client_name = matter_data.get("client_name", "")
            opposing_parties = matter_data.get("opposing_parties", [])
            
            # Check for conflicts via MCP
            conflict_result = await self._check_conflicts_via_mcp(
                client_name=client_name,
                opposing_parties=opposing_parties,
                organization_id=organization_id
            )
            
            if conflict_result.get("has_conflicts", False):
                raise ConflictException(conflict_result.get("conflicts", []))
            
            # Create matter if no conflicts
            matter = self._create_matter(matter_data, organization_id)
            
            # Sync initial data from MCP sources
            await self._sync_matter_with_mcp_sources(matter)
            
            return matter
            
        except Exception as e:
            logger.error(f"Error creating matter: {str(e)}")
            raise
            
    def _create_matter(self, matter_data: dict, organization_id: str) -> Matter:
        """Create a matter in the database"""
        matter = Matter(
            id=str(uuid4()),
            organization_id=organization_id,
            client_id=matter_data["client_id"],
            matter_name=matter_data["matter_name"],
            matter_type=MatterType(matter_data["matter_type"]),
            status=MatterStatus(matter_data.get("status", "active")),
            opposing_parties=matter_data.get("opposing_parties", []),
            jurisdiction=matter_data.get("jurisdiction"),
            case_number=matter_data.get("case_number"),
            judge_assigned=matter_data.get("judge_assigned"),
            description=matter_data.get("description"),
            billing_type=matter_data.get("billing_type", "hourly"),
            estimated_value=matter_data.get("estimated_value"),
            mcp_metadata={}
        )
        
        self.db.add(matter)
        self.db.commit()
        self.db.refresh(matter)
        
        return matter
        
    async def _check_conflicts_via_mcp(self, client_name: str, opposing_parties: List[Dict], 
                                      organization_id: str) -> Dict[str, Any]:
        """Check for conflicts of interest using MCP legal data server"""
        # Generate cache key
        cache_key = self._generate_cache_key("conflict_check", {
            "client_name": client_name,
            "opposing_parties": opposing_parties,
            "organization_id": organization_id
        })
        
        # Check cache first
        cached_result = self._get_cached_query(cache_key, organization_id)
        if cached_result:
            return cached_result
            
        # Query MCP for conflict check
        try:
            result = await self.mcp_manager.query_server(
                "legal_data",
                "conflict_check",
                {
                    "client_name": client_name,
                    "opposing_parties": opposing_parties,
                    "organization_id": organization_id
                }
            )
            
            # Cache the result
            self._cache_query_result("legal_data", cache_key, result, organization_id)
            
            return result
            
        except Exception as e:
            logger.error(f"MCP conflict check failed: {str(e)}")
            # Fallback to basic local conflict check
            return await self._local_conflict_check(client_name, opposing_parties, organization_id)
            
    async def _local_conflict_check(self, client_name: str, opposing_parties: List[Dict], 
                                   organization_id: str) -> Dict[str, Any]:
        """Fallback local conflict checking when MCP is unavailable"""
        conflicts = []
        
        # Check if any opposing party is an existing client
        for party in opposing_parties:
            party_name = party.get("name", "")
            # Simple check - in production, this would be more sophisticated
            existing_matters = self.db.query(Matter).filter(
                and_(
                    Matter.organization_id == organization_id,
                    Matter.status != MatterStatus.CLOSED,
                    or_(
                        Matter.client.has(User.full_name.ilike(f"%{party_name}%")),
                        Matter.opposing_parties.contains([{"name": party_name}])
                    )
                )
            ).all()
            
            if existing_matters:
                for matter in existing_matters:
                    conflicts.append({
                        "type": "client_opposing_party",
                        "party_name": party_name,
                        "conflicting_matter_id": matter.id,
                        "conflicting_matter_name": matter.matter_name
                    })
                    
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts
        }
        
    async def _sync_matter_with_mcp_sources(self, matter: Matter):
        """Sync matter data with various MCP sources"""
        sync_tasks = []
        
        # Sync with court data if case number exists
        if matter.case_number and matter.jurisdiction:
            sync_tasks.append(self._sync_court_data(matter))
            
        # Sync with calendar for deadlines
        sync_tasks.append(self._sync_calendar_deadlines(matter))
        
        # Sync with email for communications
        sync_tasks.append(self._sync_email_communications(matter))
        
        # Execute all sync tasks
        for task in sync_tasks:
            try:
                await task
            except Exception as e:
                logger.warning(f"MCP sync task failed: {str(e)}")
                
    async def _sync_court_data(self, matter: Matter):
        """Sync matter with court MCP server"""
        try:
            court_data = await self.mcp_manager.query_server(
                "court_api",
                "get_case_info",
                {
                    "case_number": matter.case_number,
                    "jurisdiction": matter.jurisdiction
                }
            )
            
            if court_data:
                # Update matter with court data
                if court_data.get("judge"):
                    matter.judge_assigned = court_data["judge"]
                    
                # Create deadlines from court calendar
                for deadline in court_data.get("upcoming_dates", []):
                    self._create_deadline_from_court_data(matter, deadline)
                    
                # Update MCP metadata
                matter.mcp_metadata["court_sync"] = {
                    "last_sync": datetime.utcnow().isoformat(),
                    "court_api_id": court_data.get("case_id")
                }
                
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Court data sync failed: {str(e)}")
            
    async def _sync_calendar_deadlines(self, matter: Matter):
        """Sync deadlines from calendar MCP server"""
        try:
            calendar_events = await self.mcp_manager.query_server(
                "calendar",
                "get_events",
                {
                    "matter_id": matter.id,
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=365)).isoformat()
                }
            )
            
            for event in calendar_events.get("events", []):
                if "deadline" in event.get("tags", []):
                    self._create_deadline_from_calendar(matter, event)
                    
        except Exception as e:
            logger.error(f"Calendar sync failed: {str(e)}")
            
    async def _sync_email_communications(self, matter: Matter):
        """Sync email communications from email MCP server"""
        try:
            # Search emails related to matter
            search_terms = [matter.matter_name, matter.case_number] if matter.case_number else [matter.matter_name]
            
            emails = await self.mcp_manager.query_server(
                "email",
                "search",
                {
                    "query": " OR ".join(search_terms),
                    "limit": 100,
                    "since": matter.date_opened.isoformat()
                }
            )
            
            for email in emails.get("messages", []):
                self._create_communication_from_email(matter, email)
                
        except Exception as e:
            logger.error(f"Email sync failed: {str(e)}")
            
    def _create_deadline_from_court_data(self, matter: Matter, court_deadline: Dict):
        """Create a deadline from court data"""
        deadline = Deadline(
            matter_id=matter.id,
            organization_id=matter.organization_id,
            title=court_deadline.get("title", "Court Deadline"),
            description=court_deadline.get("description"),
            due_date=datetime.fromisoformat(court_deadline["date"]),
            is_court_deadline=True,
            mcp_sync_source="court_api",
            mcp_sync_id=court_deadline.get("id")
        )
        self.db.add(deadline)
        
    def _create_deadline_from_calendar(self, matter: Matter, calendar_event: Dict):
        """Create a deadline from calendar event"""
        deadline = Deadline(
            matter_id=matter.id,
            organization_id=matter.organization_id,
            title=calendar_event.get("title", "Deadline"),
            description=calendar_event.get("description"),
            due_date=datetime.fromisoformat(calendar_event["date"]),
            is_court_deadline=False,
            mcp_sync_source="calendar",
            mcp_sync_id=calendar_event.get("id")
        )
        self.db.add(deadline)
        
    def _create_communication_from_email(self, matter: Matter, email: Dict):
        """Create a communication record from email data"""
        # Check if already exists
        existing = self.db.query(Communication).filter(
            and_(
                Communication.mcp_source == "email",
                Communication.mcp_external_id == email.get("id")
            )
        ).first()
        
        if not existing:
            communication = Communication(
                matter_id=matter.id,
                organization_id=matter.organization_id,
                communication_type="email",
                direction="inbound" if email.get("from") != matter.organization.billing_email else "outbound",
                subject=email.get("subject"),
                content=email.get("body"),
                participants=email.get("participants", []),
                timestamp=datetime.fromisoformat(email["date"]),
                mcp_source="email",
                mcp_external_id=email.get("id"),
                mcp_metadata={"headers": email.get("headers", {})}
            )
            self.db.add(communication)
            
    async def get_matter_mcp_context(self, matter_id: str) -> Dict[str, Any]:
        """Get all MCP-enriched data for a matter"""
        matter = self.db.query(Matter).filter(Matter.id == matter_id).first()
        if not matter:
            raise ValueError("Matter not found")
            
        context = {
            "matter": {
                "id": matter.id,
                "name": matter.matter_name,
                "type": matter.matter_type.value,
                "status": matter.status.value,
                "client_id": matter.client_id,
                "opposing_parties": matter.opposing_parties,
                "jurisdiction": matter.jurisdiction,
                "case_number": matter.case_number,
                "judge": matter.judge_assigned
            },
            "mcp_data": {}
        }
        
        # Get data from each MCP source
        mcp_sources = ["court_api", "calendar", "email", "document_management"]
        
        for source in mcp_sources:
            try:
                source_data = await self.mcp_manager.query_server(
                    source,
                    "get_matter_data",
                    {"matter_id": matter_id}
                )
                context["mcp_data"][source] = source_data
            except Exception as e:
                logger.warning(f"Failed to get data from {source}: {str(e)}")
                context["mcp_data"][source] = {"error": str(e)}
                
        return context
        
    async def sync_court_data_for_matter(self, matter_id: str) -> Dict[str, Any]:
        """Manually trigger court data sync for a matter"""
        matter = self.db.query(Matter).filter(Matter.id == matter_id).first()
        if not matter:
            raise ValueError("Matter not found")
            
        await self._sync_court_data(matter)
        
        return {
            "success": True,
            "matter_id": matter_id,
            "sync_timestamp": datetime.utcnow().isoformat()
        }
        
    def _generate_cache_key(self, query_type: str, params: Dict) -> str:
        """Generate a unique cache key for a query"""
        # Create a deterministic string from params
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(f"{query_type}:{param_str}".encode()).hexdigest()
        
    def _get_cached_query(self, cache_key: str, organization_id: str) -> Optional[Dict]:
        """Get cached query result if not expired"""
        cached = self.db.query(MCPQueryCache).filter(
            and_(
                MCPQueryCache.query_hash == cache_key,
                MCPQueryCache.organization_id == organization_id,
                MCPQueryCache.expires_at > datetime.utcnow()
            )
        ).first()
        
        if cached:
            # Increment hit count
            cached.hit_count += 1
            self.db.commit()
            return cached.response_data
            
        return None
        
    def _cache_query_result(self, server_type: str, cache_key: str, 
                           result: Dict, organization_id: str, ttl_minutes: int = 60):
        """Cache a query result"""
        cache_entry = MCPQueryCache(
            server_type=server_type,
            query_hash=cache_key,
            response_data=result,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
            organization_id=organization_id
        )
        self.db.add(cache_entry)
        self.db.commit()