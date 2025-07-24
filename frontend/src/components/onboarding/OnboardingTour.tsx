import React, { useEffect, useState } from 'react';
import { X, ChevronLeft, ChevronRight, CheckCircle } from 'lucide-react';
import { useOnboarding } from '../../contexts/OnboardingContext';
import { createPortal } from 'react-dom';

interface HighlightPosition {
  top: number;
  left: number;
  width: number;
  height: number;
}

export const OnboardingTour: React.FC = () => {
  const {
    isOnboarding,
    currentStep,
    steps,
    nextStep,
    previousStep,
    skipOnboarding,
    completeOnboarding,
  } = useOnboarding();

  const [highlightPosition, setHighlightPosition] = useState<HighlightPosition | null>(null);

  const currentStepData = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;

  useEffect(() => {
    if (!isOnboarding || !currentStepData.target) {
      setHighlightPosition(null);
      return;
    }

    // Find and highlight target element
    const targetElement = document.querySelector(currentStepData.target);
    if (targetElement) {
      const rect = targetElement.getBoundingClientRect();
      setHighlightPosition({
        top: rect.top - 5,
        left: rect.left - 5,
        width: rect.width + 10,
        height: rect.height + 10,
      });

      // Scroll element into view
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isOnboarding, currentStep, currentStepData]);

  if (!isOnboarding) return null;

  const getTooltipPosition = () => {
    if (!highlightPosition || !currentStepData.position) {
      return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
    }

    const tooltipWidth = 400;
    const tooltipHeight = 200;
    const padding = 20;

    switch (currentStepData.position) {
      case 'top':
        return {
          top: highlightPosition.top - tooltipHeight - padding,
          left: highlightPosition.left + highlightPosition.width / 2 - tooltipWidth / 2,
        };
      case 'bottom':
        return {
          top: highlightPosition.top + highlightPosition.height + padding,
          left: highlightPosition.left + highlightPosition.width / 2 - tooltipWidth / 2,
        };
      case 'left':
        return {
          top: highlightPosition.top + highlightPosition.height / 2 - tooltipHeight / 2,
          left: highlightPosition.left - tooltipWidth - padding,
        };
      case 'right':
        return {
          top: highlightPosition.top + highlightPosition.height / 2 - tooltipHeight / 2,
          left: highlightPosition.left + highlightPosition.width + padding,
        };
      default:
        return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
    }
  };

  return createPortal(
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-[9998]" onClick={skipOnboarding} />

      {/* Highlight */}
      {highlightPosition && (
        <div
          className="fixed border-4 border-blue-500 rounded-lg pointer-events-none z-[9999] animate-pulse"
          style={{
            top: highlightPosition.top,
            left: highlightPosition.left,
            width: highlightPosition.width,
            height: highlightPosition.height,
          }}
        />
      )}

      {/* Tooltip */}
      <div
        className="fixed bg-white rounded-lg shadow-2xl p-6 w-96 z-[10000] animate-fade-in"
        style={getTooltipPosition()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {currentStepData.title}
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Step {currentStep + 1} of {steps.length}
            </p>
          </div>
          <button
            onClick={skipOnboarding}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <p className="text-gray-700 mb-6">
          {currentStepData.description}
        </p>

        {/* Progress dots */}
        <div className="flex justify-center space-x-2 mb-6">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`h-2 w-2 rounded-full transition-all ${
                index === currentStep
                  ? 'bg-blue-600 w-8'
                  : index < currentStep
                  ? 'bg-blue-400'
                  : 'bg-gray-300'
              }`}
            />
          ))}
        </div>

        {/* Actions */}
        <div className="flex justify-between">
          <button
            onClick={previousStep}
            disabled={currentStep === 0}
            className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </button>

          <div className="flex space-x-3">
            <button
              onClick={skipOnboarding}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Skip Tour
            </button>
            
            {isLastStep ? (
              <button
                onClick={completeOnboarding}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Complete
              </button>
            ) : (
              <button
                onClick={nextStep}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </button>
            )}
          </div>
        </div>
      </div>
    </>,
    document.body
  );
};

// Onboarding prompt component
export const OnboardingPrompt: React.FC = () => {
  const { showOnboardingPrompt, startOnboarding, dismissOnboardingPrompt } = useOnboarding();

  if (!showOnboardingPrompt) return null;

  return createPortal(
    <div className="fixed bottom-6 right-6 bg-white rounded-lg shadow-xl p-6 max-w-sm z-50 animate-slide-up">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 p-2 bg-blue-100 rounded-lg">
          <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            New to Legal AI Assistant?
          </h4>
          <p className="text-sm text-gray-600 mb-3">
            Take a quick tour to learn how to analyze legal documents with AI.
          </p>
          <div className="flex space-x-2">
            <button
              onClick={startOnboarding}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              Start Tour
            </button>
            <button
              onClick={dismissOnboardingPrompt}
              className="px-3 py-1.5 text-gray-600 text-sm hover:text-gray-800 transition-colors"
            >
              Maybe Later
            </button>
          </div>
        </div>
        <button
          onClick={dismissOnboardingPrompt}
          className="flex-shrink-0 p-1 hover:bg-gray-100 rounded transition-colors"
        >
          <X className="h-4 w-4 text-gray-400" />
        </button>
      </div>
    </div>,
    document.body
  );
};