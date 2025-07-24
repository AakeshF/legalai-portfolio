import React from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'hover' | 'interactive';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  shadow?: 'none' | 'soft' | 'default' | 'lifted';
}

const Card: React.FC<CardProps> = ({
  children,
  className,
  variant = 'default',
  padding = 'md',
  shadow = 'default',
  ...props
}) => {
  const baseStyles = 'bg-white rounded-lg border border-brand-gray-200';
  
  const variants = {
    default: '',
    hover: 'transition-all duration-300 hover:shadow-lifted hover:border-brand-gray-300 hover:translate-y-[-2px]',
    interactive: 'cursor-pointer transition-all duration-300 hover:shadow-lifted hover:border-brand-blue-200 hover:translate-y-[-2px]'
  };

  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };

  const shadows = {
    none: '',
    soft: 'shadow-soft',
    default: 'shadow-sm',
    lifted: 'shadow-lifted'
  };

  return (
    <div
      className={cn(
        baseStyles,
        variants[variant],
        paddings[padding],
        shadows[shadow],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'flex items-center justify-between border-b border-brand-gray-200 pb-4 mb-4',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  children,
  className,
  ...props
}) => {
  return (
    <h3
      className={cn(
        'font-serif text-xl font-bold text-brand-gray-900',
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
};

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'text-brand-gray-700',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'flex items-center justify-between border-t border-brand-gray-200 pt-4 mt-4',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;
