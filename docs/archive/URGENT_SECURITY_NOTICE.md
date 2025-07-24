# 🚨 URGENT: Critical Security Vulnerabilities

**Priority:** IMMEDIATE ACTION REQUIRED  
**Blocker:** All other development is blocked until resolved

## Critical Issues Found

### 1. Hardcoded Secrets in Repository

The following secrets are exposed in `backend/config.py`:

```python
# Line 19 - API Key exposed
[ai-provider]_api_key: str = "YOUR_API_KEY_HERE"

# Line 44 - JWT Secret exposed  
JWT_SECRET_KEY: str = "your-secret-key-change-in-production"

# Line 49 - Encryption Key exposed
ENCRYPTION_KEY: str = "YOUR_ENCRYPTION_KEY_HERE"
```

### 2. Required Actions

1. **Immediately remove all hardcoded secrets**
2. **Rotate all exposed keys**
3. **Implement proper environment variable management**
4. **Enable authentication middleware**

### 3. Implementation Guide

```python
# Updated config.py structure
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys - NEVER hardcode
    [ai-provider]_api_key: str = Field(..., env='DEEPSEEK_API_KEY')
    jwt_secret_key: str = Field(..., env='JWT_SECRET_KEY')
    encryption_key: str = Field(..., env='ENCRYPTION_KEY')
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 4. Create .env.example

```bash
# API Keys
DEEPSEEK_API_KEY=your_[ai-provider]_api_key_here

# Security
JWT_SECRET_KEY=generate_with_openssl_rand_hex_32
ENCRYPTION_KEY=generate_with_fernet_generate_key

# Database
DATABASE_URL=sqlite:///./legal_ai.db
```

### 5. Auth Middleware Must Be Enabled

Update all routes to require authentication:

```python
from fastapi import Depends, HTTPException
from auth_middleware import get_current_user

@app.get("/api/documents")
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Implementation
    pass
```

## Frontend is Blocked

The frontend team cannot proceed with auth integration until:
1. Secrets are removed and env vars work
2. Auth middleware is enabled
3. API returns proper 401 responses

## Verification Steps

- [ ] No secrets in code
- [ ] .env.example created
- [ ] All keys rotated
- [ ] Auth middleware active
- [ ] API requires tokens

**This must be completed TODAY before any other work proceeds.**