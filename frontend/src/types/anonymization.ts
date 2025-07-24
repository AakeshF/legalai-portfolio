export interface SensitiveDataPattern {
  id: string;
  type: 'personal' | 'financial' | 'medical' | 'legal' | 'custom';
  pattern: RegExp | string;
  replacement: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
}

export interface RedactedSegment {
  start: number;
  end: number;
  type: string;
  original: string;
  redacted: string;
  isManuallyToggled?: boolean;
}

export interface AnonymizationResult {
  original: string;
  redacted: string;
  segments: RedactedSegment[];
  detectedSensitiveTypes: string[];
  confidenceScore: number;
}

export interface PromptReviewStatus {
  id: string;
  promptId: string;
  status: 'pending' | 'approved' | 'rejected' | 'edited';
  reviewedBy?: string;
  reviewedAt?: string;
  comments?: string;
  editedContent?: string;
}

export interface PromptSubmission {
  id: string;
  userId: string;
  organizationId: string;
  originalContent: string;
  redactedContent: string;
  segments: RedactedSegment[];
  model: string;
  status: 'draft' | 'pending_review' | 'approved' | 'rejected';
  createdAt: string;
  updatedAt: string;
  reviewStatus?: PromptReviewStatus;
  autoRedactionEnabled: boolean;
}

export interface AnonymizationSettings {
  autoRedactionEnabled: boolean;
  sensitivityThreshold: 'low' | 'medium' | 'high';
  customPatterns: SensitiveDataPattern[];
  enabledCategories: string[];
  requireApprovalForSensitive: boolean;
}