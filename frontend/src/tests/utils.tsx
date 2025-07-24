import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { SimpleModeProvider } from '../contexts/SimpleModeContext';
import { AIPreferencesProvider } from '../contexts/AIPreferencesContext';
import { ToastProvider } from '../components/Toast';
import { vi } from 'vitest';

// Mock user for testing
export const mockUser = {
  id: 1,
  email: '[email@example.com]',
  full_name: 'Test User',
  role: 'attorney',
  organization_id: 1,
  organization: {
    id: 1,
    name: 'Test Law Firm',
  },
};

// Mock auth context value
export const mockAuthContextValue = {
  user: mockUser,
  organization: null,
  loading: false,
  error: null,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  isAuthenticated: true,
};

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authValue?: Partial<typeof mockAuthContextValue>;
  route?: string;
}

// Custom render function with all providers
export function renderWithProviders(
  ui: React.ReactElement,
  {
    authValue = mockAuthContextValue,
    route = '/',
    ...options
  }: CustomRenderOptions = {}
) {
  window.history.pushState({}, 'Test page', route);

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <BrowserRouter>
        <AuthProvider>
          <AIPreferencesProvider>
            <SimpleModeProvider>
              <ToastProvider>
                {children}
              </ToastProvider>
            </SimpleModeProvider>
          </AIPreferencesProvider>
        </AuthProvider>
      </BrowserRouter>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options }),
  };
}

// Re-export everything from testing library
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';

// Utility to wait for async operations
export const waitForLoadingToFinish = () => 
  vi.waitFor(() => {
    const loadingElements = document.querySelectorAll('[aria-busy="true"]');
    if (loadingElements.length > 0) {
      throw new Error('Still loading');
    }
  });

// Mock API responses
export const mockApiResponses = {
  login: {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    user: mockUser,
  },
  documents: {
    documents: [
      {
        id: 1,
        filename: 'test-document.pdf',
        file_path: '/uploads/test-document.pdf',
        document_type: 'contract',
        processing_status: 'completed',
        created_at: '2024-01-01T00:00:00Z',
      },
    ],
    total: 1,
  },
  chat: {
    response: 'This is a test response',
    session_id: 'test-session',
    sources: [],
  },
};