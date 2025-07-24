import { vi } from 'vitest';

export const documentService = {
  getDocuments: vi.fn(),
  getDocument: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  reprocessDocument: vi.fn(),
  searchDocuments: vi.fn(),
};