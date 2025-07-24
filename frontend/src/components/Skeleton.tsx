import React from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'text',
  width,
  height,
  animation = 'pulse'
}) => {
  const baseClasses = 'bg-slate-200';
  
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg'
  };
  
  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'skeleton',
    none: ''
  };
  
  const style: React.CSSProperties = {
    width: width || (variant === 'circular' ? 40 : '100%'),
    height: height || (variant === 'text' ? 20 : variant === 'circular' ? 40 : 100)
  };
  
  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]} ${className}`}
      style={style}
    />
  );
};

// Document Card Skeleton
export const DocumentCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 animate-fade-in">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3 flex-1">
          <Skeleton variant="rectangular" width={40} height={40} />
          <div className="flex-1">
            <Skeleton width="70%" height={20} className="mb-2" />
            <Skeleton width="40%" height={16} />
          </div>
        </div>
        <Skeleton variant="rectangular" width={80} height={28} />
      </div>
      
      <div className="space-y-2">
        <Skeleton width="50%" height={16} />
        <div className="space-y-1">
          <Skeleton width="100%" height={16} />
          <Skeleton width="80%" height={16} />
        </div>
      </div>
    </div>
  );
};

// Document List Skeleton
export const DocumentListSkeleton: React.FC = () => {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[...Array(6)].map((_, index) => (
        <DocumentCardSkeleton key={index} />
      ))}
    </div>
  );
};

// Chat Message Skeleton
export const ChatMessageSkeleton: React.FC = () => {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="max-w-3xl">
        <div className="flex items-center space-x-2 mb-1">
          <Skeleton variant="circular" width={16} height={16} />
          <Skeleton width={80} height={16} />
        </div>
        <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
          <div className="space-y-2">
            <Skeleton width="100%" height={16} />
            <Skeleton width="90%" height={16} />
            <Skeleton width="75%" height={16} />
          </div>
        </div>
      </div>
    </div>
  );
};

// Document View Skeleton
export const DocumentViewSkeleton: React.FC = () => {
  return (
    <div className="animate-fade-in">
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <div className="flex items-start space-x-4">
          <Skeleton variant="rectangular" width={56} height={56} />
          <div className="flex-1">
            <Skeleton width="40%" height={32} className="mb-2" />
            <div className="flex items-center space-x-4">
              <Skeleton width={120} height={16} />
              <Skeleton width={80} height={16} />
            </div>
          </div>
        </div>
      </div>
      
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <Skeleton width={200} height={24} className="mb-4" />
            <div className="space-y-2">
              <Skeleton width="100%" height={16} />
              <Skeleton width="100%" height={16} />
              <Skeleton width="80%" height={16} />
            </div>
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <Skeleton width={150} height={24} className="mb-4" />
            <div className="space-y-3">
              <Skeleton width="100%" height={40} />
              <Skeleton width="100%" height={40} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Table Skeleton
export const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({ 
  rows = 5, 
  columns = 4 
}) => {
  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <Skeleton width={200} height={24} />
          <Skeleton width={100} height={32} />
        </div>
      </div>
      
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-200">
            {[...Array(columns)].map((_, index) => (
              <th key={index} className="p-4 text-left">
                <Skeleton width="80%" height={16} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...Array(rows)].map((_, rowIndex) => (
            <tr key={rowIndex} className="border-b border-slate-100">
              {[...Array(columns)].map((_, colIndex) => (
                <td key={colIndex} className="p-4">
                  <Skeleton width="90%" height={16} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Skeleton;