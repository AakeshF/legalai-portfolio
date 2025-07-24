# Afternoon Tasks - Post-Lunch Sprint

**Time:** 1:00 PM - 6:00 PM  
**Goal:** Complete test coverage and prepare for performance optimization

---

## Backend Team Tasks

### 1. Test Suite Implementation (2:00 PM - 5:00 PM)

#### A. Create Test Structure (30 mins)
```bash
backend/tests/
├── __init__.py
├── conftest.py          # Shared fixtures and test DB setup
├── test_auth.py         # Authentication tests
├── test_documents.py    # Document CRUD tests
├── test_chat.py         # Chat functionality tests
├── test_ai_service.py   # AI service mocking
└── test_integration.py  # End-to-end flows
```

#### B. Priority Test Files

**1. conftest.py** - Test Configuration
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import get_db
from models import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    # Create test user and return auth headers
    response = client.post("/api/auth/register", json={
        "email": "[email@example.com]",
        "password": "TestPass123!",
        "full_name": "Test User",
        "organization_name": "Test Org"
    })
    login_response = client.post("/api/auth/login", json={
        "email": "[email@example.com]",
        "password": "TestPass123!"
    })
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

**2. test_auth.py** - Critical Auth Tests
```python
def test_user_registration(client):
    # Test successful registration
    # Test duplicate email
    # Test invalid data

def test_user_login(client):
    # Test successful login
    # Test invalid credentials
    # Test token format

def test_token_refresh(client):
    # Test refresh token flow
    # Test expired refresh token

def test_protected_routes(client):
    # Test access without token (401)
    # Test access with valid token (200)
    # Test access with expired token
```

**3. test_documents.py** - Document Operations
```python
def test_document_upload(client, auth_headers):
    # Test PDF upload
    # Test file size limits
    # Test invalid file types

def test_document_list(client, auth_headers):
    # Test pagination
    # Test filtering
    # Test organization isolation

def test_document_processing(client, auth_headers, mocker):
    # Mock AI service
    # Test processing pipeline
    # Test error handling
```

#### C. Run Coverage Report (5:00 PM)
```bash
pytest --cov=. --cov-report=html --cov-report=term
# Check coverage is >80%
# Focus on untested critical paths
```

### 2. Redis Caching Preparation (5:00 PM - 6:00 PM)

#### A. Install Redis Dependencies
```bash
pip install redis aioredis
pip freeze > requirements.txt
```

#### B. Create Cache Service
```python
# services/cache_service.py
from typing import Optional, Any
import redis
import json
from config import settings

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url)
        
    async def get(self, key: str) -> Optional[Any]:
        value = self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        self.redis.setex(key, ttl, json.dumps(value))
    
    async def delete(self, key: str):
        self.redis.delete(key)

cache_service = CacheService()
```

---

## Frontend Team Tasks

### 1. Component Test Suite (2:00 PM - 5:00 PM)

#### A. Setup Test Environment (30 mins)
```bash
# Install missing test dependencies
npm install -D @testing-library/user-event msw @mswjs/data

# Create test structure
src/
├── __tests__/
│   ├── setup.ts
│   ├── utils.tsx
│   └── mocks/
│       ├── handlers.ts
│       └── server.ts
├── components/__tests__/
├── services/__tests__/
└── hooks/__tests__/
```

#### B. Priority Test Files

**1. Mock Service Worker Setup**
```typescript
// src/__tests__/mocks/handlers.ts
import { rest } from 'msw';

export const handlers = [
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(ctx.json({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh',
      user: { id: 1, email: '[email@example.com]' }
    }));
  }),
  
  rest.get('/api/documents', (req, res, ctx) => {
    return res(ctx.json({
      documents: [],
      total: 0
    }));
  }),
];

// src/__tests__/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

**2. Critical Component Tests**
```typescript
// src/components/auth/__tests__/LoginForm.test.tsx
- Test form validation
- Test successful login flow
- Test error handling
- Test loading states

// src/components/documents/__tests__/DocumentList.test.tsx
- Test empty state
- Test document rendering
- Test pagination
- Test filtering

// src/services/__tests__/api.test.ts
- Test auth header injection
- Test token refresh flow
- Test error handling
```

#### C. Run Coverage Report (5:00 PM)
```bash
npm run test -- --coverage
# Ensure >80% coverage
# Focus on critical user paths
```

### 2. Performance Prep (5:00 PM - 6:00 PM)

#### A. Install Performance Tools
```bash
npm install -D @types/react-window react-window
npm install -D rollup-plugin-visualizer
```

#### B. Identify Optimization Points
- Mark components for lazy loading
- Identify large lists for virtualization
- Plan code splitting strategy
- Review bundle size

---

## 6:00 PM Sync Meeting

### Agenda
1. **Coverage Reports** (10 mins)
   - Backend: Show coverage percentage
   - Frontend: Show coverage percentage
   - Identify any gaps

2. **Integration Test** (15 mins)
   - Run full auth flow together
   - Test document upload/retrieval
   - Verify error handling

3. **Tomorrow's Plan** (5 mins)
   - Backend: Redis caching implementation
   - Frontend: Performance optimizations
   - Both: WebSocket planning

### Success Criteria
- [ ] Backend coverage ≥ 80%
- [ ] Frontend coverage ≥ 80%
- [ ] All auth flows working
- [ ] CI/CD pipeline green
- [ ] Ready for performance work

---

## Quick Reference Commands

### Backend
```bash
# Run tests with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Check coverage report
open htmlcov/index.html
```

### Frontend
```bash
# Run tests with coverage
npm run test -- --coverage

# Run in watch mode
npm run test -- --watch

# Check coverage report
open coverage/lcov-report/index.html
```

### Docker Commands
```bash
# Run all services
docker-compose up

# Run tests in container
docker-compose exec backend pytest
docker-compose exec frontend npm test
```

**Remember:** Quality over speed. Better to have 70% well-written tests than 80% flaky tests.