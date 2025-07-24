export interface CourtAppearance {
  id: string;
  time: string;
  date: Date;
  courtroom: string;
  caseName: string;
  caseNumber: string;
  judge: string;
  type: 'hearing' | 'trial' | 'conference' | 'motion';
  notes?: string;
  isVirtual?: boolean;
  virtualLink?: string;
  matterId?: string;
}

export interface DeadlineAlert {
  id: string;
  title: string;
  description?: string;
  date: Date;
  daysRemaining: number;
  severity: 'urgent' | 'high' | 'medium' | 'low';
  type: string;
  matterId: string;
  matterName: string;
  isFromMCP?: boolean;
}

export interface FollowUpReminder {
  id: string;
  clientName: string;
  type: 'call' | 'email' | 'meeting' | 'document';
  description: string;
  dueDate: Date;
  priority: 'high' | 'medium' | 'low';
  matterId?: string;
}

export interface FilingStatus {
  id: string;
  documentName: string;
  status: 'pending' | 'filed' | 'accepted' | 'rejected' | 'processing';
  filedDate?: Date;
  confirmationNumber?: string;
  court: string;
  nextStep?: string;
  matterId: string;
}

export interface RecentMatter {
  id: string;
  name: string;
  clientName: string;
  type: string;
  status: 'active' | 'pending' | 'closed';
  lastActivity: Date;
  nextDeadline?: Date;
  assignedAttorney: string;
  caseNumber?: string;
}

export interface DashboardMetrics {
  activeMatters: number;
  upcomingDeadlines: number;
  todayAppearances: number;
  pendingFilings: number;
  overdueTasks: number;
}