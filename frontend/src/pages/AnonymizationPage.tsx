import React, { useState, useEffect } from 'react';
import { Shield, Settings, History, Lock } from 'lucide-react';
import {
  PromptAnonymizer,
  AnonymizationSettings,
  UserSubmissionHistory,
  PromptReviewStatus,
  SensitiveDataConsentModal,
  DeepSeekDemoMode,
  detectSensitiveData
} from '../components/anonymization';
import { useAuth } from '../contexts/AuthContext';
import { AnonymizationSettings as AnonymizationSettingsType, RedactedSegment } from '../types/anonymization';

export const AnonymizationPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'compose' | 'settings' | 'history'>('compose');
  const [promptValue, setPromptValue] = useState('');
  const [selectedModel, setSelectedModel] = useState('gpt-4-turbo');
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [pendingSubmission, setPendingSubmission] = useState<{
    original: string;
    redacted: string;
    segments: RedactedSegment[];
  } | null>(null);
  const [submissionStatus, setSubmissionStatus] = useState<string | null>(null);
  const [isDeepSeekDemo, setIsDeepSeekDemo] = useState(false);
  
  const [settings, setSettings] = useState<AnonymizationSettingsType>({
    autoRedactionEnabled: true,
    sensitivityThreshold: 'medium',
    customPatterns: [],
    enabledCategories: ['personal', 'financial', 'medical', 'legal'],
    requireApprovalForSensitive: true
  });

  useEffect(() => {
    // Load user settings
    loadUserSettings();
  }, [user]);

  const loadUserSettings = async () => {
    try {
      const response = await fetch(`/api/users/${user?.id}/anonymization-settings`);
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const handlePromptSubmit = async (original: string, redacted: string, segments: RedactedSegment[]) => {
    // Check if consent is needed
    const result = detectSensitiveData(original);
    
    if (result.segments.length > 0 && settings.requireApprovalForSensitive) {
      setPendingSubmission({ original, redacted, segments });
      setShowConsentModal(true);
    } else {
      await submitPrompt(original, redacted, segments);
    }
  };

  const handleConsentConfirm = async (consentData: any) => {
    setShowConsentModal(false);
    if (pendingSubmission) {
      await submitPrompt(
        pendingSubmission.original,
        pendingSubmission.redacted,
        pendingSubmission.segments,
        consentData
      );
    }
  };

  const submitPrompt = async (
    original: string,
    redacted: string,
    segments: RedactedSegment[],
    consentData?: any
  ) => {
    try {
      const response = await fetch('/api/prompts/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          originalContent: original,
          redactedContent: redacted,
          segments,
          model: selectedModel,
          autoRedactionEnabled: settings.autoRedactionEnabled,
          consent: consentData
        })
      });

      const data = await response.json();
      
      if (data.requiresReview) {
        setSubmissionStatus(data.id);
      } else {
        // Process immediately
        await processPrompt(data.id);
      }
      
      setPromptValue('');
    } catch (error) {
      console.error('Failed to submit prompt:', error);
    }
  };

  const processPrompt = async (promptId: string) => {
    try {
      const response = await fetch(`/api/prompts/${promptId}/process`, {
        method: 'POST'
      });
      const result = await response.json();
      // Handle AI response
      console.log('AI Response:', result);
    } catch (error) {
      console.error('Failed to process prompt:', error);
    }
  };

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
    setIsDeepSeekDemo(model === '[ai-provider]-demo');
  };

  const handleDeepSeekPromptSelect = (prompt: string) => {
    setPromptValue(prompt);
  };

  const tabs = [
    { id: 'compose', label: 'Compose', icon: Shield },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'history', label: 'History', icon: History }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Secure AI Prompting</h1>
        <p className="text-gray-600 mt-2">
          Anonymize sensitive data before sending prompts to AI models
        </p>
      </div>

      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === 'compose' && (
        <div className="space-y-6">
          {submissionStatus && (
            <PromptReviewStatus
              promptId={submissionStatus}
              onStatusChange={(status) => {
                if (status === 'approved') {
                  processPrompt(submissionStatus);
                  setSubmissionStatus(null);
                }
              }}
            />
          )}

          {isDeepSeekDemo ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DeepSeekDemoMode onSelectPrompt={handleDeepSeekPromptSelect} />
              <div>
                <PromptAnonymizer
                  value={promptValue}
                  onChange={setPromptValue}
                  onSubmit={handlePromptSubmit}
                  autoRedaction={settings.autoRedactionEnabled}
                  customPatterns={settings.customPatterns}
                />
              </div>
            </div>
          ) : (
            <PromptAnonymizer
              value={promptValue}
              onChange={setPromptValue}
              onSubmit={handlePromptSubmit}
              autoRedaction={settings.autoRedactionEnabled}
              customPatterns={settings.customPatterns}
            />
          )}
        </div>
      )}

      {activeTab === 'settings' && (
        <AnonymizationSettings
          settings={settings}
          onSettingsChange={setSettings}
          organizationLocked={user?.organizationRole !== 'admin'}
          selectedModel={selectedModel}
          onModelChange={handleModelChange}
        />
      )}

      {activeTab === 'history' && user && (
        <UserSubmissionHistory
          userId={user.id}
          onSelectSubmission={(submission) => {
            setPromptValue(submission.originalContent);
            setActiveTab('compose');
          }}
        />
      )}

      {showConsentModal && pendingSubmission && (
        <SensitiveDataConsentModal
          isOpen={showConsentModal}
          onClose={() => {
            setShowConsentModal(false);
            setPendingSubmission(null);
          }}
          onConfirm={handleConsentConfirm}
          detectedSensitiveTypes={Array.from(new Set(pendingSubmission.segments.map(s => s.type)))}
          segments={pendingSubmission.segments}
          model={selectedModel}
          isDeepSeekDemo={isDeepSeekDemo}
        />
      )}
    </div>
  );
};