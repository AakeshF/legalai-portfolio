import { ConsentRequirement } from '../types/consent';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface IntegratedResponse {
  status: 'success' | 'consent_required' | 'pending_review' | 'blocked';
  data?: {
    response?: string;
    model?: string;
    usage?: {
      promptTokens: number;
      completionTokens: number;
      totalCost: number;
    };
  };
  message?: string;
  consentDetails?: ConsentRequirement;
  reviewId?: string;
}

export interface ProcessPromptOptions {
  model?: string;
  context?: any;
  consent?: {
    clientAuthorized: boolean;
    dataIsSanitized: boolean;
    understandRisks: boolean;
    additionalNotes?: string;
  };
}

export class IntegratedAnonymizationAPI {
  private static async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const token = localStorage.getItem('authToken');
    const orgId = localStorage.getItem('organizationId');
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(orgId && { 'X-Organization-ID': orgId }),
        ...options?.headers
      }
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Main integrated endpoint that handles the entire security pipeline
   */
  static async processPrompt(
    prompt: string,
    options?: ProcessPromptOptions
  ): Promise<IntegratedResponse> {
    return this.request('/ai/integrated/process', {
      method: 'POST',
      body: JSON.stringify({
        prompt,
        ...options
      })
    });
  }

  /**
   * Check the status of a prompt under review
   */
  static async checkReviewStatus(reviewId: string): Promise<{
    status: 'pending' | 'approved' | 'rejected';
    reviewedBy?: string;
    reviewedAt?: string;
    comments?: string;
  }> {
    return this.request(`/ai/review/${reviewId}/status`);
  }

  /**
   * Get user's anonymization settings
   */
  static async getSettings(userId: string) {
    return this.request(`/users/${userId}/anonymization-settings`);
  }

  /**
   * Update user's anonymization settings
   */
  static async updateSettings(userId: string, settings: any) {
    return this.request(`/users/${userId}/anonymization-settings`, {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
  }

  /**
   * Get submission history
   */
  static async getSubmissionHistory(userId: string, params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }) {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request(`/users/${userId}/submissions?${queryParams}`);
  }

  /**
   * Admin endpoints for review dashboard
   */
  static async getAdminQueue(organizationId: string) {
    return this.request(`/admin/organizations/${organizationId}/review-queue`);
  }

  static async approvePrompt(reviewId: string, editedContent?: string) {
    return this.request(`/admin/reviews/${reviewId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ editedContent })
    });
  }

  static async rejectPrompt(reviewId: string, reason: string) {
    return this.request(`/admin/reviews/${reviewId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
  }

  /**
   * Session management for conversation context
   */
  static async createSession(): Promise<{ session_id: string }> {
    return this.request('/ai/integrated/session/create', {
      method: 'POST'
    });
  }

  /**
   * Batch processing for multiple prompts
   */
  static async processBatch(prompts: Array<{ prompt: string; options?: ProcessPromptOptions }>) {
    return this.request('/ai/integrated/batch', {
      method: 'POST',
      body: JSON.stringify({ prompts })
    });
  }

  /**
   * Health check for AI providers
   */
  static async checkHealth(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy';
    providers: Array<{
      name: string;
      status: 'available' | 'unavailable';
      response_time_ms: number;
    }>;
  }> {
    return this.request('/ai/integrated/health');
  }

  /**
   * Test anonymization patterns
   */
  static async testAnonymization(text: string): Promise<{
    original: string;
    anonymized: string;
    patterns_matched: Array<{
      type: string;
      count: number;
    }>;
  }> {
    return this.request('/anonymization/test', {
      method: 'POST',
      body: JSON.stringify({ text })
    });
  }

  /**
   * WebSocket connection for real-time updates
   */
  static connectWebSocket(promptId: string): WebSocket {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws');
    return new WebSocket(`${wsUrl}/prompts/ws/${promptId}`);
  }
}