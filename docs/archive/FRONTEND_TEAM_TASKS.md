# Frontend Team - Detailed Task Instructions

**Document Type:** Frontend Implementation Guide  
**Team:** Frontend Engineering  
**Timeline:** 16 Weeks  
**Priority Labels:** 🔴 CRITICAL | 🟡 HIGH | 🟢 MEDIUM | 🔵 LOW

---

## Team Roles & Responsibilities

- **FE-01**: Senior Frontend Engineer (Architecture & Auth)
- **FE-02**: Frontend Engineer (UI/UX & Components)
- **FE-03**: Frontend Engineer (State & Performance)
- **FE-04**: Frontend Engineer (Testing & Quality)
- **FE-05**: UI/UX Designer

---

## Week 1-2: Critical Auth Integration 🔴

### TASK-FE-001: Token Management Implementation 🔴
**Owner:** FE-01  
**Duration:** 8 hours  
**Dependencies:** Backend auth endpoints working  
**Labels:** `auth`, `critical`, `blocking`

#### Step 1: Create Auth Token Service
```typescript
// frontend/src/services/auth/token.service.ts
import { jwtDecode } from 'jwt-decode';

interface TokenPayload {
  sub: string;
  email: string;
  org: number;
  role: string;
  exp: number;
  iat: number;
}

class TokenService {
  private static instance: TokenService;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshPromise: Promise<string> | null = null;

  static getInstance(): TokenService {
    if (!TokenService.instance) {
      TokenService.instance = new TokenService();
    }
    return TokenService.instance;
  }

  constructor() {
    // Load tokens from storage on init
    this.loadTokens();
  }

  private loadTokens(): void {
    this.refreshToken = localStorage.getItem('refreshToken');
    // Don't store access token in localStorage for security
  }

  setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    
    // Only store refresh token
    localStorage.setItem('refreshToken', refreshToken);
  }

  getAccessToken(): string | null {
    if (!this.accessToken) return null;

    try {
      const payload = jwtDecode<TokenPayload>(this.accessToken);
      const now = Date.now() / 1000;
      
      // Check if token is expired or about to expire (5 min buffer)
      if (payload.exp < now + 300) {
        return null;
      }
      
      return this.accessToken;
    } catch {
      return null;
    }
  }

  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  async refreshAccessToken(): Promise<string> {
    // Prevent multiple simultaneous refresh attempts
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this._performRefresh();
    
    try {
      const newToken = await this.refreshPromise;
      return newToken;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async _performRefresh(): Promise<string> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      this.clearTokens();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    this.setTokens(data.access_token, data.refresh_token);
    
    return data.access_token;
  }

  clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('refreshToken');
  }

  getUserInfo(): TokenPayload | null {
    const token = this.getAccessToken();
    if (!token) return null;
    
    try {
      return jwtDecode<TokenPayload>(token);
    } catch {
      return null;
    }
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken() || !!this.getRefreshToken();
  }
}

export const tokenService = TokenService.getInstance();
```

#### Step 2: Create API Client with Interceptors
```typescript
// frontend/src/services/api/client.ts
import { tokenService } from '../auth/token.service';

interface RequestConfig extends RequestInit {
  skipAuth?: boolean;
  retry?: boolean;
}

class APIClient {
  private baseURL: string;
  private requestQueue: Map<string, Promise<Response>> = new Map();

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  private async request(url: string, config: RequestConfig = {}): Promise<Response> {
    const { skipAuth, retry = true, ...fetchConfig } = config;

    // Add auth header if needed
    if (!skipAuth) {
      const token = tokenService.getAccessToken();
      
      if (!token && tokenService.getRefreshToken()) {
        try {
          await tokenService.refreshAccessToken();
        } catch (error) {
          window.location.href = '/login';
          throw error;
        }
      }

      const currentToken = tokenService.getAccessToken();
      if (currentToken) {
        fetchConfig.headers = {
          ...fetchConfig.headers,
          'Authorization': `Bearer ${currentToken}`,
        };
      }
    }

    // Make request
    const response = await fetch(`${this.baseURL}${url}`, fetchConfig);

    // Handle 401 - try refresh once
    if (response.status === 401 && retry && !skipAuth) {
      try {
        await tokenService.refreshAccessToken();
        return this.request(url, { ...config, retry: false });
      } catch {
        window.location.href = '/login';
        throw new Error('Authentication failed');
      }
    }

    return response;
  }

  async get<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.request(url, { ...config, method: 'GET' });
    if (!response.ok) throw new Error(`GET ${url} failed: ${response.statusText}`);
    return response.json();
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
    if (!response.ok) throw new Error(`POST ${url} failed: ${response.statusText}`);
    return response.json();
  }

  async upload<T>(url: string, formData: FormData, config?: RequestConfig): Promise<T> {
    const response = await this.request(url, {
      ...config,
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error(`Upload to ${url} failed: ${response.statusText}`);
    return response.json();
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
    if (!response.ok) throw new Error(`PUT ${url} failed: ${response.statusText}`);
    return response.json();
  }

  async delete(url: string, config?: RequestConfig): Promise<void> {
    const response = await this.request(url, { ...config, method: 'DELETE' });
    if (!response.ok) throw new Error(`DELETE ${url} failed: ${response.statusText}`);
  }
}

export const apiClient = new APIClient();
```

#### Step 3: Update Auth Context
```typescript
// frontend/src/contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/api/client';
import { tokenService } from '../services/auth/token.service';
import { useNavigate } from 'react-router-dom';

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  organization_id: number;
  organization?: {
    id: number;
    name: string;
  };
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchUser = useCallback(async () => {
    try {
      const userData = await apiClient.get<User>('/api/auth/me');
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      if (tokenService.isAuthenticated()) {
        await fetchUser();
      }
      setLoading(false);
    };

    initAuth();
  }, [fetchUser]);

  const login = async (email: string, password: string) => {
    try {
      setError(null);
      const response = await apiClient.post<{
        access_token: string;
        refresh_token: string;
        user: User;
      }>('/api/auth/login', { email, password }, { skipAuth: true });

      tokenService.setTokens(response.access_token, response.refresh_token);
      setUser(response.user);
      navigate('/dashboard');
    } catch (error) {
      setError('Invalid email or password');
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiClient.post('/api/auth/logout', {});
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      tokenService.clearTokens();
      setUser(null);
      navigate('/login');
    }
  };

  return (
    <AuthContext.Provider 
      value={{
        user,
        loading,
        error,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

#### Verification Checklist:
- [ ] Token service properly stores/retrieves tokens
- [ ] API client adds auth headers automatically
- [ ] 401 responses trigger token refresh
- [ ] Failed refresh redirects to login
- [ ] User context updates on login/logout

---

### TASK-FE-002: Protected Routes Implementation 🔴
**Owner:** FE-01  
**Duration:** 4 hours  
**Dependencies:** TASK-FE-001  
**Labels:** `auth`, `routing`, `critical`

#### Step 1: Create Route Protection
```typescript
// frontend/src/components/auth/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LoadingSpinner } from '../ui/LoadingSpinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string[];
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  requiredRole, 
  redirectTo = '/login' 
}: ProtectedRouteProps) {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  if (requiredRole && user && !requiredRole.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
}
```

#### Step 2: Update App Router
```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { AdminPage } from './pages/AdminPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <Navigate to="/dashboard" replace />
            </ProtectedRoute>
          } />
          
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } />
          
          <Route path="/documents" element={
            <ProtectedRoute>
              <DocumentsPage />
            </ProtectedRoute>
          } />
          
          {/* Admin only routes */}
          <Route path="/admin/*" element={
            <ProtectedRoute requiredRole={['admin']}>
              <AdminPage />
            </ProtectedRoute>
          } />
          
          {/* Error pages */}
          <Route path="/unauthorized" element={<UnauthorizedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

---

### TASK-FE-003: Update All API Calls 🔴
**Owner:** FE-02  
**Duration:** 8 hours  
**Dependencies:** TASK-FE-001  
**Labels:** `api`, `refactor`, `critical`

#### Step 1: Update Document Services
```typescript
// frontend/src/services/document.service.ts
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
    
    return apiClient.get(`/api/documents?${queryParams}`);
  },

  async getDocument(id: number): Promise<Document> {
    return apiClient.get(`/api/documents/${id}`);
  },

  async uploadDocument(file: File, documentType: string): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    
    return apiClient.upload('/api/documents/upload', formData);
  },

  async deleteDocument(id: number): Promise<void> {
    return apiClient.delete(`/api/documents/${id}`);
  },

  async reprocessDocument(id: number): Promise<Document> {
    return apiClient.post(`/api/documents/${id}/reprocess`);
  },

  async searchDocuments(query: string): Promise<Document[]> {
    return apiClient.get(`/api/documents/search?q=${encodeURIComponent(query)}`);
  },
};
```

#### Step 2: Update React Query Hooks
```typescript
// frontend/src/hooks/useDocuments.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services/document.service';
import { toast } from '../components/ui/Toast';

export function useDocuments(params?: {
  page?: number;
  limit?: number;
  document_type?: string;
}) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => documentService.getDocuments(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useDocument(id: number) {
  return useQuery({
    queryKey: ['document', id],
    queryFn: () => documentService.getDocument(id),
    enabled: !!id,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, documentType }: { file: File; documentType: string }) =>
      documentService.uploadDocument(file, documentType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document uploaded successfully');
    },
    onError: (error) => {
      toast.error('Failed to upload document');
      console.error('Upload error:', error);
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: documentService.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete document');
    },
  });
}
```

---

## Week 3-4: Testing & Quality 🟡

### TASK-FE-004: Component Testing Suite 🟡
**Owner:** FE-04  
**Duration:** 16 hours  
**Dependencies:** TASK-FE-003  
**Labels:** `testing`, `quality`

#### Step 1: Setup Testing Environment
```bash
# Install testing dependencies
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event
npm install -D vitest @vitest/ui jsdom
npm install -D msw @mswjs/data
```

#### Step 2: Create Test Utilities
```typescript
// frontend/src/tests/utils.tsx
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

export function renderWithProviders(
  ui: React.ReactElement,
  {
    route = '/',
    user = null,
    ...options
  } = {}
) {
  window.history.pushState({}, 'Test page', route);

  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            {children}
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options }),
    queryClient,
  };
}
```

#### Step 3: Test Auth Components
```typescript
// frontend/src/components/auth/__tests__/LoginForm.test.tsx
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '../LoginForm';
import { renderWithProviders } from '../../../tests/utils';
import { server } from '../../../tests/server';
import { rest } from 'msw';

describe('LoginForm', () => {
  it('renders login form', () => {
    renderWithProviders(<LoginForm />);
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows validation errors', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);
    
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);
    
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
  });

  it('handles successful login', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);
    
    await user.type(screen.getByLabelText(/email/i), '[email@example.com]');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    
    await waitFor(() => {
      expect(window.location.pathname).toBe('/dashboard');
    });
  });

  it('handles login error', async () => {
    server.use(
      rest.post('/api/auth/login', (req, res, ctx) => {
        return res(ctx.status(401), ctx.json({ detail: 'Invalid credentials' }));
      })
    );

    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);
    
    await user.type(screen.getByLabelText(/email/i), '[email@example.com]');
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    
    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument();
  });
});
```

---

## Week 5-6: Performance Optimization 🟡

### TASK-FE-005: Code Splitting & Lazy Loading 🟡
**Owner:** FE-03  
**Duration:** 12 hours  
**Dependencies:** TASK-FE-004  
**Labels:** `performance`, `optimization`

#### Step 1: Implement Route-Based Code Splitting
```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react';
import { LoadingPage } from './components/LoadingPage';

// Lazy load pages
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));

function App() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <Routes>
        {/* Routes with lazy loaded components */}
      </Routes>
    </Suspense>
  );
}
```

#### Step 2: Optimize Bundle Size
```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({ open: true, gzipSize: true }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@headlessui/react', 'lucide-react'],
          utils: ['date-fns', 'clsx', 'tailwind-merge'],
        },
      },
    },
  },
});
```

#### Step 3: Implement Virtual Scrolling
```typescript
// frontend/src/components/VirtualDocumentList.tsx
import { VariableSizeList as List } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import { Document } from '../types';

interface VirtualDocumentListProps {
  documents: Document[];
  onDocumentClick: (doc: Document) => void;
}

export function VirtualDocumentList({ documents, onDocumentClick }: VirtualDocumentListProps) {
  const getItemSize = (index: number) => {
    // Variable height based on content
    const doc = documents[index];
    return doc.summary ? 120 : 80;
  };

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const document = documents[index];
    
    return (
      <div style={style} className="p-4 border-b hover:bg-gray-50">
        <DocumentCard
          document={document}
          onClick={() => onDocumentClick(document)}
        />
      </div>
    );
  };

  return (
    <AutoSizer>
      {({ height, width }) => (
        <List
          height={height}
          width={width}
          itemCount={documents.length}
          itemSize={getItemSize}
          overscanCount={5}
        >
          {Row}
        </List>
      )}
    </AutoSizer>
  );
}
```

---

## Week 7-10: Enterprise Features 🟢

### TASK-FE-006: Real-time WebSocket Integration 🟢
**Owner:** FE-02  
**Duration:** 12 hours  
**Dependencies:** Backend WebSocket  
**Labels:** `feature`, `realtime`

#### Step 1: WebSocket Service
```typescript
// frontend/src/services/websocket.service.ts
import { tokenService } from './auth/token.service';

type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(): void {
    const token = tokenService.getAccessToken();
    if (!token) return;

    const wsUrl = `${import.meta.env.VITE_WS_URL}/ws?token=${token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected', {});
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected', {});
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    this.reconnectTimeout = setTimeout(() => {
      console.log(`Attempting reconnection ${this.reconnectAttempts}`);
      this.connect();
    }, delay);
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(type: string, data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }

  on(event: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(event)) {
      this.messageHandlers.set(event, new Set());
    }
    
    this.messageHandlers.get(event)!.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.messageHandlers.get(event)?.delete(handler);
    };
  }

  private handleMessage(message: any): void {
    this.emit(message.type, message.data);
  }

  private emit(event: string, data: any): void {
    const handlers = this.messageHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }
}

export const websocketService = new WebSocketService();
```

#### Step 2: Real-time Hooks
```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useCallback } from 'react';
import { websocketService } from '../services/websocket.service';
import { useQueryClient } from '@tanstack/react-query';

export function useWebSocket() {
  const queryClient = useQueryClient();

  useEffect(() => {
    websocketService.connect();

    return () => {
      websocketService.disconnect();
    };
  }, []);

  useEffect(() => {
    const unsubscribers = [
      // Document updates
      websocketService.on('document_update', (data) => {
        queryClient.invalidateQueries({ queryKey: ['documents'] });
        queryClient.invalidateQueries({ queryKey: ['document', data.document_id] });
      }),

      // Chat messages
      websocketService.on('chat_message', (data) => {
        queryClient.setQueryData(['chat', data.session_id], (old: any) => ({
          ...old,
          messages: [...(old?.messages || []), data.message],
        }));
      }),

      // User presence
      websocketService.on('user_presence', (data) => {
        queryClient.setQueryData(['presence'], (old: any) => ({
          ...old,
          [data.user_id]: data.status,
        }));
      }),
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [queryClient]);

  const sendMessage = useCallback((type: string, data: any) => {
    websocketService.send(type, data);
  }, []);

  return { sendMessage };
}
```

---

### TASK-FE-007: Advanced Search UI 🟢
**Owner:** FE-03  
**Duration:** 16 hours  
**Dependencies:** Backend Elasticsearch  
**Labels:** `feature`, `search`

#### Step 1: Search Components
```typescript
// frontend/src/components/search/AdvancedSearch.tsx
import { useState, useCallback } from 'react';
import { useDebounce } from '../../hooks/useDebounce';
import { Search, Filter, Calendar, Tag } from 'lucide-react';

export function AdvancedSearch() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    documentType: [],
    dateRange: { from: null, to: null },
    parties: [],
    tags: [],
  });
  
  const debouncedQuery = useDebounce(query, 300);
  
  const { data, isLoading } = useSearchDocuments({
    query: debouncedQuery,
    ...filters,
  });

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents..."
          className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <DocumentTypeFilter
          selected={filters.documentType}
          onChange={(types) => setFilters({ ...filters, documentType: types })}
        />
        
        <DateRangeFilter
          value={filters.dateRange}
          onChange={(range) => setFilters({ ...filters, dateRange: range })}
        />
        
        <TagFilter
          selected={filters.tags}
          onChange={(tags) => setFilters({ ...filters, tags })}
        />
      </div>

      {/* Results */}
      <SearchResults
        results={data?.results || []}
        total={data?.total || 0}
        isLoading={isLoading}
        aggregations={data?.aggregations}
      />
    </div>
  );
}
```

---

## Week 11-16: Production Readiness 🔵

### TASK-FE-008: PWA Implementation 🔵
**Owner:** FE-01  
**Duration:** 8 hours  
**Dependencies:** None  
**Labels:** `feature`, `pwa`

#### Step 1: Service Worker Setup
```typescript
// frontend/src/service-worker.ts
/// <reference lib="webworker" />
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate, NetworkFirst } from 'workbox-strategies';

declare const self: ServiceWorkerGlobalScope;

// Precache all static assets
precacheAndRoute(self.__WB_MANIFEST);

// API caching strategy
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/documents'),
  new StaleWhileRevalidate({
    cacheName: 'api-cache',
    plugins: [
      {
        cacheWillUpdate: async ({ response }) => {
          if (response && response.headers) {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
              return response;
            }
          }
          return null;
        },
      },
    ],
  })
);

// Offline fallback
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match('/offline.html') as Promise<Response>;
      })
    );
  }
});
```

---

## Summary & Verification

### Frontend Team Deliverables Checklist

#### Week 1-2 ✓
- [ ] Token management implemented
- [ ] API client with auth interceptors
- [ ] Protected routes working
- [ ] All API calls updated

#### Week 3-4 ✓
- [ ] Component tests >80% coverage
- [ ] E2E tests implemented
- [ ] Performance benchmarks

#### Week 5-6 ✓
- [ ] Code splitting implemented
- [ ] Virtual scrolling for lists
- [ ] Bundle size optimized

#### Week 7-10 ✓
- [ ] WebSocket real-time updates
- [ ] Advanced search UI
- [ ] Enterprise features

#### Week 11-16 ✓
- [ ] PWA functionality
- [ ] Offline support
- [ ] Production deployment

### Critical Success Metrics
- Lighthouse score: >90
- Bundle size: <500KB initial
- Test coverage: >80%
- Load time: <2s
- Auth flow: Seamless