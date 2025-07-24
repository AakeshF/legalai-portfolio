import { apiClient } from './api/client';
import type { AIProvider } from '../components/ai-config/types';

interface AuthTestResponse {
  authenticated?: boolean;
  healthy?: boolean;
  error?: string;
  billing_info?: {
    quotaRemaining?: number;
    quotaUsed?: number;
    quotaLimit?: number;
    billingPeriodEnd?: string;
  };
}

interface ConnectivityTestResponse {
  success?: boolean;
  error?: string;
}

interface RateLimitTestResponse {
  rate_limit_ok?: boolean;
  error?: string;
}

export interface ProviderAuthStatus {
  provider: AIProvider;
  isAuthenticated: boolean;
  isHealthy: boolean;
  lastChecked: Date;
  error?: string;
  errorType?: 'api_key_invalid' | 'billing_exceeded' | 'rate_limited' | 'service_unavailable';
  billingInfo?: {
    quotaRemaining?: number;
    quotaUsed?: number;
    quotaLimit?: number;
    billingPeriodEnd?: Date;
  };
  responseTime?: number;
}

export interface ProviderDiagnostics {
  provider: AIProvider;
  testResults: {
    authentication: 'pass' | 'fail';
    connectivity: 'pass' | 'fail';
    billing: 'pass' | 'fail' | 'unknown';
    rateLimit: 'pass' | 'fail' | 'unknown';
  };
  details: string[];
  recommendations: string[];
}

class AIProviderAuthService {
  private statusCache = new Map<AIProvider, ProviderAuthStatus>();
  private cacheExpiry = 5 * 60 * 1000; // 5 minutes

  /**
   * Check authentication status for a specific provider
   */
  async checkProviderAuth(provider: AIProvider): Promise<ProviderAuthStatus> {
    const cached = this.statusCache.get(provider);
    if (cached && Date.now() - cached.lastChecked.getTime() < this.cacheExpiry) {
      return cached;
    }

    const startTime = Date.now();
    let status: ProviderAuthStatus = {
      provider,
      isAuthenticated: false,
      isHealthy: false,
      lastChecked: new Date()
    };

    try {
      // Test authentication with a simple API call
      const response = await apiClient.post<AuthTestResponse>('/api/ai/test-auth', {
        provider,
        test_type: 'authentication'
      });

      status = {
        provider,
        isAuthenticated: response.authenticated || false,
        isHealthy: response.healthy || false,
        lastChecked: new Date(),
        billingInfo: response.billing_info ? {
          ...response.billing_info,
          billingPeriodEnd: response.billing_info.billingPeriodEnd 
            ? new Date(response.billing_info.billingPeriodEnd) 
            : undefined
        } : undefined,
        responseTime: Date.now() - startTime
      };

      if (!response.authenticated && response.error) {
        status.error = response.error;
        status.errorType = this.categorizeError(response.error);
      }
    } catch (error: any) {
      status.error = error.message;
      status.errorType = error.errorType || 'service_unavailable';
      status.responseTime = Date.now() - startTime;
    }

    this.statusCache.set(provider, status);
    return status;
  }

  /**
   * Check authentication status for all configured providers
   */
  async checkAllProviders(): Promise<ProviderAuthStatus[]> {
    const providers: AIProvider[] = ['openai', 'anthropic', 'google', 'azure', 'ollama'];
    const results = await Promise.all(
      providers.map(provider => this.checkProviderAuth(provider))
    );
    return results;
  }

  /**
   * Run comprehensive diagnostics on a provider
   */
  async runDiagnostics(provider: AIProvider): Promise<ProviderDiagnostics> {
    const diagnostics: ProviderDiagnostics = {
      provider,
      testResults: {
        authentication: 'fail',
        connectivity: 'fail',
        billing: 'unknown',
        rateLimit: 'unknown'
      },
      details: [],
      recommendations: []
    };

    try {
      // Test connectivity
      const connectivityResponse = await apiClient.post<ConnectivityTestResponse>('/api/ai/test-auth', {
        provider,
        test_type: 'connectivity'
      });

      if (connectivityResponse.success) {
        diagnostics.testResults.connectivity = 'pass';
        diagnostics.details.push('✓ Provider endpoint is reachable');
      } else {
        diagnostics.details.push('✗ Cannot reach provider endpoint');
        diagnostics.recommendations.push('Check your internet connection');
        return diagnostics;
      }

      // Test authentication
      const authResponse = await apiClient.post<AuthTestResponse>('/api/ai/test-auth', {
        provider,
        test_type: 'authentication'
      });

      if (authResponse.authenticated) {
        diagnostics.testResults.authentication = 'pass';
        diagnostics.details.push('✓ API key is valid and authenticated');
      } else {
        diagnostics.details.push('✗ Authentication failed');
        if (authResponse.error) {
          diagnostics.details.push(`  Error: ${authResponse.error}`);
        }
        this.addAuthenticationRecommendations(diagnostics, authResponse.error);
      }

      // Test billing/quota status
      if (authResponse.authenticated && authResponse.billing_info) {
        const billing = authResponse.billing_info;
        if (billing.quotaRemaining && billing.quotaRemaining > 0) {
          diagnostics.testResults.billing = 'pass';
          diagnostics.details.push(`✓ Quota available: ${billing.quotaRemaining}/${billing.quotaLimit}`);
        } else {
          diagnostics.testResults.billing = 'fail';
          diagnostics.details.push('✗ Quota exceeded or billing issue');
          diagnostics.recommendations.push('Check billing dashboard and add credits if needed');
        }
      }

      // Test rate limits
      const rateLimitResponse = await apiClient.post<RateLimitTestResponse>('/api/ai/test-auth', {
        provider,
        test_type: 'rate_limit'
      });

      if (rateLimitResponse.rate_limit_ok) {
        diagnostics.testResults.rateLimit = 'pass';
        diagnostics.details.push('✓ Rate limits are healthy');
      } else {
        diagnostics.testResults.rateLimit = 'fail';
        diagnostics.details.push('✗ Rate limit exceeded');
        diagnostics.recommendations.push('Wait before making more requests or upgrade your plan');
      }

    } catch (error: any) {
      diagnostics.details.push(`✗ Diagnostic error: ${error.message}`);
      
      if (error.errorType) {
        switch (error.errorType) {
          case 'api_key_invalid':
            diagnostics.recommendations.push('Verify your API key is correct and active');
            break;
          case 'billing_exceeded':
            diagnostics.recommendations.push('Check your billing status and add credits');
            break;
          case 'rate_limited':
            diagnostics.recommendations.push('Wait before retrying or upgrade your plan');
            break;
          default:
            diagnostics.recommendations.push('Contact support for assistance');
        }
      }
    }

    return diagnostics;
  }

  /**
   * Get cached status without making new requests
   */
  getCachedStatus(provider: AIProvider): ProviderAuthStatus | null {
    const cached = this.statusCache.get(provider);
    if (cached && Date.now() - cached.lastChecked.getTime() < this.cacheExpiry) {
      return cached;
    }
    return null;
  }

  /**
   * Clear cache for a specific provider or all providers
   */
  clearCache(provider?: AIProvider): void {
    if (provider) {
      this.statusCache.delete(provider);
    } else {
      this.statusCache.clear();
    }
  }

  /**
   * Find healthy providers that can be used as fallbacks
   */
  async getHealthyProviders(): Promise<AIProvider[]> {
    const allStatus = await this.checkAllProviders();
    return allStatus
      .filter(status => status.isAuthenticated && status.isHealthy)
      .map(status => status.provider);
  }

  private categorizeError(error: string): ProviderAuthStatus['errorType'] {
    const errorLower = error.toLowerCase();
    
    if (errorLower.includes('api key') || errorLower.includes('unauthorized') || errorLower.includes('invalid')) {
      return 'api_key_invalid';
    } else if (errorLower.includes('quota') || errorLower.includes('billing') || errorLower.includes('limit')) {
      return 'billing_exceeded';
    } else if (errorLower.includes('rate limit') || errorLower.includes('too many')) {
      return 'rate_limited';
    } else {
      return 'service_unavailable';
    }
  }

  private addAuthenticationRecommendations(diagnostics: ProviderDiagnostics, error?: string): void {
    if (!error) {
      diagnostics.recommendations.push('Verify your API key is configured correctly');
      return;
    }

    const errorLower = error.toLowerCase();
    
    if (errorLower.includes('api key') || errorLower.includes('invalid')) {
      diagnostics.recommendations.push('Check that your API key is correct and hasn\'t expired');
      diagnostics.recommendations.push('Verify the API key has the required permissions');
      diagnostics.recommendations.push('Contact your administrator to update the API key');
    } else if (errorLower.includes('quota') || errorLower.includes('billing')) {
      diagnostics.recommendations.push('Check your billing dashboard for usage limits');
      diagnostics.recommendations.push('Add credits or upgrade your plan if needed');
    } else if (errorLower.includes('rate limit')) {
      diagnostics.recommendations.push('Wait before making more requests');
      diagnostics.recommendations.push('Consider upgrading for higher rate limits');
    } else {
      diagnostics.recommendations.push('Check provider status page for outages');
      diagnostics.recommendations.push('Contact support if the issue persists');
    }
  }
}

export const aiProviderAuthService = new AIProviderAuthService();
