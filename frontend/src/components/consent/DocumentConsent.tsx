import React, { useState } from 'react';
import { Shield, Lock, Unlock, AlertTriangle, Info } from 'lucide-react';
import { Toast } from '../SimpleToast';

export interface DocumentConsentSettings {
  documentId: string;
  consentGiven: boolean;
  sensitivityLevel: 'public' | 'internal' | 'confidential' | 'highly-sensitive';
  restrictions: {
    allowAIProcessing: boolean;
    allowModelTraining: boolean;
    allowAnalytics: boolean;
    requireExplicitConsent: boolean;
  };
  consentHistory: Array<{
    timestamp: string;
    action: 'granted' | 'revoked';
    userId: string;
    reason?: string;
  }>;
}

interface DocumentConsentProps {
  documentId: string;
  documentName: string;
  onConsentChange?: (consent: DocumentConsentSettings) => void;
  initialConsent?: DocumentConsentSettings;
  compact?: boolean;
}

export const DocumentConsent: React.FC<DocumentConsentProps> = ({
  documentId,
  documentName,
  onConsentChange,
  initialConsent,
  compact = false
}) => {
  const [consent, setConsent] = useState<DocumentConsentSettings>(initialConsent || {
    documentId,
    consentGiven: true,
    sensitivityLevel: 'internal',
    restrictions: {
      allowAIProcessing: true,
      allowModelTraining: false,
      allowAnalytics: true,
      requireExplicitConsent: false
    },
    consentHistory: []
  });

  const [showDetails, setShowDetails] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const sensitivityConfig = {
    'public': { 
      color: 'text-green-600 bg-green-50', 
      icon: Unlock, 
      label: 'Public',
      description: 'No restrictions on AI processing'
    },
    'internal': { 
      color: 'text-blue-600 bg-blue-50', 
      icon: Shield, 
      label: 'Internal',
      description: 'Standard privacy protections apply'
    },
    'confidential': { 
      color: 'text-yellow-600 bg-yellow-50', 
      icon: Lock, 
      label: 'Confidential',
      description: 'Restricted AI processing, no training'
    },
    'highly-sensitive': { 
      color: 'text-red-600 bg-red-50', 
      icon: AlertTriangle, 
      label: 'Highly Sensitive',
      description: 'Requires explicit consent for each use'
    }
  };

  const currentSensitivity = sensitivityConfig[consent.sensitivityLevel];
  const IconComponent = currentSensitivity.icon;

  const updateConsent = async (updates: Partial<DocumentConsentSettings>) => {
    const newConsent = { ...consent, ...updates };
    setConsent(newConsent);
    
    // Add to consent history
    if (updates.consentGiven !== undefined && updates.consentGiven !== consent.consentGiven) {
      newConsent.consentHistory = [
        ...newConsent.consentHistory,
        {
          timestamp: new Date().toISOString(),
          action: updates.consentGiven ? 'granted' : 'revoked',
          userId: 'current-user' // This would come from auth context
        }
      ];
    }

    try {
      const response = await fetch(`/api/documents/${documentId}/consent`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify(newConsent)
      });

      if (response.ok) {
        setToastMessage('Document consent settings updated');
        setShowToast(true);
        onConsentChange?.(newConsent);
      }
    } catch (error) {
      console.error('Failed to update document consent:', error);
    }
  };

  const handleSensitivityChange = (level: DocumentConsentSettings['sensitivityLevel']) => {
    const updates: Partial<DocumentConsentSettings> = {
      sensitivityLevel: level,
      restrictions: { ...consent.restrictions }
    };

    // Auto-adjust restrictions based on sensitivity
    switch (level) {
      case 'public':
        updates.restrictions = {
          allowAIProcessing: true,
          allowModelTraining: true,
          allowAnalytics: true,
          requireExplicitConsent: false
        };
        break;
      case 'internal':
        updates.restrictions = {
          allowAIProcessing: true,
          allowModelTraining: false,
          allowAnalytics: true,
          requireExplicitConsent: false
        };
        break;
      case 'confidential':
        updates.restrictions = {
          allowAIProcessing: true,
          allowModelTraining: false,
          allowAnalytics: false,
          requireExplicitConsent: false
        };
        break;
      case 'highly-sensitive':
        updates.restrictions = {
          allowAIProcessing: false,
          allowModelTraining: false,
          allowAnalytics: false,
          requireExplicitConsent: true
        };
        updates.consentGiven = false; // Revoke consent for highly sensitive
        break;
    }

    updateConsent(updates);
  };

  if (compact) {
    return (
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className={`flex items-center space-x-1 px-2 py-1 rounded-md text-xs font-medium ${currentSensitivity.color}`}
        >
          <IconComponent className="h-3 w-3" />
          <span>{currentSensitivity.label}</span>
        </button>
        
        {showDetails && (
          <div className="absolute z-10 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 p-4">
            <h4 className="font-medium text-sm text-gray-900 mb-2">Document Privacy</h4>
            <p className="text-xs text-gray-600 mb-3">{currentSensitivity.description}</p>
            
            <div className="space-y-2">
              {Object.entries(sensitivityConfig).map(([level, config]) => (
                <button
                  key={level}
                  onClick={() => handleSensitivityChange(level as DocumentConsentSettings['sensitivityLevel'])}
                  className={`w-full flex items-center space-x-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    consent.sensitivityLevel === level 
                      ? config.color 
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <config.icon className="h-4 w-4" />
                  <span>{config.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Document Privacy Settings</h3>
        <IconComponent className={`h-6 w-6 ${currentSensitivity.color.split(' ')[0]}`} />
      </div>

      <div className="mb-6">
        <p className="text-sm text-gray-600 mb-1">Current document:</p>
        <p className="font-medium text-gray-900">{documentName}</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sensitivity Level
          </label>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(sensitivityConfig).map(([level, config]) => (
              <button
                key={level}
                onClick={() => handleSensitivityChange(level as DocumentConsentSettings['sensitivityLevel'])}
                className={`flex items-center space-x-2 px-4 py-3 rounded-lg border-2 transition-all ${
                  consent.sensitivityLevel === level 
                    ? `${config.color} border-current` 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <config.icon className="h-5 w-5" />
                <div className="text-left">
                  <p className="font-medium">{config.label}</p>
                  <p className="text-xs opacity-75">{config.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {consent.sensitivityLevel !== 'highly-sensitive' && (
          <div className="space-y-3 pt-4 border-t border-gray-200">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Allow AI processing</span>
              <input
                type="checkbox"
                checked={consent.restrictions.allowAIProcessing}
                onChange={(e) => updateConsent({
                  restrictions: { ...consent.restrictions, allowAIProcessing: e.target.checked }
                })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Allow for model training</span>
              <input
                type="checkbox"
                checked={consent.restrictions.allowModelTraining}
                onChange={(e) => updateConsent({
                  restrictions: { ...consent.restrictions, allowModelTraining: e.target.checked }
                })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Allow analytics</span>
              <input
                type="checkbox"
                checked={consent.restrictions.allowAnalytics}
                onChange={(e) => updateConsent({
                  restrictions: { ...consent.restrictions, allowAnalytics: e.target.checked }
                })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </label>
          </div>
        )}

        {consent.sensitivityLevel === 'highly-sensitive' && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800">Highly Sensitive Document</p>
                <p className="text-sm text-red-700 mt-1">
                  This document requires explicit consent for each AI operation. 
                  No automatic processing is allowed.
                </p>
              </div>
            </div>
          </div>
        )}

        {consent.consentHistory.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700"
            >
              <Info className="h-4 w-4" />
              <span>View consent history ({consent.consentHistory.length})</span>
            </button>
            
            {showDetails && (
              <div className="mt-3 space-y-2">
                {consent.consentHistory.slice(-5).reverse().map((entry, index) => (
                  <div key={index} className="text-xs text-gray-600">
                    <span className={entry.action === 'granted' ? 'text-green-600' : 'text-red-600'}>
                      {entry.action === 'granted' ? '✓' : '✗'}
                    </span>
                    {' '}
                    {new Date(entry.timestamp).toLocaleString()}
                    {entry.reason && ` - ${entry.reason}`}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

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