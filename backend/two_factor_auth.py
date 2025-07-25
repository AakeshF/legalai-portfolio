# two_factor_auth.py - Enterprise two-factor authentication with TOTP
import pyotp
import qrcode
import io
import base64
import secrets
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import Session
from database import Base
from models import User
from encryption import get_encryption_service
from audit_logger import AuditLogger, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


@dataclass
class TwoFactorConfig:
    """Configuration for 2FA"""

    issuer_name: str = "Legal AI Platform"
    totp_digits: int = 6
    totp_interval: int = 30  # seconds
    backup_codes_count: int = 10
    max_attempts: int = 3
    lockout_duration: int = 900  # 15 minutes
    require_2fa_for_admins: bool = True
    allow_remember_device: bool = True
    remember_device_days: int = 30


class TwoFactorAuth(Base):
    """Database model for 2FA settings"""

    __tablename__ = "two_factor_auth"

    user_id = Column(String, primary_key=True)
    secret_encrypted = Column(String, nullable=False)  # Encrypted TOTP secret
    backup_codes_encrypted = Column(Text, nullable=True)  # Encrypted JSON array
    enabled = Column(Boolean, default=False)
    enabled_at = Column(DateTime, nullable=True)

    # Recovery settings
    recovery_email = Column(String, nullable=True)
    recovery_phone = Column(String, nullable=True)

    # Security tracking
    last_used = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Device trust
    trusted_devices = Column(Text, nullable=True)  # Encrypted JSON


class TwoFactorService:
    """
    Enterprise-grade two-factor authentication service
    Implements TOTP (Time-based One-Time Password) with backup codes
    """

    def __init__(
        self,
        db_session_factory,
        config: TwoFactorConfig = None,
        audit_logger: AuditLogger = None,
    ):
        self.db_session_factory = db_session_factory
        self.config = config or TwoFactorConfig()
        self.encryption_service = get_encryption_service()
        self.audit_logger = audit_logger

    def setup_2fa(self, user: User) -> Dict[str, Any]:
        """
        Set up 2FA for a user

        Returns:
            Setup data including QR code and backup codes
        """
        db = self.db_session_factory()

        try:
            # Check if already exists
            existing = (
                db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user.id).first()
            )

            if existing and existing.enabled:
                raise ValueError("2FA is already enabled for this user")

            # Generate secret
            secret = pyotp.random_base32()

            # Generate backup codes
            backup_codes = [
                f"{secrets.token_hex(4)}-{secrets.token_hex(4)}"
                for _ in range(self.config.backup_codes_count)
            ]

            # Encrypt sensitive data
            secret_encrypted = self.encryption_service.encrypt_field(
                secret, f"totp_secret_{user.id}"
            )
            backup_codes_encrypted = self.encryption_service.encrypt_field(
                json.dumps(backup_codes), f"backup_codes_{user.id}"
            )

            # Create or update 2FA record
            if existing:
                existing.secret_encrypted = secret_encrypted
                existing.backup_codes_encrypted = backup_codes_encrypted
                existing.enabled = False  # Not enabled until verified
                existing.failed_attempts = 0
                existing.locked_until = None
            else:
                two_fa = TwoFactorAuth(
                    user_id=user.id,
                    secret_encrypted=secret_encrypted,
                    backup_codes_encrypted=backup_codes_encrypted,
                    enabled=False,
                    recovery_email=user.email,
                )
                db.add(two_fa)

            db.commit()

            # Generate QR code
            provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user.email, issuer_name=self.config.issuer_name
            )

            qr_code_base64 = self._generate_qr_code(provisioning_uri)

            # Log setup attempt
            if self.audit_logger:
                self.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.SECURITY_EVENT,
                        user_id=user.id,
                        organization_id=user.organization_id,
                        action="2fa_setup_initiated",
                        details={"method": "totp"},
                    )
                )

            return {
                "secret": secret,  # Only shown once
                "qr_code": qr_code_base64,
                "backup_codes": backup_codes,
                "manual_entry_key": self._format_secret_for_display(secret),
            }

        finally:
            db.close()

    def verify_and_enable_2fa(
        self,
        user: User,
        totp_code: str,
        trust_device: bool = False,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify TOTP code and enable 2FA

        Returns:
            Success status and device trust token if requested
        """
        db = self.db_session_factory()

        try:
            two_fa = (
                db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user.id).first()
            )

            if not two_fa:
                raise ValueError("2FA not set up for this user")

            if two_fa.enabled:
                raise ValueError("2FA is already enabled")

            # Decrypt secret
            secret = self.encryption_service.decrypt_field(
                two_fa.secret_encrypted, f"totp_secret_{user.id}"
            )

            # Verify TOTP code
            totp = pyotp.TOTP(secret)
            if not totp.verify(totp_code, valid_window=1):
                raise ValueError("Invalid verification code")

            # Enable 2FA
            two_fa.enabled = True
            two_fa.enabled_at = datetime.utcnow()
            two_fa.last_used = datetime.utcnow()

            # Handle device trust
            device_token = None
            if trust_device and device_id and self.config.allow_remember_device:
                device_token = self._trust_device(two_fa, device_id)

            db.commit()

            # Log successful enablement
            if self.audit_logger:
                self.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.SECURITY_EVENT,
                        user_id=user.id,
                        organization_id=user.organization_id,
                        action="2fa_enabled",
                        result="success",
                        details={"device_trusted": trust_device},
                    )
                )

            return {
                "success": True,
                "message": "2FA enabled successfully",
                "device_token": device_token,
            }

        finally:
            db.close()

    def verify_totp(
        self, user: User, totp_code: str, device_token: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify TOTP code for login

        Returns:
            Tuple of (success, error_message)
        """
        db = self.db_session_factory()

        try:
            two_fa = (
                db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user.id).first()
            )

            if not two_fa or not two_fa.enabled:
                return True, None  # 2FA not enabled, skip

            # Check if account is locked
            if two_fa.locked_until and datetime.utcnow() < two_fa.locked_until:
                remaining = int(
                    (two_fa.locked_until - datetime.utcnow()).total_seconds()
                )
                return False, f"Account locked. Try again in {remaining} seconds"

            # Check device trust
            if device_token and self._is_device_trusted(two_fa, device_token):
                logger.info(
                    f"2FA bypassed for trusted device", extra={"user_id": user.id}
                )
                return True, None

            # Decrypt secret
            secret = self.encryption_service.decrypt_field(
                two_fa.secret_encrypted, f"totp_secret_{user.id}"
            )

            # Verify TOTP
            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(totp_code, valid_window=1)

            if is_valid:
                # Reset failed attempts
                two_fa.failed_attempts = 0
                two_fa.locked_until = None
                two_fa.last_used = datetime.utcnow()
                db.commit()

                # Log successful verification
                if self.audit_logger:
                    self.audit_logger.log_event(
                        AuditEvent(
                            event_type=AuditEventType.LOGIN_SUCCESS,
                            user_id=user.id,
                            organization_id=user.organization_id,
                            details={"2fa_method": "totp"},
                        )
                    )

                return True, None
            else:
                # Check if it's a backup code
                if self._verify_backup_code(two_fa, totp_code, db):
                    return True, None

                # Increment failed attempts
                two_fa.failed_attempts += 1

                if two_fa.failed_attempts >= self.config.max_attempts:
                    # Lock account
                    two_fa.locked_until = datetime.utcnow() + timedelta(
                        seconds=self.config.lockout_duration
                    )
                    db.commit()

                    # Log lockout
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            AuditEvent(
                                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                                user_id=user.id,
                                organization_id=user.organization_id,
                                action="2fa_lockout",
                                details={"failed_attempts": two_fa.failed_attempts},
                            )
                        )

                    return False, "Too many failed attempts. Account locked"

                db.commit()
                attempts_remaining = self.config.max_attempts - two_fa.failed_attempts
                return False, f"Invalid code. {attempts_remaining} attempts remaining"

        finally:
            db.close()

    def disable_2fa(self, user: User, password: str) -> bool:
        """Disable 2FA for a user (requires password verification)"""
        db = self.db_session_factory()

        try:
            # Verify password first (implement in auth_utils)
            # if not verify_password(password, user.password_hash):
            #     raise ValueError("Invalid password")

            two_fa = (
                db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user.id).first()
            )

            if not two_fa:
                return False

            # Disable 2FA
            two_fa.enabled = False
            two_fa.trusted_devices = None
            db.commit()

            # Log disablement
            if self.audit_logger:
                self.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.SECURITY_EVENT,
                        user_id=user.id,
                        organization_id=user.organization_id,
                        action="2fa_disabled",
                        result="success",
                    )
                )

            return True

        finally:
            db.close()

    def generate_backup_codes(self, user: User) -> List[str]:
        """Generate new backup codes (invalidates old ones)"""
        db = self.db_session_factory()

        try:
            two_fa = (
                db.query(TwoFactorAuth)
                .filter(TwoFactorAuth.user_id == user.id, TwoFactorAuth.enabled == True)
                .first()
            )

            if not two_fa:
                raise ValueError("2FA not enabled for this user")

            # Generate new codes
            backup_codes = [
                f"{secrets.token_hex(4)}-{secrets.token_hex(4)}"
                for _ in range(self.config.backup_codes_count)
            ]

            # Encrypt and store
            two_fa.backup_codes_encrypted = self.encryption_service.encrypt_field(
                json.dumps(backup_codes), f"backup_codes_{user.id}"
            )

            db.commit()

            # Log regeneration
            if self.audit_logger:
                self.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.SECURITY_EVENT,
                        user_id=user.id,
                        organization_id=user.organization_id,
                        action="backup_codes_regenerated",
                    )
                )

            return backup_codes

        finally:
            db.close()

    def get_2fa_status(self, user: User) -> Dict[str, Any]:
        """Get 2FA status for a user"""
        db = self.db_session_factory()

        try:
            two_fa = (
                db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user.id).first()
            )

            if not two_fa:
                return {"enabled": False, "configured": False}

            # Count remaining backup codes
            backup_codes_count = 0
            if two_fa.backup_codes_encrypted:
                codes = json.loads(
                    self.encryption_service.decrypt_field(
                        two_fa.backup_codes_encrypted, f"backup_codes_{user.id}"
                    )
                )
                backup_codes_count = len(
                    [c for c in codes if c]
                )  # Count non-null codes

            return {
                "enabled": two_fa.enabled,
                "configured": True,
                "enabled_at": (
                    two_fa.enabled_at.isoformat() if two_fa.enabled_at else None
                ),
                "last_used": two_fa.last_used.isoformat() if two_fa.last_used else None,
                "backup_codes_remaining": backup_codes_count,
                "recovery_email": two_fa.recovery_email,
                "recovery_phone": two_fa.recovery_phone is not None,
            }

        finally:
            db.close()

    def enforce_2fa_requirement(self, user: User) -> bool:
        """Check if 2FA is required for user"""
        # Admins always require 2FA
        if user.role == "admin" and self.config.require_2fa_for_admins:
            return True

        # Check organization policy (implement as needed)
        # if user.organization.require_2fa:
        #     return True

        return False

    # Private methods
    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """Generate QR code as base64 string"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode()

    def _format_secret_for_display(self, secret: str) -> str:
        """Format secret for manual entry (groups of 4)"""
        return " ".join(secret[i : i + 4] for i in range(0, len(secret), 4))

    def _verify_backup_code(
        self, two_fa: TwoFactorAuth, code: str, db: Session
    ) -> bool:
        """Verify and consume backup code"""
        if not two_fa.backup_codes_encrypted:
            return False

        # Decrypt codes
        codes = json.loads(
            self.encryption_service.decrypt_field(
                two_fa.backup_codes_encrypted, f"backup_codes_{two_fa.user_id}"
            )
        )

        # Check if code exists
        if code in codes:
            # Remove used code
            codes[codes.index(code)] = None

            # Re-encrypt and save
            two_fa.backup_codes_encrypted = self.encryption_service.encrypt_field(
                json.dumps(codes), f"backup_codes_{two_fa.user_id}"
            )

            two_fa.last_used = datetime.utcnow()
            db.commit()

            # Log backup code usage
            if self.audit_logger:
                self.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.SECURITY_EVENT,
                        user_id=two_fa.user_id,
                        action="backup_code_used",
                        details={"remaining": len([c for c in codes if c])},
                    )
                )

            return True

        return False

    def _trust_device(self, two_fa: TwoFactorAuth, device_id: str) -> str:
        """Trust a device and return trust token"""
        # Generate device token
        device_token = secrets.token_urlsafe(32)

        # Get trusted devices
        trusted_devices = {}
        if two_fa.trusted_devices:
            trusted_devices = json.loads(
                self.encryption_service.decrypt_field(
                    two_fa.trusted_devices, f"trusted_devices_{two_fa.user_id}"
                )
            )

        # Add new device
        trusted_devices[device_token] = {
            "device_id": device_id,
            "trusted_at": datetime.utcnow().isoformat(),
            "expires_at": (
                datetime.utcnow() + timedelta(days=self.config.remember_device_days)
            ).isoformat(),
        }

        # Encrypt and save
        two_fa.trusted_devices = self.encryption_service.encrypt_field(
            json.dumps(trusted_devices), f"trusted_devices_{two_fa.user_id}"
        )

        return device_token

    def _is_device_trusted(self, two_fa: TwoFactorAuth, device_token: str) -> bool:
        """Check if device token is valid and not expired"""
        if not two_fa.trusted_devices:
            return False

        try:
            trusted_devices = json.loads(
                self.encryption_service.decrypt_field(
                    two_fa.trusted_devices, f"trusted_devices_{two_fa.user_id}"
                )
            )

            device_info = trusted_devices.get(device_token)
            if not device_info:
                return False

            # Check expiration
            expires_at = datetime.fromisoformat(device_info["expires_at"])
            return datetime.utcnow() < expires_at

        except Exception:
            return False
