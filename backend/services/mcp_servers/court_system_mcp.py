# services/mcp_servers/court_system_mcp.py - Court System MCP Server implementation

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import logging
from bs4 import BeautifulSoup
import re

from .base_legal_mcp import BaseLegalMCPServer
from .court_adapters import (
    HamiltonCountyAdapter,
    CampbellCountyAdapter,
    KentonCountyAdapter
)
from .deadline_calculator import CourtDeadlineCalculator
from .court_types import CaseInfo, FilingRequirements

logger = logging.getLogger(__name__)

class CourtSystemMCPServer(BaseLegalMCPServer):
    """MCP Server for integrating with local court systems"""
    
    def __init__(self):
        super().__init__()
        
        # Court configurations
        self.court_configs = {
            "hamilton_county_oh": {
                "name": "Hamilton County Court of Common Pleas",
                "base_url": "https://www.courtclerk.org",
                "api_type": "web_scraping",
                "adapter_class": HamiltonCountyAdapter,
                "selectors": {
                    "case_search": "input#case-number",
                    "case_info": "div.case-details",
                    "party_list": "table.parties-table",
                    "docket": "table.docket-entries",
                    "calendar": "div.court-calendar"
                },
                "cache_ttl": {
                    "case_info": 60,  # 1 hour
                    "calendar": 1440,  # 24 hours
                    "rules": 10080  # 1 week
                }
            },
            "campbell_county_ky": {
                "name": "Campbell County Circuit Court",
                "base_url": "https://kcoj.kycourts.net",
                "api_type": "rest_api",
                "adapter_class": CampbellCountyAdapter,
                "api_endpoints": {
                    "case_search": "/api/cases/search",
                    "case_detail": "/api/cases/{case_number}",
                    "calendar": "/api/calendar",
                    "e_filing": "/api/efiling"
                },
                "cache_ttl": {
                    "case_info": 60,
                    "calendar": 1440,
                    "rules": 10080
                }
            },
            "kenton_county_ky": {
                "name": "Kenton County Circuit Court",
                "base_url": "https://kcoj.kycourts.net",
                "api_type": "rest_api",
                "adapter_class": KentonCountyAdapter,
                "api_endpoints": {
                    "case_search": "/api/cases/search",
                    "case_detail": "/api/cases/{case_number}",
                    "calendar": "/api/calendar",
                    "rules": "/api/local-rules"
                },
                "cache_ttl": {
                    "case_info": 60,
                    "calendar": 1440,
                    "rules": 10080
                }
            }
        }
        
        # Initialize court adapters
        self.adapters = {}
        for court_id, config in self.court_configs.items():
            adapter_class = config.get("adapter_class")
            if adapter_class:
                self.adapters[court_id] = adapter_class(config)
                
        # Initialize deadline calculator
        self.deadline_calculator = CourtDeadlineCalculator()
        
        # Track court availability
        self.court_status = {}
        
    async def query(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a query action with parameters"""
        try:
            # Clean expired cache periodically
            self._clean_expired_cache()
            
            if action == "search_case":
                return await self._search_case(params)
            elif action == "get_case_info":
                return await self._get_case_info(params)
            elif action == "get_calendar":
                return await self._get_court_calendar(params)
            elif action == "get_local_rules":
                return await self._get_local_rules(params)
            elif action == "calculate_deadlines":
                return await self._calculate_deadlines(params)
            elif action == "get_filing_requirements":
                return await self._get_filing_requirements(params)
            elif action == "check_court_holidays":
                return await self._check_court_holidays(params)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Court system query error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities and supported actions"""
        return {
            "server_name": "Court System MCP Server",
            "version": "1.0.0",
            "supported_courts": list(self.court_configs.keys()),
            "actions": {
                "search_case": {
                    "description": "Search for cases by number or party name",
                    "params": ["court_id", "case_number", "party_name"]
                },
                "get_case_info": {
                    "description": "Get detailed case information",
                    "params": ["court_id", "case_number"]
                },
                "get_calendar": {
                    "description": "Get court calendar for date range",
                    "params": ["court_id", "start_date", "end_date", "judge"]
                },
                "get_local_rules": {
                    "description": "Get local court rules",
                    "params": ["court_id", "rule_category"]
                },
                "calculate_deadlines": {
                    "description": "Calculate all deadlines from trigger date",
                    "params": ["trigger_date", "case_type", "jurisdiction"]
                },
                "get_filing_requirements": {
                    "description": "Get requirements for specific filing type",
                    "params": ["court_id", "document_type"]
                },
                "check_court_holidays": {
                    "description": "Check court holidays for date range",
                    "params": ["court_id", "start_date", "end_date"]
                }
            }
        }
        
    async def _search_case(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for cases across courts"""
        self.validate_params(params, ["court_id"])
        
        court_id = params["court_id"]
        case_number = params.get("case_number")
        party_name = params.get("party_name")
        
        if not case_number and not party_name:
            raise ValueError("Either case_number or party_name required")
            
        # Check cache
        cache_key = self._generate_cache_key("search_case", params)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Get adapter for court
        adapter = self.adapters.get(court_id)
        if not adapter:
            raise ValueError(f"Unsupported court: {court_id}")
            
        # Perform search
        try:
            if case_number:
                results = await adapter.search_by_case_number(case_number)
            else:
                results = await adapter.search_by_party_name(party_name)
                
            # Cache results
            cache_ttl = self.court_configs[court_id]["cache_ttl"]["case_info"]
            self._cache_result(cache_key, results, cache_ttl)
            
            return {
                "success": True,
                "court_id": court_id,
                "results": results,
                "search_criteria": {
                    "case_number": case_number,
                    "party_name": party_name
                }
            }
            
        except Exception as e:
            logger.error(f"Case search failed for {court_id}: {str(e)}")
            # Return cached stale data if available
            stale_data = self.cache.get(cache_key)
            if stale_data:
                return {
                    "success": True,
                    "court_id": court_id,
                    "results": stale_data.data.get("results", []),
                    "warning": "Using cached data due to court unavailability",
                    "cached_at": stale_data.expires_at - timedelta(minutes=cache_ttl)
                }
            raise
            
    async def _get_case_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed case information"""
        self.validate_params(params, ["court_id", "case_number"])
        
        court_id = params["court_id"]
        case_number = params["case_number"]
        
        # Check cache
        cache_key = self._generate_cache_key("get_case_info", params)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Get adapter
        adapter = self.adapters.get(court_id)
        if not adapter:
            raise ValueError(f"Unsupported court: {court_id}")
            
        # Get case info
        case_info = await adapter.get_case_details(case_number)
        
        # Enrich with calculated deadlines if applicable
        if case_info and case_info.filing_date:
            deadlines = await self._calculate_deadlines({
                "trigger_date": case_info.filing_date.isoformat(),
                "case_type": case_info.case_type,
                "jurisdiction": {"court_id": court_id}
            })
            case_info.calculated_deadlines = deadlines.get("deadlines", [])
            
        result = {
            "success": True,
            "court_id": court_id,
            "case_info": case_info.__dict__ if case_info else None
        }
        
        # Cache result
        cache_ttl = self.court_configs[court_id]["cache_ttl"]["case_info"]
        self._cache_result(cache_key, result, cache_ttl)
        
        return result
        
    async def _get_court_calendar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get court calendar for date range"""
        self.validate_params(params, ["court_id", "start_date", "end_date"])
        
        court_id = params["court_id"]
        start_date = datetime.fromisoformat(params["start_date"])
        end_date = datetime.fromisoformat(params["end_date"])
        judge = params.get("judge")
        
        # Check cache
        cache_key = self._generate_cache_key("get_calendar", params)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Get adapter
        adapter = self.adapters.get(court_id)
        if not adapter:
            raise ValueError(f"Unsupported court: {court_id}")
            
        # Get calendar
        calendar_events = await adapter.get_court_calendar(start_date, end_date, judge)
        
        result = {
            "success": True,
            "court_id": court_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "events": calendar_events,
            "total_events": len(calendar_events)
        }
        
        # Cache with 24-hour TTL
        cache_ttl = self.court_configs[court_id]["cache_ttl"]["calendar"]
        self._cache_result(cache_key, result, cache_ttl)
        
        return result
        
    async def _get_local_rules(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get local court rules"""
        self.validate_params(params, ["court_id"])
        
        court_id = params["court_id"]
        rule_category = params.get("rule_category", "all")
        
        # Check cache
        cache_key = self._generate_cache_key("get_local_rules", params)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Get adapter
        adapter = self.adapters.get(court_id)
        if not adapter:
            raise ValueError(f"Unsupported court: {court_id}")
            
        # Get rules
        rules = await adapter.get_local_rules(rule_category)
        
        result = {
            "success": True,
            "court_id": court_id,
            "rule_category": rule_category,
            "rules": rules,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Cache with 1-week TTL
        cache_ttl = self.court_configs[court_id]["cache_ttl"]["rules"]
        self._cache_result(cache_key, result, cache_ttl)
        
        return result
        
    async def _calculate_deadlines(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate all deadlines from trigger date"""
        self.validate_params(params, ["trigger_date", "case_type", "jurisdiction"])
        
        trigger_date = datetime.fromisoformat(params["trigger_date"])
        case_type = params["case_type"]
        jurisdiction = params["jurisdiction"]
        
        # Get court holidays if court_id provided
        court_holidays = []
        if "court_id" in jurisdiction:
            holidays_result = await self._check_court_holidays({
                "court_id": jurisdiction["court_id"],
                "start_date": trigger_date.isoformat(),
                "end_date": (trigger_date + timedelta(days=730)).isoformat()  # 2 years
            })
            court_holidays = holidays_result.get("holidays", [])
            
        # Calculate deadlines
        deadlines = self.deadline_calculator.calculate_all_deadlines(
            trigger_date=trigger_date,
            case_type=case_type,
            jurisdiction=jurisdiction,
            court_holidays=court_holidays
        )
        
        return {
            "success": True,
            "trigger_date": trigger_date.isoformat(),
            "case_type": case_type,
            "jurisdiction": jurisdiction,
            "deadlines": [d.__dict__ for d in deadlines],
            "total_deadlines": len(deadlines)
        }
        
    async def _get_filing_requirements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get requirements for specific filing type"""
        self.validate_params(params, ["court_id", "document_type"])
        
        court_id = params["court_id"]
        document_type = params["document_type"]
        
        # Check cache
        cache_key = self._generate_cache_key("get_filing_requirements", params)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Get adapter
        adapter = self.adapters.get(court_id)
        if not adapter:
            raise ValueError(f"Unsupported court: {court_id}")
            
        # Get requirements
        requirements = await adapter.get_filing_requirements(document_type)
        
        result = {
            "success": True,
            "court_id": court_id,
            "document_type": document_type,
            "requirements": requirements.__dict__ if requirements else None
        }
        
        # Cache with 1-week TTL
        self._cache_result(cache_key, result, 10080)
        
        return result
        
    async def _check_court_holidays(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check court holidays for date range"""
        self.validate_params(params, ["court_id", "start_date", "end_date"])
        
        court_id = params["court_id"]
        start_date = datetime.fromisoformat(params["start_date"])
        end_date = datetime.fromisoformat(params["end_date"])
        
        # Check cache
        cache_key = self._generate_cache_key("check_court_holidays", params)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Get adapter
        adapter = self.adapters.get(court_id)
        if not adapter:
            raise ValueError(f"Unsupported court: {court_id}")
            
        # Get holidays
        holidays = await adapter.get_court_holidays(start_date, end_date)
        
        result = {
            "success": True,
            "court_id": court_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "holidays": holidays
        }
        
        # Cache with 24-hour TTL
        self._cache_result(cache_key, result, 1440)
        
        return result
        
    async def warm_cache(self, court_ids: List[str] = None):
        """Pre-populate cache with common queries"""
        if not court_ids:
            court_ids = list(self.court_configs.keys())
            
        logger.info(f"Warming cache for courts: {court_ids}")
        
        # Common queries to cache
        today = datetime.utcnow()
        common_queries = [
            # Court calendars for next 30 days
            {
                "action": "get_calendar",
                "params": {
                    "start_date": today.isoformat(),
                    "end_date": (today + timedelta(days=30)).isoformat()
                }
            },
            # Local rules
            {
                "action": "get_local_rules",
                "params": {
                    "rule_category": "all"
                }
            },
            # Court holidays for next year
            {
                "action": "check_court_holidays",
                "params": {
                    "start_date": today.isoformat(),
                    "end_date": (today + timedelta(days=365)).isoformat()
                }
            }
        ]
        
        tasks = []
        for court_id in court_ids:
            for query in common_queries:
                params = query["params"].copy()
                params["court_id"] = court_id
                tasks.append(self.query(query["action"], params))
                
        # Execute all warming queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        logger.info(f"Cache warming complete: {success_count}/{len(tasks)} successful")