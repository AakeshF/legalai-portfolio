import React from 'react';
import { cn } from '../../utils/cn';
import { AlertCircle, CheckCircle } from 'lucide-react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  success?: string;
  helperText?: string;
  variant?: 'default' | 'error' | 'success';
  showCount?: boolean;
  maxLength?: number;
  minRows?: number;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({
  className,
  label,
  error,
  success,
  helperText,
  variant = 'default',
  showCount = false,
  maxLength,
  minRows = 3,
  placeholder,
  value,
  onChange,
  disabled,
  ...props
}, ref) => {
  const hasError = error || variant === 'error';
  const hasSuccess = success || variant === 'success';

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange?.(e);
  };

  const baseStyles = 'w-full rounded-lg border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-60 disabled:cursor-not-allowed resize-none input-focus';
  
  const variants = {
    default: 'border-brand-gray-300 bg-white text-brand-gray-900 placeholder-brand-gray-500 focus:border-brand-blue-500 focus:ring-brand-blue-500/20',
    error: 'border-red-500 bg-red-50 text-red-900 placeholder-red-400 focus:border-red-500 focus:ring-red-500/20',
    success: 'border-green-500 bg-green-50 text-green-900 placeholder-green-400 focus:border-green-500 focus:ring-green-500/20'
  };

  const padding = 'px-4 py-3';

  // Hunter S. Thompson inspired placeholder
  const getPlaceholder = () => {
    if (placeholder) return placeholder;
    return 'Unleash your thoughts... let the words flow like ammunition.';
  };

  // Calculate character count
  const characterCount = typeof value === 'string' ? value.length : 0;

  // Get character count message with attitude
  const getCountMessage = () => {
    if (!maxLength) {
      return `${characterCount} characters unleashed`;
    }
    
    const remaining = maxLength - characterCount;
    if (remaining <= 0) {
      return 'Maximum firepower reached';
    } else if (remaining <= 20) {
      return `${remaining} characters left in the chamber`;
    } else {
      return `${characterCount}/${maxLength} characters unleashed`;
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
        <textarea
          ref={ref}
          placeholder={getPlaceholder()}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          maxLength={maxLength}
          rows={props.rows || minRows}
          className={cn(
            baseStyles,
            variants[hasError ? 'error' : hasSuccess ? 'success' : 'default'],
            padding,
            className
          )}
          {...props}
        />

        {/* Status Icon */}
        {(hasError || hasSuccess) && (
          <div className="absolute top-3 right-3 pointer-events-none">
            {hasError ? (
              <AlertCircle className="w-5 h-5 text-red-500" />
            ) : (
              <CheckCircle className="w-5 h-5 text-green-500" />
            )}
          </div>
        )}
      </div>

      {/* Character Count */}
      {showCount && (
        <div className={cn(
          'text-xs font-medium',
          maxLength && characterCount >= maxLength ? 'text-red-600' : 
          maxLength && characterCount >= maxLength * 0.9 ? 'text-yellow-600' : 
          'text-brand-gray-500'
        )}>
          {getCountMessage()}
        </div>
      )}

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

Textarea.displayName = 'Textarea';

export default Textarea;
