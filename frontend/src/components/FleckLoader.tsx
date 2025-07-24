import React from 'react';
import { Shield, Zap, Brain, Lock } from 'lucide-react';
import { cn } from '../utils/cn';

interface FleckLoaderProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'shield' | 'intelligence' | 'beast' | 'fortress';
  message?: string;
  className?: string;
}

const FleckLoader: React.FC<FleckLoaderProps> = ({
  size = 'md',
  variant = 'shield',
  message,
  className
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24'
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-5 h-5',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12'
  };

  const getIcon = () => {
    switch (variant) {
      case 'intelligence':
        return <Brain className={iconSizes[size]} />;
      case 'beast':
        return <Zap className={iconSizes[size]} />;
      case 'fortress':
        return <Lock className={iconSizes[size]} />;
      default:
        return <Shield className={iconSizes[size]} />;
    }
  };

  const getAnimation = () => {
    switch (variant) {
      case 'intelligence':
        return 'intelligence-flow';
      case 'beast':
        return 'animate-shield-pulse beast-activate';
      case 'fortress':
        return 'animate-pulse-scale';
      default:
        return 'animate-shield-pulse';
    }
  };

  const getMessage = () => {
    if (message) return message;
    
    switch (variant) {
      case 'intelligence':
        return 'Extracting intelligence...';
      case 'beast':
        return 'Beast mode engaged...';
      case 'fortress':
        return 'Securing fortress...';
      default:
        return 'Processing...';
    }
  };

  return (
    <div className={cn('flex flex-col items-center justify-center space-y-4', className)}>
      {/* Main Loader */}
      <div className={cn(
        'relative flex items-center justify-center rounded-full',
        'bg-gradient-to-br from-brand-blue-500 to-brand-blue-700 text-white',
        sizeClasses[size],
        getAnimation()
      )}>
        {getIcon()}
        
        {/* Pulse Rings */}
        <div className="absolute inset-0 rounded-full border-2 border-brand-blue-400 animate-ping opacity-20"></div>
        <div className="absolute inset-0 rounded-full border border-brand-blue-300 animate-pulse"></div>
      </div>

      {/* Loading Message */}
      {(message !== null) && (
        <div className="text-center">
          <p className="text-sm font-medium text-brand-gray-700 animate-pulse">
            {getMessage()}
          </p>
          
          {/* Loading Dots */}
          <div className="flex justify-center space-x-1 mt-2">
            <div className="w-2 h-2 bg-brand-blue-500 rounded-full ai-thinking-dot"></div>
            <div className="w-2 h-2 bg-brand-blue-500 rounded-full ai-thinking-dot"></div>
            <div className="w-2 h-2 bg-brand-blue-500 rounded-full ai-thinking-dot"></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FleckLoader;

// Specialized loaders for different contexts
export const ShieldLoader: React.FC<Omit<FleckLoaderProps, 'variant'>> = (props) => (
  <FleckLoader {...props} variant="shield" />
);

export const IntelligenceLoader: React.FC<Omit<FleckLoaderProps, 'variant'>> = (props) => (
  <FleckLoader {...props} variant="intelligence" />
);

export const BeastLoader: React.FC<Omit<FleckLoaderProps, 'variant'>> = (props) => (
  <FleckLoader {...props} variant="beast" />
);

export const FortressLoader: React.FC<Omit<FleckLoaderProps, 'variant'>> = (props) => (
  <FleckLoader {...props} variant="fortress" />
);

// Inline loader for smaller spaces
export const InlineFleckLoader: React.FC<{ variant?: FleckLoaderProps['variant'] }> = ({ 
  variant = 'shield' 
}) => (
  <FleckLoader size="sm" variant={variant} message={undefined} className="inline-flex" />
);
