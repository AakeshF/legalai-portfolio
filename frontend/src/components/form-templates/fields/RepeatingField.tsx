import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { FormField } from '../types';
import { FormFieldRenderer } from '../FormFieldRenderer';

interface RepeatingFieldProps {
  field: FormField;
  value: any[] | undefined;
  onChange: (value: any[] | undefined) => void;
  error?: string;
  disabled?: boolean;
  errors?: Record<string, string>;
  isSimpleMode?: boolean;
}

export function RepeatingField({ 
  field, 
  value = [], 
  onChange, 
  error, 
  disabled, 
  errors = {},
  isSimpleMode 
}: RepeatingFieldProps) {
  const addItem = () => {
    const newItem: Record<string, any> = {};
    if (field.fields) {
      field.fields.forEach(subField => {
        newItem[subField.id] = subField.defaultValue || '';
      });
    }
    onChange([...value, newItem]);
  };

  const removeItem = (index: number) => {
    const newValue = [...value];
    newValue.splice(index, 1);
    onChange(newValue.length > 0 ? newValue : undefined);
  };

  const updateItem = (index: number, itemField: FormField, itemValue: any) => {
    const newValue = [...value];
    newValue[index] = {
      ...newValue[index],
      [itemField.id]: itemValue
    };
    onChange(newValue);
  };

  return (
    <div className="form-field">
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-gray-700">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>
        <button
          type="button"
          onClick={addItem}
          disabled={disabled || (field.validation?.maxItems && value.length >= field.validation.maxItems)}
          className="inline-flex items-center px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-4 h-4 mr-1" />
          Add {field.itemLabel || 'Item'}
        </button>
      </div>

      {field.helpText && !error && (
        <p className="mb-2 text-sm text-gray-500">{field.helpText}</p>
      )}

      <div className="space-y-4">
        {value.map((item, index) => (
          <div key={index} className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-start justify-between mb-3">
              <h4 className="text-sm font-medium text-gray-700">
                {field.itemLabel || 'Item'} {index + 1}
              </h4>
              <button
                type="button"
                onClick={() => removeItem(index)}
                disabled={disabled || (field.validation?.minItems && value.length <= field.validation.minItems)}
                className="text-red-600 hover:text-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Remove item"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              {field.fields?.map(subField => (
                <FormFieldRenderer
                  key={subField.id}
                  field={subField}
                  value={item[subField.id]}
                  onChange={(newValue) => updateItem(index, subField, newValue)}
                  error={errors[`${field.id}.${index}.${subField.id}`]}
                  disabled={disabled}
                  isSimpleMode={isSimpleMode}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {value.length === 0 && (
        <div className="mt-2 p-4 text-center text-gray-500 bg-gray-50 border border-gray-200 rounded-lg">
          No {field.itemLabel?.toLowerCase() || 'items'} added yet
        </div>
      )}

      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}