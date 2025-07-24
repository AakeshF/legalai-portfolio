# services/mcp_servers/court_adapters.py - Court-specific adapter implementations

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import from court_types to avoid circular import
from .court_types import CaseInfo, FilingRequirements

class CourtAdapter(ABC):
    """Base class for court-specific adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config["base_url"]
        self.name = config["name"]
        
    @abstractmethod
    async def search_by_case_number(self, case_number: str) -> List[Dict[str, Any]]:
        """Search cases by case number"""
        pass
        
    @abstractmethod
    async def search_by_party_name(self, party_name: str) -> List[Dict[str, Any]]:
        """Search cases by party name"""
        pass
        
    @abstractmethod
    async def get_case_details(self, case_number: str) -> Optional[CaseInfo]:
        """Get detailed case information"""
        pass
        
    @abstractmethod
    async def get_court_calendar(self, start_date: date, end_date: date, 
                                judge: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get court calendar events"""
        pass
        
    @abstractmethod
    async def get_local_rules(self, category: str = "all") -> List[Dict[str, Any]]:
        """Get local court rules"""
        pass
        
    @abstractmethod
    async def get_filing_requirements(self, document_type: str) -> Optional[FilingRequirements]:
        """Get filing requirements for document type"""
        pass
        
    @abstractmethod
    async def get_court_holidays(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get court holidays"""
        pass


class HamiltonCountyAdapter(CourtAdapter):
    """Adapter for Hamilton County Court of Common Pleas (Ohio)"""
    
    async def search_by_case_number(self, case_number: str) -> List[Dict[str, Any]]:
        """Search cases by case number using web scraping"""
        async with aiohttp.ClientSession() as session:
            # Format case number for Hamilton County (e.g., A2301234)
            formatted_case = self._format_case_number(case_number)
            
            search_url = f"{self.base_url}/case-search"
            data = {
                "case_number": formatted_case,
                "search_type": "case_number"
            }
            
            try:
                async with session.post(search_url, data=data) as response:
                    html = await response.text()
                    return self._parse_search_results(html)
            except Exception as e:
                logger.error(f"Hamilton County case search error: {str(e)}")
                return []
                
    async def search_by_party_name(self, party_name: str) -> List[Dict[str, Any]]:
        """Search cases by party name"""
        async with aiohttp.ClientSession() as session:
            search_url = f"{self.base_url}/case-search"
            data = {
                "party_name": party_name,
                "search_type": "party"
            }
            
            try:
                async with session.post(search_url, data=data) as response:
                    html = await response.text()
                    return self._parse_search_results(html)
            except Exception as e:
                logger.error(f"Hamilton County party search error: {str(e)}")
                return []
                
    async def get_case_details(self, case_number: str) -> Optional[CaseInfo]:
        """Get detailed case information via web scraping"""
        async with aiohttp.ClientSession() as session:
            case_url = f"{self.base_url}/case/{case_number}"
            
            try:
                async with session.get(case_url) as response:
                    html = await response.text()
                    return self._parse_case_details(html, case_number)
            except Exception as e:
                logger.error(f"Hamilton County case details error: {str(e)}")
                return None
                
    async def get_court_calendar(self, start_date: date, end_date: date, 
                                judge: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get court calendar via web scraping"""
        async with aiohttp.ClientSession() as session:
            calendar_url = f"{self.base_url}/calendar"
            params = {
                "start_date": start_date.strftime("%m/%d/%Y"),
                "end_date": end_date.strftime("%m/%d/%Y")
            }
            if judge:
                params["judge"] = judge
                
            try:
                async with session.get(calendar_url, params=params) as response:
                    html = await response.text()
                    return self._parse_calendar(html)
            except Exception as e:
                logger.error(f"Hamilton County calendar error: {str(e)}")
                return []
                
    async def get_local_rules(self, category: str = "all") -> List[Dict[str, Any]]:
        """Get local court rules"""
        rules = []
        
        # Hamilton County specific rules
        if category in ["all", "civil"]:
            rules.extend([
                {
                    "rule_number": "3.01",
                    "title": "Assignment of Cases",
                    "category": "civil",
                    "text": "All civil cases shall be randomly assigned..."
                },
                {
                    "rule_number": "12.01",
                    "title": "Motion Practice",
                    "category": "civil",
                    "text": "All motions must be filed with proposed orders..."
                }
            ])
            
        if category in ["all", "criminal"]:
            rules.extend([
                {
                    "rule_number": "24.01",
                    "title": "Arraignment Procedures",
                    "category": "criminal",
                    "text": "Arraignments shall be conducted within 48 hours..."
                }
            ])
            
        return rules
        
    async def get_filing_requirements(self, document_type: str) -> Optional[FilingRequirements]:
        """Get filing requirements for document type"""
        requirements_map = {
            "complaint": FilingRequirements(
                document_type="complaint",
                required_copies=3,
                filing_fee=250.00,
                service_requirements=["Personal service required", "Service within 120 days"],
                formatting_rules={
                    "font": "Times New Roman 12pt",
                    "margins": "1 inch all sides",
                    "line_spacing": "double",
                    "page_limit": None
                },
                deadlines=[
                    {"name": "Service deadline", "days": 120, "from": "filing"}
                ]
            ),
            "motion": FilingRequirements(
                document_type="motion",
                required_copies=2,
                filing_fee=50.00,
                service_requirements=["Electronic service acceptable"],
                formatting_rules={
                    "font": "Times New Roman 12pt",
                    "margins": "1 inch all sides",
                    "line_spacing": "double",
                    "page_limit": 20
                },
                deadlines=[
                    {"name": "Response deadline", "days": 21, "from": "service"}
                ]
            )
        }
        
        return requirements_map.get(document_type.lower())
        
    async def get_court_holidays(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get court holidays"""
        # Hamilton County observed holidays
        holidays = [
            {"date": "2024-01-01", "name": "New Year's Day"},
            {"date": "2024-01-15", "name": "Martin Luther King Jr. Day"},
            {"date": "2024-02-19", "name": "Presidents Day"},
            {"date": "2024-05-27", "name": "Memorial Day"},
            {"date": "2024-07-04", "name": "Independence Day"},
            {"date": "2024-09-02", "name": "Labor Day"},
            {"date": "2024-10-14", "name": "Columbus Day"},
            {"date": "2024-11-11", "name": "Veterans Day"},
            {"date": "2024-11-28", "name": "Thanksgiving Day"},
            {"date": "2024-11-29", "name": "Day after Thanksgiving"},
            {"date": "2024-12-25", "name": "Christmas Day"}
        ]
        
        # Filter by date range
        return [h for h in holidays 
                if start_date <= datetime.strptime(h["date"], "%Y-%m-%d").date() <= end_date]
                
    def _format_case_number(self, case_number: str) -> str:
        """Format case number for Hamilton County"""
        # Remove spaces and hyphens
        clean = re.sub(r'[\s\-]', '', case_number.upper())
        return clean
        
    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse search results from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result rows (example structure)
        for row in soup.select('tr.case-result'):
            case_link = row.select_one('a.case-number')
            if case_link:
                results.append({
                    "case_number": case_link.text.strip(),
                    "case_name": row.select_one('.case-name').text.strip(),
                    "filing_date": row.select_one('.filing-date').text.strip(),
                    "status": row.select_one('.case-status').text.strip()
                })
                
        return results
        
    def _parse_case_details(self, html: str, case_number: str) -> Optional[CaseInfo]:
        """Parse case details from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract case information
            case_name = soup.select_one('.case-title').text.strip()
            filing_date_str = soup.select_one('.filing-date').text.strip()
            filing_date = datetime.strptime(filing_date_str, "%m/%d/%Y")
            case_type = soup.select_one('.case-type').text.strip()
            status = soup.select_one('.case-status').text.strip()
            judge = soup.select_one('.assigned-judge').text.strip()
            
            # Extract parties
            parties = []
            for party_row in soup.select('.party-row'):
                parties.append({
                    "name": party_row.select_one('.party-name').text.strip(),
                    "type": party_row.select_one('.party-type').text.strip(),
                    "attorney": party_row.select_one('.attorney-name').text.strip() if party_row.select_one('.attorney-name') else None
                })
                
            # Extract docket entries
            events = []
            for event_row in soup.select('.docket-entry'):
                events.append({
                    "date": event_row.select_one('.entry-date').text.strip(),
                    "description": event_row.select_one('.entry-text').text.strip(),
                    "filed_by": event_row.select_one('.filed-by').text.strip() if event_row.select_one('.filed-by') else None
                })
                
            return CaseInfo(
                case_number=case_number,
                case_name=case_name,
                filing_date=filing_date,
                case_type=case_type,
                status=status,
                judge=judge,
                parties=parties,
                events=events
            )
            
        except Exception as e:
            logger.error(f"Error parsing case details: {str(e)}")
            return None
            
    def _parse_calendar(self, html: str) -> List[Dict[str, Any]]:
        """Parse calendar from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        events = []
        
        for event in soup.select('.calendar-event'):
            events.append({
                "date": event.select_one('.event-date').text.strip(),
                "time": event.select_one('.event-time').text.strip(),
                "case_number": event.select_one('.case-number').text.strip(),
                "case_name": event.select_one('.case-name').text.strip(),
                "event_type": event.select_one('.event-type').text.strip(),
                "judge": event.select_one('.judge-name').text.strip(),
                "courtroom": event.select_one('.courtroom').text.strip()
            })
            
        return events


class CampbellCountyAdapter(CourtAdapter):
    """Adapter for Campbell County Circuit Court (Kentucky) - REST API based"""
    
    async def search_by_case_number(self, case_number: str) -> List[Dict[str, Any]]:
        """Search cases using REST API"""
        async with aiohttp.ClientSession() as session:
            api_url = f"{self.base_url}/api/cases/search"
            params = {
                "case_number": case_number,
                "court": "campbell_circuit"
            }
            
            try:
                async with session.get(api_url, params=params) as response:
                    data = await response.json()
                    return data.get("results", [])
            except Exception as e:
                logger.error(f"Campbell County API error: {str(e)}")
                return []
                
    async def search_by_party_name(self, party_name: str) -> List[Dict[str, Any]]:
        """Search cases by party name"""
        async with aiohttp.ClientSession() as session:
            api_url = f"{self.base_url}/api/cases/search"
            params = {
                "party_name": party_name,
                "court": "campbell_circuit"
            }
            
            try:
                async with session.get(api_url, params=params) as response:
                    data = await response.json()
                    return data.get("results", [])
            except Exception as e:
                logger.error(f"Campbell County API error: {str(e)}")
                return []
                
    async def get_case_details(self, case_number: str) -> Optional[CaseInfo]:
        """Get case details via API"""
        async with aiohttp.ClientSession() as session:
            api_url = f"{self.base_url}/api/cases/{case_number}"
            
            try:
                async with session.get(api_url) as response:
                    data = await response.json()
                    
                    if data:
                        return CaseInfo(
                            case_number=data["case_number"],
                            case_name=data["case_name"],
                            filing_date=datetime.fromisoformat(data["filing_date"]),
                            case_type=data["case_type"],
                            status=data["status"],
                            judge=data.get("judge"),
                            parties=data.get("parties", []),
                            events=data.get("events", []),
                            documents=data.get("documents", [])
                        )
                    return None
                    
            except Exception as e:
                logger.error(f"Campbell County case details error: {str(e)}")
                return None
                
    async def get_court_calendar(self, start_date: date, end_date: date, 
                                judge: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get court calendar via API"""
        async with aiohttp.ClientSession() as session:
            api_url = f"{self.base_url}/api/calendar"
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "court": "campbell_circuit"
            }
            if judge:
                params["judge"] = judge
                
            try:
                async with session.get(api_url, params=params) as response:
                    data = await response.json()
                    return data.get("events", [])
            except Exception as e:
                logger.error(f"Campbell County calendar error: {str(e)}")
                return []
                
    async def get_local_rules(self, category: str = "all") -> List[Dict[str, Any]]:
        """Get local court rules"""
        # Kentucky Rules of Civil Procedure apply
        rules = []
        
        if category in ["all", "civil"]:
            rules.extend([
                {
                    "rule_number": "CR 3.03",
                    "title": "Commencement of Action",
                    "category": "civil",
                    "text": "A civil action is commenced by filing a complaint..."
                },
                {
                    "rule_number": "CR 12.02",
                    "title": "Time to Answer",
                    "category": "civil",
                    "text": "A defendant shall serve an answer within 20 days..."
                }
            ])
            
        return rules
        
    async def get_filing_requirements(self, document_type: str) -> Optional[FilingRequirements]:
        """Get filing requirements"""
        requirements_map = {
            "complaint": FilingRequirements(
                document_type="complaint",
                required_copies=2,
                filing_fee=178.00,  # Kentucky circuit court filing fee
                service_requirements=["Service by certified mail acceptable"],
                formatting_rules={
                    "font": "Courier or Times New Roman",
                    "margins": "1 inch minimum",
                    "line_spacing": "double",
                    "page_limit": None
                },
                deadlines=[
                    {"name": "Service deadline", "days": 120, "from": "filing"}
                ]
            )
        }
        
        return requirements_map.get(document_type.lower())
        
    async def get_court_holidays(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get Kentucky court holidays"""
        holidays = [
            {"date": "2024-01-01", "name": "New Year's Day"},
            {"date": "2024-01-15", "name": "Martin Luther King Jr. Day"},
            {"date": "2024-02-19", "name": "Presidents Day"},
            {"date": "2024-03-29", "name": "Good Friday"},  # Kentucky observes
            {"date": "2024-05-27", "name": "Memorial Day"},
            {"date": "2024-07-04", "name": "Independence Day"},
            {"date": "2024-09-02", "name": "Labor Day"},
            {"date": "2024-11-05", "name": "Election Day"},  # Kentucky observes
            {"date": "2024-11-11", "name": "Veterans Day"},
            {"date": "2024-11-28", "name": "Thanksgiving Day"},
            {"date": "2024-11-29", "name": "Day after Thanksgiving"},
            {"date": "2024-12-24", "name": "Christmas Eve"},
            {"date": "2024-12-25", "name": "Christmas Day"},
            {"date": "2024-12-31", "name": "New Year's Eve"}
        ]
        
        return [h for h in holidays 
                if start_date <= datetime.strptime(h["date"], "%Y-%m-%d").date() <= end_date]


class KentonCountyAdapter(CampbellCountyAdapter):
    """Adapter for Kenton County Circuit Court (Kentucky) - inherits from Campbell"""
    
    async def get_filing_requirements(self, document_type: str) -> Optional[FilingRequirements]:
        """Get Kenton County specific filing requirements"""
        # Kenton County may have slightly different requirements
        requirements = await super().get_filing_requirements(document_type)
        
        if requirements and document_type == "complaint":
            # Kenton County specific modifications
            requirements.required_copies = 3  # Kenton requires an extra copy
            
        return requirements
        
    async def get_local_rules(self, category: str = "all") -> List[Dict[str, Any]]:
        """Get Kenton County specific local rules"""
        rules = await super().get_local_rules(category)
        
        # Add Kenton County specific rules
        if category in ["all", "civil"]:
            rules.append({
                "rule_number": "LR 3.01",
                "title": "Electronic Filing Requirements",
                "category": "civil",
                "text": "All attorneys must file documents electronically..."
            })
            
        return rules