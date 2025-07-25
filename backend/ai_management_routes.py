# ai_management_routes.py - API routes for AI provider management, consent, and audit
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db
from auth_middleware import get_current_user, get_current_organization
from services.api_key_manager import APIKeyManager, APIKeyStore
from services.consent_manager import ConsentManager, ConsentType, ConsentScope
from services.ai_audit_trail import AIAuditTrail
from services.multi_provider_ai_service import MultiProviderAIService, AIProvider
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Management"])


# Pydantic models for requests/responses
class APIKeyUpdate(BaseModel):
    provider: str
    api_key: str


class ConsentRequest(BaseModel):
    consent_type: str
    granted: bool
    scope: str = "organization"
    purpose: Optional[str] = None
    providers_allowed: Optional[List[str]] = None
    expires_in_days: Optional[int] = None


class OrganizationPreferences(BaseModel):
    require_explicit_consent: Optional[bool] = None
    default_ai_provider: Optional[str] = None
    allowed_providers: Optional[List[str]] = None
    allow_cloud_processing: Optional[bool] = None
    require_local_only: Optional[bool] = None
    data_retention_days: Optional[int] = None


# AI Provider Management Routes
@router.get("/providers")
async def get_available_providers(
    current_user=Depends(get_current_user), org=Depends(get_current_organization)
):
    """Get list of available AI providers and their status"""
    try:
        service = MultiProviderAIService()
        providers = service.get_available_providers()

        # Add API key status from secure storage
        db = next(get_db())
        key_manager = APIKeyManager(db)
        key_status = key_manager.get_provider_status(org.id)

        # Merge provider info with key status
        for provider in providers:
            provider_type = provider["type"]
            if provider_type in key_status:
                provider["key_configured"] = key_status[provider_type]["configured"]
                provider["key_source"] = key_status[provider_type].get(
                    "source", "database"
                )
                provider["validation_status"] = key_status[provider_type].get(
                    "validation_status"
                )

        return {
            "providers": providers,
            "default_provider": service.default_provider.value,
            "fallback_order": [p.value for p in service.fallback_order],
        }

    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/keys")
async def update_api_key(
    key_update: APIKeyUpdate,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Securely store or update an API key for a provider"""
    try:
        key_manager = APIKeyManager(db)

        # Store encrypted key
        result = key_manager.store_api_key(
            organization_id=org.id,
            provider=key_update.provider,
            api_key=key_update.api_key,
            user_id=current_user.id,
        )

        # Validate the key
        validation = key_manager.validate_api_key(org.id, key_update.provider)
        result["validation"] = validation

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/providers/keys/{provider}")
async def revoke_api_key(
    provider: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Revoke an API key for a provider"""
    try:
        key_manager = APIKeyManager(db)
        success = key_manager.revoke_api_key(org.id, provider)

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": f"API key for {provider} revoked successfully"}

    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/keys")
async def list_api_keys(
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """List all configured API keys (without exposing the actual keys)"""
    try:
        key_manager = APIKeyManager(db)
        keys = key_manager.list_api_keys(org.id)
        return {"keys": keys}

    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/keys/validate-all")
async def validate_all_api_keys(
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Validate all configured API keys"""
    try:
        key_manager = APIKeyManager(db)
        ai_service = MultiProviderAIService()

        results = {}
        providers = ["claude", "openai", "gemini"]

        for provider in providers:
            # First check if key exists
            api_key = key_manager.get_api_key(org.id, provider)
            if not api_key:
                results[provider] = {
                    "status": "not_configured",
                    "valid": False,
                    "error": "No API key configured",
                }
                continue

            # Test the provider with a minimal request
            try:
                test_messages = [
                    {"role": "user", "content": "Say 'test successful' in 3 words"}
                ]

                # Temporarily set the API key
                import os

                env_map = {
                    "claude": "ANTHROPIC_API_KEY",
                    "openai": "OPENAI_API_KEY",
                    "gemini": "GOOGLE_API_KEY",
                }
                old_key = os.environ.get(env_map[provider])
                os.environ[env_map[provider]] = api_key

                # Test the provider
                provider_enum = AIProvider[provider.upper()]
                if provider == "claude":
                    provider_enum = AIProvider.CLAUDE
                elif provider == "openai":
                    provider_enum = AIProvider.OPENAI

                response, _ = await ai_service.process_with_provider(
                    provider_enum, test_messages, max_tokens=10
                )

                # Restore old key
                if old_key:
                    os.environ[env_map[provider]] = old_key
                else:
                    os.environ.pop(env_map[provider], None)

                # Update validation status
                key_record = (
                    db.query(APIKeyStore)
                    .filter_by(
                        organization_id=org.id, provider=provider, is_active=True
                    )
                    .first()
                )

                if key_record:
                    key_record.last_validated = datetime.utcnow()
                    key_record.validation_status = "valid"
                    db.commit()

                results[provider] = {
                    "status": "valid",
                    "valid": True,
                    "validated_at": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                results[provider] = {
                    "status": "invalid",
                    "valid": False,
                    "error": str(e),
                }

                # Update validation status
                key_record = (
                    db.query(APIKeyStore)
                    .filter_by(
                        organization_id=org.id, provider=provider, is_active=True
                    )
                    .first()
                )

                if key_record:
                    key_record.last_validated = datetime.utcnow()
                    key_record.validation_status = "invalid"
                    db.commit()

        return {
            "validation_results": results,
            "validated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error validating API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Consent Management Routes
@router.post("/consent")
async def record_consent(
    consent: ConsentRequest,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Record consent for AI processing"""
    try:
        consent_manager = ConsentManager(db)

        # Map string to enum
        consent_type = ConsentType[consent.consent_type.upper()]
        consent_scope = ConsentScope[consent.scope.upper()]

        record = consent_manager.record_consent(
            organization_id=org.id,
            consent_type=consent_type,
            granted=consent.granted,
            user_id=current_user.id,
            scope=consent_scope,
            purpose=consent.purpose,
            providers_allowed=consent.providers_allowed,
            expires_in_days=consent.expires_in_days,
        )

        return {
            "consent_id": record.id,
            "consent_type": record.consent_type.value,
            "granted": record.granted,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        }

    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid consent type or scope")
    except Exception as e:
        logger.error(f"Error recording consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent/check")
async def check_consent(
    consent_type: str,
    provider: Optional[str] = None,
    document_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Check if consent is granted for a specific AI action"""
    try:
        consent_manager = ConsentManager(db)

        # Map string to enum
        consent_type_enum = ConsentType[consent_type.upper()]

        result = consent_manager.check_consent(
            organization_id=org.id,
            consent_type=consent_type_enum,
            user_id=current_user.id,
            document_id=document_id,
            provider=provider,
        )

        return result

    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid consent type")
    except Exception as e:
        logger.error(f"Error checking consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent/history")
async def get_consent_history(
    include_revoked: bool = False,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get consent history for the current user"""
    try:
        consent_manager = ConsentManager(db)
        history = consent_manager.get_consent_history(
            organization_id=org.id,
            user_id=current_user.id,
            include_revoked=include_revoked,
        )

        return {"consent_history": history}

    except Exception as e:
        logger.error(f"Error getting consent history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/consent/preferences")
async def update_organization_preferences(
    preferences: OrganizationPreferences,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Update organization-wide consent preferences"""
    try:
        consent_manager = ConsentManager(db)

        # Convert to dict and remove None values
        pref_dict = {k: v for k, v in preferences.dict().items() if v is not None}

        updated = consent_manager.set_organization_preferences(org.id, pref_dict)

        return {
            "message": "Preferences updated successfully",
            "updated_at": updated.updated_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent/preferences")
async def get_organization_preferences(
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get organization consent preferences"""
    try:
        consent_manager = ConsentManager(db)
        preferences = consent_manager.get_organization_preferences(org.id)

        if not preferences:
            return {"preferences": None, "using_defaults": True}

        return {"preferences": preferences, "using_defaults": False}

    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Audit Trail Routes
@router.get("/audit/{request_id}")
async def get_audit_log(
    request_id: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get a specific AI audit log by request ID"""
    try:
        audit_trail = AIAuditTrail(db)
        log = audit_trail.get_audit_log(request_id)

        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")

        # Verify organization access
        if log["organization_id"] != org.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return log

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit")
async def search_audit_logs(
    provider: Optional[str] = None,
    request_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Search AI audit logs with filters"""
    try:
        audit_trail = AIAuditTrail(db)
        logs = audit_trail.search_audit_logs(
            organization_id=org.id,
            user_id=current_user.id,
            provider=provider,
            request_type=request_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return {"logs": logs, "count": len(logs), "limit": limit}

    except Exception as e:
        logger.error(f"Error searching audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/analytics")
async def get_ai_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get AI usage analytics for the organization"""
    try:
        audit_trail = AIAuditTrail(db)
        analytics = audit_trail.get_usage_analytics(
            organization_id=org.id, start_date=start_date, end_date=end_date
        )

        return analytics

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/export")
async def export_audit_logs(
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Export audit logs for compliance reporting"""
    try:
        audit_trail = AIAuditTrail(db)
        export_data = audit_trail.export_audit_logs(
            organization_id=org.id,
            format=format,
            start_date=start_date,
            end_date=end_date,
        )

        # Set appropriate content type
        content_type = "application/json" if format == "json" else "text/csv"
        filename = f"ai_audit_{org.id}_{datetime.utcnow().strftime('%Y%m%d')}.{format}"

        from fastapi.responses import Response

        return Response(
            content=export_data,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Error exporting audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/report")
async def get_compliance_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Generate AI compliance report including consent and audit data"""
    try:
        consent_manager = ConsentManager(db)
        audit_trail = AIAuditTrail(db)

        # Get consent compliance
        consent_report = consent_manager.get_compliance_report(
            organization_id=org.id, start_date=start_date, end_date=end_date
        )

        # Get usage analytics
        usage_analytics = audit_trail.get_usage_analytics(
            organization_id=org.id, start_date=start_date, end_date=end_date
        )

        return {
            "organization_id": org.id,
            "report_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "consent_compliance": consent_report,
            "ai_usage": usage_analytics,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Provider Health Monitoring Routes
@router.post("/providers/health-check")
async def check_provider_health(
    provider: Optional[str] = None,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Check health status of AI providers"""
    try:
        from services.provider_health_monitor import ProviderHealthMonitor

        monitor = ProviderHealthMonitor(db)
        key_manager = APIKeyManager(db)

        if provider:
            # Check specific provider
            api_key = key_manager.get_api_key(org.id, provider)
            result = await monitor.check_provider_health(provider, api_key)
            return result
        else:
            # Check all providers
            api_keys = {}
            for p in ["claude", "openai", "gemini"]:
                api_keys[p] = key_manager.get_api_key(org.id, p)

            results = await monitor.check_all_providers(api_keys)
            return {"providers": results, "checked_at": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Error checking provider health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/health-status")
async def get_provider_health_status(
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get current health status of all providers"""
    try:
        from services.provider_health_monitor import ProviderHealthMonitor

        monitor = ProviderHealthMonitor(db)
        status = monitor.get_all_provider_status()

        return {"providers": status, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider}/statistics")
async def get_provider_statistics(
    provider: str,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 7 days
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get provider statistics over time period"""
    try:
        from services.provider_health_monitor import ProviderHealthMonitor

        monitor = ProviderHealthMonitor(db)
        stats = monitor.get_provider_statistics(provider, hours)

        return stats

    except Exception as e:
        logger.error(f"Error getting provider statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cost Management Routes
@router.get("/costs/current-month")
async def get_current_month_costs(
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get current month AI costs"""
    try:
        from services.ai_cost_tracker import AICostTracker

        tracker = AICostTracker(db)
        breakdown = await tracker.get_cost_breakdown(org.id)

        return breakdown

    except Exception as e:
        logger.error(f"Error getting costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/trends")
async def get_cost_trends(
    days: int = Query(30, ge=7, le=90),
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get cost trends over time"""
    try:
        from services.ai_cost_tracker import AICostTracker

        tracker = AICostTracker(db)
        trends = await tracker.get_cost_trends(org.id, days)

        return {"trends": trends, "period_days": days}

    except Exception as e:
        logger.error(f"Error getting cost trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BudgetUpdate(BaseModel):
    monthly_budget: Optional[float] = None
    alert_threshold: Optional[float] = None
    alerts_enabled: Optional[bool] = None


@router.put("/costs/budget")
async def update_budget_settings(
    budget: BudgetUpdate,
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Update organization budget settings"""
    try:
        from services.ai_cost_tracker import AICostTracker

        tracker = AICostTracker(db)
        result = tracker.update_budget_settings(
            org.id,
            monthly_budget=budget.monthly_budget,
            alert_threshold=budget.alert_threshold,
            alerts_enabled=budget.alerts_enabled,
        )

        return result

    except Exception as e:
        logger.error(f"Error updating budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/costs/check-budget")
async def check_budget_availability(
    provider: str = Body(...),
    estimated_tokens: int = Body(...),
    current_user=Depends(get_current_user),
    org=Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Check if budget allows for a request"""
    try:
        from services.ai_cost_tracker import AICostTracker

        tracker = AICostTracker(db)
        result = await tracker.check_budget_before_request(
            org.id, provider, estimated_tokens
        )

        return result

    except Exception as e:
        logger.error(f"Error checking budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))
