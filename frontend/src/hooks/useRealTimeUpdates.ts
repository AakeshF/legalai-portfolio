import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { websocketService } from '../services/websocket.service';
import { useToast } from '../components/ui/Toast';

interface RealTimeUpdateOptions {
  onDocumentUpdate?: (documentId: string | number) => void;
  onChatMessage?: (message: any) => void;
  onUserPresence?: (userId: string, status: 'online' | 'offline') => void;
  onNotification?: (notification: any) => void;
}

export const useRealTimeUpdates = (options: RealTimeUpdateOptions = {}) => {
  const queryClient = useQueryClient();
  const { showInfo, showSuccess } = useToast();

  const handleDocumentUpdate = useCallback(
    (message: any) => {
      const { document_id, status, update_type } = message.data;

      // Invalidate document queries to refetch
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', document_id] });

      // Show notification
      if (update_type === 'processing_complete') {
        showSuccess('Document processed', 'Your document has been analyzed successfully');
      }

      // Call custom handler
      options.onDocumentUpdate?.(document_id);
    },
    [queryClient, showSuccess, options]
  );

  const handleChatMessage = useCallback(
    (message: any) => {
      const { session_id, message: chatMessage } = message.data;

      // Update chat query data
      queryClient.setQueryData(['chat', session_id], (oldData: any) => {
        if (!oldData) return oldData;
        return {
          ...oldData,
          messages: [...(oldData.messages || []), chatMessage],
        };
      });

      // Call custom handler
      options.onChatMessage?.(chatMessage);
    },
    [queryClient, options]
  );

  const handleUserPresence = useCallback(
    (message: any) => {
      const { user_id, status } = message.data;

      // Update presence data
      queryClient.setQueryData(['presence'], (oldData: any) => ({
        ...oldData,
        [user_id]: status,
      }));

      // Call custom handler
      options.onUserPresence?.(user_id, status);
    },
    [queryClient, options]
  );

  const handleNotification = useCallback(
    (message: any) => {
      const notification = message.data;

      // Show toast notification
      showInfo(notification.title, notification.message);

      // Invalidate notifications query
      queryClient.invalidateQueries({ queryKey: ['notifications'] });

      // Call custom handler
      options.onNotification?.(notification);
    },
    [queryClient, showInfo, options]
  );

  useEffect(() => {
    // Subscribe to different message types
    const unsubscribers = [
      websocketService.on('document_update', handleDocumentUpdate),
      websocketService.on('chat_message', handleChatMessage),
      websocketService.on('user_presence', handleUserPresence),
      websocketService.on('notification', handleNotification),
    ];

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }, [handleDocumentUpdate, handleChatMessage, handleUserPresence, handleNotification]);

  // Expose methods to send messages
  const sendChatMessage = useCallback((sessionId: string, content: string) => {
    websocketService.send('chat_message', {
      session_id: sessionId,
      content,
    });
  }, []);

  const updatePresence = useCallback((status: 'online' | 'away' | 'busy') => {
    websocketService.send('presence_update', { status });
  }, []);

  const subscribeToDocument = useCallback((documentId: string | number) => {
    websocketService.send('subscribe', {
      type: 'document',
      id: documentId,
    });

    // Return unsubscribe function
    return () => {
      websocketService.send('unsubscribe', {
        type: 'document',
        id: documentId,
      });
    };
  }, []);

  return {
    sendChatMessage,
    updatePresence,
    subscribeToDocument,
  };
};