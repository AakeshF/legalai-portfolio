import { 
  PromptSubmission, 
  AnonymizationSettings, 
  PromptReviewStatus,
  RedactedSegment 
} from '../types/anonymization';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

interface SubmitPromptRequest {
  originalContent: string;
  redactedContent: string;
  segments: RedactedSegment[];
  model: string;
  autoRedactionEnabled: boolean;
  consent?: any;
}

interface SubmitPromptResponse {
  id: string;
  requiresReview: boolean;
  status: PromptSubmission['status'];
}

interface ProcessPromptResponse {
  id: string;
  response: string;
  model: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalCost: number;
  };
}

export class AnonymizationAPI {
  private static async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const token = localStorage.getItem('authToken');
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options?.headers
      }
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  static async submitPrompt(data: SubmitPromptRequest): Promise<SubmitPromptResponse> {
    return this.request('/prompts/submit', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async getPromptStatus(promptId: string): Promise<{
    status: PromptSubmission['status'];
    reviewStatus?: PromptReviewStatus;
  }> {
    return this.request(`/prompts/${promptId}/status`);
  }

  static async processPrompt(promptId: string): Promise<ProcessPromptResponse> {
    return this.request(`/prompts/${promptId}/process`, {
      method: 'POST'
    });
  }

  static async getUserSubmissions(
    userId: string,
    params?: {
      limit?: number;
      offset?: number;
      status?: PromptSubmission['status'];
    }
  ): Promise<PromptSubmission[]> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request(`/users/${userId}/submissions?${queryParams}`);
  }

  static async getAnonymizationSettings(userId: string): Promise<AnonymizationSettings> {
    return this.request(`/users/${userId}/anonymization-settings`);
  }

  static async updateAnonymizationSettings(
    userId: string,
    settings: AnonymizationSettings
  ): Promise<AnonymizationSettings> {
    return this.request(`/users/${userId}/anonymization-settings`, {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
  }

  // Admin endpoints
  static async getAdminSubmissions(params: {
    organizationId: string;
    status?: string;
    user?: string;
    dateRange?: string;
    model?: string;
    sortBy?: string;
  }): Promise<PromptSubmission[]> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request(`/admin/submissions?${queryParams}`);
  }

  static async approvePrompt(
    promptId: string,
    editedContent?: string
  ): Promise<void> {
    return this.request(`/admin/submissions/${promptId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ editedContent })
    });
  }

  static async rejectPrompt(promptId: string, reason: string): Promise<void> {
    return this.request(`/admin/submissions/${promptId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
  }

  static async batchAction(params: {
    ids: string[];
    action: 'approve' | 'reject';
  }): Promise<void> {
    return this.request('/admin/submissions/batch', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  static async getAdminStats(organizationId: string): Promise<{
    totalSubmissions: number;
    pendingReviews: number;
    approvalRate: number;
    avgReviewTime: number;
    activeUsers: number;
    submissionsToday: number;
  }> {
    return this.request(`/admin/stats?organizationId=${organizationId}`);
  }

  static async getAuditLogs(params: {
    organizationId: string;
    userId?: string;
    limit?: number;
    startDate?: string;
    endDate?: string;
    action?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request(`/audit-logs?${queryParams}`);
  }
}

// WebSocket connection for real-time updates
export class AnonymizationWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  connect(organizationId: string): void {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws').replace('/api', '');
    this.ws = new WebSocket(`${wsUrl}/ws?organizationId=${organizationId}`);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data.type, data.payload);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      // Attempt to reconnect after 5 seconds
      setTimeout(() => this.connect(organizationId), 5000);
    };
  }

  on(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  off(event: string, callback: (data: any) => void): void {
    this.listeners.get(event)?.delete(callback);
  }

  private emit(event: string, data: any): void {
    this.listeners.get(event)?.forEach(callback => callback(data));
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
    this.listeners.clear();
  }
}