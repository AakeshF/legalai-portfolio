import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../utils/cn';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  children: React.ReactNode;
  showCloseButton?: boolean;
  closeOnOverlay?: boolean;
  closeOnEscape?: boolean;
  className?: string;
}

const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  size = 'md',
  children,
  showCloseButton = true,
  closeOnOverlay = true,
  closeOnEscape = true,
  className
}) => {
  // Handle ESC key press
  useEffect(() => {
    if (!closeOnEscape || !isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [closeOnEscape, isOpen, onClose]);

  // Handle body scroll lock
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-7xl mx-4'
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (closeOnOverlay && e.target === e.currentTarget) {
      onClose();
    }
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      onClick={handleOverlayClick}
    >
      {/* Glassmorphism Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      
      {/* Modal Container */}
      <div 
        className={cn(
          'relative bg-white rounded-xl shadow-lifted border border-brand-gray-200 animate-slide-up',
          'max-h-[90vh] overflow-hidden flex flex-col',
          sizes[size],
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between p-6 border-b border-brand-gray-200 bg-brand-gray-50/50 rounded-t-xl">
            {title && (
              <h2 className="text-xl font-serif font-bold text-brand-gray-900">
                {title}
              </h2>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className="p-2 text-brand-gray-500 hover:text-brand-gray-700 hover:bg-brand-gray-100 rounded-lg transition-all duration-200 btn-press"
                aria-label="Dismiss"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </div>
  );

  // Render modal in portal
  return createPortal(modalContent, document.body);
};

// Convenience components for structured content
export const ModalHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className,
  ...props
}) => (
  <div
    className={cn('mb-4', className)}
    {...props}
  >
    {children}
  </div>
);

export const ModalBody: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className,
  ...props
}) => (
  <div
    className={cn('space-y-4', className)}
    {...props}
  >
    {children}
  </div>
);

export const ModalFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className,
  ...props
}) => (
  <div
    className={cn(
      'flex items-center justify-end space-x-3 pt-4 mt-6 border-t border-brand-gray-200',
      className
    )}
    {...props}
  >
    {children}
  </div>
);

// Confirmation modal with Legal AI branding
export interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'danger' | 'success';
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you ready to execute this command?',
  confirmText = 'Execute',
  cancelText = 'Abort',
  variant = 'default'
}) => {
  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const getVariantStyles = () => {
    switch (variant) {
      case 'danger':
        return {
          confirmButton: 'bg-red-600 hover:bg-red-700 text-white',
          icon: '⚠️'
        };
      case 'success':
        return {
          confirmButton: 'bg-green-600 hover:bg-green-700 text-white',
          icon: '✓'
        };
      default:
        return {
          confirmButton: 'bg-brand-blue-600 hover:bg-brand-blue-700 text-white',
          icon: '🎯'
        };
    }
  };

  const variantStyles = getVariantStyles();

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm">
      <ModalBody>
        <div className="text-center space-y-4">
          <div className="text-4xl">{variantStyles.icon}</div>
          <div>
            <h3 className="text-lg font-serif font-bold text-brand-gray-900 mb-2">
              {title}
            </h3>
            <p className="text-brand-gray-600">
              {message}
            </p>
          </div>
        </div>
      </ModalBody>
      
      <ModalFooter>
        <button
          onClick={onClose}
          className="px-4 py-2 text-brand-gray-600 hover:text-brand-gray-800 hover:bg-brand-gray-100 rounded-lg transition-all duration-200 btn-press"
        >
          {cancelText}
        </button>
        <button
          onClick={handleConfirm}
          className={cn(
            'px-4 py-2 rounded-lg transition-all duration-200 btn-press shadow-sm hover:shadow-md',
            variantStyles.confirmButton
          )}
        >
          {confirmText}
        </button>
      </ModalFooter>
    </Modal>
  );
};

export default Modal;
