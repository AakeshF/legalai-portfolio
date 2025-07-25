# auth_utils.py - Authentication utilities for user management
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import os
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging

logger = logging.getLogger(__name__)

# Password hashing configuration (12 rounds for security)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", f"{SECRET_KEY}_refresh")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days
RESET_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "[email@example.com]")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_user_tokens(
    user_id: str, email: str, organization_id: str, role: str
) -> Dict[str, str]:
    """Create both access and refresh tokens for a user"""
    # Access token (2 hours)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": user_id,
        "email": email,
        "org": organization_id,  # Changed from org_id to match frontend expectations
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc).timestamp(),  # Added for frontend
    }
    access_token = create_access_token(
        access_token_data, expires_delta=access_token_expires
    )

    # Refresh token (7 days)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_data = {"sub": user_id, "type": "refresh"}
    refresh_token = create_refresh_token(
        refresh_token_data, expires_delta=refresh_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
    }


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT refresh token"""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def create_password_reset_token(user_id: str, email: str) -> str:
    """Create a password reset token"""
    expires_delta = timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "email": email,
        "type": "password_reset",
        "exp": datetime.now(timezone.utc) + expires_delta,
    }

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_password_reset_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a password reset token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload
    except JWTError:
        return None


def generate_secure_session_id() -> str:
    """Generate a cryptographically secure session ID"""
    return secrets.token_urlsafe(32)


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    return True, "Password is valid"


def generate_temp_password() -> str:
    """Generate a secure temporary password"""
    # Use secrets for cryptographically secure random generation
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for _ in range(12))
    # Ensure it meets our requirements
    return password + "1A!"


async def send_password_reset_email(email: str, reset_token: str, user_name: str):
    """Send password reset email"""
    try:
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Password Reset Request - Legal AI"
        msg["From"] = EMAIL_FROM
        msg["To"] = email

        # Create the HTML content
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2c3e50;">Password Reset Request</h2>
              <p>Hi {user_name},</p>
              <p>We received a request to reset your password for Legal AI. If you didn't make this request, please ignore this email.</p>
              <p>To reset your password, click the link below:</p>
              <div style="margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
              </div>
              <p>Or copy and paste this link into your browser:</p>
              <p style="word-break: break-all; color: #3498db;">{reset_link}</p>
              <p><strong>This link will expire in 30 minutes.</strong></p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              <p style="font-size: 12px; color: #666;">If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
            </div>
          </body>
        </html>
        """

        # Create plain text version
        text = f"""
Hi {user_name},

We received a request to reset your password for Legal AI. If you didn't make this request, please ignore this email.

To reset your password, visit this link:
{reset_link}

This link will expire in 30 minutes.

If you didn't request this password reset, please ignore this email. Your password will remain unchanged.
        """

        # Attach parts
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Send email
        if SMTP_USER and SMTP_PASSWORD:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Password reset email sent to {email}")
        else:
            # In development, just log the link
            logger.warning(f"Email not configured. Reset link: {reset_link}")

    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        raise


async def send_welcome_email(
    email: str,
    user_name: str,
    organization_name: str,
    temp_password: Optional[str] = None,
):
    """Send welcome email to new user"""
    try:
        login_link = f"{FRONTEND_URL}/login"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Welcome to Legal AI - {organization_name}"
        msg["From"] = EMAIL_FROM
        msg["To"] = email

        password_section = ""
        if temp_password:
            password_section = f"""
            <p><strong>Your temporary password is:</strong> <code style="background-color: #f5f5f5; padding: 5px 10px; border-radius: 3px;">{temp_password}</code></p>
            <p style="color: #e74c3c;">Please change your password after your first login.</p>
            """

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2c3e50;">Welcome to Legal AI!</h2>
              <p>Hi {user_name},</p>
              <p>Your account has been created for <strong>{organization_name}</strong>.</p>
              {password_section}
              <p>You can log in at:</p>
              <div style="margin: 30px 0;">
                <a href="{login_link}" style="background-color: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Log In to Legal AI</a>
              </div>
              <p>Legal AI helps you:</p>
              <ul>
                <li>Analyze legal documents with AI</li>
                <li>Extract key information from contracts</li>
                <li>Identify potential risks and issues</li>
                <li>Save time on document review</li>
              </ul>
              <p>If you have any questions, please don't hesitate to reach out.</p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              <p style="font-size: 12px; color: #666;">This email was sent to {email} because an account was created for you on Legal AI.</p>
            </div>
          </body>
        </html>
        """

        text = f"""
Welcome to Legal AI!

Hi {user_name},

Your account has been created for {organization_name}.

{"Your temporary password is: " + temp_password if temp_password else ""}
{"Please change your password after your first login." if temp_password else ""}

You can log in at: {login_link}

Legal AI helps you:
- Analyze legal documents with AI
- Extract key information from contracts
- Identify potential risks and issues
- Save time on document review

If you have any questions, please don't hesitate to reach out.
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        if SMTP_USER and SMTP_PASSWORD:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Welcome email sent to {email}")
        else:
            logger.warning(f"Email not configured. Welcome email for {email} not sent")

    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        # Don't raise - welcome email is not critical
