#!/usr/bin/env python3
"""
Example: Using the Court System MCP Server for case management
"""

import asyncio
from datetime import datetime, date
from services.mcp_servers.court_system_mcp import CourtSystemMCPServer
from services.matter_service import MatterService
from services.mcp_manager import MCPManager
from database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_court_system_integration():
    """Demonstrate Court System MCP Server integration"""
    
    # Initialize Court System MCP Server
    court_server = CourtSystemMCPServer()
    
    async with court_server:
        # 1. Show server capabilities
        logger.info("=== Court System MCP Server Capabilities ===")
        capabilities = court_server.get_capabilities()
        logger.info(f"Server: {capabilities['server_name']} v{capabilities['version']}")
        logger.info(f"Supported courts: {', '.join(capabilities['supported_courts'])}")
        logger.info(f"Available actions: {', '.join(capabilities['actions'].keys())}")
        
        # 2. Search for a case
        logger.info("\n=== Case Search Example ===")
        search_result = await court_server.query("search_case", {
            "court_id": "hamilton_county_oh",
            "case_number": "A2024001234"
        })
        
        if search_result["success"]:
            logger.info(f"Found {len(search_result['results'])} case(s)")
            for case in search_result["results"]:
                logger.info(f"  - {case['case_number']}: {case['case_name']} ({case['status']})")
        
        # 3. Get detailed case information
        logger.info("\n=== Case Details Example ===")
        case_info = await court_server.query("get_case_info", {
            "court_id": "hamilton_county_oh",
            "case_number": "A2024001234"
        })
        
        if case_info["success"] and case_info["case_info"]:
            info = case_info["case_info"]
            logger.info(f"Case: {info['case_name']}")
            logger.info(f"Judge: {info['judge']}")
            logger.info(f"Filed: {info['filing_date']}")
            logger.info(f"Parties: {len(info['parties'])}")
            
        # 4. Calculate deadlines for a personal injury case
        logger.info("\n=== Deadline Calculation Example ===")
        deadlines_result = await court_server.query("calculate_deadlines", {
            "trigger_date": "2024-01-15",
            "case_type": "personal_injury",
            "jurisdiction": {"state": "KY", "court_id": "campbell_county_ky"}
        })
        
        if deadlines_result["success"]:
            logger.info(f"Calculated {deadlines_result['total_deadlines']} deadlines:")
            for deadline in deadlines_result["deadlines"][:5]:  # Show first 5
                logger.info(f"  - {deadline['name']}: {deadline['due_date']} "
                          f"({'CRITICAL' if deadline['is_jurisdictional'] else 'Normal'})")
                if deadline.get('citation'):
                    logger.info(f"    Citation: {deadline['citation']}")
                    
        # 5. Get court calendar
        logger.info("\n=== Court Calendar Example ===")
        calendar = await court_server.query("get_calendar", {
            "court_id": "hamilton_county_oh",
            "start_date": "2024-03-01",
            "end_date": "2024-03-31"
        })
        
        if calendar["success"]:
            logger.info(f"Found {calendar['total_events']} court events in March 2024")
            for event in calendar["events"][:3]:  # Show first 3
                logger.info(f"  - {event['date']} {event['time']}: {event['event_type']} "
                          f"({event['case_name']}) - Courtroom {event['courtroom']}")
                
        # 6. Check filing requirements
        logger.info("\n=== Filing Requirements Example ===")
        requirements = await court_server.query("get_filing_requirements", {
            "court_id": "hamilton_county_oh",
            "document_type": "complaint"
        })
        
        if requirements["success"] and requirements["requirements"]:
            req = requirements["requirements"]
            logger.info(f"Filing a {req['document_type']}:")
            logger.info(f"  - Required copies: {req['required_copies']}")
            logger.info(f"  - Filing fee: ${req['filing_fee']:.2f}")
            logger.info(f"  - Service requirements: {', '.join(req['service_requirements'])}")
            
        # 7. Integration with Matter Service
        logger.info("\n=== Matter Service Integration Example ===")
        
        # Create a mock database session
        db = SessionLocal()
        mcp_manager = MCPManager()
        matter_service = MatterService(db, mcp_manager)
        
        # Example: Check for conflicts before creating a matter
        logger.info("Checking for conflicts of interest...")
        conflict_check = {
            "client_name": "John Smith",
            "opposing_parties": [
                {"name": "ABC Corporation", "type": "Defendant"},
                {"name": "Jane Doe", "type": "Co-Defendant"}
            ],
            "organization_id": "test-org-123"
        }
        
        # This would normally query the MCP server for conflict checking
        logger.info("  - Checking client database...")
        logger.info("  - Checking opposing parties...")
        logger.info("  - No conflicts found ✓")
        
        # 8. Cache warming for performance
        logger.info("\n=== Cache Warming Example ===")
        logger.info("Pre-populating cache for frequently accessed data...")
        await court_server.warm_cache(["hamilton_county_oh", "campbell_county_ky"])
        logger.info("Cache warming complete!")
        
        # 9. Demonstrate error handling
        logger.info("\n=== Error Handling Example ===")
        error_result = await court_server.query("search_case", {
            "court_id": "invalid_court",
            "case_number": "12345"
        })
        
        if not error_result["success"]:
            logger.info(f"Expected error: {error_result['error']}")
            
        # Close database
        db.close()

async def demo_deadline_warnings():
    """Demonstrate deadline warning system"""
    from services.mcp_servers.deadline_calculator import CourtDeadlineCalculator, Deadline, DeadlineType
    
    logger.info("\n=== Deadline Warning System ===")
    
    calculator = CourtDeadlineCalculator()
    
    # Create some sample deadlines
    today = date.today()
    deadlines = [
        Deadline(
            name="Statute of Limitations",
            due_date=today + timedelta(days=5),
            deadline_type=DeadlineType.STATUTE_OF_LIMITATIONS,
            description="Last day to file lawsuit",
            is_jurisdictional=True,
            warning_days=30,
            priority="critical"
        ),
        Deadline(
            name="Discovery Deadline",
            due_date=today + timedelta(days=15),
            deadline_type=DeadlineType.DISCOVERY,
            description="Complete all discovery",
            warning_days=14,
            priority="high"
        ),
        Deadline(
            name="Motion Filing",
            due_date=today - timedelta(days=2),
            deadline_type=DeadlineType.MOTION,
            description="File dispositive motions",
            warning_days=7,
            priority="normal"
        )
    ]
    
    # Get warnings
    warnings = calculator.get_deadline_warnings(deadlines, today)
    
    logger.info(f"Found {len(warnings)} deadline warnings:")
    for warning in warnings:
        if warning["status"] == "overdue":
            logger.warning(f"  ⚠️  OVERDUE: {warning['deadline']} "
                         f"({warning['days_overdue']} days overdue)")
        else:
            logger.info(f"  ⏰ WARNING: {warning['deadline']} "
                       f"({warning['days_remaining']} days remaining)")

async def demo_court_comparison():
    """Compare rules across jurisdictions"""
    logger.info("\n=== Jurisdiction Comparison ===")
    
    court_server = CourtSystemMCPServer()
    
    async with court_server:
        # Compare statute of limitations
        case_types = ["personal_injury", "contract"]
        states = ["KY", "OH"]
        
        for case_type in case_types:
            logger.info(f"\n{case_type.replace('_', ' ').title()} - Statute of Limitations:")
            
            for state in states:
                result = await court_server.query("calculate_deadlines", {
                    "trigger_date": "2024-01-15",
                    "case_type": case_type,
                    "jurisdiction": {"state": state}
                })
                
                if result["success"]:
                    sol = next((d for d in result["deadlines"] 
                              if "Statute Of Limitations" in d["name"]), None)
                    if sol:
                        logger.info(f"  {state}: {sol['calculation_basis']} - {sol['citation']}")

if __name__ == "__main__":
    # Run demonstrations
    asyncio.run(demo_court_system_integration())
    asyncio.run(demo_deadline_warnings())
    asyncio.run(demo_court_comparison())