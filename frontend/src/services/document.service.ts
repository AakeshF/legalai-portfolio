import { apiClient } from './api/client';

export interface Document {
  id: number;
  filename: string;
  file_path: string;
  content?: string;
  document_type: string;
  processing_status: string;
  extracted_entities?: Record<string, any>;
  ai_analysis?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export const documentService = {
  async getDocuments(params?: {
    page?: number;
    limit?: number;
    document_type?: string;
  }): Promise<{ documents: Document[]; total: number }> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.document_type) queryParams.append('document_type', params.document_type);
    
    return apiClient.get(`/api/documents?${queryParams}`, { skipAuth: true });
  },

  async getDocument(id: number): Promise<Document> {
    return apiClient.get(`/api/documents/${id}`, { skipAuth: true });
  },

  async uploadDocument(file: File, documentType: string): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    
    return apiClient.upload('/api/documents/upload', formData, { skipAuth: true });
  },

  async deleteDocument(id: number): Promise<void> {
    return apiClient.delete(`/api/documents/${id}`, { skipAuth: true });
  },

  async reprocessDocument(id: number): Promise<Document> {
    return apiClient.post(`/api/documents/${id}/reprocess`, {}, { skipAuth: true });
  },

  async searchDocuments(query: string): Promise<Document[]> {
    return apiClient.get(`/api/documents/search?q=${encodeURIComponent(query)}`, { skipAuth: true });
  },
};
