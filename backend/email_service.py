# email_service.py - Production email service for legal professionals
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from typing import List, Dict, Any, Optional
from pydantic import EmailStr, BaseModel
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Email configuration
email_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_USERNAME"),
    MAIL_PASSWORD=os.getenv("SMTP_PASSWORD"),
    MAIL_FROM=os.getenv("EMAIL_FROM_ADDRESS", "noreply@[YOUR-DOMAIN]"),
    MAIL_FROM_NAME=os.getenv("EMAIL_FROM_NAME", "Legal AI Assistant"),
    MAIL_PORT=int(os.getenv("SMTP_PORT", "587")),
    MAIL_SERVER=os.getenv("SMTP_HOST", "smtp.gmail.com"),
    MAIL_STARTTLS=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "email_templates",
)

# Initialize FastMail
fast_mail = FastMail(email_config)

# Initialize Jinja2 for email templates
template_env = Environment(
    loader=FileSystemLoader("email_templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    """Email service for legal professionals"""

    async def send_welcome_email(
        self, user_email: str, user_name: str, organization: str
    ):
        """Send welcome email to new users"""
        template_data = {
            "user_name": user_name,
            "organization": organization,
            "login_url": f"{os.getenv('FRONTEND_URL', 'https://app.example.com')}/login",
            "support_email": "[SUPPORT-EMAIL]",
            "year": datetime.now().year,
        }

        message = MessageSchema(
            subject=f"Welcome to Legal AI Assistant - {organization}",
            recipients=[user_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="welcome.html")
        logger.info(f"Welcome email sent to {user_email}")

    async def send_password_reset(
        self, user_email: str, reset_token: str, user_name: str
    ):
        """Send password reset email"""
        reset_url = f"{os.getenv('FRONTEND_URL')}/reset-password?token={reset_token}"

        template_data = {
            "user_name": user_name,
            "reset_url": reset_url,
            "expires_in": "30 minutes",
            "support_email": "[SUPPORT-EMAIL]",
        }

        message = MessageSchema(
            subject="Reset Your Legal AI Assistant Password",
            recipients=[user_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="password_reset.html")
        logger.info(f"Password reset email sent to {user_email}")

    async def send_document_processed(
        self,
        user_email: str,
        user_name: str,
        document_name: str,
        document_type: str,
        key_findings: List[str],
        risk_level: str,
    ):
        """Send notification when document processing is complete"""
        template_data = {
            "user_name": user_name,
            "document_name": document_name,
            "document_type": document_type,
            "key_findings": key_findings,
            "risk_level": risk_level,
            "risk_color": self._get_risk_color(risk_level),
            "view_url": f"{os.getenv('FRONTEND_URL')}/documents",
            "year": datetime.now().year,
        }

        message = MessageSchema(
            subject=f"Document Analysis Complete: {document_name}",
            recipients=[user_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="document_processed.html")
        logger.info(f"Document processed email sent to {user_email}")

    async def send_organization_invite(
        self,
        invitee_email: str,
        inviter_name: str,
        organization_name: str,
        invite_token: str,
        role: str = "attorney",
    ):
        """Send organization invitation email"""
        accept_url = f"{os.getenv('FRONTEND_URL')}/accept-invite?token={invite_token}"

        template_data = {
            "inviter_name": inviter_name,
            "organization_name": organization_name,
            "role": role.title(),
            "accept_url": accept_url,
            "expires_in": "7 days",
            "features": [
                "AI-powered legal document analysis",
                "Secure document storage",
                "Collaborative workspace",
                "Advanced search capabilities",
            ],
        }

        message = MessageSchema(
            subject=f"You're invited to join {organization_name} on Legal AI Assistant",
            recipients=[invitee_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="organization_invite.html")
        logger.info(f"Organization invite sent to {invitee_email}")

    async def send_security_alert(
        self, user_email: str, user_name: str, alert_type: str, details: Dict[str, Any]
    ):
        """Send security alert emails"""
        template_data = {
            "user_name": user_name,
            "alert_type": alert_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ip_address": details.get("ip_address", "Unknown"),
            "location": details.get("location", "Unknown"),
            "device": details.get("device", "Unknown"),
            "action_required": details.get("action_required", False),
            "security_url": f"{os.getenv('FRONTEND_URL')}/security",
        }

        # Determine subject based on alert type
        subjects = {
            "new_login": "New Login to Your Legal AI Account",
            "suspicious_activity": "Suspicious Activity Detected",
            "password_changed": "Your Password Was Changed",
            "2fa_enabled": "Two-Factor Authentication Enabled",
        }

        message = MessageSchema(
            subject=subjects.get(alert_type, "Security Alert"),
            recipients=[user_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="security_alert.html")
        logger.info(f"Security alert sent to {user_email}: {alert_type}")

    async def send_subscription_notification(
        self,
        billing_email: str,
        organization_name: str,
        notification_type: str,
        details: Dict[str, Any],
    ):
        """Send subscription-related notifications"""
        template_data = {
            "organization_name": organization_name,
            "notification_type": notification_type,
            "current_plan": details.get("current_plan", "Basic"),
            "new_plan": details.get("new_plan"),
            "renewal_date": details.get("renewal_date"),
            "amount": details.get("amount"),
            "billing_url": f"{os.getenv('FRONTEND_URL')}/billing",
            "year": datetime.now().year,
        }

        subjects = {
            "upgrade": f"Plan Upgraded for {organization_name}",
            "downgrade": f"Plan Changed for {organization_name}",
            "renewal": f"Subscription Renewal Notice for {organization_name}",
            "payment_failed": f"Payment Failed - Action Required",
        }

        message = MessageSchema(
            subject=subjects.get(notification_type, "Subscription Update"),
            recipients=[billing_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="subscription.html")
        logger.info(f"Subscription notification sent: {notification_type}")

    async def send_weekly_summary(
        self,
        user_email: str,
        user_name: str,
        organization_name: str,
        summary_data: Dict[str, Any],
    ):
        """Send weekly activity summary"""
        template_data = {
            "user_name": user_name,
            "organization_name": organization_name,
            "week_ending": datetime.now().strftime("%B %d, %Y"),
            "documents_processed": summary_data.get("documents_processed", 0),
            "ai_queries": summary_data.get("ai_queries", 0),
            "time_saved_hours": summary_data.get("time_saved_hours", 0),
            "top_document_types": summary_data.get("top_document_types", []),
            "risk_alerts": summary_data.get("risk_alerts", 0),
            "dashboard_url": f"{os.getenv('FRONTEND_URL')}/dashboard",
        }

        message = MessageSchema(
            subject=f"Your Weekly Legal AI Summary - {organization_name}",
            recipients=[user_email],
            template_body=template_data,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message, template_name="weekly_summary.html")
        logger.info(f"Weekly summary sent to {user_email}")

    def _get_risk_color(self, risk_level: str) -> str:
        """Get color for risk level"""
        colors = {"low": "#28a745", "medium": "#ffc107", "high": "#dc3545"}
        return colors.get(risk_level.lower(), "#6c757d")


# Email template models for API
class WelcomeEmailRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    organization: str


class PasswordResetEmailRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    reset_token: str


class DocumentProcessedEmailRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    document_name: str
    document_type: str
    key_findings: List[str]
    risk_level: str


# Initialize email service
email_service = EmailService()
