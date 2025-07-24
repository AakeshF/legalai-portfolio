import React, { useRef } from 'react';
import { Upload } from 'lucide-react';
import { FormField } from '../types';

interface FileFieldProps {
  field: FormField;
  value: File | undefined;
  onChange: (value: File | undefined) => void;
  error?: string;
  disabled?: boolean;
}

export function FileField({ field, value, onChange, error, disabled }: FileFieldProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    onChange(file);
  };

  const handleRemove = () => {
    onChange(undefined);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="form-field">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {!value ? (
        <div className="relative">
          <input
            ref={fileInputRef}
            type="file"
            id={field.id}
            onChange={handleFileChange}
            disabled={disabled}
            required={field.required}
            accept={field.validation?.accept}
            className="sr-only"
          />
          <label
            htmlFor={field.id}
            className={`flex items-center justify-center w-full px-4 py-3 border-2 border-dashed rounded-lg cursor-pointer hover:border-gray-400 transition-colors ${
              error ? 'border-red-300' : 'border-gray-300'
            } ${disabled ? 'bg-gray-50 cursor-not-allowed' : ''}`}
          >
            <Upload className="w-5 h-5 mr-2 text-gray-400" />
            <span className="text-sm text-gray-600">
              Click to upload or drag and drop
            </span>
          </label>
        </div>
      ) : (
        <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-md">
          <span className="text-sm text-gray-700 truncate">{value.name}</span>
          <button
            type="button"
            onClick={handleRemove}
            disabled={disabled}
            className="text-sm text-red-600 hover:text-red-700 font-medium"
          >
            Remove
          </button>
        </div>
      )}
      
      {field.helpText && !error && (
        <p className="mt-1 text-sm text-gray-500">{field.helpText}</p>
      )}
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}