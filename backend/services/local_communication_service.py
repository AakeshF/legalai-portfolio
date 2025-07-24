# services/local_communication_service.py - Local communication service (no external APIs)
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class LocalEmail:
    id: str
    subject: str
    sender: str
    recipients: List[str]
    date: datetime
    content: str
    attachments: List[Dict[str, Any]]
    direction: str  # inbound/outbound
    thread_id: Optional[str] = None

@dataclass
class LocalCalendarEvent:
    id: str
    title: str
    date: datetime
    duration: int  # minutes
    participants: List[str]
    location: Optional[str] = None
    description: Optional[str] = None

class LocalCommunicationService:
    """
    Local communication service that stores all communications locally.
    No external API calls - perfect for offline/private deployments.
    """
    
    def __init__(self):
        self.storage_dir = Path("./local_communications")
        self.emails_dir = self.storage_dir / "emails"
        self.calendar_dir = self.storage_dir / "calendar"
        self.sms_dir = self.storage_dir / "sms"
        
        # Create directories
        for dir_path in [self.emails_dir, self.calendar_dir, self.sms_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("LocalCommunicationService initialized - all data stored locally")
    
    async def save_email(self, email: LocalEmail) -> bool:
        """Save email locally"""
        try:
            filename = f"{email.date.isoformat()}_{email.id}.json"
            filepath = self.emails_dir / filename
            
            email_data = asdict(email)
            email_data['date'] = email.date.isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(email_data, f, indent=2)
            
            logger.info(f"Email saved locally: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save email: {e}")
            return False
    
    async def get_emails(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve stored emails"""
        emails = []
        for filepath in sorted(self.emails_dir.glob("*.json"), reverse=True)[:limit]:
            with open(filepath, 'r') as f:
                emails.append(json.load(f))
        return emails
    
    async def save_calendar_event(self, event: LocalCalendarEvent) -> bool:
        """Save calendar event locally"""
        try:
            filename = f"{event.date.isoformat()}_{event.id}.json"
            filepath = self.calendar_dir / filename
            
            event_data = asdict(event)
            event_data['date'] = event.date.isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(event_data, f, indent=2)
            
            logger.info(f"Calendar event saved locally: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save calendar event: {e}")
            return False
    
    async def get_calendar_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Retrieve calendar events within date range"""
        events = []
        for filepath in self.calendar_dir.glob("*.json"):
            with open(filepath, 'r') as f:
                event = json.load(f)
                event_date = datetime.fromisoformat(event['date'])
                if start_date <= event_date <= end_date:
                    events.append(event)
        
        return sorted(events, key=lambda x: x['date'])
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of local communication storage"""
        return {
            "email": {
                "enabled": True,
                "type": "local_storage",
                "count": len(list(self.emails_dir.glob("*.json")))
            },
            "calendar": {
                "enabled": True,
                "type": "local_storage",
                "count": len(list(self.calendar_dir.glob("*.json")))
            },
            "sms": {
                "enabled": False,
                "type": "disabled",
                "reason": "SMS requires external provider"
            },
            "phone": {
                "enabled": False,
                "type": "disabled",
                "reason": "Phone requires external provider"
            }
        }

# Create global instance
local_communication_service = LocalCommunicationService()