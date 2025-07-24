import React, { useState } from 'react';
import { 
  Bot, 
  User, 
  FileText, 
  Copy, 
  ThumbsUp, 
  ThumbsDown, 
  Zap, 
  Clock, 
  Info,
  Coins
} from 'lucide-react';
import { ResponseMetrics } from './MetricsDisplay';

export interface ChatMessageType {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: Array<{
    document_id: string;
    document_name: string;
    relevance: string;
  }>;
  responseType?: 'instant' | 'analyzed';
  responseTime?: number; // in milliseconds
  tokensSaved?: number;
}

interface ChatMessageProps {
  message: ChatMessageType;
  onCopy: (text: string) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, onCopy }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatResponseTime = (ms?: number) => {
    if (!ms) return null;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const isInstant = message.responseType === 'instant';
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group animate-slide-up`}>
      <div className={`max-w-3xl ${isUser ? 'order-2' : ''}`}>
        {/* Message Header */}
        <div className={`flex items-center space-x-2 mb-1 ${
          isUser ? 'justify-end' : 'justify-start'
        }`}>
          {!isUser && <Bot className="w-4 h-4 text-blue-600" />}
          <span className="text-xs font-medium text-slate-600">
            {isUser ? 'You' : 'Legal AI'}
          </span>
          
          {/* Instant Badge and Response Info */}
          {!isUser && isInstant && (
            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-200">
                <Zap className="w-3 h-3 mr-1" />
                Instant
              </span>
              
              {/* Info Icon with Tooltip */}
              <div className="relative">
                <button
                  onMouseEnter={() => setShowTooltip(true)}
                  onMouseLeave={() => setShowTooltip(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <Info className="w-3 h-3" />
                </button>
                
                {showTooltip && (
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 bg-slate-900 text-white text-xs rounded-lg shadow-lg z-10">
                    <div className="font-semibold mb-1">Instant Response</div>
                    <p>This response uses cached metadata for faster answers. Full document analysis provides more detailed insights.</p>
                    <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 rotate-45 w-2 h-2 bg-slate-900"></div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          <span className="text-xs text-slate-400">
            {formatTimestamp(message.timestamp)}
          </span>
          {isUser && <User className="w-4 h-4 text-slate-600" />}
        </div>

        {/* Response Metrics */}
        {!isUser && (message.responseTime || message.tokensSaved || isInstant) && (
          <ResponseMetrics
            responseTime={message.responseTime ? message.responseTime / 1000 : undefined}
            tokensSaved={message.tokensSaved}
            isInstant={isInstant}
            className="mb-2"
          />
        )}

        {/* Message Content */}
        <div className={`p-4 rounded-lg ${
          isUser
            ? 'bg-blue-600 text-white'
            : isInstant
            ? 'bg-gradient-to-r from-purple-50 to-indigo-50 text-slate-900 border border-purple-200'
            : 'bg-slate-50 text-slate-900 border border-slate-200'
        }`}>
          <div className="whitespace-pre-wrap">{message.content}</div>
          
          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className={`mt-3 pt-3 border-t ${
              isInstant ? 'border-purple-200' : 'border-slate-200'
            }`}>
              <p className={`text-xs font-medium mb-2 ${
                isInstant ? 'text-purple-700' : 'text-slate-600'
              }`}>
                Referenced Documents:
              </p>
              <div className="space-y-1">
                {message.sources.map((source, index) => (
                  <div key={index} className="flex items-center space-x-2 text-xs">
                    <FileText className={`w-3 h-3 ${
                      isInstant ? 'text-purple-500' : 'text-slate-500'
                    }`} />
                    <span className={isInstant ? 'text-purple-700' : 'text-slate-600'}>
                      {source.document_name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Message Actions */}
        {!isUser && (
          <div className="flex items-center space-x-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => onCopy(message.content)}
              className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-700"
              title="Copy message"
            >
              <Copy className="w-3 h-3" />
            </button>
            <button className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-green-600">
              <ThumbsUp className="w-3 h-3" />
            </button>
            <button className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-red-600">
              <ThumbsDown className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
