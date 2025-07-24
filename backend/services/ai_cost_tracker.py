# services/ai_cost_tracker.py - AI usage cost tracking and alerts
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from models import Organization, AIAuditLog
from email_service import EmailService

logger = logging.getLogger(__name__)

class AICostTracker:
    """Track AI usage costs and enforce budget limits"""
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        
        # Cost per 1M tokens (approximate)
        self.provider_costs = {
            "openai": {"input": 3.00, "output": 15.00},   # GPT-4 Turbo
            "claude": {"input": 3.00, "output": 15.00},  # Claude 3.5 Sonnet
            "gemini": {"input": 1.25, "output": 5.00},    # Gemini 1.5 Pro
            "local": {"input": 0.0, "output": 0.0}         # No cost for local
        }
    
    async def check_budget_before_request(
        self,
        organization_id: str,
        provider: str,
        estimated_tokens: int
    ) -> Dict[str, Any]:
        """Check if organization has budget for request"""
        
        org = self.db.query(Organization).filter_by(id=organization_id).first()
        if not org:
            return {"allowed": True, "reason": "Organization not found"}
        
        # No budget limit set
        if not org.ai_monthly_budget:
            return {"allowed": True, "reason": "No budget limit"}
        
        # Get current month cost
        current_cost = await self.get_current_month_cost(organization_id)
        
        # Estimate request cost
        provider_rates = self.provider_costs.get(provider, self.provider_costs["openai"])
        # Assume 50/50 input/output for estimation
        avg_rate = (provider_rates["input"] + provider_rates["output"]) / 2
        estimated_cost = (estimated_tokens / 1_000_000) * avg_rate
        
        projected_cost = current_cost + estimated_cost
        
        # Check if over budget
        if projected_cost > org.ai_monthly_budget:
            return {
                "allowed": False,
                "reason": "Monthly AI budget exceeded",
                "current_cost": round(current_cost, 2),
                "budget": org.ai_monthly_budget,
                "projected_cost": round(projected_cost, 2)
            }
        
        # Check if approaching limit
        if projected_cost > (org.ai_monthly_budget * org.ai_budget_alert_threshold):
            # Send alert but allow request
            asyncio.create_task(
                self._send_budget_alert(org, current_cost, projected_cost)
            )
        
        return {
            "allowed": True,
            "current_cost": round(current_cost, 2),
            "budget": org.ai_monthly_budget,
            "usage_percentage": round((current_cost / org.ai_monthly_budget) * 100, 1)
        }
    
    async def record_usage_cost(
        self,
        organization_id: str,
        provider: str,
        tokens_used: int,
        request_id: str
    ) -> float:
        """Record actual cost after request completion"""
        
        # Calculate actual cost
        provider_rates = self.provider_costs.get(provider, self.provider_costs["openai"])
        # Rough 30/70 split for input/output
        input_tokens = int(tokens_used * 0.3)
        output_tokens = int(tokens_used * 0.7)
        
        cost = (
            (input_tokens / 1_000_000) * provider_rates["input"] +
            (output_tokens / 1_000_000) * provider_rates["output"]
        )
        
        # Update organization's running total
        org = self.db.query(Organization).filter_by(id=organization_id).first()
        if org:
            # Reset monthly cost if new month
            if org.ai_budget_period_start:
                if org.ai_budget_period_start.month != datetime.utcnow().month:
                    org.ai_current_month_cost = 0
                    org.ai_budget_period_start = datetime.utcnow()
            else:
                org.ai_budget_period_start = datetime.utcnow()
            
            org.ai_current_month_cost += cost
            self.db.commit()
            
            # Check if alert needed
            if org.ai_monthly_budget and org.ai_cost_alerts_enabled:
                usage_percentage = (org.ai_current_month_cost / org.ai_monthly_budget) * 100
                
                # Send alerts at 80%, 90%, 95%, 100%
                alert_thresholds = [80, 90, 95, 100]
                for threshold in alert_thresholds:
                    if usage_percentage >= threshold and usage_percentage < threshold + 5:
                        asyncio.create_task(
                            self._send_usage_alert(org, usage_percentage, threshold)
                        )
        
        return cost
    
    async def get_current_month_cost(self, organization_id: str) -> float:
        """Get total AI costs for current month"""
        
        # First check org's cached value
        org = self.db.query(Organization).filter_by(id=organization_id).first()
        if org and org.ai_budget_period_start:
            if org.ai_budget_period_start.month == datetime.utcnow().month:
                return org.ai_current_month_cost
        
        # Otherwise calculate from audit logs
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        
        total_cost = self.db.query(func.sum(AIAuditLog.estimated_cost)).filter(
            AIAuditLog.organization_id == organization_id,
            AIAuditLog.request_timestamp >= start_of_month
        ).scalar() or 0
        
        return total_cost
    
    async def get_cost_breakdown(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown by provider"""
        
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Query costs by provider
        provider_costs = self.db.query(
            AIAuditLog.provider_used,
            func.sum(AIAuditLog.estimated_cost).label('total_cost'),
            func.count(AIAuditLog.id).label('request_count'),
            func.sum(AIAuditLog.tokens_used).label('total_tokens')
        ).filter(
            AIAuditLog.organization_id == organization_id,
            AIAuditLog.request_timestamp >= start_date,
            AIAuditLog.request_timestamp <= end_date
        ).group_by(AIAuditLog.provider_used).all()
        
        breakdown = {}
        total_cost = 0
        
        for provider, cost, count, tokens in provider_costs:
            breakdown[provider] = {
                "cost": round(cost or 0, 2),
                "requests": count,
                "tokens": tokens or 0,
                "avg_cost_per_request": round((cost or 0) / count, 4) if count > 0 else 0
            }
            total_cost += cost or 0
        
        # Get budget info
        org = self.db.query(Organization).filter_by(id=organization_id).first()
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_cost": round(total_cost, 2),
            "budget": org.ai_monthly_budget if org else None,
            "usage_percentage": round((total_cost / org.ai_monthly_budget) * 100, 1) if org and org.ai_monthly_budget else None,
            "by_provider": breakdown,
            "alerts_enabled": org.ai_cost_alerts_enabled if org else False
        }
    
    async def get_cost_trends(
        self,
        organization_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily cost trends"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        daily_costs = self.db.query(
            func.date(AIAuditLog.request_timestamp).label('date'),
            func.sum(AIAuditLog.estimated_cost).label('cost'),
            func.count(AIAuditLog.id).label('requests')
        ).filter(
            AIAuditLog.organization_id == organization_id,
            AIAuditLog.request_timestamp >= start_date
        ).group_by(func.date(AIAuditLog.request_timestamp)).all()
        
        return [
            {
                "date": date.isoformat() if date else None,
                "cost": round(cost or 0, 2),
                "requests": requests
            }
            for date, cost, requests in daily_costs
        ]
    
    async def _send_budget_alert(
        self,
        org: Organization,
        current_cost: float,
        projected_cost: float
    ):
        """Send budget alert email"""
        
        if not org.billing_email:
            return
        
        subject = f"AI Budget Alert - {org.name}"
        
        body = f"""
        <h2>AI Usage Budget Alert</h2>
        
        <p>Your organization is approaching its monthly AI usage budget.</p>
        
        <ul>
            <li>Current Month Cost: ${current_cost:.2f}</li>
            <li>Monthly Budget: ${org.ai_monthly_budget:.2f}</li>
            <li>Usage: {(current_cost / org.ai_monthly_budget * 100):.1f}%</li>
            <li>Projected with current request: ${projected_cost:.2f}</li>
        </ul>
        
        <p>Consider reviewing your AI usage or increasing your budget limit.</p>
        
        <p>To manage your budget settings, visit the AI Management section in your dashboard.</p>
        """
        
        try:
            await self.email_service.send_email(
                to=org.billing_email,
                subject=subject,
                body=body,
                html=True
            )
            logger.info(f"Budget alert sent to {org.billing_email}")
        except Exception as e:
            logger.error(f"Failed to send budget alert: {e}")
    
    async def _send_usage_alert(
        self,
        org: Organization,
        usage_percentage: float,
        threshold: int
    ):
        """Send usage threshold alert"""
        
        if not org.billing_email:
            return
        
        subject = f"AI Usage Alert - {threshold}% of Monthly Budget"
        
        body = f"""
        <h2>AI Usage Threshold Reached</h2>
        
        <p>Your organization has reached {threshold}% of its monthly AI budget.</p>
        
        <ul>
            <li>Current Usage: {usage_percentage:.1f}%</li>
            <li>Current Cost: ${org.ai_current_month_cost:.2f}</li>
            <li>Monthly Budget: ${org.ai_monthly_budget:.2f}</li>
            <li>Remaining Budget: ${org.ai_monthly_budget - org.ai_current_month_cost:.2f}</li>
        </ul>
        
        <p>At current usage rates, you may exceed your budget before month end.</p>
        
        <p>Options:</p>
        <ul>
            <li>Switch to lower-cost AI providers</li>
            <li>Enable local AI processing for sensitive documents</li>
            <li>Increase your monthly budget limit</li>
        </ul>
        """
        
        try:
            await self.email_service.send_email(
                to=org.billing_email,
                subject=subject,
                body=body,
                html=True
            )
            logger.info(f"Usage alert ({threshold}%) sent to {org.billing_email}")
        except Exception as e:
            logger.error(f"Failed to send usage alert: {e}")
    
    def update_budget_settings(
        self,
        organization_id: str,
        monthly_budget: Optional[float] = None,
        alert_threshold: Optional[float] = None,
        alerts_enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update organization budget settings"""
        
        org = self.db.query(Organization).filter_by(id=organization_id).first()
        if not org:
            raise ValueError("Organization not found")
        
        if monthly_budget is not None:
            org.ai_monthly_budget = monthly_budget
        
        if alert_threshold is not None:
            org.ai_budget_alert_threshold = alert_threshold
        
        if alerts_enabled is not None:
            org.ai_cost_alerts_enabled = alerts_enabled
        
        self.db.commit()
        
        return {
            "monthly_budget": org.ai_monthly_budget,
            "alert_threshold": org.ai_budget_alert_threshold,
            "alerts_enabled": org.ai_cost_alerts_enabled,
            "current_usage": org.ai_current_month_cost,
            "usage_percentage": round((org.ai_current_month_cost / org.ai_monthly_budget) * 100, 1) if org.ai_monthly_budget else 0
        }