import React, { useState } from 'react';
import { AlertTriangle, Shield, Lock, Info, CheckCircle, X } from 'lucide-react';
import { RedactedSegment } from '../../types/anonymization';

interface SensitiveDataConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (consent: ConsentData) => void;
  detectedSensitiveTypes: string[];
  segments: RedactedSegment[];
  model: string;
  isAIProviderDemo?: boolean;
}

interface ConsentData {
  clientAuthorized: boolean;
  dataIsSanitized: boolean;
  understandRisks: boolean;
  additionalNotes?: string;
}

const SENSITIVITY_LEVELS = {
  low: {
    color: 'yellow',
    icon: Info,
    title: 'Low Sensitivity',
    description: 'This prompt contains general information that may be identifiable.'
  },
  medium: {
    color: 'orange',
    icon: AlertTriangle,
    title: 'Medium Sensitivity',
    description: 'This prompt contains personal or business information.'
  },
  high: {
    color: 'red',
    icon: Shield,
    title: 'High Sensitivity',
    description: 'This prompt contains sensitive personal, financial, or legal information.'
  },
  critical: {
    color: 'red',
    icon: Lock,
    title: 'Critical Sensitivity',
    description: 'This prompt contains highly confidential information requiring special handling.'
  }
};

export const SensitiveDataConsentModal: React.FC<SensitiveDataConsentModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  detectedSensitiveTypes,
  segments,
  model,
  isAIProviderDemo = false
}) => {
  const [consent, setConsent] = useState<ConsentData>({
    clientAuthorized: false,
    dataIsSanitized: false,
    understandRisks: false,
    additionalNotes: ''
  });
  const [showDetails, setShowDetails] = useState(false);

  if (!isOpen) return null;

  const getSensitivityLevel = () => {
    const hasFinancial = detectedSensitiveTypes.includes('financial');
    const hasMedical = detectedSensitiveTypes.includes('medical');
    const hasLegal = detectedSensitiveTypes.includes('legal');
    const segmentCount = segments.length;

    if (hasFinancial || hasMedical || segmentCount > 5) return 'critical';
    if (hasLegal || segmentCount > 3) return 'high';
    if (segmentCount > 1) return 'medium';
    return 'low';
  };

  const sensitivityLevel = getSensitivityLevel();
  const levelConfig = SENSITIVITY_LEVELS[sensitivityLevel];
  const Icon = levelConfig.icon;

  const canConfirm = consent.clientAuthorized && consent.dataIsSanitized && consent.understandRisks;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className={`p-6 bg-${levelConfig.color}-50 border-b border-${levelConfig.color}-200`}>
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <Icon className={`w-6 h-6 text-${levelConfig.color}-600 mt-1`} />
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  {levelConfig.title} Data Detected
                </h2>
                <p className="text-sm text-gray-700 mt-1">
                  {levelConfig.description}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div className={`p-4 bg-${levelConfig.color}-50 border border-${levelConfig.color}-200 rounded-lg`}>
            <div className="flex items-start gap-3">
              <AlertTriangle className={`w-5 h-5 text-${levelConfig.color}-600 mt-0.5`} />
              <div className="flex-1">
                <p className="font-medium text-gray-900">Sensitive Information Warning</p>
                <p className="text-sm text-gray-700 mt-1">
                  We've detected {segments.length} sensitive data element{segments.length > 1 ? 's' : ''} in your prompt:
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Array.from(new Set(segments.map(s => s.type))).map(type => (
                    <span
                      key={type}
                      className={`px-2 py-1 text-xs bg-${levelConfig.color}-100 text-${levelConfig.color}-800 rounded`}
                    >
                      {type.charAt(0).toUpperCase() + type.slice(1)} Data
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {isAIProviderDemo && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <Lock className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-900">Demo Mode Restrictions</p>
                  <p className="text-sm text-blue-700 mt-1">
                    [AI Provider] demo mode only accepts pre-defined placeholder prompts. 
                    Your actual data will not be sent to the AI model.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
            >
              {showDetails ? 'Hide' : 'Show'} detected items
              <ChevronDown className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`} />
            </button>
            
            {showDetails && (
              <div className="mt-3 space-y-2">
                {segments.map((segment, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded"
                  >
                    <span className="text-sm text-gray-600">{segment.redacted}</span>
                    <span className="text-xs text-gray-500">{segment.type}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <h3 className="font-medium text-gray-900">Required Confirmations</h3>
            
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.clientAuthorized}
                onChange={(e) => setConsent({ ...consent, clientAuthorized: e.target.checked })}
                className="w-5 h-5 text-blue-600 rounded mt-0.5"
              />
              <div className="flex-1">
                <p className="font-medium text-gray-900">Client Authorization</p>
                <p className="text-sm text-gray-600">
                  I confirm that I have obtained proper authorization from the client to share this information
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.dataIsSanitized}
                onChange={(e) => setConsent({ ...consent, dataIsSanitized: e.target.checked })}
                className="w-5 h-5 text-blue-600 rounded mt-0.5"
              />
              <div className="flex-1">
                <p className="font-medium text-gray-900">Data Sanitization</p>
                <p className="text-sm text-gray-600">
                  I have reviewed and properly sanitized all sensitive information
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.understandRisks}
                onChange={(e) => setConsent({ ...consent, understandRisks: e.target.checked })}
                className="w-5 h-5 text-blue-600 rounded mt-0.5"
              />
              <div className="flex-1">
                <p className="font-medium text-gray-900">Risk Acknowledgment</p>
                <p className="text-sm text-gray-600">
                  I understand the risks of sharing sensitive data with AI systems and accept responsibility
                </p>
              </div>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes (Optional)
            </label>
            <textarea
              value={consent.additionalNotes}
              onChange={(e) => setConsent({ ...consent, additionalNotes: e.target.value })}
              placeholder="Add any additional context or justification..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>

          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-gray-600 mt-0.5" />
              <div className="text-sm text-gray-600">
                <p className="font-medium">AI Model: {model}</p>
                <p className="mt-1">
                  This consent will be logged for compliance and audit purposes.
                  Your organization's data retention policies apply.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 bg-gray-50 border-t border-gray-200">
          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => onConfirm(consent)}
              disabled={!canConfirm}
              className={`px-6 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                canConfirm
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              Confirm and Proceed
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};