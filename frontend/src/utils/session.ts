/**
 * Session management utilities for AI conversation continuity
 * Implements backend team's best practices
 */

import { IntegratedAnonymizationAPI } from '../services/integrated-anonymization-api';

const SESSION_STORAGE_KEY = 'ai_session_id';
const SESSION_EXPIRY_KEY = 'ai_session_expiry';
const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

export class SessionManager {
  /**
   * Get or create a session ID
   */
  static async getSessionId(): Promise<string> {
    // Check for existing valid session
    const existingSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
    const sessionExpiry = localStorage.getItem(SESSION_EXPIRY_KEY);
    
    if (existingSessionId && sessionExpiry) {
      const expiryTime = parseInt(sessionExpiry, 10);
      if (Date.now() < expiryTime) {
        return existingSessionId;
      }
    }
    
    // Create new session
    try {
      const { session_id } = await IntegratedAnonymizationAPI.createSession();
      this.saveSession(session_id);
      return session_id;
    } catch (error) {
      console.error('Failed to create session:', error);
      // Generate a temporary client-side session ID as fallback
      const tempSessionId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      this.saveSession(tempSessionId);
      return tempSessionId;
    }
  }
  
  /**
   * Save session to localStorage with expiry
   */
  private static saveSession(sessionId: string): void {
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    localStorage.setItem(SESSION_EXPIRY_KEY, (Date.now() + SESSION_DURATION).toString());
  }
  
  /**
   * Clear current session
   */
  static clearSession(): void {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    localStorage.removeItem(SESSION_EXPIRY_KEY);
  }
  
  /**
   * Check if session is valid
   */
  static isSessionValid(): boolean {
    const sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
    const sessionExpiry = localStorage.getItem(SESSION_EXPIRY_KEY);
    
    if (!sessionId || !sessionExpiry) {
      return false;
    }
    
    const expiryTime = parseInt(sessionExpiry, 10);
    return Date.now() < expiryTime;
  }
}