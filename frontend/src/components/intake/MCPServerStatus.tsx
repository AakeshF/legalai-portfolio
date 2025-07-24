import React from 'react';
import { Wifi, WifiOff, AlertTriangle, RefreshCw } from 'lucide-react';
import { useMCPServerStatus } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';

export const MCPServerStatus: React.FC = () => {
  const { data: servers, isLoading, refetch } = useMCPServerStatus();
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  // Don't show if loading or no servers
  if (isLoading || !servers || servers.length === 0) {
    return null;
  }
  
  const connectedCount = servers.filter(s => s.status === 'connected').length;
  const totalCount = servers.length;
  const allConnected = connectedCount === totalCount;
  const someConnected = connectedCount > 0 && connectedCount < totalCount;
  const noneConnected = connectedCount === 0;
  
  return (
    <div className={`mb-6 p-4 rounded-lg border ${
      allConnected 
        ? 'bg-green-50 border-green-200' 
        : someConnected 
          ? 'bg-yellow-50 border-yellow-200'
          : 'bg-red-50 border-red-200'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {allConnected ? (
            <Wifi className="w-5 h-5 text-green-600" />
          ) : someConnected ? (
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
          ) : (
            <WifiOff className="w-5 h-5 text-red-600" />
          )}
          
          <div>
            <p className={`font-medium ${
              allConnected ? 'text-green-900' : someConnected ? 'text-yellow-900' : 'text-red-900'
            } ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
              {allConnected 
                ? getSimpleText('All systems online')
                : someConnected 
                  ? getSimpleText('Some systems offline')
                  : getSimpleText('Systems offline - Limited functionality')
              }
            </p>
            <p className={`${
              allConnected ? 'text-green-700' : someConnected ? 'text-yellow-700' : 'text-red-700'
            } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
              {getSimpleText(`${connectedCount} of ${totalCount} services connected`)}
            </p>
          </div>
        </div>
        
        <button
          onClick={() => refetch()}
          className={`p-2 rounded-lg transition-colors ${
            allConnected 
              ? 'hover:bg-green-100' 
              : someConnected 
                ? 'hover:bg-yellow-100'
                : 'hover:bg-red-100'
          }`}
          title={getSimpleText('Refresh connection status')}
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
      
      {/* Show individual server status on expand */}
      {!allConnected && (
        <details className="mt-3">
          <summary className={`cursor-pointer text-gray-600 hover:text-gray-800 ${
            isSimpleMode ? 'text-base' : 'text-sm'
          }`}>
            {getSimpleText('Show details')}
          </summary>
          <div className="mt-2 space-y-1">
            {servers.map(server => (
              <div key={server.id} className="flex items-center justify-between py-1">
                <span className={`text-gray-700 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                  {server.name}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  server.status === 'connected' 
                    ? 'bg-green-100 text-green-700'
                    : server.status === 'error'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-700'
                }`}>
                  {getSimpleText(server.status)}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
};