export interface Deadline {
  id: string;
  title: string;
  description?: string;
  date: Date;
  daysFromTrigger: number;
  type: DeadlineType;
  severity: 'critical' | 'high' | 'medium' | 'low';
  jurisdiction: {
    state: string;
    county?: string;
    court?: string;
  };
  citation?: string; // Legal rule reference
  mcpSource?: boolean; // Whether this came from MCP
  isBusinessDays: boolean;
  includesHolidays: boolean;
  notificationDays?: number[]; // Days before deadline to notify
}

export type DeadlineType = 
  | 'statute_of_limitations'
  | 'discovery'
  | 'motion'
  | 'response'
  | 'appeal'
  | 'service'
  | 'filing'
  | 'notice'
  | 'hearing'
  | 'other';

export interface CaseType {
  id: string;
  name: string;
  category: 'civil' | 'criminal' | 'family' | 'bankruptcy' | 'administrative';
  deadlineProfiles: DeadlineProfile[];
}

export interface DeadlineProfile {
  id: string;
  name: string;
  description: string;
  deadlines: DeadlineTemplate[];
}

export interface DeadlineTemplate {
  title: string;
  daysFromTrigger: number;
  type: DeadlineType;
  isBusinessDays: boolean;
  severity: 'critical' | 'high' | 'medium' | 'low';
  citation?: string;
}

export interface CourtHoliday {
  date: Date;
  name: string;
  court: string;
  isObserved: boolean;
}

export interface MCPServerStatus {
  server: string;
  isOnline: boolean;
  lastChecked: Date;
  responseTime?: number;
  capabilities?: string[];
  error?: string;
}

export interface DeadlineCalculationRequest {
  triggerDate: Date;
  caseType: string;
  jurisdiction: {
    state: string;
    county?: string;
    court?: string;
  };
  includeWeekends?: boolean;
  includeHolidays?: boolean;
}