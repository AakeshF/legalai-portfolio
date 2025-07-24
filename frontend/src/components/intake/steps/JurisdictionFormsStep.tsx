import React, { useState, useEffect } from 'react';
import { 
  FileText, Loader2, AlertCircle, CheckCircle, 
  Download, ChevronRight, Info, FileCheck 
} from 'lucide-react';
import { StepProps } from '../CaseIntakeWizard';
import { useJurisdictionForms, JurisdictionForm, FormField } from '../../../services/mcp';
import { useSimpleMode } from '../../../contexts/SimpleModeContext';
import { SimpleModeInput, SimpleModeCard, SimpleModeAlert } from '../../SimpleModeWrapper';

export const JurisdictionFormsStep: React.FC<StepProps> = ({ 
  data, 
  updateData, 
  onNext,
  onBack 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const [formData, setFormData] = useState<Record<string, any>>(data.forms || {});
  const [completedForms, setCompletedForms] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Fetch required forms based on case type and jurisdiction
  const { 
    data: formsResponse, 
    isLoading, 
    error 
  } = useJurisdictionForms(
    data.caseType || '', 
    data.jurisdiction || ''
  );

  const forms = formsResponse?.data || [];
  const requiredForms = forms.filter(f => f.required);
  const optionalForms = forms.filter(f => !f.required);

  // Update parent data when form data changes
  useEffect(() => {
    updateData({ forms: formData });
  }, [formData, updateData]);

  const handleFieldChange = (formId: string, fieldName: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [formId]: {
        ...prev[formId],
        [fieldName]: value
      }
    }));
    
    // Clear error for this field
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[`${formId}.${fieldName}`];
      return newErrors;
    });
  };

  const validateForm = (form: JurisdictionForm): boolean => {
    let isValid = true;
    const newErrors: Record<string, string> = {};

    form.fields.forEach(field => {
      const value = formData[form.id]?.[field.name];
      
      if (field.required && !value) {
        newErrors[`${form.id}.${field.name}`] = `${field.label} is required`;
        isValid = false;
      }
      
      if (value && field.validation) {
        if (field.validation.pattern) {
          const regex = new RegExp(field.validation.pattern);
          if (!regex.test(value)) {
            newErrors[`${form.id}.${field.name}`] = `Invalid format for ${field.label}`;
            isValid = false;
          }
        }
        
        if (field.validation.minLength && value.length < field.validation.minLength) {
          newErrors[`${form.id}.${field.name}`] = 
            `${field.label} must be at least ${field.validation.minLength} characters`;
          isValid = false;
        }
        
        if (field.validation.maxLength && value.length > field.validation.maxLength) {
          newErrors[`${form.id}.${field.name}`] = 
            `${field.label} must be no more than ${field.validation.maxLength} characters`;
          isValid = false;
        }
      }
    });

    setErrors(prev => ({ ...prev, ...newErrors }));
    return isValid;
  };

  const markFormComplete = (formId: string) => {
    const form = forms.find(f => f.id === formId);
    if (form && validateForm(form)) {
      setCompletedForms(prev => new Set(prev).add(formId));
    }
  };

  const isFormComplete = (formId: string): boolean => {
    return completedForms.has(formId);
  };

  const allRequiredFormsComplete = requiredForms.every(form => isFormComplete(form.id));
  const canProceed = allRequiredFormsComplete;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">
          {getSimpleText('Loading required forms...')}
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <SimpleModeAlert type="error">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{getSimpleText('Unable to load forms')}</p>
            <p className="mt-1">{getSimpleText('Please try again or contact support')}</p>
          </div>
        </div>
      </SimpleModeAlert>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className={`font-semibold text-gray-900 mb-2 ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          {getSimpleText('Required Forms')}
        </h2>
        <p className={`text-gray-600 mb-6 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
          {getSimpleText(`Complete the following forms required for ${data.caseType} cases in ${data.jurisdiction}`)}
        </p>

        {/* Forms Summary */}
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <FileCheck className="w-5 h-5 text-blue-600 mr-3" />
              <span className={`text-blue-900 font-medium ${
                isSimpleMode ? 'text-lg' : 'text-base'
              }`}>
                {completedForms.size} of {requiredForms.length} required forms completed
              </span>
            </div>
            <div className="flex items-center space-x-2">
              {allRequiredFormsComplete && (
                <CheckCircle className="w-5 h-5 text-green-600" />
              )}
            </div>
          </div>
        </div>

        {/* Required Forms */}
        {requiredForms.length > 0 && (
          <div className="space-y-6">
            <h3 className={`font-medium text-gray-900 ${
              isSimpleMode ? 'text-xl' : 'text-lg'
            }`}>
              {getSimpleText('Required Forms')}
            </h3>
            {requiredForms.map(form => (
              <FormCard
                key={form.id}
                form={form}
                formData={formData[form.id] || {}}
                errors={errors}
                isComplete={isFormComplete(form.id)}
                onFieldChange={(field, value) => handleFieldChange(form.id, field, value)}
                onComplete={() => markFormComplete(form.id)}
              />
            ))}
          </div>
        )}

        {/* Optional Forms */}
        {optionalForms.length > 0 && (
          <div className="space-y-6 mt-8">
            <h3 className={`font-medium text-gray-900 ${
              isSimpleMode ? 'text-xl' : 'text-lg'
            }`}>
              {getSimpleText('Optional Forms')}
            </h3>
            {optionalForms.map(form => (
              <FormCard
                key={form.id}
                form={form}
                formData={formData[form.id] || {}}
                errors={errors}
                isComplete={isFormComplete(form.id)}
                isOptional
                onFieldChange={(field, value) => handleFieldChange(form.id, field, value)}
                onComplete={() => markFormComplete(form.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between">
        <button
          onClick={onBack}
          className={`
            flex items-center px-6 py-3 rounded-lg font-medium transition-all
            bg-gray-200 text-gray-700 hover:bg-gray-300
            ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
          `}
        >
          {getSimpleText('Back')}
        </button>

        <button
          onClick={onNext}
          disabled={!canProceed}
          className={`
            flex items-center px-6 py-3 rounded-lg font-medium transition-all
            ${canProceed
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }
            ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
          `}
        >
          {getSimpleText('Continue')}
          <ChevronRight className="w-5 h-5 ml-2" />
        </button>
      </div>
    </div>
  );
};

// Form Card Component
interface FormCardProps {
  form: JurisdictionForm;
  formData: Record<string, any>;
  errors: Record<string, string>;
  isComplete: boolean;
  isOptional?: boolean;
  onFieldChange: (fieldName: string, value: any) => void;
  onComplete: () => void;
}

const FormCard: React.FC<FormCardProps> = ({ 
  form, 
  formData, 
  errors,
  isComplete,
  isOptional = false,
  onFieldChange,
  onComplete
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const [isExpanded, setIsExpanded] = useState(!isComplete);

  return (
    <div className={`border rounded-lg ${
      isComplete ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'
    }`}>
      <div 
        className="p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <FileText className={`w-5 h-5 ${
              isComplete ? 'text-green-600' : 'text-gray-400'
            }`} />
            <div>
              <h4 className={`font-medium ${
                isComplete ? 'text-green-900' : 'text-gray-900'
              } ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                {getSimpleText(form.name)}
                {isOptional && (
                  <span className="ml-2 text-sm text-gray-500">
                    ({getSimpleText('Optional')})
                  </span>
                )}
              </h4>
              {form.description && (
                <p className={`mt-1 ${
                  isComplete ? 'text-green-700' : 'text-gray-600'
                } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                  {getSimpleText(form.description)}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {isComplete && <CheckCircle className="w-5 h-5 text-green-600" />}
            <ChevronRight className={`w-5 h-5 text-gray-400 transition-transform ${
              isExpanded ? 'rotate-90' : ''
            }`} />
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {form.fields.map(field => (
              <div key={field.name} className={
                field.type === 'textarea' ? 'md:col-span-2' : ''
              }>
                <FormFieldInput
                  field={field}
                  value={formData[field.name] || ''}
                  error={errors[`${form.id}.${field.name}`]}
                  onChange={(value) => onFieldChange(field.name, value)}
                />
              </div>
            ))}
          </div>
          
          <div className="mt-4 flex justify-end">
            <button
              onClick={onComplete}
              className={`px-4 py-2 rounded-lg font-medium transition-all
                ${isComplete 
                  ? 'bg-green-600 text-white hover:bg-green-700' 
                  : 'bg-blue-600 text-white hover:bg-blue-700'
                }
                ${isSimpleMode ? 'text-base min-h-[44px]' : 'text-sm'}
              `}
            >
              {isComplete ? getSimpleText('Update Form') : getSimpleText('Mark Complete')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Form Field Input Component
interface FormFieldInputProps {
  field: FormField;
  value: any;
  error?: string;
  onChange: (value: any) => void;
}

const FormFieldInput: React.FC<FormFieldInputProps> = ({ 
  field, 
  value, 
  error,
  onChange 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();

  switch (field.type) {
    case 'select':
      return (
        <div>
          <label className={`block font-medium text-gray-700 mb-2 ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            {getSimpleText(field.label)}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={`
              w-full rounded-lg border ${error ? 'border-red-500' : 'border-gray-300'}
              focus:outline-none focus:ring-2 focus:ring-blue-500
              ${isSimpleMode ? 'px-4 py-3 text-lg min-h-[48px]' : 'px-3 py-2 text-base'}
            `}
          >
            <option value="">{getSimpleText('Select an option')}</option>
            {field.options?.map(option => (
              <option key={option} value={option}>
                {getSimpleText(option)}
              </option>
            ))}
          </select>
          {error && (
            <p className={`mt-1 text-red-600 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
              {getSimpleText(error)}
            </p>
          )}
        </div>
      );

    case 'checkbox':
      return (
        <div>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => onChange(e.target.checked)}
              className={`rounded border-gray-300 text-blue-600 
                focus:ring-2 focus:ring-blue-500
                ${isSimpleMode ? 'w-5 h-5' : 'w-4 h-4'}
              `}
            />
            <span className={`text-gray-700 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
              {getSimpleText(field.label)}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </span>
          </label>
          {error && (
            <p className={`mt-1 text-red-600 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
              {getSimpleText(error)}
            </p>
          )}
        </div>
      );

    case 'textarea':
      return (
        <SimpleModeInput
          label={field.label}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          error={error}
          required={field.required}
          as="textarea"
          rows={4}
        />
      );

    default:
      return (
        <SimpleModeInput
          label={field.label}
          type={field.type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          error={error}
          required={field.required}
        />
      );
  }
};