import { FormTemplate, FormField, FormData, FormValidationError, FieldCondition, MatterData } from './types';

// Evaluate field conditions
export function evaluateCondition(condition: FieldCondition | undefined, formData: FormData): boolean {
  if (!condition) return true;
  
  const fieldValue = formData[condition.field];
  
  switch (condition.operator) {
    case 'equals':
      return fieldValue === condition.value;
    case 'notEquals':
      return fieldValue !== condition.value;
    case 'contains':
      return String(fieldValue).includes(String(condition.value));
    case 'greaterThan':
      return Number(fieldValue) > Number(condition.value);
    case 'lessThan':
      return Number(fieldValue) < Number(condition.value);
    default:
      return true;
  }
}

// Auto-populate form from matter data
export function populateFromMatter(fields: FormField[], matterData: MatterData): FormData {
  const formData: FormData = {};
  
  fields.forEach(field => {
    if (field.autoPopulateFrom) {
      const value = getNestedValue(matterData, field.autoPopulateFrom);
      if (value !== undefined) {
        formData[field.id] = value;
      }
    } else if (field.defaultValue !== undefined) {
      formData[field.id] = field.defaultValue;
    }
    
    // Recursively populate nested fields
    if (field.children) {
      const childData = populateFromMatter(field.children, matterData);
      Object.assign(formData, childData);
    }
  });
  
  return formData;
}

// Get nested value from object using dot notation
function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

// Local form validation
export function validateFormLocally(formData: FormData, template: FormTemplate): FormValidationError[] {
  const errors: FormValidationError[] = [];
  
  template.sections.forEach(section => {
    validateFields(section.fields, formData, errors);
  });
  
  return errors;
}

function validateFields(fields: FormField[], formData: FormData, errors: FormValidationError[]): void {
  fields.forEach(field => {
    const value = formData[field.id];
    
    // Check required fields
    if (field.required && !value) {
      errors.push({
        fieldId: field.id,
        message: `${field.label} is required`,
        severity: 'error'
      });
      return;
    }
    
    // Skip validation if field is empty and not required
    if (!value && !field.required) return;
    
    // Apply field-specific validation
    if (field.validation) {
      const validation = field.validation;
      
      // Pattern validation
      if (validation.pattern && !new RegExp(validation.pattern).test(String(value))) {
        errors.push({
          fieldId: field.id,
          message: validation.errorMessage || `${field.label} format is invalid`,
          severity: 'error'
        });
      }
      
      // Length validation
      if (validation.minLength && String(value).length < validation.minLength) {
        errors.push({
          fieldId: field.id,
          message: `${field.label} must be at least ${validation.minLength} characters`,
          severity: 'error'
        });
      }
      
      if (validation.maxLength && String(value).length > validation.maxLength) {
        errors.push({
          fieldId: field.id,
          message: `${field.label} must be no more than ${validation.maxLength} characters`,
          severity: 'error'
        });
      }
      
      // Numeric validation
      if (validation.min !== undefined && Number(value) < validation.min) {
        errors.push({
          fieldId: field.id,
          message: `${field.label} must be at least ${validation.min}`,
          severity: 'error'
        });
      }
      
      if (validation.max !== undefined && Number(value) > validation.max) {
        errors.push({
          fieldId: field.id,
          message: `${field.label} must be no more than ${validation.max}`,
          severity: 'error'
        });
      }
    }
    
    // Validate conditional children if condition is met
    if (field.children && evaluateCondition(field.condition, formData)) {
      validateFields(field.children, formData, errors);
    }
  });
}

// Flatten form data for submission
export function flattenFormData(formData: FormData): FormData {
  const flattened: FormData = {};
  
  function flatten(obj: any, prefix: string = ''): void {
    Object.keys(obj).forEach(key => {
      const value = obj[key];
      const newKey = prefix ? `${prefix}.${key}` : key;
      
      if (value && typeof value === 'object' && !Array.isArray(value) && !(value instanceof Date)) {
        flatten(value, newKey);
      } else {
        flattened[newKey] = value;
      }
    });
  }
  
  flatten(formData);
  return flattened;
}

// Group templates by category
export function groupTemplatesByCategory(templates: FormTemplate[]): Record<string, FormTemplate[]> {
  return templates.reduce((groups, template) => {
    const category = template.category || 'Other';
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(template);
    return groups;
  }, {} as Record<string, FormTemplate[]>);
}

// Sort templates by requirement and name
export function sortTemplates(templates: FormTemplate[]): FormTemplate[] {
  return [...templates].sort((a, b) => {
    // Required forms first
    if (a.isRequired !== b.isRequired) {
      return a.isRequired ? -1 : 1;
    }
    // Then by name
    return a.name.localeCompare(b.name);
  });
}

// Cache templates in localStorage
const TEMPLATE_CACHE_KEY = 'legal_ai_form_templates';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

export function cacheTemplates(templates: FormTemplate[]): void {
  const cache = {
    templates,
    timestamp: Date.now()
  };
  localStorage.setItem(TEMPLATE_CACHE_KEY, JSON.stringify(cache));
}

export function getCachedTemplates(): FormTemplate[] | null {
  const cached = localStorage.getItem(TEMPLATE_CACHE_KEY);
  if (!cached) return null;
  
  try {
    const { templates, timestamp } = JSON.parse(cached);
    
    // Check if cache is expired
    if (Date.now() - timestamp > CACHE_DURATION) {
      localStorage.removeItem(TEMPLATE_CACHE_KEY);
      return null;
    }
    
    // Convert date strings back to Date objects
    return templates.map((t: any) => ({
      ...t,
      lastUpdated: new Date(t.lastUpdated),
      mcpLastUpdated: t.mcpLastUpdated ? new Date(t.mcpLastUpdated) : undefined
    }));
  } catch {
    return null;
  }
}

// Generate unique field ID
export function generateFieldId(): string {
  return `field_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Calculate form completion percentage
export function calculateFormCompletion(formData: FormData, template: FormTemplate): number {
  let totalFields = 0;
  let completedFields = 0;
  
  template.sections.forEach(section => {
    countFieldCompletion(section.fields, formData);
  });
  
  function countFieldCompletion(fields: FormField[], data: FormData): void {
    fields.forEach(field => {
      if (field.type === 'heading' || field.type === 'paragraph') return;
      
      totalFields++;
      if (data[field.id] !== undefined && data[field.id] !== '') {
        completedFields++;
      }
      
      if (field.children && evaluateCondition(field.condition, data)) {
        countFieldCompletion(field.children, data);
      }
    });
  }
  
  return totalFields === 0 ? 0 : Math.round((completedFields / totalFields) * 100);
}

// Validate form with MCP integration
export async function validateFormWithMCP(
  formData: FormData,
  template: FormTemplate,
  api: any
): Promise<Record<string, string>> {
  const errors: Record<string, string> = {};
  
  // First do local validation
  const localErrors = validateFormLocally(formData, template);
  localErrors.forEach(error => {
    errors[error.fieldId] = error.message;
  });
  
  // If local validation passes, do MCP validation
  if (Object.keys(errors).length === 0) {
    try {
      const response = await api.post('/api/mcp/query', {
        server: 'document_templates',
        action: 'validate_form',
        params: {
          templateId: template.id,
          formData: formData,
          jurisdiction: template.jurisdiction
        }
      });
      
      if (response.data && !response.data.isValid) {
        Object.assign(errors, response.data.errors);
      }
    } catch (error) {
      console.error('MCP validation failed:', error);
      // Continue with local validation only
    }
  }
  
  return errors;
}

// Auto-populate form from matter data with template
export function populateFromMatter(template: FormTemplate, matterData: MatterData): FormData {
  const formData: FormData = {};
  
  template.sections.forEach(section => {
    const sectionData = populateFromMatterFields(section.fields, matterData);
    Object.assign(formData, sectionData);
  });
  
  return formData;
}

function populateFromMatterFields(fields: FormField[], matterData: MatterData): FormData {
  const formData: FormData = {};
  
  fields.forEach(field => {
    if (field.autoPopulateFrom) {
      const value = getNestedValue(matterData, field.autoPopulateFrom);
      if (value !== undefined) {
        formData[field.id] = value;
      }
    } else if (field.defaultValue !== undefined) {
      formData[field.id] = field.defaultValue;
    }
    
    // Recursively populate nested fields
    if (field.children) {
      const childData = populateFromMatterFields(field.children, matterData);
      Object.assign(formData, childData);
    }
  });
  
  return formData;
}