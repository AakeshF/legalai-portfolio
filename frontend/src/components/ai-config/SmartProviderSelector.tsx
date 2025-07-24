import React, { useState, useEffect } from 'react';
import { 
  Brain, Zap, FileText, TrendingUp, DollarSign, 
  Clock, Target, Info, Settings, CheckCircle
} from 'lucide-react';
import { AI_PROVIDERS, AI_MODELS, AIProvider } from './types';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';

interface DocumentTypeMapping {
  documentType: string;
  recommendedProvider: AIProvider;
  recommendedModel: string;
  reasoning: string;
  accuracy: number;
  averageCost: number;
  averageTime: number;
}

interface SmartSelectionRule {
  id: string;
  name: string;
  priority: number;
  conditions: {
    documentTypes?: string[];
    complexity?: 'low' | 'medium' | 'high';
    urgency?: 'low' | 'medium' | 'high';
    costSensitivity?: 'low' | 'medium' | 'high';
    accuracyRequirement?: 'standard' | 'high' | 'critical';
  };
  providerPreferences: {
    provider: AIProvider;
    model: string;
    weight: number;
  }[];
}

interface SmartSelectionConfig {
  enabled: boolean;
  learningEnabled: boolean;
  mappings: DocumentTypeMapping[];
  rules: SmartSelectionRule[];
  defaultStrategy: 'cost' | 'performance' | 'balanced';
}

export const SmartProviderSelector: React.FC = () => {
  const { user } = useAuth();
  const [config, setConfig] = useState<SmartSelectionConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [editingMapping, setEditingMapping] = useState<DocumentTypeMapping | null>(null);
  const [testDocument, setTestDocument] = useState({
    type: 'Contract',
    complexity: 'medium' as const,
    urgency: 'medium' as const
  });

  const documentTypes = [
    'Contract', 'NDA', 'Legal Brief', 'Court Filing', 
    'Patent', 'License Agreement', 'Employment Agreement',
    'Financial Document', 'Medical Record', 'Lease Agreement',
    'Corporate Bylaws', 'Privacy Policy', 'Terms of Service'
  ];

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/smart-selection-config`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to fetch smart selection config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSmartSelection = async () => {
    if (!config) return;

    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/smart-selection-config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          ...config,
          enabled: !config.enabled
        })
      });

      if (response.ok) {
        setConfig(prev => prev ? { ...prev, enabled: !prev.enabled } : null);
        setToastMessage(config.enabled ? 'Smart selection disabled' : 'Smart selection enabled');
        setShowToast(true);
      }
    } catch (error) {
      console.error('Failed to toggle smart selection:', error);
    }
  };

  const testSelection = async () => {
    try {
      const response = await fetch('/api/test-smart-selection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify(testDocument)
      });

      if (response.ok) {
        const result = await response.json();
        setToastMessage(`Recommended: ${AI_PROVIDERS[result.provider].name} - ${result.model}`);
        setShowToast(true);
      }
    } catch (error) {
      console.error('Failed to test selection:', error);
    }
  };

  const updateMapping = async (mapping: DocumentTypeMapping) => {
    if (!config) return;

    try {
      const updatedMappings = config.mappings.map(m => 
        m.documentType === mapping.documentType ? mapping : m
      );

      const response = await fetch(`/api/organizations/${user?.organizationId}/smart-selection-config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          ...config,
          mappings: updatedMappings
        })
      });

      if (response.ok) {
        await fetchConfig();
        setEditingMapping(null);
        setToastMessage('Mapping updated successfully');
        setShowToast(true);
      }
    } catch (error) {
      console.error('Failed to update mapping:', error);
    }
  };

  if (isLoading || !config) {
    return <div className="animate-pulse h-96 bg-gray-100 rounded-lg"></div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Brain className="h-6 w-6 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">Smart Provider Selection</h3>
          </div>
          
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.learningEnabled}
                onChange={(e) => setConfig({ ...config, learningEnabled: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">Enable Learning</span>
            </label>

            <button
              onClick={toggleSmartSelection}
              className={`px-4 py-2 rounded-md transition-colors ${
                config.enabled
                  ? 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {config.enabled ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <Zap className="h-5 w-5 text-purple-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-purple-900">Intelligent AI Selection</p>
              <p className="text-sm text-purple-800 mt-1">
                Automatically selects the best AI provider and model based on document type, 
                complexity, and your optimization preferences. Learning mode improves accuracy over time.
              </p>
            </div>
          </div>
        </div>

        {/* Test Selection */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Test Smart Selection</h4>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Document Type</label>
              <select
                value={testDocument.type}
                onChange={(e) => setTestDocument({ ...testDocument, type: e.target.value })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {documentTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Complexity</label>
              <select
                value={testDocument.complexity}
                onChange={(e) => setTestDocument({ ...testDocument, complexity: e.target.value as any })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Urgency</label>
              <select
                value={testDocument.urgency}
                onChange={(e) => setTestDocument({ ...testDocument, urgency: e.target.value as any })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>
          <button
            onClick={testSelection}
            className="px-3 py-1 bg-purple-600 text-white text-sm rounded-md hover:bg-purple-700"
          >
            Test Selection
          </button>
        </div>
      </div>

      {/* Document Type Mappings */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Document Type Performance</h3>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Document Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Best Provider
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Model
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Accuracy
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Cost
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Time
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {config.mappings.map((mapping) => (
                <tr key={mapping.documentType} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-gray-400" />
                      <span>{mapping.documentType}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                    <div className="flex items-center space-x-2">
                      <span>{AI_PROVIDERS[mapping.recommendedProvider].icon}</span>
                      <span>{AI_PROVIDERS[mapping.recommendedProvider].name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                    {mapping.recommendedModel}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                    <span className={`font-medium ${
                      mapping.accuracy >= 90 ? 'text-green-600' : 
                      mapping.accuracy >= 80 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {mapping.accuracy}%
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-700">
                    ${mapping.averageCost.toFixed(3)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-700">
                    {(mapping.averageTime / 1000).toFixed(1)}s
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <button
                      onClick={() => setEditingMapping(mapping)}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Strategy Settings */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Selection Strategy</h3>
        
        <div className="grid grid-cols-3 gap-4">
          <button
            onClick={() => setConfig({ ...config, defaultStrategy: 'cost' })}
            className={`p-4 rounded-lg border-2 transition-all ${
              config.defaultStrategy === 'cost'
                ? 'border-green-500 bg-green-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <DollarSign className="h-8 w-8 text-green-600 mx-auto mb-2" />
            <h4 className="font-medium text-gray-900">Cost Optimized</h4>
            <p className="text-xs text-gray-600 mt-1">
              Minimize costs while maintaining acceptable quality
            </p>
          </button>

          <button
            onClick={() => setConfig({ ...config, defaultStrategy: 'performance' })}
            className={`p-4 rounded-lg border-2 transition-all ${
              config.defaultStrategy === 'performance'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <TrendingUp className="h-8 w-8 text-blue-600 mx-auto mb-2" />
            <h4 className="font-medium text-gray-900">Performance First</h4>
            <p className="text-xs text-gray-600 mt-1">
              Maximum accuracy and speed, cost is secondary
            </p>
          </button>

          <button
            onClick={() => setConfig({ ...config, defaultStrategy: 'balanced' })}
            className={`p-4 rounded-lg border-2 transition-all ${
              config.defaultStrategy === 'balanced'
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <Target className="h-8 w-8 text-purple-600 mx-auto mb-2" />
            <h4 className="font-medium text-gray-900">Balanced</h4>
            <p className="text-xs text-gray-600 mt-1">
              Optimize for best value across all metrics
            </p>
          </button>
        </div>
      </div>

      {/* Edit Mapping Modal */}
      {editingMapping && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Edit Mapping: {editingMapping.documentType}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recommended Provider
                </label>
                <select
                  value={editingMapping.recommendedProvider}
                  onChange={(e) => setEditingMapping({
                    ...editingMapping,
                    recommendedProvider: e.target.value as AIProvider
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.entries(AI_PROVIDERS).map(([key, provider]) => (
                    <option key={key} value={key}>{provider.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recommended Model
                </label>
                <select
                  value={editingMapping.recommendedModel}
                  onChange={(e) => setEditingMapping({
                    ...editingMapping,
                    recommendedModel: e.target.value
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {AI_MODELS
                    .filter(m => m.provider === editingMapping.recommendedProvider)
                    .map(model => (
                      <option key={model.id} value={model.id}>{model.name}</option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reasoning
                </label>
                <textarea
                  value={editingMapping.reasoning}
                  onChange={(e) => setEditingMapping({
                    ...editingMapping,
                    reasoning: e.target.value
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setEditingMapping(null)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={() => updateMapping(editingMapping)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
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