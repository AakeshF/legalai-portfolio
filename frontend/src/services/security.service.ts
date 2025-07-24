import { apiClient } from './api/client';

export interface TwoFactorStatus {
  enabled: boolean;
  method: 'app' | 'sms' | null;
  phoneNumber?: string;
  backupCodesRemaining?: number;
  lastEnabled?: string;
  lastUsed?: string;
}

export interface SecurityEvent {
  id: string;
  timestamp: string;
  eventType: string;
  severity: string;
  message: string;
  userId?: string;
  ipAddress?: string;
  userAgent?: string;
  metadata?: Record<string, any>;
}

export interface SecurityMetrics {
  failedLoginAttempts: number;
  suspiciousActivities: number;
  dataExports: number;
  apiKeyRotations: number;
  periodStart: string;
  periodEnd: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userEmail: string;
  action: string;
  resourceType: string;
  resourceId?: string;
  ipAddress: string;
  userAgent: string;
  details?: Record<string, any>;
  status: 'success' | 'failure';
}

export const securityService = {
  // Two-Factor Authentication
  async get2FAStatus(): Promise<TwoFactorStatus> {
    return apiClient.get('/api/security/2fa/status');
  },

  async setup2FA(method: 'app' | 'sms', phoneNumber?: string): Promise<{
    qrCode?: string;
    secret?: string;
    phoneNumber?: string;
  }> {
    return apiClient.post('/api/security/2fa/setup', { method, phoneNumber });
  },

  async verify2FA(code: string): Promise<{ backupCodes: string[] }> {
    return apiClient.post('/api/security/2fa/verify', { code });
  },

  async disable2FA(code: string): Promise<void> {
    return apiClient.post('/api/security/2fa/disable', { code });
  },

  async getBackupCodes(): Promise<{ codes: string[]; remaining: number }> {
    return apiClient.get('/api/security/2fa/backup-codes');
  },

  async regenerateBackupCodes(): Promise<{ codes: string[] }> {
    return apiClient.post('/api/security/2fa/backup-codes/regenerate');
  },

  // Security Events
  async getSecurityEvents(params?: {
    limit?: number;
    offset?: number;
    severity?: string;
    eventType?: string;
  }): Promise<{ events: SecurityEvent[]; total: number }> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.severity) queryParams.append('severity', params.severity);
    if (params?.eventType) queryParams.append('event_type', params.eventType);
    
    return apiClient.get(`/api/security/events?${queryParams}`);
  },

  async getSecurityMetrics(): Promise<SecurityMetrics> {
    return apiClient.get('/api/security/metrics');
  },

  async getSecurityStatus(): Promise<{
    overallStatus: 'secure' | 'warning' | 'critical';
    checks: Array<{
      name: string;
      status: 'pass' | 'fail' | 'warning';
      message: string;
    }>;
  }> {
    return apiClient.get('/api/security/status');
  },

  // Audit Logs
  async getAuditLogs(params?: {
    limit?: number;
    offset?: number;
    startDate?: string;
    endDate?: string;
    userId?: string;
    action?: string;
  }): Promise<{ logs: AuditLog[]; total: number }> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.startDate) queryParams.append('start_date', params.startDate);
    if (params?.endDate) queryParams.append('end_date', params.endDate);
    if (params?.userId) queryParams.append('user_id', params.userId);
    if (params?.action) queryParams.append('action', params.action);
    
    return apiClient.get(`/api/audit/logs?${queryParams}`);
  },

  async exportAuditLogs(format: 'csv' | 'json', filters?: any): Promise<Blob> {
    const response = await apiClient.post('/api/audit/export', {
      format,
      filters
    });
    return response as unknown as Blob;
  },
};