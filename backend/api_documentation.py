"""
Comprehensive API documentation with OpenAPI enhancements
"""

from fastapi import FastAPI
from typing import Dict, Any


def enhance_api_documentation(app: FastAPI) -> FastAPI:
    """Enhance FastAPI app with comprehensive API documentation."""

    # Update OpenAPI schema
    app.title = "Legal AI Assistant API"
    app.description = """
# Legal AI Assistant API Documentation

## Overview
The Legal AI Assistant API provides intelligent document analysis, chat capabilities, and document management for legal professionals.

## Key Features
- 🔐 **Secure Authentication**: JWT-based authentication with refresh tokens
- 📄 **Document Management**: Upload, analyze, and manage legal documents
- 🤖 **AI-Powered Analysis**: Intelligent document analysis and risk assessment
- 💬 **Contextual Chat**: AI chat with document context
- 🏢 **Multi-tenancy**: Organization-based data isolation

## Authentication
All API endpoints (except auth endpoints) require authentication. Include the JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting
- Authenticated requests: 100 requests per minute
- Document uploads: 10 per minute
- AI analysis: 20 per minute

## Base URL
```
https://api.example.com/api
```

## Common Response Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Contact
- **Support Email**: [SUPPORT-EMAIL]
- **API Status**: https://status.example.com
"""

    app.version = "1.0.0"
    app.terms_of_service = "https://example.com/terms"
    app.contact = {
        "name": "Legal AI Support",
        "url": "https://example.com/support",
        "email": "[SUPPORT-EMAIL]",
    }
    app.license_info = {"name": "Proprietary", "url": "https://example.com/license"}

    # Add tags for better organization
    tags_metadata = [
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints",
            "externalDocs": {
                "description": "Auth flow documentation",
                "url": "https://docs.example.com/auth",
            },
        },
        {
            "name": "Documents",
            "description": "Document upload, management, and analysis",
            "externalDocs": {
                "description": "Document API guide",
                "url": "https://docs.example.com/documents",
            },
        },
        {
            "name": "Chat",
            "description": "AI-powered chat functionality with document context",
            "externalDocs": {
                "description": "Chat API guide",
                "url": "https://docs.example.com/chat",
            },
        },
        {
            "name": "AI Analysis",
            "description": "AI document analysis and insights",
            "externalDocs": {
                "description": "AI capabilities",
                "url": "https://docs.example.com/ai",
            },
        },
        {
            "name": "Organizations",
            "description": "Organization and user management",
            "externalDocs": {
                "description": "Multi-tenancy guide",
                "url": "https://docs.example.com/organizations",
            },
        },
        {"name": "Health", "description": "Service health and monitoring endpoints"},
    ]

    app.openapi_tags = tags_metadata

    return app


# API endpoint documentation examples
api_examples = {
    "login": {
        "request": {"email": "[USER-EMAIL]", "password": "securepassword123"},
        "response": {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "email": "[USER-EMAIL]",
                "first_name": "John",
                "last_name": "Doe",
                "role": "attorney",
            },
            "organization": {
                "id": 1,
                "name": "Smith & Associates",
                "subscription_tier": "enterprise",
            },
        },
    },
    "document_upload": {
        "request": {"file": "<binary PDF data>", "document_type": "contract"},
        "response": {
            "id": 123,
            "filename": "service-agreement.pdf",
            "file_type": "application/pdf",
            "file_size": 245632,
            "status": "processing",
            "document_type": "contract",
            "uploaded_at": "2024-01-15T10:30:00Z",
        },
    },
    "document_analysis": {
        "response": {
            "id": 123,
            "filename": "service-agreement.pdf",
            "status": "completed",
            "ai_analysis": {
                "summary": "Service agreement between ABC Corp and XYZ Ltd for software development services.",
                "document_type": "contract",
                "key_terms": [
                    "Duration: 12 months",
                    "Value: $150,000",
                    "Payment: Monthly installments",
                ],
                "important_dates": [
                    "2024-01-01: Contract start date",
                    "2024-12-31: Contract end date",
                ],
                "potential_issues": [
                    {
                        "issue": "No termination clause specified",
                        "risk_level": "medium",
                        "recommendation": "Add clear termination conditions",
                    }
                ],
                "entities": {
                    "parties": ["ABC Corp", "XYZ Ltd"],
                    "dates": ["2024-01-01", "2024-12-31"],
                    "monetary_values": ["$150,000", "$12,500/month"],
                },
            },
        }
    },
    "chat_message": {
        "request": {
            "message": "What are the payment terms in the uploaded contract?",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "context": {"document_ids": [123]},
        },
        "response": {
            "response": "Based on the service agreement, the payment terms are:\n\n1. **Total Value**: $150,000\n2. **Payment Schedule**: Monthly installments of $12,500\n3. **Payment Due**: Within 30 days of invoice\n4. **Late Payment**: 1.5% monthly interest on overdue amounts\n\nThe contract specifies that invoices will be issued on the first business day of each month.",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "sources": [
                {
                    "document_id": 123,
                    "document_name": "service-agreement.pdf",
                    "relevant_sections": ["Section 4.2: Payment Terms"],
                }
            ],
        },
    },
}


# Rate limit documentation
rate_limits = {
    "endpoints": {
        "/api/auth/login": {"limit": "5 requests per minute", "scope": "IP address"},
        "/api/auth/register": {"limit": "3 requests per hour", "scope": "IP address"},
        "/api/documents/upload": {"limit": "10 requests per minute", "scope": "User"},
        "/api/chat": {"limit": "20 requests per minute", "scope": "User"},
        "/api/*": {"limit": "100 requests per minute", "scope": "User"},
    },
    "headers": {
        "X-RateLimit-Limit": "Request limit per window",
        "X-RateLimit-Remaining": "Requests remaining in window",
        "X-RateLimit-Reset": "Window reset timestamp",
        "Retry-After": "Seconds until next request allowed (429 only)",
    },
}


# Error response documentation
error_responses = {
    "400": {
        "description": "Bad Request",
        "example": {
            "detail": "Invalid document type. Must be one of: contract, immigration, family_law"
        },
    },
    "401": {
        "description": "Unauthorized",
        "example": {"detail": "Invalid or expired token"},
    },
    "403": {
        "description": "Forbidden",
        "example": {"detail": "Insufficient permissions for this operation"},
    },
    "404": {"description": "Not Found", "example": {"detail": "Document not found"}},
    "422": {
        "description": "Validation Error",
        "example": {
            "detail": [
                {
                    "loc": ["body", "email"],
                    "msg": "invalid email address",
                    "type": "value_error.email",
                }
            ]
        },
    },
    "429": {
        "description": "Too Many Requests",
        "example": {
            "detail": "Rate limit exceeded. Please retry after 60 seconds",
            "retry_after": 60,
        },
    },
    "500": {
        "description": "Internal Server Error",
        "example": {
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    },
}


def get_api_documentation() -> Dict[str, Any]:
    """Get complete API documentation."""
    return {
        "examples": api_examples,
        "rate_limits": rate_limits,
        "error_responses": error_responses,
        "webhooks": {
            "document.processed": {
                "description": "Fired when document analysis is complete",
                "payload": {
                    "event": "document.processed",
                    "document_id": 123,
                    "status": "completed",
                    "timestamp": "2024-01-15T10:35:00Z",
                },
            }
        },
        "sdk_examples": {
            "python": """
# Install: pip install legalai-sdk

from legalai import LegalAIClient

client = LegalAIClient(api_key="your-api-key")

# Upload document
doc = client.documents.upload("contract.pdf", document_type="contract")

# Get analysis
analysis = client.documents.get(doc.id)
print(analysis.ai_analysis.summary)

# Chat with context
response = client.chat.send(
    "What are the risks in this contract?",
    document_ids=[doc.id]
)
print(response.message)
""",
            "javascript": """
// Install: npm install @legalai/sdk

import { LegalAIClient } from '@legalai/sdk';

const client = new LegalAIClient({ apiKey: 'your-api-key' });

// Upload document
const doc = await client.documents.upload(file, { 
  documentType: 'contract' 
});

// Get analysis
const analysis = await client.documents.get(doc.id);
console.log(analysis.aiAnalysis.summary);

// Chat with context
const response = await client.chat.send({
  message: 'What are the risks in this contract?',
  documentIds: [doc.id]
});
console.log(response.message);
""",
        },
    }
