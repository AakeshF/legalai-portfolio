import React, { createContext, useContext } from 'react';

// Mock auth context for when auth is disabled
const MockAuthContext = createContext({
  user: {
    id: 'mock-user-id',
    email: '[DEMO-USER-EMAIL]',
    full_name: 'Demo User',
    role: 'attorney',
    organization_id: 1,
    organization: {
      id: 1,
      name: 'Legal AI Demo'
    }
  },
  organization: {
    id: 'mock-org-id',
    name: 'Legal AI Demo',
    subscription: 'trial' as const,
    usageStats: {
      documentsProcessed: 0,
      apiCalls: 0,
      storageUsed: 0
    }
  },
  loading: false,
  error: null,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  isAuthenticated: true
});

export function MockAuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <MockAuthContext.Provider value={{
      user: {
        id: 'mock-user-id',
        email: '[DEMO-USER-EMAIL]',
        full_name: 'Demo User',
        role: 'attorney',
        organization_id: 1,
        organization: {
          id: 1,
          name: 'Legal AI Demo'
        }
      },
      organization: {
        id: 'mock-org-id',
        name: 'Legal AI Demo',
        subscription: 'trial',
        usageStats: {
          documentsProcessed: 0,
          apiCalls: 0,
          storageUsed: 0
        }
      },
      loading: false,
      error: null,
      login: async () => {},
      register: async () => {},
      logout: async () => {},
      isAuthenticated: true
    }}>
      {children}
    </MockAuthContext.Provider>
  );
}

export const useAuth = () => {
  return useContext(MockAuthContext);
};
