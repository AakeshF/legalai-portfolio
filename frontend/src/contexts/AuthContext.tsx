import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/api/client';
import { tokenService } from '../services/auth/token.service';
import { useNavigate } from 'react-router-dom';

export type UserRole = 'attorney' | 'admin' | 'paralegal';

export interface User {
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

export interface Organization {
  id: string;
  name: string;
  subscription: 'trial' | 'professional' | 'enterprise';
  usageStats: {
    documentsProcessed: number;
    apiCalls: number;
    storageUsed: number;
  };
}

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string, organization_name: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
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

  const register = async (email: string, password: string, full_name: string, organization_name: string) => {
    try {
      setError(null);
      const response = await apiClient.post<{
        access_token: string;
        refresh_token: string;
        user: User;
      }>('/api/auth/register', { 
        email, 
        password, 
        full_name,
        organization_name 
      }, { skipAuth: true });

      tokenService.setTokens(response.access_token, response.refresh_token);
      setUser(response.user);
      navigate('/dashboard');
    } catch (error: any) {
      setError(error.message || 'Registration failed');
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
        organization,
        loading,
        error,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};