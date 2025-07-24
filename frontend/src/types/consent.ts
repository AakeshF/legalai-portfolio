export enum ConsentScope {
  ORGANIZATION = 'organization',
  USER = 'user',
  DOCUMENT = 'document',
  SESSION = 'session'
}

export enum ConsentType {
  CLOUD_AI = 'cloud_ai',
  LOCAL_AI = 'local_ai',
  THIRD_PARTY_SHARING = 'third_party_sharing'
}

export interface ConsentRequirement {
  scope: ConsentScope;
  scopeId?: string; // documentId, sessionId, etc.
  types: ConsentType[];
  reason?: string;
}

export interface ConsentCheck {
  hasConsent: boolean;
  scope: ConsentScope;
  types: ConsentType[];
  grantedAt?: string;
  expiresAt?: string;
}

export interface ConsentPolicy {
  organizationId: string;
  requireExplicitConsent: boolean;
  defaultConsents: {
    [key in ConsentType]?: boolean;
  };
  sensitivityThresholds: {
    requireDocumentConsent: 'confidential' | 'highly-sensitive';
    requireSessionConsent: 'highly-sensitive' | 'never';
  };
}