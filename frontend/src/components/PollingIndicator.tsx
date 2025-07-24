import React from 'react';
import { RefreshCw, Wifi, WifiOff } from 'lucide-react';

interface PollingIndicatorProps {
  isPolling: boolean;
  hasProcessingDocuments: boolean;
  retryCount?: number;
  className?: string;
}

export const PollingIndicator: React.FC<PollingIndicatorProps> = ({
  isPolling,
  hasProcessingDocuments,
  retryCount = 0,
  className = ''
}) => {
  if (!hasProcessingDocuments) {
    return null;
  }

  return (
    <div className={`flex items-center space-x-2 text-sm ${className}`}>
      {isPolling ? (
        <>
          <RefreshCw className="w-4 h-4 text-blue-600 animate-spin" />
          <span className="text-slate-600">
            Checking for updates...
          </span>
          {retryCount > 0 && (
            <span className="text-amber-600 text-xs">
              (Retry {retryCount})
            </span>
          )}
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4 text-slate-400" />
          <span className="text-slate-500">
            Updates paused
          </span>
        </>
      )}
    </div>
  );
};

interface InlinePollingIndicatorProps {
  isPolling: boolean;
  className?: string;
}

export const InlinePollingIndicator: React.FC<InlinePollingIndicatorProps> = ({
  isPolling,
  className = ''
}) => {
  if (!isPolling) {
    return null;
  }

  return (
    <div className={`inline-flex items-center ${className}`}>
      <div className="relative">
        <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
        <div className="absolute inset-0 w-2 h-2 bg-blue-600 rounded-full animate-ping"></div>
      </div>
      <span className="ml-2 text-xs text-slate-600">Live</span>
    </div>
  );
};