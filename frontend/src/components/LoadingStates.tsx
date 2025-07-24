import React from 'react';
import { FileText, Sparkles } from 'lucide-react';

export const DocumentCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 animate-fade-in">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3 flex-1">
          <div className="p-2 bg-slate-100 rounded-lg animate-pulse">
            <div className="w-5 h-5 bg-slate-200 rounded"></div>
          </div>
          <div className="flex-1">
            <div className="h-5 bg-slate-200 rounded w-3/4 mb-2 animate-pulse"></div>
            <div className="h-4 bg-slate-100 rounded w-1/4 animate-pulse"></div>
          </div>
        </div>
        <div className="h-6 bg-slate-100 rounded-full w-20 animate-pulse"></div>
      </div>
      <div className="space-y-2">
        <div className="h-4 bg-slate-100 rounded w-full animate-pulse"></div>
        <div className="h-4 bg-slate-100 rounded w-5/6 animate-pulse"></div>
      </div>
    </div>
  );
};

export const ChatMessageSkeleton: React.FC = () => {
  return (
    <div className="flex items-start space-x-3 p-4 animate-fade-in">
      <div className="w-8 h-8 bg-blue-100 rounded-full animate-pulse flex items-center justify-center">
        <Sparkles className="w-4 h-4 text-blue-300" />
      </div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-slate-200 rounded w-3/4 animate-pulse"></div>
        <div className="h-4 bg-slate-200 rounded w-full animate-pulse"></div>
        <div className="h-4 bg-slate-200 rounded w-2/3 animate-pulse"></div>
      </div>
    </div>
  );
};

interface TypingIndicatorProps {
  className?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ className = '' }) => {
  return (
    <div className={`flex items-center space-x-2 p-4 ${className}`}>
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
      </div>
      <span className="text-sm text-slate-500">AI is thinking...</span>
    </div>
  );
};

interface BrandedSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const BrandedSpinner: React.FC<BrandedSpinnerProps> = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  return (
    <div className={`relative ${sizeClasses[size]} ${className}`}>
      <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full animate-spin"></div>
      <div className="absolute inset-1 bg-white rounded-full"></div>
      <div className="absolute inset-2 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full animate-pulse"></div>
    </div>
  );
};

interface ProgressBarProps {
  progress: number;
  showPercentage?: boolean;
  animated?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ 
  progress, 
  showPercentage = true, 
  animated = true,
  className = '' 
}) => {
  return (
    <div className={`w-full ${className}`}>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-600">Progress</span>
        {showPercentage && (
          <span className="text-sm font-medium text-slate-900">{Math.round(progress)}%</span>
        )}
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div 
          className={`h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500 ease-out relative ${
            animated ? 'animate-shimmer' : ''
          }`}
          style={{ width: `${progress}%` }}
        >
          {animated && (
            <div className="absolute inset-0 bg-white/20 animate-shimmer"></div>
          )}
        </div>
      </div>
    </div>
  );
};

interface LoadingCardProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
}

export const LoadingCard: React.FC<LoadingCardProps> = ({ title, subtitle, icon }) => {
  return (
    <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-8 text-center animate-fade-in">
      <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4 animate-pulse-scale">
        {icon || <FileText className="w-8 h-8 text-blue-600" />}
      </div>
      <h3 className="text-lg font-semibold text-slate-900 mb-2">{title}</h3>
      {subtitle && (
        <p className="text-sm text-slate-600">{subtitle}</p>
      )}
      <div className="mt-6">
        <BrandedSpinner size="md" className="mx-auto" />
      </div>
    </div>
  );
};

interface LoadingStatesProps {
  type: 'spinner' | 'card' | 'skeleton' | 'typing' | 'chat';
  title?: string;
  subtitle?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingStates: React.FC<LoadingStatesProps> = ({ 
  type, 
  title = 'Loading...', 
  subtitle,
  size = 'md',
  className = ''
}) => {
  switch (type) {
    case 'spinner':
      return <BrandedSpinner size={size} className={className} />;
    case 'card':
      return <LoadingCard title={title} subtitle={subtitle} />;
    case 'skeleton':
      return <DocumentCardSkeleton />;
    case 'chat':
      return <ChatMessageSkeleton />;
    case 'typing':
      return <TypingIndicator className={className} />;
    default:
      return <BrandedSpinner size={size} className={className} />;
  }
};