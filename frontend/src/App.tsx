import React, { useState, useEffect, lazy, Suspense } from 'react';
import { FileText, MessageSquare, Upload, Settings, Menu, X, Shield, Sparkles, Plus, LayoutDashboard } from 'lucide-react';

// Essential Components (loaded immediately)
import Header from './components/Header';
import ErrorBoundary, { ComponentErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider, useToast } from './components/Toast';
import OfflineIndicator from './components/OfflineIndicator';
import { DocumentListSkeleton } from './components/Skeleton';
import { ApiError, NetworkError } from './utils/api';
import { documentService } from './services/document.service';
import { useDocumentPolling } from './hooks';
import { InlinePollingIndicator } from './components/PollingIndicator';
import { useSimpleMode } from './contexts/SimpleModeContext';
import { AIPreferencesProvider } from './contexts/AIPreferencesContext';
import { MockAuthProvider } from './contexts/MockAuthContext';

// Lazy loaded components for code splitting
const DocumentUpload = lazy(() => import('./components/EnhancedDocumentUpload'));
const UnifiedChatInterface = lazy(() => import('./components/chat/UnifiedChatInterface'));
const DocumentList = lazy(() => import('./components/DocumentList'));
const DocumentView = lazy(() => import('./components/DocumentView'));
const DemoMode = lazy(() => import('./components/DemoMode').then(m => ({ default: m.DemoMode })));
const WelcomeOverlay = lazy(() => import('./components/DemoMode').then(m => ({ default: m.WelcomeOverlay })));
const SuccessCelebration = lazy(() => import('./components/SuccessCelebration').then(m => ({ default: m.SuccessCelebration })));
const KeyboardShortcuts = lazy(() => import('./components/KeyboardShortcuts').then(m => ({ default: m.KeyboardShortcuts })));
const MetricsDashboard = lazy(() => import('./components/MetricsDisplay').then(m => ({ default: m.MetricsDashboard })));

// Import generateSampleDocuments separately
import { generateSampleDocuments } from './components/DemoMode';
import { useKeyboardShortcuts } from './components/KeyboardShortcuts';

// Import types to match UnifiedChatInterface
import type { AIProvider } from './components/ai-config/types';

// Types - must match UnifiedChatInterface exactly
interface Document {
  id: string | number;
  filename: string;
  file_size?: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  upload_timestamp?: string;
  created_at?: string;
  summary?: string;
  metadata?: {
    document_type?: string;
    case_number?: string;
    jurisdiction?: string;
    parties?: Array<{
      name: string;
      role: string;
      type?: 'individual' | 'organization';
    }>;
    dates?: Array<{
      date: string;
      type: string;
      description?: string;
    }>;
    money_amounts?: Array<{
      amount: number;
      currency: string;
      context: string;
    }>;
    key_terms?: string[];
    obligations?: string[];
  };
  legal_metadata?: any;
  extracted_entities?: any;
  ai_analysis?: any;
}

interface ChatMessageMetadata {
  provider_used?: AIProvider;
  model?: string;
  audit_id?: string;
  response_time_ms?: number;
  tokens_used?: number;
  cost?: number;
}

interface ChatMessageType {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: ChatMessageMetadata;
  sources?: Array<{
    document_id: string;
    document_name: string;
    relevance: string;
  }>;
  responseType?: 'instant' | 'analyzed';
  responseTime?: number;
  tokensSaved?: number;
  status?: 'pending_review' | 'blocked' | 'error' | 'completed';
  reviewId?: string;
}

type ViewType = 'chat' | 'documents' | 'upload';

// Main App component wrapped with providers
function App() {
  return (
    <ErrorBoundary>
      <MockAuthProvider>
        <AIPreferencesProvider>
          <ToastProvider>
            <AppContent />
          </ToastProvider>
        </AIPreferencesProvider>
      </MockAuthProvider>
    </ErrorBoundary>
  );
}

// Separate component to use hooks
function AppContent() {
  const [currentView, setCurrentView] = useState<ViewType>('chat');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showWelcome, setShowWelcome] = useState(() => 
    localStorage.getItem('hasSeenWelcome') !== 'true'
  );
  const [demoMode, setDemoMode] = useState(false);
  const [showSuccessCelebration, setShowSuccessCelebration] = useState(false);
  const [celebrationMessage, setCelebrationMessage] = useState('');
  
  // Hooks
  const { showSuccess, showError, showInfo } = useToast();
  const { isSimpleMode, getSimpleText } = useSimpleMode();
  
  // Document polling hook
  const { isPolling, hasProcessingDocuments } = useDocumentPolling(documents, {
    onStatusUpdate: (updatedDocuments) => {
      setDocuments(updatedDocuments);
      
      // Check if any documents just completed
      const justCompleted = updatedDocuments.filter(doc => {
        const oldDoc = documents.find(d => d.id === doc.id);
        return oldDoc?.processing_status === 'processing' && 
               doc.processing_status === 'completed';
      });
      
      if (justCompleted.length > 0) {
        showSuccess(
          'Intelligence extracted',
          `${justCompleted.length} document${justCompleted.length > 1 ? 's' : ''} dominated and analyzed`
        );
        
        // Show celebration for demo mode
        if (demoMode) {
          setCelebrationMessage('Document Analysis Complete! 🎉');
          setShowSuccessCelebration(true);
        }
      }
      
      // Check if any documents failed
      const justFailed = updatedDocuments.filter(doc => {
        const oldDoc = documents.find(d => d.id === doc.id);
        return oldDoc?.processing_status === 'processing' && 
               doc.processing_status === 'failed';
      });
      
      if (justFailed.length > 0) {
        showError(
          'Hit a snag',
          `${justFailed.length} document${justFailed.length > 1 ? 's' : ''} resisted analysis. We'll crush it next time.`
        );
      }
    },
    onError: (error) => {
      // Only show error for network issues, not for regular polling errors
      if (error instanceof NetworkError) {
        showError('Network hiccup', 'Intelligence feed temporarily disrupted');
      }
    }
  });

  // Keyboard shortcuts
  const { showShortcuts, setShowShortcuts } = useKeyboardShortcuts({
    onSearch: () => {
      // Focus search in document list
      setCurrentView('documents');
    },
    onUpload: () => setCurrentView('upload'),
    onDocuments: () => setCurrentView('documents'),
    onChat: () => setCurrentView('chat')
  });

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setIsLoadingDocuments(true);
    try {
      // Check if we're in demo mode
      const token = localStorage.getItem('legal-ai-token');
      if (token && token.startsWith('demo-token-')) {
        // In demo mode, just use the existing documents (from sample data)
        setIsLoadingDocuments(false);
        return;
      }
      
      const response = await documentService.getDocuments();
      const data = response.documents || [];
      
      // Transform data to ensure consistent field naming
      // Backend might return 'status' instead of 'processing_status'
      const transformedData = data.map((doc: any) => ({
        ...doc,
        id: String(doc.id), // Ensure id is always string
        processing_status: (doc.processing_status || doc.status || 'pending') as 'pending' | 'processing' | 'completed' | 'failed'
      })) as Document[];
      
      setDocuments(transformedData);
      
      if (data.length === 0) {
        showInfo('Arsenal empty', 'Time to feed the beast some documents');
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
      
      if (error instanceof NetworkError) {
        showError('No internet connection', 'Please check your network and try again');
      } else if (error instanceof ApiError) {
        showError('Failed to load documents', error.message);
      } else {
        showError('Failed to load documents', 'Please try again');
      }
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  const handleDocumentUpload = (newDocument: Document) => {
    // Instead of immediately adding the document, reload all documents
    // to get the latest status from the backend
    loadDocuments();
    // Switch to documents view to show the upload
    setCurrentView('documents');
  };

  const handleNewMessage = (message: ChatMessageType) => {
    setChatMessages(prev => [...prev, message]);
  };

  const handleDocumentDelete = (documentId: string) => {
    // Optimistically remove the document from state
    setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    
    // If the deleted document was selected, close the view
    if (selectedDocument?.id === documentId) {
      setSelectedDocument(null);
    }
    
    showSuccess('Document deleted', 'The document has been removed from your library');
  };

  const loadSampleData = () => {
    const sampleDocs = generateSampleDocuments();
    setDocuments(prev => [...prev, ...sampleDocs]);
    showSuccess('Sample data loaded', `${sampleDocs.length} demo documents added`);
    
    // Simulate processing completion for the NDA document after 3 seconds
    setTimeout(() => {
      setDocuments(prev => prev.map(doc => {
        if (doc.id === 'demo-3' && doc.processing_status === 'processing') {
          return {
            ...doc,
            processing_status: 'completed',
            summary: 'Mutual non-disclosure agreement between InnovateTech Solutions and GlobalPartners Inc. for discussions regarding potential strategic partnership. Duration: 3 years with standard confidentiality provisions.',
            legal_metadata: {
              document_type: 'Non-Disclosure Agreement',
              parties: [
                { name: 'InnovateTech Solutions', role: 'Disclosing Party', type: 'organization' },
                { name: 'GlobalPartners Inc.', role: 'Receiving Party', type: 'organization' }
              ],
              money_amounts: [
                { amount: 100000, currency: 'USD', context: 'Liquidated damages for breach' }
              ],
              dates: [
                { date: '2024-01-15', type: 'Effective Date' },
                { date: '2027-01-15', type: 'Expiration Date' }
              ],
              risk_indicators: [
                { category: 'Scope', severity: 'low', description: 'Well-defined confidential information scope' },
                { category: 'Duration', severity: 'medium', description: '3-year term is longer than typical' },
                { category: 'Remedies', severity: 'low', description: 'Standard liquidated damages clause' }
              ],
              key_terms: ['Mutual NDA', 'Confidential Information', 'Non-Circumvention', 'Liquidated Damages'],
              risk_score: 2
            }
          };
        }
        return doc;
      }));
      showSuccess('Document processed', 'NDA_Mutual_Partners.pdf has been analyzed');
    }, 3000);
  };

  const handleWelcomeDemoStart = () => {
    setShowWelcome(false);
    localStorage.setItem('hasSeenWelcome', 'true');
    setDemoMode(true);
    loadSampleData();
  };

  const allSidebarItems = [
    { id: 'chat', icon: MessageSquare, label: 'AI Assistant', view: 'chat' as ViewType },
    { id: 'documents', icon: FileText, label: 'Documents', view: 'documents' as ViewType, badge: documents.length },
    { id: 'upload', icon: Upload, label: 'Upload', view: 'upload' as ViewType },
    { id: 'secure-ai', icon: Shield, label: 'Secure AI', href: '/secure-ai' },
  ];
  
  // In Simple Mode, only show essential items
  const sidebarItems = isSimpleMode 
    ? allSidebarItems.filter(item => ['chat', 'documents'].includes(item.id))
    : allSidebarItems;

  // Calculate metrics
  const processedDocuments = documents.filter(d => d.processing_status === 'completed').length;
  const avgResponseTime = chatMessages
    .filter(m => m.role === 'assistant' && m.responseTime)
    .reduce((acc, m, _, arr) => acc + (m.responseTime || 0) / arr.length, 0) / 1000;
  const totalTokensSaved = chatMessages
    .filter(m => m.role === 'assistant' && m.tokensSaved)
    .reduce((acc, m) => acc + (m.tokensSaved || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-brand-gray-50 bg-pattern">
      {/* Header */}
      <Header 
        onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        currentView={currentView}
        isPolling={isPolling}
        hasProcessingDocuments={hasProcessingDocuments}
      />

      <div className="flex h-[calc(100vh-4rem)]">
        {/* Sidebar */}
        <div className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed inset-y-0 left-0 top-16 z-50 w-64 bg-white border-r border-brand-gray-200 shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0`}>
          
          {/* Sidebar Header */}
          <div className="p-6 border-b border-brand-gray-200">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-brand-blue-600 rounded-lg">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-serif text-xl font-bold text-brand-gray-900">Legal AI</h2>
                <p className="text-sm text-brand-gray-600">Your AI Stays Home</p>
              </div>
            </div>
            
            {/* Dashboard Button - Disabled for now */}
            <button
              onClick={() => showInfo('Coming Soon', 'Dashboard feature will be available in the next update')}
              className={`w-full flex items-center justify-center px-4 py-3 bg-brand-blue-600 text-white rounded-lg 
                hover:bg-brand-blue-700 transition-all font-medium shadow-sm hover:shadow-md mb-3
                ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
            >
              <LayoutDashboard className="w-5 h-5 mr-2" />
              {getSimpleText('Dashboard')}
            </button>
            
            {/* New Case Button - Disabled for now */}
            <button
              onClick={() => showInfo('Coming Soon', 'Case intake feature will be available in the next update')}
              className={`w-full flex items-center justify-center px-4 py-3 bg-brand-blue-500 text-white rounded-lg 
                hover:bg-brand-blue-600 transition-all font-medium shadow-sm hover:shadow-md
                ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
            >
              <Plus className="w-5 h-5 mr-2" />
              {getSimpleText('New Case')}
            </button>
          </div>

          {/* Navigation */}
          <nav className="p-4 space-y-2">
        {sidebarItems.map((item) => {
          if (item.href) {
            return (
              <button
                key={item.id}
                onClick={() => showInfo('Coming Soon', 'This feature will be available in the next update')}
                className="w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all duration-200 group text-slate-600 hover:bg-slate-50 hover:text-slate-900 hover:shadow-sm hover:translate-x-1"
              >
                <div className="flex items-center space-x-3">
                  <item.icon className="w-5 h-5" />
                  <span className="font-medium">{getSimpleText(item.label)}</span>
                </div>
              </button>
            );
          }
          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.view) {
                  setCurrentView(item.view);
                  setSidebarOpen(false);
                }
              }}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all duration-200 group ${
                currentView === item.view
                  ? 'bg-brand-blue-50 text-brand-blue-700 border border-brand-blue-200 shadow-sm'
                  : 'text-brand-gray-600 hover:bg-brand-gray-50 hover:text-brand-gray-900 hover:shadow-sm hover:translate-x-1'
              }`}
            >
              <div className="flex items-center space-x-3">
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{getSimpleText(item.label)}</span>
              </div>
              {item.badge && (
                <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-600 rounded-full">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
          </nav>

          {/* Status */}
          <div className="absolute bottom-4 left-4 right-4">
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-green-700">{getSimpleText('AI Online')}</span>
              </div>
              <p className="text-xs text-green-600 mt-1">{isSimpleMode ? 'Ready to help' : 'AI system connected'}</p>
            </div>
            {/* Polling indicator in sidebar */}
            {hasProcessingDocuments && (
              <div className="mt-3 p-2 bg-blue-50 rounded-lg border border-blue-200">
                <InlinePollingIndicator isPolling={isPolling} />
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Content Area */}
          <main className="flex-1 overflow-auto">
            <Suspense fallback={
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                  <p className="text-gray-600">Loading...</p>
                </div>
              </div>
            }>
              {currentView === 'chat' && (
                <UnifiedChatInterface 
                  messages={chatMessages}
                  documents={documents}
                  onNewMessage={handleNewMessage}
                  isLoading={isLoading}
                  setIsLoading={setIsLoading}
                />
              )}
              
              {currentView === 'documents' && (
                isLoadingDocuments ? (
                  <div className="p-6 max-w-6xl mx-auto">
                    <div className="mb-6">
                      <div className="h-8 w-48 bg-slate-200 rounded animate-pulse mb-2"></div>
                      <div className="h-4 w-64 bg-slate-200 rounded animate-pulse"></div>
                    </div>
                    <DocumentListSkeleton />
                  </div>
                ) : (
                  <DocumentList 
                    documents={documents}
                    onRefresh={loadDocuments}
                    onDocumentSelect={(doc: Document) => {
                      setSelectedDocument(doc);
                    }}
                    onDocumentDelete={handleDocumentDelete}
                    isPolling={isPolling}
                    hasProcessingDocuments={hasProcessingDocuments}
                  />
                )
              )}
              
              {currentView === 'upload' && (
                <DocumentUpload 
                  onUploadComplete={(doc: Document) => handleDocumentUpload(doc)}
                  onViewChange={setCurrentView}
                />
              )}
            </Suspense>
          </main>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Document View Modal */}
      {selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-7xl max-h-[90vh] flex flex-col">
            <Suspense fallback={
              <div className="flex items-center justify-center h-96">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              </div>
            }>
              <DocumentView 
                document={selectedDocument}
                onBack={() => setSelectedDocument(null)}
                onDelete={handleDocumentDelete}
              />
            </Suspense>
          </div>
        </div>
      )}
      
      {/* Offline Indicator */}
      <OfflineIndicator />
      
      {/* Welcome Overlay */}
      {showWelcome && (
        <Suspense fallback={null}>
          <WelcomeOverlay
            onClose={() => {
              setShowWelcome(false);
              localStorage.setItem('hasSeenWelcome', 'true');
            }}
            onStartDemo={handleWelcomeDemoStart}
          />
        </Suspense>
      )}
      
      {/* Demo Mode */}
      {!showWelcome && (
        <Suspense fallback={null}>
          <DemoMode
            onLoadSampleData={loadSampleData}
            isActive={demoMode}
            onToggle={setDemoMode}
          />
        </Suspense>
      )}
      
      {/* Success Celebration */}
      <Suspense fallback={null}>
        <SuccessCelebration
          show={showSuccessCelebration}
          message={celebrationMessage}
          onComplete={() => setShowSuccessCelebration(false)}
        />
      </Suspense>
      
      {/* Keyboard Shortcuts */}
      <Suspense fallback={null}>
        <KeyboardShortcuts
          isOpen={showShortcuts}
          onClose={() => setShowShortcuts(false)}
        />
      </Suspense>
      
      {/* Metrics Dashboard - Show in documents view */}
      {currentView === 'documents' && documents.length > 0 && (
        <div className="fixed bottom-20 left-4 right-4 md:left-auto md:right-4 md:w-96 z-30 animate-slide-up">
          <Suspense fallback={null}>
            <MetricsDashboard
              totalDocuments={documents.length}
              processedDocuments={processedDocuments}
              averageResponseTime={avgResponseTime || undefined}
              totalTokensSaved={totalTokensSaved || undefined}
              className="shadow-lifted"
            />
          </Suspense>
        </div>
      )}
    </div>
  );
}

export default App;
