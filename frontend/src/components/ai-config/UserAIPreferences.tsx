import React, { useState, useEffect } from 'react';
import { AIProvider, AI_PROVIDERS, AI_MODELS } from './types';
import { useAIPreferences } from '../../contexts/AIPreferencesContext';
import { Toast } from '../SimpleToast';
import { Skeleton } from '../Skeleton';
import { ToggleGroup, ToggleGroupItem } from '../ui/ToggleGroup';
import { Info, Settings } from 'lucide-react';

export const UserAIPreferences: React.FC = () => {
  const { 
    userPreferences, 
    organizationSettings, 
    effectiveSettings,
    isLoading, 
    updateUserPreferences, 
    toggleOverride 
  } = useAIPreferences();

  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');
  const [isSaving, setIsSaving] = useState(false);

  const [overrideEnabled, setOverrideEnabled] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<AIProvider>('openai');
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4-turbo');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);

  useEffect(() => {
    if (userPreferences) {
      setOverrideEnabled(userPreferences.overrideOrganizationSettings);
      if (userPreferences.preferredProvider) {
        setSelectedProvider(userPreferences.preferredProvider.provider);
        setSelectedModel(userPreferences.preferredProvider.modelId);
        setTemperature(userPreferences.preferredProvider.temperature || 0.7);
        setMaxTokens(userPreferences.preferredProvider.maxTokens || 2048);
      }
    }
  }, [userPreferences]);

  const handleToggleOverride = async (enabled: boolean) => {
    setOverrideEnabled(enabled);
    setIsSaving(true);
    
    try {
      await toggleOverride(enabled);
      setToastMessage(enabled ? 'Using personal AI preferences' : 'Using organization defaults');
      setToastType('success');
      setShowToast(true);
    } catch (error) {
      setToastMessage('Failed to update preference override');
      setToastType('error');
      setShowToast(true);
      setOverrideEnabled(!enabled); // Revert on error
    } finally {
      setIsSaving(false);
    }
  };

  const handleSavePreferences = async () => {
    if (!overrideEnabled) return;
    
    setIsSaving(true);
    try {
      await updateUserPreferences({
        overrideOrganizationSettings: true,
        preferredProvider: {
          provider: selectedProvider,
          modelId: selectedModel,
          temperature,
          maxTokens
        }
      });
      
      setToastMessage('Personal AI preferences saved');
      setToastType('success');
      setShowToast(true);
    } catch (error) {
      setToastMessage('Failed to save preferences');
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

  const canOverride = organizationSettings?.allowUserOverrides;

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Personal AI Preferences</h3>
        <Settings className="h-5 w-5 text-gray-400" />
      </div>

      {!canOverride ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Organization Policy</p>
              <p className="text-sm text-gray-600 mt-1">
                Your organization does not allow personal AI provider preferences. 
                Contact your administrator to enable this feature.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div>
            <label className="flex items-center justify-between mb-4">
              <span className="text-sm font-medium text-gray-700">
                Use personal preferences instead of organization defaults
              </span>
              <button
                onClick={() => handleToggleOverride(!overrideEnabled)}
                disabled={isSaving}
                className={`
                  relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                  ${overrideEnabled ? 'bg-blue-600' : 'bg-gray-200'}
                  ${isSaving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
              >
                <span
                  className={`
                    inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                    ${overrideEnabled ? 'translate-x-6' : 'translate-x-1'}
                  `}
                />
              </button>
            </label>

            {organizationSettings && !overrideEnabled && (
              <div className="bg-gray-50 rounded-lg p-4 text-sm">
                <p className="font-medium text-gray-700 mb-2">Current Organization Settings:</p>
                <div className="space-y-1 text-gray-600">
                  <p>Provider: {AI_PROVIDERS[organizationSettings.primaryProvider.provider].name}</p>
                  <p>Model: {organizationSettings.primaryProvider.modelId}</p>
                </div>
              </div>
            )}
          </div>

          <div className={`space-y-6 ${!overrideEnabled ? 'opacity-50 pointer-events-none' : ''}`}>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preferred AI Provider
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
                Preferred Model
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
                  <p>Context: {selectedModelData.contextWindow.toLocaleString()} tokens</p>
                  <p>Cost: ${selectedModelData.costPer1kTokens.input}/1k in, ${selectedModelData.costPer1kTokens.output}/1k out</p>
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

            <div className="flex justify-end">
              <button
                onClick={handleSavePreferences}
                disabled={isSaving || !overrideEnabled}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save Preferences'}
              </button>
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