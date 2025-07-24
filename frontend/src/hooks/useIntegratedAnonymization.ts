import { useState, useCallback } from 'react';
import { IntegratedAnonymizationAPI } from '../services/integrated-anonymization-api';
import type { IntegratedResponse, ProcessPromptOptions } from '../services/integrated-anonymization-api';

export function useIntegratedAnonymization() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const processPrompt = useCallback(async (
    prompt: string,
    options?: ProcessPromptOptions
  ): Promise<IntegratedResponse> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await IntegratedAnonymizationAPI.processPrompt(prompt, options);
      
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process prompt';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const checkReviewStatus = useCallback(async (reviewId: string) => {
    try {
      return await IntegratedAnonymizationAPI.checkReviewStatus(reviewId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to check status';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const handleIntegratedResponse = useCallback(async (
    response: IntegratedResponse,
    callbacks: {
      onSuccess?: (data: any) => void;
      onConsentRequired?: (consentDetails: any) => void;
      onPendingReview?: (reviewId: string) => void;
      onBlocked?: (message: string) => void;
    }
  ) => {
    switch (response.status) {
      case 'success':
        callbacks.onSuccess?.(response.data);
        break;
        
      case 'consent_required':
        callbacks.onConsentRequired?.(response.consentDetails);
        break;
        
      case 'pending_review':
        if (response.reviewId) {
          callbacks.onPendingReview?.(response.reviewId);
        }
        break;
        
      case 'blocked':
        callbacks.onBlocked?.(response.message || 'Request blocked for security reasons');
        break;
    }
  }, []);

  return {
    processPrompt,
    checkReviewStatus,
    handleIntegratedResponse,
    loading,
    error
  };
}

// Hook for polling review status
export function useReviewStatusPolling(
  reviewId: string | null,
  options?: {
    interval?: number;
    onStatusChange?: (status: any) => void;
  }
) {
  const [status, setStatus] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);

  useCallback(() => {
    if (!reviewId) return;

    const checkStatus = async () => {
      try {
        setIsPolling(true);
        const result = await IntegratedAnonymizationAPI.checkReviewStatus(reviewId);
        setStatus(result);
        options?.onStatusChange?.(result);
        
        // Stop polling if approved or rejected
        if (result.status !== 'pending') {
          return false; // Stop polling
        }
        return true; // Continue polling
      } catch (error) {
        console.error('Failed to check review status:', error);
        return true; // Continue polling on error
      } finally {
        setIsPolling(false);
      }
    };

    // Initial check
    checkStatus();

    // Set up polling
    const interval = setInterval(async () => {
      const shouldContinue = await checkStatus();
      if (!shouldContinue) {
        clearInterval(interval);
      }
    }, options?.interval || 5000);

    return () => clearInterval(interval);
  }, [reviewId, options]);

  return { status, isPolling };
}
