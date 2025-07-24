import React, { useState } from 'react';
import { Shield, Lock, Bell, Database, FileText, Settings, AlertCircle, Users } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { SecurityDashboard } from './SecurityDashboard';
import { TwoFactorAuth } from './TwoFactorAuth';
import { PrivacyControls } from './PrivacyControls';
import { AuditLogViewer } from './AuditLogViewer';
import { OrganizationSecuritySettings } from './OrganizationSecuritySettings';
import { SecurityNotifications } from './SecurityNotifications';
import { DataManagement } from './DataManagement';
import { SecurityStatusIndicator } from './SecurityStatusIndicator';

type SecurityTab = 'overview' | '2fa' | 'privacy' | 'audit' | 'organization' | 'notifications' | 'data';

export const SecurityPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<SecurityTab>('overview');
  const isAdmin = user?.role === 'admin';

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Shield, component: SecurityDashboard },
    { id: '2fa', label: 'Two-Factor Auth', icon: Lock, component: TwoFactorAuth },
    { id: 'privacy', label: 'Privacy', icon: FileText, component: PrivacyControls },
    { id: 'audit', label: 'Audit Logs', icon: FileText, component: AuditLogViewer, adminOnly: true },
    { id: 'organization', label: 'Organization', icon: Users, component: OrganizationSecuritySettings, adminOnly: true },
    { id: 'notifications', label: 'Notifications', icon: Bell, component: SecurityNotifications },
    { id: 'data', label: 'Data Management', icon: Database, component: DataManagement }
  ].filter(tab => !tab.adminOnly || isAdmin);

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || SecurityDashboard;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <Shield className="h-8 w-8 mr-3 text-blue-600" />
              Security & Privacy
            </h1>
            <SecurityStatusIndicator variant="compact" />
          </div>
          <p className="text-gray-600">
            Manage your security settings, privacy preferences, and compliance requirements
          </p>
        </div>

        {/* Navigation */}
        <div className="bg-white rounded-lg shadow-md mb-6">
          <nav className="flex flex-wrap">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as SecurityTab)}
                  className={`flex items-center px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'text-blue-600 border-blue-600 bg-blue-50'
                      : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <ActiveComponent />

        {/* Security Tips */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-start">
            <AlertCircle className="h-6 w-6 text-blue-600 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-lg font-medium text-blue-900">Security Best Practices</h3>
              <ul className="mt-2 space-y-1 text-sm text-blue-700 list-disc list-inside">
                <li>Enable two-factor authentication for enhanced account security</li>
                <li>Use a unique, strong password and change it regularly</li>
                <li>Review your security alerts and audit logs periodically</li>
                <li>Keep your browser and operating system up to date</li>
                <li>Be cautious of phishing attempts and suspicious emails</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};