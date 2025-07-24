import React, { useEffect, useState } from 'react';
import { 
  Bell, AlertCircle, Calendar, Users, FileText, 
  X, Check, Clock, ExternalLink 
} from 'lucide-react';
import { format } from 'date-fns';
import { subscribeMCPEvents, MCPEventHandlers } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { useToast } from '../Toast';

interface MCPNotification {
  id: string;
  type: 'court_update' | 'deadline' | 'conflict' | 'filing_status';
  title: string;
  message: string;
  timestamp: Date;
  severity: 'info' | 'warning' | 'urgent';
  actionUrl?: string;
  actionLabel?: string;
  read: boolean;
}

export const MCPNotificationCenter: React.FC = () => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const { showSuccess, showError, showWarning } = useToast();
  const [notifications, setNotifications] = useState<MCPNotification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Subscribe to MCP events
  useEffect(() => {
    const handlers: MCPEventHandlers = {
      onCourtUpdate: (update) => {
        const notification: MCPNotification = {
          id: `court-${Date.now()}`,
          type: 'court_update',
          title: 'Court Update',
          message: update.message || 'Court information has been updated',
          timestamp: new Date(),
          severity: update.urgent ? 'urgent' : 'info',
          actionUrl: update.url,
          actionLabel: 'View Details',
          read: false
        };
        
        setNotifications(prev => [notification, ...prev]);
        
        if (update.urgent) {
          showWarning('Urgent court update received');
        } else {
          showSuccess('Court information updated');
        }
      },
      
      onDeadlineApproaching: (deadline) => {
        const notification: MCPNotification = {
          id: `deadline-${Date.now()}`,
          type: 'deadline',
          title: 'Deadline Approaching',
          message: `${deadline.title} - ${deadline.daysRemaining} days remaining`,
          timestamp: new Date(),
          severity: deadline.daysRemaining <= 3 ? 'urgent' : 'warning',
          actionUrl: `/matters/${deadline.matterId}`,
          actionLabel: 'View Matter',
          read: false
        };
        
        setNotifications(prev => [notification, ...prev]);
        showWarning(`Deadline approaching: ${deadline.title}`);
      },
      
      onConflictDetected: (conflict) => {
        const notification: MCPNotification = {
          id: `conflict-${Date.now()}`,
          type: 'conflict',
          title: 'Potential Conflict Detected',
          message: conflict.description,
          timestamp: new Date(),
          severity: conflict.severity === 'high' ? 'urgent' : 'warning',
          actionUrl: '/conflicts',
          actionLabel: 'Review Conflict',
          read: false
        };
        
        setNotifications(prev => [notification, ...prev]);
        showError('Potential conflict detected');
      }
    };
    
    const subscription = subscribeMCPEvents(handlers);
    
    return () => {
      subscription.unsubscribe();
    };
  }, [showSuccess, showError, showWarning]);
  
  // Update unread count
  useEffect(() => {
    setUnreadCount(notifications.filter(n => !n.read).length);
  }, [notifications]);
  
  const markAsRead = (notificationId: string) => {
    setNotifications(prev => 
      prev.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
  };
  
  const markAllAsRead = () => {
    setNotifications(prev => 
      prev.map(n => ({ ...n, read: true }))
    );
  };
  
  const clearNotification = (notificationId: string) => {
    setNotifications(prev => 
      prev.filter(n => n.id !== notificationId)
    );
  };
  
  const getIcon = (type: string) => {
    switch (type) {
      case 'court_update': return Calendar;
      case 'deadline': return Clock;
      case 'conflict': return Users;
      case 'filing_status': return FileText;
      default: return Bell;
    }
  };
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'urgent': return 'red';
      case 'warning': return 'yellow';
      default: return 'blue';
    }
  };
  
  return (
    <>
      {/* Notification Bell */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-gray-100 rounded-lg transition-colors"
        aria-label={getSimpleText('Notifications')}
      >
        <Bell className="w-5 h-5 text-gray-600" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-medium">
            {unreadCount}
          </span>
        )}
      </button>
      
      {/* Notification Panel */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Panel */}
          <div className="fixed right-4 top-16 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className={`font-semibold text-gray-900 ${
                  isSimpleMode ? 'text-lg' : 'text-base'
                }`}>
                  {getSimpleText('Notifications')}
                </h3>
                
                <div className="flex items-center space-x-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className={`text-blue-600 hover:text-blue-700 ${
                        isSimpleMode ? 'text-sm' : 'text-xs'
                      }`}
                    >
                      {getSimpleText('Mark all read')}
                    </button>
                  )}
                  
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
            </div>
            
            {/* Notifications List */}
            <div className="flex-1 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center">
                  <Bell className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className={`text-gray-500 ${
                    isSimpleMode ? 'text-base' : 'text-sm'
                  }`}>
                    {getSimpleText('No notifications')}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {notifications.map(notification => {
                    const Icon = getIcon(notification.type);
                    const color = getSeverityColor(notification.severity);
                    
                    return (
                      <div
                        key={notification.id}
                        className={`
                          p-4 hover:bg-gray-50 transition-colors cursor-pointer
                          ${!notification.read ? 'bg-blue-50' : ''}
                        `}
                        onClick={() => markAsRead(notification.id)}
                      >
                        <div className="flex items-start space-x-3">
                          <div className={`
                            p-2 rounded-lg flex-shrink-0
                            ${color === 'red' ? 'bg-red-100' : ''}
                            ${color === 'yellow' ? 'bg-yellow-100' : ''}
                            ${color === 'blue' ? 'bg-blue-100' : ''}
                          `}>
                            <Icon className={`w-4 h-4
                              ${color === 'red' ? 'text-red-600' : ''}
                              ${color === 'yellow' ? 'text-yellow-600' : ''}
                              ${color === 'blue' ? 'text-blue-600' : ''}
                            `} />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <h4 className={`font-medium text-gray-900 ${
                                  isSimpleMode ? 'text-base' : 'text-sm'
                                }`}>
                                  {getSimpleText(notification.title)}
                                </h4>
                                <p className={`text-gray-600 mt-1 ${
                                  isSimpleMode ? 'text-sm' : 'text-xs'
                                }`}>
                                  {getSimpleText(notification.message)}
                                </p>
                                
                                {notification.actionUrl && (
                                  <a
                                    href={notification.actionUrl}
                                    className={`
                                      inline-flex items-center mt-2 text-blue-600 
                                      hover:text-blue-700 font-medium
                                      ${isSimpleMode ? 'text-sm' : 'text-xs'}
                                    `}
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {getSimpleText(notification.actionLabel || 'View')}
                                    <ExternalLink className="w-3 h-3 ml-1" />
                                  </a>
                                )}
                              </div>
                              
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  clearNotification(notification.id);
                                }}
                                className="p-1 hover:bg-gray-200 rounded ml-2"
                              >
                                <X className="w-3 h-3 text-gray-400" />
                              </button>
                            </div>
                            
                            <p className={`text-gray-500 mt-2 ${
                              isSimpleMode ? 'text-xs' : 'text-[10px]'
                            }`}>
                              {format(notification.timestamp, 'h:mm a')}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
};