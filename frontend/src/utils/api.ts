import { API_CONFIG, getApiUrl } from '../config/api.config';

export interface ApiOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
  timeout?: number;
  onRetry?: (attempt: number, error: Error) => void;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public statusText?: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network connection error') {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string = 'Request timeout') {
    super(message);
    this.name = 'TimeoutError';
  }
}

// Check if the browser is online
export const isOnline = (): boolean => {
  return navigator.onLine;
};

// Create an AbortController with timeout
const createAbortController = (timeout?: number): AbortController => {
  const controller = new AbortController();
  
  if (timeout) {
    setTimeout(() => controller.abort(), timeout);
  }
  
  return controller;
};

// Delay helper for retries
const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

// Get auth token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem('legal-ai-token');
};

// Main fetch wrapper with retry logic
export const fetchWithRetry = async (
  url: string,
  options: ApiOptions = {}
): Promise<Response> => {
  const {
    retries = API_CONFIG.retry.maxAttempts,
    retryDelay = API_CONFIG.retry.delay,
    timeout = API_CONFIG.timeout,
    onRetry,
    ...fetchOptions
  } = options;
  
  // Convert relative URLs to absolute URLs
  const fullUrl = url.startsWith('http') ? url : getApiUrl(url);

  // Check if online
  if (!isOnline()) {
    throw new NetworkError('No internet connection');
  }

  // Add auth token to headers if available
  const token = getAuthToken();
  if (token) {
    fetchOptions.headers = {
      ...fetchOptions.headers,
      'Authorization': `Bearer ${token}`
    };
  }

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = createAbortController(timeout);
      
      const response = await fetch(fullUrl, {
        ...fetchOptions,
        signal: controller.signal
      });

      // If response is ok, return it
      if (response.ok) {
        return response;
      }

      // If it's a client error (4xx), don't retry
      if (response.status >= 400 && response.status < 500) {
        const errorData = await response.json().catch(() => null);
        throw new ApiError(
          `API Error: ${response.statusText}`,
          response.status,
          response.statusText,
          errorData
        );
      }

      // For server errors (5xx), throw to trigger retry
      throw new ApiError(
        `Server Error: ${response.statusText}`,
        response.status,
        response.statusText
      );

    } catch (error: any) {
      lastError = error;

      // If it's an abort error, throw timeout
      if (error.name === 'AbortError') {
        throw new TimeoutError();
      }

      // If it's a network error, throw it
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new NetworkError();
      }

      // If it's a client error, don't retry
      if (error instanceof ApiError && error.status && error.status >= 400 && error.status < 500) {
        throw error;
      }

      // If we have retries left, wait and retry
      if (attempt < retries) {
        if (onRetry) {
          onRetry(attempt + 1, error);
        }
        
        // Exponential backoff
        const waitTime = retryDelay * Math.pow(API_CONFIG.retry.backoffMultiplier, attempt);
        await delay(waitTime);
        continue;
      }

      // No retries left, throw the error
      throw lastError;
    }
  }

  throw lastError || new Error('Unknown error occurred');
};

// Helper to handle JSON responses
const handleJsonResponse = async (response: Response) => {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return text;
  }
};

// Convenience methods for common HTTP methods
export const api = {
  get: async (url: string, options?: ApiOptions) => {
    const response = await fetchWithRetry(url, { ...options, method: 'GET' });
    return {
      ...response,
      data: await handleJsonResponse(response)
    };
  },
  
  post: async (url: string, data?: any, options?: ApiOptions) => {
    const response = await fetchWithRetry(url, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: data ? JSON.stringify(data) : undefined
    });
    return {
      ...response,
      data: await handleJsonResponse(response)
    };
  },
  
  put: async (url: string, data?: any, options?: ApiOptions) => {
    const response = await fetchWithRetry(url, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: data ? JSON.stringify(data) : undefined
    });
    return {
      ...response,
      data: await handleJsonResponse(response)
    };
  },
  
  patch: async (url: string, data?: any, options?: ApiOptions) => {
    const response = await fetchWithRetry(url, {
      ...options,
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: data ? JSON.stringify(data) : undefined
    });
    return {
      ...response,
      data: await handleJsonResponse(response)
    };
  },
  
  delete: async (url: string, options?: ApiOptions) => {
    const response = await fetchWithRetry(url, { ...options, method: 'DELETE' });
    return {
      ...response,
      data: await handleJsonResponse(response)
    };
  },
  
  upload: async (url: string, formData: FormData, options?: ApiOptions) => {
    const response = await fetchWithRetry(url, {
      ...options,
      method: 'POST',
      body: formData
    });
    return {
      ...response,
      data: await handleJsonResponse(response)
    };
  }
};

// Offline detection hook
import { useEffect, useState } from 'react';

export const useOnlineStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
};