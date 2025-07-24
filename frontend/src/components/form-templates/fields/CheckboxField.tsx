import React from 'react';
import { FormField } from '../types';

interface CheckboxFieldProps {
  field: FormField;
  value: boolean | string[] | undefined;
  onChange: (value: boolean | string[] | undefined) => void;
  error?: string;
  disabled?: boolean;
}

export function CheckboxField({ field, value, onChange, error, disabled }: CheckboxFieldProps) {
  // Single checkbox
  if (!field.options || field.options.length === 0) {
    return (
      <div className="form-field">
        <label className="flex items-center">
          <input
            type="checkbox"
            id={field.id}
            checked={value === true}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
            required={field.required}
            className="mr-2 text-blue-600 focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </span>
        </label>
        {field.helpText && !error && (
          <p className="mt-1 text-sm text-gray-500 ml-6">{field.helpText}</p>
        )}
        {error && <p className="mt-1 text-sm text-red-600 ml-6">{error}</p>}
      </div>
    );
  }

  // Multiple checkboxes
  const selectedValues = Array.isArray(value) ? value : [];
  
  return (
    <div className="form-field">
      <fieldset>
        <legend className="block text-sm font-medium text-gray-700 mb-2">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </legend>
        <div className="space-y-2">
          {field.options.map((option) => (
            <label key={option.value} className="flex items-center">
              <input
                type="checkbox"
                value={option.value}
                checked={selectedValues.includes(option.value)}
                onChange={(e) => {
                  if (e.target.checked) {
                    onChange([...selectedValues, option.value]);
                  } else {
                    onChange(selectedValues.filter(v => v !== option.value));
                  }
                }}
                disabled={disabled}
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