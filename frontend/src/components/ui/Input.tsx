import React from 'react';
import { cn } from '../../utils/cn';
import { AlertCircle, CheckCircle } from 'lucide-react';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  variant?: 'default' | 'error' | 'success';
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  error?: string;
  success?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  helperText?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(({
  className,
  variant = 'default',
  size = 'md',
  label,
  error,
  success,
  leftIcon,
  rightIcon,
  helperText,
  type = 'text',
  placeholder,
  disabled,
  ...props
}, ref) => {
  const hasError = error || variant === 'error';
  const hasSuccess = success || variant === 'success';
  const hasLeftIcon = leftIcon;
  const hasRightIcon = rightIcon || hasError || hasSuccess;

  const baseStyles = 'w-full rounded-lg border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-60 disabled:cursor-not-allowed input-focus';
  
  const variants = {
    default: 'border-brand-gray-300 bg-white text-brand-gray-900 placeholder-brand-gray-500 focus:border-brand-blue-500 focus:ring-brand-blue-500/20',
    error: 'border-red-500 bg-red-50 text-red-900 placeholder-red-400 focus:border-red-500 focus:ring-red-500/20',
    success: 'border-green-500 bg-green-50 text-green-900 placeholder-green-400 focus:border-green-500 focus:ring-green-500/20'
  };

  const sizes = {
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2.5 text-base',
    lg: 'px-5 py-3.5 text-lg'
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  const paddingWithIcons = {
    sm: {
      left: hasLeftIcon ? 'pl-9' : '',
      right: hasRightIcon ? 'pr-9' : ''
    },
    md: {
      left: hasLeftIcon ? 'pl-11' : '',
      right: hasRightIcon ? 'pr-11' : ''
    },
    lg: {
      left: hasLeftIcon ? 'pl-14' : '',
      right: hasRightIcon ? 'pr-14' : ''
    }
  };

  // Hunter S. Thompson inspired placeholders
  const getPlaceholder = () => {
    if (placeholder) return placeholder;
    
    switch (type) {
      case 'email':
        return 'Your digital coordinates...';
      case 'password':
        return 'Your secret weapon...';
      case 'search':
        return 'Hunt for intelligence...';
      case 'text':
      default:
        return 'Unleash your query...';
    }
  };

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-brand-gray-900">
          {label}
        </label>
      )}
      
      <div className="relative">
        {/* Left Icon */}
        {hasLeftIcon && (
          <div className={cn(
            'absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none',
            hasError ? 'text-red-500' : hasSuccess ? 'text-green-500' : 'text-brand-gray-400'
          )}>
            <div className={iconSizes[size]}>
              {leftIcon}
            </div>
          </div>
        )}

        {/* Input */}
        <input
          ref={ref}
          type={type}
          placeholder={getPlaceholder()}
          disabled={disabled}
          className={cn(
            baseStyles,
            variants[hasError ? 'error' : hasSuccess ? 'success' : 'default'],
            sizes[size],
            paddingWithIcons[size].left,
            paddingWithIcons[size].right,
            className
          )}
          {...props}
        />

        {/* Right Icon */}
        {hasRightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <div className={cn(
              iconSizes[size],
              hasError ? 'text-red-500' : hasSuccess ? 'text-green-500' : 'text-brand-gray-400'
            )}>
              {hasError ? (
                <AlertCircle className="w-full h-full" />
              ) : hasSuccess ? (
                <CheckCircle className="w-full h-full" />
              ) : (
                rightIcon
              )}
            </div>
          </div>
        )}
      </div>

      {/* Helper Text / Error / Success Messages */}
      {(helperText || error || success) && (
        <div className="space-y-1">
          {error && (
            <p className="text-sm text-red-600 font-medium animate-slide-in-right">
              ⚠️ {error}
            </p>
          )}
          {success && (
            <p className="text-sm text-green-600 font-medium animate-slide-in-right">
              ✓ {success}
            </p>
          )}
          {helperText && !error && !success && (
            <p className="text-sm text-brand-gray-500">
              {helperText}
            </p>
          )}
        </div>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
