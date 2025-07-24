import React, { createContext, useContext, useState, useEffect } from 'react';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  target?: string; // CSS selector for element to highlight
  position?: 'top' | 'bottom' | 'left' | 'right';
  action?: () => void;
}

interface OnboardingContextType {
  isOnboarding: boolean;
  currentStep: number;
  steps: OnboardingStep[];
  startOnboarding: () => void;
  nextStep: () => void;
  previousStep: () => void;
  skipOnboarding: () => void;
  completeOnboarding: () => void;
  hasCompletedOnboarding: boolean;
  showOnboardingPrompt: boolean;
  dismissOnboardingPrompt: () => void;
}

const OnboardingContext = createContext<OnboardingContextType | undefined>(undefined);

// Default onboarding steps for legal professionals
const defaultSteps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to Legal AI Assistant',
    description: 'Let\'s take a quick tour to help you get the most out of our AI-powered legal document analysis platform.',
  },
  {
    id: 'upload',
    title: 'Upload Legal Documents',
    description: 'Start by uploading contracts, briefs, or any legal documents. We support PDF, DOCX, and TXT formats.',
    target: '[data-tour="upload-button"]',
    position: 'bottom',
  },
  {
    id: 'document-list',
    title: 'Document Library',
    description: 'View all your uploaded documents here. Documents are securely stored and encrypted.',
    target: '[data-tour="documents-button"]',
    position: 'right',
  },
  {
    id: 'ai-chat',
    title: 'AI Legal Assistant',
    description: 'Chat with our AI to analyze documents, extract key terms, identify risks, and get legal insights.',
    target: '[data-tour="chat-button"]',
    position: 'right',
  },
  {
    id: 'security',
    title: 'Enterprise Security',
    description: 'Your data is protected with bank-level encryption, HIPAA compliance, and SOC 2 certification.',
    target: '[data-tour="security-indicator"]',
    position: 'bottom',
  },
  {
    id: 'sample-docs',
    title: 'Try Sample Documents',
    description: 'Not ready to upload your own documents? Try our sample legal documents to see the AI in action.',
    target: '[data-tour="demo-mode"]',
    position: 'top',
  },
];

export const OnboardingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(false);
  const [showOnboardingPrompt, setShowOnboardingPrompt] = useState(false);
  const [steps] = useState<OnboardingStep[]>(defaultSteps);

  // Check if user has completed onboarding
  useEffect(() => {
    const completed = localStorage.getItem('onboarding-completed') === 'true';
    const dismissed = localStorage.getItem('onboarding-dismissed') === 'true';
    const lastPrompt = localStorage.getItem('onboarding-last-prompt');
    
    setHasCompletedOnboarding(completed);
    
    // Show prompt if not completed, not dismissed, and haven't shown in last 7 days
    if (!completed && !dismissed) {
      const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
      if (!lastPrompt || parseInt(lastPrompt) < sevenDaysAgo) {
        setTimeout(() => setShowOnboardingPrompt(true), 3000); // Show after 3 seconds
      }
    }
  }, []);

  const startOnboarding = () => {
    setIsOnboarding(true);
    setCurrentStep(0);
    setShowOnboardingPrompt(false);
  };

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      completeOnboarding();
    }
  };

  const previousStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const skipOnboarding = () => {
    setIsOnboarding(false);
    setCurrentStep(0);
    localStorage.setItem('onboarding-dismissed', 'true');
  };

  const completeOnboarding = () => {
    setIsOnboarding(false);
    setCurrentStep(0);
    setHasCompletedOnboarding(true);
    localStorage.setItem('onboarding-completed', 'true');
    localStorage.removeItem('onboarding-dismissed');
  };

  const dismissOnboardingPrompt = () => {
    setShowOnboardingPrompt(false);
    localStorage.setItem('onboarding-last-prompt', Date.now().toString());
  };

  const value: OnboardingContextType = {
    isOnboarding,
    currentStep,
    steps,
    startOnboarding,
    nextStep,
    previousStep,
    skipOnboarding,
    completeOnboarding,
    hasCompletedOnboarding,
    showOnboardingPrompt,
    dismissOnboardingPrompt,
  };

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
};

export const useOnboarding = () => {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error('useOnboarding must be used within OnboardingProvider');
  }
  return context;
};