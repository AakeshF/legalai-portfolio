import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/MockAuthContext';
import { AnonymizationAPI, AnonymizationWebSocket } from '../services/anonymization-api';
import {
  PromptSubmission,
  AnonymizationSettings,
  RedactedSegment
} from '../types/anonymization';

interface UseAnonymizationOptions {
  enableWebSocket?: boolean;
  pollingInterval?: number;
}

export function useAnonymization(options: UseAnonymizationOptions = {}) {
  const { user } = useAuth();
  const [settings, setSettings] = useState<AnonymizationSettings | null>(null);
  const [submissions, setSubmissions] = useState<PromptSubmission[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ws, setWs] = useState<AnonymizationWebSocket | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    if (options.enableWebSocket && user?.organizationId) {
      const websocket = new AnonymizationWebSocket();
      websocket.connect(user.organizationId);
      
      // Listen for real-time updates
      websocket.on('prompt.statusChanged', (data) => {
        setSubmissions(prev => 
          prev.map(s => s.id === data.promptId ? { ...s, status: data.status } : s)
        );
      });

      websocket.on('prompt.new', (data) => {
        setSubmissions(prev => [data, ...prev]);
      });

      setWs(websocket);

      return () => {
        websocket.disconnect();
      };
    }
  }, [user?.organizationId, options.enableWebSocket]);

  // Load user settings
  const loadSettings = useCallback(async () => {
    if (!user?.id) return;
    
    try {
      setLoading(true);
      const data = await AnonymizationAPI.getAnonymizationSettings(user.id);
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  // Update settings
  const updateSettings = useCallback(async (newSettings: AnonymizationSettings) => {
    if (!user?.id) return;
    
    try {
      setLoading(true);
      const updated = await AnonymizationAPI.updateAnonymizationSettings(user.id, newSettings);
      setSettings(updated);
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update settings');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  // Submit prompt
  const submitPrompt = useCallback(async (
    original: string,
    redacted: string,
    segments: RedactedSegment[],
    model: string,
    consent?: any
  ) => {
    if (!settings) throw new Error('Settings not loaded');
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await AnonymizationAPI.submitPrompt({
        originalContent: original,
        redactedContent: redacted,
        segments,
        model,
        autoRedactionEnabled: settings.autoRedactionEnabled,
        consent
      });
      
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit prompt');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [settings]);

  // Load submissions
  const loadSubmissions = useCallback(async (params?: {
    limit?: number;
    offset?: number;
    status?: PromptSubmission['status'];
  }) => {
    if (!user?.id) return;
    
    try {
      setLoading(true);
      const data = await AnonymizationAPI.getUserSubmissions(user.id, params);
      setSubmissions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load submissions');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  // Check prompt status
  const checkPromptStatus = useCallback(async (promptId: string) => {
    try {
      const status = await AnonymizationAPI.getPromptStatus(promptId);
      
      // Update local state
      setSubmissions(prev =>
        prev.map(s => s.id === promptId ? { ...s, ...status } : s)
      );
      
      return status;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check status');
      throw err;
    }
  }, []);

  // Process approved prompt
  const processPrompt = useCallback(async (promptId: string) => {
    try {
      setLoading(true);
      const result = await AnonymizationAPI.processPrompt(promptId);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process prompt');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Load initial data
  useEffect(() => {
    loadSettings();
    loadSubmissions();
  }, [loadSettings, loadSubmissions]);

  return {
    settings,
    updateSettings,
    submissions,
    loadSubmissions,
    submitPrompt,
    checkPromptStatus,
    processPrompt,
    loading,
    error,
    ws
  };
}

// Admin-specific hook
export function useAnonymizationAdmin() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [submissions, setSubmissions] = useState<PromptSubmission[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAdminData = useCallback(async (params: any) => {
    if (!user?.organizationId) return;
    
    try {
      setLoading(true);
      const [submissionsData, statsData] = await Promise.all([
        AnonymizationAPI.getAdminSubmissions({ ...params, organizationId: user.organizationId }),
        AnonymizationAPI.getAdminStats(user.organizationId)
      ]);
      
      setSubmissions(submissionsData);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  }, [user?.organizationId]);

  const approvePrompt = useCallback(async (promptId: string, editedContent?: string) => {
    try {
      await AnonymizationAPI.approvePrompt(promptId, editedContent);
      // Refresh data
      loadAdminData({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve prompt');
      throw err;
    }
  }, [loadAdminData]);

  const rejectPrompt = useCallback(async (promptId: string, reason: string) => {
    try {
      await AnonymizationAPI.rejectPrompt(promptId, reason);
      // Refresh data
      loadAdminData({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject prompt');
      throw err;
    }
  }, [loadAdminData]);

  const batchAction = useCallback(async (ids: string[], action: 'approve' | 'reject') => {
    try {
      await AnonymizationAPI.batchAction({ ids, action });
      // Refresh data
      loadAdminData({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to perform batch action');
      throw err;
    }
  }, [loadAdminData]);

  return {
    stats,
    submissions,
    loadAdminData,
    approvePrompt,
    rejectPrompt,
    batchAction,
    loading,
    error
  };
}
