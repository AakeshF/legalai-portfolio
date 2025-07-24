# services/mcp_servers/court_types.py - Shared court system types

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Any, List, Optional


@dataclass
class CaseInfo:
    """Information about a court case"""
    case_number: str
    case_title: str
    filing_date: date
    case_type: str
    status: str
    parties: List[Dict[str, str]]
    docket_entries: List[Dict[str, Any]]
    next_hearing_date: Optional[date] = None
    judge: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_number": self.case_number,
            "case_title": self.case_title,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "case_type": self.case_type,
            "status": self.status,
            "parties": self.parties,
            "docket_entries": self.docket_entries,
            "next_hearing_date": self.next_hearing_date.isoformat() if self.next_hearing_date else None,
            "judge": self.judge
        }


@dataclass
class FilingRequirements:
    """Requirements for filing documents with a court"""
    court_name: str
    case_type: str
    required_documents: List[str]
    filing_fee: float
    service_requirements: List[str]
    deadlines: Dict[str, int]  # deadline_type -> days
    special_instructions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "court_name": self.court_name,
            "case_type": self.case_type,
            "required_documents": self.required_documents,
            "filing_fee": self.filing_fee,
            "service_requirements": self.service_requirements,
            "deadlines": self.deadlines,
            "special_instructions": self.special_instructions
        }