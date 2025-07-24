import React, { useState, useEffect } from 'react';
import { Shield, Download, Search, Calendar, User, Activity, Settings, CheckCircle } from 'lucide-react';

interface AuditLogEntry {
  id: string;
  timestamp: string;
  userId: string;
  action: 'prompt_submitted' | 'prompt_approved' | 'prompt_rejected' | 'data_exported' | 'settings_changed';
  details: {
    promptId?: string;
    model?: string;
    sensitiveDataCount?: number;
    changes?: Record<string, any>;
  };
  ipAddress: string;
  userAgent: string;
}

interface SecurityAuditLogProps {
  organizationId: string;
  userId?: string;
  limit?: number;
}

export const SecurityAuditLog: React.FC<SecurityAuditLogProps> = ({
  organizationId,
  userId,
  limit = 100
}) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    action: 'all',
    searchQuery: ''
  });

  useEffect(() => {
    fetchAuditLogs();
  }, [organizationId, userId, filters]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        organizationId,
        ...(userId && { userId }),
        limit: limit.toString(),
        ...filters
      });
      const response = await fetch(`/api/audit-logs?${params}`);
      const data = await response.json();
      setLogs(data);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportLogs = () => {
    const csv = [
      ['Timestamp', 'User', 'Action', 'Details', 'IP Address'].join(','),
      ...logs.map(log => [
        log.timestamp,
        log.userId,
        log.action,
        JSON.stringify(log.details),
        log.ipAddress
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${new Date().toISOString()}.csv`;
    a.click();
  };

  const getActionIcon = (action: AuditLogEntry['action']) => {
    switch (action) {
      case 'prompt_submitted':
        return <Activity className="w-4 h-4 text-blue-600" />;
      case 'prompt_approved':
        return <Shield className="w-4 h-4 text-green-600" />;
      case 'prompt_rejected':
        return <Shield className="w-4 h-4 text-red-600" />;
      case 'data_exported':
        return <Download className="w-4 h-4 text-purple-600" />;
      case 'settings_changed':
        return <Settings className="w-4 h-4 text-gray-600" />;
    }
  };

  const getActionLabel = (action: AuditLogEntry['action']) => {
    const labels = {
      prompt_submitted: 'Prompt Submitted',
      prompt_approved: 'Prompt Approved',
      prompt_rejected: 'Prompt Rejected',
      data_exported: 'Data Exported',
      settings_changed: 'Settings Changed'
    };
    return labels[action];
  };

  const filteredLogs = logs.filter(log => {
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      return (
        log.userId.toLowerCase().includes(query) ||
        log.action.toLowerCase().includes(query) ||
        JSON.stringify(log.details).toLowerCase().includes(query)
      );
    }
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Security Audit Log</h3>
        </div>
        <button
          onClick={exportLogs}
          className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={filters.searchQuery}
              onChange={(e) => setFilters({ ...filters, searchQuery: e.target.value })}
              placeholder="Search logs..."
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          <select
            value={filters.action}
            onChange={(e) => setFilters({ ...filters, action: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          >
            <option value="all">All Actions</option>
            <option value="prompt_submitted">Prompts Submitted</option>
            <option value="prompt_approved">Prompts Approved</option>
            <option value="prompt_rejected">Prompts Rejected</option>
            <option value="data_exported">Data Exported</option>
            <option value="settings_changed">Settings Changed</option>
          </select>

          <input
            type="date"
            value={filters.startDate}
            onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          />

          <input
            type="date"
            value={filters.endDate}
            onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          />
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No audit log entries found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Timestamp</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">User</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Action</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Details</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">IP Address</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map(log => (
                  <tr key={log.id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-900">{log.userId}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getActionIcon(log.action)}
                        <span className="font-medium">{getActionLabel(log.action)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {log.details.model && (
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded mr-2">
                          {log.details.model}
                        </span>
                      )}
                      {log.details.sensitiveDataCount !== undefined && (
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                          {log.details.sensitiveDataCount} sensitive items
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {log.ipAddress}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-700">
          <strong>Data Retention:</strong> Audit logs are retained for 90 days in accordance with our data retention policy. 
          Logs older than 90 days are automatically archived.
        </p>
      </div>
    </div>
  );
};