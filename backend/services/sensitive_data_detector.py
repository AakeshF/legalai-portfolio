import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
import spacy
from transformers import pipeline
import logging
from datetime import datetime

from models import Organization, User

logger = logging.getLogger(__name__)


@dataclass
class SensitiveDataItem:
    type: str
    text: str
    start: int
    end: int
    confidence: float
    category: str  # pii, legal, financial, medical, privileged
    severity: str  # low, medium, high, critical


class SensitiveDataDetector:
    """
    ML-powered detection service for sensitive legal data
    """

    def __init__(self):
        self.nlp = None
        self.classifier = None
        self._init_models()

        # Categories of sensitive data
        self.categories = {
            "pii": ["person_name", "ssn", "phone", "email", "address", "date_of_birth"],
            "legal": ["case_number", "attorney_client", "work_product", "court_filing"],
            "financial": [
                "credit_card",
                "bank_account",
                "ein",
                "currency",
                "financial_record",
            ],
            "medical": ["medical_record", "diagnosis", "treatment", "medication"],
            "privileged": [
                "privileged_communication",
                "confidential_memo",
                "settlement_terms",
            ],
        }

        # Severity mapping
        self.severity_map = {
            "ssn": "critical",
            "credit_card": "critical",
            "bank_account": "critical",
            "medical_record": "critical",
            "privileged_communication": "critical",
            "attorney_client": "high",
            "work_product": "high",
            "settlement_terms": "high",
            "person_name": "medium",
            "case_number": "medium",
            "phone": "low",
            "email": "low",
        }

    def _init_models(self):
        """Initialize NLP and ML models"""
        try:
            # SpaCy for entity recognition
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("SpaCy model not found. Installing...")
            import subprocess

            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")

        try:
            # Transformer model for classification
            self.classifier = pipeline(
                "text-classification",
                model="dslim/bert-base-NER",
                aggregation_strategy="simple",
            )
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}")
            self.classifier = None

    async def analyze(
        self,
        text: str,
        db: Session,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze text for sensitive data with ML and pattern matching
        """
        detected_items = []

        # Pattern-based detection
        pattern_items = self._detect_patterns(text)
        detected_items.extend(pattern_items)

        # NLP entity detection
        nlp_items = self._detect_entities(text)
        detected_items.extend(nlp_items)

        # Context-based detection
        context_items = self._detect_contextual_sensitive(text)
        detected_items.extend(context_items)

        # ML classification if available
        if self.classifier:
            ml_items = await self._detect_with_ml(text)
            detected_items.extend(ml_items)

        # Remove duplicates and merge overlapping detections
        detected_items = self._merge_detections(detected_items)

        # Calculate overall sensitivity score
        sensitivity_score = self._calculate_sensitivity_score(detected_items)

        # Categorize items
        categorized = self._categorize_items(detected_items)

        # Apply organization-specific rules
        if org_id:
            detected_items = self._apply_org_rules(detected_items, db, org_id)

        return {
            "detected_items": [self._item_to_dict(item) for item in detected_items],
            "overall_sensitivity": sensitivity_score,
            "categories": categorized,
            "requires_consent": self._requires_consent(detected_items),
            "summary": self._generate_summary(detected_items),
        }

    def _detect_patterns(self, text: str) -> List[SensitiveDataItem]:
        """Detect using regex patterns"""
        patterns = {
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "case_number": r"\b(?:Case\s*(?:No\.?|Number)?:?\s*)?(\d{2,4}[-\s]?[A-Z]{2,4}[-\s]?\d{3,6})\b",
            "bank_account": r"\b\d{8,17}\b",
            "ein": r"\b\d{2}-\d{7}\b",
            "medical_record": r"\b(?:MRN|Medical Record Number):?\s*\d{6,10}\b",
            "privileged": r"\b(?:PRIVILEGED|CONFIDENTIAL|ATTORNEY[- ]CLIENT)\b",
        }

        detected = []
        for pattern_type, regex in patterns.items():
            for match in re.finditer(regex, text, re.IGNORECASE):
                category = self._get_category(pattern_type)
                detected.append(
                    SensitiveDataItem(
                        type=pattern_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.95,
                        category=category,
                        severity=self.severity_map.get(pattern_type, "medium"),
                    )
                )

        return detected

    def _detect_entities(self, text: str) -> List[SensitiveDataItem]:
        """Detect using NLP entity recognition"""
        doc = self.nlp(text)
        detected = []

        entity_mapping = {
            "PERSON": ("person_name", "pii", 0.8),
            "ORG": ("organization", "legal", 0.7),
            "DATE": ("date", "pii", 0.6),
            "MONEY": ("currency", "financial", 0.8),
            "GPE": ("location", "pii", 0.6),
        }

        for ent in doc.ents:
            if ent.label_ in entity_mapping:
                data_type, category, confidence = entity_mapping[ent.label_]
                detected.append(
                    SensitiveDataItem(
                        type=data_type,
                        text=ent.text,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=confidence,
                        category=category,
                        severity=self.severity_map.get(data_type, "low"),
                    )
                )

        return detected

    def _detect_contextual_sensitive(self, text: str) -> List[SensitiveDataItem]:
        """Detect sensitive data based on context"""
        detected = []

        # Legal privilege indicators
        privilege_patterns = [
            (r"(?:attorney[- ]client|legal advice|work product)", "attorney_client"),
            (
                r"(?:confidential memorandum|privileged communication)",
                "privileged_communication",
            ),
            (r"(?:settlement discussion|mediation)", "settlement_terms"),
        ]

        for pattern, data_type in privilege_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Look for context around the match
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]

                # Increase confidence if certain keywords are present
                confidence = 0.7
                if any(
                    word in context.lower()
                    for word in ["confidential", "privileged", "not for disclosure"]
                ):
                    confidence = 0.9

                detected.append(
                    SensitiveDataItem(
                        type=data_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence,
                        category="privileged",
                        severity="high",
                    )
                )

        return detected

    async def _detect_with_ml(self, text: str) -> List[SensitiveDataItem]:
        """Use ML model for detection"""
        detected = []

        try:
            # Split text into chunks for classification
            chunks = self._split_text(text, 512)

            for chunk_text, chunk_start in chunks:
                results = self.classifier(chunk_text)

                for result in results:
                    if result["score"] > 0.7:
                        # Map ML labels to our types
                        data_type = self._map_ml_label(result["label"])
                        if data_type:
                            detected.append(
                                SensitiveDataItem(
                                    type=data_type,
                                    text=result.get("word", chunk_text),
                                    start=chunk_start + result.get("start", 0),
                                    end=chunk_start
                                    + result.get("end", len(chunk_text)),
                                    confidence=result["score"],
                                    category=self._get_category(data_type),
                                    severity=self.severity_map.get(data_type, "medium"),
                                )
                            )
        except Exception as e:
            logger.error(f"ML detection error: {e}")

        return detected

    def _split_text(self, text: str, max_length: int) -> List[Tuple[str, int]]:
        """Split text into chunks for processing"""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        chunk_start = 0

        for i, word in enumerate(words):
            if current_length + len(word) > max_length:
                chunk_text = " ".join(current_chunk)
                chunks.append((chunk_text, chunk_start))
                current_chunk = [word]
                current_length = len(word)
                chunk_start = text.find(word, chunk_start + len(chunk_text))
            else:
                current_chunk.append(word)
                current_length += len(word) + 1

        if current_chunk:
            chunks.append((" ".join(current_chunk), chunk_start))

        return chunks

    def _map_ml_label(self, label: str) -> Optional[str]:
        """Map ML model labels to our data types"""
        label_mapping = {
            "PER": "person_name",
            "ORG": "organization",
            "LOC": "location",
            "MISC": None,
        }
        return label_mapping.get(label.upper())

    def _merge_detections(
        self, items: List[SensitiveDataItem]
    ) -> List[SensitiveDataItem]:
        """Merge overlapping detections"""
        if not items:
            return []

        # Sort by start position
        sorted_items = sorted(items, key=lambda x: x.start)
        merged = []

        for item in sorted_items:
            if not merged or item.start >= merged[-1].end:
                merged.append(item)
            else:
                # Overlapping - keep the one with higher confidence
                if item.confidence > merged[-1].confidence:
                    merged[-1] = item

        return merged

    def _calculate_sensitivity_score(self, items: List[SensitiveDataItem]) -> float:
        """Calculate overall sensitivity score (0-1)"""
        if not items:
            return 0.0

        # Weight by severity
        severity_weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}

        total_weight = 0
        for item in items:
            weight = severity_weights.get(item.severity, 0.3)
            total_weight += weight * item.confidence

        # Normalize by number of items and scale
        score = min(1.0, total_weight / (len(items) * 0.5))

        return round(score, 2)

    def _categorize_items(self, items: List[SensitiveDataItem]) -> Dict[str, List[str]]:
        """Categorize detected items"""
        categorized = {}

        for item in items:
            if item.category not in categorized:
                categorized[item.category] = []
            if item.type not in categorized[item.category]:
                categorized[item.category].append(item.type)

        return categorized

    def _get_category(self, data_type: str) -> str:
        """Get category for a data type"""
        for category, types in self.categories.items():
            if data_type in types:
                return category
        return "other"

    def _requires_consent(self, items: List[SensitiveDataItem]) -> bool:
        """Check if any items require explicit consent"""
        consent_required_types = {
            "ssn",
            "credit_card",
            "bank_account",
            "medical_record",
            "privileged_communication",
        }

        return any(item.type in consent_required_types for item in items)

    def _generate_summary(self, items: List[SensitiveDataItem]) -> str:
        """Generate human-readable summary"""
        if not items:
            return "No sensitive data detected"

        type_counts = {}
        for item in items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1

        summary_parts = []
        for data_type, count in sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        ):
            summary_parts.append(f"{count} {data_type.replace('_', ' ')}")

        return f"Detected: {', '.join(summary_parts[:3])}" + (
            " and more" if len(summary_parts) > 3 else ""
        )

    def _apply_org_rules(
        self, items: List[SensitiveDataItem], db: Session, org_id: str
    ) -> List[SensitiveDataItem]:
        """Apply organization-specific detection rules"""
        # This would load org-specific patterns and thresholds
        # For now, return items as-is
        return items

    def _item_to_dict(self, item: SensitiveDataItem) -> Dict[str, Any]:
        """Convert item to dictionary"""
        return {
            "type": item.type,
            "text": item.text[:20] + "..." if len(item.text) > 20 else item.text,
            "position": {"start": item.start, "end": item.end},
            "confidence": item.confidence,
            "category": item.category,
            "severity": item.severity,
        }
