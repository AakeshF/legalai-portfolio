import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import spacy
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
import hashlib
import logging

from models import Organization, User, AnonymizationPattern, AnonymizationRule, RedactionToken
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class SensitivePattern:
    type: str
    pattern: str
    confidence: float
    start: int
    end: int
    original_text: str
    replacement: str
    needs_consent: bool = False


@dataclass
class AnonymizationResult:
    original: str
    redacted: str
    sensitive_patterns: List[SensitivePattern] = field(default_factory=list)
    needs_consent: bool = False
    token_mapping: Dict[str, str] = field(default_factory=dict)
    confidence_score: float = 0.0


class AnonymizationService:
    def __init__(self):
        self.nlp = None
        self._init_nlp()
        # Generate or use a proper Fernet key
        try:
            # Try to use the key as-is if it's already a valid Fernet key
            self.cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())
        except:
            # Generate a new valid Fernet key if the provided one is invalid
            from cryptography.fernet import Fernet
            generated_key = Fernet.generate_key()
            self.cipher_suite = Fernet(generated_key)
            print(f"Warning: Invalid encryption key. Generated new key for this session.")
        
        # Default patterns for legal documents
        self.default_patterns = {
            "case_number": r"\b(?:Case\s*(?:No\.?|Number)?:?\s*)?(\d{2,4}[-\s]?[A-Z]{2,4}[-\s]?\d{3,6})\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b",
            "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "date": r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
            "currency": r"\$[\d,]+(?:\.\d{2})?|\b\d+\s*(?:dollars?|USD)\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "driver_license": r"\b[A-Z]\d{7,8}\b",
            "passport": r"\b[A-Z]\d{8}\b",
            "ein": r"\b\d{2}-\d{7}\b",
            "bank_account": r"\b\d{8,17}\b",
            "address": r"\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Plaza|Pl)\b",
            "zip_code": r"\b\d{5}(?:-\d{4})?\b"
        }
    
    def _init_nlp(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("Spacy model not found. Installing...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
    
    def anonymize_text(
        self,
        text: str,
        db: Session,
        user_id: Optional[int] = None,
        org_id: Optional[int] = None,
        custom_patterns: Optional[Dict[str, str]] = None
    ) -> AnonymizationResult:
        """
        Anonymize text based on configured patterns and rules
        """
        result = AnonymizationResult(original=text, redacted=text)
        
        # Get organization and user-specific patterns
        patterns = self._get_patterns(db, user_id, org_id)
        if custom_patterns:
            patterns.update(custom_patterns)
        
        # Detect sensitive data using regex patterns
        regex_patterns = self._detect_regex_patterns(text, patterns)
        result.sensitive_patterns.extend(regex_patterns)
        
        # Detect entities using NLP
        nlp_entities = self._detect_nlp_entities(text)
        result.sensitive_patterns.extend(nlp_entities)
        
        # Get anonymization rules
        rules = self._get_rules(db, user_id, org_id)
        
        # Apply anonymization based on rules
        result.redacted, result.token_mapping = self._apply_anonymization(
            text, result.sensitive_patterns, rules
        )
        
        # Calculate overall confidence and consent requirements
        result.confidence_score = self._calculate_confidence(result.sensitive_patterns)
        result.needs_consent = self._check_consent_requirements(
            result.sensitive_patterns, rules
        )
        
        # Store redaction tokens for reversibility
        if user_id or org_id:
            self._store_redaction_tokens(db, result.token_mapping, user_id, org_id)
        
        return result
    
    def _get_patterns(
        self,
        db: Session,
        user_id: Optional[int],
        org_id: Optional[int]
    ) -> Dict[str, str]:
        """Get patterns from database with user/org overrides"""
        patterns = self.default_patterns.copy()
        
        # Add organization patterns
        if org_id:
            org_patterns = db.query(AnonymizationPattern).filter(
                AnonymizationPattern.organization_id == org_id,
                AnonymizationPattern.is_active == True
            ).all()
            for pattern in org_patterns:
                patterns[pattern.name] = pattern.regex_pattern
        
        # Add user-specific patterns (override org patterns)
        if user_id:
            user_patterns = db.query(AnonymizationPattern).filter(
                AnonymizationPattern.user_id == user_id,
                AnonymizationPattern.is_active == True
            ).all()
            for pattern in user_patterns:
                patterns[pattern.name] = pattern.regex_pattern
        
        return patterns
    
    def _get_rules(
        self,
        db: Session,
        user_id: Optional[int],
        org_id: Optional[int]
    ) -> List[AnonymizationRule]:
        """Get anonymization rules with user/org hierarchy"""
        rules = []
        
        # Get organization rules
        if org_id:
            org_rules = db.query(AnonymizationRule).filter(
                AnonymizationRule.organization_id == org_id,
                AnonymizationRule.is_active == True
            ).all()
            rules.extend(org_rules)
        
        # Get user rules (can override org rules)
        if user_id:
            user_rules = db.query(AnonymizationRule).filter(
                AnonymizationRule.user_id == user_id,
                AnonymizationRule.is_active == True
            ).all()
            rules.extend(user_rules)
        
        return rules
    
    def _detect_regex_patterns(
        self,
        text: str,
        patterns: Dict[str, str]
    ) -> List[SensitivePattern]:
        """Detect sensitive data using regex patterns"""
        detected = []
        
        for pattern_type, regex in patterns.items():
            try:
                for match in re.finditer(regex, text, re.IGNORECASE):
                    detected.append(SensitivePattern(
                        type=pattern_type,
                        pattern=regex,
                        confidence=0.9,  # High confidence for regex matches
                        start=match.start(),
                        end=match.end(),
                        original_text=match.group(),
                        replacement=self._generate_replacement(pattern_type, match.group())
                    ))
            except re.error as e:
                logger.error(f"Invalid regex pattern for {pattern_type}: {e}")
        
        return detected
    
    def _detect_nlp_entities(self, text: str) -> List[SensitivePattern]:
        """Detect entities using NLP"""
        detected = []
        doc = self.nlp(text)
        
        # Map spaCy entity types to our pattern types
        entity_mapping = {
            "PERSON": "person_name",
            "ORG": "organization",
            "GPE": "location",
            "DATE": "date",
            "MONEY": "currency",
            "FAC": "facility",
            "LOC": "location"
        }
        
        for ent in doc.ents:
            if ent.label_ in entity_mapping:
                pattern_type = entity_mapping[ent.label_]
                detected.append(SensitivePattern(
                    type=pattern_type,
                    pattern=f"NLP_{ent.label_}",
                    confidence=0.7,  # Lower confidence for NLP
                    start=ent.start_char,
                    end=ent.end_char,
                    original_text=ent.text,
                    replacement=self._generate_replacement(pattern_type, ent.text)
                ))
        
        return detected
    
    def _generate_replacement(self, pattern_type: str, original: str) -> str:
        """Generate consistent replacement tokens"""
        # Create a hash of the original text for consistency
        hash_obj = hashlib.md5(original.encode())
        hash_hex = hash_obj.hexdigest()[:6].upper()
        
        # Generate type-specific replacements
        replacements = {
            "person_name": f"[PERSON_{hash_hex}]",
            "case_number": f"[CASE_{hash_hex}]",
            "ssn": "[SSN_REDACTED]",
            "phone": f"[PHONE_{hash_hex}]",
            "email": f"[EMAIL_{hash_hex}]",
            "date": f"[DATE_{hash_hex}]",
            "currency": f"[AMOUNT_{hash_hex}]",
            "credit_card": "[CC_REDACTED]",
            "driver_license": "[DL_REDACTED]",
            "passport": "[PASSPORT_REDACTED]",
            "ein": "[EIN_REDACTED]",
            "bank_account": "[BANK_REDACTED]",
            "address": f"[ADDRESS_{hash_hex}]",
            "zip_code": f"[ZIP_{hash_hex}]",
            "organization": f"[ORG_{hash_hex}]",
            "location": f"[LOC_{hash_hex}]",
            "facility": f"[FAC_{hash_hex}]"
        }
        
        return replacements.get(pattern_type, f"[{pattern_type.upper()}_{hash_hex}]")
    
    def _apply_anonymization(
        self,
        text: str,
        patterns: List[SensitivePattern],
        rules: List[AnonymizationRule]
    ) -> Tuple[str, Dict[str, str]]:
        """Apply anonymization based on rules"""
        # Sort patterns by start position (reverse order for replacement)
        patterns.sort(key=lambda x: x.start, reverse=True)
        
        redacted_text = text
        token_mapping = {}
        
        for pattern in patterns:
            # Check if pattern should be anonymized based on rules
            should_anonymize = self._should_anonymize(pattern, rules)
            
            if should_anonymize:
                # Store mapping for reversibility
                encrypted_original = self.cipher_suite.encrypt(
                    pattern.original_text.encode()
                ).decode()
                token_mapping[pattern.replacement] = encrypted_original
                
                # Replace in text
                redacted_text = (
                    redacted_text[:pattern.start] +
                    pattern.replacement +
                    redacted_text[pattern.end:]
                )
        
        return redacted_text, token_mapping
    
    def _should_anonymize(
        self,
        pattern: SensitivePattern,
        rules: List[AnonymizationRule]
    ) -> bool:
        """Check if pattern should be anonymized based on rules"""
        # Find applicable rules for this pattern type
        applicable_rules = [
            rule for rule in rules
            if rule.pattern_type == pattern.type or rule.pattern_type == "all"
        ]
        
        if not applicable_rules:
            # Default to anonymize if no rules found
            return True
        
        # Check rules (user rules take precedence)
        for rule in sorted(applicable_rules, key=lambda x: x.user_id is not None, reverse=True):
            if rule.action == "redact":
                return True
            elif rule.action == "preserve":
                return False
            elif rule.action == "conditional":
                # Evaluate condition (simplified for now)
                if rule.condition and "confidence" in rule.condition:
                    min_confidence = float(rule.condition.get("min_confidence", 0.8))
                    return pattern.confidence >= min_confidence
        
        return True
    
    def _calculate_confidence(self, patterns: List[SensitivePattern]) -> float:
        """Calculate overall confidence score"""
        if not patterns:
            return 1.0
        
        total_confidence = sum(p.confidence for p in patterns)
        return total_confidence / len(patterns)
    
    def _check_consent_requirements(
        self,
        patterns: List[SensitivePattern],
        rules: List[AnonymizationRule]
    ) -> bool:
        """Check if consent is required for any patterns"""
        sensitive_types = {"ssn", "credit_card", "bank_account", "driver_license", "passport"}
        
        # Check if any highly sensitive data detected
        for pattern in patterns:
            if pattern.type in sensitive_types:
                # Check rules for consent requirements
                for rule in rules:
                    if rule.pattern_type == pattern.type and rule.requires_consent:
                        return True
        
        return False
    
    def _store_redaction_tokens(
        self,
        db: Session,
        token_mapping: Dict[str, str],
        user_id: Optional[int],
        org_id: Optional[int]
    ):
        """Store redaction tokens for later reversal"""
        for token, encrypted_value in token_mapping.items():
            redaction_token = RedactionToken(
                token=token,
                encrypted_value=encrypted_value,
                user_id=user_id,
                organization_id=org_id,
                created_at=datetime.utcnow()
            )
            db.add(redaction_token)
        
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to store redaction tokens: {e}")
            db.rollback()
    
    def deanonymize_text(
        self,
        text: str,
        db: Session,
        user_id: Optional[int] = None,
        org_id: Optional[int] = None
    ) -> str:
        """Reverse anonymization using stored tokens"""
        # Get stored tokens
        query = db.query(RedactionToken)
        if user_id:
            query = query.filter(RedactionToken.user_id == user_id)
        if org_id:
            query = query.filter(RedactionToken.organization_id == org_id)
        
        tokens = query.all()
        
        # Replace tokens with original values
        deanonymized_text = text
        for token_record in tokens:
            if token_record.token in deanonymized_text:
                try:
                    original = self.cipher_suite.decrypt(
                        token_record.encrypted_value.encode()
                    ).decode()
                    deanonymized_text = deanonymized_text.replace(
                        token_record.token, original
                    )
                except Exception as e:
                    logger.error(f"Failed to decrypt token {token_record.token}: {e}")
        
        return deanonymized_text