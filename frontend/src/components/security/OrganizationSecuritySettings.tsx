import React, { useState, useEffect } from 'react';
import { Shield, Globe, Clock, Lock, Plus, Trash2, AlertCircle, CheckCircle, Info, Users } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { Toast } from '../SimpleToast';
import { API_ENDPOINTS, buildUrl } from '../../config/api.config';

interface IPRestriction {
  id: string;
  ipAddress: string;
  description: string;
  type: 'allow' | 'deny';
  createdAt: string;
  createdBy: string;
}

interface SessionSettings {
  sessionTimeout: number; // minutes
  maxConcurrentSessions: number;
  requireReauthForSensitive: boolean;
  idleTimeout: number; // minutes
  rememberMeEnabled: boolean;
  rememberMeDuration: number; // days
}

interface PasswordPolicy {
  minLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireNumbers: boolean;
  requireSpecialChars: boolean;
  passwordExpiry: number; // days
  preventReuse: number; // number of previous passwords
  requireChangeOnFirstLogin: boolean;
}

interface SecuritySettings {
  ipRestrictions: IPRestriction[];
  sessionSettings: SessionSettings;
  passwordPolicy: PasswordPolicy;
  enforceIPRestrictions: boolean;
  allowedCountries: string[];
  blockedCountries: string[];
  geoBlockingEnabled: boolean;
}

export const OrganizationSecuritySettings: React.FC = () => {
  const { user, organization } = useAuth();
  const [settings, setSettings] = useState<SecuritySettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');
  const [activeTab, setActiveTab] = useState<'ip' | 'session' | 'password'>('ip');
  const [newIP, setNewIP] = useState({ address: '', description: '', type: 'allow' as 'allow' | 'deny' });
  const [showAddIP, setShowAddIP] = useState(false);

  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    fetchSecuritySettings();
  }, []);

  const fetchSecuritySettings = async () => {
    try {
      const response = await api.get(API_ENDPOINTS.organization.security.settings);
      if (response.data) {
        setSettings(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch security settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateSettings = async (updates: Partial<SecuritySettings>) => {
    if (!settings || !isAdmin) return;

    setIsSaving(true);
    try {
      const response = await api.patch(API_ENDPOINTS.organization.security.settings, updates);
      if (response.data) {
        setSettings({ ...settings, ...updates });
        showNotification('Security settings updated successfully', 'success');
      }
    } catch (error) {
      showNotification('Failed to update security settings', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const addIPRestriction = async () => {
    if (!newIP.address || !isAdmin) return;

    try {
      const response = await api.post(API_ENDPOINTS.organization.security.ipRestrictions, newIP);
      if (response.data) {
        setSettings({
          ...settings!,
          ipRestrictions: [...settings!.ipRestrictions, response.data]
        });
        setNewIP({ address: '', description: '', type: 'allow' });
        setShowAddIP(false);
        showNotification('IP restriction added successfully', 'success');
      }
    } catch (error) {
      showNotification('Failed to add IP restriction', 'error');
    }
  };

  const removeIPRestriction = async (id: string) => {
    if (!isAdmin || !confirm('Are you sure you want to remove this IP restriction?')) return;

    try {
      const url = buildUrl(API_ENDPOINTS.organization.security.removeIpRestriction, { id });
      await api.delete(url);
      setSettings({
        ...settings!,
        ipRestrictions: settings!.ipRestrictions.filter(ip => ip.id !== id)
      });
      showNotification('IP restriction removed successfully', 'success');
    } catch (error) {
      showNotification('Failed to remove IP restriction', 'error');
    }
  };

  const showNotification = (message: string, type: 'success' | 'error') => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
  };

  const validateIPAddress = (ip: string) => {
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
    const ipv6Regex = /^([\da-fA-F]{1,4}:){7}[\da-fA-F]{1,4}(\/\d{1,3})?$/;
    return ipv4Regex.test(ip) || ipv6Regex.test(ip);
  };

  if (isLoading || !settings) {
    return <div className="animate-pulse h-96 bg-gray-200 rounded-lg"></div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
          <Shield className="h-6 w-6 mr-2 text-blue-600" />
          Organization Security Settings
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Configure security policies for {organization?.name}
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex">
          <button
            onClick={() => setActiveTab('ip')}
            className={`py-2 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'ip'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            IP Restrictions
          </button>
          <button
            onClick={() => setActiveTab('session')}
            className={`py-2 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'session'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Session Management
          </button>
          <button
            onClick={() => setActiveTab('password')}
            className={`py-2 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'password'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Password Policy
          </button>
        </nav>
      </div>

      <div className="p-6">
        {/* IP Restrictions Tab */}
        {activeTab === 'ip' && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">IP Address Restrictions</h3>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.enforceIPRestrictions}
                    onChange={(e) => updateSettings({ enforceIPRestrictions: e.target.checked })}
                    disabled={!isAdmin}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">Enforce IP restrictions</span>
                </label>
              </div>

              {settings.enforceIPRestrictions && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div className="ml-3">
                      <p className="text-sm text-yellow-700">
                        When enabled, only IP addresses in the allow list can access the organization.
                        Ensure your current IP is included before enabling.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                {settings.ipRestrictions.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No IP restrictions configured</p>
                ) : (
                  settings.ipRestrictions.map((restriction) => (
                    <div
                      key={restriction.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex items-center space-x-4">
                        <Globe className={`h-5 w-5 ${
                          restriction.type === 'allow' ? 'text-green-500' : 'text-red-500'
                        }`} />
                        <div>
                          <p className="font-medium text-gray-900">{restriction.ipAddress}</p>
                          <p className="text-sm text-gray-600">{restriction.description}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            Added by {restriction.createdBy} on {new Date(restriction.createdAt).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          restriction.type === 'allow'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {restriction.type}
                        </span>
                        {isAdmin && (
                          <button
                            onClick={() => removeIPRestriction(restriction.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {isAdmin && (
                <div className="mt-4">
                  {showAddIP ? (
                    <div className="border rounded-lg p-4 space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          IP Address or CIDR
                        </label>
                        <input
                          type="text"
                          value={newIP.address}
                          onChange={(e) => setNewIP({ ...newIP, address: e.target.value })}
                          placeholder="192.168.1.1 or 192.168.1.0/24"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <input
                          type="text"
                          value={newIP.description}
                          onChange={(e) => setNewIP({ ...newIP, description: e.target.value })}
                          placeholder="Office network"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Type
                        </label>
                        <select
                          value={newIP.type}
                          onChange={(e) => setNewIP({ ...newIP, type: e.target.value as 'allow' | 'deny' })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="allow">Allow</option>
                          <option value="deny">Deny</option>
                        </select>
                      </div>
                      <div className="flex justify-end space-x-3">
                        <button
                          onClick={() => {
                            setShowAddIP(false);
                            setNewIP({ address: '', description: '', type: 'allow' });
                          }}
                          className="px-4 py-2 text-gray-700 hover:text-gray-800"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={addIPRestriction}
                          disabled={!validateIPAddress(newIP.address)}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                          Add IP Restriction
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowAddIP(true)}
                      className="flex items-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add IP Restriction
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Session Management Tab */}
        {activeTab === 'session' && (
          <div className="space-y-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Session Management</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Session Timeout
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={settings.sessionSettings.sessionTimeout}
                    onChange={(e) => updateSettings({
                      sessionSettings: { ...settings.sessionSettings, sessionTimeout: parseInt(e.target.value) }
                    })}
                    disabled={!isAdmin}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    min="15"
                    max="1440"
                  />
                  <span className="text-sm text-gray-600">minutes</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Time before users are automatically logged out
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Idle Timeout
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={settings.sessionSettings.idleTimeout}
                    onChange={(e) => updateSettings({
                      sessionSettings: { ...settings.sessionSettings, idleTimeout: parseInt(e.target.value) }
                    })}
                    disabled={!isAdmin}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    min="5"
                    max="120"
                  />
                  <span className="text-sm text-gray-600">minutes</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Time of inactivity before requiring re-authentication
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Concurrent Sessions
                </label>
                <input
                  type="number"
                  value={settings.sessionSettings.maxConcurrentSessions}
                  onChange={(e) => updateSettings({
                    sessionSettings: { ...settings.sessionSettings, maxConcurrentSessions: parseInt(e.target.value) }
                  })}
                  disabled={!isAdmin}
                  className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="10"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Number of devices a user can be logged in from
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Remember Me Duration
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={settings.sessionSettings.rememberMeDuration}
                    onChange={(e) => updateSettings({
                      sessionSettings: { ...settings.sessionSettings, rememberMeDuration: parseInt(e.target.value) }
                    })}
                    disabled={!isAdmin || !settings.sessionSettings.rememberMeEnabled}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    min="1"
                    max="90"
                  />
                  <span className="text-sm text-gray-600">days</span>
                </div>
              </div>
            </div>

            <div className="space-y-3 pt-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.sessionSettings.requireReauthForSensitive}
                  onChange={(e) => updateSettings({
                    sessionSettings: { ...settings.sessionSettings, requireReauthForSensitive: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Require re-authentication for sensitive operations
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.sessionSettings.rememberMeEnabled}
                  onChange={(e) => updateSettings({
                    sessionSettings: { ...settings.sessionSettings, rememberMeEnabled: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Allow "Remember Me" option at login
                </span>
              </label>
            </div>

            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start">
                <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                <div className="ml-3">
                  <h4 className="font-medium text-blue-900">Active Sessions</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    Users can manage their active sessions from their security settings.
                    Administrators can force logout users from the user management interface.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Password Policy Tab */}
        {activeTab === 'password' && (
          <div className="space-y-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Password Policy</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Password Length
                </label>
                <input
                  type="number"
                  value={settings.passwordPolicy.minLength}
                  onChange={(e) => updateSettings({
                    passwordPolicy: { ...settings.passwordPolicy, minLength: parseInt(e.target.value) }
                  })}
                  disabled={!isAdmin}
                  className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  min="8"
                  max="32"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password Expiry
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={settings.passwordPolicy.passwordExpiry}
                    onChange={(e) => updateSettings({
                      passwordPolicy: { ...settings.passwordPolicy, passwordExpiry: parseInt(e.target.value) }
                    })}
                    disabled={!isAdmin}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    min="0"
                    max="365"
                  />
                  <span className="text-sm text-gray-600">days</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Set to 0 to disable password expiry
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password History
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={settings.passwordPolicy.preventReuse}
                    onChange={(e) => updateSettings({
                      passwordPolicy: { ...settings.passwordPolicy, preventReuse: parseInt(e.target.value) }
                    })}
                    disabled={!isAdmin}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    min="0"
                    max="24"
                  />
                  <span className="text-sm text-gray-600">passwords</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Prevent reuse of recent passwords
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-4">
              <h4 className="text-sm font-medium text-gray-700">Password Requirements</h4>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.passwordPolicy.requireUppercase}
                  onChange={(e) => updateSettings({
                    passwordPolicy: { ...settings.passwordPolicy, requireUppercase: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Require uppercase letters (A-Z)
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.passwordPolicy.requireLowercase}
                  onChange={(e) => updateSettings({
                    passwordPolicy: { ...settings.passwordPolicy, requireLowercase: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Require lowercase letters (a-z)
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.passwordPolicy.requireNumbers}
                  onChange={(e) => updateSettings({
                    passwordPolicy: { ...settings.passwordPolicy, requireNumbers: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Require numbers (0-9)
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.passwordPolicy.requireSpecialChars}
                  onChange={(e) => updateSettings({
                    passwordPolicy: { ...settings.passwordPolicy, requireSpecialChars: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Require special characters (!@#$%^&*)
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.passwordPolicy.requireChangeOnFirstLogin}
                  onChange={(e) => updateSettings({
                    passwordPolicy: { ...settings.passwordPolicy, requireChangeOnFirstLogin: e.target.checked }
                  })}
                  disabled={!isAdmin}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Require password change on first login
                </span>
              </label>
            </div>
          </div>
        )}

        {!isAdmin && (
          <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <div className="flex items-center">
              <Lock className="h-5 w-5 text-gray-400 mr-3" />
              <p className="text-sm text-gray-600">
                Only administrators can modify organization security settings.
              </p>
            </div>
          </div>
        )}
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