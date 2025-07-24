import { apiClient } from './api/client';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{
    document_id: string;
    document_name: string;
    relevance: string;
  }>;
}

export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at?: string;
}

export const chatService = {
  async sendMessage(message: string, sessionId?: string): Promise<{
    response: string;
    sources?: Array<{
      document_id: string;
      document_name: string;
      relevance: string;
    }>;
    session_id: string;
  }> {
    // No authentication required - public endpoint
    return apiClient.post('/api/chat', {
      message,
      session_id: sessionId,
    }, { skipAuth: true });
  },

  async getChatHistory(sessionId?: string): Promise<ChatSession[]> {
    const url = sessionId 
      ? `/api/chat/session/${sessionId}`
      : '/api/chat/history';
    return apiClient.get(url, { skipAuth: true });
  },

  async deleteSession(sessionId: string): Promise<void> {
    return apiClient.delete(`/api/chat/session/${sessionId}`, { skipAuth: true });
  },
};
