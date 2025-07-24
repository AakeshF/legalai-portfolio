import React, { useState } from 'react';
import { 
  Settings, Shield, Key, DollarSign, BarChart3, Brain,
  Zap, Users, ChevronRight
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { AIProviderSettings } from '../components/ai-config/AIProviderSettings';
import { EnhancedAPIKeyManager } from '../components/ai-config/EnhancedAPIKeyManager';
import { CostOptimizer } from '../components/ai-config/CostOptimizer';
import { AIProviderAnalytics } from '../components/ai-config/AIProviderAnalytics';
import { SmartProviderSelector } from '../components/ai-config/SmartProviderSelector';
import { ConsentAutomation } from '../components/consent/ConsentAutomation';
import { MultiLevelConsentManager } from '../components/consent/MultiLevelConsentManager';
import { ConsentScope } from '../types/consent';

type TabId = 'provider' | 'keys' | 'consent' | 'cost' | 'analytics' | 'smart' | 'automation';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ElementType;
  adminOnly?: boolean;
  description: string;
}

export const AIConfigurationPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>('provider');
  const isAdmin = user?.role === 'admin';

  const tabs: Tab[] = [
    {
      id: 'provider',
      label: 'Provider Settings',
      icon: Settings,
      description: 'Configure AI providers and models',
      adminOnly: true
    },
    {
      id: 'keys',
      label: 'API Keys',
      icon: Key,
      description: 'Manage API keys and rotation',
      adminOnly: true
    },
    {
      id: 'consent',
      label: 'Consent Management',
      icon: Shield,
      description: 'Configure consent policies',
      adminOnly: false
    },
    {
      id: 'automation',
      label: 'Consent Automation',
      icon: Zap,
      description: 'Automated consent workflows',
      adminOnly: true
    },
    {
      id: 'cost',
      label: 'Cost Optimization',
      icon: DollarSign,
      description: 'Monitor and optimize AI costs',
      adminOnly: false
    },
    {
      id: 'analytics',
      label: 'Performance',
      icon: BarChart3,
      description: 'Provider performance analytics',
      adminOnly: false
    },
    {
      id: 'smart',
      label: 'Smart Selection',
      icon: Brain,
      description: 'Intelligent provider selection',
      adminOnly: true
    }
  ];

  const filteredTabs = tabs.filter(tab => !tab.adminOnly || isAdmin);

  const renderContent = () => {
    switch (activeTab) {
      case 'provider':
        return (
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-blue-900 mb-2">Provider Selection Hierarchy</h3>
              <ol className="space-y-1 text-sm text-blue-800">
                <li>1. <strong>Per-Request Override</strong> - Switch providers in real-time</li>
                <li>2. <strong>User Preference</strong> - Personal provider settings (if enabled)</li>
                <li>3. <strong>Organization Default</strong> - Set by administrators</li>
                <li>4. <strong>System Default</strong> - Platform fallback</li>
              </ol>
            </div>
            <AIProviderSettings />
          </div>
        );
      
      case 'keys':
        return <EnhancedAPIKeyManager />;
      
      case 'consent':
        return (
          <div className="space-y-6">
            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Multi-Level Consent System</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">Organization Level</h4>
                  <MultiLevelConsentManager scope={ConsentScope.ORGANIZATION} />
                </div>
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">User Level</h4>
                  <MultiLevelConsentManager scope={ConsentScope.USER} />
                </div>
              </div>
            </div>
          </div>
        );
      
      case 'automation':
        return <ConsentAutomation />;
      
      case 'cost':
        return <CostOptimizer />;
      
      case 'analytics':
        return <AIProviderAnalytics />;
      
      case 'smart':
        return <SmartProviderSelector />;
      
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">AI Configuration</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Manage AI providers, consent, and optimization settings
                </p>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Users className="h-4 w-4" />
                <span>{user?.role === 'admin' ? 'Administrator' : 'User'} View</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar Navigation */}
          <div className="lg:w-64">
            <nav className="space-y-1">
              {filteredTabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center justify-between px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className="h-5 w-5" />
                      <span>{tab.label}</span>
                    </div>
                    {activeTab === tab.id && <ChevronRight className="h-4 w-4" />}
                  </button>
                );
              })}
            </nav>

            {/* Help Section */}
            <div className="mt-8 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Need Help?</h3>
              <p className="text-xs text-gray-600 mb-3">
                {tabs.find(t => t.id === activeTab)?.description}
              </p>
              <a href="#" className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                View Documentation →
              </a>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  );
};