import React from 'react';
import { FormField, FormData, FormValidationError } from './types';
import { evaluateCondition } from './utils';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { AlertCircle, HelpCircle, Calendar, Clock, Upload, Plus, Trash2 } from 'lucide-react';

// Individual field components
import { TextField } from './fields/TextField';
import { TextAreaField } from './fields/TextAreaField';
import { NumberField } from './fields/NumberField';
import { DateField } from './fields/DateField';
import { SelectField } from './fields/SelectField';
import { RadioField } from './fields/RadioField';
import { CheckboxField } from './fields/CheckboxField';
import { FileField } from './fields/FileField';
import { SignatureField } from './fields/SignatureField';
import { RepeatingField } from './fields/RepeatingField';

interface FormFieldRendererProps {
  field: FormField;
  value: any;
  onChange: (value: any) => void;
  errors?: FormValidationError[];
  error?: string;
  disabled?: boolean;
  formData?: FormData;
  isSimpleMode?: boolean;
}

export const FormFieldRenderer: React.FC<FormFieldRendererProps> = ({
  field,
  value,
  onChange,
  errors = [],
  error,
  disabled = false,
  formData = {},
  isSimpleMode: propIsSimpleMode
}) => {
  const { isSimpleMode: contextIsSimpleMode, getSimpleText } = useSimpleMode();
  const isSimpleMode = propIsSimpleMode ?? contextIsSimpleMode;
  
  // Handle conditional fields
  if (field.type === 'conditional') {
    if (!evaluateCondition(field.condition, formData)) {
      return null;
    }
    // Render children if condition is met
    return (
      <div className="space-y-6 pl-6 border-l-2 border-blue-200">
        {field.children?.map((childField) => (
          <FormFieldRenderer
            key={childField.id}
            field={childField}
            value={formData[childField.id]}
            onChange={(val) => onChange({ ...formData, [childField.id]: val })}
            errors={errors.filter(e => e.fieldId === childField.id)}
            formData={formData}
          />
        ))}
      </div>
    );
  }
  
  // Handle group fields
  if (field.type === 'group') {
    return (
      <div className="space-y-6 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h4 className={`font-semibold text-gray-900
          ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
          {field.label}
        </h4>
        {field.helpText && (
          <p className={`text-gray-600
            ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
            {field.helpText}
          </p>
        )}
        {field.children?.map((childField) => (
          <FormFieldRenderer
            key={childField.id}
            field={childField}
            value={formData[childField.id]}
            onChange={(val) => onChange({ ...formData, [childField.id]: val })}
            errors={errors.filter(e => e.fieldId === childField.id)}
            formData={formData}
          />
        ))}
      </div>
    );
  }
  
  // Handle heading
  if (field.type === 'heading') {
    return (
      <h3 className={`font-semibold text-gray-900
        ${isSimpleMode ? 'text-xl' : 'text-lg'}`}>
        {field.label}
      </h3>
    );
  }
  
  // Handle paragraph
  if (field.type === 'paragraph') {
    return (
      <p className={`text-gray-600
        ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
        {field.label}
      </p>
    );
  }
  
  // Render regular field with wrapper
  const hasError = errors.length > 0 || !!error;
  const errorMessage = error || errors[0]?.message;
  
  return (
    <div className="space-y-2">
      {/* Field Component - render directly without wrapper for most fields */}
      {renderField(field, value, onChange, errorMessage, disabled, isSimpleMode, getSimpleText, formData)}
    </div>
  );
};

// Helper function to render specific field types
function renderField(
  field: FormField,
  value: any,
  onChange: (value: any) => void,
  error: string | undefined,
  disabled: boolean,
  isSimpleMode: boolean,
  getSimpleText: (text: string) => string,
  formData: FormData
) {
  switch (field.type) {
    case 'text':
      return (
        <TextField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'textarea':
      return (
        <TextAreaField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'number':
      return (
        <NumberField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'date':
    case 'time':
    case 'datetime':
      return (
        <DateField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'select':
    case 'multiselect':
      return (
        <SelectField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'radio':
      return (
        <RadioField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'checkbox':
      return (
        <CheckboxField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'file':
      return (
        <FileField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'signature':
      return (
        <SignatureField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      );
      
    case 'repeating':
      return (
        <RepeatingField
          field={field}
          value={value}
          onChange={onChange}
          error={error}
          disabled={disabled}
          errors={{}}
          isSimpleMode={isSimpleMode}
        />
      );
      
    default:
      return (
        <div className="p-4 bg-gray-100 rounded text-gray-600">
          Unsupported field type: {field.type}
        </div>
      );
  }
}