import React from 'react';
import { Wifi, WifiOff, RefreshCw, Clock } from 'lucide-react';
import { useMCPServerCheck } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { format } from 'date-fns';

interface MCPStatusBadgeProps {
  server: string;
  onRefresh?: () => void;
}

export const MCPStatusBadge: React.FC<MCPStatusBadgeProps> = ({ server, onRefresh }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const { data: status, isLoading, refetch } = useMCPServerCheck(server);
  
  const handleRefresh = () => {
    refetch();
    onRefresh?.();
  };
  
  if (isLoading) {
    return (
      <div className={`inline-flex items-center px-3 py-1 rounded-full bg-gray-100 border border-gray-200 ${
        isSimpleMode ? 'text-base' : 'text-sm'
      }`}>
        <RefreshCw className="w-4 h-4 text-gray-500 animate-spin mr-2" />
        <span className="text-gray-600">{getSimpleText('Checking...')}</span>
      </div>
    );
  }
  
  const isOnline = status?.isOnline ?? false;
  const lastChecked = status?.lastChecked;
  
  return (
    <div className={`inline-flex items-center ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
      <div className={`
        inline-flex items-center px-3 py-1 rounded-full border font-medium
        ${isOnline 
          ? 'bg-green-50 border-green-200 text-green-700' 
          : 'bg-yellow-50 border-yellow-200 text-yellow-700'
        }
      `}>
        {isOnline ? (
          <Wifi className="w-4 h-4 mr-2" />
        ) : (
          <WifiOff className="w-4 h-4 mr-2" />
        )}
        <span>
          {isOnline 
            ? getSimpleText('Live Court Data') 
            : getSimpleText('Offline Mode')
          }
        </span>
      </div>
      
      <button
        onClick={handleRefresh}
        className="ml-2 p-1 rounded-lg hover:bg-gray-100 transition-colors"
        title={getSimpleText('Refresh status')}
      >
        <RefreshCw className="w-4 h-4 text-gray-500" />
      </button>
      
      {lastChecked && (
        <div className="ml-3 flex items-center text-gray-500">
          <Clock className="w-3 h-3 mr-1" />
          <span className={isSimpleMode ? 'text-sm' : 'text-xs'}>
            {format(lastChecked, 'h:mm a')}
          </span>
        </div>
      )}
      
      {status?.error && !isOnline && (
        <div className={`ml-3 text-yellow-600 ${isSimpleMode ? 'text-sm' : 'text-xs'}`}>
          ({getSimpleText('Using cached data')})
        </div>
      )}
    </div>
  );
};