import React, { useState, useEffect, useCallback } from 'react';
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { PromptSubmission, PromptReviewStatus as ReviewStatusType } from '../../types/anonymization';

interface PromptReviewStatusProps {
  promptId: string;
  initialStatus?: PromptSubmission['status'];
  onStatusChange?: (status: PromptSubmission['status'], reviewStatus?: ReviewStatusType) => void;
  pollingInterval?: number;
}

export const PromptReviewStatus: React.FC<PromptReviewStatusProps> = ({
  promptId,
  initialStatus = 'pending_review',
  onStatusChange,
  pollingInterval = 5000
}) => {
  const [status, setStatus] = useState<PromptSubmission['status']>(initialStatus);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatusType | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date>(new Date());

  const checkStatus = useCallback(async () => {
    try {
      setIsPolling(true);
      const response = await fetch(`/api/prompts/${promptId}/status`);
      const data = await response.json();
      
      if (data.status !== status || data.reviewStatus?.status !== reviewStatus?.status) {
        setStatus(data.status);
        setReviewStatus(data.reviewStatus);
        onStatusChange?.(data.status, data.reviewStatus);
      }
      
      setLastChecked(new Date());
    } catch (error) {
      console.error('Failed to check prompt status:', error);
    } finally {
      setIsPolling(false);
    }
  }, [promptId, status, reviewStatus, onStatusChange]);

  useEffect(() => {
    if (status === 'pending_review') {
      checkStatus();
      const interval = setInterval(checkStatus, pollingInterval);
      return () => clearInterval(interval);
    }
  }, [status, checkStatus, pollingInterval]);

  const getStatusIcon = () => {
    switch (status) {
      case 'pending_review':
        return <Clock className={`w-5 h-5 ${isPolling ? 'animate-spin' : ''} text-amber-600`} />;
      case 'approved':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'rejected':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'pending_review':
        return {
          title: 'Prompt Under Review',
          description: 'Your prompt contains sensitive information and is being reviewed by an administrator.',
          color: 'amber'
        };
      case 'approved':
        return {
          title: 'Prompt Approved',
          description: reviewStatus?.comments || 'Your prompt has been approved and is being processed.',
          color: 'green'
        };
      case 'rejected':
        return {
          title: 'Prompt Rejected',
          description: reviewStatus?.comments || 'Your prompt was rejected due to security concerns.',
          color: 'red'
        };
      default:
        return {
          title: 'Processing',
          description: 'Your prompt is being processed.',
          color: 'gray'
        };
    }
  };

  const statusInfo = getStatusMessage();

  return (
    <div className={`p-4 bg-${statusInfo.color}-50 border border-${statusInfo.color}-200 rounded-lg`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">{getStatusIcon()}</div>
        <div className="flex-1">
          <h3 className={`font-medium text-${statusInfo.color}-900`}>{statusInfo.title}</h3>
          <p className={`text-sm text-${statusInfo.color}-700 mt-1`}>{statusInfo.description}</p>
          
          {status === 'pending_review' && (
            <div className="flex items-center gap-4 mt-3 text-xs text-gray-600">
              <span>Last checked: {lastChecked.toLocaleTimeString()}</span>
              <button
                onClick={checkStatus}
                disabled={isPolling}
                className="flex items-center gap-1 text-blue-600 hover:text-blue-700 disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${isPolling ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          )}
          
          {reviewStatus && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-600">
                Reviewed by {reviewStatus.reviewedBy} at {new Date(reviewStatus.reviewedAt!).toLocaleString()}
              </p>
              {reviewStatus.editedContent && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-gray-700">Edited content:</p>
                  <p className="text-sm text-gray-600 mt-1 p-2 bg-white rounded border border-gray-200">
                    {reviewStatus.editedContent}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};