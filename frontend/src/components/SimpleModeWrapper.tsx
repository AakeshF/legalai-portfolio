import React from 'react';
import { useSimpleMode } from '../contexts/SimpleModeContext';

interface SimpleModeWrapperProps {
  children: React.ReactNode;
  className?: string;
}

export const SimpleModeWrapper: React.FC<SimpleModeWrapperProps> = ({ children, className = '' }) => {
  const { isSimpleMode } = useSimpleMode();
  
  return (
    <div className={`simple-mode-wrapper ${isSimpleMode ? 'simple-mode-active' : ''} ${className}`}>
      {children}
    </div>
  );
};

// Button component that respects Simple Mode
interface SimpleModeButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export const SimpleModeButton: React.FC<SimpleModeButtonProps> = ({ 
  variant = 'primary', 
  size = 'md',
  children,
  className = '',
  ...props 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const baseClasses = 'font-semibold rounded-lg transition-all duration-200 flex items-center justify-center';
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-4 focus:ring-blue-300',
    secondary: 'bg-gray-200 text-gray-700 hover:bg-gray-300 focus:ring-4 focus:ring-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-4 focus:ring-red-300',
  };
  
  const sizeClasses = {
    sm: isSimpleMode ? 'px-4 py-2 text-base min-h-[44px]' : 'px-3 py-1.5 text-sm',
    md: isSimpleMode ? 'px-6 py-3 text-lg min-h-[48px]' : 'px-4 py-2 text-base',
    lg: isSimpleMode ? 'px-8 py-4 text-xl min-h-[56px]' : 'px-6 py-3 text-lg',
  };
  
  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {typeof children === 'string' ? getSimpleText(children) : children}
    </button>
  );
};

// Input component that respects Simple Mode
interface SimpleModeInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'as'> {
  label?: string;
  error?: string;
  as?: 'input' | 'textarea';
  rows?: number;
}

export const SimpleModeInput: React.FC<SimpleModeInputProps> = ({ 
  label, 
  error,
  className = '',
  placeholder,
  as = 'input',
  rows = 4,
  ...props 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const inputClasses = `w-full rounded-lg border ${error ? 'border-red-500' : 'border-gray-300'} 
    ${isSimpleMode ? 'px-4 py-3 text-lg min-h-[48px]' : 'px-3 py-2 text-base'} 
    focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`;
  
  return (
    <div className="space-y-2">
      {label && (
        <label className={`block font-medium ${isSimpleMode ? 'text-lg' : 'text-sm'} text-gray-700`}>
          {getSimpleText(label)}
          {props.required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      {as === 'textarea' ? (
        <textarea
          className={inputClasses}
          placeholder={placeholder ? getSimpleText(placeholder) : undefined}
          rows={rows}
          {...(props as any)}
        />
      ) : (
        <input
          className={inputClasses}
          placeholder={placeholder ? getSimpleText(placeholder) : undefined}
          {...props}
        />
      )}
      {error && (
        <p className={`${isSimpleMode ? 'text-base' : 'text-sm'} text-red-600 mt-1`}>
          {getSimpleText(error)}
        </p>
      )}
    </div>
  );
};

// Card component that respects Simple Mode
interface SimpleModeCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export const SimpleModeCard: React.FC<SimpleModeCardProps> = ({ 
  children, 
  className = '',
  title 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  return (
    <div className={`bg-white rounded-lg shadow-md ${isSimpleMode ? 'p-6' : 'p-4'} ${className}`}>
      {title && (
        <h3 className={`font-semibold ${isSimpleMode ? 'text-2xl mb-4' : 'text-lg mb-3'} text-gray-900`}>
          {getSimpleText(title)}
        </h3>
      )}
      {children}
    </div>
  );
};

// Alert component that respects Simple Mode
interface SimpleModeAlertProps {
  type: 'info' | 'success' | 'warning' | 'error';
  children: React.ReactNode;
  className?: string;
}

export const SimpleModeAlert: React.FC<SimpleModeAlertProps> = ({ 
  type, 
  children,
  className = '' 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const typeStyles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800',
  };
  
  return (
    <div className={`${isSimpleMode ? 'p-5' : 'p-4'} rounded-lg border-2 ${typeStyles[type]} ${className}`}>
      <div className={`${isSimpleMode ? 'text-lg' : 'text-base'} font-medium`}>
        {typeof children === 'string' ? getSimpleText(children) : children}
      </div>
    </div>
  );
};

export default SimpleModeWrapper;