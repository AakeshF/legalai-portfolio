# Multi-Tenancy Setup Guide

## Overview

Simple multi-tenancy support has been added to the Legal AI Backend for small law firms (2-10 attorneys). This guide explains the changes and how to use the new features.

## What's New

### 1. New Database Models

**Organization Model** (`models.py`):
- Represents a law firm or legal practice
- Fields: name, subscription_tier, billing_email
- Each organization is isolated from others

**User Model** (`models.py`):
- Represents attorneys, admins, and paralegals
- Fields: email, password_hash, first_name, last_name, role
- Each user belongs to one organization

### 2. Updated Models

**Document Model**:
- Added `organization_id` - links documents to organizations
- Added `uploaded_by_id` - tracks which user uploaded the document

**ChatSession Model**:
- Added `organization_id` - links chat sessions to organizations
- Added `user_id` - tracks which user created the session

### 3. Authentication System

**Password Security** (`auth_utils.py`):
- Bcrypt password hashing
- JWT token generation
- Password validation (8+ chars, uppercase, lowercase, number)
- Email validation

**Auth Endpoints** (`auth_routes.py`):
- `POST /api/auth/register` - Register new organization with admin user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info

## Setup Instructions

### 1. Install Dependencies

```bash
pip install passlib[bcrypt] python-jose[cryptography]
```

### 2. Update Environment Variables

Add to your `.env` file:
```env
JWT_SECRET_KEY=your-very-secure-secret-key-change-this
```

### 3. Run Database Migration

```bash
python migrate_add_multitenancy.py
```

This will:
- Create new tables (organizations, users)
- Add organization_id columns to existing tables
- Create a default organization for existing data
- Create a default admin user: `[email@example.com]` / `Admin123!`
- Add necessary indexes

### 4. Test the System

```bash
# Test registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "Smith & Associates Law",
    "billing_email": "[email@example.com]",
    "admin_email": "[email@example.com]",
    "admin_password": "SecurePass123!",
    "admin_first_name": "John",
    "admin_last_name": "Smith"
  }'

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "[email@example.com]",
    "password": "Admin123!"
  }'

# Use the token from login response
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Next Steps

### 1. Update Existing Endpoints

To secure existing endpoints, add the authentication dependency:

```python
from auth_routes import get_current_user_dependency
from models import User

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    # Now you have current_user with organization_id
    # Filter all queries by current_user.organization_id
```

### 2. Filter Queries by Organization

Always filter database queries by organization:

```python
# Get documents for current organization only
documents = db.query(Document).filter(
    Document.organization_id == current_user.organization_id
).all()

# Create new document with organization
new_doc = Document(
    filename=file.filename,
    organization_id=current_user.organization_id,
    uploaded_by_id=current_user.id,
    # ... other fields
)
```

### 3. Add User Management Endpoints

Consider adding these endpoints:

```python
# List users in organization (admin only)
@app.get("/api/users")
async def list_users(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(
        User.organization_id == current_user.organization_id
    ).all()
    return users

# Create new user (admin only)
@app.post("/api/users")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Create user in same organization
    new_user = User(
        organization_id=current_user.organization_id,
        # ... other fields
    )
```

## Security Considerations

1. **Always validate organization access** - Users should only see their organization's data
2. **Use HTTPS in production** - JWT tokens must be transmitted securely
3. **Rotate JWT secret keys** - Change the JWT_SECRET_KEY periodically
4. **Implement token expiration** - Tokens currently expire after 24 hours
5. **Add rate limiting** - Prevent brute force attacks on login endpoint

## Subscription Tiers

The system supports three subscription tiers:
- **basic**: Default tier for new organizations
- **pro**: Enhanced features (implement as needed)
- **enterprise**: Full features (implement as needed)

You can check the tier in your code:

```python
if current_user.organization.subscription_tier == "enterprise":
    # Allow enterprise features
    pass
```

## Migration Notes

- All existing data is assigned to a "Default Organization"
- The default admin password is `Admin123!` - change this immediately
- Organization IDs are UUIDs for security
- Passwords are hashed with bcrypt (cannot be reversed)

## Support

For issues or questions:
1. Check the migration script output for errors
2. Verify JWT_SECRET_KEY is set in environment
3. Ensure all dependencies are installed
4. Check database connection settings