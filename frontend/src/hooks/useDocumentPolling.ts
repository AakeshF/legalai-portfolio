import { useState, useEffect, useRef, useCallback } from 'react';
import { api, ApiError, NetworkError } from '../utils/api';
import { API_ENDPOINTS, buildUrl } from '../config/api.config';

interface Document {
  id: string | number;
  filename: string;
  file_size?: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  upload_timestamp?: string;
  created_at?: string;
  summary?: string;
  metadata?: {
    document_type?: string;
    case_number?: string;
    jurisdiction?: string;
    parties?: Array<{
      name: string;
      role: string;
      type?: 'individual' | 'organization';
    }>;
    dates?: Array<{
      date: string;
      type: string;
      description?: string;
    }>;
    money_amounts?: Array<{
      amount: number;
      currency: string;
      context: string;
    }>;
    key_terms?: string[];
    obligations?: string[];
  };
  legal_metadata?: any;
  extracted_entities?: any;
  ai_analysis?: any;
}

interface UseDocumentPollingOptions {
  onStatusUpdate?: (updatedDocuments: Document[]) => void;
  onError?: (error: Error) => void;
  pollInterval?: number;
  maxRetries?: number;
}

export const useDocumentPolling = (
  documents: Document[],
  options: UseDocumentPollingOptions = {}
) => {
  const {
    onStatusUpdate,
    onError,
    pollInterval = 3000,
    maxRetries = 3
  } = options;

  const [isPolling, setIsPolling] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastPollTimeRef = useRef<number>(Date.now());

  // Track which documents are processing
  const processingDocumentIds = documents
    .filter(doc => doc.processing_status?.toLowerCase() === 'processing')
    .map(doc => doc.id);

  // Check if any documents are processing
  const hasProcessingDocuments = processingDocumentIds.length > 0;

  // Function to fetch status updates
  const fetchStatusUpdates = useCallback(async () => {
    // Don't poll if no documents are processing
    if (!hasProcessingDocuments) {
      return;
    }

    // Cancel any in-flight requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    try {
      // For now, fetch all documents - in production, you'd want a specific endpoint
      // that only returns status updates for specific document IDs
      const response = await api.get(API_ENDPOINTS.documents.list, {
        signal: abortControllerRef.current.signal,
        retries: 0 // Don't retry polling requests
      });

      if (!response.ok) {
        throw new ApiError('Failed to fetch status updates', response.status, response.statusText);
      }

      const data = await response.json();
      
      // Transform data to ensure consistent field naming
      const transformedData = data.map((doc: any) => ({
        ...doc,
        processing_status: doc.processing_status || doc.status || 'pending'
      }));

      // Filter to only documents that were processing
      const relevantUpdates = transformedData.filter((doc: Document) => 
        processingDocumentIds.includes(doc.id)
      );

      // Check if any statuses have changed
      const changedDocuments = relevantUpdates.filter((newDoc: Document) => {
        const oldDoc = documents.find(d => d.id === newDoc.id);
        return oldDoc && oldDoc.processing_status !== newDoc.processing_status;
      });

      if (changedDocuments.length > 0 && onStatusUpdate) {
        onStatusUpdate(transformedData);
      }

      // Reset retry count on successful fetch
      setRetryCount(0);
      lastPollTimeRef.current = Date.now();

    } catch (error) {
      // Don't handle abort errors
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      console.error('Polling error:', error);
      
      // Increment retry count
      setRetryCount(prev => prev + 1);

      // Stop polling if max retries exceeded
      if (retryCount >= maxRetries) {
        stopPolling();
        if (onError) {
          onError(new Error(`Polling stopped after ${maxRetries} consecutive failures`));
        }
      } else if (onError) {
        onError(error as Error);
      }
    }
  }, [documents, processingDocumentIds, hasProcessingDocuments, onStatusUpdate, onError, retryCount, maxRetries]);

  // Function to start polling
  const startPolling = useCallback(() => {
    if (intervalRef.current || !hasProcessingDocuments) {
      return;
    }

    setIsPolling(true);
    setRetryCount(0);

    // Do initial fetch
    fetchStatusUpdates();

    // Set up interval
    intervalRef.current = setInterval(() => {
      fetchStatusUpdates();
    }, pollInterval);
  }, [fetchStatusUpdates, hasProcessingDocuments, pollInterval]);

  // Function to stop polling
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setIsPolling(false);
  }, []);

  // Handle page visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page is hidden, stop polling
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } else {
        // Page is visible again
        if (isPolling && hasProcessingDocuments && !intervalRef.current) {
          // Check if enough time has passed since last poll
          const timeSinceLastPoll = Date.now() - lastPollTimeRef.current;
          if (timeSinceLastPoll >= pollInterval) {
            // Fetch immediately
            fetchStatusUpdates();
          }
          
          // Resume interval
          intervalRef.current = setInterval(() => {
            fetchStatusUpdates();
          }, pollInterval);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isPolling, hasProcessingDocuments, fetchStatusUpdates, pollInterval]);

  // Start/stop polling based on processing documents
  useEffect(() => {
    if (hasProcessingDocuments && !intervalRef.current) {
      startPolling();
    } else if (!hasProcessingDocuments && intervalRef.current) {
      stopPolling();
    }
  }, [hasProcessingDocuments, startPolling, stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    isPolling,
    retryCount,
    startPolling,
    stopPolling,
    hasProcessingDocuments
  };
};
