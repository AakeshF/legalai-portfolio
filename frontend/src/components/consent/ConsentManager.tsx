import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';

export interface ConsentSettings {
  id: string;
  userId: string;
  organizationId: string;
  hasGivenConsent: boolean;
  consentDate?: string;
  consentVersion: string;
  allowDataProcessing: boolean;
  allowModelTraining: boolean;
  allowAnalytics: boolean;
  updatedAt: string;
}

export const ConsentManager: React.FC = () => {
  const { user } = useAuth();
  const [consent, setConsent] = useState<ConsentSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');

  const [allowDataProcessing, setAllowDataProcessing] = useState(true);
  const [allowModelTraining, setAllowModelTraining] = useState(false);
  const [allowAnalytics, setAllowAnalytics] = useState(true);

  useEffect(() => {
    fetchConsentSettings();
  }, []);

  const fetchConsentSettings = async () => {
    try {
      const response = await fetch(`/api/users/${user?.id}/consent`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setConsent(data);
        setAllowDataProcessing(data.allowDataProcessing);
        setAllowModelTraining(data.allowModelTraining);
        setAllowAnalytics(data.allowAnalytics);
      }
    } catch (error) {
      console.error('Failed to fetch consent settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateConsent = async (giveConsent: boolean) => {
    setIsSaving(true);
    try {
      const response = await fetch(`/api/users/${user?.id}/consent`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          hasGivenConsent: giveConsent,
          allowDataProcessing: giveConsent ? allowDataProcessing : false,
          allowModelTraining: giveConsent ? allowModelTraining : false,
          allowAnalytics: giveConsent ? allowAnalytics : false,
          consentVersion: '1.0'
        })
      });

      if (response.ok) {
        setToastMessage(giveConsent ? 'Consent preferences updated' : 'You have opted out of AI processing');
        setToastType('success');
        setShowToast(true);
        await fetchConsentSettings();
      } else {
        throw new Error('Failed to update consent');
      }
    } catch (error) {
      setToastMessage('Failed to update consent preferences');
      setToastType('error');
      setShowToast(true);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div className="animate-pulse h-48 bg-gray-100 rounded-lg"></div>;
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Shield className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">AI Data Processing Consent</h3>
        </div>
        {consent?.hasGivenConsent && (
          <CheckCircle className="h-5 w-5 text-green-500" />
        )}
      </div>

      {!consent?.hasGivenConsent ? (
        <div className="space-y-4">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-800">AI Processing Disabled</p>
                <p className="text-sm text-yellow-700 mt-1">
                  You have opted out of AI data processing. Document analysis and chat features will not be available.
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => updateConsent(true)}
            disabled={isSaving}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Enable AI Processing
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-green-800">AI Processing Enabled</p>
                <p className="text-sm text-green-700 mt-1">
                  Your documents are being processed by AI to provide analysis and insights.
                  {consent.consentDate && (
                    <span className="block mt-1">
                      Consent given on {new Date(consent.consentDate).toLocaleDateString()}
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700"
            >
              <Info className="h-4 w-4" />
              <span>{showDetails ? 'Hide' : 'Show'} detailed preferences</span>
            </button>

            {showDetails && (
              <div className="space-y-4 pl-6 border-l-2 border-gray-200">
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowDataProcessing}
                    onChange={(e) => setAllowDataProcessing(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-700">Document Processing</p>
                    <p className="text-xs text-gray-500">Allow AI to analyze and extract information from your documents</p>
                  </div>
                </label>

                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowModelTraining}
                    onChange={(e) => setAllowModelTraining(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-700">Improve AI Models</p>
                    <p className="text-xs text-gray-500">Allow anonymized data to be used for improving AI accuracy</p>
                  </div>
                </label>

                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowAnalytics}
                    onChange={(e) => setAllowAnalytics(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-700">Usage Analytics</p>
                    <p className="text-xs text-gray-500">Track feature usage to improve the platform</p>
                  </div>
                </label>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    onClick={() => updateConsent(true)}
                    disabled={isSaving || !allowDataProcessing}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    Update Preferences
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-gray-200">
            <button
              onClick={() => {
                if (confirm('Are you sure you want to opt out? This will disable all AI features.')) {
                  updateConsent(false);
                }
              }}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Opt out of AI processing
            </button>
          </div>
        </div>
      )}

      {showToast && (
        <Toast
          message={toastMessage}
          type={toastType}
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
};