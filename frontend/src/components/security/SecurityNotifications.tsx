import React, { useState, useEffect } from 'react';
import { Bell, Shield, AlertCircle, CheckCircle, Info, X, Mail, Smartphone, Monitor, Globe } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { API_ENDPOINTS, buildUrl } from '../../config/api.config';

interface SecurityAlert {
  id: string;
  type: 'login_new_device' | 'login_new_location' | 'password_change' | 'permission_change' | 'suspicious_activity' | 'data_export' | 'failed_login_attempts';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
  actionRequired: boolean;
  metadata?: {
    device?: string;
    location?: string;
    ipAddress?: string;
    attemptCount?: number;
  };
}

interface NotificationPreferences {
  email: {
    enabled: boolean;
    newDeviceLogin: boolean;
    newLocationLogin: boolean;
    passwordChanges: boolean;
    suspiciousActivity: boolean;
    dataExports: boolean;
    weeklyDigest: boolean;
  };
  inApp: {
    enabled: boolean;
    newDeviceLogin: boolean;
    newLocationLogin: boolean;
    passwordChanges: boolean;
    suspiciousActivity: boolean;
    dataExports: boolean;
  };
  sms: {
    enabled: boolean;
    criticalOnly: boolean;
    phoneNumber?: string;
  };
}

export const SecurityNotifications: React.FC = () => {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'alerts' | 'preferences'>('alerts');
  const [filterSeverity, setFilterSeverity] = useState<'all' | 'info' | 'warning' | 'critical'>('all');
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [alertsResponse, prefsResponse] = await Promise.all([
        api.get(API_ENDPOINTS.security.alerts),
        api.get(API_ENDPOINTS.security.notificationPreferences)
      ]);

      if (alertsResponse.data) {
        setAlerts(alertsResponse.data.alerts || []);
      }
      if (prefsResponse.data) {
        setPreferences(prefsResponse.data);
      }
    } catch (error) {
      console.error('Failed to fetch security data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const markAsRead = async (alertId: string) => {
    try {
      await api.patch(`${API_ENDPOINTS.security.alerts}/${alertId}/read`);
      setAlerts(alerts.map(alert => 
        alert.id === alertId ? { ...alert, read: true } : alert
      ));
    } catch (error) {
      console.error('Failed to mark alert as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.patch(`${API_ENDPOINTS.security.alerts}/read-all`);
      setAlerts(alerts.map(alert => ({ ...alert, read: true })));
    } catch (error) {
      console.error('Failed to mark all alerts as read:', error);
    }
  };

  const updatePreferences = async (updates: Partial<NotificationPreferences>) => {
    if (!preferences) return;

    try {
      const response = await api.patch(API_ENDPOINTS.security.notificationPreferences, updates);
      if (response.data) {
        setPreferences({ ...preferences, ...updates });
      }
    } catch (error) {
      console.error('Failed to update preferences:', error);
    }
  };

  const getAlertIcon = (type: SecurityAlert['type']) => {
    switch (type) {
      case 'login_new_device':
        return <Monitor className="h-5 w-5" />;
      case 'login_new_location':
        return <Globe className="h-5 w-5" />;
      case 'password_change':
      case 'permission_change':
        return <Shield className="h-5 w-5" />;
      case 'suspicious_activity':
      case 'failed_login_attempts':
        return <AlertCircle className="h-5 w-5" />;
      case 'data_export':
        return <Info className="h-5 w-5" />;
      default:
        return <Bell className="h-5 w-5" />;
    }
  };

  const getSeverityColor = (severity: SecurityAlert['severity']) => {
    switch (severity) {
      case 'info':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'warning':
        return 'bg-yellow-50 text-yellow-700 border-yellow-200';
      case 'critical':
        return 'bg-red-50 text-red-700 border-red-200';
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filterSeverity !== 'all' && alert.severity !== filterSeverity) return false;
    if (showUnreadOnly && alert.read) return false;
    return true;
  });

  const unreadCount = alerts.filter(a => !a.read).length;

  if (isLoading) {
    return <div className="animate-pulse h-96 bg-gray-200 rounded-lg"></div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
            <Bell className="h-6 w-6 mr-2 text-blue-600" />
            Security Notifications
            {unreadCount > 0 && (
              <span className="ml-2 px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                {unreadCount}
              </span>
            )}
          </h2>
        </div>

        {/* Tab Navigation */}
        <div className="mt-4 flex space-x-4 border-b border-gray-200">
          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'alerts'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Security Alerts
          </button>
          <button
            onClick={() => setActiveTab('preferences')}
            className={`pb-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'preferences'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Notification Preferences
          </button>
        </div>
      </div>

      <div className="p-6">
        {activeTab === 'alerts' && (
          <div>
            {/* Filters */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-4">
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value as any)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Severities</option>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="critical">Critical</option>
                </select>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={showUnreadOnly}
                    onChange={(e) => setShowUnreadOnly(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">Unread only</span>
                </label>
              </div>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Mark all as read
                </button>
              )}
            </div>

            {/* Alert List */}
            <div className="space-y-3">
              {filteredAlerts.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No security alerts</p>
              ) : (
                filteredAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-lg border ${getSeverityColor(alert.severity)} ${
                      !alert.read ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        {getAlertIcon(alert.type)}
                        <div className="flex-1">
                          <h3 className="font-medium">{alert.title}</h3>
                          <p className="text-sm mt-1">{alert.description}</p>
                          
                          {alert.metadata && (
                            <div className="mt-2 text-xs space-y-1">
                              {alert.metadata.device && (
                                <p>Device: {alert.metadata.device}</p>
                              )}
                              {alert.metadata.location && (
                                <p>Location: {alert.metadata.location}</p>
                              )}
                              {alert.metadata.ipAddress && (
                                <p>IP Address: {alert.metadata.ipAddress}</p>
                              )}
                              {alert.metadata.attemptCount && (
                                <p>Attempts: {alert.metadata.attemptCount}</p>
                              )}
                            </div>
                          )}
                          
                          <p className="text-xs mt-2">
                            {new Date(alert.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {alert.actionRequired && (
                          <span className="px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded">
                            Action Required
                          </span>
                        )}
                        {!alert.read && (
                          <button
                            onClick={() => markAsRead(alert.id)}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'preferences' && preferences && (
          <div className="space-y-6">
            {/* Email Notifications */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <Mail className="h-5 w-5 mr-2" />
                Email Notifications
              </h3>
              
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={preferences.email.enabled}
                    onChange={(e) => updatePreferences({
                      email: { ...preferences.email, enabled: e.target.checked }
                    })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Enable email notifications
                  </span>
                </label>

                {preferences.email.enabled && (
                  <div className="ml-6 space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.email.newDeviceLogin}
                        onChange={(e) => updatePreferences({
                          email: { ...preferences.email, newDeviceLogin: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">New device login</span>
                    </label>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.email.newLocationLogin}
                        onChange={(e) => updatePreferences({
                          email: { ...preferences.email, newLocationLogin: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">New location login</span>
                    </label>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.email.passwordChanges}
                        onChange={(e) => updatePreferences({
                          email: { ...preferences.email, passwordChanges: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">Password changes</span>
                    </label>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.email.suspiciousActivity}
                        onChange={(e) => updatePreferences({
                          email: { ...preferences.email, suspiciousActivity: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">Suspicious activity</span>
                    </label>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.email.dataExports}
                        onChange={(e) => updatePreferences({
                          email: { ...preferences.email, dataExports: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">Data exports</span>
                    </label>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.email.weeklyDigest}
                        onChange={(e) => updatePreferences({
                          email: { ...preferences.email, weeklyDigest: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">Weekly security digest</span>
                    </label>
                  </div>
                )}
              </div>
            </div>

            {/* In-App Notifications */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <Bell className="h-5 w-5 mr-2" />
                In-App Notifications
              </h3>
              
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={preferences.inApp.enabled}
                    onChange={(e) => updatePreferences({
                      inApp: { ...preferences.inApp, enabled: e.target.checked }
                    })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Enable in-app notifications
                  </span>
                </label>

                {preferences.inApp.enabled && (
                  <p className="ml-6 text-sm text-gray-600">
                    You'll receive notifications for all security events while using the application.
                  </p>
                )}
              </div>
            </div>

            {/* SMS Notifications */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <Smartphone className="h-5 w-5 mr-2" />
                SMS Notifications
              </h3>
              
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={preferences.sms.enabled}
                    onChange={(e) => updatePreferences({
                      sms: { ...preferences.sms, enabled: e.target.checked }
                    })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Enable SMS notifications
                  </span>
                </label>

                {preferences.sms.enabled && (
                  <div className="ml-6 space-y-3">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferences.sms.criticalOnly}
                        onChange={(e) => updatePreferences({
                          sms: { ...preferences.sms, criticalOnly: e.target.checked }
                        })}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">
                        Critical alerts only
                      </span>
                    </label>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Phone Number
                      </label>
                      <input
                        type="tel"
                        value={preferences.sms.phoneNumber || ''}
                        onChange={(e) => updatePreferences({
                          sms: { ...preferences.sms, phoneNumber: e.target.value }
                        })}
                        placeholder="[PHONE-NUMBER]"
                        className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div className="ml-3">
                    <h4 className="font-medium text-blue-900">Critical Security Alerts</h4>
                    <p className="text-sm text-blue-700 mt-1">
                      Critical security alerts will always be sent to your registered email address, 
                      regardless of your notification preferences, to ensure account security.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};