# Frontend Integration Guide - Legal AI Anonymization System

## Backend Update Summary
Great news! The backend team has completed all 14 planned components with a production-ready implementation. The backend now provides a comprehensive security pipeline with a simplified integration approach.

## Key Integration Change: Unified Endpoint

The backend has implemented a **single unified endpoint** that handles the entire security pipeline automatically:

```
POST /api/ai/integrated/process
```

This endpoint handles:
- ✅ Automatic anonymization
- ✅ Consent checking
- ✅ Security enforcement
- ✅ Model routing
- ✅ Admin review workflow

## Frontend Integration Requirements

### 1. Update the Main API Call

Replace the current multi-step process with a single call to the integrated endpoint:

```typescript
// In src/services/anonymization-api.ts
export async function processPromptIntegrated(prompt: string, context?: any) {
  const response = await fetch('/api/ai/integrated/process', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('authToken')}`
    },
    body: JSON.stringify({ prompt, context })
  });
  
  const data = await response.json();
  return data;
}
```

### 2. Handle Response Statuses

The integrated endpoint returns different statuses that need specific handling:

```typescript
interface IntegratedResponse {
  status: 'success' | 'consent_required' | 'pending_review' | 'blocked';
  data?: any;
  message?: string;
  consentDetails?: ConsentRequirement;
  reviewId?: string;
}

// Handle each status:
switch (response.status) {
  case 'success':
    // Display AI response
    break;
    
  case 'consent_required':
    // Show consent modal with response.consentDetails
    // Re-submit with consent after user approval
    break;
    
  case 'pending_review':
    // Show review status component
    // Poll using response.reviewId
    break;
    
  case 'blocked':
    // Show security warning
    // Display response.message
    break;
}
```

### 3. Update Components to Use Integrated Flow

#### In `PromptAnonymizer.tsx`:
- Keep the client-side preview functionality for user experience
- Submit to the integrated endpoint instead of separate endpoints
- The backend will re-validate and enforce security policies

#### In `ChatInterface.tsx`:
- Add integration with the anonymization flow
- Handle the different response statuses appropriately

#### In `AnonymizationPage.tsx`:
- Update the submission flow to use the integrated endpoint
- Ensure proper status handling for all response types

### 4. Simplify the API Service

Since the backend handles everything, we can simplify our API service:

```typescript
// src/services/anonymization-api.ts - Simplified version
export class AnonymizationAPI {
  static async processPrompt(prompt: string, options?: {
    model?: string;
    context?: any;
    consent?: ConsentData;
  }): Promise<IntegratedResponse> {
    return this.request('/api/ai/integrated/process', {
      method: 'POST',
      body: JSON.stringify({
        prompt,
        ...options
      })
    });
  }
  
  // Keep these for UI features:
  static async getSettings(userId: string) { /* ... */ }
  static async updateSettings(userId: string, settings: any) { /* ... */ }
  static async getSubmissionHistory(userId: string) { /* ... */ }
}
```

## What Stays the Same

These frontend components remain valuable for UX:
- **Client-side anonymization preview** - Instant feedback for users
- **Consent modal** - Progressive disclosure UI
- **Admin dashboard** - For reviewing pending prompts
- **Settings management** - User preferences
- **Audit log viewer** - Compliance tracking

## Next Steps

1. **Update API calls** to use `/api/ai/integrated/process`
2. **Test response handling** for all status types
3. **Verify consent flow** works with backend requirements
4. **Ensure admin features** connect to backend properly
5. **Test end-to-end** security pipeline

## Testing Checklist

- [ ] Submit clean prompt → Should get 'success' status
- [ ] Submit prompt with sensitive data → Should get 'consent_required'
- [ ] Submit with consent → Should process or go to 'pending_review'
- [ ] Admin approve/reject → Should update status appropriately
- [ ] Test rate limiting → Should get appropriate error
- [ ] Verify audit logs → Should show all actions

## Security Notes

The backend enforces all security policies server-side, so:
- Client-side redaction is for UX only
- All security decisions are made by the backend
- The frontend should gracefully handle all security responses
- Never bypass security checks client-side

## Support

The backend team has confirmed all routes are properly registered and tested. If you encounter any issues with the integrated endpoint, the response will include helpful error messages to guide integration.

---

The system is designed to provide maximum security while maintaining a smooth user experience. The unified endpoint approach simplifies integration while ensuring comprehensive protection of sensitive legal data.