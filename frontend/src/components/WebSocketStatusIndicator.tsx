import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, AlertCircle, Loader2 } from 'lucide-react';
import { websocketService, WebSocketStatus } from '../services/websocket.service';

export const WebSocketStatusIndicator: React.FC = () => {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [isReconnecting, setIsReconnecting] = useState(false);

  useEffect(() => {
    // Subscribe to status changes
    const unsubscribe = websocketService.onStatusChange((newStatus) => {
      setStatus(newStatus);
      setIsReconnecting(newStatus === 'connecting');
    });

    // Connect on mount
    websocketService.connect();

    return () => {
      unsubscribe();
    };
  }, []);

  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-green-600" />;
      case 'connecting':
        return <Loader2 className="w-4 h-4 text-yellow-600 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      default:
        return <WifiOff className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Live updates active';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Connection error';
      default:
        return 'Offline';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'connecting':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor()}`}>
      {getStatusIcon()}
      <span className="ml-2">{getStatusText()}</span>
      {isReconnecting && (
        <span className="ml-2 text-xs opacity-75">Reconnecting...</span>
      )}
    </div>
  );
};