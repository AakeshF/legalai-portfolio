import React, { useState } from 'react';
import { Shield, Settings, AlertTriangle, Plus, Trash2, Save } from 'lucide-react';
import { AnonymizationSettings as AnonymizationSettingsType, SensitiveDataPattern } from '../../types/anonymization';
import { AIProvider, AI_MODELS } from '../ai-config/types';

interface AnonymizationSettingsProps {
  settings: AnonymizationSettingsType;
  onSettingsChange: (settings: AnonymizationSettingsType) => void;
  organizationLocked?: boolean;
  selectedModel?: string;
  onModelChange?: (model: string) => void;
}

const CATEGORY_OPTIONS = [
  { id: 'personal', label: 'Personal Information', icon: '👤' },
  { id: 'financial', label: 'Financial Data', icon: '💳' },
  { id: 'medical', label: 'Medical Information', icon: '🏥' },
  { id: 'legal', label: 'Legal Identifiers', icon: '⚖️' },
  { id: 'custom', label: 'Custom Patterns', icon: '🔧' }
];

export const AnonymizationSettings: React.FC<AnonymizationSettingsProps> = ({
  settings,
  onSettingsChange,
  organizationLocked = false,
  selectedModel,
  onModelChange
}) => {
  const [showCustomPatternForm, setShowCustomPatternForm] = useState(false);
  const [newPattern, setNewPattern] = useState<Partial<SensitiveDataPattern>>({
    type: 'custom',
    severity: 'medium'
  });

  const handleAutoRedactionToggle = () => {
    if (!organizationLocked) {
      onSettingsChange({
        ...settings,
        autoRedactionEnabled: !settings.autoRedactionEnabled
      });
    }
  };

  const handleSensitivityChange = (threshold: 'low' | 'medium' | 'high') => {
    onSettingsChange({
      ...settings,
      sensitivityThreshold: threshold
    });
  };

  const handleCategoryToggle = (categoryId: string) => {
    const updatedCategories = settings.enabledCategories.includes(categoryId)
      ? settings.enabledCategories.filter(id => id !== categoryId)
      : [...settings.enabledCategories, categoryId];
    
    onSettingsChange({
      ...settings,
      enabledCategories: updatedCategories
    });
  };

  const handleAddCustomPattern = () => {
    if (newPattern.pattern && newPattern.replacement && newPattern.description) {
      const pattern: SensitiveDataPattern = {
        id: `custom-${Date.now()}`,
        type: 'custom',
        pattern: newPattern.pattern,
        replacement: newPattern.replacement,
        severity: newPattern.severity || 'medium',
        description: newPattern.description
      };
      
      onSettingsChange({
        ...settings,
        customPatterns: [...settings.customPatterns, pattern]
      });
      
      setNewPattern({ type: 'custom', severity: 'medium' });
      setShowCustomPatternForm(false);
    }
  };

  const handleRemoveCustomPattern = (patternId: string) => {
    onSettingsChange({
      ...settings,
      customPatterns: settings.customPatterns.filter(p => p.id !== patternId)
    });
  };

  const availableModels = AI_MODELS.filter(model => 
    model.provider === 'openai' || model.provider === 'anthropic' || model.id === '[ai-provider]-demo'
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 pb-4 border-b">
        <Shield className="w-6 h-6 text-blue-600" />
        <h2 className="text-xl font-semibold">Anonymization Settings</h2>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-3">
            <Settings className="w-5 h-5 text-gray-600" />
            <div>
              <h3 className="font-medium">Auto-Redaction</h3>
              <p className="text-sm text-gray-600">
                Automatically detect and redact sensitive information
              </p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.autoRedactionEnabled}
              onChange={handleAutoRedactionToggle}
              disabled={organizationLocked}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {organizationLocked && (
          <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
            <p className="text-sm text-amber-700">
              Auto-redaction is controlled by your organization's security policy
            </p>
          </div>
        )}

        {settings.autoRedactionEnabled && (
          <>
            <div className="space-y-3">
              <h3 className="font-medium text-gray-700">Sensitivity Level</h3>
              <div className="flex gap-2">
                {(['low', 'medium', 'high'] as const).map(level => (
                  <button
                    key={level}
                    onClick={() => handleSensitivityChange(level)}
                    className={`px-4 py-2 rounded-lg border transition-colors ${
                      settings.sensitivityThreshold === level
                        ? 'bg-blue-50 border-blue-300 text-blue-700'
                        : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="font-medium text-gray-700">Detection Categories</h3>
              <div className="space-y-2">
                {CATEGORY_OPTIONS.map(category => (
                  <label
                    key={category.id}
                    className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50"
                  >
                    <input
                      type="checkbox"
                      checked={settings.enabledCategories.includes(category.id)}
                      onChange={() => handleCategoryToggle(category.id)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-xl">{category.icon}</span>
                    <span className="font-medium">{category.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-700">Custom Patterns</h3>
                <button
                  onClick={() => setShowCustomPatternForm(true)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                >
                  <Plus className="w-4 h-4" />
                  Add Pattern
                </button>
              </div>

              {showCustomPatternForm && (
                <div className="p-4 bg-gray-50 rounded-lg space-y-3">
                  <input
                    type="text"
                    placeholder="Pattern (regex)"
                    value={newPattern.pattern as string || ''}
                    onChange={(e) => setNewPattern({ ...newPattern, pattern: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="Replacement text (e.g., [REDACTED])"
                    value={newPattern.replacement || ''}
                    onChange={(e) => setNewPattern({ ...newPattern, replacement: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="Description"
                    value={newPattern.description || ''}
                    onChange={(e) => setNewPattern({ ...newPattern, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <select
                    value={newPattern.severity || 'medium'}
                    onChange={(e) => setNewPattern({ ...newPattern, severity: e.target.value as any })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low Severity</option>
                    <option value="medium">Medium Severity</option>
                    <option value="high">High Severity</option>
                    <option value="critical">Critical Severity</option>
                  </select>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setShowCustomPatternForm(false)}
                      className="px-3 py-1 text-gray-600 hover:text-gray-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleAddCustomPattern}
                      className="px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Add
                    </button>
                  </div>
                </div>
              )}

              {settings.customPatterns.length > 0 && (
                <div className="space-y-2">
                  {settings.customPatterns.map(pattern => (
                    <div
                      key={pattern.id}
                      className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{pattern.description}</p>
                        <p className="text-sm text-gray-600">
                          Replace with: {pattern.replacement}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveCustomPattern(pattern.id)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {onModelChange && (
          <div className="space-y-3 pt-4 border-t">
            <h3 className="font-medium text-gray-700">AI Model Selection</h3>
            <select
              value={selectedModel || ''}
              onChange={(e) => onModelChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a model...</option>
              {availableModels.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name} ({model.provider})
                </option>
              ))}
              <option value="[ai-provider]-demo">DeepSeek Demo (Limited)</option>
            </select>
          </div>
        )}

        <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
          <input
            type="checkbox"
            id="require-approval"
            checked={settings.requireApprovalForSensitive}
            onChange={(e) => onSettingsChange({
              ...settings,
              requireApprovalForSensitive: e.target.checked
            })}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
          <label htmlFor="require-approval" className="flex-1">
            <p className="font-medium text-blue-900">Require approval for sensitive prompts</p>
            <p className="text-sm text-blue-700">
              Prompts containing sensitive data will be sent for review before processing
            </p>
          </label>
        </div>
      </div>
    </div>
  );
};