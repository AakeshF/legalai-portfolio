import { useState, useCallback } from 'react';
import { ConsentScope, ConsentType, ConsentCheck } from '../types/consent';
import { useAuth } from '../contexts/MockAuthContext';

interface UseConsentCheckProps {
  documentId?: string;
  documentSensitivity?: 'public' | 'internal' | 'confidential' | 'highly-sensitive';
  sessionId?: string;
}

export const useConsentCheck = ({ documentId, documentSensitivity, sessionId }: UseConsentCheckProps) => {
  const { user, organization } = useAuth();
  const [isChecking, setIsChecking] = useState(false);
  const [consentRequired, setConsentRequired] = useState<ConsentScope | null>(null);

  const checkConsent = useCallback(async (): Promise<ConsentCheck | null> => {
    setIsChecking(true);
    
    try {
      // Implement the practical flow from backend
      if (documentSensitivity === 'highly-sensitive' && documentId) {
        // Require document-specific consent
        const response = await fetch(`/api/consent/check?scope=document&scopeId=${documentId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (response.ok) {
          const consent = await response.json();
          if (!consent.hasConsent) {
            setConsentRequired(ConsentScope.DOCUMENT);
            return null;
          }
          return consent;
        }
      } else if (organization?.requireExplicitConsent) {
        // Check user has general consent
        const response = await fetch(`/api/consent/check?scope=user&scopeId=${user?.id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (response.ok) {
          const consent = await response.json();
          if (!consent.hasConsent) {
            setConsentRequired(ConsentScope.USER);
            return null;
          }
          return consent;
        }
      } else {
        // Use organization blanket consent
        const response = await fetch(`/api/consent/check?scope=organization&scopeId=${organization?.id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (response.ok) {
          const consent = await response.json();
          return consent;
        }
      }
      
      return null;
    } catch (error) {
      console.error('Failed to check consent:', error);
      return null;
    } finally {
      setIsChecking(false);
    }
  }, [documentId, documentSensitivity, organization, user]);

  const requireConsent = useCallback(async (scope: ConsentScope, scopeId?: string) => {
    const response = await fetch('/api/consent/require', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      },
      body: JSON.stringify({
        scope,
        scopeId,
        types: [ConsentType.CLOUD_AI],
        userId: user?.id
      })
    });

    return response.ok;
  }, [user]);

  return {
    checkConsent,
    requireConsent,
    consentRequired,
    isChecking
  };
};
