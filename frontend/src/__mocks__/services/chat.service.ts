import { vi } from 'vitest';

export const chatService = {
  sendMessage: vi.fn(),
  getChatHistory: vi.fn(),
  deleteSession: vi.fn(),
};