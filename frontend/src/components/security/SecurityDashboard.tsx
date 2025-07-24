import React, { useState, useEffect } from 'react';
import { Shield, AlertCircle, CheckCircle, Lock, Globe, Monitor, Smartphone, Clock, TrendingUp } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { API_ENDPOINTS } from '../../config/api.config';

interface SecurityEvent {
  id: string;
  type: 'login' | 'logout' | 'failed_login' | 'password_change' | 'permission_change' | 'data_export' | 'data_deletion';
  timestamp: string;
  userAgent: string;
  ipAddress: string;
  location?: string;
  deviceType: 'desktop' | 'mobile' | 'tablet';
  success: boolean;
  details?: string;
}

interface SecurityMetrics {
  totalLogins: number;
  failedAttempts: number;
  uniqueDevices: number;
  activeSession: number;
  securityScore: number;
  lastPasswordChange: string;
  twoFactorEnabled: boolean;
}

export const SecurityDashboard: React.FC = () => {
  const { user, organization } = useAuth();
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [metrics, setMetrics] = useState<SecurityMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeFilter, setTimeFilter] = useState<'24h' | '7d' | '30d' | '90d'>('7d');

  useEffect(() => {
    fetchSecurityData();
  }, [timeFilter]);

  const fetchSecurityData = async () => {
    try {
      const [eventsResponse, metricsResponse] = await Promise.all([
        api.get(`${API_ENDPOINTS.security.events}?timeframe=${timeFilter}`),
        api.get(API_ENDPOINTS.security.metrics)
      ]);

      if (eventsResponse.data) {
        setEvents(eventsResponse.data.events || []);
      }
      if (metricsResponse.data) {
        setMetrics(metricsResponse.data);
      }
    } catch (error) {
      console.error('Failed to fetch security data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getEventIcon = (type: SecurityEvent['type']) => {
    switch (type) {
      case 'login':
      case 'logout':
        return <Monitor className="h-4 w-4" />;
      case 'failed_login':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'password_change':
        return <Lock className="h-4 w-4 text-blue-500" />;
      case 'permission_change':
        return <Shield className="h-4 w-4 text-purple-500" />;
      case 'data_export':
      case 'data_deletion':
        return <Globe className="h-4 w-4 text-orange-500" />;
      default:
        return <Shield className="h-4 w-4" />;
    }
  };

  const getEventColor = (type: SecurityEvent['type'], success: boolean) => {
    if (!success) return 'bg-red-50 border-red-200';
    
    switch (type) {
      case 'login':
      case 'logout':
        return 'bg-green-50 border-green-200';
      case 'password_change':
        return 'bg-blue-50 border-blue-200';
      case 'permission_change':
        return 'bg-purple-50 border-purple-200';
      case 'data_export':
      case 'data_deletion':
        return 'bg-orange-50 border-orange-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getSecurityScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
      case 'mobile':
        return <Smartphone className="h-4 w-4" />;
      case 'tablet':
        return <Monitor className="h-4 w-4" />;
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-32 bg-gray-200 rounded-lg mb-6"></div>
        <div className="space-y-4">
          <div className="h-20 bg-gray-200 rounded-lg"></div>
          <div className="h-20 bg-gray-200 rounded-lg"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Security Overview */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
            <Shield className="h-6 w-6 mr-2 text-blue-600" />
            Security Overview
          </h2>
          <div className="flex items-center space-x-2">
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
        </div>

        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Security Score</span>
                <TrendingUp className={`h-4 w-4 ${getSecurityScoreColor(metrics.securityScore)}`} />
              </div>
              <div className={`text-3xl font-bold ${getSecurityScoreColor(metrics.securityScore)}`}>
                {metrics.securityScore}%
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {metrics.securityScore >= 80 ? 'Excellent' : metrics.securityScore >= 60 ? 'Good' : 'Needs Improvement'}
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Two-Factor Auth</span>
                {metrics.twoFactorEnabled ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-yellow-500" />
                )}
              </div>
              <div className="text-lg font-semibold text-gray-900">
                {metrics.twoFactorEnabled ? 'Enabled' : 'Disabled'}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {metrics.twoFactorEnabled ? 'Account secured' : 'Enable for better security'}
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Failed Logins</span>
                <AlertCircle className={`h-4 w-4 ${metrics.failedAttempts > 0 ? 'text-red-500' : 'text-gray-400'}`} />
              </div>
              <div className="text-3xl font-bold text-gray-900">{metrics.failedAttempts}</div>
              <p className="text-xs text-gray-500 mt-1">In the last {timeFilter}</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Active Devices</span>
                <Monitor className="h-4 w-4 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-gray-900">{metrics.uniqueDevices}</div>
              <p className="text-xs text-gray-500 mt-1">Unique devices</p>
            </div>
          </div>
        )}
      </div>

      {/* Recent Security Events */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Security Events</h3>
        
        <div className="space-y-3">
          {events.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No security events in the selected timeframe</p>
          ) : (
            events.map((event) => (
              <div
                key={event.id}
                className={`flex items-center justify-between p-4 rounded-lg border ${getEventColor(event.type, event.success)}`}
              >
                <div className="flex items-center space-x-3">
                  {getEventIcon(event.type)}
                  <div>
                    <p className="font-medium text-gray-900">
                      {event.type.replace(/_/g, ' ').charAt(0).toUpperCase() + event.type.replace(/_/g, ' ').slice(1)}
                    </p>
                    <p className="text-sm text-gray-600">
                      {event.ipAddress} • {event.location || 'Unknown location'}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    {getDeviceIcon(event.deviceType)}
                    <span className="hidden sm:inline">{event.deviceType}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3" />
                    <span>{new Date(event.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {events.length > 0 && (
          <div className="mt-4 flex justify-center">
            <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
              View All Security Events →
            </button>
          </div>
        )}
      </div>

      {/* Security Recommendations */}
      {metrics && !metrics.twoFactorEnabled && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div className="ml-3">
              <h4 className="font-medium text-yellow-900">Security Recommendation</h4>
              <p className="text-sm text-yellow-700 mt-1">
                Enable two-factor authentication to significantly improve your account security.
              </p>
              <button className="mt-2 text-sm font-medium text-yellow-900 hover:text-yellow-800">
                Enable 2FA →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};