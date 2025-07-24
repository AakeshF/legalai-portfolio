import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../utils/cn';
import { ChevronDown, Search, Check, AlertCircle } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
  description?: string;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  options: SelectOption[];
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
  error?: string;
  success?: string;
  label?: string;
  helperText?: string;
  searchable?: boolean;
  clearable?: boolean;
  variant?: 'default' | 'error' | 'success';
  onValueChange?: (value: string) => void;
}

const Select = React.forwardRef<HTMLDivElement, SelectProps>(({
  options = [],
  placeholder,
  size = 'md',
  error,
  success,
  label,
  helperText,
  searchable = false,
  clearable = false,
  variant = 'default',
  value,
  disabled,
  onValueChange,
  className,
  ...props
}, ref) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const hasError = error || variant === 'error';
  const hasSuccess = success || variant === 'success';

  // Get selected option
  const selectedOption = options.find(option => option.value === value);

  // Filter options based on search term
  const filteredOptions = searchable 
    ? options.filter(option => 
        option.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        option.value.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : options;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchTerm('');
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isOpen) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setHighlightedIndex(prev => 
            prev < filteredOptions.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          event.preventDefault();
          setHighlightedIndex(prev => 
            prev > 0 ? prev - 1 : filteredOptions.length - 1
          );
          break;
        case 'Enter':
          event.preventDefault();
          if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
            handleOptionSelect(filteredOptions[highlightedIndex]);
          }
          break;
        case 'Escape':
          setIsOpen(false);
          setSearchTerm('');
          setHighlightedIndex(-1);
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, highlightedIndex, filteredOptions]);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, searchable]);

  const handleOptionSelect = (option: SelectOption) => {
    if (option.disabled) return;
    
    onValueChange?.(option.value);
    setIsOpen(false);
    setSearchTerm('');
    setHighlightedIndex(-1);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onValueChange?.('');
  };

  const baseStyles = 'relative w-full rounded-lg border transition-all duration-200 focus-within:ring-2 focus-within:ring-offset-1 cursor-pointer';
  
  const variants = {
    default: 'border-brand-gray-300 bg-white focus-within:border-brand-blue-500 focus-within:ring-brand-blue-500/20',
    error: 'border-red-500 bg-red-50 focus-within:border-red-500 focus-within:ring-red-500/20',
    success: 'border-green-500 bg-green-50 focus-within:border-green-500 focus-within:ring-green-500/20'
  };

  const sizes = {
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2.5 text-base',
    lg: 'px-5 py-3.5 text-lg'
  };

  // Hunter S. Thompson inspired placeholder
  const getPlaceholder = () => {
    if (placeholder) return placeholder;
    return 'Choose your weapon...';
  };

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-brand-gray-900">
          {label}
        </label>
      )}
      
      <div ref={containerRef} className="relative">
        {/* Trigger */}
        <div
          ref={ref}
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className={cn(
            baseStyles,
            variants[hasError ? 'error' : hasSuccess ? 'success' : 'default'],
            sizes[size],
            disabled && 'opacity-60 cursor-not-allowed',
            isOpen && 'ring-2 ring-offset-1',
            isOpen && !hasError && !hasSuccess && 'border-brand-blue-500 ring-brand-blue-500/20',
            className
          )}
        >
          <div className="flex items-center justify-between">
            <span className={cn(
              selectedOption ? 'text-brand-gray-900' : 'text-brand-gray-500',
              hasError && 'text-red-900',
              hasSuccess && 'text-green-900'
            )}>
              {selectedOption ? selectedOption.label : getPlaceholder()}
            </span>
            
            <div className="flex items-center space-x-2">
              {clearable && selectedOption && (
                <button
                  onClick={handleClear}
                  className="p-1 hover:bg-brand-gray-100 rounded transition-colors"
                  tabIndex={-1}
                >
                  <span className="text-brand-gray-400 hover:text-brand-gray-600">×</span>
                </button>
              )}
              
              {hasError && <AlertCircle className="w-4 h-4 text-red-500" />}
              {hasSuccess && <Check className="w-4 h-4 text-green-500" />}
              
              <ChevronDown 
                className={cn(
                  'w-4 h-4 transition-transform duration-200',
                  isOpen && 'rotate-180',
                  hasError ? 'text-red-500' : hasSuccess ? 'text-green-500' : 'text-brand-gray-400'
                )}
              />
            </div>
          </div>
        </div>

        {/* Dropdown */}
        {isOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-brand-gray-200 rounded-lg shadow-lifted animate-slide-up">
            {/* Search Input */}
            {searchable && (
              <div className="p-2 border-b border-brand-gray-200">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-gray-400" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder="Hunt for options..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm border border-brand-gray-300 rounded-lg focus:outline-none focus:border-brand-blue-500 focus:ring-1 focus:ring-brand-blue-500/20"
                  />
                </div>
              </div>
            )}

            {/* Options */}
            <div className="max-h-60 overflow-y-auto py-1">
              {filteredOptions.length === 0 ? (
                <div className="px-4 py-3 text-sm text-brand-gray-500 text-center">
                  {searchTerm ? 'No matches found. Try different intel.' : 'No options available.'}
                </div>
              ) : (
                filteredOptions.map((option, index) => (
                  <div
                    key={option.value}
                    onClick={() => handleOptionSelect(option)}
                    className={cn(
                      'px-4 py-2 cursor-pointer transition-colors duration-150',
                      option.disabled && 'opacity-50 cursor-not-allowed',
                      !option.disabled && index === highlightedIndex && 'bg-brand-blue-50 text-brand-blue-900',
                      !option.disabled && index !== highlightedIndex && 'hover:bg-brand-gray-50',
                      selectedOption?.value === option.value && 'bg-brand-blue-100 text-brand-blue-900 font-medium'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm">{option.label}</div>
                        {option.description && (
                          <div className="text-xs text-brand-gray-500 mt-1">
                            {option.description}
                          </div>
                        )}
                      </div>
                      {selectedOption?.value === option.value && (
                        <Check className="w-4 h-4 text-brand-blue-600" />
                      )}
                    </div>
                  </div>
                ))
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

Select.displayName = 'Select';

export default Select;
