# secure_upload.py - Enterprise-grade secure file upload validation
import os
import hashlib
import magic
import yara
import clamd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import tempfile
import shutil
from pathlib import Path
import zipfile
import logging
from datetime import datetime
import mimetypes

from fastapi import UploadFile, HTTPException, status
from audit_logger import AuditLogger, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


@dataclass
class FileValidationConfig:
    """Configuration for file validation"""

    # Size limits
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    min_file_size: int = 1  # 1 byte

    # Allowed file types
    allowed_extensions: List[str] = None
    allowed_mime_types: List[str] = None

    # Security scanning
    enable_virus_scan: bool = True
    enable_yara_scan: bool = True
    enable_content_inspection: bool = True

    # Advanced validation
    check_file_headers: bool = True
    check_embedded_content: bool = True
    sanitize_filenames: bool = True

    # Quarantine settings
    quarantine_suspicious: bool = True
    quarantine_path: str = "/tmp/quarantine"

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [".pdf", ".docx", ".doc", ".txt", ".rtf"]
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
                "text/plain",
                "application/rtf",
            ]


class SecureFileValidator:
    """
    Comprehensive file validation for legal document uploads
    Implements defense-in-depth security approach
    """

    def __init__(
        self, config: FileValidationConfig = None, audit_logger: AuditLogger = None
    ):
        self.config = config or FileValidationConfig()
        self.audit_logger = audit_logger

        # Initialize magic for file type detection
        self.file_magic = magic.Magic(mime=True)

        # Initialize ClamAV connection if available
        self.clamav = None
        if self.config.enable_virus_scan:
            try:
                self.clamav = clamd.ClamdUnixSocket()
                self.clamav.ping()
                logger.info("ClamAV antivirus connected successfully")
            except Exception as e:
                logger.warning(f"ClamAV not available: {e}")
                self.clamav = None

        # Load YARA rules if enabled
        self.yara_rules = None
        if self.config.enable_yara_scan:
            self._load_yara_rules()

        # Create quarantine directory
        os.makedirs(self.config.quarantine_path, exist_ok=True)

    async def validate_upload(
        self, file: UploadFile, user_id: str, organization_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate uploaded file through multiple security checks

        Returns:
            Tuple of (is_valid, validation_details)
        """
        validation_start = datetime.utcnow()
        validation_results = {
            "filename": file.filename,
            "size": 0,
            "mime_type": None,
            "checks_passed": [],
            "checks_failed": [],
            "risk_score": 0,
            "sanitized_filename": None,
        }

        temp_file = None

        try:
            # Save to temporary file for scanning
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_file = tmp.name
                validation_results["size"] = len(content)

            # Reset file position
            await file.seek(0)

            # 1. Filename validation and sanitization
            is_valid, sanitized_name = self._validate_filename(file.filename)
            if not is_valid:
                validation_results["checks_failed"].append("filename_validation")
                validation_results["risk_score"] += 20
            else:
                validation_results["checks_passed"].append("filename_validation")
                validation_results["sanitized_filename"] = sanitized_name

            # 2. File size validation
            if not self._validate_file_size(len(content)):
                validation_results["checks_failed"].append("file_size")
                validation_results["risk_score"] += 10
                self._log_validation_failure(
                    user_id, organization_id, file.filename, "file_size"
                )
                return False, validation_results
            else:
                validation_results["checks_passed"].append("file_size")

            # 3. File extension validation
            if not self._validate_extension(file.filename):
                validation_results["checks_failed"].append("file_extension")
                validation_results["risk_score"] += 30
                self._log_validation_failure(
                    user_id, organization_id, file.filename, "invalid_extension"
                )
                return False, validation_results
            else:
                validation_results["checks_passed"].append("file_extension")

            # 4. MIME type validation
            detected_mime = self.file_magic.from_file(temp_file)
            validation_results["mime_type"] = detected_mime

            if not self._validate_mime_type(detected_mime, file.filename):
                validation_results["checks_failed"].append("mime_type")
                validation_results["risk_score"] += 40
                self._log_validation_failure(
                    user_id, organization_id, file.filename, "mime_mismatch"
                )
                return False, validation_results
            else:
                validation_results["checks_passed"].append("mime_type")

            # 5. File header validation (magic bytes)
            if self.config.check_file_headers:
                if not self._validate_file_header(temp_file, detected_mime):
                    validation_results["checks_failed"].append("file_header")
                    validation_results["risk_score"] += 50
                else:
                    validation_results["checks_passed"].append("file_header")

            # 6. Virus scanning
            if self.config.enable_virus_scan and self.clamav:
                scan_result = self._scan_for_viruses(temp_file)
                if scan_result:
                    validation_results["checks_failed"].append("virus_scan")
                    validation_results["risk_score"] += 100
                    validation_results["virus_detected"] = scan_result

                    # Quarantine file
                    if self.config.quarantine_suspicious:
                        self._quarantine_file(
                            temp_file, file.filename, "virus_detected"
                        )

                    self._log_security_threat(
                        user_id, organization_id, file.filename, "virus", scan_result
                    )
                    return False, validation_results
                else:
                    validation_results["checks_passed"].append("virus_scan")

            # 7. YARA rules scanning
            if self.config.enable_yara_scan and self.yara_rules:
                yara_matches = self._scan_with_yara(temp_file)
                if yara_matches:
                    validation_results["checks_failed"].append("yara_scan")
                    validation_results["risk_score"] += 70
                    validation_results["yara_matches"] = yara_matches

                    if self.config.quarantine_suspicious:
                        self._quarantine_file(temp_file, file.filename, "yara_match")

                    self._log_security_threat(
                        user_id, organization_id, file.filename, "yara", yara_matches
                    )
                else:
                    validation_results["checks_passed"].append("yara_scan")

            # 8. Content inspection for embedded threats
            if self.config.check_embedded_content:
                embedded_threats = self._check_embedded_content(
                    temp_file, detected_mime
                )
                if embedded_threats:
                    validation_results["checks_failed"].append("embedded_content")
                    validation_results["risk_score"] += embedded_threats["risk_score"]
                    validation_results["embedded_threats"] = embedded_threats["threats"]
                else:
                    validation_results["checks_passed"].append("embedded_content")

            # 9. Check for encrypted/password-protected files
            if self._is_encrypted(temp_file, detected_mime):
                validation_results["is_encrypted"] = True
                validation_results["risk_score"] += 20  # Slight risk increase

            # Calculate final validation result
            is_valid = validation_results["risk_score"] < 50

            # Log validation result
            if self.audit_logger:
                self.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.DOCUMENT_UPLOAD,
                        user_id=user_id,
                        organization_id=organization_id,
                        resource_type="file_validation",
                        resource_id=file.filename,
                        result="success" if is_valid else "failure",
                        details={
                            "risk_score": validation_results["risk_score"],
                            "checks_passed": validation_results["checks_passed"],
                            "checks_failed": validation_results["checks_failed"],
                            "duration_ms": int(
                                (datetime.utcnow() - validation_start).total_seconds()
                                * 1000
                            ),
                        },
                    )
                )

            return is_valid, validation_results

        except Exception as e:
            logger.error(f"File validation error: {e}", exc_info=True)
            validation_results["error"] = str(e)
            return False, validation_results

        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def _validate_filename(self, filename: str) -> Tuple[bool, str]:
        """Validate and sanitize filename"""
        if not filename:
            return False, ""

        # Remove path components
        filename = os.path.basename(filename)

        # Check for suspicious patterns
        suspicious_patterns = [
            "..",  # Directory traversal
            "~",  # Backup files
            "$",  # Hidden files
            ".exe",
            ".bat",
            ".cmd",
            ".com",  # Executables
            ".scr",
            ".vbs",
            ".js",  # Scripts
        ]

        for pattern in suspicious_patterns:
            if pattern in filename.lower():
                return False, ""

        # Sanitize filename
        if self.config.sanitize_filenames:
            # Replace problematic characters
            sanitized = "".join(c for c in filename if c.isalnum() or c in ".-_")

            # Ensure extension is preserved
            name, ext = os.path.splitext(filename)
            sanitized_name = "".join(c for c in name if c.isalnum() or c in "-_")

            # Limit length
            if len(sanitized_name) > 100:
                sanitized_name = sanitized_name[:100]

            sanitized = f"{sanitized_name}{ext}"

            return True, sanitized

        return True, filename

    def _validate_file_size(self, size: int) -> bool:
        """Validate file size"""
        return self.config.min_file_size <= size <= self.config.max_file_size

    def _validate_extension(self, filename: str) -> bool:
        """Validate file extension"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.config.allowed_extensions

    def _validate_mime_type(self, detected_mime: str, filename: str) -> bool:
        """Validate MIME type matches extension"""
        if detected_mime not in self.config.allowed_mime_types:
            return False

        # Check MIME type matches extension
        ext = os.path.splitext(filename)[1].lower()
        expected_mime = mimetypes.guess_type(filename)[0]

        # Allow some flexibility for text files
        if ext == ".txt" and detected_mime.startswith("text/"):
            return True

        # Strict checking for other types
        mime_extension_map = {
            "application/pdf": [".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
                ".docx"
            ],
            "application/msword": [".doc"],
            "application/rtf": [".rtf"],
        }

        allowed_extensions = mime_extension_map.get(detected_mime, [])
        return ext in allowed_extensions

    def _validate_file_header(self, filepath: str, mime_type: str) -> bool:
        """Validate file header (magic bytes)"""
        magic_bytes = {
            "application/pdf": b"%PDF",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": b"PK",
            "application/msword": b"\xd0\xcf\x11\xe0",
            "application/rtf": b"{\\rtf",
        }

        expected_header = magic_bytes.get(mime_type)
        if not expected_header:
            return True  # Skip validation for unknown types

        with open(filepath, "rb") as f:
            file_header = f.read(len(expected_header))

        return file_header.startswith(expected_header)

    def _scan_for_viruses(self, filepath: str) -> Optional[str]:
        """Scan file for viruses using ClamAV"""
        if not self.clamav:
            return None

        try:
            result = self.clamav.scan(filepath)
            if result and filepath in result:
                status, virus_name = result[filepath]
                if status == "FOUND":
                    return virus_name
        except Exception as e:
            logger.error(f"Virus scan error: {e}")

        return None

    def _load_yara_rules(self):
        """Load YARA rules for malware detection"""
        rules_content = """
        rule Suspicious_PDF_Javascript {
            meta:
                description = "Detect PDFs with embedded JavaScript"
                risk_score = 50
            strings:
                $js1 = "/JavaScript"
                $js2 = "/JS"
                $js3 = "app.alert"
                $js4 = "this.exportDataObject"
            condition:
                uint32(0) == 0x25504446 and any of them
        }
        
        rule Suspicious_Office_Macros {
            meta:
                description = "Detect Office documents with macros"
                risk_score = 40
            strings:
                $macro1 = "vbaProject.bin"
                $macro2 = "macros/vbaProject"
                $auto1 = "Auto_Open"
                $auto2 = "AutoOpen"
                $auto3 = "Document_Open"
            condition:
                (uint32(0) == 0x504B0304 or uint32(0) == 0xD0CF11E0) and 
                any of ($macro*) and any of ($auto*)
        }
        
        rule Embedded_Executable {
            meta:
                description = "Detect embedded executables"
                risk_score = 80
            strings:
                $mz = "MZ"
                $pe = "PE"
                $elf = "\x7fELF"
            condition:
                any of them at 0 or
                for any i in (0..filesize-1024) : (
                    uint16(i) == 0x5A4D and uint32(uint32(i+0x3C)+i) == 0x00004550
                )
        }
        """

        try:
            self.yara_rules = yara.compile(source=rules_content)
            logger.info("YARA rules loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YARA rules: {e}")
            self.yara_rules = None

    def _scan_with_yara(self, filepath: str) -> List[str]:
        """Scan file with YARA rules"""
        if not self.yara_rules:
            return []

        try:
            matches = self.yara_rules.match(filepath)
            return [match.rule for match in matches]
        except Exception as e:
            logger.error(f"YARA scan error: {e}")
            return []

    def _check_embedded_content(
        self, filepath: str, mime_type: str
    ) -> Optional[Dict[str, Any]]:
        """Check for embedded threats in documents"""
        threats = []
        risk_score = 0

        # PDF-specific checks
        if mime_type == "application/pdf":
            with open(filepath, "rb") as f:
                content = f.read()

                # Check for JavaScript
                if b"/JavaScript" in content or b"/JS" in content:
                    threats.append("embedded_javascript")
                    risk_score += 30

                # Check for embedded files
                if b"/EmbeddedFile" in content:
                    threats.append("embedded_files")
                    risk_score += 20

                # Check for launch actions
                if b"/Launch" in content:
                    threats.append("launch_action")
                    risk_score += 40

        # Office document checks
        elif mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            # Check for OLE objects
            if zipfile.is_zipfile(filepath):
                try:
                    with zipfile.ZipFile(filepath, "r") as zf:
                        for filename in zf.namelist():
                            if "embeddings" in filename or "oleObject" in filename:
                                threats.append("ole_objects")
                                risk_score += 30
                                break
                except Exception:
                    pass

        if threats:
            return {"threats": threats, "risk_score": risk_score}

        return None

    def _is_encrypted(self, filepath: str, mime_type: str) -> bool:
        """Check if file is encrypted or password-protected"""
        # PDF encryption check
        if mime_type == "application/pdf":
            with open(filepath, "rb") as f:
                content = f.read(1024)  # Read first KB
                return b"/Encrypt" in content

        # Office document encryption indicators
        elif mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
            try:
                with zipfile.ZipFile(filepath, "r") as zf:
                    # Encrypted Office files have specific structure
                    return "EncryptionInfo" in zf.namelist()
            except Exception:
                pass

        return False

    def _quarantine_file(self, filepath: str, original_filename: str, reason: str):
        """Move suspicious file to quarantine"""
        try:
            quarantine_name = (
                f"{datetime.utcnow().isoformat()}_{reason}_{original_filename}"
            )
            quarantine_path = os.path.join(self.config.quarantine_path, quarantine_name)
            shutil.move(filepath, quarantine_path)

            logger.warning(f"File quarantined: {original_filename} - Reason: {reason}")

            # Write quarantine metadata
            metadata_path = f"{quarantine_path}.metadata"
            with open(metadata_path, "w") as f:
                f.write(f"Original: {original_filename}\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Date: {datetime.utcnow().isoformat()}\n")

        except Exception as e:
            logger.error(f"Failed to quarantine file: {e}")

    def _log_validation_failure(
        self, user_id: str, org_id: str, filename: str, reason: str
    ):
        """Log validation failure"""
        if self.audit_logger:
            self.audit_logger.log_event(
                AuditEvent(
                    event_type=AuditEventType.SECURITY_EVENT,
                    user_id=user_id,
                    organization_id=org_id,
                    action="file_validation_failed",
                    resource_type="upload",
                    resource_id=filename,
                    result="blocked",
                    details={"reason": reason},
                )
            )

    def _log_security_threat(
        self, user_id: str, org_id: str, filename: str, threat_type: str, details: Any
    ):
        """Log security threat detection"""
        if self.audit_logger:
            self.audit_logger.log_event(
                AuditEvent(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    user_id=user_id,
                    organization_id=org_id,
                    action="threat_detected",
                    resource_type="upload",
                    resource_id=filename,
                    result="blocked",
                    details={"threat_type": threat_type, "threat_details": details},
                )
            )
