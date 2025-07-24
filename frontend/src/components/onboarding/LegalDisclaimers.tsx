import React, { useState, useEffect } from 'react';
import { AlertTriangle, Scale, Shield, Info, X } from 'lucide-react';

interface LegalDisclaimersProps {
  context?: 'upload' | 'chat' | 'general';
  onAccept?: () => void;
  onDecline?: () => void;
}

export const LegalDisclaimers: React.FC<LegalDisclaimersProps> = ({ 
  context = 'general',
  onAccept,
  onDecline 
}) => {
  const [showFullDisclaimer, setShowFullDisclaimer] = useState(false);
  const [hasAccepted, setHasAccepted] = useState(false);

  useEffect(() => {
    // Check if user has previously accepted disclaimers
    const accepted = localStorage.getItem('legal-disclaimers-accepted');
    if (accepted) {
      setHasAccepted(true);
    }
  }, []);

  const handleAccept = () => {
    setHasAccepted(true);
    localStorage.setItem('legal-disclaimers-accepted', 'true');
    localStorage.setItem('legal-disclaimers-date', new Date().toISOString());
    onAccept?.();
  };

  const handleDecline = () => {
    onDecline?.();
  };

  const getContextualDisclaimer = () => {
    switch (context) {
      case 'upload':
        return (
          <p className="text-sm text-gray-700">
            Documents uploaded to this platform are encrypted and stored securely. 
            However, AI analysis should not replace professional legal advice.
          </p>
        );
      case 'chat':
        return (
          <p className="text-sm text-gray-700">
            AI responses are for informational purposes only and do not constitute 
            legal advice. Always consult with a licensed attorney.
          </p>
        );
      default:
        return (
          <p className="text-sm text-gray-700">
            This AI assistant provides document analysis and insights but does not 
            replace professional legal counsel.
          </p>
        );
    }
  };

  if (hasAccepted && !showFullDisclaimer) {
    // Show minimal disclaimer for accepted users
    return (
      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Scale className="h-4 w-4 text-gray-500" />
            <p className="text-xs text-gray-600">
              AI analysis is not legal advice. 
              <button
                onClick={() => setShowFullDisclaimer(true)}
                className="ml-1 text-blue-600 hover:text-blue-700 underline"
              >
                View full disclaimer
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-amber-200 shadow-lg">
      {/* Header */}
      <div className="p-4 bg-amber-50 border-b border-amber-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <AlertTriangle className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Important Legal Notice</h3>
              <p className="text-sm text-gray-600">Please read before using AI assistance</p>
            </div>
          </div>
          {showFullDisclaimer && hasAccepted && (
            <button
              onClick={() => setShowFullDisclaimer(false)}
              className="p-1 hover:bg-amber-100 rounded transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4">
        {/* Contextual disclaimer */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              {getContextualDisclaimer()}
            </div>
          </div>
        </div>

        {/* Main disclaimers */}
        <div className="space-y-3">
          <div className="flex items-start space-x-3">
            <div className="p-1.5 bg-gray-100 rounded">
              <Scale className="h-4 w-4 text-gray-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900 mb-1">Not Legal Advice</h4>
              <p className="text-sm text-gray-600">
                Information provided by this AI system is for general informational purposes only 
                and does not constitute legal advice. No attorney-client relationship is formed.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="p-1.5 bg-gray-100 rounded">
              <Shield className="h-4 w-4 text-gray-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900 mb-1">Professional Consultation Required</h4>
              <p className="text-sm text-gray-600">
                Always consult with a qualified attorney licensed in your jurisdiction before 
                making legal decisions or taking legal action based on any analysis.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="p-1.5 bg-gray-100 rounded">
              <AlertTriangle className="h-4 w-4 text-gray-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900 mb-1">Limitations of AI Analysis</h4>
              <p className="text-sm text-gray-600">
                AI may make errors, miss important details, or misinterpret complex legal concepts. 
                Human review and verification of all AI-generated analysis is essential.
              </p>
            </div>
          </div>
        </div>

        {/* Expanded disclaimer */}
        <details className="text-sm text-gray-600">
          <summary className="cursor-pointer font-medium text-gray-700 hover:text-gray-900">
            View complete terms and conditions
          </summary>
          <div className="mt-3 space-y-2 text-xs leading-relaxed">
            <p>
              <strong>1. No Legal Advice:</strong> The Legal AI Assistant provides document analysis 
              and information extraction services. It does not provide legal advice, legal opinions, 
              or legal representation.
            </p>
            <p>
              <strong>2. No Attorney-Client Relationship:</strong> Use of this service does not create 
              an attorney-client relationship between you and any party.
            </p>
            <p>
              <strong>3. Jurisdictional Limitations:</strong> Legal requirements vary by jurisdiction. 
              This service may not be aware of or account for specific local, state, or federal laws 
              applicable to your situation.
            </p>
            <p>
              <strong>4. Accuracy Disclaimer:</strong> While we strive for accuracy, AI systems can 
              make mistakes. All output should be verified by qualified legal professionals.
            </p>
            <p>
              <strong>5. Confidentiality:</strong> While we implement security measures, absolute 
              confidentiality cannot be guaranteed. Sensitive documents should be handled with appropriate care.
            </p>
            <p>
              <strong>6. Liability Limitation:</strong> We are not liable for any damages arising from 
              the use or inability to use this service, including any decisions made based on AI analysis.
            </p>
          </div>
        </details>

        {/* Actions */}
        {!hasAccepted && (
          <div className="pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                By proceeding, you acknowledge these limitations
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={handleDecline}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAccept}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  I Understand
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Inline disclaimer for chat messages
export const InlineDisclaimer: React.FC = () => {
  return (
    <div className="flex items-center space-x-2 p-2 bg-gray-50 rounded-lg border border-gray-200">
      <Scale className="h-3 w-3 text-gray-400 flex-shrink-0" />
      <p className="text-xs text-gray-500">
        This is AI-generated analysis, not legal advice. Consult an attorney for legal matters.
      </p>
    </div>
  );
};

// Modal disclaimer for first-time users
export const DisclaimerModal: React.FC<{
  isOpen: boolean;
  onAccept: () => void;
  onDecline: () => void;
}> = ({ isOpen, onAccept, onDecline }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-amber-50 to-orange-50">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-amber-100 rounded-lg">
              <AlertTriangle className="h-8 w-8 text-amber-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Legal Disclaimer</h2>
              <p className="text-gray-600">Important information before you begin</p>
            </div>
          </div>
        </div>
        
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          <LegalDisclaimers context="general" />
        </div>
        
        <div className="p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              You must accept these terms to use the service
            </p>
            <div className="flex space-x-3">
              <button
                onClick={onDecline}
                className="px-6 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Decline
              </button>
              <button
                onClick={onAccept}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Accept & Continue
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};