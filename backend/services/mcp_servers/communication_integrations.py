# services/mcp_servers/communication_integrations.py - Communication service integrations

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
import logging
import asyncio
import aiohttp
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class Email:
    id: str
    subject: str
    sender: str
    recipients: List[str]
    date: datetime
    content: str
    attachments: List[Dict[str, Any]]
    headers: Dict[str, str]
    direction: str  # inbound/outbound
    thread_id: Optional[str] = None

@dataclass
class PhoneCall:
    id: str
    caller: str
    recipient: str
    date: datetime
    duration: int  # seconds
    direction: str  # inbound/outbound
    recording_url: Optional[str] = None
    transcript: Optional[str] = None

@dataclass
class SMS:
    id: str
    sender: str
    recipient: str
    date: datetime
    content: str
    direction: str  # inbound/outbound

@dataclass
class CalendarEvent:
    id: str
    title: str
    date: datetime
    duration: int  # minutes
    participants: List[str]
    location: Optional[str] = None
    description: Optional[str] = None
    meeting_url: Optional[str] = None

@dataclass
class EmailResult:
    success: bool
    message_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None

class CommunicationIntegration(ABC):
    """Base class for communication integrations"""
    
    @abstractmethod
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to the service"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the service"""
        pass
        
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is active"""
        pass


class EmailIntegration(CommunicationIntegration):
    """Email service integration (IMAP/SMTP)"""
    
    def __init__(self):
        self.imap_client = None
        self.smtp_client = None
        self.config = {}
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to email service"""
        self.config = config
        
        try:
            # Connect IMAP for reading
            if config.get("imap_server"):
                self.imap_client = imaplib.IMAP4_SSL(
                    config["imap_server"],
                    config.get("imap_port", 993)
                )
                self.imap_client.login(config["username"], config["password"])
                
            # Connect SMTP for sending
            if config.get("smtp_server"):
                self.smtp_client = smtplib.SMTP_SSL(
                    config["smtp_server"],
                    config.get("smtp_port", 465)
                )
                self.smtp_client.login(config["username"], config["password"])
                
            return True
            
        except Exception as e:
            logger.error(f"Email connection failed: {str(e)}")
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from email service"""
        try:
            if self.imap_client:
                self.imap_client.logout()
            if self.smtp_client:
                self.smtp_client.quit()
            return True
        except Exception as e:
            logger.error(f"Email disconnect error: {str(e)}")
            return False
            
    async def test_connection(self) -> bool:
        """Test email connection"""
        try:
            if self.imap_client:
                self.imap_client.noop()
            return True
        except:
            return False
            
    async def sync_emails(self, mailbox_config: Dict[str, Any]) -> List[Email]:
        """Sync emails from mailbox"""
        emails = []
        
        try:
            # Select mailbox
            mailbox = mailbox_config.get("mailbox", "INBOX")
            self.imap_client.select(mailbox)
            
            # Search emails
            search_criteria = self._build_search_criteria(mailbox_config)
            status, message_ids = self.imap_client.search(None, search_criteria)
            
            if status != "OK":
                return emails
                
            # Fetch emails
            for msg_id in message_ids[0].split()[-100:]:  # Last 100 emails
                try:
                    status, msg_data = self.imap_client.fetch(msg_id, "(RFC822)")
                    if status == "OK":
                        email_msg = email.message_from_bytes(msg_data[0][1])
                        parsed_email = self._parse_email(email_msg, msg_id.decode())
                        emails.append(parsed_email)
                except Exception as e:
                    logger.error(f"Error parsing email {msg_id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Email sync error: {str(e)}")
            
        return emails
        
    async def send_tracked_email(self, email_data: Dict[str, Any]) -> EmailResult:
        """Send an email with tracking"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = email_data.get("from", self.config["username"])
            msg["To"] = ", ".join(email_data["to"])
            msg["Subject"] = email_data["subject"]
            
            # Add tracking headers
            message_id = f"<{datetime.utcnow().timestamp()}@legal-ai>"
            msg["Message-ID"] = message_id
            msg["X-Legal-Matter-ID"] = email_data.get("matter_id", "")
            
            # Add body
            msg.attach(MIMEText(email_data["body"], "plain"))
            
            # Add attachments
            for attachment in email_data.get("attachments", []):
                self._add_attachment(msg, attachment)
                
            # Send email
            self.smtp_client.send_message(msg)
            
            return EmailResult(
                success=True,
                message_id=message_id,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Email send error: {str(e)}")
            return EmailResult(
                success=False,
                error=str(e)
            )
            
    def _build_search_criteria(self, config: Dict[str, Any]) -> str:
        """Build IMAP search criteria"""
        criteria = []
        
        # Date range
        if config.get("since_date"):
            date_str = config["since_date"].strftime("%d-%b-%Y")
            criteria.append(f'SINCE "{date_str}"')
            
        # From filter
        if config.get("from_addresses"):
            for addr in config["from_addresses"]:
                criteria.append(f'FROM "{addr}"')
                
        # Subject filter
        if config.get("subject_contains"):
            criteria.append(f'SUBJECT "{config["subject_contains"]}"')
            
        return " ".join(criteria) if criteria else "ALL"
        
    def _parse_email(self, email_msg, msg_id: str) -> Email:
        """Parse email message"""
        # Extract headers
        subject = email_msg.get("Subject", "")
        sender = email_msg.get("From", "")
        recipients = email_msg.get("To", "").split(",")
        date_str = email_msg.get("Date", "")
        
        # Parse date
        try:
            date = email.utils.parsedate_to_datetime(date_str)
        except:
            date = datetime.utcnow()
            
        # Extract content
        content = ""
        attachments = []
        
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    content = part.get_payload(decode=True).decode(errors="ignore")
                elif part.get_content_disposition() == "attachment":
                    attachments.append({
                        "filename": part.get_filename(),
                        "content_type": part.get_content_type(),
                        "size": len(part.get_payload())
                    })
        else:
            content = email_msg.get_payload(decode=True).decode(errors="ignore")
            
        return Email(
            id=msg_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            date=date,
            content=content,
            attachments=attachments,
            headers=dict(email_msg.items()),
            direction="inbound"
        )
        
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email"""
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment["content"])
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment["filename"]}"'
        )
        msg.attach(part)


class PhoneSystemIntegration(CommunicationIntegration):
    """Phone system integration (VoIP/PBX)"""
    
    def __init__(self):
        self.api_client = None
        self.config = {}
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to phone system API"""
        self.config = config
        
        # Initialize API client (example for common VoIP systems)
        self.api_client = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {config.get('api_key')}"}
        )
        
        return await self.test_connection()
        
    async def disconnect(self) -> bool:
        """Disconnect from phone system"""
        if self.api_client:
            await self.api_client.close()
        return True
        
    async def test_connection(self) -> bool:
        """Test phone system connection"""
        try:
            async with self.api_client.get(f"{self.config['api_url']}/health") as response:
                return response.status == 200
        except:
            return False
            
    async def get_call_logs(self, filters: Dict[str, Any]) -> List[PhoneCall]:
        """Get phone call logs"""
        calls = []
        
        try:
            # Build query parameters
            params = {
                "start_date": filters.get("start_date", datetime.utcnow() - timedelta(days=30)),
                "end_date": filters.get("end_date", datetime.utcnow()),
                "limit": filters.get("limit", 100)
            }
            
            # Get call logs from API
            async with self.api_client.get(
                f"{self.config['api_url']}/calls",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for call_data in data.get("calls", []):
                        calls.append(PhoneCall(
                            id=call_data["id"],
                            caller=call_data["from"],
                            recipient=call_data["to"],
                            date=datetime.fromisoformat(call_data["timestamp"]),
                            duration=call_data["duration"],
                            direction=call_data["direction"],
                            recording_url=call_data.get("recording_url"),
                            transcript=call_data.get("transcript")
                        ))
                        
        except Exception as e:
            logger.error(f"Phone log retrieval error: {str(e)}")
            
        return calls
        
    async def get_call_transcript(self, call_id: str) -> Optional[str]:
        """Get transcript for a specific call"""
        try:
            async with self.api_client.get(
                f"{self.config['api_url']}/calls/{call_id}/transcript"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("transcript")
        except Exception as e:
            logger.error(f"Transcript retrieval error: {str(e)}")
            
        return None


class SMSIntegration(CommunicationIntegration):
    """SMS integration (Twilio/similar)"""
    
    def __init__(self):
        self.api_client = None
        self.config = {}
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to SMS service"""
        self.config = config
        
        # Initialize API client
        self.api_client = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(config["account_sid"], config["auth_token"])
        )
        
        return await self.test_connection()
        
    async def disconnect(self) -> bool:
        """Disconnect from SMS service"""
        if self.api_client:
            await self.api_client.close()
        return True
        
    async def test_connection(self) -> bool:
        """Test SMS service connection"""
        try:
            async with self.api_client.get(
                f"{self.config['api_url']}/Accounts/{self.config['account_sid']}.json"
            ) as response:
                return response.status == 200
        except:
            return False
            
    async def get_messages(self, filters: Dict[str, Any]) -> List[SMS]:
        """Get SMS messages"""
        messages = []
        
        try:
            params = {
                "DateSent>": filters.get("start_date", datetime.utcnow() - timedelta(days=30)),
                "PageSize": filters.get("limit", 100)
            }
            
            async with self.api_client.get(
                f"{self.config['api_url']}/Accounts/{self.config['account_sid']}/Messages.json",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for msg_data in data.get("messages", []):
                        messages.append(SMS(
                            id=msg_data["sid"],
                            sender=msg_data["from"],
                            recipient=msg_data["to"],
                            date=datetime.fromisoformat(msg_data["date_sent"]),
                            content=msg_data["body"],
                            direction=msg_data["direction"]
                        ))
                        
        except Exception as e:
            logger.error(f"SMS retrieval error: {str(e)}")
            
        return messages
        
    async def send_sms(self, to: str, body: str, from_number: Optional[str] = None) -> bool:
        """Send an SMS message"""
        try:
            data = {
                "To": to,
                "From": from_number or self.config["from_number"],
                "Body": body
            }
            
            async with self.api_client.post(
                f"{self.config['api_url']}/Accounts/{self.config['account_sid']}/Messages.json",
                data=data
            ) as response:
                return response.status == 201
                
        except Exception as e:
            logger.error(f"SMS send error: {str(e)}")
            return False


class CalendarIntegration(CommunicationIntegration):
    """Calendar integration (Google/Outlook/CalDAV)"""
    
    def __init__(self):
        self.api_client = None
        self.config = {}
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to calendar service"""
        self.config = config
        
        # Initialize API client based on service type
        if config["service_type"] == "google":
            # Google Calendar API setup
            self.api_client = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {config['access_token']}"}
            )
        elif config["service_type"] == "outlook":
            # Outlook Calendar API setup
            self.api_client = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {config['access_token']}"}
            )
            
        return await self.test_connection()
        
    async def disconnect(self) -> bool:
        """Disconnect from calendar service"""
        if self.api_client:
            await self.api_client.close()
        return True
        
    async def test_connection(self) -> bool:
        """Test calendar connection"""
        try:
            if self.config["service_type"] == "google":
                url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
            elif self.config["service_type"] == "outlook":
                url = "https://graph.microsoft.com/v1.0/me/calendars"
            else:
                return False
                
            async with self.api_client.get(url) as response:
                return response.status == 200
        except:
            return False
            
    async def get_events(self, filters: Dict[str, Any]) -> List[CalendarEvent]:
        """Get calendar events"""
        events = []
        
        try:
            if self.config["service_type"] == "google":
                events = await self._get_google_events(filters)
            elif self.config["service_type"] == "outlook":
                events = await self._get_outlook_events(filters)
                
        except Exception as e:
            logger.error(f"Calendar event retrieval error: {str(e)}")
            
        return events
        
    async def _get_google_events(self, filters: Dict[str, Any]) -> List[CalendarEvent]:
        """Get events from Google Calendar"""
        events = []
        
        params = {
            "timeMin": filters.get("start_date", datetime.utcnow()).isoformat(),
            "timeMax": filters.get("end_date", datetime.utcnow() + timedelta(days=30)).isoformat(),
            "maxResults": filters.get("limit", 100),
            "singleEvents": True,
            "orderBy": "startTime"
        }
        
        async with self.api_client.get(
            f"https://www.googleapis.com/calendar/v3/calendars/{self.config['calendar_id']}/events",
            params=params
        ) as response:
            if response.status == 200:
                data = await response.json()
                
                for event_data in data.get("items", []):
                    events.append(CalendarEvent(
                        id=event_data["id"],
                        title=event_data.get("summary", ""),
                        date=datetime.fromisoformat(event_data["start"].get("dateTime", event_data["start"].get("date"))),
                        duration=self._calculate_duration(event_data),
                        participants=[att.get("email") for att in event_data.get("attendees", [])],
                        location=event_data.get("location"),
                        description=event_data.get("description"),
                        meeting_url=self._extract_meeting_url(event_data)
                    ))
                    
        return events
        
    async def _get_outlook_events(self, filters: Dict[str, Any]) -> List[CalendarEvent]:
        """Get events from Outlook Calendar"""
        events = []
        
        # Implement Outlook-specific logic
        # Similar to Google Calendar but using Microsoft Graph API
        
        return events
        
    def _calculate_duration(self, event_data: Dict[str, Any]) -> int:
        """Calculate event duration in minutes"""
        try:
            start = datetime.fromisoformat(event_data["start"].get("dateTime"))
            end = datetime.fromisoformat(event_data["end"].get("dateTime"))
            return int((end - start).total_seconds() / 60)
        except:
            return 60  # Default 1 hour
            
    def _extract_meeting_url(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Extract meeting URL from event data"""
        # Check common fields for meeting URLs
        description = event_data.get("description", "")
        location = event_data.get("location", "")
        
        # Look for common meeting URL patterns
        import re
        url_pattern = r'https?://(?:zoom\.us|meet\.google\.com|teams\.microsoft\.com)/[^\s]+'
        
        match = re.search(url_pattern, description + " " + location)
        return match.group(0) if match else None