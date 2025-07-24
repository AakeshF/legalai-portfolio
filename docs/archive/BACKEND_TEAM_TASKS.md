# Backend Team - Detailed Task Instructions

**Document Type:** Backend Implementation Guide  
**Team:** Backend Engineering  
**Timeline:** 16 Weeks  
**Priority Labels:** 🔴 CRITICAL | 🟡 HIGH | 🟢 MEDIUM | 🔵 LOW

---

## Team Roles & Responsibilities

- **BE-01**: Senior Backend Engineer (Security & Auth)
- **BE-02**: Backend Engineer (API & Services)
- **BE-03**: Backend Engineer (Data & Performance)
- **BE-04**: DevOps Engineer (Infrastructure)
- **BE-05**: QA Engineer (Testing)

---

## Week 1-2: Critical Security Fixes 🔴

### TASK-BE-001: Remove Hardcoded Secrets 🔴
**Owner:** BE-01  
**Duration:** 4 hours  
**Dependencies:** None  
**Labels:** `security`, `critical`, `blocking`

#### Step 1: Audit Current Secrets
```bash
cd backend
# Find all hardcoded secrets
grep -r "sk-" . --exclude-dir=venv --exclude-dir=__pycache__
grep -r "secret" . --exclude-dir=venv -i
grep -r "password" . --exclude-dir=venv -i
grep -r "key" . --exclude-dir=venv -i | grep -E "(=|:)\s*['\"]"

# Document findings in security_audit.txt
```

#### Step 2: Create Environment Template
```bash
# Create .env.example
cat > .env.example << 'EOF'
# API Keys (NEVER commit actual values)
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Security Keys (Generate new for each environment)
JWT_SECRET_KEY=
ENCRYPTION_KEY=
SESSION_SECRET_KEY=

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/legalai
REDIS_URL=redis://localhost:6379/0

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=[email@example.com]

# Application Settings
ENVIRONMENT=development
DEBUG=False
CORS_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]

# Monitoring
SENTRY_DSN=
PROMETHEUS_ENABLED=True
EOF
```

#### Step 3: Update config.py
```python
# backend/config.py - COMPLETE REPLACEMENT
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import secrets
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # API Keys
    [ai-provider]_api_key: str = Field(..., description="[AI Provider] API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    
    # Security
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    jwt_refresh_expiration_days: int = 7
    encryption_key: str = Field(..., description="Fernet encryption key")
    session_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    
    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    redis_url: str = Field("redis://localhost:6379/0")
    
    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_email: str = "[email@example.com]"
    
    # Application
    environment: str = Field("development", pattern="^(development|staging|production)$")
    debug: bool = Field(False)
    cors_origins: List[str] = ["http://localhost:3000"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    # File Upload
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "uploads"
    allowed_extensions: List[str] = [".pdf", ".docx", ".txt"]
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    prometheus_enabled: bool = True
    log_level: str = "INFO"
    
    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        try:
            from cryptography.fernet import Fernet
            Fernet(v.encode() if isinstance(v, str) else v)
        except Exception:
            raise ValueError("Invalid Fernet encryption key")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Export for easy access
settings = get_settings()
```

#### Step 4: Generate Secure Keys
```bash
# Create key generation script
cat > generate_keys.py << 'EOF'
#!/usr/bin/env python3
import secrets
from cryptography.fernet import Fernet

print("# Generated secure keys - ADD TO .env FILE")
print(f"JWT_SECRET_KEY={secrets.token_hex(32)}")
print(f"SESSION_SECRET_KEY={secrets.token_hex(32)}")
print(f"ENCRYPTION_KEY={Fernet.generate_key().decode()}")
EOF

python generate_keys.py
```

#### Verification Checklist:
- [ ] No hardcoded secrets in any .py file
- [ ] .env file created with all values
- [ ] .env added to .gitignore
- [ ] config.py only uses environment variables
- [ ] All keys are properly validated

---

### TASK-BE-002: Clean Git History 🔴
**Owner:** BE-04  
**Duration:** 2 hours  
**Dependencies:** TASK-BE-001  
**Labels:** `security`, `critical`, `git`

#### Step 1: Backup Repository
```bash
# Create complete backup
cd ..
tar -czf legalai_backup_$(date +%Y%m%d_%H%M%S).tar.gz legal-ai/
cd legal-ai
```

#### Step 2: Install BFG Repo Cleaner
```bash
# macOS
brew install bfg

# Linux
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
alias bfg='java -jar bfg-1.14.0.jar'
```

#### Step 3: Create Sensitive Data List
```bash
cat > sensitive_patterns.txt << 'EOF'
sk-56fe0d5e45b84a559cf5fc92e41c9b8c
oJn3xOTp_y72ReNmCi18mRIY6yxY6cwL_QlKAXlOTPg=
regex:sk-[a-zA-Z0-9]{48}
regex:postgres://[^@]+@
regex:smtp://[^@]+@
EOF
```

#### Step 4: Clean Repository
```bash
# Remove sensitive strings
bfg --replace-text sensitive_patterns.txt

# Remove sensitive files
bfg --delete-files '*.{pdf,docx,db}'
bfg --delete-folders uploads

# Clean git history
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

#### Step 5: Update .gitignore
```bash
cat >> .gitignore << 'EOF'

# Security
.env
.env.*
!.env.example
*.pem
*.key
*.cert

# Uploads
uploads/
temp/
tmp/

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store
EOF
```

#### Verification Checklist:
- [ ] Sensitive data removed from history
- [ ] No client files in repository
- [ ] .gitignore properly configured
- [ ] Team notified about force push

---

### TASK-BE-003: Fix Authentication Middleware 🔴
**Owner:** BE-01  
**Duration:** 8 hours  
**Dependencies:** TASK-BE-001  
**Labels:** `auth`, `critical`, `api`

#### Step 1: Update JWT Authentication
```python
# backend/auth/jwt_handler.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class JWTHandler:
    """Handle JWT token creation and validation"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expiration_days)
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)

jwt_handler = JWTHandler()
```

#### Step 2: Create Auth Dependencies
```python
# backend/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User
from .jwt_handler import jwt_handler

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    # Verify token
    payload = jwt_handler.verify_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_organization_member(
    current_user: User = Depends(get_current_user),
    organization_id: int = None
) -> User:
    """Verify user belongs to organization"""
    if organization_id and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    return current_user
```

#### Step 3: Update Auth Routes
```python
# backend/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import User, Organization, AuditLog
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from .jwt_handler import jwt_handler
from .dependencies import get_current_user
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user and organization"""
    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization if needed
    if user_data.organization_name:
        organization = Organization(
            name=user_data.organization_name,
            created_at=datetime.utcnow()
        )
        db.add(organization)
        db.flush()
        organization_id = organization.id
    else:
        organization_id = user_data.organization_id
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=jwt_handler.get_password_hash(user_data.password),
        full_name=user_data.full_name,
        organization_id=organization_id,
        role=user_data.role or "attorney",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    
    # Log registration
    audit_log = AuditLog(
        user_id=user.id,
        organization_id=organization_id,
        action="user_registered",
        details={"email": user.email},
        ip_address=user_data.ip_address,
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login and receive tokens"""
    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not jwt_handler.verify_password(credentials.password, user.hashed_password):
        # Log failed attempt
        if user:
            audit_log = AuditLog(
                user_id=user.id,
                organization_id=user.organization_id,
                action="login_failed",
                details={"reason": "invalid_password"},
                ip_address=credentials.ip_address,
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "org": user.organization_id,
        "role": user.role
    }
    
    access_token = jwt_handler.create_access_token(token_data)
    refresh_token = jwt_handler.create_refresh_token(token_data)
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Log successful login
    audit_log = AuditLog(
        user_id=user.id,
        organization_id=user.organization_id,
        action="login_success",
        details={"ip": credentials.ip_address},
        ip_address=credentials.ip_address,
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration_minutes * 60,
        "user": user
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    # Verify refresh token
    payload = jwt_handler.verify_token(refresh_token, token_type="refresh")
    user_id = payload.get("sub")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Create new tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "org": user.organization_id,
        "role": user.role
    }
    
    new_access_token = jwt_handler.create_access_token(token_data)
    new_refresh_token = jwt_handler.create_refresh_token(token_data)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration_minutes * 60,
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user (log the action)"""
    audit_log = AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="logout",
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Logged out successfully"}
```

#### Step 4: Apply Auth to All Routes
```python
# backend/main.py - Update all routes
from auth.dependencies import get_current_user, get_current_admin_user

# Example: Update document routes
@app.get("/api/documents")
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    document_type: Optional[str] = None
):
    """Get all documents for user's organization"""
    query = db.query(Document).filter(
        Document.organization_id == current_user.organization_id
    )
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    total = query.count()
    documents = query.offset(skip).limit(limit).all()
    
    return {
        "documents": documents,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document with auth"""
    # Existing upload logic...
    document.uploaded_by_id = current_user.id
    document.organization_id = current_user.organization_id
    # ...
```

#### Verification Checklist:
- [ ] JWT tokens properly generated
- [ ] All routes require authentication
- [ ] Token refresh working
- [ ] Audit logging implemented
- [ ] Organization isolation enforced

---

### TASK-BE-004: Database Migration & Cleanup 🟡
**Owner:** BE-03  
**Duration:** 4 hours  
**Dependencies:** TASK-BE-003  
**Labels:** `database`, `migration`

#### Step 1: Create Migration for Security Tables
```python
# backend/migrations/add_security_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add missing columns to users table
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), default=0))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))
    
    # Create sessions table for token management
    op.create_table('user_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('refresh_token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Index('idx_sessions_user', 'user_id'),
        sa.Index('idx_sessions_token', 'token_hash'),
        sa.Index('idx_sessions_expires', 'expires_at')
    )
    
    # Create API keys table
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('last_used_at', sa.DateTime()),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Index('idx_api_keys_org', 'organization_id'),
        sa.Index('idx_api_keys_hash', 'key_hash')
    )

def downgrade():
    op.drop_table('api_keys')
    op.drop_table('user_sessions')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login')
```

#### Step 2: Run Migrations
```bash
# Create migration
cd backend
alembic revision -m "add security tables"

# Edit the generated file with above content

# Run migration
alembic upgrade head

# Verify
python -c "
from sqlalchemy import create_engine, inspect
from config import settings

engine = create_engine(settings.database_url)
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
print('User columns:', [c['name'] for c in inspector.get_columns('users')])
"
```

#### Step 3: Data Cleanup Script
```python
# backend/scripts/cleanup_data.py
import os
import shutil
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import get_db
from models import Document, AuditLog
from config import settings

def cleanup_old_data(db: Session, days: int = 90):
    """Remove old data and files"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get old documents
    old_documents = db.query(Document).filter(
        Document.created_at < cutoff_date,
        Document.is_archived == True
    ).all()
    
    # Delete files
    for doc in old_documents:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
                print(f"Deleted file: {doc.file_path}")
            except Exception as e:
                print(f"Error deleting {doc.file_path}: {e}")
    
    # Delete database records
    db.query(Document).filter(
        Document.id.in_([d.id for d in old_documents])
    ).delete(synchronize_session=False)
    
    # Clean old audit logs
    db.query(AuditLog).filter(
        AuditLog.created_at < cutoff_date
    ).delete(synchronize_session=False)
    
    db.commit()
    print(f"Cleaned {len(old_documents)} old documents")

def cleanup_temp_files():
    """Clean temporary upload files"""
    temp_dir = os.path.join(settings.upload_dir, "temp")
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            if os.path.getmtime(file_path) < time.time() - 86400:  # 24 hours
                os.remove(file_path)
                print(f"Removed temp file: {file}")

if __name__ == "__main__":
    db = next(get_db())
    cleanup_old_data(db)
    cleanup_temp_files()
```

---

## Week 3-4: Testing & Quality Assurance 🟡

### TASK-BE-005: Unit Test Suite 🟡
**Owner:** BE-05  
**Duration:** 16 hours  
**Dependencies:** TASK-BE-003  
**Labels:** `testing`, `quality`

#### Step 1: Test Structure Setup
```bash
# Create test structure
mkdir -p backend/tests/{unit/{models,services,utils},integration,fixtures}

# Install testing dependencies
pip install pytest pytest-cov pytest-asyncio pytest-mock factory-boy faker hypothesis
```

#### Step 2: Create Test Factories
```python
# backend/tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from models import User, Organization, Document, ChatSession
from auth.jwt_handler import jwt_handler

fake = Faker()

class OrganizationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Organization
    
    name = factory.LazyFunction(lambda: f"{fake.company()} Law Firm")
    subscription_tier = "professional"
    is_active = True
    max_users = 50
    max_storage_gb = 100

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
    
    email = factory.LazyFunction(fake.email)
    hashed_password = factory.LazyFunction(
        lambda: jwt_handler.get_password_hash("TestPassword123!")
    )
    full_name = factory.LazyFunction(fake.name)
    organization = factory.SubFactory(OrganizationFactory)
    role = "attorney"
    is_active = True

class DocumentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Document
    
    filename = factory.LazyFunction(lambda: f"{fake.word()}.pdf")
    file_path = factory.LazyFunction(lambda: f"uploads/{fake.uuid4()}.pdf")
    file_size = factory.LazyFunction(lambda: fake.random_int(1000, 10000000))
    content = factory.LazyFunction(lambda: fake.text(max_nb_chars=5000))
    document_type = factory.LazyFunction(
        lambda: fake.random_element(['contract', 'brief', 'motion', 'memo'])
    )
    processing_status = "completed"
    organization = factory.SubFactory(OrganizationFactory)
    uploaded_by = factory.SubFactory(UserFactory)
```

#### Step 3: Unit Tests for Services
```python
# backend/tests/unit/services/test_ai_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.ai_service import AIService
from services.document_processor import DocumentProcessor
import json

class TestAIService:
    
    @pytest.fixture
    def ai_service(self):
        with patch('services.ai_service.settings') as mock_settings:
            mock_settings.[ai-provider]_api_key = "test-key"
            mock_settings.openai_api_key = "test-key"
            return AIService()
    
    @pytest.mark.asyncio
    async def test_analyze_contract_success(self, ai_service):
        """Test successful contract analysis"""
        # Mock API response
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "document_type": "contract",
                        "parties": ["Company A", "Company B"],
                        "key_dates": {"effective_date": "2024-01-01"},
                        "obligations": ["Payment of $10,000"],
                        "risks": ["Late payment penalties"],
                        "summary": "Service agreement between parties"
                    })
                }
            }]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=mock_response
            )
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await ai_service.analyze_document(
                "contract",
                "This is a test contract content"
            )
            
            assert result["document_type"] == "contract"
            assert len(result["parties"]) == 2
            assert "Company A" in result["parties"]
            assert result["summary"] == "Service agreement between parties"
    
    @pytest.mark.asyncio
    async def test_analyze_document_fallback_to_demo(self, ai_service):
        """Test fallback to demo mode on API failure"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 500
            
            result = await ai_service.analyze_document(
                "contract",
                "This is a test contract"
            )
            
            # Should return demo data
            assert result["summary"] == "[Demo Mode] AI analysis unavailable"
            assert "demo" in result["metadata"]
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, ai_service):
        """Test rate limiting functionality"""
        with patch('services.ai_service.AIRateLimiter.check_rate_limit') as mock_limit:
            mock_limit.return_value = False
            
            with pytest.raises(Exception, match="Rate limit exceeded"):
                await ai_service.analyze_document("contract", "content")
    
    def test_sanitize_content(self, ai_service):
        """Test content sanitization"""
        sensitive_content = """
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        Email: [email@example.com]
        """
        
        sanitized = ai_service._sanitize_content(sensitive_content)
        
        assert "123-45-6789" not in sanitized
        assert "4111-1111-1111-1111" not in sanitized
        assert "[REDACTED]" in sanitized

# backend/tests/unit/services/test_document_processor.py
class TestDocumentProcessor:
    
    @pytest.fixture
    def processor(self):
        return DocumentProcessor()
    
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a sample PDF for testing"""
        from reportlab.pdfgen import canvas
        
        pdf_path = tmp_path / "test.pdf"
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 100, "This is a test PDF document")
        c.save()
        return pdf_path
    
    def test_extract_text_from_pdf(self, processor, sample_pdf):
        """Test PDF text extraction"""
        text = processor.extract_text(str(sample_pdf))
        assert "test PDF document" in text
    
    def test_extract_text_from_docx(self, processor, tmp_path):
        """Test DOCX text extraction"""
        from docx import Document
        
        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_paragraph("This is a test DOCX document")
        doc.save(str(docx_path))
        
        text = processor.extract_text(str(docx_path))
        assert "test DOCX document" in text
    
    def test_file_validation(self, processor):
        """Test file validation"""
        assert processor.validate_file("test.pdf", 1024 * 1024) == True
        assert processor.validate_file("test.exe", 1024) == False
        assert processor.validate_file("test.pdf", 100 * 1024 * 1024) == False
    
    def test_extract_metadata(self, processor, sample_pdf):
        """Test metadata extraction"""
        metadata = processor.extract_metadata(str(sample_pdf))
        
        assert "page_count" in metadata
        assert "file_size" in metadata
        assert metadata["file_type"] == "pdf"
```

#### Step 4: Integration Tests
```python
# backend/tests/integration/test_auth_flow.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
from tests.factories import UserFactory, OrganizationFactory

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

class TestAuthenticationFlow:
    
    def test_complete_auth_flow(self, client, db):
        """Test complete authentication flow"""
        # 1. Register new user
        register_data = {
            "email": "[email@example.com]",
            "password": "SecurePass123!",
            "full_name": "Test Lawyer",
            "organization_name": "Test Law Firm"
        }
        
        response = client.post("/api/auth/register", json=register_data)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == register_data["email"]
        
        # 2. Login
        login_data = {
            "email": "[email@example.com]",
            "password": "SecurePass123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        tokens = response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        # 3. Access protected endpoint
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "[email@example.com]"
        
        # 4. Refresh token
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = client.post("/api/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        new_tokens = response.json()
        assert new_tokens["access_token"] != tokens["access_token"]
        
        # 5. Logout
        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        response = client.post("/api/auth/logout", headers=headers)
        assert response.status_code == 200
    
    def test_invalid_credentials(self, client, db):
        """Test login with invalid credentials"""
        UserFactory._meta.sqlalchemy_session = db
        user = UserFactory(email="[email@example.com]")
        db.commit()
        
        # Wrong password
        response = client.post("/api/auth/login", json={
            "email": "[email@example.com]",
            "password": "WrongPassword"
        })
        assert response.status_code == 401
        
        # Non-existent email
        response = client.post("/api/auth/login", json={
            "email": "[email@example.com]",
            "password": "TestPassword123!"
        })
        assert response.status_code == 401
    
    def test_token_expiration(self, client, db):
        """Test token expiration handling"""
        # Create expired token
        from datetime import datetime, timedelta
        from auth.jwt_handler import jwt_handler
        
        expired_token = jwt_handler.create_access_token({
            "sub": "1",
            "exp": datetime.utcnow() - timedelta(hours=1)
        })
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
```

#### Step 5: Performance Tests
```python
# backend/tests/performance/test_load.py
import pytest
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time

class TestPerformance:
    
    @pytest.mark.slow
    async def test_concurrent_document_uploads(self, client, authenticated_headers):
        """Test system under concurrent load"""
        async def upload_document():
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', b'test content', 
                             filename='test.pdf',
                             content_type='application/pdf')
                data.add_field('document_type', 'contract')
                
                async with session.post(
                    'http://localhost:8000/api/documents/upload',
                    data=data,
                    headers=authenticated_headers
                ) as response:
                    return response.status
        
        # Run 50 concurrent uploads
        start_time = time.time()
        tasks = [upload_document() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Assertions
        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 45  # 90% success rate
        assert duration < 10  # Should complete within 10 seconds
        
        print(f"Uploaded {success_count}/50 documents in {duration:.2f}s")
    
    @pytest.mark.slow
    def test_database_query_performance(self, db, benchmark):
        """Benchmark database queries"""
        # Create test data
        org = OrganizationFactory()
        users = [UserFactory(organization=org) for _ in range(100)]
        docs = [DocumentFactory(organization=org) for _ in range(1000)]
        db.add_all(users + docs)
        db.commit()
        
        # Benchmark query
        def query_documents():
            return db.query(Document).filter(
                Document.organization_id == org.id
            ).limit(20).all()
        
        result = benchmark(query_documents)
        assert len(result) == 20
```

---

## Week 5-6: Performance & Monitoring 🟡

### TASK-BE-006: Redis Caching Layer 🟡
**Owner:** BE-03  
**Duration:** 8 hours  
**Dependencies:** TASK-BE-005  
**Labels:** `performance`, `caching`

#### Step 1: Redis Configuration
```python
# backend/cache/redis_config.py
import redis
from redis import ConnectionPool
from config import settings
import pickle
import json
from typing import Optional, Any, Union
from datetime import timedelta

class RedisCache:
    """Redis cache implementation with connection pooling"""
    
    def __init__(self):
        self.pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=False
        )
        self.client = redis.Redis(connection_pool=self.pool)
        self.default_ttl = 3600  # 1 hour
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        return pickle.dumps(value)
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        if value is None:
            return None
        return pickle.loads(value)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            serialized = self._serialize(value)
            ttl = ttl or self.default_ttl
            return self.client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete pattern error: {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error: {e}")
            return 0
    
    def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        return self.client.ttl(key)
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(self.client.exists(key))
    
    def health_check(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except Exception:
            return False

# Initialize cache
cache = RedisCache()
```

#### Step 2: Cache Decorators
```python
# backend/cache/decorators.py
from functools import wraps
import hashlib
import inspect
from typing import Optional, Callable
from .redis_config import cache

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached(
    prefix: str,
    ttl: int = 3600,
    key_func: Optional[Callable] = None,
    unless: Optional[Callable] = None
):
    """Cache decorator for functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if caching should be skipped
            if unless and unless(*args, **kwargs):
                return await func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key_str = f"{prefix}:{key_func(*args, **kwargs)}"
            else:
                # Skip 'self' for class methods
                func_args = args[1:] if args and hasattr(args[0], '__class__') else args
                cache_key_str = f"{prefix}:{cache_key(*func_args, **kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key_str)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                cache.set(cache_key_str, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check if caching should be skipped
            if unless and unless(*args, **kwargs):
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key_str = f"{prefix}:{key_func(*args, **kwargs)}"
            else:
                # Skip 'self' for class methods
                func_args = args[1:] if args and hasattr(args[0], '__class__') else args
                cache_key_str = f"{prefix}:{cache_key(*func_args, **kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key_str)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                cache.set(cache_key_str, result, ttl)
            
            return result
        
        # Return appropriate wrapper
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

def invalidate_cache(patterns: list):
    """Decorator to invalidate cache patterns after function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            for pattern in patterns:
                cache.delete_pattern(pattern)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for pattern in patterns:
                cache.delete_pattern(pattern)
            return result
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
```

#### Step 3: Apply Caching to Services
```python
# backend/services/cached_services.py
from cache.decorators import cached, invalidate_cache
from models import Document, User
from typing import List, Optional

class CachedDocumentService:
    
    @cached(prefix="doc", ttl=900)  # 15 minutes
    async def get_document(self, document_id: int, organization_id: int) -> Optional[Document]:
        """Get document with caching"""
        return db.query(Document).filter(
            Document.id == document_id,
            Document.organization_id == organization_id
        ).first()
    
    @cached(
        prefix="docs_list",
        ttl=300,  # 5 minutes
        key_func=lambda self, org_id, page, limit, doc_type: f"{org_id}:{page}:{limit}:{doc_type or 'all'}"
    )
    async def get_documents_list(
        self,
        organization_id: int,
        page: int = 1,
        limit: int = 20,
        document_type: Optional[str] = None
    ) -> dict:
        """Get paginated documents with caching"""
        query = db.query(Document).filter(
            Document.organization_id == organization_id
        )
        
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        total = query.count()
        documents = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "documents": documents,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    @invalidate_cache(["docs_list:*", "doc:*"])
    async def update_document(self, document_id: int, data: dict) -> Document:
        """Update document and invalidate cache"""
        document = db.query(Document).filter(Document.id == document_id).first()
        for key, value in data.items():
            setattr(document, key, value)
        db.commit()
        return document

class CachedAIService:
    
    @cached(
        prefix="ai_analysis",
        ttl=86400,  # 24 hours
        key_func=lambda self, doc_type, content: hashlib.md5(
            f"{doc_type}:{content[:500]}".encode()
        ).hexdigest()
    )
    async def analyze_document(self, document_type: str, content: str) -> dict:
        """Cache AI analysis results"""
        # Expensive AI API call
        return await self._call_ai_api(document_type, content)
```

---

### TASK-BE-007: Monitoring & Alerting Setup 🟡
**Owner:** BE-04  
**Duration:** 12 hours  
**Dependencies:** TASK-BE-006  
**Labels:** `monitoring`, `infrastructure`

#### Step 1: Prometheus Metrics
```python
# backend/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import generate_latest, REGISTRY
from functools import wraps
import time
from typing import Callable

# Application metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

active_users = Gauge(
    'active_users_total',
    'Number of active users',
    ['organization']
)

documents_processed = Counter(
    'documents_processed_total',
    'Total documents processed',
    ['document_type', 'status']
)

ai_api_calls = Counter(
    'ai_api_calls_total',
    'AI API calls',
    ['provider', 'model', 'status']
)

ai_api_latency = Histogram(
    'ai_api_latency_seconds',
    'AI API call latency',
    ['provider', 'model']
)

cache_operations = Counter(
    'cache_operations_total',
    'Cache operations',
    ['operation', 'status']
)

db_connections = Gauge(
    'database_connections_active',
    'Active database connections'
)

app_info = Info(
    'app_info',
    'Application information'
)

# Set app info
app_info.info({
    'version': '1.0.0',
    'environment': settings.environment,
    'python_version': sys.version
})

def track_time(metric: Histogram):
    """Decorator to track execution time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

class MetricsMiddleware:
    """FastAPI middleware for automatic metrics collection"""
    
    async def __call__(self, request, call_next):
        start_time = time.time()
        
        # Track active users
        if hasattr(request.state, "user"):
            active_users.labels(
                organization=request.state.user.organization.name
            ).inc()
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=str(status)
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
        
        return response
```

#### Step 2: Logging Configuration
```python
# backend/monitoring/logging_config.py
import logging
import json
from pythonjsonlogger import jsonlogger
from datetime import datetime
import sys

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add custom fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['environment'] = settings.environment
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'organization_id'):
            log_record['organization_id'] = record.organization_id

def setup_logging():
    """Configure application logging"""
    
    # Create formatters
    json_formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    # Console handler (JSON format for production)
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.environment == "production":
        console_handler.setFormatter(json_formatter)
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    # File handler (always JSON)
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(json_formatter)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/error.log',
        maxBytes=10485760,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Add Sentry handler if configured
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )

# Request logging middleware
class LoggingMiddleware:
    """Log all requests and responses"""
    
    async def __call__(self, request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Log request
        logger.info(
            "Request received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )
        
        # Add request ID to context
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
```

#### Step 3: Docker Compose Monitoring Stack
```yaml
# backend/docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=redis-datasource
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    networks:
      - monitoring

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - monitoring

  postgres-exporter:
    image: wrouesnel/postgres_exporter:latest
    ports:
      - "9187:9187"
    environment:
      DATA_SOURCE_NAME: "postgresql://user:password@postgres:5432/legalai?sslmode=disable"
    networks:
      - monitoring

  redis-exporter:
    image: oliver006/redis_exporter:latest
    ports:
      - "9121:9121"
    environment:
      REDIS_ADDR: "redis://redis:6379"
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:
```

#### Step 4: Alert Rules
```yaml
# backend/monitoring/alerts.yml
groups:
  - name: legalai_alerts
    interval: 30s
    rules:
      # API Performance
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High API response time"
          description: "95th percentile response time is {{ $value }}s"
      
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      # Document Processing
      - alert: DocumentProcessingBacklog
        expr: documents_processing_queue > 100
        for: 15m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Large document processing backlog"
          description: "{{ $value }} documents in queue"
      
      - alert: DocumentProcessingFailures
        expr: rate(documents_processed_total{status="failed"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High document processing failure rate"
          description: "Failure rate is {{ $value | humanizePercentage }}"
      
      # AI Service
      - alert: AIServiceDown
        expr: up{job="ai_service"} == 0
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "AI service is down"
          description: "AI service has been down for more than 1 minute"
      
      - alert: AIAPIHighLatency
        expr: histogram_quantile(0.95, rate(ai_api_latency_seconds_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "AI API high latency"
          description: "95th percentile latency is {{ $value }}s"
      
      # Infrastructure
      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections_active / database_connections_max > 0.8
        for: 5m
        labels:
          severity: warning
          team: devops
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "Using {{ $value | humanizePercentage }} of connections"
      
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.9
        for: 5m
        labels:
          severity: warning
          team: devops
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"
      
      - alert: DiskSpaceLow
        expr: (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) > 0.85
        for: 10m
        labels:
          severity: warning
          team: devops
        annotations:
          summary: "Low disk space"
          description: "Disk usage is {{ $value | humanizePercentage }}"
```

---

## Week 7-10: Enterprise Features 🟢

### TASK-BE-008: WebSocket Real-time Updates 🟢
**Owner:** BE-02  
**Duration:** 12 hours  
**Dependencies:** TASK-BE-007  
**Labels:** `feature`, `realtime`

#### Step 1: WebSocket Manager
```python
# backend/websocket/manager.py
from typing import Dict, List, Set
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # Store active connections by organization
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store user-specific connections
        self.user_connections: Dict[int, WebSocket] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        organization_id: int
    ):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        # Add to organization connections
        if organization_id not in self.active_connections:
            self.active_connections[organization_id] = set()
        self.active_connections[organization_id].add(websocket)
        
        # Add to user connections
        self.user_connections[user_id] = websocket
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "organization_id": organization_id,
            "connected_at": datetime.utcnow()
        }
        
        # Send connection confirmation
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        metadata = self.connection_metadata.get(websocket)
        
        if metadata:
            # Remove from organization connections
            org_id = metadata["organization_id"]
            if org_id in self.active_connections:
                self.active_connections[org_id].discard(websocket)
                if not self.active_connections[org_id]:
                    del self.active_connections[org_id]
            
            # Remove from user connections
            user_id = metadata["user_id"]
            if user_id in self.user_connections:
                del self.user_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, message: dict, user_id: int):
        """Send message to specific user"""
        if user_id in self.user_connections:
            await self.send_personal_message(
                message,
                self.user_connections[user_id]
            )
    
    async def broadcast_to_organization(
        self,
        message: dict,
        organization_id: int,
        exclude_user: Optional[int] = None
    ):
        """Broadcast message to all users in organization"""
        if organization_id in self.active_connections:
            disconnected = []
            
            for connection in self.active_connections[organization_id]:
                metadata = self.connection_metadata.get(connection)
                
                # Skip excluded user
                if exclude_user and metadata and metadata["user_id"] == exclude_user:
                    continue
                
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def send_document_update(
        self,
        document_id: int,
        organization_id: int,
        update_type: str,
        data: dict
    ):
        """Send document update notification"""
        message = {
            "type": "document_update",
            "document_id": document_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_organization(message, organization_id)

# Global connection manager
manager = ConnectionManager()
```

#### Step 2: WebSocket Routes
```python
# backend/websocket/routes.py
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from auth.dependencies import get_current_user_ws
from .manager import manager
import asyncio

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time updates"""
    
    # Authenticate user
    try:
        user = await get_current_user_ws(token, db)
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Connect
    await manager.connect(websocket, user.id, user.organization_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            # Handle different message types
            if data["type"] == "ping":
                await manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                    websocket
                )
            
            elif data["type"] == "document_subscribe":
                # Subscribe to document updates
                document_id = data["document_id"]
                # Add subscription logic
                
            elif data["type"] == "presence":
                # Broadcast user presence
                await manager.broadcast_to_organization(
                    {
                        "type": "user_presence",
                        "user_id": user.id,
                        "status": data["status"],
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    user.organization_id,
                    exclude_user=user.id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
        # Notify others about disconnect
        await manager.broadcast_to_organization(
            {
                "type": "user_disconnected",
                "user_id": user.id,
                "timestamp": datetime.utcnow().isoformat()
            },
            user.organization_id
        )
```

#### Step 3: Real-time Event Broadcasting
```python
# backend/events/broadcaster.py
from websocket.manager import manager
from typing import Optional
import asyncio

class EventBroadcaster:
    """Broadcast events to WebSocket clients"""
    
    async def document_created(
        self,
        document: Document,
        user_id: int
    ):
        """Broadcast document creation"""
        await manager.send_document_update(
            document.id,
            document.organization_id,
            "created",
            {
                "filename": document.filename,
                "document_type": document.document_type,
                "created_by": user_id,
                "created_at": document.created_at.isoformat()
            }
        )
    
    async def document_processed(
        self,
        document: Document,
        success: bool,
        error: Optional[str] = None
    ):
        """Broadcast document processing completion"""
        await manager.send_document_update(
            document.id,
            document.organization_id,
            "processed",
            {
                "status": "completed" if success else "failed",
                "error": error,
                "processed_at": datetime.utcnow().isoformat()
            }
        )
    
    async def chat_message_received(
        self,
        session_id: str,
        message: ChatMessage,
        organization_id: int
    ):
        """Broadcast new chat message"""
        await manager.broadcast_to_organization(
            {
                "type": "chat_message",
                "session_id": session_id,
                "message": {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                }
            },
            organization_id
        )
    
    async def user_activity(
        self,
        user_id: int,
        organization_id: int,
        activity_type: str,
        details: dict
    ):
        """Broadcast user activity"""
        await manager.broadcast_to_organization(
            {
                "type": "user_activity",
                "user_id": user_id,
                "activity_type": activity_type,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            },
            organization_id,
            exclude_user=user_id
        )

# Global event broadcaster
broadcaster = EventBroadcaster()

# Update document upload to broadcast event
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... existing upload logic ...
    
    # Broadcast document creation
    await broadcaster.document_created(document, current_user.id)
    
    # ... rest of the function ...
```

---

### TASK-BE-009: Advanced Search with Elasticsearch 🟢
**Owner:** BE-03  
**Duration:** 16 hours  
**Dependencies:** TASK-BE-008  
**Labels:** `feature`, `search`

#### Step 1: Elasticsearch Configuration
```python
# backend/search/elasticsearch_config.py
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from typing import List, Dict, Any
import json

class ElasticsearchService:
    """Elasticsearch service for advanced search"""
    
    def __init__(self):
        self.client = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            http_auth=(settings.elasticsearch_user, settings.elasticsearch_password)
        )
        self.index_prefix = f"legalai_{settings.environment}"
    
    async def create_indices(self):
        """Create Elasticsearch indices with mappings"""
        
        # Document index mapping
        document_mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "organization_id": {"type": "integer"},
                    "filename": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "document_type": {"type": "keyword"},
                    "parties": {"type": "keyword"},
                    "key_dates": {"type": "date"},
                    "obligations": {"type": "text"},
                    "risks": {"type": "text"},
                    "summary": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "uploaded_by": {"type": "integer"},
                    "file_size": {"type": "long"},
                    "page_count": {"type": "integer"}
                }
            },
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "legal_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop",
                                "legal_synonyms",
                                "snowball"
                            ]
                        }
                    },
                    "filter": {
                        "legal_synonyms": {
                            "type": "synonym",
                            "synonyms": [
                                "agreement,contract",
                                "party,parties",
                                "shall,will,must",
                                "breach,violation,default"
                            ]
                        }
                    }
                }
            }
        }
        
        # Create document index
        await self.client.indices.create(
            index=f"{self.index_prefix}_documents",
            body=document_mapping,
            ignore=400  # Ignore if already exists
        )
    
    async def index_document(self, document: Document):
        """Index a single document"""
        doc_data = {
            "id": document.id,
            "organization_id": document.organization_id,
            "filename": document.filename,
            "content": document.content,
            "document_type": document.document_type,
            "parties": document.extracted_entities.get("parties", []) if document.extracted_entities else [],
            "key_dates": document.extracted_entities.get("dates", []) if document.extracted_entities else [],
            "obligations": document.extracted_entities.get("obligations", []) if document.extracted_entities else [],
            "risks": document.extracted_entities.get("risks", []) if document.extracted_entities else [],
            "summary": document.ai_analysis.get("summary", "") if document.ai_analysis else "",
            "tags": document.tags if document.tags else [],
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "uploaded_by": document.uploaded_by_id,
            "file_size": document.file_size,
            "page_count": document.metadata.get("page_count", 0) if document.metadata else 0
        }
        
        await self.client.index(
            index=f"{self.index_prefix}_documents",
            id=document.id,
            body=doc_data
        )
    
    async def bulk_index_documents(self, documents: List[Document]):
        """Bulk index multiple documents"""
        actions = []
        for doc in documents:
            actions.append({
                "_index": f"{self.index_prefix}_documents",
                "_id": doc.id,
                "_source": {
                    "id": doc.id,
                    "organization_id": doc.organization_id,
                    "filename": doc.filename,
                    "content": doc.content,
                    "document_type": doc.document_type,
                    # ... other fields ...
                }
            })
        
        await async_bulk(self.client, actions)
    
    async def search_documents(
        self,
        organization_id: int,
        query: str,
        filters: Dict[str, Any] = None,
        from_: int = 0,
        size: int = 20,
        sort: List[Dict] = None
    ) -> Dict[str, Any]:
        """Search documents with advanced features"""
        
        # Build query
        must_clauses = [
            {"term": {"organization_id": organization_id}}
        ]
        
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "filename^2",
                        "content",
                        "summary",
                        "parties",
                        "obligations",
                        "risks"
                    ],
                    "type": "best_fields",
                    "operator": "or",
                    "fuzziness": "AUTO"
                }
            })
        
        # Add filters
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    must_clauses.append({
                        "terms": {field: value}
                    })
                elif isinstance(value, dict) and "from" in value:
                    # Date range
                    must_clauses.append({
                        "range": {
                            field: {
                                "gte": value.get("from"),
                                "lte": value.get("to")
                            }
                        }
                    })
                else:
                    must_clauses.append({
                        "term": {field: value}
                    })
        
        # Build search body
        search_body = {
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "from": from_,
            "size": size,
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 3
                    }
                }
            },
            "aggs": {
                "document_types": {
                    "terms": {"field": "document_type"}
                },
                "date_histogram": {
                    "date_histogram": {
                        "field": "created_at",
                        "interval": "month"
                    }
                }
            }
        }
        
        if sort:
            search_body["sort"] = sort
        else:
            search_body["sort"] = [
                "_score",
                {"created_at": {"order": "desc"}}
            ]
        
        # Execute search
        response = await self.client.search(
            index=f"{self.index_prefix}_documents",
            body=search_body
        )
        
        # Format response
        return {
            "total": response["hits"]["total"]["value"],
            "documents": [
                {
                    **hit["_source"],
                    "score": hit["_score"],
                    "highlights": hit.get("highlight", {})
                }
                for hit in response["hits"]["hits"]
            ],
            "aggregations": response.get("aggregations", {}),
            "took": response["took"]
        }
    
    async def suggest_search_terms(
        self,
        organization_id: int,
        prefix: str
    ) -> List[str]:
        """Get search suggestions"""
        suggest_body = {
            "suggest": {
                "text": prefix,
                "completion": {
                    "field": "filename.keyword",
                    "size": 10,
                    "fuzzy": {
                        "fuzziness": "AUTO"
                    },
                    "contexts": {
                        "organization": organization_id
                    }
                }
            }
        }
        
        response = await self.client.search(
            index=f"{self.index_prefix}_documents",
            body=suggest_body
        )
        
        suggestions = []
        for suggestion in response.get("suggest", {}).get("completion", []):
            for option in suggestion.get("options", []):
                suggestions.append(option["text"])
        
        return suggestions

# Initialize service
es_service = ElasticsearchService()
```

#### Step 2: Search API Routes
```python
# backend/search/routes.py
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from .elasticsearch_config import es_service

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/documents")
async def search_documents(
    q: Optional[str] = Query(None, description="Search query"),
    document_type: Optional[List[str]] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    parties: Optional[List[str]] = Query(None),
    tags: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("relevance", regex="^(relevance|date|name)$"),
    current_user: User = Depends(get_current_user)
):
    """Advanced document search"""
    
    # Build filters
    filters = {}
    if document_type:
        filters["document_type"] = document_type
    if date_from or date_to:
        filters["created_at"] = {
            "from": date_from.isoformat() if date_from else "1970-01-01",
            "to": date_to.isoformat() if date_to else datetime.utcnow().isoformat()
        }
    if parties:
        filters["parties"] = parties
    if tags:
        filters["tags"] = tags
    
    # Build sort
    sort = []
    if sort_by == "date":
        sort.append({"created_at": {"order": "desc"}})
    elif sort_by == "name":
        sort.append({"filename.keyword": {"order": "asc"}})
    
    # Search
    results = await es_service.search_documents(
        organization_id=current_user.organization_id,
        query=q,
        filters=filters,
        from_=(page - 1) * page_size,
        size=page_size,
        sort=sort
    )
    
    return {
        "results": results["documents"],
        "total": results["total"],
        "page": page,
        "pages": (results["total"] + page_size - 1) // page_size,
        "aggregations": results["aggregations"],
        "search_time_ms": results["took"]
    }

@router.get("/suggest")
async def search_suggestions(
    prefix: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user)
):
    """Get search suggestions"""
    suggestions = await es_service.suggest_search_terms(
        organization_id=current_user.organization_id,
        prefix=prefix
    )
    
    return {"suggestions": suggestions}

@router.post("/reindex")
async def reindex_documents(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reindex all documents (admin only)"""
    
    # Get all documents for organization
    documents = db.query(Document).filter(
        Document.organization_id == current_user.organization_id
    ).all()
    
    # Bulk index
    await es_service.bulk_index_documents(documents)
    
    return {
        "message": f"Reindexed {len(documents)} documents",
        "count": len(documents)
    }
```

---

## Week 11-16: Microservices & Scale 🔵

### TASK-BE-010: Microservices Architecture 🔵
**Owner:** BE-01, BE-04  
**Duration:** 40 hours  
**Dependencies:** All previous tasks  
**Labels:** `architecture`, `scale`

#### Step 1: Service Extraction Plan
```yaml
# backend/microservices/docker-compose.services.yml
version: '3.8'

services:
  # API Gateway
  kong:
    image: kong:latest
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /kong/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
    ports:
      - "8000:8000"
      - "8001:8001"
    volumes:
      - ./kong/kong.yml:/kong/kong.yml
    networks:
      - legalai

  # Auth Service
  auth-service:
    build: ./services/auth
    environment:
      DATABASE_URL: ${AUTH_DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    networks:
      - legalai
    deploy:
      replicas: 2

  # Document Service
  document-service:
    build: ./services/document
    environment:
      DATABASE_URL: ${DOCUMENT_DATABASE_URL}
      STORAGE_BACKEND: s3
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: ${S3_BUCKET}
    networks:
      - legalai
    deploy:
      replicas: 3

  # AI Service
  ai-service:
    build: ./services/ai
    environment:
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      REDIS_URL: ${REDIS_URL}
    networks:
      - legalai
    deploy:
      replicas: 2

  # Search Service
  search-service:
    build: ./services/search
    environment:
      ELASTICSEARCH_URL: ${ELASTICSEARCH_URL}
      DATABASE_URL: ${SEARCH_DATABASE_URL}
    networks:
      - legalai

  # Message Queue
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - legalai

  # Service Registry
  consul:
    image: consul:latest
    ports:
      - "8500:8500"
    networks:
      - legalai

networks:
  legalai:
    driver: overlay
```

#### Step 2: Message Queue Integration
```python
# backend/messaging/rabbitmq_config.py
import pika
import json
from typing import Callable, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MessageQueue:
    """RabbitMQ message queue implementation"""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.connection = None
        self.channel = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._connect()
    
    def _connect(self):
        """Establish connection to RabbitMQ"""
        parameters = pika.URLParameters(self.connection_url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        
        # Declare exchanges
        self.channel.exchange_declare(
            exchange='legalai.events',
            exchange_type='topic',
            durable=True
        )
        
        # Declare queues
        queues = [
            'document.processing',
            'ai.analysis',
            'email.notifications',
            'search.indexing'
        ]
        
        for queue in queues:
            self.channel.queue_declare(queue=queue, durable=True)
    
    def publish(
        self,
        routing_key: str,
        message: Dict[str, Any],
        exchange: str = 'legalai.events'
    ):
        """Publish message to queue"""
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type='application/json'
            )
        )
    
    def consume(
        self,
        queue: str,
        callback: Callable,
        auto_ack: bool = False
    ):
        """Consume messages from queue"""
        def wrapper(ch, method, properties, body):
            try:
                message = json.loads(body)
                callback(message)
                
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if not auto_ack:
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True
                    )
        
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=queue,
            on_message_callback=wrapper,
            auto_ack=auto_ack
        )
        
        self.channel.start_consuming()
    
    async def publish_async(
        self,
        routing_key: str,
        message: Dict[str, Any]
    ):
        """Async wrapper for publishing"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.publish,
            routing_key,
            message
        )

# Document processing worker
class DocumentWorker:
    """Worker for processing documents"""
    
    def __init__(self, mq: MessageQueue):
        self.mq = mq
    
    def process_document(self, message: Dict[str, Any]):
        """Process document message"""
        document_id = message['document_id']
        action = message['action']
        
        try:
            if action == 'extract_text':
                # Extract text from document
                pass
            elif action == 'analyze':
                # Send to AI service
                self.mq.publish(
                    'ai.analysis.request',
                    {
                        'document_id': document_id,
                        'content': message['content'],
                        'type': message['document_type']
                    }
                )
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            
            # Send to dead letter queue
            self.mq.publish(
                'document.processing.failed',
                {
                    'document_id': document_id,
                    'error': str(e),
                    'original_message': message
                }
            )
    
    def start(self):
        """Start consuming messages"""
        self.mq.consume(
            'document.processing',
            self.process_document
        )
```

---

## Summary & Verification

### Backend Team Deliverables Checklist

#### Week 1-2 ✓
- [ ] All hardcoded secrets removed
- [ ] Environment configuration implemented
- [ ] Git history cleaned
- [ ] Authentication working end-to-end
- [ ] Database migrations completed

#### Week 3-4 ✓
- [ ] Unit tests >80% coverage
- [ ] Integration tests passing
- [ ] CI/CD pipeline deployed
- [ ] Performance tests completed

#### Week 5-6 ✓
- [ ] Redis caching implemented
- [ ] Database optimized
- [ ] Monitoring dashboard live
- [ ] Alerts configured

#### Week 7-10 ✓
- [ ] WebSocket real-time updates
- [ ] Elasticsearch search
- [ ] Enterprise features complete

#### Week 11-16 ✓
- [ ] Microservices architecture
- [ ] Message queue integration
- [ ] Auto-scaling configured
- [ ] Production deployment

### Critical Success Metrics
- API response time: <100ms (p95)
- Test coverage: >80%
- Zero hardcoded secrets
- All auth endpoints secured
- Monitoring alerts functional

This completes the backend team task instructions. Each task has clear ownership, dependencies, and verification steps.