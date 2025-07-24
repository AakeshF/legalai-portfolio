# Backend Integration Guide

## Overview

All mock API calls have been replaced with real backend integration. The application now connects to actual backend APIs for authentication, security features, and data management.

## Configuration

### Environment Variables

Create a `.env` file in the root directory based on `.env.example`:

```env
# Backend API Configuration
VITE_API_URL=http://localhost:8000/api

# Environment
VITE_ENV=development

# Optional: Feature Flags
VITE_ENABLE_2FA=true
VITE_ENABLE_AUDIT_LOGS=true
VITE_ENABLE_DATA_EXPORT=true
```

### API Configuration

The API configuration is centralized in `src/config/api.config.ts`:

- **Base URL**: Configurable via `VITE_API_URL` environment variable
- **Timeout**: 30 seconds default
- **Retry**: 3 attempts with exponential backoff
- **Authentication**: JWT tokens automatically included in all requests

## API Endpoints

### Authentication (`/auth/*`)
- `POST /auth/login` - User login
- `POST /auth/register` - New organization registration
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/me` - Get current user profile
- `PATCH /auth/profile` - Update user profile
- `POST /auth/password` - Change password

### Security (`/security/*`)
- `GET /security/events` - Get security events
- `GET /security/metrics` - Get security metrics
- `GET /security/status` - Get security status
- `GET /security/alerts` - Get security alerts
- `GET /security/notification-preferences` - Get notification preferences
- `PATCH /security/notification-preferences` - Update notification preferences

### Two-Factor Authentication (`/security/2fa/*`)
- `GET /security/2fa/status` - Get 2FA status
- `POST /security/2fa/setup` - Setup 2FA
- `POST /security/2fa/verify` - Verify 2FA code
- `POST /security/2fa/disable` - Disable 2FA
- `GET /security/2fa/backup-codes` - Get backup codes
- `POST /security/2fa/backup-codes/regenerate` - Regenerate backup codes

### Privacy & Data Management (`/privacy/*`)
- `GET /privacy/settings` - Get privacy settings
- `PATCH /privacy/settings` - Update privacy settings
- `GET /privacy/compliance` - Get compliance status
- `POST /privacy/data/export` - Request data export
- `GET /privacy/data/exports` - Get export history
- `GET /privacy/data/export/download/:id` - Download export
- `POST /privacy/data/deletion/initiate` - Initiate account deletion
- `POST /privacy/data/deletion/confirm` - Confirm account deletion

### Organization Management (`/organization/*`)
- `GET /organization` - Get organization info
- `GET /organization/users` - Get organization users
- `POST /organization/users/invite` - Invite user
- `PATCH /organization/users/:userId/role` - Update user role
- `DELETE /organization/users/:userId` - Remove user
- `GET /organization/settings` - Get organization settings
- `PATCH /organization/settings` - Update organization settings

### Organization Security (`/organization/security/*`)
- `GET /organization/security/settings` - Get security settings
- `PATCH /organization/security/settings` - Update security settings
- `GET /organization/security/ip-restrictions` - Get IP restrictions
- `POST /organization/security/ip-restrictions` - Add IP restriction
- `DELETE /organization/security/ip-restrictions/:id` - Remove IP restriction

### Audit Logs (`/audit/*`)
- `GET /audit/logs` - Get audit logs (with query parameters)
- `GET /audit/export` - Export audit logs
- `GET /audit/logs/:id` - Get audit log details

### Documents (`/documents/*`)
- `GET /documents` - List documents
- `POST /documents/upload` - Upload document
- `GET /documents/:id` - Get document details
- `DELETE /documents/:id` - Delete document
- `GET /documents/:id/status` - Get document status

### Chat (`/chat/*`)
- `POST /chat` - Send chat message
- `GET /chat/history` - Get chat history
- `GET /chat/session/:sessionId` - Get session messages

## Authentication Flow

1. **Login/Register**: User credentials are sent to backend
2. **JWT Token**: Backend returns JWT token with expiration
3. **Token Storage**: Token stored in localStorage with expiry
4. **Auto-Refresh**: Token refreshed 5 minutes before expiry
5. **API Calls**: Token automatically included in Authorization header

## Error Handling

All API calls include comprehensive error handling:

- **Network Errors**: Detected and user notified
- **Authentication Errors**: Redirect to login
- **API Errors**: Display user-friendly messages
- **Retry Logic**: Automatic retry with exponential backoff

## Security Features

- **HTTPS**: All API calls use HTTPS in production
- **JWT Tokens**: Secure token-based authentication
- **CORS**: Proper CORS headers required from backend
- **Rate Limiting**: Backend should implement rate limiting
- **Input Validation**: Both frontend and backend validation

## Usage Examples

### Making API Calls

```typescript
import { api } from '../utils/api';
import { API_ENDPOINTS } from '../config/api.config';

// GET request
const response = await api.get(API_ENDPOINTS.security.events);
const events = response.data;

// POST request
const response = await api.post(API_ENDPOINTS.auth.login, {
  email: '[email@example.com]',
  password: 'password'
});

// With path parameters
import { buildUrl } from '../config/api.config';
const url = buildUrl(API_ENDPOINTS.organization.updateUserRole, { userId: '123' });
const response = await api.patch(url, { role: 'admin' });
```

### Organization Context

All API calls that need organization context automatically include the organization ID:

```typescript
// In components
const { organization } = useAuth();

const response = await api.post(API_ENDPOINTS.documents.upload, formData, {
  headers: {
    'X-Organization-ID': organization?.id
  }
});
```

## Backend Requirements

The backend must implement:

1. **JWT Authentication**: Issue and validate JWT tokens
2. **Multi-tenancy**: Filter data by organization
3. **Role-based Access**: Enforce user permissions
4. **Audit Logging**: Track all security-relevant actions
5. **Rate Limiting**: Prevent API abuse
6. **CORS Headers**: Allow frontend domain
7. **Error Responses**: Consistent error format

## Testing

To test the integration:

1. Start the backend server on `http://localhost:8000`
2. Configure `.env` with the backend URL
3. Run `npm run dev` to start the frontend
4. Test authentication flow
5. Verify all features work with real data

## Production Deployment

1. Set `VITE_API_URL` to production backend URL
2. Ensure HTTPS is enabled
3. Configure proper CORS headers
4. Enable rate limiting
5. Set up monitoring and logging
6. Configure backup and recovery

## Troubleshooting

### Common Issues

1. **CORS Errors**: Backend must allow frontend origin
2. **401 Unauthorized**: Token expired or invalid
3. **Network Errors**: Check backend is running
4. **Empty Responses**: Ensure backend returns proper JSON

### Debug Mode

Enable debug logging:

```typescript
// In src/utils/api.ts
const DEBUG = import.meta.env.VITE_ENV === 'development';
if (DEBUG) console.log('API Request:', url, options);
```