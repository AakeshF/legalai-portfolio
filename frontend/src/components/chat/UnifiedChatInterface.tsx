import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, FileText, Zap, ChevronDown, DollarSign, Clock, Shield, AlertCircle } from 'lucide-react';
import ChatMessage from '../ChatMessage';
import { TypingIndicator } from '../LoadingStates';
import { ResponseMetrics } from '../MetricsDisplay';
import { WebSocketStatusIndicator } from '../WebSocketStatusIndicator';
import { useAIPreferences } from '../../contexts/AIPreferencesContext';
import { useAuth } from '../../contexts/MockAuthContext';
import { chatService } from '../../services/chat.service';
import { websocketService } from '../../services/websocket.service';
import type { AIProvider } from '../ai-config/types';
import { AI_PROVIDERS, AI_MODELS } from '../ai-config/types';
import { Toast } from '../Toast';
import { useIntegratedAnonymization } from '../../hooks/useIntegratedAnonymization';
import { SensitiveDataConsentModal } from '../anonymization/SensitiveDataConsentModal';
import { detectSensitiveData } from '../anonymization/SensitiveDataDetector';
import type { AnonymizationResult, RedactedSegment } from '../../types/anonymization';

// Proper TypeScript interfaces - no `any` types
interface Document {
  id: string | number;
  filename: string;
  file_size?: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  upload_timestamp?: string;
  created_at?: string;
  summary?: string;
  metadata?: DocumentMetadata;
  legal_metadata?: LegalMetadata;
  extracted_entities?: ExtractedEntity[];
  ai_analysis?: AIAnalysis;
}

interface DocumentMetadata {
  document_type?: string;
  case_number?: string;
  jurisdiction?: string;
  parties?: Party[];
  dates?: DateInfo[];
  money_amounts?: MoneyAmount[];
  key_terms?: string[];
  obligations?: string[];
}

interface LegalMetadata {
  document_type?: string;
  parties?: Party[];
  money_amounts?: MoneyAmount[];
  dates?: DateInfo[];
  risk_indicators?: RiskIndicator[];
  key_terms?: string[];
  risk_score?: number;
}

interface Party {
  name: string;
  role: string;
  type?: 'individual' | 'organization';
}

interface DateInfo {
  date: string;
  type: string;
  description?: string;
}

interface MoneyAmount {
  amount: number;
  currency: string;
  context: string;
}

interface RiskIndicator {
  category: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
}

interface ExtractedEntity {
  type: string;
  value: string;
  confidence: number;
}

interface AIAnalysis {
  summary?: string;
  key_points?: string[];
  risk_assessment?: string;
  recommendations?: string[];
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
  sources?: MessageSource[];
  responseType?: 'instant' | 'analyzed';
  responseTime?: number;
  tokensSaved?: number;
  status?: 'pending_review' | 'blocked' | 'error' | 'completed';
  reviewId?: string;
}

interface MessageSource {
  document_id: string;
  document_name: string;
  relevance: string;
}

interface ChatConfig {
  enableAnonymization: boolean;
  enableMultiProvider: boolean;
  enableCostTracking: boolean;
  enableWebSocket: boolean;
  enableMessagePersistence: boolean;
}

interface ConsentDetails {
  detectedTypes: string[];
  segments: RedactedSegment[];
  requiresReview: boolean;
}

interface UnifiedChatInterfaceProps {
  messages: ChatMessageType[];
  documents: Document[];
  onNewMessage: (message: ChatMessageType) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  config?: Partial<ChatConfig>;
  sessionId?: string;
}

const DEFAULT_CONFIG: ChatConfig = {
  enableAnonymization: true,
  enableMultiProvider: true,
  enableCostTracking: true,
  enableWebSocket: true,
  enableMessagePersistence: true,
};

const UnifiedChatInterface: React.FC<UnifiedChatInterfaceProps> = ({
  messages,
  documents,
  onNewMessage,
  isLoading,
  setIsLoading,
  config = {},
  sessionId = 'default-session'
}) => {
  // Merge config with defaults
  const activeConfig = { ...DEFAULT_CONFIG, ...config };
  
  // State management
  const [inputValue, setInputValue] = useState('');
  const [showProviderSelector, setShowProviderSelector] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<AIProvider>('openai');
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4-turbo');
  const [estimatedCost, setEstimatedCost] = useState<number>(0);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [responseStartTime, setResponseStartTime] = useState<number | null>(null);
  
  // Anonymization state
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [consentDetails, setConsentDetails] = useState<ConsentDetails | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState('');
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  
  // Refs and hooks
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { effectiveSettings } = useAIPreferences();
  const { processPrompt, handleIntegratedResponse } = useIntegratedAnonymization();

  // Effects
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (effectiveSettings) {
      // Ensure the provider is valid, fallback to 'ollama' if not
      const provider = effectiveSettings.provider as AIProvider;
      const validProvider = AI_PROVIDERS[provider] ? provider : 'ollama';
      setSelectedProvider(validProvider);
      setSelectedModel(effectiveSettings.model || 'llama3.1');
    }
  }, [effectiveSettings]);

  useEffect(() => {
    if (inputValue && activeConfig.enableCostTracking) {
      const estimatedTokens = Math.ceil(inputValue.length / 4);
      const model = AI_MODELS.find(m => m.id === selectedModel);
      if (model) {
        const inputCost = (estimatedTokens / 1000) * model.costPer1kTokens.input;
        const estimatedOutputTokens = estimatedTokens * 3;
        const outputCost = (estimatedOutputTokens / 1000) * model.costPer1kTokens.output;
        setEstimatedCost(inputCost + outputCost);
      }
    } else {
      setEstimatedCost(0);
    }
  }, [inputValue, selectedModel, activeConfig.enableCostTracking]);

  // WebSocket effects
  useEffect(() => {
    if (activeConfig.enableWebSocket) {
      const unsubscribe = websocketService.onStatusChange((status) => {
        setWsConnected(status === 'connected');
      });

      // Listen for real-time messages
      const unsubscribeMessages = websocketService.on('chat_message', (message) => {
        if (message.data.sessionId === sessionId) {
          const chatMessage: ChatMessageType = {
            id: message.data.id,
            role: message.data.role,
            content: message.data.content,
            timestamp: message.data.timestamp,
            metadata: message.data.metadata,
            sources: message.data.sources
          };
          onNewMessage(chatMessage);
        }
      });

      return () => {
        unsubscribe();
        unsubscribeMessages();
      };
    }
  }, [activeConfig.enableWebSocket, sessionId, onNewMessage]);

  // Helper functions
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleProviderChange = (provider: AIProvider, modelId: string) => {
    setSelectedProvider(provider);
    setSelectedModel(modelId);
    setShowProviderSelector(false);
    
    const providerName = AI_PROVIDERS[provider].name;
    const modelName = AI_MODELS.find(m => m.id === modelId)?.name || modelId;
    setToastMessage(`Switched to ${providerName} - ${modelName}`);
    setShowToast(true);
  };

  const persistMessage = async (message: ChatMessageType) => {
    if (activeConfig.enableMessagePersistence) {
      try {
        // Note: Message persistence would be handled by backend
      } catch (error) {
        console.error('Failed to persist message:', error);
      }
    }
  };

  const handleSubmit = async (promptText?: string) => {
    const textToSubmit = promptText || inputValue;
    if (!textToSubmit.trim() || isLoading) return;

    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      role: 'user',
      content: textToSubmit,
      timestamp: new Date().toISOString(),
      metadata: activeConfig.enableCostTracking ? {
        provider_used: selectedProvider,
        model: selectedModel,
        audit_id: `user-${Date.now()}`,
        response_time_ms: 0,
        tokens_used: 0,
        cost: 0
      } : undefined
    };

    onNewMessage(userMessage);
    await persistMessage(userMessage);
    setInputValue('');
    setIsLoading(true);
    setResponseStartTime(Date.now());

    // Handle anonymization if enabled
    if (activeConfig.enableAnonymization) {
      const sensitiveDataResult = detectSensitiveData(textToSubmit);
      const hasSensitiveData = sensitiveDataResult && sensitiveDataResult.segments.length > 0;
      
      if (hasSensitiveData) {
        setPendingPrompt(textToSubmit);
        setConsentDetails({
          detectedTypes: sensitiveDataResult.detectedSensitiveTypes,
          segments: sensitiveDataResult.segments,
          requiresReview: true
        });
        setShowConsentModal(true);
        setIsLoading(false);
        return;
      }
    }

    await processMessage(textToSubmit, userMessage);
  };

  const processMessage = async (text: string, userMessage: ChatMessageType) => {
    try {
      let response;
      
      if (activeConfig.enableAnonymization) {
        // Use integrated anonymization endpoint
        response = await processPrompt(text, {
          context: {
            documentIds: documents.map(d => d.id.toString())
          }
        });
        
        await handleIntegratedResponse(response, {
          onSuccess: (data) => {
            createAssistantMessage(data, userMessage);
          },
          onConsentRequired: (details) => {
            setConsentDetails(details);
            setShowConsentModal(true);
          },
          onPendingReview: (id) => {
            setReviewId(id);
            const pendingMessage: ChatMessageType = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: 'Your prompt contains sensitive information and is being reviewed by an administrator. You\'ll be notified once the review is complete.',
              timestamp: new Date().toISOString(),
              status: 'pending_review',
              reviewId: id
            };
            onNewMessage(pendingMessage);
            persistMessage(pendingMessage);
          },
          onBlocked: (message) => {
            setBlockedMessage(message);
            const blockedMsg: ChatMessageType = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: message,
              timestamp: new Date().toISOString(),
              status: 'blocked'
            };
            onNewMessage(blockedMsg);
            persistMessage(blockedMsg);
          }
        });
      } else {
        // Use regular chat service
        response = await chatService.sendMessage(text, sessionId);
        createAssistantMessage(response, userMessage);
      }
    } catch (error) {
      const errorMessage: ChatMessageType = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        timestamp: new Date().toISOString(),
        status: 'error'
      };
      onNewMessage(errorMessage);
      await persistMessage(errorMessage);
    } finally {
      setIsLoading(false);
      setResponseStartTime(null);
    }
  };

  const createAssistantMessage = async (data: any, userMessage: ChatMessageType) => {
    const responseTime = responseStartTime ? Date.now() - responseStartTime : 0;
    
    const assistantMessage: ChatMessageType = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: data.response || data.message || data.content || 'No response content found',
      timestamp: data.timestamp || new Date().toISOString(),
      metadata: activeConfig.enableCostTracking ? {
        provider_used: data.provider_used || selectedProvider,
        model: data.model || selectedModel,
        audit_id: data.audit_id,
        response_time_ms: responseTime,
        tokens_used: data.tokens_used,
        cost: data.estimated_cost
      } : undefined,
      sources: data.sources,
      responseType: data.response_type || 'analyzed',
      responseTime: responseTime,
      tokensSaved: data.tokens_saved,
      status: 'completed'
    };

    onNewMessage(assistantMessage);
    await persistMessage(assistantMessage);

    // Send via WebSocket if enabled
    if (activeConfig.enableWebSocket && wsConnected) {
      websocketService.send('chat_message', {
        sessionId,
        message: assistantMessage
      });
    }
  };

  const handleConsentConfirm = async (consent: any) => {
    setShowConsentModal(false);
    await processMessage(pendingPrompt, {
      id: Date.now().toString(),
      role: 'user',
      content: pendingPrompt,
      timestamp: new Date().toISOString()
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setToastMessage('Copied to clipboard');
      setShowToast(true);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  // Client-side sensitive data preview
  const sensitiveDataResult: AnonymizationResult | null = activeConfig.enableAnonymization && inputValue 
    ? detectSensitiveData(inputValue) 
    : null;
  const hasSensitiveData = sensitiveDataResult && sensitiveDataResult.segments.length > 0;

  // Ensure selectedProvider is valid, fallback to 'ollama' if not
  const validProvider = AI_PROVIDERS[selectedProvider] ? selectedProvider : 'ollama';
  const filteredModels = AI_MODELS.filter(model => model.provider === validProvider);
  const currentModel = AI_MODELS.find(m => m.id === selectedModel);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Chat Header */}
      <div className="border-b border-slate-200 p-4 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">Legal AI Legal AI Assistant</h2>
              <p className="text-sm text-slate-600">
                {documents.length > 0 
                  ? `Ready to analyze ${documents.length} document${documents.length !== 1 ? 's' : ''}`
                  : 'Upload documents to get started'
                }
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* WebSocket Status */}
            {activeConfig.enableWebSocket && <WebSocketStatusIndicator />}
            
            {documents.length > 0 && (
              <div className="flex items-center space-x-2 text-sm text-slate-600">
                <FileText className="w-4 h-4" />
                <span>{documents.length} docs available</span>
              </div>
            )}
            
            {/* Provider Selector */}
            {activeConfig.enableMultiProvider && (
              <div className="relative">
                <button
                  onClick={() => setShowProviderSelector(!showProviderSelector)}
                  className="flex items-center space-x-2 px-3 py-2 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                >
                  <span className="text-lg">{AI_PROVIDERS[validProvider].icon}</span>
                  <div className="text-left">
                    <p className="text-sm font-medium text-gray-900">{AI_PROVIDERS[validProvider].name}</p>
                    <p className="text-xs text-gray-500">{currentModel?.name}</p>
                  </div>
                  <ChevronDown className="h-4 w-4 text-gray-400" />
                </button>
                
                {showProviderSelector && (
                  <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                    <div className="p-4">
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">Select AI Provider</h3>
                      
                      {Object.entries(AI_PROVIDERS).map(([key, provider]) => (
                        <div key={key} className="mb-3">
                          <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                            <span className="mr-2">{provider.icon}</span>
                            {provider.name}
                          </h4>
                          <div className="space-y-1">
                            {AI_MODELS.filter(m => m.provider === key).map(model => (
                              <button
                                key={model.id}
                                onClick={() => handleProviderChange(key as AIProvider, model.id)}
                                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                                  selectedModel === model.id
                                    ? 'bg-blue-50 text-blue-700 font-medium'
                                    : 'hover:bg-gray-50 text-gray-700'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span>{model.name}</span>
                                  {activeConfig.enableCostTracking && (
                                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                                      <span>${model.costPer1kTokens.input}/1k</span>
                                      <span>{Math.round(model.contextWindow / 1000)}k ctx</span>
                                    </div>
                                  )}
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    {activeConfig.enableCostTracking && (
                      <div className="border-t border-gray-200 p-4 bg-gray-50">
                        <div className="flex items-center justify-between text-xs text-gray-600">
                          <span>Est. cost for this message:</span>
                          <span className="font-medium">${estimatedCost.toFixed(4)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Security Status Indicators */}
      {activeConfig.enableAnonymization && (
        <>
          {hasSensitiveData && (
            <div className="px-4 py-2 bg-amber-50 border-b border-amber-200">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-amber-600" />
                <span className="text-sm text-amber-700">
                  Sensitive data detected. It will be handled securely.
                </span>
              </div>
            </div>
          )}

          {reviewId && (
            <div className="px-4 py-3 bg-blue-50 border-b border-blue-200">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-600 animate-spin" />
                <span className="text-sm text-blue-700">
                  Your prompt is under security review...
                </span>
              </div>
            </div>
          )}

          {blockedMessage && (
            <div className="px-4 py-3 bg-red-50 border-b border-red-200">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600" />
                <span className="text-sm text-red-700">{blockedMessage}</span>
              </div>
            </div>
          )}
        </>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Bot className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-600 mb-2">
              Welcome to Legal AI Legal AI Assistant
            </h3>
            <p className="text-slate-500 max-w-md mx-auto">
              I'm here to help you analyze legal documents, review contracts, and provide professional insights. 
              {documents.length === 0 
                ? ' Start by uploading some documents or ask me a general legal question.'
                : ' Ask me anything about your uploaded documents!'
              }
            </p>
            
            {/* Suggested Questions */}
            <div className="mt-6 max-w-lg mx-auto">
              <p className="text-sm font-medium text-slate-600 mb-3">Try asking:</p>
              <div className="grid gap-2">
                {(documents.length > 0 ? [
                  "What type of documents did I upload?",
                  "Summarize the key points in my documents",
                  "Are there any potential legal issues?"
                ] : [
                  "How can you help me with legal documents?",
                  "What types of contracts can you analyze?",
                  "What should I look for in a lease agreement?"
                ]).map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setInputValue(question)}
                    className="text-left p-3 bg-slate-50 hover:bg-slate-100 rounded-lg text-sm text-slate-700 transition-colors"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} className="animate-fade-in">
                <ChatMessage
                  message={message}
                  onCopy={copyToClipboard}
                />
                
                {/* Show metadata for assistant messages */}
                {message.role === 'assistant' && message.metadata && (
                  <div className="flex items-center space-x-4 mt-2 ml-12 text-xs text-gray-500">
                    {activeConfig.enableMultiProvider && message.metadata.provider_used && AI_PROVIDERS[message.metadata.provider_used] && (
                      <span className="flex items-center space-x-1">
                        <span>{AI_PROVIDERS[message.metadata.provider_used].icon}</span>
                        <span>{message.metadata.model}</span>
                      </span>
                    )}
                    {message.metadata.response_time_ms && (
                      <span className="flex items-center space-x-1">
                        <Clock className="h-3 w-3" />
                        <span>{(message.metadata.response_time_ms / 1000).toFixed(1)}s</span>
                      </span>
                    )}
                    {message.metadata.tokens_used && (
                      <span>{message.metadata.tokens_used.toLocaleString()} tokens</span>
                    )}
                    {activeConfig.enableCostTracking && message.metadata.cost && (
                      <span className="flex items-center space-x-1">
                        <DollarSign className="h-3 w-3" />
                        <span>${message.metadata.cost.toFixed(4)}</span>
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="animate-fade-in">
                <TypingIndicator />
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Response Metrics */}
      {responseStartTime && (
        <div className="px-4 py-2 border-t border-slate-200 bg-slate-50">
          <ResponseMetrics 
            processingTime={(Date.now() - responseStartTime) / 1000}
            isInstant={false}
          />
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-slate-200 p-4 bg-white">
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={documents.length > 0 
                ? "Ask me about your documents..." 
                : "Type your legal question here..."
              }
              className="w-full px-4 py-3 pr-12 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none h-12"
              rows={1}
              disabled={isLoading}
            />
            
            {/* Estimated Cost Display */}
            {activeConfig.enableCostTracking && inputValue && estimatedCost > 0 && (
              <div className="absolute right-12 top-1/2 transform -translate-y-1/2 text-xs text-gray-500">
                ~${estimatedCost.toFixed(4)}
              </div>
            )}
          </div>
          
          <button
            onClick={() => handleSubmit()}
            disabled={!inputValue.trim() || isLoading}
            className={`px-6 py-3 rounded-lg font-medium transition-all flex items-center space-x-2
              ${!inputValue.trim() || isLoading
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
              }`}
          >
            {activeConfig.enableAnonymization && hasSensitiveData && <Shield className="w-4 h-4" />}
            <Send className="w-5 h-5" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </div>
        
        {/* Quick Actions */}
        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center space-x-2 text-xs text-slate-500">
            <button className="flex items-center space-x-1 hover:text-slate-700 transition-colors">
              <Zap className="w-3 h-3" />
              <span>Smart Mode</span>
            </button>
          </div>
          
          <span className="text-xs text-slate-500">
            Press Enter to send, Shift+Enter for new line
          </span>
        </div>
      </div>

      {/* Consent Modal */}
      {activeConfig.enableAnonymization && showConsentModal && consentDetails && (
        <SensitiveDataConsentModal
          isOpen={showConsentModal}
          onClose={() => {
            setShowConsentModal(false);
            setConsentDetails(null);
            setPendingPrompt('');
            setIsLoading(false);
          }}
          onConfirm={handleConsentConfirm}
          detectedSensitiveTypes={sensitiveDataResult?.detectedSensitiveTypes || []}
          segments={sensitiveDataResult?.segments || []}
          model={selectedModel}
        />
      )}

      {/* Toast Notification */}
      {showToast && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
};

export default UnifiedChatInterface;
