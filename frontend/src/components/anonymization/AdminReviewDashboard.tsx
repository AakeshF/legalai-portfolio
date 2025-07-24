import React, { useState, useEffect } from 'react';
import { 
  Shield, Search, Filter, CheckCircle, XCircle, Edit3, 
  AlertTriangle, Clock, Users, Activity, TrendingUp,
  Calendar, RefreshCw, ChevronDown
} from 'lucide-react';
import { PromptSubmission } from '../../types/anonymization';
import { SensitiveDataDetector } from './SensitiveDataDetector';

interface AdminReviewDashboardProps {
  organizationId: string;
}

interface FilterOptions {
  status: 'all' | 'pending_review' | 'approved' | 'rejected';
  user: string;
  dateRange: 'today' | 'week' | 'month' | 'all';
  model: string;
  sortBy: 'newest' | 'oldest' | 'user' | 'model';
}

interface DashboardStats {
  totalSubmissions: number;
  pendingReviews: number;
  approvalRate: number;
  avgReviewTime: number;
  activeUsers: number;
  submissionsToday: number;
}

export const AdminReviewDashboard: React.FC<AdminReviewDashboardProps> = ({
  organizationId
}) => {
  const [submissions, setSubmissions] = useState<PromptSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSubmission, setSelectedSubmission] = useState<PromptSubmission | null>(null);
  const [filters, setFilters] = useState<FilterOptions>({
    status: 'all',
    user: '',
    dateRange: 'week',
    model: '',
    sortBy: 'newest'
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showBatchActions, setShowBatchActions] = useState(false);
  const [editingContent, setEditingContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    fetchSubmissions();
    fetchStats();
    const interval = setInterval(() => {
      fetchSubmissions();
      fetchStats();
    }, 30000);
    return () => clearInterval(interval);
  }, [organizationId, filters]);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        organizationId,
        ...filters
      });
      const response = await fetch(`/api/admin/submissions?${params}`);
      const data = await response.json();
      setSubmissions(data);
    } catch (error) {
      console.error('Failed to fetch submissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`/api/admin/stats?organizationId=${organizationId}`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleApprove = async (submissionId: string, editedContent?: string) => {
    try {
      await fetch(`/api/admin/submissions/${submissionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ editedContent })
      });
      fetchSubmissions();
      setSelectedSubmission(null);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to approve submission:', error);
    }
  };

  const handleReject = async (submissionId: string, reason: string) => {
    try {
      await fetch(`/api/admin/submissions/${submissionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });
      fetchSubmissions();
      setSelectedSubmission(null);
    } catch (error) {
      console.error('Failed to reject submission:', error);
    }
  };

  const handleBatchAction = async (action: 'approve' | 'reject') => {
    const ids = Array.from(selectedIds);
    try {
      await fetch('/api/admin/submissions/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, action })
      });
      fetchSubmissions();
      setSelectedIds(new Set());
      setShowBatchActions(false);
    } catch (error) {
      console.error('Failed to perform batch action:', error);
    }
  };

  const filteredSubmissions = submissions.filter(submission => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        submission.originalContent.toLowerCase().includes(query) ||
        submission.redactedContent.toLowerCase().includes(query) ||
        submission.userId.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const StatCard: React.FC<{ title: string; value: string | number; icon: React.ReactNode; trend?: number }> = ({
    title, value, icon, trend
  }) => (
    <div className="bg-white p-4 rounded-lg border border-gray-200">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-semibold mt-1">{value}</p>
          {trend !== undefined && (
            <p className={`text-xs mt-1 ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend >= 0 ? '+' : ''}{trend}% from last period
            </p>
          )}
        </div>
        <div className="p-2 bg-blue-50 rounded-lg">{icon}</div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-bold">Admin Review Dashboard</h1>
        </div>
        <button
          onClick={fetchSubmissions}
          className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Pending Reviews"
            value={stats.pendingReviews}
            icon={<Clock className="w-5 h-5 text-blue-600" />}
          />
          <StatCard
            title="Approval Rate"
            value={`${stats.approvalRate}%`}
            icon={<CheckCircle className="w-5 h-5 text-green-600" />}
            trend={5}
          />
          <StatCard
            title="Avg Review Time"
            value={`${stats.avgReviewTime}m`}
            icon={<Activity className="w-5 h-5 text-purple-600" />}
            trend={-12}
          />
          <StatCard
            title="Active Users"
            value={stats.activeUsers}
            icon={<Users className="w-5 h-5 text-orange-600" />}
            trend={8}
          />
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search prompts..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value as any })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="pending_review">Pending Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>

              <select
                value={filters.dateRange}
                onChange={(e) => setFilters({ ...filters, dateRange: e.target.value as any })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
                <option value="all">All Time</option>
              </select>

              <select
                value={filters.sortBy}
                onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as any })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="user">By User</option>
                <option value="model">By Model</option>
              </select>
            </div>
          </div>

          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3 mt-4 p-3 bg-blue-50 rounded-lg">
              <span className="text-sm font-medium text-blue-900">
                {selectedIds.size} items selected
              </span>
              <button
                onClick={() => handleBatchAction('approve')}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700"
              >
                Approve All
              </button>
              <button
                onClick={() => handleBatchAction('reject')}
                className="px-3 py-1 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700"
              >
                Reject All
              </button>
              <button
                onClick={() => setSelectedIds(new Set())}
                className="px-3 py-1 text-gray-600 text-sm hover:text-gray-700"
              >
                Clear Selection
              </button>
            </div>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedIds(new Set(filteredSubmissions.map(s => s.id)));
                      } else {
                        setSelectedIds(new Set());
                      }
                    }}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">User</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Content</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Model</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Sensitive Data</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    Loading submissions...
                  </td>
                </tr>
              ) : filteredSubmissions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    No submissions found
                  </td>
                </tr>
              ) : (
                filteredSubmissions.map(submission => (
                  <tr key={submission.id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(submission.id)}
                        onChange={(e) => {
                          const newIds = new Set(selectedIds);
                          if (e.target.checked) {
                            newIds.add(submission.id);
                          } else {
                            newIds.delete(submission.id);
                          }
                          setSelectedIds(newIds);
                        }}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm">{submission.userId}</td>
                    <td className="px-4 py-3 text-sm max-w-xs truncate">
                      {submission.redactedContent}
                    </td>
                    <td className="px-4 py-3 text-sm">{submission.model}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">
                        {submission.segments.length} items
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {submission.status === 'pending_review' && (
                        <span className="px-2 py-1 text-xs bg-amber-100 text-amber-700 rounded">
                          Pending
                        </span>
                      )}
                      {submission.status === 'approved' && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                          Approved
                        </span>
                      )}
                      {submission.status === 'rejected' && (
                        <span className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">
                          Rejected
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => {
                          setSelectedSubmission(submission);
                          setEditingContent(submission.redactedContent);
                        }}
                        className="text-blue-600 hover:text-blue-700 text-sm"
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedSubmission && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Review Submission</h2>
                <button
                  onClick={() => {
                    setSelectedSubmission(null);
                    setIsEditing(false);
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Original Content</h3>
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <SensitiveDataDetector
                      text={selectedSubmission.originalContent}
                      showOriginal={true}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-700">Redacted Content</h3>
                    {!isEditing && (
                      <button
                        onClick={() => setIsEditing(true)}
                        className="text-blue-600 hover:text-blue-700"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  {isEditing ? (
                    <textarea
                      value={editingContent}
                      onChange={(e) => setEditingContent(e.target.value)}
                      className="w-full h-40 p-4 border border-blue-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                      <p className="whitespace-pre-wrap">{selectedSubmission.redactedContent}</p>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="font-medium text-gray-700 mb-2">Submission Details</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">User ID:</p>
                    <p className="font-medium">{selectedSubmission.userId}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Model:</p>
                    <p className="font-medium">{selectedSubmission.model}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Submitted:</p>
                    <p className="font-medium">
                      {new Date(selectedSubmission.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Auto-redaction:</p>
                    <p className="font-medium">
                      {selectedSubmission.autoRedactionEnabled ? 'Enabled' : 'Disabled'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  onClick={() => {
                    const reason = prompt('Rejection reason:');
                    if (reason) {
                      handleReject(selectedSubmission.id, reason);
                    }
                  }}
                  className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                >
                  Reject
                </button>
                <button
                  onClick={() => handleApprove(
                    selectedSubmission.id,
                    isEditing ? editingContent : undefined
                  )}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Approve {isEditing && 'with Edits'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};