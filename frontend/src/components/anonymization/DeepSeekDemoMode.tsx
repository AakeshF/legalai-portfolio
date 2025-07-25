import React from 'react';
import { Sparkles, AlertCircle } from 'lucide-react';

interface DeepSeekDemoModeProps {
  className?: string;
}

export const DeepSeekDemoMode: React.FC<DeepSeekDemoModeProps> = ({ className = '' }) => {
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 bg-amber-100 text-amber-800 rounded-lg text-sm ${className}`}>
      <Sparkles className="w-4 h-4" />
      <span className="font-medium">DeepSeek Demo Mode</span>
      <AlertCircle className="w-3.5 h-3.5" />
    </div>
  );
};

export default DeepSeekDemoMode;