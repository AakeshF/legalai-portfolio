# AI Security Features Implementation

This document describes the comprehensive AI security and compliance features added to the Legal AI Backend.

## Overview

The implementation provides a complete security pipeline for AI operations in legal contexts, including:

1. **Anonymization and Data Protection**
2. **Prompt Review and Admin Workflow**
3. **Multi-Model AI Routing**
4. **Consent Management**
5. **Security Enforcement and Compliance**
6. **Integrated AI Assistant**

## Component Details

### 1. Anonymization Engine (`services/anonymization_service.py`)

**Features:**
- Pattern-based detection (SSN, credit cards, case numbers, etc.)
- NLP-based entity recognition using spaCy
- Reversible redaction with encrypted token storage
- Organization and user-specific pattern configuration
- Confidence scoring for detections

**Key Methods:**
- `anonymize_text()` - Main anonymization function
- `deanonymize_text()` - Reverse anonymization using stored tokens

**API Endpoints:**
- `POST /api/anonymization/patterns` - Create custom patterns
- `GET /api/anonymization/patterns` - List patterns
- `POST /api/anonymization/test` - Test anonymization
- `POST /api/anonymization/deanonymize` - Reverse anonymization

### 2. Prompt Processing Pipeline (`services/prompt_processor.py`)

**Features:**
- Automatic sensitive data detection
- Consent requirement checking
- Review queue management
- Auto-approval for low-risk prompts

**Workflow:**
1. Detect sensitive data
2. Check consent requirements
3. Apply anonymization
4. Determine review requirements
5. Route to review queue or auto-approve

**API Endpoints:**
- `POST /api/prompts/submit` - Submit prompt for processing
- `GET /api/prompts/status/{id}` - Check prompt status
- `GET /api/prompts/history` - User prompt history
- `WebSocket /api/prompts/ws/{id}` - Real-time status updates

### 3. Admin Review System (`services/admin_review_service.py`)

**Features:**
- Priority-based review queue
- Assignment and escalation
- Approval/rejection workflow
- Audit trail for all actions
- Analytics and reporting

**Admin Endpoints:**
- `GET /api/prompts/admin/pending` - Get pending prompts
- `POST /api/prompts/admin/{id}/approve` - Approve prompt
- `POST /api/prompts/admin/{id}/reject` - Reject prompt
- `GET /api/prompts/admin/analytics` - Review statistics

### 4. Model Router (`services/model_router.py`)

**Features:**
- Support for OpenAI, Claude, [AI Provider], and local models
- Intelligent routing based on preferences and availability
- API key management with encryption
- Rate limiting and health monitoring
- Cost tracking and estimation

**Supported Providers:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic Claude (Opus, Sonnet, Haiku)
- [AI Provider] (with demo mode)
- Local LLMs via Ollama

### 5. API Key Management (`services/api_key_manager.py`)

**Features:**
- Encrypted storage of API keys
- Validation and health checking
- Usage tracking and rotation
- Organization and user-level keys

### 6. Consent Management (`services/consent_manager.py`)

**Features:**
- Multiple consent types (Cloud AI, Data Retention, etc.)
- Hierarchical consent (org → user → document)
- Consent expiration and renewal
- Compliance reporting

**API Endpoints:**
- `POST /api/consent/record` - Record consent
- `GET /api/consent/check` - Check consent status
- `GET /api/consent/history` - Consent history
- `GET /api/consent/compliance/report` - Compliance report

### 7. Security Enforcement (`services/security_enforcement.py`)

**Features:**
- Data classification (Public → Privileged)
- Policy-based access control
- Security incident tracking
- Compliance scoring
- Data retention enforcement

**Classifications:**
- Public: No restrictions
- Internal: Minimal redaction
- Confidential: Consent required
- Restricted: No cloud AI, review required
- Privileged: Maximum security, local only

**API Endpoints:**
- `POST /api/security/check` - Security policy check
- `GET /api/security/compliance/report` - Compliance report
- `POST /api/security/retention/enforce` - Enforce retention
- `GET /api/security/incidents` - Security incidents

### 8. Integrated AI Assistant (`services/integrated_ai_assistant.py`)

**Features:**
- Complete pipeline integration
- Document context support
- Session management
- Usage statistics
- Health monitoring

**Main Endpoint:**
- `POST /api/ai/integrated/process` - Process AI request

**Workflow:**
1. Security check
2. Prompt processing & anonymization
3. Admin review (if required)
4. Model routing
5. Response post-processing
6. Audit logging

## Database Schema Additions

### New Tables:
- `anonymization_patterns` - Custom regex patterns
- `anonymization_rules` - Processing rules
- `redaction_tokens` - Reversible tokens
- `prompt_logs` - All prompts
- `prompt_admin_actions` - Admin actions
- `prompt_review_queue` - Review queue
- `consent_records` - Consent tracking
- `consent_preferences` - Org preferences

## Security Features

### Data Protection:
- End-to-end encryption for sensitive data
- Reversible anonymization
- Secure API key storage
- Audit trails for all operations

### Access Control:
- Role-based permissions
- Organization isolation
- Document-level consent
- Policy enforcement

### Compliance:
- GDPR-ready consent management
- Data retention policies
- Compliance reporting
- Incident tracking

## Usage Example

```python
# Complete AI request with security
POST /api/ai/integrated/process
{
    "prompt": "Analyze the contract between John Doe (SSN: 123-45-6789) and Acme Corp",
    "document_ids": ["doc123"],
    "preferred_model": "claude-3-sonnet"
}

# Response
{
    "status": "success",
    "response": "The contract between [PERSON_A1B2C3] and [ORG_D4E5F6] contains standard terms...",
    "metadata": {
        "prompt_id": 456,
        "model_used": "claude:claude-3-sonnet",
        "anonymization_applied": true,
        "classification": "confidential",
        "cost_estimate": 0.0125
    }
}
```

## Configuration

### Environment Variables:
```
# API Keys (optional - users can provide their own)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# Security
ENCRYPTION_KEY=your-encryption-key
JWT_SECRET_KEY=your-jwt-secret

# Models
DEFAULT_AI_PROVIDER=claude
DEFAULT_AI_MODEL=claude-3-sonnet
```

### Organization Settings:
- Security policies per classification
- Consent requirements
- Model preferences
- Budget limits

## Monitoring and Analytics

### Available Metrics:
- Compliance score
- Security incidents
- Model usage and costs
- Review queue statistics
- Consent rates

### Health Checks:
- Component status
- API key validation
- Model availability
- System performance

## Best Practices

1. **Always enable anonymization** for sensitive documents
2. **Configure organization policies** before processing
3. **Monitor compliance scores** regularly
4. **Review security incidents** promptly
5. **Rotate API keys** periodically
6. **Train custom patterns** for domain-specific data
7. **Set appropriate retention policies**
8. **Use local models** for highly sensitive data

## Future Enhancements

- Machine learning for pattern detection improvement
- Advanced consent workflows
- Real-time threat detection
- Automated compliance remediation
- Multi-language support
- Blockchain audit trails