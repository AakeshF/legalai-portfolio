# services/local_email_service.py - Local email service (no external SMTP)
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LocalEmailService:
    """
    Local email service that stores emails as files instead of sending them.
    Perfect for offline/private deployments where external SMTP is not desired.
    """

    def __init__(self):
        self.email_dir = Path("./local_emails")
        self.email_dir.mkdir(exist_ok=True)
        self.enabled = False  # Disabled by default for privacy
        logger.info(
            f"LocalEmailService initialized - emails will be saved to {self.email_dir}"
        )

    async def send_email(
        self, to: List[str], subject: str, body: str, html_body: Optional[str] = None
    ):
        """Save email locally instead of sending"""
        if not self.enabled:
            logger.debug(f"Email service disabled - would have sent: {subject} to {to}")
            return True

        timestamp = datetime.utcnow().isoformat()
        email_data = {
            "timestamp": timestamp,
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "status": "saved_locally",
        }

        # Save email as JSON file
        filename = (
            f"{timestamp.replace(':', '-')}_{subject[:30].replace(' ', '_')}.json"
        )
        filepath = self.email_dir / filename

        with open(filepath, "w") as f:
            json.dump(email_data, f, indent=2)

        logger.info(f"Email saved locally: {filepath}")
        return True

    async def send_welcome_email(
        self, user_email: str, user_name: str, organization: str
    ):
        """Save welcome email locally"""
        subject = f"Welcome to PrivateLegal AI, {user_name}!"
        body = f"""
Welcome to PrivateLegal AI, {user_name}!

You have been successfully registered with {organization}.

Your PrivateLegal AI system is running completely offline and all your data stays private within your organization.

If you need assistance, please contact your system administrator.

Best regards,
PrivateLegal AI Team
"""
        return await self.send_email([user_email], subject, body)

    async def send_document_processed(
        self, user_email: str, document_name: str, summary: str
    ):
        """Save document processed notification locally"""
        subject = f"Document Processed: {document_name}"
        body = f"""
Your document "{document_name}" has been processed successfully.

Summary:
{summary}

You can view the full analysis in your PrivateLegal AI dashboard.

This email was generated locally and no data was sent outside your network.
"""
        return await self.send_email([user_email], subject, body)

    async def send_alert(self, admin_emails: List[str], alert_type: str, message: str):
        """Save alert locally"""
        subject = f"PrivateLegal AI Alert: {alert_type}"
        body = f"""
Alert Type: {alert_type}
Timestamp: {datetime.utcnow().isoformat()}

Message:
{message}

This is a local alert. Please check your PrivateLegal AI system.
"""
        return await self.send_email(admin_emails, subject, body)

    def get_saved_emails(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve saved emails for admin viewing"""
        emails = []
        for filepath in sorted(self.email_dir.glob("*.json"), reverse=True)[:limit]:
            with open(filepath, "r") as f:
                emails.append(json.load(f))
        return emails


# Create global instance
local_email_service = LocalEmailService()
