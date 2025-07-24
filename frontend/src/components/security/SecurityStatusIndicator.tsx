import React, { useState, useEffect } from 'react';
import { Shield, Lock, AlertTriangle, CheckCircle, Info, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { API_ENDPOINTS } from '../../config/api.config';

interface SecurityStatus {
  overallScore: number;
  twoFactorEnabled: boolean;
  lastPasswordChange: string;
  activeThreats: number;
  encryptionEnabled: boolean;
  ipRestricted: boolean;
  sessionSecure: boolean;
}

interface SecurityStatusIndicatorProps {
  variant?: 'full' | 'compact' | 'mini';
  showDetails?: boolean;
}

export const SecurityStatusIndicator: React.FC<SecurityStatusIndicatorProps> = ({ 
  variant = 'compact',
  showDetails = true 
}) => {
  const { user } = useAuth();
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    fetchSecurityStatus();
    
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // Refresh status every 5 minutes
    const interval = setInterval(fetchSecurityStatus, 5 * 60 * 1000);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, []);

  const fetchSecurityStatus = async () => {
    try {
      const response = await api.get(API_ENDPOINTS.security.status);
      if (response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch security status:', error);
    }
  };

  const getSecurityLevel = () => {
    if (!status) return 'unknown';
    if (status.activeThreats > 0) return 'critical';
    if (status.overallScore >= 80) return 'excellent';
    if (status.overallScore >= 60) return 'good';
    return 'poor';
  };

  const getSecurityColor = () => {
    const level = getSecurityLevel();
    switch (level) {
      case 'excellent':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'good':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'poor':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getSecurityIcon = () => {
    const level = getSecurityLevel();
    switch (level) {
      case 'excellent':
        return <CheckCircle className="h-5 w-5" />;
      case 'critical':
        return <AlertTriangle className="h-5 w-5" />;
      default:
        return <Shield className="h-5 w-5" />;
    }
  };

  if (variant === 'mini') {
    return (
      <div className="relative">
        <button
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          className={`p-2 rounded-lg border ${getSecurityColor()}`}
        >
          {getSecurityIcon()}
        </button>
        
        {showTooltip && status && (
          <div className="absolute bottom-full right-0 mb-2 w-64 p-3 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
            <div className="text-sm">
              <div className="font-medium text-gray-900 mb-2">Security Status</div>
              <div className="space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Overall Score</span>
                  <span className="font-medium">{status.overallScore}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">2FA</span>
                  <span className={status.twoFactorEnabled ? 'text-green-600' : 'text-red-600'}>
                    {status.twoFactorEnabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                {status.activeThreats > 0 && (
                  <div className="flex items-center justify-between text-red-600">
                    <span>Active Threats</span>
                    <span className="font-medium">{status.activeThreats}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg border ${getSecurityColor()}`}>
        {getSecurityIcon()}
        <span className="text-sm font-medium">
          {getSecurityLevel() === 'excellent' ? 'Secure' :
           getSecurityLevel() === 'good' ? 'Good' :
           getSecurityLevel() === 'critical' ? 'At Risk' : 'Poor'}
        </span>
        {!isOnline && (
          <WifiOff className="h-4 w-4" />
        )}
      </div>
    );
  }

  // Full variant
  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 flex items-center">
          <Shield className="h-5 w-5 mr-2 text-blue-600" />
          Security Status
        </h3>
        {!isOnline && (
          <div className="flex items-center text-orange-600">
            <WifiOff className="h-4 w-4 mr-1" />
            <span className="text-sm">Offline</span>
          </div>
        )}
      </div>

      {status ? (
        <div className="space-y-3">
          <div className={`p-3 rounded-lg border ${getSecurityColor()}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {getSecurityIcon()}
                <span className="font-medium">
                  Security Level: {getSecurityLevel().charAt(0).toUpperCase() + getSecurityLevel().slice(1)}
                </span>
              </div>
              <span className="text-2xl font-bold">{status.overallScore}%</span>
            </div>
          </div>

          {showDetails && (
            <div className="space-y-2">
              <SecurityDetail
                label="Two-Factor Authentication"
                value={status.twoFactorEnabled ? 'Enabled' : 'Disabled'}
                status={status.twoFactorEnabled ? 'good' : 'warning'}
                icon={<Lock className="h-4 w-4" />}
              />
              
              <SecurityDetail
                label="Password Security"
                value={`Changed ${getDaysSince(status.lastPasswordChange)} days ago`}
                status={getDaysSince(status.lastPasswordChange) < 90 ? 'good' : 'warning'}
                icon={<Shield className="h-4 w-4" />}
              />
              
              <SecurityDetail
                label="Connection"
                value={status.encryptionEnabled ? 'Encrypted' : 'Not Encrypted'}
                status={status.encryptionEnabled ? 'good' : 'critical'}
                icon={<Lock className="h-4 w-4" />}
              />
              
              {status.activeThreats > 0 && (
                <SecurityDetail
                  label="Active Threats"
                  value={`${status.activeThreats} detected`}
                  status="critical"
                  icon={<AlertTriangle className="h-4 w-4" />}
                />
              )}
            </div>
          )}

          <button className="w-full text-sm text-blue-600 hover:text-blue-700 font-medium">
            View Security Dashboard →
          </button>
        </div>
      ) : (
        <div className="animate-pulse space-y-3">
          <div className="h-12 bg-gray-200 rounded"></div>
          <div className="h-8 bg-gray-200 rounded"></div>
          <div className="h-8 bg-gray-200 rounded"></div>
        </div>
      )}
    </div>
  );
};

interface SecurityDetailProps {
  label: string;
  value: string;
  status: 'good' | 'warning' | 'critical';
  icon: React.ReactNode;
}

const SecurityDetail: React.FC<SecurityDetailProps> = ({ label, value, status, icon }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'good':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'critical':
        return 'text-red-600';
    }
  };

  return (
    <div className="flex items-center justify-between p-2 rounded-md bg-gray-50">
      <div className="flex items-center space-x-2 text-sm text-gray-700">
        <span className={getStatusColor()}>{icon}</span>
        <span>{label}</span>
      </div>
      <span className={`text-sm font-medium ${getStatusColor()}`}>{value}</span>
    </div>
  );
};

const getDaysSince = (dateString: string): number => {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

// Export a hook for programmatic access to security status
export const useSecurityStatus = () => {
  const [status, setStatus] = useState<SecurityStatus | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await api.get(API_ENDPOINTS.security.status);
        if (response.data) {
          setStatus(response.data);
        }
      } catch (error) {
        console.error('Failed to fetch security status:', error);
      }
    };

    fetchStatus();
  }, []);

  return status;
};