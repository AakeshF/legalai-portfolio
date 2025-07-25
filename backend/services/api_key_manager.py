# services/api_key_manager.py - Secure API key management with encryption
import os
import json
from typing import Dict, Optional, List, Any
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class APIKeyStore(Base):
    """Database model for encrypted API key storage"""

    __tablename__ = "api_key_store"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    provider = Column(
        String(50), nullable=False
    )  # claude, openai, gemini, [ai-provider]
    encrypted_key = Column(Text, nullable=False)
    key_hint = Column(String(20))  # Last 4 characters for identification
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    # Validation metadata
    last_validated = Column(DateTime)
    validation_status = Column(String(20))  # valid, invalid, unchecked

    # Usage tracking
    last_used = Column(DateTime)
    usage_count = Column(Integer, default=0)


class APIKeyManager:
    """Secure API key management with per-organization encryption"""

    def __init__(self, db: Session, master_key: Optional[str] = None):
        self.db = db
        self.master_key = master_key or os.getenv(
            "API_KEY_MASTER_SECRET", self._generate_master_key()
        )
        self._cipher_suite = self._initialize_cipher()

        # Provider validation patterns
        self.key_patterns = {
            "claude": r"^sk-ant-",
            "openai": r"^sk-",
            "[ai-provider]": r"^sk-",
            "gemini": r"^[A-Za-z0-9_-]{39}$",  # Google API keys are 39 chars
        }

        logger.info("API Key Manager initialized with encryption")

    def _generate_master_key(self) -> str:
        """Generate a new master key for encryption"""
        return Fernet.generate_key().decode()

    def _initialize_cipher(self) -> Fernet:
        """Initialize encryption cipher with master key"""
        # Use PBKDF2 to derive a key from the master key
        # Generate or retrieve salt from environment
        salt_str = os.getenv(
            "API_KEY_SALT", base64.urlsafe_b64encode(os.urandom(16)).decode()
        )
        salt = base64.urlsafe_b64decode(salt_str.encode())

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)

    def store_api_key(
        self,
        organization_id: int,
        provider: str,
        api_key: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Store an encrypted API key for an organization"""

        # Validate provider
        if provider not in self.key_patterns:
            raise ValueError(f"Unsupported provider: {provider}")

        # Basic validation
        if not api_key or len(api_key) < 10:
            raise ValueError("Invalid API key format")

        # Encrypt the key
        encrypted_key = self._cipher_suite.encrypt(api_key.encode()).decode()

        # Create hint (last 4 characters)
        key_hint = f"...{api_key[-4:]}" if len(api_key) > 4 else "****"

        # Check if key already exists for this org/provider
        existing = (
            self.db.query(APIKeyStore)
            .filter_by(
                organization_id=organization_id, provider=provider, is_active=True
            )
            .first()
        )

        if existing:
            # Update existing key
            existing.encrypted_key = encrypted_key
            existing.key_hint = key_hint
            existing.updated_at = datetime.utcnow()
            existing.validation_status = "unchecked"
            key_record = existing
            action = "updated"
        else:
            # Create new key record
            key_record = APIKeyStore(
                organization_id=organization_id,
                provider=provider,
                encrypted_key=encrypted_key,
                key_hint=key_hint,
                created_by=user_id,
                validation_status="unchecked",
            )
            self.db.add(key_record)
            action = "created"

        self.db.commit()

        logger.info(f"API key {action} for org {organization_id}, provider {provider}")

        return {
            "id": key_record.id,
            "provider": provider,
            "key_hint": key_hint,
            "action": action,
            "created_at": key_record.created_at.isoformat(),
        }

    def get_api_key(self, organization_id: int, provider: str) -> Optional[str]:
        """Retrieve and decrypt an API key"""

        key_record = (
            self.db.query(APIKeyStore)
            .filter_by(
                organization_id=organization_id, provider=provider, is_active=True
            )
            .first()
        )

        if not key_record:
            # Fall back to environment variables
            env_map = {
                "claude": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "[ai-provider]": "DEEPSEEK_API_KEY",
                "gemini": "GOOGLE_API_KEY",
            }
            return os.getenv(env_map.get(provider))

        try:
            # Decrypt the key
            decrypted_key = self._cipher_suite.decrypt(
                key_record.encrypted_key.encode()
            ).decode()

            # Update usage stats
            key_record.last_used = datetime.utcnow()
            key_record.usage_count += 1
            self.db.commit()

            return decrypted_key

        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            return None

    def validate_api_key(self, organization_id: int, provider: str) -> Dict[str, Any]:
        """Validate an API key by making a test request"""

        api_key = self.get_api_key(organization_id, provider)
        if not api_key:
            return {"valid": False, "error": "No API key found", "provider": provider}

        # Provider-specific validation
        validation_result = self._validate_key_format(provider, api_key)

        if validation_result["valid"]:
            # Update validation status
            key_record = (
                self.db.query(APIKeyStore)
                .filter_by(
                    organization_id=organization_id, provider=provider, is_active=True
                )
                .first()
            )

            if key_record:
                key_record.last_validated = datetime.utcnow()
                key_record.validation_status = "valid"
                self.db.commit()

        return validation_result

    def _validate_key_format(self, provider: str, api_key: str) -> Dict[str, Any]:
        """Validate API key format based on provider patterns"""
        import re

        pattern = self.key_patterns.get(provider)
        if not pattern:
            return {"valid": False, "error": "Unknown provider"}

        if not re.match(pattern, api_key):
            return {
                "valid": False,
                "error": f"Invalid {provider} API key format",
                "provider": provider,
            }

        return {
            "valid": True,
            "provider": provider,
            "validated_at": datetime.utcnow().isoformat(),
        }

    def list_api_keys(self, organization_id: int) -> List[Dict[str, Any]]:
        """List all API keys for an organization (without decrypting)"""

        keys = (
            self.db.query(APIKeyStore)
            .filter_by(organization_id=organization_id, is_active=True)
            .all()
        )

        return [
            {
                "id": key.id,
                "provider": key.provider,
                "key_hint": key.key_hint,
                "validation_status": key.validation_status,
                "last_validated": (
                    key.last_validated.isoformat() if key.last_validated else None
                ),
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "usage_count": key.usage_count,
                "created_at": key.created_at.isoformat(),
            }
            for key in keys
        ]

    def revoke_api_key(self, organization_id: int, provider: str) -> bool:
        """Revoke an API key (soft delete)"""

        key_record = (
            self.db.query(APIKeyStore)
            .filter_by(
                organization_id=organization_id, provider=provider, is_active=True
            )
            .first()
        )

        if key_record:
            key_record.is_active = False
            key_record.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(
                f"API key revoked for org {organization_id}, provider {provider}"
            )
            return True

        return False

    def rotate_api_key(
        self,
        organization_id: int,
        provider: str,
        new_api_key: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Rotate an API key by revoking the old one and storing a new one"""

        # Revoke existing key
        self.revoke_api_key(organization_id, provider)

        # Store new key
        result = self.store_api_key(organization_id, provider, new_api_key, user_id)
        result["action"] = "rotated"

        return result

    def get_provider_status(self, organization_id: int) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers for an organization"""

        providers = ["claude", "openai", "[ai-provider]", "gemini"]
        status = {}

        for provider in providers:
            key_record = (
                self.db.query(APIKeyStore)
                .filter_by(
                    organization_id=organization_id, provider=provider, is_active=True
                )
                .first()
            )

            if key_record:
                status[provider] = {
                    "configured": True,
                    "key_hint": key_record.key_hint,
                    "validation_status": key_record.validation_status,
                    "last_used": (
                        key_record.last_used.isoformat()
                        if key_record.last_used
                        else None
                    ),
                }
            else:
                # Check environment variables
                env_key = self.get_api_key(organization_id, provider)
                status[provider] = {
                    "configured": bool(env_key),
                    "source": "environment" if env_key else "none",
                    "validation_status": "unchecked" if env_key else "missing",
                }

        return status
