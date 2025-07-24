import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChevronRight, ChevronLeft, Check, AlertCircle } from 'lucide-react';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { SimpleModeWrapper } from '../SimpleModeWrapper';
import { MCPServerStatus } from './MCPServerStatus';
import { CaseTypeStep } from './steps/CaseTypeStep';
import { ClientInfoStep } from './steps/ClientInfoStep';
import { MatterDetailsStep } from './steps/MatterDetailsStep';
import { JurisdictionFormsStep } from './steps/JurisdictionFormsStep';
import { ReviewStep } from './steps/ReviewStep';

// Create a new QueryClient for the wizard
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 5 * 60 * 1000 // 5 minutes
    }
  }
});

export interface IntakeData {
  caseType?: string;
  jurisdiction?: string;
  client?: {
    name: string;
    email: string;
    phone: string;
    address: string;
    dateOfBirth?: string;
  };
  adverseParty?: {
    name: string;
    attorney?: string;
  };
  matter?: {
    description: string;
    caseNumber?: string;
    courtName?: string;
    judge?: string;
    nextHearing?: string;
    filingDeadline?: string;
  };
  forms?: Record<string, any>;
  conflicts?: any[];
}

interface Step {
  id: string;
  title: string;
  description: string;
  component: React.ComponentType<StepProps>;
  validate?: (data: IntakeData) => string | null;
}

export interface StepProps {
  data: IntakeData;
  updateData: (updates: Partial<IntakeData>) => void;
  onNext: () => void;
  onBack: () => void;
  isFirstStep: boolean;
  isLastStep: boolean;
}

const steps: Step[] = [
  {
    id: 'case-type',
    title: 'Case Type',
    description: 'Select the type of legal matter',
    component: CaseTypeStep,
    validate: (data) => {
      if (!data.caseType) return 'Please select a case type';
      if (!data.jurisdiction) return 'Please select a jurisdiction';
      return null;
    }
  },
  {
    id: 'client-info',
    title: 'Client Information',
    description: 'Enter client details and check for conflicts',
    component: ClientInfoStep,
    validate: (data) => {
      if (!data.client?.name) return 'Client name is required';
      if (!data.client?.email && !data.client?.phone) 
        return 'Please provide either email or phone number';
      if (data.conflicts && data.conflicts.length > 0 && data.conflicts.some(c => c.severity === 'high'))
        return 'High severity conflicts must be resolved before proceeding';
      return null;
    }
  },
  {
    id: 'matter-details',
    title: 'Matter Details',
    description: 'Provide case information',
    component: MatterDetailsStep,
    validate: (data) => {
      if (!data.matter?.description) return 'Please provide a matter description';
      return null;
    }
  },
  {
    id: 'forms',
    title: 'Required Forms',
    description: 'Complete jurisdiction-specific forms',
    component: JurisdictionFormsStep,
    validate: (data) => {
      // Dynamic validation based on required forms
      return null;
    }
  },
  {
    id: 'review',
    title: 'Review & Submit',
    description: 'Review all information before submitting',
    component: ReviewStep
  }
];

export const CaseIntakeWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [intakeData, setIntakeData] = useState<IntakeData>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { getSimpleText, isSimpleMode } = useSimpleMode();

  const updateData = (updates: Partial<IntakeData>) => {
    setIntakeData(prev => ({ ...prev, ...updates }));
    // Clear errors for updated fields
    const errorKeys = Object.keys(updates);
    setErrors(prev => {
      const newErrors = { ...prev };
      errorKeys.forEach(key => delete newErrors[key]);
      return newErrors;
    });
  };

  const handleNext = () => {
    const step = steps[currentStep];
    if (step.validate) {
      const error = step.validate(intakeData);
      if (error) {
        setErrors({ [step.id]: error });
        return;
      }
    }
    
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const CurrentStepComponent = steps[currentStep].component;

  return (
    <QueryClientProvider client={queryClient}>
      <SimpleModeWrapper className="min-h-screen bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className={`font-bold text-gray-900 ${isSimpleMode ? 'text-4xl' : 'text-3xl'}`}>
              {getSimpleText('New Case Intake')}
            </h1>
            <p className={`text-gray-600 mt-2 ${isSimpleMode ? 'text-xl' : 'text-lg'}`}>
              {getSimpleText('Complete the following steps to create a new case')}
            </p>
          </div>

          {/* MCP Server Status */}
          <MCPServerStatus />

          {/* Progress Indicator */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              {steps.map((step, index) => (
                <React.Fragment key={step.id}>
                  <div className="flex items-center">
                    <div
                      className={`
                        ${isSimpleMode ? 'w-12 h-12' : 'w-10 h-10'} 
                        rounded-full flex items-center justify-center font-semibold
                        ${index < currentStep 
                          ? 'bg-green-600 text-white' 
                          : index === currentStep 
                            ? 'bg-blue-600 text-white' 
                            : 'bg-gray-200 text-gray-600'
                        }
                      `}
                    >
                      {index < currentStep ? (
                        <Check className={isSimpleMode ? 'w-6 h-6' : 'w-5 h-5'} />
                      ) : (
                        index + 1
                      )}
                    </div>
                    <div className="ml-3 hidden md:block">
                      <p className={`font-medium text-gray-900 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                        {getSimpleText(step.title)}
                      </p>
                      <p className={`text-gray-500 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                        {getSimpleText(step.description)}
                      </p>
                    </div>
                  </div>
                  {index < steps.length - 1 && (
                    <div 
                      className={`flex-1 h-1 mx-4 ${
                        index < currentStep ? 'bg-green-600' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Mobile Step Indicator */}
            <div className="md:hidden text-center">
              <p className={`font-medium text-gray-900 ${isSimpleMode ? 'text-xl' : 'text-lg'}`}>
                Step {currentStep + 1} of {steps.length}: {getSimpleText(steps[currentStep].title)}
              </p>
            </div>
          </div>

          {/* Error Display */}
          {errors[steps[currentStep].id] && (
            <div className={`mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              <AlertCircle className="w-5 h-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
              <span className="text-red-800">{getSimpleText(errors[steps[currentStep].id])}</span>
            </div>
          )}

          {/* Step Content */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <CurrentStepComponent
              data={intakeData}
              updateData={updateData}
              onNext={handleNext}
              onBack={handleBack}
              isFirstStep={currentStep === 0}
              isLastStep={currentStep === steps.length - 1}
            />
          </div>

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center">
            <button
              onClick={handleBack}
              disabled={currentStep === 0}
              className={`
                flex items-center px-6 py-3 rounded-lg font-medium transition-all
                ${currentStep === 0 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }
                ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
              `}
            >
              <ChevronLeft className="w-5 h-5 mr-2" />
              {getSimpleText('Back')}
            </button>

            <div className="text-center">
              <p className={`text-gray-600 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                {currentStep + 1} / {steps.length}
              </p>
            </div>

            <button
              onClick={handleNext}
              className={`
                flex items-center px-6 py-3 rounded-lg font-medium transition-all
                bg-blue-600 text-white hover:bg-blue-700
                ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
              `}
            >
              {currentStep === steps.length - 1 ? getSimpleText('Submit') : getSimpleText('Next')}
              <ChevronRight className="w-5 h-5 ml-2" />
            </button>
          </div>
        </div>
      </SimpleModeWrapper>
      
    </QueryClientProvider>
  );
};

export default CaseIntakeWizard;