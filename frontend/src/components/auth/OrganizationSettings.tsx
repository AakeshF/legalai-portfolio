import React, { useState } from 'react';
import { Building2, CreditCard, TrendingUp, HardDrive, FileText, Users, Brain } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';
import { AIProviderSettings } from '../ai-config/AIProviderSettings';

export const OrganizationSettings: React.FC = () => {
  const { organization, user } = useAuth();
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [orgName, setOrgName] = useState(organization?.name || '');

  const isAdmin = user?.role === 'admin';

  const getSubscriptionBadge = (tier: string) => {
    const badges = {
      trial: { color: 'bg-yellow-100 text-yellow-800', label: 'Trial' },
      professional: { color: 'bg-blue-100 text-blue-800', label: 'Professional' },
      enterprise: { color: 'bg-purple-100 text-purple-800', label: 'Enterprise' }
    };
    return badges[tier as keyof typeof badges] || badges.trial;
  };

  const handleSaveName = () => {
    setToastMessage('Organization name updated successfully');
    setShowToast(true);
    setIsEditingName(false);
  };

  const formatBytes = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const subscription = getSubscriptionBadge(organization?.subscription || 'trial');

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Organization Settings</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${subscription.color}`}>
          {subscription.label}
        </span>
      </div>

      <div className="space-y-8">
        <div>
          <div className="flex items-center mb-4">
            <Building2 className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Organization Details</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Organization Name
              </label>
              {isEditingName && isAdmin ? (
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={handleSaveName}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setOrgName(organization?.name || '');
                      setIsEditingName(false);
                    }}
                    className="px-4 py-2 text-gray-600 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <p className="text-gray-900">{organization?.name}</p>
                  {isAdmin && (
                    <button
                      onClick={() => setIsEditingName(true)}
                      className="text-sm text-blue-600 hover:text-blue-500"
                    >
                      Edit
                    </button>
                  )}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Organization ID
              </label>
              <p className="text-gray-500 font-mono text-sm">{organization?.id}</p>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center mb-4">
            <TrendingUp className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Usage Statistics</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <FileText className="h-8 w-8 text-blue-600" />
                <span className="text-2xl font-semibold text-gray-900">
                  {organization?.usageStats.documentsProcessed || 0}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-2">Documents Processed</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <TrendingUp className="h-8 w-8 text-green-600" />
                <span className="text-2xl font-semibold text-gray-900">
                  {organization?.usageStats.apiCalls || 0}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-2">API Calls</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <HardDrive className="h-8 w-8 text-purple-600" />
                <span className="text-2xl font-semibold text-gray-900">
                  {formatBytes(organization?.usageStats.storageUsed || 0)}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-2">Storage Used</p>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center mb-4">
            <CreditCard className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Billing & Subscription</h3>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm text-gray-600">Current Plan</p>
                <p className="text-lg font-medium text-gray-900">
                  {subscription.label} Plan
                </p>
              </div>
              {isAdmin && (
                <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                  Upgrade Plan
                </button>
              )}
            </div>
            
            {organization?.subscription === 'trial' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mt-4">
                <p className="text-sm text-yellow-800">
                  Your trial expires in 23 days. Upgrade to continue using all features.
                </p>
              </div>
            )}
          </div>
        </div>

        {isAdmin && (
          <>
            <div>
              <div className="flex items-center mb-4">
                <Brain className="h-5 w-5 text-gray-400 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">AI Configuration</h3>
              </div>
              <AIProviderSettings />
            </div>

            <div>
              <div className="flex items-center mb-4">
                <Users className="h-5 w-5 text-gray-400 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">Quick Actions</h3>
              </div>
              
              <div className="flex flex-wrap gap-3">
                <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                  Manage Users
                </button>
                <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                  View Audit Logs
                </button>
                <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                  Export Data
                </button>
                <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                  API Settings
                </button>
              </div>
            </div>
          </>
        )}
      </div>

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