import React from 'react';
import { Zap, TrendingDown, Clock, CheckCircle, Activity } from 'lucide-react';

interface MetricProps {
  label: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export const MetricCard: React.FC<MetricProps> = ({ 
  label, 
  value, 
  unit, 
  icon, 
  trend, 
  className = '' 
}) => {
  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-slate-600'
  };

  return (
    <div className={`bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-all duration-200 animate-fade-in ${className}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 bg-blue-50 rounded-lg">
          {icon || <Activity className="w-5 h-5 text-blue-600" />}
        </div>
        {trend && (
          <span className={`text-sm font-medium ${trendColors[trend]}`}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '—'}
          </span>
        )}
      </div>
      <div>
        <p className="text-sm text-slate-600 mb-1">{label}</p>
        <div className="flex items-baseline space-x-1">
          <span className="text-2xl font-bold text-slate-900">{value}</span>
          {unit && <span className="text-sm text-slate-500">{unit}</span>}
        </div>
      </div>
    </div>
  );
};

interface ResponseMetricsProps {
  responseTime?: number;
  tokensSaved?: number;
  isInstant?: boolean;
  processingTime?: number;
  className?: string;
}

export const ResponseMetrics: React.FC<ResponseMetricsProps> = ({
  responseTime,
  tokensSaved,
  isInstant,
  processingTime,
  className = ''
}) => {
  return (
    <div className={`flex flex-wrap items-center gap-3 text-sm ${className}`}>
      {isInstant && (
        <div className="flex items-center space-x-1 px-3 py-1 bg-green-50 text-green-700 rounded-full border border-green-200 animate-slide-up">
          <Zap className="w-4 h-4" />
          <span className="font-medium">Instant Response</span>
        </div>
      )}
      
      {responseTime !== undefined && (
        <div className="flex items-center space-x-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full border border-blue-200 animate-slide-up" style={{ animationDelay: '50ms' }}>
          <Clock className="w-4 h-4" />
          <span>{responseTime.toFixed(1)}s response</span>
        </div>
      )}
      
      {tokensSaved !== undefined && tokensSaved > 0 && (
        <div className="flex items-center space-x-1 px-3 py-1 bg-purple-50 text-purple-700 rounded-full border border-purple-200 animate-slide-up" style={{ animationDelay: '100ms' }}>
          <TrendingDown className="w-4 h-4" />
          <span>{tokensSaved.toLocaleString()} tokens saved</span>
        </div>
      )}
      
      {processingTime !== undefined && (
        <div className="flex items-center space-x-1 px-3 py-1 bg-amber-50 text-amber-700 rounded-full border border-amber-200 animate-slide-up" style={{ animationDelay: '150ms' }}>
          <Activity className="w-4 h-4" />
          <span>{processingTime.toFixed(1)}s processing</span>
        </div>
      )}
    </div>
  );
};

interface MetricsDashboardProps {
  totalDocuments: number;
  processedDocuments: number;
  averageProcessingTime?: number;
  totalTokensSaved?: number;
  averageResponseTime?: number;
  className?: string;
}

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({
  totalDocuments,
  processedDocuments,
  averageProcessingTime,
  totalTokensSaved,
  averageResponseTime,
  className = ''
}) => {
  const processingRate = totalDocuments > 0 ? Math.round((processedDocuments / totalDocuments) * 100) : 0;

  return (
    <div className={`bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center">
        <Activity className="w-5 h-5 mr-2 text-blue-600" />
        Performance Metrics
      </h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Documents Processed"
          value={processedDocuments}
          unit={`/ ${totalDocuments}`}
          icon={<CheckCircle className="w-5 h-5 text-green-600" />}
          trend={processingRate > 80 ? 'up' : processingRate > 50 ? 'neutral' : 'down'}
        />
        
        {averageProcessingTime !== undefined && (
          <MetricCard
            label="Avg Processing Time"
            value={averageProcessingTime.toFixed(1)}
            unit="seconds"
            icon={<Clock className="w-5 h-5 text-blue-600" />}
            trend={averageProcessingTime < 5 ? 'up' : averageProcessingTime < 10 ? 'neutral' : 'down'}
          />
        )}
        
        {totalTokensSaved !== undefined && (
          <MetricCard
            label="Tokens Saved"
            value={totalTokensSaved > 1000 ? `${(totalTokensSaved / 1000).toFixed(1)}k` : totalTokensSaved}
            icon={<TrendingDown className="w-5 h-5 text-purple-600" />}
            trend="up"
          />
        )}
        
        {averageResponseTime !== undefined && (
          <MetricCard
            label="Avg Response Time"
            value={averageResponseTime.toFixed(1)}
            unit="seconds"
            icon={<Zap className="w-5 h-5 text-amber-600" />}
            trend={averageResponseTime < 1 ? 'up' : averageResponseTime < 3 ? 'neutral' : 'down'}
          />
        )}
      </div>
      
      <div className="mt-4 pt-4 border-t border-slate-200">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Processing Rate</span>
          <span className="text-sm font-medium text-slate-900">{processingRate}%</span>
        </div>
        <div className="mt-2 w-full bg-slate-200 rounded-full h-2 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-1000 ease-out animate-slide-in-left"
            style={{ width: `${processingRate}%` }}
          />
        </div>
      </div>
    </div>
  );
};