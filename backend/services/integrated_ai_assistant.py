import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from models import (
    User,
    Organization,
    Document,
    PromptLog,
    PromptStatus,
    ChatSession,
    ChatMessage,
    AIAuditLog,
    ConsentType,
)
from services.prompt_processor import PromptProcessor
from services.security_enforcement import SecurityEnforcementService, SecurityAction
from services.model_router import ModelRouter
from services.consent_manager import ConsentManager
from services.document_processor import document_processor

logger = logging.getLogger(__name__)


class IntegratedAIAssistant:
    """
    Main service that integrates all components for secure AI processing
    """

    def __init__(self):
        self.prompt_processor = PromptProcessor()
        self.security_service = SecurityEnforcementService()
        self.model_router = ModelRouter()
        self.initialized = True
        logger.info("Integrated AI Assistant initialized")

    async def process_request(
        self,
        prompt: str,
        db: Session,
        user_id: str,
        org_id: str,
        session_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        preferred_model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process an AI request through the complete security pipeline
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Security check
            security_decision = await self.security_service.enforce_security_policy(
                content=prompt,
                operation_type="chat",
                db=db,
                user_id=user_id,
                org_id=org_id,
                metadata=context,
            )

            # Handle security actions
            if security_decision.action == SecurityAction.BLOCK:
                return {
                    "status": "blocked",
                    "message": "Request blocked by security policy",
                    "reasons": security_decision.reasons,
                    "classification": security_decision.classification.value,
                }

            if security_decision.action == SecurityAction.REQUIRE_CONSENT:
                return {
                    "status": "consent_required",
                    "message": "Consent required to process this request",
                    "required_consents": [
                        c.value for c in security_decision.required_consents
                    ],
                    "classification": security_decision.classification.value,
                }

            # Step 2: Process prompt through anonymization pipeline
            prompt_result = await self.prompt_processor.process_prompt(
                prompt=prompt,
                db=db,
                user_id=user_id,
                org_id=org_id,
                model_requested=preferred_model,
                context=context,
            )

            if prompt_result["status"] == "pending_review":
                return {
                    "status": "pending_review",
                    "message": "Your request requires manual review",
                    "prompt_id": prompt_result["prompt_id"],
                    "estimated_wait_time": prompt_result.get("estimated_wait_time", 0),
                }

            # Step 3: Get processed prompt
            processed_prompt = prompt_result.get("processed_prompt", prompt)

            # Step 4: Add document context if requested
            if document_ids:
                document_context = await self._get_document_context(
                    db, document_ids, user_id, org_id
                )
                processed_prompt = self._add_document_context(
                    processed_prompt, document_context
                )

            # Step 5: Route to AI model
            model_response = await self.model_router.route_request(
                prompt=processed_prompt,
                db=db,
                user_id=user_id,
                org_id=org_id,
                prompt_log_id=prompt_result.get("prompt_id"),
                preferred_provider=None,
                preferred_model=preferred_model,
            )

            # Step 6: Post-process response
            final_response = await self._post_process_response(
                model_response.content, security_decision, db, user_id, org_id
            )

            # Step 7: Update chat session if provided
            if session_id:
                await self._update_chat_session(
                    db, session_id, prompt, final_response, model_response
                )

            # Step 8: Update prompt log
            if prompt_result.get("prompt_id"):
                await self._update_prompt_log(
                    db, prompt_result["prompt_id"], model_response, final_response
                )

            # Calculate total processing time
            processing_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            return {
                "status": "success",
                "response": final_response,
                "metadata": {
                    "prompt_id": prompt_result.get("prompt_id"),
                    "model_used": f"{model_response.provider}:{model_response.model}",
                    "tokens_used": model_response.tokens_used,
                    "processing_time_ms": processing_time,
                    "anonymization_applied": prompt_result.get(
                        "anonymization_applied", False
                    ),
                    "classification": security_decision.classification.value,
                    "cost_estimate": model_response.cost,
                },
            }

        except Exception as e:
            logger.error(f"Error processing AI request: {e}")

            # Log failure
            await self._log_failure(db, user_id, org_id, str(e))

            return {
                "status": "error",
                "message": "An error occurred processing your request",
                "error": str(e),
            }

    async def _get_document_context(
        self, db: Session, document_ids: List[str], user_id: str, org_id: str
    ) -> List[Dict[str, Any]]:
        """Get context from documents"""
        documents = (
            db.query(Document)
            .filter(
                Document.id.in_(document_ids),
                Document.organization_id == org_id,
                Document.processing_status == "completed",
            )
            .all()
        )

        context = []
        for doc in documents:
            # Check document-level consent
            consent_manager = ConsentManager(db)
            consent_check = consent_manager.check_consent(
                org_id, ConsentType.CLOUD_AI, user_id, doc.id
            )

            if consent_check.get("granted", False):
                context.append(
                    {
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "content": doc.extracted_content[:5000],  # Limit context size
                        "metadata": doc.legal_metadata,
                    }
                )

        return context

    def _add_document_context(
        self, prompt: str, document_context: List[Dict[str, Any]]
    ) -> str:
        """Add document context to prompt"""
        if not document_context:
            return prompt

        context_text = "\n\nDocument Context:\n"
        for doc in document_context:
            context_text += f"\n--- {doc['filename']} ---\n"
            context_text += f"{doc['content']}\n"

        return prompt + context_text

    async def _post_process_response(
        self,
        response: str,
        security_decision: Any,
        db: Session,
        user_id: str,
        org_id: str,
    ) -> str:
        """Post-process AI response for security"""
        # If redaction was required, check response for sensitive data
        if security_decision.redaction_required:
            sensitivity_result = await self.security_service.sensitive_detector.analyze(
                response, db, user_id, org_id
            )

            if sensitivity_result.get("overall_sensitivity", 0) > 0.5:
                # Apply anonymization to response
                anonymization_result = (
                    self.prompt_processor.anonymization_service.anonymize_text(
                        response, db, user_id, org_id
                    )
                )
                return anonymization_result.redacted

        return response

    async def _update_chat_session(
        self,
        db: Session,
        session_id: str,
        prompt: str,
        response: str,
        model_response: Any,
    ):
        """Update chat session with new messages"""
        # Add user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=prompt,
            timestamp=datetime.utcnow(),
        )
        db.add(user_message)

        # Add assistant message
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response,
            timestamp=datetime.utcnow(),
            model_used=f"{model_response.provider}:{model_response.model}",
            processing_time=model_response.response_time_ms,
        )
        db.add(assistant_message)

        # Update session last activity
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.last_activity = datetime.utcnow()

        db.commit()

    async def _update_prompt_log(
        self, db: Session, prompt_id: int, model_response: Any, final_response: str
    ):
        """Update prompt log with results"""
        prompt_log = db.query(PromptLog).filter(PromptLog.id == prompt_id).first()

        if prompt_log:
            prompt_log.response_output = final_response
            prompt_log.response_time_ms = model_response.response_time_ms
            prompt_log.tokens_used = model_response.tokens_used
            prompt_log.status = PromptStatus.COMPLETED
            prompt_log.completed_at = datetime.utcnow()
            db.commit()

    async def _log_failure(self, db: Session, user_id: str, org_id: str, error: str):
        """Log failure to audit trail"""
        audit_log = AIAuditLog(
            organization_id=org_id,
            user_id=user_id,
            request_type="chat",
            decision_type="error",
            decision_summary=error[:500],  # Limit error message length
            created_at=datetime.utcnow(),
        )
        db.add(audit_log)

        try:
            db.commit()
        except:
            db.rollback()

    async def check_system_health(self, db: Session) -> Dict[str, Any]:
        """Check health of all integrated components"""
        health_status = {
            "overall": "healthy",
            "components": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Check prompt processor
        try:
            # Simple health check
            health_status["components"]["prompt_processor"] = {
                "status": "healthy" if self.prompt_processor else "unhealthy",
                "initialized": bool(self.prompt_processor),
            }
        except Exception as e:
            health_status["components"]["prompt_processor"] = {
                "status": "error",
                "error": str(e),
            }

        # Check security service
        try:
            health_status["components"]["security_service"] = {
                "status": "healthy" if self.security_service else "unhealthy",
                "initialized": bool(self.security_service),
            }
        except Exception as e:
            health_status["components"]["security_service"] = {
                "status": "error",
                "error": str(e),
            }

        # Check model router
        try:
            # Validate API keys
            key_status = await self.model_router.validate_all_keys(db, "default")
            health_status["components"]["model_router"] = {
                "status": "healthy",
                "providers": key_status,
            }
        except Exception as e:
            health_status["components"]["model_router"] = {
                "status": "error",
                "error": str(e),
            }

        # Determine overall health
        if any(
            comp.get("status") == "error"
            for comp in health_status["components"].values()
        ):
            health_status["overall"] = "degraded"

        return health_status

    async def get_usage_statistics(
        self,
        db: Session,
        org_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics for the organization"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get prompt statistics
        prompt_stats = (
            db.query(
                func.count(PromptLog.id).label("total_prompts"),
                func.avg(PromptLog.response_time_ms).label("avg_response_time"),
                func.sum(PromptLog.tokens_used).label("total_tokens"),
            )
            .filter(
                PromptLog.organization_id == org_id,
                PromptLog.created_at.between(start_date, end_date),
            )
            .first()
        )

        # Get model usage
        model_usage = (
            db.query(
                AIAuditLog.model_used,
                func.count(AIAuditLog.id).label("count"),
                func.sum(AIAuditLog.tokens_used).label("tokens"),
                func.sum(AIAuditLog.estimated_cost).label("cost"),
            )
            .filter(
                AIAuditLog.organization_id == org_id,
                AIAuditLog.request_timestamp.between(start_date, end_date),
            )
            .group_by(AIAuditLog.model_used)
            .all()
        )

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_prompts": prompt_stats.total_prompts or 0,
                "avg_response_time_ms": float(prompt_stats.avg_response_time or 0),
                "total_tokens": prompt_stats.total_tokens or 0,
            },
            "model_usage": [
                {
                    "model": usage.model_used,
                    "requests": usage.count,
                    "tokens": usage.tokens or 0,
                    "estimated_cost": float(usage.cost or 0),
                }
                for usage in model_usage
            ],
            "total_estimated_cost": sum(
                float(usage.cost or 0) for usage in model_usage
            ),
        }


# Global instance
integrated_ai_assistant = IntegratedAIAssistant()


from sqlalchemy import func
