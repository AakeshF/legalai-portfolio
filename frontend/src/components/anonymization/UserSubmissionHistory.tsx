import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, XCircle, FileText, ChevronRight, Filter } from 'lucide-react';
import { PromptSubmission } from '../../types/anonymization';
import { PromptReviewStatus } from './PromptReviewStatus';

interface UserSubmissionHistoryProps {
  userId: string;
  onSelectSubmission?: (submission: PromptSubmission) => void;
}

export const UserSubmissionHistory: React.FC<UserSubmissionHistoryProps> = ({
  userId,
  onSelectSubmission
}) => {
  const [submissions, setSubmissions] = useState<PromptSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetchSubmissions();
  }, [userId]);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/users/${userId}/submissions`);
      const data = await response.json();
      setSubmissions(data);
    } catch (error) {
      console.error('Failed to fetch submissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSubmissions = submissions.filter(submission => {
    if (filter === 'all') return true;
    if (filter === 'pending') return submission.status === 'pending_review';
    return submission.status === filter;
  });

  const getStatusIcon = (status: PromptSubmission['status']) => {
    switch (status) {
      case 'pending_review':
        return <Clock className="w-4 h-4 text-amber-600" />;
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'rejected':
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <FileText className="w-4 h-4 text-gray-600" />;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Submission History</h3>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-600" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Submissions</option>
            <option value="pending">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {filteredSubmissions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No submissions found
        </div>
      ) : (
        <div className="space-y-2">
          {filteredSubmissions.map(submission => (
            <div
              key={submission.id}
              className="bg-white border border-gray-200 rounded-lg overflow-hidden transition-all hover:shadow-md"
            >
              <button
                onClick={() => setExpandedId(expandedId === submission.id ? null : submission.id)}
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(submission.status)}
                  <div>
                    <p className="font-medium text-gray-900">
                      {submission.redactedContent.substring(0, 50)}...
                    </p>
                    <p className="text-sm text-gray-600">
                      {formatDate(submission.createdAt)} • {submission.model}
                    </p>
                  </div>
                </div>
                <ChevronRight
                  className={`w-5 h-5 text-gray-400 transition-transform ${
                    expandedId === submission.id ? 'rotate-90' : ''
                  }`}
                />
              </button>

              {expandedId === submission.id && (
                <div className="px-4 py-3 border-t border-gray-200 space-y-3">
                  <div>
                    <p className="text-sm font-medium text-gray-700">Redacted Content:</p>
                    <p className="text-sm text-gray-600 mt-1 p-2 bg-gray-50 rounded">
                      {submission.redactedContent}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      Detected Sensitive Data: {submission.segments.length} items
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {submission.segments.map((segment, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded"
                        >
                          {segment.redacted}
                        </span>
                      ))}
                    </div>
                  </div>

                  {submission.status === 'pending_review' && (
                    <PromptReviewStatus
                      promptId={submission.id}
                      initialStatus={submission.status}
                      onStatusChange={(newStatus) => {
                        setSubmissions(submissions.map(s =>
                          s.id === submission.id ? { ...s, status: newStatus } : s
                        ));
                      }}
                    />
                  )}

                  {onSelectSubmission && (
                    <button
                      onClick={() => onSelectSubmission(submission)}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      View Details
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};