import React, { useState, useEffect } from 'react';
import { 
  Settings, Plus, Trash2, Edit2, Save, X, 
  FileText, Shield, Zap, Info, CheckCircle,
  AlertTriangle, Play, Pause
} from 'lucide-react';
import { DocumentConsentSettings } from './DocumentConsent';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';

interface ConsentRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  conditions: {
    documentTypes?: string[];
    keywords?: string[];
    senders?: string[];
    jurisdictions?: string[];
    sensitivityThreshold?: 'any' | 'internal' | 'confidential' | 'highly-sensitive';
  };
  actions: {
    setSensitivityLevel?: DocumentConsentSettings['sensitivityLevel'];
    allowAIProcessing?: boolean;
    allowModelTraining?: boolean;
    allowAnalytics?: boolean;
    requireManualReview?: boolean;
    notifyUsers?: string[];
  };
  priority: number;
  createdAt: string;
  updatedAt: string;
  matchCount: number;
}

interface ConsentWorkflow {
  id: string;
  organizationId: string;
  rules: ConsentRule[];
  defaultConsent: DocumentConsentSettings['restrictions'];
  automationEnabled: boolean;
}

export const ConsentAutomation: React.FC = () => {
  const { user } = useAuth();
  const [workflow, setWorkflow] = useState<ConsentWorkflow | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [editingRule, setEditingRule] = useState<ConsentRule | null>(null);
  const [showNewRule, setShowNewRule] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');

  const documentTypes = [
    'Contract', 'NDA', 'Legal Brief', 'Court Filing', 
    'Patent', 'License Agreement', 'Employment Agreement',
    'Financial Document', 'Medical Record', 'Other'
  ];

  const sensitivityLevels = [
    { value: 'any', label: 'Any Level', color: 'text-gray-600' },
    { value: 'internal', label: 'Internal or Higher', color: 'text-blue-600' },
    { value: 'confidential', label: 'Confidential or Higher', color: 'text-yellow-600' },
    { value: 'highly-sensitive', label: 'Highly Sensitive Only', color: 'text-red-600' }
  ];

  useEffect(() => {
    fetchWorkflow();
  }, []);

  const fetchWorkflow = async () => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/consent-workflow`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setWorkflow(data);
      }
    } catch (error) {
      console.error('Failed to fetch consent workflow:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleAutomation = async () => {
    if (!workflow) return;

    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/consent-workflow`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          ...workflow,
          automationEnabled: !workflow.automationEnabled
        })
      });

      if (response.ok) {
        setWorkflow(prev => prev ? { ...prev, automationEnabled: !prev.automationEnabled } : null);
        setToastMessage(workflow.automationEnabled ? 'Automation disabled' : 'Automation enabled');
        setToastType('success');
        setShowToast(true);
      }
    } catch (error) {
      setToastMessage('Failed to toggle automation');
      setToastType('error');
      setShowToast(true);
    }
  };

  const saveRule = async (rule: ConsentRule) => {
    if (!workflow) return;

    try {
      const updatedRules = editingRule
        ? workflow.rules.map(r => r.id === rule.id ? rule : r)
        : [...workflow.rules, { ...rule, id: Date.now().toString() }];

      const response = await fetch(`/api/organizations/${user?.organizationId}/consent-workflow`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          ...workflow,
          rules: updatedRules
        })
      });

      if (response.ok) {
        await fetchWorkflow();
        setEditingRule(null);
        setShowNewRule(false);
        setToastMessage('Rule saved successfully');
        setToastType('success');
        setShowToast(true);
      }
    } catch (error) {
      setToastMessage('Failed to save rule');
      setToastType('error');
      setShowToast(true);
    }
  };

  const deleteRule = async (ruleId: string) => {
    if (!workflow || !confirm('Are you sure you want to delete this rule?')) return;

    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/consent-workflow`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          ...workflow,
          rules: workflow.rules.filter(r => r.id !== ruleId)
        })
      });

      if (response.ok) {
        await fetchWorkflow();
        setToastMessage('Rule deleted successfully');
        setToastType('success');
        setShowToast(true);
      }
    } catch (error) {
      setToastMessage('Failed to delete rule');
      setToastType('error');
      setShowToast(true);
    }
  };

  const RuleEditor: React.FC<{ rule: ConsentRule; onSave: (rule: ConsentRule) => void; onCancel: () => void }> = ({ 
    rule, 
    onSave, 
    onCancel 
  }) => {
    const [editedRule, setEditedRule] = useState(rule);

    return (
      <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">
          {rule.id ? 'Edit Rule' : 'New Consent Rule'}
        </h4>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name</label>
            <input
              type="text"
              value={editedRule.name}
              onChange={(e) => setEditedRule({ ...editedRule, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Medical Records Protection"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={editedRule.description}
              onChange={(e) => setEditedRule({ ...editedRule, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="Describe what this rule does..."
            />
          </div>

          {/* Conditions */}
          <div className="border-t border-gray-200 pt-4">
            <h5 className="text-sm font-semibold text-gray-700 mb-3">Conditions (when to apply)</h5>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Document Types</label>
                <div className="grid grid-cols-3 gap-2">
                  {documentTypes.map(type => (
                    <label key={type} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={editedRule.conditions.documentTypes?.includes(type) || false}
                        onChange={(e) => {
                          const types = editedRule.conditions.documentTypes || [];
                          setEditedRule({
                            ...editedRule,
                            conditions: {
                              ...editedRule.conditions,
                              documentTypes: e.target.checked
                                ? [...types, type]
                                : types.filter(t => t !== type)
                            }
                          });
                        }}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-sm">{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-600 mb-1">Keywords (comma-separated)</label>
                <input
                  type="text"
                  value={editedRule.conditions.keywords?.join(', ') || ''}
                  onChange={(e) => setEditedRule({
                    ...editedRule,
                    conditions: {
                      ...editedRule.conditions,
                      keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
                    }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., confidential, proprietary, trade secret"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-600 mb-1">Minimum Sensitivity Level</label>
                <select
                  value={editedRule.conditions.sensitivityThreshold || 'any'}
                  onChange={(e) => setEditedRule({
                    ...editedRule,
                    conditions: {
                      ...editedRule.conditions,
                      sensitivityThreshold: e.target.value as any
                    }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {sensitivityLevels.map(level => (
                    <option key={level.value} value={level.value}>
                      {level.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="border-t border-gray-200 pt-4">
            <h5 className="text-sm font-semibold text-gray-700 mb-3">Actions (what to do)</h5>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Set Sensitivity Level</label>
                <select
                  value={editedRule.actions.setSensitivityLevel || ''}
                  onChange={(e) => setEditedRule({
                    ...editedRule,
                    actions: {
                      ...editedRule.actions,
                      setSensitivityLevel: e.target.value as any || undefined
                    }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Don't change</option>
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="highly-sensitive">Highly Sensitive</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={editedRule.actions.allowAIProcessing !== undefined}
                    onChange={(e) => setEditedRule({
                      ...editedRule,
                      actions: {
                        ...editedRule.actions,
                        allowAIProcessing: e.target.checked ? true : undefined
                      }
                    })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">Set AI Processing Permission</span>
                </label>
                
                {editedRule.actions.allowAIProcessing !== undefined && (
                  <div className="ml-6">
                    <label className="flex items-center space-x-2">
                      <input
                        type="radio"
                        checked={editedRule.actions.allowAIProcessing === true}
                        onChange={() => setEditedRule({
                          ...editedRule,
                          actions: { ...editedRule.actions, allowAIProcessing: true }
                        })}
                      />
                      <span className="text-sm">Allow</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input
                        type="radio"
                        checked={editedRule.actions.allowAIProcessing === false}
                        onChange={() => setEditedRule({
                          ...editedRule,
                          actions: { ...editedRule.actions, allowAIProcessing: false }
                        })}
                      />
                      <span className="text-sm">Deny</span>
                    </label>
                  </div>
                )}
              </div>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={editedRule.actions.requireManualReview || false}
                  onChange={(e) => setEditedRule({
                    ...editedRule,
                    actions: {
                      ...editedRule.actions,
                      requireManualReview: e.target.checked
                    }
                  })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700">Require Manual Review</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 hover:text-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={() => onSave(editedRule)}
              disabled={!editedRule.name}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              Save Rule
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (isLoading || !workflow) {
    return <div className="animate-pulse h-96 bg-gray-100 rounded-lg"></div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Settings className="h-6 w-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">Automated Consent Workflows</h3>
          </div>
          
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleAutomation}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
                workflow.automationEnabled
                  ? 'bg-green-100 text-green-700 hover:bg-green-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {workflow.automationEnabled ? (
                <>
                  <Play className="h-4 w-4" />
                  <span>Automation Active</span>
                </>
              ) : (
                <>
                  <Pause className="h-4 w-4" />
                  <span>Automation Paused</span>
                </>
              )}
            </button>

            <button
              onClick={() => setShowNewRule(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              <span>Add Rule</span>
            </button>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-900">How Consent Automation Works</p>
              <p className="text-sm text-blue-800 mt-1">
                Rules are applied in priority order when documents are uploaded. The first matching rule 
                determines the consent settings. Manual review requests bypass automation.
              </p>
            </div>
          </div>
        </div>

        {/* Rules List */}
        <div className="space-y-4">
          {showNewRule && (
            <RuleEditor
              rule={{
                id: '',
                name: '',
                description: '',
                enabled: true,
                conditions: {},
                actions: {},
                priority: workflow.rules.length + 1,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                matchCount: 0
              }}
              onSave={saveRule}
              onCancel={() => setShowNewRule(false)}
            />
          )}

          {editingRule && (
            <RuleEditor
              rule={editingRule}
              onSave={saveRule}
              onCancel={() => setEditingRule(null)}
            />
          )}

          {workflow.rules
            .sort((a, b) => a.priority - b.priority)
            .map((rule, index) => (
              <div
                key={rule.id}
                className={`bg-white rounded-lg border p-4 ${
                  rule.enabled ? 'border-gray-200' : 'border-gray-200 opacity-60'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="text-sm text-gray-500">#{index + 1}</span>
                      <h4 className="font-medium text-gray-900">{rule.name}</h4>
                      {rule.enabled ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-gray-400" />
                      )}
                      {rule.actions.requireManualReview && (
                        <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-full">
                          Manual Review
                        </span>
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-3">{rule.description}</p>
                    
                    <div className="flex items-center space-x-6 text-xs text-gray-500">
                      <span>Applied {rule.matchCount} times</span>
                      <span>Updated {new Date(rule.updatedAt).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setEditingRule(rule)}
                      className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-md"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}

          {workflow.rules.length === 0 && !showNewRule && (
            <div className="text-center py-12 text-gray-500">
              <Shield className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p>No automation rules configured</p>
              <p className="text-sm mt-1">Add rules to automate consent decisions</p>
            </div>
          )}
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
  );
};