# services/mcp_servers/deadline_calculator.py - Court deadline calculation engine

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class DeadlineType(Enum):
    """Types of legal deadlines"""
    STATUTE_OF_LIMITATIONS = "statute_of_limitations"
    DISCOVERY = "discovery"
    MOTION = "motion"
    RESPONSE = "response"
    APPEAL = "appeal"
    SERVICE = "service"
    EXPERT_DISCLOSURE = "expert_disclosure"
    TRIAL = "trial"
    PRETRIAL = "pretrial"

@dataclass
class Deadline:
    """Represents a calculated deadline"""
    name: str
    due_date: date
    deadline_type: DeadlineType
    description: str
    citation: Optional[str] = None
    is_jurisdictional: bool = False
    can_be_extended: bool = True
    calculation_basis: Optional[str] = None
    warning_days: int = 7
    priority: str = "normal"  # low, normal, high, critical

class CourtDeadlineCalculator:
    """Calculate deadlines based on jurisdiction rules and court holidays"""
    
    def __init__(self):
        # Jurisdiction-specific rules
        self.jurisdiction_rules = {
            "KY": {
                "personal_injury": {
                    "statute_of_limitations": {
                        "years": 1,
                        "citation": "KRS 413.140(1)(a)",
                        "is_jurisdictional": True,
                        "can_be_extended": False
                    },
                    "discovery_deadline": {
                        "days": 180,
                        "from": "case_filed",
                        "citation": "CR 26.02"
                    },
                    "expert_disclosure": {
                        "days": 90,
                        "before": "trial_date",
                        "citation": "CR 26.02(4)"
                    },
                    "motion_deadline": {
                        "days": 30,
                        "before": "trial_date",
                        "citation": "Local Rule"
                    }
                },
                "criminal": {
                    "speedy_trial": {
                        "days": 180,
                        "from": "arraignment",
                        "citation": "KRS 500.110",
                        "is_jurisdictional": True
                    },
                    "discovery_deadline": {
                        "days": 30,
                        "from": "arraignment",
                        "citation": "RCr 7.24"
                    }
                },
                "family": {
                    "divorce_waiting_period": {
                        "days": 60,
                        "from": "filing",
                        "citation": "KRS 403.044"
                    },
                    "response_time": {
                        "days": 20,
                        "from": "service",
                        "citation": "CR 12.01"
                    }
                }
            },
            "OH": {
                "personal_injury": {
                    "statute_of_limitations": {
                        "years": 2,
                        "citation": "ORC 2305.10",
                        "is_jurisdictional": True,
                        "can_be_extended": False
                    },
                    "discovery_deadline": {
                        "days": 240,
                        "from": "case_filed",
                        "citation": "Civ.R. 26"
                    },
                    "expert_disclosure": {
                        "days": 60,
                        "before": "trial_date",
                        "citation": "Civ.R. 26(B)(5)"
                    }
                },
                "criminal": {
                    "speedy_trial": {
                        "days": 270,  # For felonies
                        "from": "arrest",
                        "citation": "ORC 2945.71",
                        "is_jurisdictional": True
                    }
                },
                "contract": {
                    "statute_of_limitations": {
                        "years": 8,  # Written contracts
                        "citation": "ORC 2305.06",
                        "is_jurisdictional": True
                    },
                    "response_time": {
                        "days": 28,
                        "from": "service",
                        "citation": "Civ.R. 12(A)"
                    }
                }
            }
        }
        
        # Federal rules (if applicable)
        self.federal_rules = {
            "civil": {
                "response_time": {
                    "days": 21,
                    "from": "service",
                    "citation": "FRCP 12(a)(1)(A)"
                },
                "discovery_deadline": {
                    "days": 120,
                    "from": "scheduling_conference",
                    "citation": "FRCP 26(f)"
                }
            }
        }
        
    def calculate_all_deadlines(self, trigger_date: datetime, case_type: str, 
                               jurisdiction: Dict[str, Any], 
                               court_holidays: List[Dict[str, Any]] = None) -> List[Deadline]:
        """Calculate all applicable deadlines for a case"""
        deadlines = []
        court_holidays = court_holidays or []
        
        # Extract jurisdiction info
        state = jurisdiction.get("state", "").upper()
        is_federal = jurisdiction.get("is_federal", False)
        
        # Get applicable rules
        if is_federal:
            rules = self.federal_rules.get("civil", {})
        else:
            state_rules = self.jurisdiction_rules.get(state, {})
            rules = state_rules.get(case_type, {})
            
        if not rules:
            logger.warning(f"No rules found for {state} - {case_type}")
            return deadlines
            
        # Calculate each deadline
        for deadline_name, rule in rules.items():
            deadline = self._calculate_single_deadline(
                deadline_name, 
                rule, 
                trigger_date, 
                court_holidays
            )
            if deadline:
                deadlines.append(deadline)
                
        # Sort by due date and priority
        deadlines.sort(key=lambda d: (d.due_date, self._priority_order(d.priority)))
        
        return deadlines
        
    def _calculate_single_deadline(self, name: str, rule: Dict[str, Any], 
                                  trigger_date: datetime, 
                                  court_holidays: List[Dict[str, Any]]) -> Optional[Deadline]:
        """Calculate a single deadline based on rule"""
        try:
            # Determine calculation type
            if "years" in rule:
                calculated_date = trigger_date + timedelta(days=365 * rule["years"])
            elif "days" in rule:
                if "from" in rule:
                    # Forward calculation from trigger
                    calculated_date = trigger_date + timedelta(days=rule["days"])
                elif "before" in rule:
                    # Backward calculation (needs trial date or other reference)
                    # For now, skip these as they need additional context
                    return None
                else:
                    calculated_date = trigger_date + timedelta(days=rule["days"])
            else:
                return None
                
            # Adjust for weekends and holidays
            final_date = self._adjust_for_court_days(
                calculated_date.date(), 
                court_holidays, 
                rule.get("exclude_weekends", True)
            )
            
            # Determine deadline type
            deadline_type = self._determine_deadline_type(name)
            
            # Set priority based on jurisdictional nature
            priority = "critical" if rule.get("is_jurisdictional", False) else "normal"
            
            return Deadline(
                name=self._format_deadline_name(name),
                due_date=final_date,
                deadline_type=deadline_type,
                description=self._generate_description(name, rule),
                citation=rule.get("citation"),
                is_jurisdictional=rule.get("is_jurisdictional", False),
                can_be_extended=rule.get("can_be_extended", True),
                calculation_basis=f"{rule.get('days', rule.get('years'))} days from {rule.get('from', 'trigger')}",
                priority=priority
            )
            
        except Exception as e:
            logger.error(f"Error calculating deadline {name}: {str(e)}")
            return None
            
    def _adjust_for_court_days(self, calculated_date: date, 
                              court_holidays: List[Dict[str, Any]], 
                              exclude_weekends: bool = True) -> date:
        """Adjust date for weekends and court holidays"""
        adjusted_date = calculated_date
        
        # Convert holiday list to dates
        holiday_dates = set()
        for holiday in court_holidays:
            try:
                holiday_date = datetime.strptime(holiday["date"], "%Y-%m-%d").date()
                holiday_dates.add(holiday_date)
            except:
                pass
                
        # Keep moving forward until we find a court day
        while True:
            # Check if it's a weekend
            if exclude_weekends and adjusted_date.weekday() in [5, 6]:  # Saturday, Sunday
                adjusted_date += timedelta(days=1)
                continue
                
            # Check if it's a holiday
            if adjusted_date in holiday_dates:
                adjusted_date += timedelta(days=1)
                continue
                
            # Valid court day found
            break
            
        return adjusted_date
        
    def _determine_deadline_type(self, name: str) -> DeadlineType:
        """Determine the type of deadline from its name"""
        name_lower = name.lower()
        
        if "statute_of_limitations" in name_lower:
            return DeadlineType.STATUTE_OF_LIMITATIONS
        elif "discovery" in name_lower:
            return DeadlineType.DISCOVERY
        elif "motion" in name_lower:
            return DeadlineType.MOTION
        elif "response" in name_lower:
            return DeadlineType.RESPONSE
        elif "appeal" in name_lower:
            return DeadlineType.APPEAL
        elif "service" in name_lower:
            return DeadlineType.SERVICE
        elif "expert" in name_lower:
            return DeadlineType.EXPERT_DISCLOSURE
        elif "trial" in name_lower:
            return DeadlineType.TRIAL
        elif "pretrial" in name_lower:
            return DeadlineType.PRETRIAL
        else:
            return DeadlineType.MOTION  # Default
            
    def _format_deadline_name(self, name: str) -> str:
        """Format deadline name for display"""
        # Convert snake_case to Title Case
        words = name.split("_")
        return " ".join(word.capitalize() for word in words)
        
    def _generate_description(self, name: str, rule: Dict[str, Any]) -> str:
        """Generate a description for the deadline"""
        if "statute_of_limitations" in name:
            return f"Last day to file lawsuit. This deadline cannot be extended."
        elif "discovery_deadline" in name:
            return f"Deadline to complete all discovery activities."
        elif "response_time" in name:
            return f"Deadline to file response to complaint/petition."
        elif "expert_disclosure" in name:
            return f"Deadline to disclose expert witnesses and reports."
        elif "speedy_trial" in name:
            return f"Constitutional deadline for trial to commence."
        else:
            return f"Legal deadline per {rule.get('citation', 'court rules')}"
            
    def _priority_order(self, priority: str) -> int:
        """Convert priority to numeric for sorting"""
        priority_map = {
            "critical": 0,
            "high": 1,
            "normal": 2,
            "low": 3
        }
        return priority_map.get(priority, 2)
        
    def calculate_deadline_from_event(self, event_date: datetime, event_type: str,
                                     case_type: str, jurisdiction: Dict[str, Any],
                                     days_offset: int = 0) -> Optional[date]:
        """Calculate a specific deadline from an event"""
        # This is useful for calculating deadlines triggered by specific events
        # like service of process, filing of motion, etc.
        
        calculated_date = event_date + timedelta(days=days_offset)
        
        # Get court holidays for adjustment
        court_holidays = []  # Would be fetched from court system
        
        return self._adjust_for_court_days(
            calculated_date.date(),
            court_holidays,
            exclude_weekends=True
        )
        
    def get_deadline_warnings(self, deadlines: List[Deadline], 
                             current_date: date = None) -> List[Dict[str, Any]]:
        """Get warnings for upcoming deadlines"""
        if not current_date:
            current_date = date.today()
            
        warnings = []
        
        for deadline in deadlines:
            days_until = (deadline.due_date - current_date).days
            
            if days_until < 0:
                # Overdue
                warnings.append({
                    "deadline": deadline.name,
                    "due_date": deadline.due_date.isoformat(),
                    "status": "overdue",
                    "days_overdue": abs(days_until),
                    "priority": "critical" if deadline.is_jurisdictional else "high"
                })
            elif days_until <= deadline.warning_days:
                # Within warning period
                warnings.append({
                    "deadline": deadline.name,
                    "due_date": deadline.due_date.isoformat(),
                    "status": "warning",
                    "days_remaining": days_until,
                    "priority": deadline.priority
                })
                
        return warnings