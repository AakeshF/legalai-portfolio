#!/usr/bin/env python3
"""
Migration to add jurisdiction rules for deadline calculations
"""

import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, Column, String, JSON, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class JurisdictionRule(Base):
    """Table to store jurisdiction-specific legal rules"""
    __tablename__ = "jurisdiction_rules"
    
    id = Column(Integer, primary_key=True)
    jurisdiction = Column(String, nullable=False)  # e.g., "KY", "OH"
    case_type = Column(String, nullable=False)  # e.g., "personal_injury"
    rule_name = Column(String, nullable=False)  # e.g., "statute_of_limitations"
    rule_data = Column(JSON, nullable=False)  # JSON with rule details
    citation = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Comprehensive jurisdiction rules
jurisdiction_rules = {
    "KY": {
        "personal_injury": {
            "statute_of_limitations": {
                "years": 1,
                "citation": "KRS 413.140(1)(a)",
                "is_jurisdictional": True,
                "can_be_extended": False,
                "description": "Actions for injury to person must be commenced within one year"
            },
            "discovery_deadline": {
                "days": 180,
                "from": "case_filed",
                "citation": "CR 26.02",
                "description": "Discovery must be completed within 180 days unless extended by court"
            },
            "expert_disclosure": {
                "days": 90,
                "before": "trial_date",
                "citation": "CR 26.02(4)",
                "description": "Expert witnesses must be disclosed 90 days before trial"
            },
            "motion_deadline": {
                "days": 30,
                "before": "trial_date",
                "citation": "Local Rule",
                "description": "Dispositive motions must be filed 30 days before trial"
            },
            "mediation_deadline": {
                "days": 60,
                "before": "trial_date",
                "citation": "Local Rule",
                "description": "Mediation must be completed 60 days before trial"
            }
        },
        "medical_malpractice": {
            "statute_of_limitations": {
                "years": 1,
                "citation": "KRS 413.140(1)(e)",
                "is_jurisdictional": True,
                "can_be_extended": False,
                "description": "Medical malpractice actions must be commenced within one year"
            },
            "certificate_of_merit": {
                "days": 90,
                "from": "filing",
                "citation": "KRS 411.167",
                "description": "Certificate of merit must be filed within 90 days"
            }
        },
        "criminal": {
            "speedy_trial": {
                "days": 180,
                "from": "arraignment",
                "citation": "KRS 500.110",
                "is_jurisdictional": True,
                "description": "Trial must commence within 180 days of arraignment"
            },
            "discovery_deadline": {
                "days": 30,
                "from": "arraignment",
                "citation": "RCr 7.24",
                "description": "Discovery requests must be made within 30 days"
            },
            "pretrial_motions": {
                "days": 45,
                "from": "arraignment",
                "citation": "RCr 8.18",
                "description": "Pretrial motions must be filed within 45 days"
            }
        },
        "family": {
            "divorce_waiting_period": {
                "days": 60,
                "from": "filing",
                "citation": "KRS 403.044",
                "is_mandatory": True,
                "description": "60-day waiting period before divorce can be finalized"
            },
            "response_time": {
                "days": 20,
                "from": "service",
                "citation": "CR 12.01",
                "description": "Response must be filed within 20 days of service"
            },
            "temporary_orders": {
                "days": 10,
                "from": "motion_filed",
                "citation": "FCRPP 4",
                "description": "Temporary order hearings within 10 days of motion"
            }
        },
        "contract": {
            "statute_of_limitations": {
                "years": 15,
                "citation": "KRS 413.090",
                "is_jurisdictional": True,
                "description": "Written contracts have 15-year limitation period"
            },
            "oral_contract_sol": {
                "years": 5,
                "citation": "KRS 413.120",
                "is_jurisdictional": True,
                "description": "Oral contracts have 5-year limitation period"
            }
        }
    },
    "OH": {
        "personal_injury": {
            "statute_of_limitations": {
                "years": 2,
                "citation": "ORC 2305.10",
                "is_jurisdictional": True,
                "can_be_extended": False,
                "description": "Personal injury actions must be filed within 2 years"
            },
            "discovery_deadline": {
                "days": 240,
                "from": "case_filed",
                "citation": "Civ.R. 26",
                "description": "Discovery period is 240 days from filing"
            },
            "expert_disclosure": {
                "days": 60,
                "before": "trial_date",
                "citation": "Civ.R. 26(B)(5)",
                "description": "Expert reports due 60 days before trial"
            },
            "witness_list": {
                "days": 30,
                "before": "trial_date",
                "citation": "Local Rule",
                "description": "Witness lists due 30 days before trial"
            }
        },
        "medical_malpractice": {
            "statute_of_limitations": {
                "years": 1,
                "citation": "ORC 2305.113",
                "is_jurisdictional": True,
                "description": "Medical malpractice claims must be filed within 1 year"
            },
            "affidavit_of_merit": {
                "with": "complaint",
                "citation": "Civ.R. 10(D)(2)",
                "is_mandatory": True,
                "description": "Affidavit of merit must accompany complaint"
            }
        },
        "criminal": {
            "speedy_trial": {
                "days": 270,
                "from": "arrest",
                "citation": "ORC 2945.71",
                "is_jurisdictional": True,
                "description": "Felony trials must commence within 270 days"
            },
            "misdemeanor_speedy_trial": {
                "days": 90,
                "from": "arrest",
                "citation": "ORC 2945.71",
                "is_jurisdictional": True,
                "description": "Misdemeanor trials must commence within 90 days"
            }
        },
        "contract": {
            "statute_of_limitations": {
                "years": 8,
                "citation": "ORC 2305.06",
                "is_jurisdictional": True,
                "description": "Written contracts have 8-year limitation period"
            },
            "oral_contract_sol": {
                "years": 6,
                "citation": "ORC 2305.07",
                "is_jurisdictional": True,
                "description": "Oral contracts have 6-year limitation period"
            },
            "response_time": {
                "days": 28,
                "from": "service",
                "citation": "Civ.R. 12(A)",
                "description": "Answer must be filed within 28 days of service"
            }
        },
        "employment": {
            "discrimination_filing": {
                "days": 180,
                "from": "incident",
                "citation": "ORC 4112.02",
                "is_jurisdictional": True,
                "description": "OCRC charge must be filed within 180 days"
            },
            "wage_claim": {
                "years": 2,
                "citation": "ORC 2305.11",
                "is_jurisdictional": True,
                "description": "Wage claims must be filed within 2 years"
            }
        }
    }
}

# Court-specific local rules
court_local_rules = {
    "hamilton_county_oh": {
        "motion_briefing": {
            "response_days": 21,
            "reply_days": 7,
            "citation": "Ham. Co. R. 6.01"
        },
        "page_limits": {
            "motion": 20,
            "response": 20,
            "reply": 10,
            "citation": "Ham. Co. R. 6.02"
        }
    },
    "campbell_county_ky": {
        "efiling_requirement": {
            "mandatory": True,
            "citation": "Campbell Cir. R. 3.01",
            "effective_date": "2023-01-01"
        }
    },
    "kenton_county_ky": {
        "motion_hearing": {
            "notice_days": 7,
            "citation": "Kenton Cir. R. 4.01"
        }
    }
}

def create_jurisdiction_rules_table():
    """Create the jurisdiction_rules table if it doesn't exist"""
    try:
        Base.metadata.create_all(bind=engine, tables=[JurisdictionRule.__table__])
        logger.info("Created jurisdiction_rules table successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        return False

def populate_jurisdiction_rules():
    """Populate the jurisdiction rules table"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Clear existing rules
        session.query(JurisdictionRule).delete()
        
        # Insert jurisdiction rules
        rules_added = 0
        for jurisdiction, case_types in jurisdiction_rules.items():
            for case_type, rules in case_types.items():
                for rule_name, rule_data in rules.items():
                    rule = JurisdictionRule(
                        jurisdiction=jurisdiction,
                        case_type=case_type,
                        rule_name=rule_name,
                        rule_data=rule_data,
                        citation=rule_data.get("citation")
                    )
                    session.add(rule)
                    rules_added += 1
                    
        session.commit()
        logger.info(f"Added {rules_added} jurisdiction rules")
        
        # Also save court-specific rules as a separate JSON file
        with open("court_local_rules.json", "w") as f:
            json.dump(court_local_rules, f, indent=2)
        logger.info("Saved court local rules to court_local_rules.json")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error populating rules: {str(e)}")
        return False
    finally:
        session.close()

def verify_migration():
    """Verify the migration was successful"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count rules by jurisdiction
        results = session.execute(
            text("SELECT jurisdiction, COUNT(*) as count FROM jurisdiction_rules GROUP BY jurisdiction")
        ).fetchall()
        
        logger.info("\nJurisdiction rule counts:")
        for jurisdiction, count in results:
            logger.info(f"  {jurisdiction}: {count} rules")
            
        # Sample some rules
        sample_rules = session.query(JurisdictionRule).limit(5).all()
        logger.info("\nSample rules:")
        for rule in sample_rules:
            logger.info(f"  {rule.jurisdiction} - {rule.case_type} - {rule.rule_name}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error verifying migration: {str(e)}")
        return False
    finally:
        session.close()

def main():
    """Run the migration"""
    logger.info("Starting jurisdiction rules migration...")
    
    # Create table
    if not create_jurisdiction_rules_table():
        logger.error("Failed to create table")
        return False
        
    # Populate rules
    if not populate_jurisdiction_rules():
        logger.error("Failed to populate rules")
        return False
        
    # Verify
    if not verify_migration():
        logger.error("Failed to verify migration")
        return False
        
    logger.info("\nMigration completed successfully!")
    logger.info("The court system MCP server can now use these rules for deadline calculations")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)