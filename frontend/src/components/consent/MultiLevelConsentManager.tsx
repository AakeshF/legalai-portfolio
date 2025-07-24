import React, { useState, useEffect, useCallback } from 'react';
import { Shield, Lock, Cloud, Server, Share2, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { ConsentScope, ConsentType, ConsentCheck, ConsentPolicy } from '../../types/consent';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';

interface MultiLevelConsentManagerProps {
  scope: ConsentScope;
  scopeId?: string;
  documentSensitivity?: 'public' | 'internal' | 'confidential' | 'highly-sensitive';
  onConsentChange?: (consent: ConsentCheck) => void;
}

export const MultiLevelConsentManager: React.FC<MultiLevelConsentManagerProps> = ({
  scope,
  scopeId,
  documentSensitivity,
  onConsentChange
}) => {
  const { user, organization } = useAuth();
  const [policy, setPolicy] = useState<ConsentPolicy | null>(null);
  const [consents, setConsents] = useState<Map<ConsentType, boolean>>(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [showDetails, setShowDetails] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const consentTypeInfo = {
    [ConsentType.CLOUD_AI]: {
      icon: Cloud,
      color: 'text-blue-600',
      title: 'Cloud AI Processing',
      description: 'Allow documents to be processed by cloud-based AI providers'
    },
    [ConsentType.LOCAL_AI]: {
      icon: Server,
      color: 'text-green-600',
      title: 'Local AI Processing',
      description: 'Allow documents to be processed by on-premises AI systems'
    },
    [ConsentType.THIRD_PARTY_SHARING]: {
      icon: Share2,
      color: 'text-purple-600',
      title: 'Third-Party Data Sharing',
      description: 'Allow AI providers to use data for model improvement'
    }
  };

  useEffect(() => {
    fetchConsentPolicy();
    checkCurrentConsents();
  }, [scope, scopeId]);

  const fetchConsentPolicy = async () => {
    try {
      const response = await fetch(`/api/organizations/${organization?.id}/consent-policy`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPolicy(data);
      }
    } catch (error) {
      console.error('Failed to fetch consent policy:', error);
    }
  };

  const checkCurrentConsents = async () => {
    try {
      const params = new URLSearchParams({
        scope: scope,
        ...(scopeId && { scopeId })
      });

      const response = await fetch(`/api/consent/check?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data: ConsentCheck = await response.json();
        const newConsents = new Map<ConsentType, boolean>();
        
        Object.values(ConsentType).forEach(type => {
          newConsents.set(type, data.types.includes(type));
        });
        
        setConsents(newConsents);
      }
    } catch (error) {
      console.error('Failed to check consents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const requiresConsent = useCallback((): boolean => {
    if (!policy) return true;

    // Check document sensitivity
    if (scope === ConsentScope.DOCUMENT && documentSensitivity) {
      const threshold = policy.sensitivityThresholds.requireDocumentConsent;
      if (documentSensitivity === 'highly-sensitive') return true;
      if (threshold === 'confidential' && 
          (documentSensitivity === 'confidential' || documentSensitivity === 'highly-sensitive')) {
        return true;
      }
    }

    // Check organization policy
    if (policy.requireExplicitConsent && scope === ConsentScope.USER) {
      return true;
    }

    // Organization scope with blanket consent
    if (scope === ConsentScope.ORGANIZATION && !policy.requireExplicitConsent) {
      return false;
    }

    return true;
  }, [policy, scope, documentSensitivity]);

  const updateConsent = async (type: ConsentType, granted: boolean) => {
    try {
      const response = await fetch('/api/consent/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          scope,
          scopeId,
          type,
          granted,
          userId: user?.id,
          organizationId: organization?.id
        })
      });

      if (response.ok) {
        setConsents(prev => {
          const updated = new Map(prev);
          updated.set(type, granted);
          return updated;
        });

        setToastMessage(`${consentTypeInfo[type].title} ${granted ? 'enabled' : 'disabled'}`);
        setShowToast(true);

        // Notify parent
        const consentCheck: ConsentCheck = {
          hasConsent: granted,
          scope,
          types: Array.from(consents.entries())
            .filter(([_, isGranted]) => isGranted)
            .map(([type]) => type),
          grantedAt: new Date().toISOString()
        };
        onConsentChange?.(consentCheck);
      }
    } catch (error) {
      setToastMessage('Failed to update consent');
      setShowToast(true);
    }
  };

  const getScopeDisplay = () => {
    switch (scope) {
      case ConsentScope.ORGANIZATION:
        return { icon: Shield, label: 'Organization-wide Consent', color: 'text-blue-600' };
      case ConsentScope.USER:
        return { icon: Lock, label: 'Personal Consent Settings', color: 'text-green-600' };
      case ConsentScope.DOCUMENT:
        return { icon: Lock, label: 'Document-specific Consent', color: 'text-yellow-600' };
      case ConsentScope.SESSION:
        return { icon: Lock, label: 'Session Consent', color: 'text-purple-600' };
    }
  };

  if (isLoading) {
    return <div className="animate-pulse h-48 bg-gray-100 rounded-lg"></div>;
  }

  const scopeInfo = getScopeDisplay();
  const ScopeIcon = scopeInfo.icon;
  const needsExplicitConsent = requiresConsent();

  // If no consent required, show simple status
  if (!needsExplicitConsent && scope === ConsentScope.ORGANIZATION) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center space-x-3">
          <CheckCircle className="h-5 w-5 text-green-600" />
          <div>
            <p className="text-sm font-medium text-green-800">Organization Blanket Consent Active</p>
            <p className="text-sm text-green-700 mt-1">
              AI processing is enabled by your organization's policy.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <ScopeIcon className={`h-6 w-6 ${scopeInfo.color}`} />
          <h3 className="text-lg font-semibold text-gray-900">{scopeInfo.label}</h3>
        </div>
        {documentSensitivity && (
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
            documentSensitivity === 'highly-sensitive' ? 'bg-red-100 text-red-700' :
            documentSensitivity === 'confidential' ? 'bg-yellow-100 text-yellow-700' :
            documentSensitivity === 'internal' ? 'bg-blue-100 text-blue-700' :
            'bg-green-100 text-green-700'
          }`}>
            {documentSensitivity.replace('-', ' ')}
          </span>
        )}
      </div>

      {scope === ConsentScope.DOCUMENT && documentSensitivity === 'highly-sensitive' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Highly Sensitive Document</p>
              <p className="text-sm text-red-700 mt-1">
                This document requires explicit consent for each AI operation due to its sensitive nature.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {Object.entries(consentTypeInfo).map(([type, info]) => {
          const Icon = info.icon;
          const isGranted = consents.get(type as ConsentType) || false;
          
          return (
            <div key={type} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                  <Icon className={`h-5 w-5 ${info.color} mt-0.5`} />
                  <div>
                    <h4 className="text-sm font-medium text-gray-900">{info.title}</h4>
                    <p className="text-sm text-gray-600 mt-1">{info.description}</p>
                  </div>
                </div>
                <button
                  onClick={() => updateConsent(type as ConsentType, !isGranted)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    isGranted ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      isGranted ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <button
        onClick={() => setShowDetails(!showDetails)}
        className="mt-6 flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700"
      >
        <Info className="h-4 w-4" />
        <span>{showDetails ? 'Hide' : 'Show'} consent details</span>
      </button>

      {showDetails && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
          <h4 className="font-medium text-gray-700 mb-2">Consent Scope Details</h4>
          <ul className="space-y-1">
            <li>• Scope: {scope}</li>
            {scopeId && <li>• Scope ID: {scopeId}</li>}
            <li>• User: {user?.email}</li>
            <li>• Organization: {organization?.name}</li>
            {policy && (
              <>
                <li>• Explicit consent required: {policy.requireExplicitConsent ? 'Yes' : 'No'}</li>
                <li>• Document consent threshold: {policy.sensitivityThresholds.requireDocumentConsent}</li>
              </>
            )}
          </ul>
        </div>
      )}

      {showToast && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
};