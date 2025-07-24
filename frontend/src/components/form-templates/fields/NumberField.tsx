import React from 'react';
import { FormField } from '../types';

interface NumberFieldProps {
  field: FormField;
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  error?: string;
  disabled?: boolean;
}

export function NumberField({ field, value, onChange, error, disabled }: NumberFieldProps) {
  return (
    <div className="form-field">
      <label htmlFor={field.id} className="block text-sm font-medium text-gray-700 mb-1">
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <input
        type="number"
        id={field.id}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
        disabled={disabled}
        required={field.required}
        min={field.validation?.min}
        max={field.validation?.max}
        step={field.validation?.step}
        placeholder={field.placeholder}
        className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          error ? 'border-red-300' : 'border-gray-300'
        } ${disabled ? 'bg-gray-50' : ''}`}
      />
      {field.helpText && !error && (
        <p className="mt-1 text-sm text-gray-500">{field.helpText}</p>
      )}
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}