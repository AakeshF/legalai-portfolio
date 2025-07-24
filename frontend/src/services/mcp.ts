import { useQuery, useMutation, useQueryClient, UseQueryOptions } from '@tanstack/react-query';
import { api } from '../utils/api';
import { useCallback, useRef } from 'react';

// MCP Server Types
export interface MCPServer {
  id: string;
  name: string;
  status: 'connected' | 'disconnected' | 'error';
  lastPing?: Date;
  capabilities: string[];
}

export interface MCPQuery {
  server: string;
  action: string;
  params?: Record<string, any>;
}

export interface MCPResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: Date;
  server: string;
}

// Conflict Check Types
export interface ConflictCheckResult {
  conflicts: Conflict[];
  checkedAt: Date;
  searchTerm: string;
}

export interface Conflict {
  id: string;
  type: 'client' | 'adverse_party' | 'related_matter';
  name: string;
  matterNumber?: string;
  conflictDetails: string;
  severity: 'high' | 'medium' | 'low';
}

// Court Integration Types
export interface CourtCase {
  caseNumber: string;
  courtName: string;
  judge?: string;
  nextHearing?: Date;
  parties: Party[];
  status: string;
  filingDate?: Date;
}

export interface Party {
  name: string;
  role: 'plaintiff' | 'defendant' | 'petitioner' | 'respondent' | 'other';
  represented?: boolean;
  attorney?: string;
}

// Jurisdiction Form Types
export interface JurisdictionForm {
  id: string;
  name: string;
  required: boolean;
  category: string;
  description?: string;
  fields: FormField[];
}

export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'date' | 'select' | 'checkbox' | 'textarea';
  required: boolean;
  options?: string[];
  validation?: {
    pattern?: string;
    minLength?: number;
    maxLength?: number;
  };
}

// React Query Hooks

// Hook for MCP queries
export function useMCPQuery<T = any>(
  queryKey: string[],
  query: MCPQuery,
  options?: UseQueryOptions<MCPResponse<T>>
) {
  return useQuery({
    queryKey,
    queryFn: async () => {
      const response = await api.post('/api/mcp/query', query);
      return {
        success: true,
        data: response.data,
        timestamp: new Date(),
        server: query.server
      };
    },
    staleTime: 5 * 60 * 1000,
    cacheTime: 10 * 60 * 1000,
    ...options
  });
}

// Hook for conflict checking with debouncing
export function useConflictCheck() {
  const queryClient = useQueryClient();
  const timeoutRef = useRef<NodeJS.Timeout>();

  const checkConflicts = useCallback((searchTerm: string, delay: number = 500) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (searchTerm.length < 3) {
      queryClient.setQueryData(['conflicts', searchTerm], null);
      return;
    }

    timeoutRef.current = setTimeout(() => {
      queryClient.prefetchQuery({
        queryKey: ['conflicts', searchTerm],
        queryFn: async () => {
          const response = await api.post('/api/mcp/query', {
            server: 'client_data',
            action: 'conflict_check',
            params: { searchTerm }
          });
          return response.data;
        }
      });
    }, delay);
  }, [queryClient]);

  return checkConflicts;
}

// Hook for court case lookup
export function useCourtCaseLookup(caseNumber: string) {
  return useMCPQuery<CourtCase>(
    ['court_case', caseNumber],
    {
      server: 'court_data',
      action: 'lookup_case',
      params: { caseNumber }
    },
    {
      enabled: !!caseNumber && caseNumber.length > 5,
      retry: 2
    }
  );
}

// Hook for jurisdiction forms
export function useJurisdictionForms(caseType: string, jurisdiction: string) {
  return useMCPQuery<JurisdictionForm[]>(
    ['jurisdiction_forms', caseType, jurisdiction],
    {
      server: 'document_templates',
      action: 'get_required_forms',
      params: { caseType, jurisdiction }
    },
    {
      enabled: !!caseType && !!jurisdiction,
      staleTime: 30 * 60 * 1000
    }
  );
}

// Hook for MCP server status
export function useMCPServerStatus() {
  return useQuery({
    queryKey: ['mcp_server_status'],
    queryFn: () => api.get('/api/mcp/status'),
    refetchInterval: 30000
  });
}

// Hook for specific MCP server status
export function useMCPServerCheck(serverId: string) {
  return useQuery({
    queryKey: ['mcp_server_status', serverId],
    queryFn: async () => {
      const response = await api.post('/api/mcp/query', {
        server: serverId,
        action: 'ping'
      });
      return {
        server: serverId,
        isOnline: response.data?.success || false,
        lastChecked: new Date(),
        error: response.data?.error
      };
    },
    staleTime: 30000,
    retry: 1
  });
}

// Hook for court holidays
export function useCourtHolidays(year: number, jurisdiction: string) {
  return useMCPQuery(
    ['court_holidays', year, jurisdiction],
    {
      server: 'court_system',
      action: 'get_holidays',
      params: { year, jurisdiction }
    },
    {
      staleTime: 24 * 60 * 60 * 1000,
      enabled: !!year && !!jurisdiction
    }
  );
}

// Hook for deadline calculation
export function useDeadlineCalculation(
  triggerDate: Date | null,
  caseType: string,
  jurisdiction: { state: string; county?: string }
) {
  return useMCPQuery(
    ['deadline_calculation', triggerDate?.toISOString(), caseType, jurisdiction],
    {
      server: 'court_system',
      action: 'calculate_deadlines',
      params: {
        triggerDate: triggerDate?.toISOString(),
        caseType,
        jurisdiction
      }
    },
    {
      enabled: !!triggerDate && !!caseType && !!jurisdiction.state,
      staleTime: 60 * 60 * 1000
    }
  );
}

// Hook for court calendar
export function useCourtCalendar(startDate?: Date, endDate?: Date) {
  return useMCPQuery(
    ['court_calendar', startDate?.toISOString(), endDate?.toISOString()],
    {
      server: 'court_system',
      action: 'get_calendar',
      params: {
        startDate: startDate?.toISOString(),
        endDate: endDate?.toISOString()
      }
    },
    {
      staleTime: 5 * 60 * 1000,
      refetchInterval: 5 * 60 * 1000
    }
  );
}

// Hook for upcoming deadlines
export function useUpcomingDeadlines(days: number = 30) {
  return useMCPQuery(
    ['upcoming_deadlines', days],
    {
      server: 'court_system',
      action: 'upcoming_deadlines',
      params: { days }
    },
    {
      staleTime: 10 * 60 * 1000,
      refetchInterval: 10 * 60 * 1000
    }
  );
}

// Hook for filing status
export function useFilingStatus(matterIds?: string[]) {
  return useMCPQuery(
    ['filing_status', matterIds],
    {
      server: 'court_system',
      action: 'filing_status',
      params: { matterIds }
    },
    {
      enabled: !!matterIds && matterIds.length > 0,
      staleTime: 3 * 60 * 1000
    }
  );
}

// Mutation for saving case intake
export function useSaveCaseIntake() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (intakeData: any) => 
      api.post('/api/cases/intake', intakeData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
    }
  });
}

// Form Template Types
export interface FormTemplate {
  id: string;
  name: string;
  description?: string;
  category: string;
  jurisdiction: string;
  caseType: string;
  version: string;
  lastUpdated: string;
  hasNewerVersion?: boolean;
  isRequired: boolean;
  sections: FormSection[];
  metadata?: Record<string, any>;
}

export interface FormSection {
  id: string;
  title: string;
  description?: string;
  fields: FormField[];
  order: number;
}

export interface FormValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
  warnings?: Record<string, string>;
}

export interface GeneratedDocument {
  documentId: string;
  file: Blob;
  fileName: string;
  format: 'pdf' | 'docx';
  efilingReady: boolean;
  efilingXml?: string;
}

// Hook for fetching form templates
export function useFormTemplates(caseType: string, jurisdiction: string, includeOptional = true) {
  return useMCPQuery<FormTemplate[]>(
    ['form_templates', caseType, jurisdiction, includeOptional],
    {
      server: 'document_templates',
      action: 'get_templates',
      params: { caseType, jurisdiction, includeOptional }
    },
    {
      enabled: !!caseType && !!jurisdiction,
      staleTime: 30 * 60 * 1000
    }
  );
}

// Hook for validating form data with MCP
export function useFormValidation(templateId: string, formData: any, jurisdiction: string) {
  return useMCPQuery<FormValidationResult>(
    ['form_validation', templateId, formData, jurisdiction],
    {
      server: 'document_templates',
      action: 'validate_form',
      params: { templateId, formData, jurisdiction }
    },
    {
      enabled: !!templateId && !!formData,
      staleTime: 0
    }
  );
}

// Mutation for generating documents
export function useGenerateDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (params: {
      templateId: string;
      formData: any;
      format: 'pdf' | 'docx';
      includeEfilingXml: boolean;
    }) => {
      const response = await api.post('/api/mcp/query', {
        server: 'document_templates',
        action: 'generate_document',
        params
      });
      
      if (!response.data) {
        throw new Error('Document generation failed');
      }
      
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });
}

// Hook for checking template updates
export function useCheckTemplateUpdates(templateIds: string[]) {
  return useMCPQuery<Record<string, boolean>>(
    ['template_updates', templateIds],
    {
      server: 'document_templates',
      action: 'check_updates',
      params: { templateIds }
    },
    {
      enabled: templateIds.length > 0,
      staleTime: 60 * 60 * 1000
    }
  );
}

// Hook for getting dynamic field data sources
export function useFieldDataSource(fieldId: string, dataSource: string, params?: any) {
  return useMCPQuery(
    ['field_data_source', fieldId, dataSource, params],
    {
      server: 'document_templates',
      action: 'get_field_data',
      params: { fieldId, dataSource, ...params }
    },
    {
      enabled: !!fieldId && !!dataSource,
      staleTime: 5 * 60 * 1000
    }
  );
}

// Hook for template version comparison
export function useTemplateVersionComparison(templateId: string, version1: string, version2: string) {
  return useMCPQuery(
    ['template_comparison', templateId, version1, version2],
    {
      server: 'document_templates',
      action: 'compare_versions',
      params: { templateId, version1, version2 }
    },
    {
      enabled: !!templateId && !!version1 && !!version2
    }
  );
}

// Mutation for saving form drafts
export function useSaveFormDraft() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (draft: {
      matterId: string;
      templateId: string;
      formData: any;
      metadata?: any;
    }) => api.post('/api/form-drafts', draft),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: ['form_drafts', variables.matterId] 
      });
    }
  });
}

// Hook for loading form drafts
export function useFormDrafts(matterId: string) {
  return useQuery({
    queryKey: ['form_drafts', matterId],
    queryFn: () => api.get(`/api/form-drafts?matterId=${matterId}`),
    enabled: !!matterId
  });
}

// Hook for template categories
export function useTemplateCategories(jurisdiction: string) {
  return useMCPQuery<string[]>(
    ['template_categories', jurisdiction],
    {
      server: 'document_templates',
      action: 'get_categories',
      params: { jurisdiction }
    },
    {
      enabled: !!jurisdiction,
      staleTime: 60 * 60 * 1000
    }
  );
}

// Check multiple MCP servers
export async function checkRequiredMCPServers(serverIds: string[]): Promise<{
  allOnline: boolean;
  online: string[];
  offline: string[];
  statuses: Record<string, boolean>;
}> {
  const statuses: Record<string, boolean> = {};
  const online: string[] = [];
  const offline: string[] = [];

  await Promise.all(
    serverIds.map(async (serverId) => {
      try {
        const response = await api.post('/api/mcp/query', {
          server: serverId,
          action: 'ping'
        });
        const isOnline = response.data?.success || false;
        statuses[serverId] = isOnline;
        if (isOnline) {
          online.push(serverId);
        } else {
          offline.push(serverId);
        }
      } catch {
        statuses[serverId] = false;
        offline.push(serverId);
      }
    })
  );

  return {
    allOnline: offline.length === 0,
    online,
    offline,
    statuses
  };
}

// MCP Event Subscription
export interface MCPEventHandlers {
  onCourtUpdate?: (update: any) => void;
  onDeadlineApproaching?: (deadline: any) => void;
  onConflictDetected?: (conflict: any) => void;
  onServerStatusChange?: (server: string, status: boolean) => void;
}

export function subscribeMCPEvents(handlers: MCPEventHandlers) {
  // Simplified version that delegates to backend event system
  const intervals: NodeJS.Timeout[] = [];
  
  // Poll for updates every 30 seconds via backend
  if (handlers.onCourtUpdate) {
    const interval = setInterval(async () => {
      try {
        const response = await api.post('/api/mcp/query', {
          server: 'court_system',
          action: 'check_updates'
        });
        if (response.data?.hasUpdates) {
          handlers.onCourtUpdate!(response.data.updates);
        }
      } catch (error) {
        console.error('Failed to check for court updates:', error);
      }
    }, 30000);
    intervals.push(interval);
  }
  
  return {
    unsubscribe: () => {
      intervals.forEach(clearInterval);
    }
  };
}