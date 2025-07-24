import React from 'react';
import { FormField } from '../types';

interface TextFieldProps {
  field: FormField;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  error?: string;
  disabled?: boolean;
  isSimpleMode?: boolean;
}

export function TextField({ field, value, onChange, error, disabled, isSimpleMode }: TextFieldProps) {
  return (
    <div className="form-field">
      <label htmlFor={field.id} className="block text-sm font-medium text-gray-700 mb-1">
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <input
        type="text"
        id={field.id}
        name={field.name}
        value={value || ''}
        onChange={(e) => onChange(e.target.value || undefined)}
        disabled={disabled}
        required={field.required}
        placeholder={field.placeholder}
        className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          error ? 'border-red-300' : 'border-gray-300'
        } ${disabled ? 'bg-gray-50' : ''} ${isSimpleMode ? 'text-lg' : 'text-base'}`}
      />
      {field.helpText && !error && (
        <p className="mt-1 text-sm text-gray-500">{field.helpText}</p>
      )}
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}