import React, { useState, useEffect } from 'react';
import { AI_PROVIDERS, AI_MODELS } from './types';
import type { AIProvider, AIProviderConfig, OrganizationAISettings } from './types';
import { useAuth } from '../../contexts/MockAuthContext';
import { Toast } from '../SimpleToast';
import { Skeleton } from '../Skeleton';
import { EnhancedAPIKeyManager } from './EnhancedAPIKeyManager';

export const AIProviderSettings: React.FC = () => {
  const { user } = useAuth();
  const [settings, setSettings] = useState<OrganizationAISettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');

  const [selectedProvider, setSelectedProvider] = useState<AIProvider>('openai');
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4-turbo');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [allowUserOverrides, setAllowUserOverrides] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`/api/organizations/${user?.organization_id}/ai-settings`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      }).catch(() => null);

      if (response?.ok) {
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            setSettings(data);
            if (data.primaryProvider) {
              setSelectedProvider(data.primaryProvider.provider);
              setSelectedModel(data.primaryProvider.modelId);
              setTemperature(data.primaryProvider.temperature || 0.7);
              setMaxTokens(data.primaryProvider.maxTokens || 2048);
              setAllowUserOverrides(data.allowUserOverrides);
            }
          } else {
            console.warn('AI settings endpoint returned non-JSON response');
          }
        } catch (parseError) {
          console.warn('Failed to parse AI settings JSON:', parseError);
        }
      } else if (response && !response.ok) {
        console.warn(`AI settings API returned ${response.status}: ${response.statusText}`);
      } else {
        // Set defaults when endpoint is not available
        console.info('AI settings endpoint not available - using defaults');
        setSelectedProvider('openai');
        setSelectedModel('gpt-4');
        setTemperature(0.7);
        setMaxTokens(2048);
        setAllowUserOverrides(false);
      }
    } catch (error) {
      console.error('Failed to fetch AI settings:', error);
      // Set defaults on error
      setSelectedProvider('openai');
      setSelectedModel('gpt-4');
      setTemperature(0.7);
      setMaxTokens(2048);
      setAllowUserOverrides(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const config: AIProviderConfig = {
        provider: selectedProvider,
        modelId: selectedModel,
        temperature,
        maxTokens
      };

      const response = await fetch(`/api/organizations/${user?.organization_id}/ai-settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          primaryProvider: config,
          allowUserOverrides
        })
      });

      if (response.ok) {
        setToastMessage('AI provider settings saved successfully');
        setToastType('success');
        setShowToast(true);
        await fetchSettings();
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      setToastMessage('Failed to save AI provider settings');
      setToastType('error');
      setShowToast(true);
    } finally {
      setIsSaving(false);
    }
  };

  const filteredModels = AI_MODELS.filter(model => model.provider === selectedProvider);
  const selectedModelData = AI_MODELS.find(m => m.id === selectedModel);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">AI Provider Configuration</h3>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            AI Provider
          </label>
          <select
            value={selectedProvider}
            onChange={(e) => {
              setSelectedProvider(e.target.value as AIProvider);
              const firstModel = AI_MODELS.find(m => m.provider === e.target.value);
              if (firstModel) setSelectedModel(firstModel.id);
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {Object.entries(AI_PROVIDERS).map(([key, provider]) => (
              <option key={key} value={key}>
                {provider.icon} {provider.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Model
          </label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {filteredModels.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
          
          {selectedModelData && (
            <div className="mt-2 text-sm text-gray-600">
              <p>Context Window: {selectedModelData.contextWindow.toLocaleString()} tokens</p>
              <p>Cost: ${selectedModelData.costPer1kTokens.input}/1k input, ${selectedModelData.costPer1kTokens.output}/1k output</p>
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Temperature ({temperature})
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Response Tokens
          </label>
          <input
            type="number"
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value))}
            min="256"
            max="4096"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="allowOverrides"
            checked={allowUserOverrides}
            onChange={(e) => setAllowUserOverrides(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="allowOverrides" className="ml-2 block text-sm text-gray-700">
            Allow users to override organization settings
          </label>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      {showToast && (
        <Toast
          message={toastMessage}
          type={toastType}
          onClose={() => setShowToast(false)}
        />
      )}
      </div>

      <EnhancedAPIKeyManager />
    </div>
  );
};
