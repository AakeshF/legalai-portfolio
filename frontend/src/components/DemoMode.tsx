import React, { useState } from 'react';
import { Sparkles, PlayCircle, X, ChevronRight, FileText, MessageSquare, Upload } from 'lucide-react';
import { useToast } from './Toast';

interface DemoModeProps {
  onLoadSampleData: () => void;
  onStartTour?: () => void;
  isActive: boolean;
  onToggle: (active: boolean) => void;
}

export const DemoMode: React.FC<DemoModeProps> = ({ 
  onLoadSampleData, 
  onStartTour, 
  isActive, 
  onToggle 
}) => {
  const [showBanner, setShowBanner] = useState(true);
  const { showSuccess } = useToast();

  const handleLoadSampleData = () => {
    onLoadSampleData();
    showSuccess('Sample data loaded', 'Demo documents have been added to your library');
  };

  if (!showBanner) return null;

  return (
    <div className={`fixed bottom-4 right-4 z-40 max-w-sm animate-slide-up ${
      isActive ? 'animate-pulse-scale' : ''
    }`}>
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg shadow-lifted p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5" />
            <h3 className="font-semibold">Demo Mode</h3>
          </div>
          <button
            onClick={() => setShowBanner(false)}
            className="text-white/80 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <p className="text-sm text-white/90 mb-4">
          Experience the full capabilities with sample legal documents and guided features.
        </p>
        
        <div className="space-y-2">
          <button
            onClick={handleLoadSampleData}
            className="w-full flex items-center justify-between px-3 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors btn-press"
          >
            <span className="flex items-center space-x-2">
              <FileText className="w-4 h-4" />
              <span className="text-sm font-medium">Load Sample Documents</span>
            </span>
            <ChevronRight className="w-4 h-4" />
          </button>
          
          {onStartTour && (
            <button
              onClick={onStartTour}
              className="w-full flex items-center justify-between px-3 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors btn-press"
            >
              <span className="flex items-center space-x-2">
                <PlayCircle className="w-4 h-4" />
                <span className="text-sm font-medium">Start Guided Tour</span>
              </span>
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
          
          <label className="flex items-center space-x-2 px-3 py-2">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => onToggle(e.target.checked)}
              className="rounded border-white/50 bg-white/20 text-white focus:ring-white/50"
            />
            <span className="text-sm">Enhanced animations</span>
          </label>
        </div>
      </div>
    </div>
  );
};

interface WelcomeOverlayProps {
  onClose: () => void;
  onStartDemo: () => void;
}

export const WelcomeOverlay: React.FC<WelcomeOverlayProps> = ({ onClose, onStartDemo }) => {
  const features = [
    { icon: FileText, title: 'Document Analysis', description: 'AI-powered legal document processing' },
    { icon: MessageSquare, title: 'Smart Chat', description: 'Ask questions about your documents' },
    { icon: Upload, title: 'Easy Upload', description: 'Drag & drop PDF, DOCX, and TXT files' }
  ];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden animate-slide-up">
        <div className="relative bg-gradient-to-br from-blue-600 to-purple-600 text-white p-8">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/80 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
          
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-3 bg-white/20 rounded-xl">
              <Sparkles className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Welcome to LegalAI</h1>
              <p className="text-white/90">Your intelligent legal document assistant</p>
            </div>
          </div>
        </div>
        
        <div className="p-8">
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {features.map((feature, index) => (
              <div 
                key={index} 
                className="text-center animate-fade-in"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-xl mb-3">
                  <feature.icon className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-1">{feature.title}</h3>
                <p className="text-sm text-slate-600">{feature.description}</p>
              </div>
            ))}
          </div>
          
          <div className="space-y-3">
            <button
              onClick={onStartDemo}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:shadow-lg transition-all duration-200 btn-press animate-pulse-scale"
            >
              <PlayCircle className="w-5 h-5 inline mr-2" />
              Start with Demo Data
            </button>
            
            <button
              onClick={onClose}
              className="w-full py-3 bg-slate-100 text-slate-700 rounded-lg font-medium hover:bg-slate-200 transition-colors btn-press"
            >
              Skip to Main App
            </button>
          </div>
          
          <p className="text-xs text-slate-500 text-center mt-6">
            Press <kbd className="px-2 py-1 bg-slate-100 rounded text-xs">?</kbd> anytime for keyboard shortcuts
          </p>
        </div>
      </div>
    </div>
  );
};

export const generateSampleDocuments = () => {
  const sampleDocs = [
    {
      id: 'demo-1',
      filename: 'Service_Agreement_TechCorp.pdf',
      file_size: 2457600,
      processing_status: 'completed',
      upload_timestamp: new Date(Date.now() - 86400000).toISOString(),
      summary: 'Software service agreement between TechCorp Inc. and ClientCo LLC for cloud-based solutions. Key terms include 12-month duration, $50,000 monthly fee, and 99.9% uptime SLA.',
      legal_metadata: {
        document_type: 'Contract',
        parties: [
          { name: 'TechCorp Inc.', role: 'Service Provider', type: 'organization' },
          { name: 'ClientCo LLC', role: 'Client', type: 'organization' }
        ],
        money_amounts: [
          { amount: 50000, currency: 'USD', context: 'Monthly service fee', payment_schedule: 'Due on 1st of each month' }
        ],
        dates: [
          { date: '2024-01-01', type: 'Effective Date' },
          { date: '2024-12-31', type: 'Termination Date' }
        ],
        risk_indicators: [
          { category: 'Payment Terms', severity: 'low', description: 'Standard NET-30 payment terms' },
          { category: 'Liability', severity: 'medium', description: 'Liability cap set at 12 months of fees' }
        ],
        key_terms: ['SLA', 'Confidentiality', 'Intellectual Property', 'Termination'],
        risk_score: 3
      }
    },
    {
      id: 'demo-2',
      filename: 'Employment_Contract_John_Doe.pdf',
      file_size: 1843200,
      processing_status: 'completed',
      upload_timestamp: new Date(Date.now() - 172800000).toISOString(),
      summary: 'Executive employment agreement for John Doe as Chief Technology Officer. Includes $250,000 base salary, equity compensation, and comprehensive benefits package.',
      legal_metadata: {
        document_type: 'Employment Agreement',
        parties: [
          { name: 'StartupCo Inc.', role: 'Employer', type: 'organization' },
          { name: 'John Doe', role: 'Employee', type: 'individual' }
        ],
        money_amounts: [
          { amount: 250000, currency: 'USD', context: 'Annual base salary' },
          { amount: 50000, currency: 'USD', context: 'Signing bonus' }
        ],
        dates: [
          { date: '2024-02-01', type: 'Start Date' },
          { date: '2024-02-01', type: 'Vesting Commencement' }
        ],
        key_terms: ['At-will Employment', 'Non-compete', 'Stock Options', 'Benefits'],
        risk_score: 4
      }
    },
    {
      id: 'demo-3',
      filename: 'NDA_Mutual_Partners.pdf',
      file_size: 921600,
      processing_status: 'processing',
      upload_timestamp: new Date(Date.now() - 3600000).toISOString(),
      summary: 'Processing document...',
      legal_metadata: {
        document_type: 'Non-Disclosure Agreement',
        risk_score: 2
      }
    }
  ];

  return sampleDocs;
};