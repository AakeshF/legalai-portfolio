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

    const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/auth/refresh`, {
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
    // Always return true since authentication is disabled
    return true;
  }

  // Clear all tokens on startup to avoid issues
  clearAllTokens(): void {
    this.clearTokens();
    localStorage.clear(); // Clear everything to be safe
  }
}

export const tokenService = TokenService.getInstance();
