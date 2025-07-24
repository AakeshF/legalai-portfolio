// API Configuration
export const API_CONFIG = {
  // Base URL for the backend API
  // In production, this should be set via environment variable
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  
  // API version
  version: 'v1',
  
  // Request timeout in milliseconds
  timeout: 30000,
  
  // Retry configuration
  retry: {
    maxAttempts: 3,
    delay: 1000,
    backoffMultiplier: 2
  }
};

// Helper to construct full API URLs
export const getApiUrl = (endpoint: string): string => {
  // Remove leading slash if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  
  // Ensure baseURL doesn't end with slash
  const cleanBaseURL = API_CONFIG.baseURL.endsWith('/') 
    ? API_CONFIG.baseURL.slice(0, -1) 
    : API_CONFIG.baseURL;
  
  return `${cleanBaseURL}/${cleanEndpoint}`;
};

// API Endpoints
export const API_ENDPOINTS = {
  // Authentication
  auth: {
    login: '/auth/login',
    register: '/auth/register',
    logout: '/auth/logout',
    refresh: '/auth/refresh',
    me: '/auth/me',
    updateProfile: '/auth/profile',
    changePassword: '/auth/password'
  },
  
  // Security
  security: {
    events: '/security/events',
    metrics: '/security/metrics',
    status: '/security/status',
    alerts: '/security/alerts',
    notificationPreferences: '/security/notification-preferences',
    twoFactor: {
      status: '/security/2fa/status',
      setup: '/security/2fa/setup',
      verify: '/security/2fa/verify',
      disable: '/security/2fa/disable',
      backupCodes: '/security/2fa/backup-codes',
      regenerateBackupCodes: '/security/2fa/backup-codes/regenerate'
    }
  },
  
  // Privacy & Data Management
  privacy: {
    settings: '/privacy/settings',
    compliance: '/privacy/compliance',
    dataExport: '/privacy/data/export',
    dataExportHistory: '/privacy/data/exports',
    dataExportDownload: '/privacy/data/export/download',
    deletion: {
      initiate: '/privacy/data/deletion/initiate',
      confirm: '/privacy/data/deletion/confirm'
    }
  },
  
  // Organization Management
  organization: {
    info: '/organization',
    users: '/organization/users',
    invite: '/organization/users/invite',
    updateUserRole: '/organization/users/:userId/role',
    removeUser: '/organization/users/:userId',
    settings: '/organization/settings',
    security: {
      settings: '/organization/security/settings',
      ipRestrictions: '/organization/security/ip-restrictions',
      removeIpRestriction: '/organization/security/ip-restrictions/:id'
    }
  },
  
  // Audit Logs
  audit: {
    logs: '/audit/logs',
    export: '/audit/export',
    details: '/audit/logs/:id'
  },
  
  // Documents (existing endpoints)
  documents: {
    list: '/documents',
    upload: '/documents/upload',
    get: '/documents/:id',
    delete: '/documents/:id',
    status: '/documents/:id/status'
  },
  
  // Chat (existing endpoints)
  chat: {
    send: '/chat',
    history: '/chat/history',
    session: '/chat/session/:sessionId',
    create: {
      demo: '/chat',
      prod: '/chat'
    }
  }
};

// Helper to replace path parameters
export const buildUrl = (endpoint: string, params?: Record<string, string>): string => {
  let url = endpoint;
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url = url.replace(`:${key}`, value);
    });
  }
  
  return url;
};