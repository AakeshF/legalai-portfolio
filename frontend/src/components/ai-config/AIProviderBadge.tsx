import React, { useState, useEffect } from 'react';
import { AI_PROVIDERS, AIProvider } from './types';
import { useAuth } from '../../contexts/AuthContext';
import { Info } from 'lucide-react';

interface AIProviderBadgeProps {
  compact?: boolean;
}

export const AIProviderBadge: React.FC<AIProviderBadgeProps> = ({ compact = false }) => {
  const { user } = useAuth();
  const [currentProvider, setCurrentProvider] = useState<AIProvider | null>(null);
  const [currentModel, setCurrentModel] = useState<string | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    fetchCurrentProvider();
  }, []);

  const fetchCurrentProvider = async () => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/ai-settings`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      }).catch(() => null);

      if (response?.ok) {
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (data.primaryProvider) {
              setCurrentProvider(data.primaryProvider.provider);
              setCurrentModel(data.primaryProvider.modelId);
            }
          } else {
            console.warn('AI provider endpoint returned non-JSON response');
          }
        } catch (parseError) {
          console.warn('Failed to parse AI provider JSON:', parseError);
        }
      } else if (response && !response.ok) {
        console.warn(`AI provider API returned ${response.status}: ${response.statusText}`);
      } else {
        // No response or network error - set defaults
        console.info('AI provider endpoint not available - using defaults');
        setCurrentProvider('openai');
        setCurrentModel('gpt-4');
      }
    } catch (error) {
      console.error('Failed to fetch AI provider:', error);
      // Set defaults on error
      setCurrentProvider('openai');
      setCurrentModel('gpt-4');
    }
  };

  if (!currentProvider) {
    return null;
  }

  const provider = AI_PROVIDERS[currentProvider];

  if (compact) {
    return (
      <div className="relative inline-flex items-center">
        <button
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          className="flex items-center space-x-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded-md text-xs font-medium text-gray-700 transition-colors"
        >
          <span>{provider.icon}</span>
          <span>{provider.name}</span>
          <Info className="h-3 w-3 text-gray-500" />
        </button>
        
        {showTooltip && (
          <div className="absolute bottom-full left-0 mb-2 w-48 p-2 bg-gray-800 text-white text-xs rounded-md shadow-lg z-10">
            <p className="font-medium">{provider.name}</p>
            <p className="text-gray-300 mt-1">Model: {currentModel}</p>
            <div className="absolute bottom-0 left-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-gray-800"></div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
      <span className="text-lg">{provider.icon}</span>
      <div>
        <p className="text-sm font-medium text-gray-900">{provider.name}</p>
        <p className="text-xs text-gray-500">{currentModel}</p>
      </div>
    </div>
  );
};