import React from 'react';
import { FormField } from '../types';

interface RadioFieldProps {
  field: FormField;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  error?: string;
  disabled?: boolean;
}

export function RadioField({ field, value, onChange, error, disabled }: RadioFieldProps) {
  return (
    <div className="form-field">
      <fieldset>
        <legend className="block text-sm font-medium text-gray-700 mb-2">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </legend>
        <div className="space-y-2">
          {field.options?.map((option) => (
            <label key={option.value} className="flex items-center">
              <input
                type="radio"
                name={field.id}
                value={option.value}
                checked={value === option.value}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                required={field.required}
                className="mr-2 text-blue-600 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">{option.label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {field.helpText && !error && (
        <p className="mt-1 text-sm text-gray-500">{field.helpText}</p>
      )}
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}