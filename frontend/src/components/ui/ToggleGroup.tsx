import React from 'react';

interface ToggleGroupProps {
  children: React.ReactNode;
  className?: string;
}

export const ToggleGroup: React.FC<ToggleGroupProps> = ({ children, className = '' }) => {
  return (
    <div className={`inline-flex rounded-lg shadow-sm ${className}`} role="group">
      {children}
    </div>
  );
};

interface ToggleGroupItemProps {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

export const ToggleGroupItem: React.FC<ToggleGroupItemProps> = ({ 
  children, 
  active = false, 
  onClick, 
  disabled = false,
  className = ''
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`
        px-4 py-2 text-sm font-medium border transition-colors
        first:rounded-l-lg last:rounded-r-lg
        ${active 
          ? 'bg-blue-600 text-white border-blue-600 z-10' 
          : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
    >
      {children}
    </button>
  );
};