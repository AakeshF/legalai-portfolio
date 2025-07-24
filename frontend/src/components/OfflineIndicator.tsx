import React from 'react';
import { WifiOff } from 'lucide-react';
import { useOnlineStatus } from '../utils/api';

const OfflineIndicator: React.FC = () => {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-sm z-50 animate-slide-up">
      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <WifiOff className="w-5 h-5 text-orange-600" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-orange-900">You're offline</h4>
            <p className="text-sm text-orange-700 mt-1">
              Some features may be unavailable. Your changes will sync when you're back online.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OfflineIndicator;