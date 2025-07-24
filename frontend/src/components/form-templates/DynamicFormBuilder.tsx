import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, Check, ChevronRight, Save, Send, Download } from 'lucide-react';
import { FormTemplate, FormSection, FormField, FormData, FormValidationError } from './types';
import { 
  validateFormLocally, 
  populateFromMatter, 
  calculateFormCompletion,
  evaluateCondition 
} from './utils';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { useToast } from '../Toast';
import { useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';
import { FormFieldRenderer } from './FormFieldRenderer';

interface DynamicFormBuilderProps {
  template: FormTemplate;
  initialData?: FormData;
  matterData?: any;
  onSubmit: (data: FormData) => Promise<void>;
  onSaveDraft?: (data: FormData) => void;
  onCancel: () => void;
}

export const DynamicFormBuilder: React.FC<DynamicFormBuilderProps> = ({
  template,
  initialData = {},
  matterData,
  onSubmit,
  onSaveDraft,
  onCancel
}) => {
  const [formData, setFormData] = useState<FormData>(() => {
    // Auto-populate from matter data if available
    if (matterData) {
      const allFields: FormField[] = [];
      template.sections.forEach(section => {
        allFields.push(...section.fields);
      });
      return { ...initialData, ...populateFromMatter(allFields, matterData) };
    }
    return initialData;
  });
  
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [validationErrors, setValidationErrors] = useState<FormValidationError[]>([]);
  const [showValidation, setShowValidation] = useState(false);
  
  const { isSimpleMode, getSimpleText } = useSimpleMode();
  const { showSuccess, showError, showInfo } = useToast();
  
  const currentSection = template.sections[currentSectionIndex];
  const completionPercentage = calculateFormCompletion(formData, template);
  
  // MCP validation mutation
  const validateMutation = useMutation({
    mutationFn: async (data: FormData) => {
      const response = await api.post('/api/form-templates/validate', {
        templateId: template.id,
        formData: data,
        jurisdiction: template.jurisdiction
      });
      
      if (!response.ok) throw new Error('Validation failed');
      return response.json();
    },
    onSuccess: (result) => {
      if (result.errors?.length > 0) {
        setValidationErrors(result.errors);
        showError('Validation issues found', 'Please review the highlighted fields');
      } else {
        setValidationErrors([]);
        showSuccess('Validation passed', 'All fields are valid');
      }
    },
    onError: () => {
      // Fall back to local validation
      const errors = validateFormLocally(formData, template);
      setValidationErrors(errors);
      if (errors.length > 0) {
        showError('Validation issues found', 'Please review the highlighted fields');
      }
    }
  });
  
  // Update field value
  const updateField = useCallback((fieldId: string, value: any) => {
    setFormData(prev => ({ ...prev, [fieldId]: value }));
    // Clear validation error for this field
    setValidationErrors(prev => prev.filter(e => e.fieldId !== fieldId));
  }, []);
  
  // Navigate sections
  const canGoNext = currentSectionIndex < template.sections.length - 1;
  const canGoPrevious = currentSectionIndex > 0;
  
  const goToNextSection = () => {
    if (canGoNext) {
      // Validate current section before moving forward
      const sectionErrors = validationErrors.filter(error => {
        return currentSection.fields.some(field => field.id === error.fieldId);
      });
      
      if (sectionErrors.length > 0) {
        setShowValidation(true);
        showError('Please fix errors', 'Complete all required fields before proceeding');
        return;
      }
      
      setCurrentSectionIndex(prev => prev + 1);
      setShowValidation(false);
    }
  };
  
  const goToPreviousSection = () => {
    if (canGoPrevious) {
      setCurrentSectionIndex(prev => prev - 1);
      setShowValidation(false);
    }
  };
  
  // Handle form submission
  const handleSubmit = async () => {
    setShowValidation(true);
    
    // Run validation
    await validateMutation.mutateAsync(formData);
    
    const errors = validateFormLocally(formData, template);
    if (errors.length > 0) {
      setValidationErrors(errors);
      showError('Form incomplete', 'Please complete all required fields');
      return;
    }
    
    try {
      await onSubmit(formData);
      showSuccess('Form submitted', 'Your form has been successfully submitted');
    } catch (error) {
      showError('Submission failed', 'Please try again');
    }
  };
  
  // Handle draft save
  const handleSaveDraft = () => {
    if (onSaveDraft) {
      onSaveDraft(formData);
      showSuccess('Draft saved', 'Your progress has been saved');
    }
  };
  
  // Auto-save draft every 30 seconds
  useEffect(() => {
    if (!onSaveDraft) return;
    
    const interval = setInterval(() => {
      onSaveDraft(formData);
    }, 30000);
    
    return () => clearInterval(interval);
  }, [formData, onSaveDraft]);
  
  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className={`font-bold text-gray-900 mb-2
          ${isSimpleMode ? 'text-2xl' : 'text-xl'}`}>
          {template.name}
        </h2>
        <p className={`text-gray-600 mb-4
          ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
          {template.description}
        </p>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>{getSimpleText('Progress')}</span>
            <span>{completionPercentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div 
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
        </div>
      </div>
      
      {/* Section Navigation */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex items-center justify-between overflow-x-auto">
          {template.sections.map((section, index) => (
            <button
              key={section.id}
              onClick={() => setCurrentSectionIndex(index)}
              className={`flex items-center px-4 py-2 rounded-lg transition-all whitespace-nowrap
                ${index === currentSectionIndex
                  ? 'bg-blue-100 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'}
                ${isSimpleMode ? 'text-base min-h-[40px]' : 'text-sm'}`}
            >
              <span className={`flex items-center justify-center w-6 h-6 rounded-full mr-2
                ${index === currentSectionIndex
                  ? 'bg-blue-600 text-white'
                  : index < currentSectionIndex
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-300 text-gray-600'}`}>
                {index < currentSectionIndex ? (
                  <Check className="w-4 h-4" />
                ) : (
                  index + 1
                )}
              </span>
              {section.title}
            </button>
          ))}
        </div>
      </div>
      
      {/* Current Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className={`font-semibold text-gray-900 mb-2
          ${isSimpleMode ? 'text-xl' : 'text-lg'}`}>
          {currentSection.title}
        </h3>
        {currentSection.description && (
          <p className={`text-gray-600 mb-6
            ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
            {currentSection.description}
          </p>
        )}
        
        {/* Form Fields */}
        <div className="space-y-6">
          {currentSection.fields.map((field) => {
            // Check if field should be visible based on condition
            if (field.condition && !evaluateCondition(field.condition, formData)) {
              return null;
            }
            
            const fieldErrors = showValidation 
              ? validationErrors.filter(e => e.fieldId === field.id)
              : [];
            
            return (
              <FormFieldRenderer
                key={field.id}
                field={field}
                value={formData[field.id]}
                onChange={(value) => updateField(field.id, value)}
                errors={fieldErrors}
                formData={formData}
              />
            );
          })}
        </div>
      </div>
      
      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={goToPreviousSection}
          disabled={!canGoPrevious}
          className={`px-6 py-3 border border-gray-300 rounded-lg font-medium
            transition-all disabled:opacity-50 disabled:cursor-not-allowed
            hover:bg-gray-50
            ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
        >
          {getSimpleText('Previous')}
        </button>
        
        <div className="flex-1" />
        
        {onSaveDraft && (
          <button
            onClick={handleSaveDraft}
            className={`flex items-center px-6 py-3 border border-gray-300 
              rounded-lg font-medium transition-all hover:bg-gray-50
              ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
          >
            <Save className="w-5 h-5 mr-2" />
            {getSimpleText('Save Draft')}
          </button>
        )}
        
        {canGoNext ? (
          <button
            onClick={goToNextSection}
            className={`flex items-center px-6 py-3 bg-blue-600 text-white 
              rounded-lg font-medium transition-all hover:bg-blue-700
              ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
          >
            {getSimpleText('Next')}
            <ChevronRight className="w-5 h-5 ml-2" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={validateMutation.isLoading}
            className={`flex items-center px-6 py-3 bg-green-600 text-white 
              rounded-lg font-medium transition-all hover:bg-green-700
              disabled:opacity-50 disabled:cursor-not-allowed
              ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
          >
            <Send className="w-5 h-5 mr-2" />
            {validateMutation.isLoading ? getSimpleText('Validating...') : getSimpleText('Submit')}
          </button>
        )}
      </div>
      
      {/* Validation Summary */}
      {showValidation && validationErrors.length > 0 && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
            <div>
              <h4 className="font-medium text-red-900 mb-1">
                {getSimpleText('Please fix the following issues:')}
              </h4>
              <ul className="list-disc list-inside space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="text-red-700 text-sm">
                    {error.message}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};