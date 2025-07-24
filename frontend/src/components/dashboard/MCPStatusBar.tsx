import React, { useState } from 'react';
import { 
  Wifi, WifiOff, RefreshCw, Clock, AlertCircle, 
  CheckCircle, Loader2 
} from 'lucide-react';
import { format } from 'date-fns';
import { useMCPServerCheck } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { useQueryClient } from '@tanstack/react-query';

interface MCPServerIndicatorProps {
  server: string;
  showLastSync?: boolean;
}

const MCPServerIndicator: React.FC<MCPServerIndicatorProps> = ({ 
  server, 
  showLastSync = true 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const { data: status, isLoading, refetch } = useMCPServerCheck(server);
  
  const getServerDisplayName = (serverId: string): string => {
    const names: Record<string, string> = {
      'court_system': 'Court System',
      'client_data': 'Client Data',
      'legal_research': 'Legal Research',
      'document_templates': 'Documents'
    };
    return names[serverId] || serverId;
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg">
        <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
        <span className={`text-gray-600 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
          {getServerDisplayName(server)}
        </span>
      </div>
    );
  }
  
  const isOnline = status?.isOnline ?? false;
  
  return (
    <div className={`
      flex items-center space-x-2 px-3 py-2 rounded-lg border
      ${isOnline 
        ? 'bg-green-50 border-green-200' 
        : 'bg-red-50 border-red-200'
      }
    `}>
      {isOnline ? (
        <CheckCircle className="w-4 h-4 text-green-600" />
      ) : (
        <AlertCircle className="w-4 h-4 text-red-600" />
      )}
      
      <div className="flex-1">
        <span className={`font-medium ${
          isOnline ? 'text-green-900' : 'text-red-900'
        } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
          {getSimpleText(getServerDisplayName(server))}
        </span>
        
        {showLastSync && status?.lastChecked && (
          <span className={`ml-2 ${
            isOnline ? 'text-green-600' : 'text-red-600'
          } ${isSimpleMode ? 'text-sm' : 'text-xs'}`}>
            {format(status.lastChecked, 'h:mm a')}
          </span>
        )}
      </div>
      
      <button
        onClick={() => refetch()}
        className="p-1 rounded hover:bg-white hover:bg-opacity-50 transition-colors"
        title={getSimpleText('Refresh')}
      >
        <RefreshCw className="w-3 h-3" />
      </button>
    </div>
  );
};

export const MCPStatusBar: React.FC = () => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);
  
  const mcpServers = ['court_system', 'client_data', 'legal_research', 'document_templates'];
  
  const syncAllMCPData = async () => {
    setIsSyncing(true);
    try {
      // Invalidate all MCP-related queries to force refresh
      await queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return typeof key === 'string' && (
            key.includes('court') || 
            key.includes('deadline') || 
            key.includes('filing') ||
            key.includes('mcp')
          );
        }
      });
      
      // Wait a moment for queries to start
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Refetch all active queries
      await queryClient.refetchQueries({
        type: 'active'
      });
      
    } finally {
      setTimeout(() => setIsSyncing(false), 1000);
    }
  };
  
  return (
    <div className={`
      bg-white border-b border-gray-200 px-4 py-3
      ${isSimpleMode ? '' : 'sticky top-0 z-40'}
    `}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Wifi className="w-5 h-5 text-gray-600" />
          <h3 className={`font-medium text-gray-900 ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            {getSimpleText('Data Sources')}
          </h3>
        </div>
        
        <button
          onClick={syncAllMCPData}
          disabled={isSyncing}
          className={`
            flex items-center space-x-2 px-4 py-2 
            bg-blue-600 text-white rounded-lg
            hover:bg-blue-700 disabled:bg-blue-400
            transition-colors font-medium
            ${isSimpleMode ? 'text-base' : 'text-sm'}
          `}
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
          <span>{getSimpleText(isSyncing ? 'Syncing...' : 'Sync All')}</span>
        </button>
      </div>
      
      <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
        {mcpServers.map(server => (
          <MCPServerIndicator 
            key={server} 
            server={server} 
            showLastSync={true} 
          />
        ))}
      </div>
      
      {isSyncing && (
        <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <span className={`text-blue-800 ${
              isSimpleMode ? 'text-base' : 'text-sm'
            }`}>
              {getSimpleText('Synchronizing all data sources...')}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};