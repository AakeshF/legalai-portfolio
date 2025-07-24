import React, { useState, useEffect } from 'react';
import { 
  Key, Trash2, CheckCircle, XCircle, RefreshCw, 
  RotateCw, TrendingUp, Clock, AlertTriangle, BarChart3,
  Calendar, DollarSign
} from 'lucide-react';
import { AIProvider, AI_PROVIDERS } from './types';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';
import { Skeleton } from '../Skeleton';

interface EnhancedAPIKey {
  id: string;
  provider: AIProvider;
  keyHint: string;
  validationStatus: 'valid' | 'invalid' | 'unchecked';
  isActive: boolean;
  createdAt: string;
  lastUsed?: string;
  lastValidated?: string;
  rotatedFrom?: string;
  expiresAt?: string;
  usageCount: number;
  usage: {
    totalRequests: number;
    totalTokens: number;
    totalCost: number;
    lastMonthRequests: number;
    lastMonthTokens: number;
    lastMonthCost: number;
  };
}

export const EnhancedAPIKeyManager: React.FC = () => {
  const { user } = useAuth();
  const [apiKeys, setApiKeys] = useState<EnhancedAPIKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const fetchApiKeys = async () => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/api-keys/enhanced`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setApiKeys(data);
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteApiKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to delete this API key?')) return;

    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        setToastMessage('API key deleted successfully');
        setToastType('success');
        setShowToast(true);
        await fetchApiKeys();
      }
    } catch (error) {
      setToastMessage('Failed to delete API key');
      setToastType('error');
      setShowToast(true);
    }
  };

  const rotateApiKey = async (keyId: string) => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/api-keys/${keyId}/rotate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        setToastMessage('API key rotation initiated. Check your email for the new key.');
        setToastType('success');
        setShowToast(true);
        await fetchApiKeys();
      } else {
        throw new Error('Failed to rotate API key');
      }
    } catch (error) {
      setToastMessage('Failed to rotate API key');
      setToastType('error');
      setShowToast(true);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  if (isLoading) {
    return <div className="animate-pulse h-64 bg-gray-100 rounded-lg"></div>;
  }

  const selectedKey = apiKeys.find(key => key.id === selectedKeyId);

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Enhanced API Key Management</h3>
          <p className="text-sm text-gray-600">API keys are managed by your administrator</p>
        </div>

        <div className="space-y-3">
          {apiKeys.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              No API keys configured. Contact your administrator to add API keys.
            </p>
          ) : (
            apiKeys.map((key) => (
              <div
                key={key.id}
                className={`p-4 bg-gray-50 rounded-lg border transition-all cursor-pointer ${
                  selectedKeyId === key.id ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setSelectedKeyId(selectedKeyId === key.id ? null : key.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <Key className="h-5 w-5 text-gray-400" />
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900">
                          {AI_PROVIDERS[key.provider].name}
                        </span>
                        {key.validationStatus === 'valid' ? (
                          <CheckCircle className="h-4 w-4 text-green-500" title="Validated" />
                        ) : key.validationStatus === 'invalid' ? (
                          <XCircle className="h-4 w-4 text-red-500" title="Invalid" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-yellow-500" title="Not validated" />
                        )}
                        {key.expiresAt && new Date(key.expiresAt) < new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) && (
                          <AlertTriangle className="h-4 w-4 text-yellow-500" title="Expires soon" />
                        )}
                      </div>
                      <div className="flex items-center space-x-2 text-sm">
                        <p className="text-gray-500 font-mono">
                          {key.provider === 'anthropic' ? 'sk-ant-' : 'sk-'}...{key.keyHint}
                        </p>
                        <span className="text-xs text-gray-400">({key.usageCount} uses)</span>
                      </div>
                      <div className="flex items-center space-x-4 text-xs text-gray-400 mt-1">
                        <span>Added {new Date(key.createdAt).toLocaleDateString()}</span>
                        {key.lastUsed && (
                          <span>Last used {new Date(key.lastUsed).toLocaleDateString()}</span>
                        )}
                        {key.rotatedFrom && (
                          <span className="text-blue-600">Rotated</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        rotateApiKey(key.id);
                      }}
                      className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md"
                      title="Request key rotation"
                    >
                      <RotateCw className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteApiKey(key.id);
                      }}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-md"
                      title="Delete key"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Usage Statistics */}
      {selectedKey && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Usage Statistics</h3>
            <BarChart3 className="h-5 w-5 text-gray-400" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <TrendingUp className="h-8 w-8 text-blue-600" />
                <span className="text-2xl font-semibold text-gray-900">
                  {formatNumber(selectedKey.usage.totalRequests)}
                </span>
              </div>
              <p className="text-sm text-gray-600">Total Requests</p>
              <p className="text-xs text-gray-500 mt-1">
                {formatNumber(selectedKey.usage.lastMonthRequests)} last month
              </p>
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <Clock className="h-8 w-8 text-green-600" />
                <span className="text-2xl font-semibold text-gray-900">
                  {formatNumber(selectedKey.usage.totalTokens)}
                </span>
              </div>
              <p className="text-sm text-gray-600">Total Tokens</p>
              <p className="text-xs text-gray-500 mt-1">
                {formatNumber(selectedKey.usage.lastMonthTokens)} last month
              </p>
            </div>

            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <DollarSign className="h-8 w-8 text-purple-600" />
                <span className="text-2xl font-semibold text-gray-900">
                  {formatCurrency(selectedKey.usage.totalCost)}
                </span>
              </div>
              <p className="text-sm text-gray-600">Total Cost</p>
              <p className="text-xs text-gray-500 mt-1">
                {formatCurrency(selectedKey.usage.lastMonthCost)} last month
              </p>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Average cost per request</span>
              <span className="font-medium text-gray-900">
                {formatCurrency(selectedKey.usage.totalCost / selectedKey.usage.totalRequests || 0)}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-600">Average tokens per request</span>
              <span className="font-medium text-gray-900">
                {Math.round(selectedKey.usage.totalTokens / selectedKey.usage.totalRequests || 0)}
              </span>
            </div>
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