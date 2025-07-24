# Enterprise Implementation Guide
## Priority Features for Legal AI Production Deployment

---

## 1. Authentication & Authorization Implementation

### JWT-Based Authentication Flow
```typescript
// src/services/auth.service.ts
import { api } from '../utils/api';

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'partner' | 'associate' | 'paralegal' | 'client';
  firmId: string;
  permissions: string[];
}

class AuthService {
  private tokens: AuthTokens | null = null;
  private user: User | null = null;

  async login(email: string, password: string): Promise<User> {
    const response = await api.post('/auth/login', { email, password });
    const data = await response.json();
    
    this.tokens = data.tokens;
    this.user = data.user;
    
    // Store tokens securely
    this.storeTokens(data.tokens);
    
    // Set up token refresh
    this.scheduleTokenRefresh();
    
    return data.user;
  }

  async loginWithSSO(provider: 'okta' | 'azure' | 'google'): Promise<void> {
    window.location.href = `/auth/sso/${provider}`;
  }

  private storeTokens(tokens: AuthTokens): void {
    // Use secure storage (not localStorage for production)
    sessionStorage.setItem('access_token', tokens.accessToken);
    // Refresh token should be httpOnly cookie set by backend
  }

  private scheduleTokenRefresh(): void {
    if (!this.tokens) return;
    
    const refreshTime = (this.tokens.expiresIn - 300) * 1000; // 5 min before expiry
    setTimeout(() => this.refreshToken(), refreshTime);
  }

  async refreshToken(): Promise<void> {
    const response = await api.post('/auth/refresh');
    const data = await response.json();
    
    this.tokens = data.tokens;
    this.storeTokens(data.tokens);
    this.scheduleTokenRefresh();
  }

  logout(): void {
    this.tokens = null;
    this.user = null;
    sessionStorage.clear();
    window.location.href = '/login';
  }

  isAuthenticated(): boolean {
    return !!this.tokens?.accessToken;
  }

  hasPermission(permission: string): boolean {
    return this.user?.permissions.includes(permission) || false;
  }

  hasRole(role: string): boolean {
    return this.user?.role === role;
  }
}

export const authService = new AuthService();
```

### Protected Route Component
```typescript
// src/components/auth/ProtectedRoute.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
  requiredRole?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiredPermission,
  requiredRole 
}) => {
  const { isAuthenticated, user, hasPermission, hasRole } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};
```

---

## 2. Multi-Tenant Architecture

### Workspace Context Provider
```typescript
// src/contexts/WorkspaceContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';

interface Workspace {
  id: string;
  name: string;
  firmId: string;
  settings: {
    allowGuestAccess: boolean;
    dataRetentionDays: number;
    defaultPermissions: string[];
  };
}

interface WorkspaceContextType {
  currentWorkspace: Workspace | null;
  workspaces: Workspace[];
  switchWorkspace: (workspaceId: string) => Promise<void>;
  createWorkspace: (name: string) => Promise<Workspace>;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    const response = await api.get('/workspaces');
    const data = await response.json();
    setWorkspaces(data.workspaces);
    
    // Set default workspace
    if (data.workspaces.length > 0) {
      setCurrentWorkspace(data.workspaces[0]);
    }
  };

  const switchWorkspace = async (workspaceId: string) => {
    const workspace = workspaces.find(w => w.id === workspaceId);
    if (workspace) {
      setCurrentWorkspace(workspace);
      // Update API client to include workspace header
      api.setDefaultHeader('X-Workspace-ID', workspaceId);
    }
  };

  return (
    <WorkspaceContext.Provider value={{
      currentWorkspace,
      workspaces,
      switchWorkspace,
      createWorkspace
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return context;
};
```

---

## 3. Advanced Document Management

### Pagination Hook with Infinite Scroll
```typescript
// src/hooks/useInfiniteDocuments.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import { api } from '../utils/api';

interface DocumentsResponse {
  documents: Document[];
  nextCursor: string | null;
  totalCount: number;
}

export const useInfiniteDocuments = (filters: DocumentFilters) => {
  return useInfiniteQuery({
    queryKey: ['documents', filters],
    queryFn: async ({ pageParam = null }) => {
      const params = new URLSearchParams({
        ...filters,
        cursor: pageParam || '',
        limit: '50'
      });
      
      const response = await api.get(`/documents?${params}`);
      return response.json() as Promise<DocumentsResponse>;
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
```

### Batch Operations Manager
```typescript
// src/services/batchOperations.service.ts
import { api } from '../utils/api';

interface BatchOperation {
  id: string;
  type: 'delete' | 'download' | 'process' | 'move' | 'tag';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  totalItems: number;
  completedItems: number;
  errors: string[];
}

class BatchOperationsService {
  private operations = new Map<string, BatchOperation>();
  private eventSource: EventSource | null = null;

  async executeBatch(
    documentIds: string[], 
    operation: BatchOperation['type'],
    options?: any
  ): Promise<string> {
    const response = await api.post('/batch-operations', {
      documentIds,
      operation,
      options
    });
    
    const { operationId } = await response.json();
    
    // Subscribe to SSE for progress updates
    this.subscribeToProgress(operationId);
    
    return operationId;
  }

  private subscribeToProgress(operationId: string): void {
    this.eventSource = new EventSource(`/api/batch-operations/${operationId}/progress`);
    
    this.eventSource.onmessage = (event) => {
      const update = JSON.parse(event.data);
      this.operations.set(operationId, update);
      
      // Emit update to UI
      window.dispatchEvent(new CustomEvent('batch-operation-update', {
        detail: { operationId, update }
      }));
    };
  }

  getOperation(operationId: string): BatchOperation | undefined {
    return this.operations.get(operationId);
  }

  cancelOperation(operationId: string): Promise<void> {
    return api.delete(`/batch-operations/${operationId}`);
  }
}

export const batchOperations = new BatchOperationsService();
```

---

## 4. Enterprise Analytics

### Analytics Dashboard Store
```typescript
// src/store/analytics.store.ts
import { create } from 'zustand';
import { api } from '../utils/api';

interface AnalyticsState {
  metrics: {
    documentsProcessed: number;
    avgProcessingTime: number;
    costSavings: number;
    activeMatters: number;
    riskAlerts: number;
  };
  trends: {
    daily: TimeSeriesData[];
    weekly: TimeSeriesData[];
    monthly: TimeSeriesData[];
  };
  isLoading: boolean;
  dateRange: { start: Date; end: Date };
  
  fetchMetrics: () => Promise<void>;
  setDateRange: (start: Date, end: Date) => void;
  exportReport: (format: 'pdf' | 'excel' | 'csv') => Promise<void>;
}

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  metrics: {
    documentsProcessed: 0,
    avgProcessingTime: 0,
    costSavings: 0,
    activeMatters: 0,
    riskAlerts: 0,
  },
  trends: {
    daily: [],
    weekly: [],
    monthly: [],
  },
  isLoading: false,
  dateRange: {
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date(),
  },

  fetchMetrics: async () => {
    set({ isLoading: true });
    
    try {
      const { dateRange } = get();
      const params = new URLSearchParams({
        startDate: dateRange.start.toISOString(),
        endDate: dateRange.end.toISOString(),
      });

      const [metrics, trends] = await Promise.all([
        api.get(`/analytics/metrics?${params}`).then(r => r.json()),
        api.get(`/analytics/trends?${params}`).then(r => r.json()),
      ]);

      set({ metrics, trends, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  setDateRange: (start, end) => {
    set({ dateRange: { start, end } });
    get().fetchMetrics();
  },

  exportReport: async (format) => {
    const { dateRange } = get();
    const response = await api.post('/analytics/export', {
      format,
      dateRange,
      includeCharts: true,
    });

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `legal-ai-report-${format}`;
    a.click();
    URL.revokeObjectURL(url);
  },
}));
```

---

## 5. Real-time Collaboration

### WebSocket Manager
```typescript
// src/services/websocket.service.ts
import { io, Socket } from 'socket.io-client';

interface WebSocketEvents {
  'document:updated': (data: { documentId: string; changes: any }) => void;
  'document:deleted': (data: { documentId: string }) => void;
  'user:joined': (data: { userId: string; documentId: string }) => void;
  'user:left': (data: { userId: string; documentId: string }) => void;
  'comment:added': (data: { commentId: string; documentId: string }) => void;
}

class WebSocketService {
  private socket: Socket | null = null;
  private listeners = new Map<string, Set<Function>>();

  connect(workspaceId: string, token: string): void {
    this.socket = io(process.env.REACT_APP_WS_URL || 'ws://localhost:3001', {
      auth: { token },
      query: { workspaceId }
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    // Set up event forwarding
    Object.keys(this.getEventMap()).forEach(event => {
      this.socket!.on(event, (data) => {
        this.emit(event, data);
      });
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  on<K extends keyof WebSocketEvents>(
    event: K, 
    callback: WebSocketEvents[K]
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    
    this.listeners.get(event)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners.get(event)?.delete(callback);
    };
  }

  private emit(event: string, data: any): void {
    this.listeners.get(event)?.forEach(callback => callback(data));
  }

  joinDocument(documentId: string): void {
    this.socket?.emit('document:join', { documentId });
  }

  leaveDocument(documentId: string): void {
    this.socket?.emit('document:leave', { documentId });
  }

  private getEventMap(): WebSocketEvents {
    return {} as WebSocketEvents;
  }
}

export const websocketService = new WebSocketService();
```

---

## 6. Audit Logging System

### Audit Logger Service
```typescript
// src/services/audit.service.ts
interface AuditLog {
  id: string;
  timestamp: Date;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  resourceId: string;
  changes?: Record<string, any>;
  ipAddress: string;
  userAgent: string;
  result: 'success' | 'failure';
  errorMessage?: string;
}

class AuditService {
  private queue: Partial<AuditLog>[] = [];
  private flushInterval: number = 5000; // 5 seconds
  private timer: NodeJS.Timeout | null = null;

  constructor() {
    this.startBatchTimer();
  }

  log(entry: Omit<AuditLog, 'id' | 'timestamp' | 'ipAddress' | 'userAgent'>): void {
    this.queue.push({
      ...entry,
      timestamp: new Date(),
    });

    // Flush immediately if queue is large
    if (this.queue.length >= 100) {
      this.flush();
    }
  }

  private startBatchTimer(): void {
    this.timer = setInterval(() => {
      if (this.queue.length > 0) {
        this.flush();
      }
    }, this.flushInterval);
  }

  private async flush(): Promise<void> {
    const entries = [...this.queue];
    this.queue = [];

    try {
      await api.post('/audit-logs/batch', { entries });
    } catch (error) {
      // Re-queue failed entries
      this.queue.unshift(...entries);
      console.error('Failed to flush audit logs:', error);
    }
  }

  async search(filters: {
    userId?: string;
    action?: string;
    startDate?: Date;
    endDate?: Date;
    resource?: string;
  }): Promise<AuditLog[]> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.append(key, value.toString());
    });

    const response = await api.get(`/audit-logs?${params}`);
    return response.json();
  }

  destroy(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.flush(); // Final flush
    }
  }
}

export const auditService = new AuditService();
```

---

## Implementation Priority

### Phase 1: Foundation (Weeks 1-4)
1. **Authentication System**
   - JWT implementation
   - Login/logout flow
   - Token refresh
   - Basic RBAC

2. **Multi-tenant Architecture**
   - Workspace context
   - Data isolation
   - Tenant switching

### Phase 2: Core Enterprise (Weeks 5-8)
1. **Advanced Document Management**
   - Pagination/infinite scroll
   - Batch operations
   - Advanced search
   - Document versioning

2. **User Management**
   - User CRUD
   - Role management
   - Permission matrix
   - Team features

### Phase 3: Analytics & Integration (Weeks 9-12)
1. **Analytics Dashboard**
   - Metrics collection
   - Trend analysis
   - Report generation
   - Export functionality

2. **System Integration**
   - SSO setup
   - API management
   - Webhook system
   - Third-party connectors

### Phase 4: Collaboration & Polish (Weeks 13-16)
1. **Real-time Features**
   - WebSocket implementation
   - Live updates
   - Presence indicators
   - Collaborative editing

2. **Audit & Compliance**
   - Comprehensive logging
   - Audit trail UI
   - Compliance reports
   - Data retention

---

## Testing Strategy

### Unit Testing
```typescript
// Example test for auth service
describe('AuthService', () => {
  it('should store tokens after successful login', async () => {
    const mockTokens = {
      accessToken: 'mock-access-token',
      refreshToken: 'mock-refresh-token',
      expiresIn: 3600
    };

    fetchMock.mockResponseOnce(JSON.stringify({ tokens: mockTokens, user: mockUser }));

    await authService.login('[email@example.com]', 'password');
    
    expect(sessionStorage.getItem('access_token')).toBe(mockTokens.accessToken);
    expect(authService.isAuthenticated()).toBe(true);
  });
});
```

### Integration Testing
- Test multi-tenant data isolation
- Verify permission enforcement
- Test batch operation workflows
- Validate real-time sync

### Load Testing
- Simulate 1000+ concurrent users
- Test with 10,000+ documents
- Measure API response times
- Stress test WebSocket connections

---

## Security Checklist

- [ ] Implement Content Security Policy (CSP)
- [ ] Add request signing for sensitive operations
- [ ] Implement rate limiting
- [ ] Add input validation on all forms
- [ ] Sanitize user-generated content
- [ ] Implement session timeout
- [ ] Add 2FA support
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] OWASP compliance check