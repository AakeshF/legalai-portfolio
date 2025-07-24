import React, { useState, useEffect } from 'react';
import { cn } from '../utils/cn';

// Enhanced Button with micro-interactions
interface FleckButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'beast';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

export const FleckButton: React.FC<FleckButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  children,
  onClick,
  disabled,
  ...props
}) => {
  const [isPressed, setIsPressed] = useState(false);
  const [showRipple, setShowRipple] = useState(false);

  const baseClasses = 'fleck-button relative font-semibold transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-gradient-to-r from-brand-blue-600 to-brand-blue-700 text-white hover:from-brand-blue-700 hover:to-brand-blue-800 focus:ring-brand-blue-500',
    secondary: 'bg-white text-brand-gray-700 border border-brand-gray-300 hover:bg-brand-gray-50 focus:ring-brand-blue-500',
    success: 'bg-gradient-to-r from-green-600 to-green-700 text-white hover:from-green-700 hover:to-green-800 focus:ring-green-500',
    danger: 'bg-gradient-to-r from-red-600 to-red-700 text-white hover:from-red-700 hover:to-red-800 focus:ring-red-500',
    beast: 'bg-gradient-to-r from-purple-600 to-indigo-700 text-white hover:from-purple-700 hover:to-indigo-800 focus:ring-purple-500 beast-activate'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm rounded-md',
    md: 'px-4 py-2 text-base rounded-lg',
    lg: 'px-6 py-3 text-lg rounded-xl'
  };

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || isLoading) return;
    
    // Trigger ripple effect
    setShowRipple(true);
    setTimeout(() => setShowRipple(false), 300);
    
    // Trigger press animation
    setIsPressed(true);
    setTimeout(() => setIsPressed(false), 150);
    
    // Execute command animation for beast mode
    if (variant === 'beast') {
      e.currentTarget.classList.add('command-execute');
      setTimeout(() => {
        e.currentTarget.classList.remove('command-execute');
      }, 400);
    }
    
    onClick?.(e);
  };

  return (
    <button
      className={cn(
        baseClasses,
        variants[variant],
        sizes[size],
        isPressed && 'scale-95',
        showRipple && 'animate-pulse',
        className
      )}
      onClick={handleClick}
      disabled={disabled || isLoading}
      {...props}
    >
      {/* Ripple effect */}
      {showRipple && (
        <span className="absolute inset-0 rounded-lg bg-white opacity-30 animate-ping"></span>
      )}
      
      {/* Loading state */}
      {isLoading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <div className="premium-loader"></div>
        </span>
      )}
      
      {/* Content */}
      <span className={cn('relative z-10', isLoading && 'opacity-0')}>
        {children}
      </span>
    </button>
  );
};

// Enhanced Card with sophisticated interactions
interface FleckCardProps {
  children: React.ReactNode;
  className?: string;
  isInteractive?: boolean;
  onHover?: () => void;
  onClick?: () => void;
}

export const FleckCard: React.FC<FleckCardProps> = ({
  children,
  className,
  isInteractive = false,
  onHover,
  onClick
}) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={cn(
        'fleck-card rounded-xl p-6 bg-white shadow-soft',
        isInteractive && 'cursor-pointer hover-lift',
        isHovered && 'shadow-lifted',
        className
      )}
      onMouseEnter={() => {
        setIsHovered(true);
        onHover?.();
      }}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {children}
      
      {/* Hover effect overlay */}
      {isHovered && isInteractive && (
        <div className="absolute inset-0 bg-gradient-to-br from-brand-blue-50 to-purple-50 opacity-30 rounded-xl animate-fade-in"></div>
      )}
    </div>
  );
};

// Status Badge with personality
interface StatusBadgeProps {
  status: 'beast-mode' | 'crushing' | 'dominated' | 'fortress' | 'ready';
  children: React.ReactNode;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  children,
  className
}) => {
  const statusClasses = {
    'beast-mode': 'status-beast-mode',
    'crushing': 'status-crushing',
    'dominated': 'status-dominated',
    'fortress': 'bg-gradient-to-r from-gray-600 to-gray-700 text-white',
    'ready': 'bg-gradient-to-r from-brand-blue-500 to-brand-blue-600 text-white'
  };

  return (
    <span className={cn(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
      statusClasses[status],
      className
    )}>
      {children}
    </span>
  );
};

// Interactive Progress Bar
interface ProgressBarProps {
  progress: number;
  variant?: 'intelligence' | 'processing' | 'domination';
  showPercentage?: boolean;
  label?: string;
  className?: string;
}

export const FleckProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  variant = 'intelligence',
  showPercentage = true,
  label,
  className
}) => {
  const [animatedProgress, setAnimatedProgress] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedProgress(progress);
    }, 100);
    return () => clearTimeout(timer);
  }, [progress]);

  const variants = {
    intelligence: 'from-brand-blue-500 to-brand-blue-600',
    processing: 'from-yellow-500 to-orange-500',
    domination: 'from-purple-500 to-indigo-600'
  };

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <div className="flex justify-between text-sm font-medium text-brand-gray-700 mb-2">
          <span>{label}</span>
          {showPercentage && <span>{Math.round(progress)}%</span>}
        </div>
      )}
      
      <div className="w-full bg-brand-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={cn(
            'h-full bg-gradient-to-r transition-all duration-700 ease-out relative',
            variants[variant],
            variant === 'processing' && 'intelligence-flow'
          )}
          style={{ width: `${animatedProgress}%` }}
        >
          {/* Shimmer effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
        </div>
      </div>
    </div>
  );
};

// Notification Toast with Legal AI styling
interface FleckToastProps {
  type: 'success' | 'error' | 'warning' | 'info' | 'beast';
  message: string;
  description?: string;
  isVisible: boolean;
  onClose: () => void;
}

export const FleckToast: React.FC<FleckToastProps> = ({
  type,
  message,
  description,
  isVisible,
  onClose
}) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  const typeStyles = {
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    beast: 'bg-purple-50 border-purple-200 text-purple-800 beast-activate'
  };

  if (!isVisible) return null;

  return (
    <div className={cn(
      'fixed top-4 right-4 max-w-md w-full bg-white rounded-lg shadow-lifted border-l-4 p-4 z-50',
      'animate-slide-in-right',
      typeStyles[type]
    )}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h4 className="font-semibold text-gonzo">{message}</h4>
          {description && (
            <p className="mt-1 text-sm opacity-90">{description}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="ml-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          ×
        </button>
      </div>
    </div>
  );
};
