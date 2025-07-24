import React, { useState } from 'react';
import { Shield, Users, Activity, Settings, Key, BarChart3 } from 'lucide-react';
import { AnonymizationPage } from './AnonymizationPage';
import { AdminReviewDashboard } from '../components/anonymization/AdminReviewDashboard';
import { SecurityAuditLog } from '../components/anonymization/SecurityAuditLog';
import { APIKeyManager } from '../components/anonymization/APIKeyManager';
import { UsageTracking } from '../components/anonymization/UsageTracking';
import { PerformanceMonitor } from '../components/anonymization/PerformanceMonitor';
import { useAuth } from '../contexts/AuthContext';

export const SecureAIAssistantPage: React.FC = () => {
  const { user } = useAuth();
  const [activeView, setActiveView] = useState<'user' | 'admin' | 'security' | 'settings'>('user');
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({
    openai: '',
    anthropic: '',
    google: ''
  });

  const isAdmin = user?.organizationRole === 'admin';

  const handleKeyUpdate = (provider: string, key: string) => {
    setApiKeys(prev => ({ ...prev, [provider]: key }));
    // Save to backend
    fetch('/api/user/api-keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, key })
    });
  };

  const testConnection = async (provider: string, key: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, key })
      });
      return response.ok;
    } catch {
      return false;
    }
  };

  const navigationItems = [
    { id: 'user', label: 'AI Assistant', icon: Shield, available: true },
    { id: 'admin', label: 'Admin Review', icon: Users, available: isAdmin },
    { id: 'security', label: 'Security & Audit', icon: Activity, available: true },
    { id: 'settings', label: 'Settings & Keys', icon: Settings, available: true }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Shield className="w-6 h-6 text-blue-600" />
              <h1 className="text-xl font-bold">Secure Legal AI Assistant</h1>
            </div>
            
            <nav className="flex gap-1">
              {navigationItems.filter(item => item.available).map(item => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveView(item.id as any)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      activeView === item.id
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1">
        {activeView === 'user' && <AnonymizationPage />}
        
        {activeView === 'admin' && isAdmin && user && (
          <div className="max-w-7xl mx-auto px-4 py-8">
            <AdminReviewDashboard organizationId={user.organizationId} />
          </div>
        )}
        
        {activeView === 'security' && user && (
          <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
            <SecurityAuditLog 
              organizationId={user.organizationId} 
              userId={user.id}
            />
            <PerformanceMonitor />
          </div>
        )}
        
        {activeView === 'settings' && user && (
          <div className="max-w-7xl mx-auto px-4 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Key className="w-5 h-5 text-blue-600" />
                    API Key Management
                  </h2>
                  <div className="space-y-4">
                    <APIKeyManager
                      provider="openai"
                      currentKey={apiKeys.openai}
                      onKeyUpdate={(key) => handleKeyUpdate('openai', key)}
                      onTestConnection={(key) => testConnection('openai', key)}
                    />
                    <APIKeyManager
                      provider="anthropic"
                      currentKey={apiKeys.anthropic}
                      onKeyUpdate={(key) => handleKeyUpdate('anthropic', key)}
                      onTestConnection={(key) => testConnection('anthropic', key)}
                    />
                    <APIKeyManager
                      provider="google"
                      currentKey={apiKeys.google}
                      onKeyUpdate={(key) => handleKeyUpdate('google', key)}
                      onTestConnection={(key) => testConnection('google', key)}
                    />
                  </div>
                </div>
              </div>
              
              <div>
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-blue-600" />
                  Usage & Billing
                </h2>
                <UsageTracking 
                  userId={user.id} 
                  organizationId={user.organizationId}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};