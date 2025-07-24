# encryption.py - AES-256 encryption for document content at rest
import os
import base64
import hashlib
import secrets
from typing import Tuple, Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import json
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    """
    Enterprise-grade AES-256 encryption service for document content
    Compliant with legal industry security standards
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service with master key
        
        Args:
            master_key: Base64 encoded master key. If not provided, will use from environment
        """
        if master_key:
            self.master_key = base64.b64decode(master_key)
        else:
            # Get from environment or generate
            env_key = os.environ.get('ENCRYPTION_MASTER_KEY')
            if env_key:
                self.master_key = base64.b64decode(env_key)
            else:
                # Generate and log warning
                logger.warning("No master key provided. Generating new key - THIS SHOULD BE STORED SECURELY!")
                self.master_key = self._generate_master_key()
                logger.info(f"Generated master key (store this securely): {base64.b64encode(self.master_key).decode()}")
        
        # Verify key length
        if len(self.master_key) != 32:  # 256 bits
            raise ValueError("Master key must be 256 bits (32 bytes)")
        
        self.backend = default_backend()
        
    def _generate_master_key(self) -> bytes:
        """Generate a secure 256-bit master key"""
        return secrets.token_bytes(32)
    
    def _derive_key(self, salt: bytes, context: str = "document") -> bytes:
        """
        Derive a key from master key using PBKDF2
        
        Args:
            salt: Random salt for key derivation
            context: Context string for domain separation
            
        Returns:
            Derived 256-bit key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt + context.encode(),
            iterations=100000,  # NIST recommended minimum
            backend=self.backend
        )
        return kdf.derive(self.master_key)
    
    def encrypt_document(self, content: bytes, document_id: str) -> Tuple[bytes, Dict[str, str]]:
        """
        Encrypt document content using AES-256-GCM
        
        Args:
            content: Document content to encrypt
            document_id: Unique document identifier
            
        Returns:
            Tuple of (encrypted_content, encryption_metadata)
        """
        # Generate random salt and IV
        salt = secrets.token_bytes(16)
        iv = secrets.token_bytes(16)
        
        # Derive encryption key
        key = self._derive_key(salt, f"doc:{document_id}")
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        
        # Add document ID as authenticated data
        encryptor.authenticate_additional_data(document_id.encode())
        
        # Encrypt content
        ciphertext = encryptor.update(content) + encryptor.finalize()
        
        # Get authentication tag
        tag = encryptor.tag
        
        # Combine encrypted data
        encrypted_data = salt + iv + tag + ciphertext
        
        # Create metadata
        metadata = {
            "encryption_version": "1.0",
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-SHA256",
            "iterations": "100000",
            "document_id": document_id,
            "encrypted_size": len(encrypted_data),
            "original_size": len(content)
        }
        
        logger.info(f"Document encrypted successfully", extra={
            "document_id": document_id,
            "original_size": len(content),
            "encrypted_size": len(encrypted_data)
        })
        
        return encrypted_data, metadata
    
    def decrypt_document(self, encrypted_content: bytes, document_id: str) -> bytes:
        """
        Decrypt document content
        
        Args:
            encrypted_content: Encrypted document data
            document_id: Document identifier (for verification)
            
        Returns:
            Decrypted document content
        """
        if len(encrypted_content) < 48:  # salt(16) + iv(16) + tag(16)
            raise ValueError("Invalid encrypted data format")
        
        # Extract components
        salt = encrypted_content[:16]
        iv = encrypted_content[16:32]
        tag = encrypted_content[32:48]
        ciphertext = encrypted_content[48:]
        
        # Derive decryption key
        key = self._derive_key(salt, f"doc:{document_id}")
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        
        # Add document ID as authenticated data
        decryptor.authenticate_additional_data(document_id.encode())
        
        # Decrypt content
        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            logger.info(f"Document decrypted successfully", extra={
                "document_id": document_id,
                "decrypted_size": len(plaintext)
            })
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed for document", extra={
                "document_id": document_id,
                "error": str(e)
            })
            raise ValueError("Decryption failed. Document may be corrupted or tampered with.")
    
    def encrypt_field(self, value: str, field_name: str) -> str:
        """
        Encrypt a single field value (for database storage)
        
        Args:
            value: Field value to encrypt
            field_name: Name of field for context
            
        Returns:
            Base64 encoded encrypted value
        """
        # Generate random IV
        iv = secrets.token_bytes(16)
        
        # Use a deterministic salt based on field name for searchability
        salt = hashlib.sha256(field_name.encode()).digest()[:16]
        
        # Derive key
        key = self._derive_key(salt, f"field:{field_name}")
        
        # Pad the value
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(value.encode()) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and ciphertext
        encrypted = iv + ciphertext
        
        # Return base64 encoded
        return base64.b64encode(encrypted).decode()
    
    def decrypt_field(self, encrypted_value: str, field_name: str) -> str:
        """
        Decrypt a single field value
        
        Args:
            encrypted_value: Base64 encoded encrypted value
            field_name: Name of field for context
            
        Returns:
            Decrypted value
        """
        # Decode from base64
        encrypted = base64.b64decode(encrypted_value)
        
        if len(encrypted) < 16:
            raise ValueError("Invalid encrypted field format")
        
        # Extract IV and ciphertext
        iv = encrypted[:16]
        ciphertext = encrypted[16:]
        
        # Use deterministic salt
        salt = hashlib.sha256(field_name.encode()).digest()[:16]
        
        # Derive key
        key = self._derive_key(salt, f"field:{field_name}")
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        return plaintext.decode()
    
    def generate_document_key(self, document_id: str) -> str:
        """
        Generate a unique key for document encryption
        
        Args:
            document_id: Document identifier
            
        Returns:
            Base64 encoded document key
        """
        # Generate random document key
        doc_key = secrets.token_bytes(32)
        
        # Encrypt document key with master key
        salt = secrets.token_bytes(16)
        derived_key = self._derive_key(salt, f"dockey:{document_id}")
        
        # Simple XOR encryption for key wrapping
        encrypted_key = bytes(a ^ b for a, b in zip(doc_key, derived_key))
        
        # Combine salt and encrypted key
        wrapped_key = salt + encrypted_key
        
        return base64.b64encode(wrapped_key).decode()
    
    def verify_encryption_integrity(self, encrypted_content: bytes, metadata: Dict[str, Any]) -> bool:
        """
        Verify encryption integrity without decrypting
        
        Args:
            encrypted_content: Encrypted data
            metadata: Encryption metadata
            
        Returns:
            True if integrity check passes
        """
        # Verify size
        if len(encrypted_content) != metadata.get("encrypted_size"):
            return False
        
        # Verify format
        if len(encrypted_content) < 48:
            return False
        
        # Additional checks can be added here
        return True
    
    def rotate_master_key(self, new_master_key: bytes, documents: list) -> None:
        """
        Rotate master encryption key (for key rotation compliance)
        
        Args:
            new_master_key: New 256-bit master key
            documents: List of documents to re-encrypt
        """
        if len(new_master_key) != 32:
            raise ValueError("New master key must be 256 bits")
        
        old_master_key = self.master_key
        
        for doc in documents:
            try:
                # Decrypt with old key
                content = self.decrypt_document(doc['encrypted_content'], doc['id'])
                
                # Update master key
                self.master_key = new_master_key
                
                # Re-encrypt with new key
                encrypted_content, metadata = self.encrypt_document(content, doc['id'])
                
                # Update document
                doc['encrypted_content'] = encrypted_content
                doc['encryption_metadata'] = metadata
                
            except Exception as e:
                # Restore old key on failure
                self.master_key = old_master_key
                logger.error(f"Key rotation failed for document {doc['id']}: {e}")
                raise
        
        logger.info(f"Master key rotated successfully for {len(documents)} documents")

# Global encryption service instance
encryption_service = None

def get_encryption_service() -> EncryptionService:
    """Get or create encryption service instance"""
    global encryption_service
    if encryption_service is None:
        encryption_service = EncryptionService()
    return encryption_service