import { tokenService } from '../auth/token.service';

interface RequestConfig extends RequestInit {
  skipAuth?: boolean;
  retry?: boolean;
}

interface AuthenticationError {
  status: number;
  provider?: string;
  errorType: 'api_key_invalid' | 'billing_exceeded' | 'rate_limited' | 'service_unavailable' | 'unknown';
  message: string;
  userMessage: string;
  suggestedActions: string[];
}

class APIClient {
  private baseURL: string;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value: any) => void;
    reject: (error: any) => void;
    config: RequestConfig;
    url: string;
  }> = [];

  constructor() {
    // For production builds, use relative URLs to support any deployment
    // For development, Vite proxy will handle /api routes
    this.baseURL = import.meta.env.VITE_API_URL || '';
  }

  private processQueue(error: Error | null, token: string | null = null): void {
    this.failedQueue.forEach(prom => {
      if (error) {
        prom.reject(error);
      } else {
        // Retry the request with the new token
        this.request(prom.url, prom.config)
          .then(prom.resolve)
          .catch(prom.reject);
      }
    });
    
    this.failedQueue = [];
  }

  private async request(url: string, config: RequestConfig = {}): Promise<Response> {
    const { skipAuth, retry = true, ...fetchConfig } = config;

    // AUTHENTICATION DISABLED - No auth headers added
    // All requests are now public/unauthenticated
    
    // Make request without any authentication
    const response = await fetch(`${this.baseURL}${url}`, fetchConfig);

    // Don't handle 401s or try to authenticate - just return response as-is
    return response;
  }

  private createAuthenticationError(response: Response, url: string): AuthenticationError {
    const isAIRequest = url.includes('/api/chat') || url.includes('/ai/') || url.includes('/provider');
    
    let errorType: AuthenticationError['errorType'] = 'unknown';
    let userMessage = 'An authentication error occurred. Please try again.';
    let suggestedActions: string[] = ['Try again in a few minutes', 'Contact support if the issue persists'];

    // Parse error details from response headers or body if available
    const errorHeader = response.headers.get('x-error-type');
    const providerHeader = response.headers.get('x-ai-provider');

    if (response.status === 403) {
      if (errorHeader === 'api_key_invalid' || response.statusText.toLowerCase().includes('invalid')) {
        errorType = 'api_key_invalid';
        userMessage = isAIRequest 
          ? 'The AI provider API key is invalid or has expired. Please check your API key configuration.'
          : 'Invalid API credentials. Please check your authentication settings.';
        suggestedActions = [
          'Verify your API key is correct and hasn\'t expired',
          'Check if the API key has the required permissions',
          'Contact your administrator to update the API key',
          'Try using a different AI provider if available'
        ];
      } else if (errorHeader === 'billing_exceeded' || response.statusText.toLowerCase().includes('quota')) {
        errorType = 'billing_exceeded';
        userMessage = isAIRequest
          ? 'Your AI provider billing limit or quota has been exceeded. Please check your billing status.'
          : 'Account quota exceeded. Please check your billing status.';
        suggestedActions = [
          'Check your billing dashboard for usage limits',
          'Upgrade your plan or add credits if needed',
          'Wait for quota reset if on a usage-based plan',
          'Switch to a different AI provider if available'
        ];
      } else if (errorHeader === 'rate_limited') {
        errorType = 'rate_limited';
        userMessage = 'You are sending requests too quickly. Please slow down and try again.';
        suggestedActions = [
          'Wait a few seconds before making another request',
          'Consider upgrading your plan for higher rate limits',
          'Try using a different AI provider if available'
        ];
      }
    } else if (response.status === 401) {
      errorType = 'api_key_invalid';
      userMessage = isAIRequest
        ? 'AI provider authentication failed. Please check your API key.'
        : 'Authentication failed. Please log in again.';
      suggestedActions = [
        'Verify your API key is correctly configured',
        'Check if the API key is active and hasn\'t been revoked',
        'Contact your administrator for assistance'
      ];
    } else if (response.status === 429) {
      errorType = 'rate_limited';
      userMessage = 'Too many requests. Please wait before trying again.';
      suggestedActions = [
        'Wait for the rate limit to reset',
        'Consider upgrading your plan for higher limits',
        'Try spacing out your requests'
      ];
    }

    return {
      status: response.status,
      provider: providerHeader || undefined,
      errorType,
      message: `${response.status} ${response.statusText}`,
      userMessage,
      suggestedActions
    };
  }

  private async handleResponse<T>(response: Response, url: string, method: string): Promise<T> {
    if (response.ok) {
      // Handle empty responses for DELETE requests
      if (method === 'DELETE' && response.status === 204) {
        return undefined as T;
      }
      return response.json();
    }

    // Handle authentication/authorization errors specially
    if (response.status === 401 || response.status === 403 || response.status === 429) {
      const authError = this.createAuthenticationError(response, url);
      const error = new Error(authError.userMessage) as Error & AuthenticationError;
      Object.assign(error, authError);
      throw error;
    }

    // Handle other HTTP errors
    let errorMessage: string;
    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorData.detail || response.statusText;
    } catch {
      errorMessage = response.statusText;
    }

    throw new Error(`${method} ${url} failed: ${errorMessage}`);
  }

  async get<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.request(url, { ...config, method: 'GET' });
    return this.handleResponse<T>(response, url, 'GET');
  }

  async post<T>(url: string, data?: any, config?: RequestConfig): Promise<T> {
    const response = await this.request(url, {
      ...config,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return this.handleResponse<T>(response, url, 'POST');
  }

  async upload<T>(url: string, formData: FormData, config?: RequestConfig): Promise<T> {
    const response = await this.request(url, {
      ...config,
      method: 'POST',
      body: formData,
    });
    return this.handleResponse<T>(response, url, 'POST');
  }

  async put<T>(url: string, data: any, config?: RequestConfig): Promise<T> {
    const response = await this.request(url, {
      ...config,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      body: JSON.stringify(data),
    });
    return this.handleResponse<T>(response, url, 'PUT');
  }

  async delete(url: string, config?: RequestConfig): Promise<void> {
    const response = await this.request(url, { ...config, method: 'DELETE' });
    await this.handleResponse<void>(response, url, 'DELETE');
  }
}

export const apiClient = new APIClient();
