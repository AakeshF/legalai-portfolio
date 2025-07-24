export interface FormTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  jurisdiction: {
    state: string;
    county?: string;
    court?: string;
  };
  caseTypes: string[];
  isRequired: boolean;
  version: string;
  lastUpdated: Date;
  mcpLastUpdated?: Date;
  hasNewerVersion?: boolean;
  sections: FormSection[];
  metadata?: {
    filingCode?: string;
    statutoryReference?: string;
    estimatedTime?: number; // in minutes
    requiredAttachments?: string[];
  };
}

export interface FormSection {
  id: string;
  title: string;
  description?: string;
  order: number;
  fields: FormField[];
  isRepeatable?: boolean;
}

export interface FormField {
  id: string;
  name: string;
  label: string;
  type: FormFieldType;
  required: boolean;
  helpText?: string;
  placeholder?: string;
  defaultValue?: any;
  validation?: FormValidation;
  options?: SelectOption[]; // for select/radio/checkbox
  condition?: FieldCondition; // for conditional fields
  children?: FormField[]; // for conditional/group fields
  dataSource?: string; // MCP data source for dynamic options
  autoPopulateFrom?: string; // Matter field to auto-populate from
}

export type FormFieldType = 
  | 'text'
  | 'textarea'
  | 'number'
  | 'date'
  | 'time'
  | 'datetime'
  | 'select'
  | 'multiselect'
  | 'radio'
  | 'checkbox'
  | 'file'
  | 'signature'
  | 'conditional'
  | 'repeating'
  | 'group'
  | 'heading'
  | 'paragraph';

export interface FormValidation {
  pattern?: string;
  minLength?: number;
  maxLength?: number;
  min?: number;
  max?: number;
  customValidator?: string; // MCP validator name
  errorMessage?: string;
}

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface FieldCondition {
  field: string;
  operator: 'equals' | 'notEquals' | 'contains' | 'greaterThan' | 'lessThan';
  value: any;
}

export interface FormData {
  [fieldId: string]: any;
}

export interface FormValidationError {
  fieldId: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface GeneratedDocument {
  id: string;
  filename: string;
  format: 'pdf' | 'docx' | 'xml';
  content: Blob;
  efilingReady?: boolean;
  efilingXml?: string;
  metadata: {
    templateId: string;
    templateVersion: string;
    generatedAt: Date;
    generatedBy: string;
  };
}

export interface MatterData {
  id: string;
  clientName: string;
  adverseParty?: string;
  caseNumber?: string;
  jurisdiction: {
    state: string;
    county?: string;
  };
  caseType: string;
  judge?: string;
  department?: string;
  filingDeadline?: Date;
  customFields?: Record<string, any>;
}