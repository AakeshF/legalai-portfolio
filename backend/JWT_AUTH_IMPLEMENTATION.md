# JWT Authentication Implementation Guide

## Overview

A comprehensive JWT-based authentication system with organization scoping has been implemented for the Legal AI Backend. The system uses short-lived access tokens (2 hours) and long-lived refresh tokens (7 days) with secure password hashing and email functionality.

## Implementation Details

### 1. JWT Token System

**Token Types:**
- **Access Token**: 2-hour expiry, contains user and organization info
- **Refresh Token**: 7-day expiry, used to generate new access tokens
- **Password Reset Token**: 30-minute expiry, for password reset links

**Token Payload Structure:**
```json
{
  "sub": "user_id",
  "email": "[email@example.com]",
  "org_id": "organization_id",
  "role": "attorney|admin|paralegal",
  "type": "access|refresh|password_reset",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### 2. Authentication Endpoints

All endpoints are under `/api/auth`:

#### POST `/api/auth/register`
Creates new organization with admin user.
```json
Request:
{
  "organization_name": "Smith Law Firm",
  "billing_email": "[email@example.com]",
  "admin_email": "[email@example.com]",
  "admin_password": "SecurePass123!",
  "admin_first_name": "John",
  "admin_last_name": "Smith"
}

Response:
{
  "organization": {...},
  "user": {...},
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### POST `/api/auth/login`
User login with email/password.
```json
Request:
{
  "email": "[email@example.com]",
  "password": "password123"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### POST `/api/auth/refresh`
Refresh expired access token.
```json
Request:
{
  "refresh_token": "eyJ..."
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### POST `/api/auth/forgot-password`
Request password reset email.
```json
Request:
{
  "email": "[email@example.com]"
}

Response:
{
  "message": "If the email exists, a password reset link has been sent."
}
```

#### POST `/api/auth/reset-password`
Reset password with token.
```json
Request:
{
  "token": "eyJ...",
  "new_password": "NewSecurePass123!"
}

Response:
{
  "message": "Password reset successful."
}
```

#### GET `/api/auth/me`
Get current user profile.
```http
Authorization: Bearer eyJ...
```

#### PUT `/api/auth/profile`
Update user profile.
```json
Request:
{
  "first_name": "John",
  "last_name": "Doe",
  "current_password": "old_password",  // Required if changing password
  "new_password": "new_password"       // Optional
}
```

### 3. Authentication Middleware

The `AuthenticationMiddleware` automatically:
- Extracts JWT from Authorization header
- Validates token and checks expiry
- Adds user and organization to `request.state`
- Filters all queries by organization
- Returns 401 for invalid/expired tokens

**Public Endpoints** (no auth required):
- `/health`
- `/docs`, `/redoc`, `/openapi.json`
- `/api/auth/*` endpoints

**Request Context:**
After authentication, these are available in all endpoints:
- `request.state.user` - Current User object
- `request.state.organization` - Current Organization object
- `request.state.user_id` - User ID string
- `request.state.organization_id` - Organization ID string
- `request.state.user_role` - User role string

### 4. Security Features

#### Password Security
- Bcrypt hashing with 12 rounds
- Password requirements:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number

#### Rate Limiting
- Authentication endpoints: 20 requests/minute per IP
- Configurable per endpoint
- Returns 429 with Retry-After header

#### Email Security
- Password reset links expire in 30 minutes
- Secure token generation using secrets module
- HTML and plain text email templates
- No user enumeration (same response for all emails)

### 5. Email Configuration

Add to `.env`:
```env
# Email settings (example for Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=[email@example.com]
SMTP_PASSWORD=your-app-password
EMAIL_FROM=[email@example.com]
FRONTEND_URL=https://yourdomain.com
```

### 6. Frontend Integration

#### Storing Tokens
```javascript
// After login/register
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);
```

#### Making Authenticated Requests
```javascript
const response = await fetch('/api/documents', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  }
});

if (response.status === 401) {
  // Token expired, try refresh
  await refreshAccessToken();
}
```

#### Token Refresh Logic
```javascript
async function refreshAccessToken() {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      refresh_token: localStorage.getItem('refresh_token')
    })
  });
  
  if (response.ok) {
    const tokens = await response.json();
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    return tokens.access_token;
  } else {
    // Refresh failed, redirect to login
    window.location.href = '/login';
  }
}
```

### 7. Using Authentication in Endpoints

All endpoints now have organization context:

```python
from auth_middleware import get_current_user, get_current_organization

@app.get("/api/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    # Documents are automatically filtered by organization
    documents = db.query(Document).filter(
        Document.organization_id == current_org.id
    ).all()
```

### 8. Security Best Practices

1. **JWT Secret**: Use a strong, random secret key
   ```bash
   openssl rand -hex 32
   ```

2. **HTTPS Only**: Always use HTTPS in production

3. **Secure Headers**: Added by middleware automatically
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block

4. **Token Storage**: 
   - Store in httpOnly cookies for web apps
   - Use secure storage for mobile apps
   - Never store in plain localStorage for sensitive apps

5. **Logout**: Clear tokens on client and optionally blacklist on server

## Testing

### Test Registration
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "Test Law Firm",
    "billing_email": "[email@example.com]",
    "admin_email": "[email@example.com]",
    "admin_password": "TestPass123!",
    "admin_first_name": "Test",
    "admin_last_name": "Admin"
  }'
```

### Test Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "[email@example.com]",
    "password": "TestPass123!"
  }'
```

### Test Authenticated Request
```bash
# Use the access_token from login response
curl -X GET http://localhost:8000/api/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Monitoring

The system logs:
- All authentication attempts
- Failed login attempts (for security monitoring)
- Token refresh events
- Password reset requests
- Rate limit violations

Check logs for patterns:
```python
# Failed logins from same IP
grep "Login failed" app.log | grep "IP_ADDRESS"

# Rate limit violations
grep "Rate limit exceeded" app.log
```

## Troubleshooting

### Common Issues

1. **"Invalid or expired token"**
   - Token has expired (2 hours for access token)
   - Use refresh token to get new access token

2. **"Organization is not active"**
   - Organization has been deactivated
   - Contact admin to reactivate

3. **"Rate limit exceeded"**
   - Too many requests in short time
   - Wait 60 seconds before retrying

4. **Email not sending**
   - Check SMTP configuration in .env
   - Verify app password (not regular password) for Gmail
   - Check logs for SMTP errors

## Next Steps

1. **Add Social Login**: OAuth2 with Google/Microsoft
2. **2FA Support**: Time-based OTP for enhanced security
3. **Session Management**: View/revoke active sessions
4. **Audit Logging**: Track all user actions
5. **IP Whitelisting**: Restrict access by IP for enterprises