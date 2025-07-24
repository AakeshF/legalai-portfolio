import React, { useState, useEffect } from 'react';
import { 
  BarChart3, TrendingUp, Clock, Zap, AlertCircle, 
  CheckCircle, XCircle, Activity, Users, FileText,
  Award, Target
} from 'lucide-react';
import { AI_PROVIDERS, AIProvider } from './types';
import { useAuth } from '../../contexts/AuthContext';
import { Skeleton } from '../Skeleton';

interface ProviderMetrics {
  provider: AIProvider;
  requests: number;
  successRate: number;
  averageResponseTime: number;
  averageTokensUsed: number;
  errorRate: number;
  costPerformanceScore: number;
  userSatisfactionScore: number;
  documentTypes: {
    type: string;
    count: number;
    performance: number;
  }[];
  timeSeriesData: {
    date: string;
    requests: number;
    responseTime: number;
    errors: number;
  }[];
}

interface AnalyticsPeriod {
  label: string;
  value: '7d' | '30d' | '90d';
}

export const AIProviderAnalytics: React.FC = () => {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<ProviderMetrics[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState<AnalyticsPeriod['value']>('30d');
  const [selectedProvider, setSelectedProvider] = useState<AIProvider | 'all'>('all');
  const [comparisonMode, setComparisonMode] = useState(false);

  const periods: AnalyticsPeriod[] = [
    { label: 'Last 7 days', value: '7d' },
    { label: 'Last 30 days', value: '30d' },
    { label: 'Last 90 days', value: '90d' }
  ];

  useEffect(() => {
    fetchAnalytics();
  }, [selectedPeriod]);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/organizations/${user?.organizationId}/ai-analytics?period=${selectedPeriod}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const calculateOverallMetrics = () => {
    if (metrics.length === 0) return null;

    const totals = metrics.reduce((acc, m) => ({
      requests: acc.requests + m.requests,
      responseTime: acc.responseTime + (m.averageResponseTime * m.requests),
      errors: acc.errors + (m.errorRate * m.requests / 100),
      satisfaction: acc.satisfaction + (m.userSatisfactionScore * m.requests)
    }), { requests: 0, responseTime: 0, errors: 0, satisfaction: 0 });

    return {
      totalRequests: totals.requests,
      averageResponseTime: totals.responseTime / totals.requests,
      overallErrorRate: (totals.errors / totals.requests) * 100,
      averageSatisfaction: totals.satisfaction / totals.requests
    };
  };

  const getPerformanceColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getPerformanceBadge = (score: number) => {
    if (score >= 90) return { icon: CheckCircle, color: 'text-green-600', label: 'Excellent' };
    if (score >= 70) return { icon: AlertCircle, color: 'text-yellow-600', label: 'Good' };
    return { icon: XCircle, color: 'text-red-600', label: 'Needs Improvement' };
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const overallMetrics = calculateOverallMetrics();
  const filteredMetrics = selectedProvider === 'all' 
    ? metrics 
    : metrics.filter(m => m.provider === selectedProvider);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <BarChart3 className="h-6 w-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">AI Provider Performance Analytics</h3>
          </div>
          
          <div className="flex items-center space-x-4">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value as AnalyticsPeriod['value'])}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {periods.map(period => (
                <option key={period.value} value={period.value}>
                  {period.label}
                </option>
              ))}
            </select>

            <button
              onClick={() => setComparisonMode(!comparisonMode)}
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                comparisonMode 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Compare Providers
            </button>
          </div>
        </div>

        {/* Overall Metrics */}
        {overallMetrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <Activity className="h-8 w-8 text-gray-400" />
                <TrendingUp className="h-4 w-4 text-green-500" />
              </div>
              <p className="text-2xl font-semibold text-gray-900">
                {overallMetrics.totalRequests.toLocaleString()}
              </p>
              <p className="text-sm text-gray-600">Total Requests</p>
            </div>

            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <Clock className="h-8 w-8 text-blue-600" />
              </div>
              <p className="text-2xl font-semibold text-gray-900">
                {(overallMetrics.averageResponseTime / 1000).toFixed(1)}s
              </p>
              <p className="text-sm text-gray-600">Avg Response Time</p>
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <p className="text-2xl font-semibold text-gray-900">
                {(100 - overallMetrics.overallErrorRate).toFixed(1)}%
              </p>
              <p className="text-sm text-gray-600">Success Rate</p>
            </div>

            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <Award className="h-8 w-8 text-purple-600" />
              </div>
              <p className="text-2xl font-semibold text-gray-900">
                {overallMetrics.averageSatisfaction.toFixed(1)}/5
              </p>
              <p className="text-sm text-gray-600">User Satisfaction</p>
            </div>
          </div>
        )}

        {/* Provider Filter */}
        <div className="mb-4">
          <div className="flex items-center space-x-2 overflow-x-auto">
            <button
              onClick={() => setSelectedProvider('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                selectedProvider === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All Providers
            </button>
            {metrics.map(metric => (
              <button
                key={metric.provider}
                onClick={() => setSelectedProvider(metric.provider)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${
                  selectedProvider === metric.provider
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span>{AI_PROVIDERS[metric.provider].icon}</span>
                <span>{AI_PROVIDERS[metric.provider].name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Provider Performance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredMetrics.map(metric => {
          const performanceBadge = getPerformanceBadge(metric.costPerformanceScore);
          return (
            <div key={metric.provider} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{AI_PROVIDERS[metric.provider].icon}</span>
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900">
                      {AI_PROVIDERS[metric.provider].name}
                    </h4>
                    <div className="flex items-center space-x-2 mt-1">
                      <performanceBadge.icon className={`h-4 w-4 ${performanceBadge.color}`} />
                      <span className={`text-sm font-medium ${performanceBadge.color}`}>
                        {performanceBadge.label}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-semibold text-gray-900">
                    {metric.costPerformanceScore}
                  </p>
                  <p className="text-xs text-gray-500">Performance Score</p>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-600">Response Time</p>
                  <p className={`text-lg font-semibold ${
                    metric.averageResponseTime < 2000 ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {(metric.averageResponseTime / 1000).toFixed(2)}s
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Success Rate</p>
                  <p className={`text-lg font-semibold ${getPerformanceColor(metric.successRate)}`}>
                    {metric.successRate.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Requests</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {metric.requests.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Satisfaction</p>
                  <p className="text-lg font-semibold text-gray-900">
                    ⭐ {metric.userSatisfactionScore.toFixed(1)}
                  </p>
                </div>
              </div>

              {/* Document Type Performance */}
              <div className="pt-4 border-t border-gray-200">
                <p className="text-sm font-medium text-gray-700 mb-2">Best for:</p>
                <div className="space-y-1">
                  {metric.documentTypes
                    .sort((a, b) => b.performance - a.performance)
                    .slice(0, 3)
                    .map((docType, index) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">{docType.type}</span>
                        <span className={`font-medium ${getPerformanceColor(docType.performance)}`}>
                          {docType.performance}% accuracy
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Comparison Chart */}
      {comparisonMode && metrics.length > 1 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Provider Comparison</h4>
          
          <div className="space-y-4">
            {/* Response Time Comparison */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Response Time</p>
              <div className="space-y-2">
                {metrics
                  .sort((a, b) => a.averageResponseTime - b.averageResponseTime)
                  .map(metric => {
                    const maxTime = Math.max(...metrics.map(m => m.averageResponseTime));
                    const percentage = (metric.averageResponseTime / maxTime) * 100;
                    return (
                      <div key={metric.provider} className="flex items-center space-x-3">
                        <span className="text-sm text-gray-600 w-32">
                          {AI_PROVIDERS[metric.provider].name}
                        </span>
                        <div className="flex-1 bg-gray-200 rounded-full h-6 relative">
                          <div
                            className="bg-blue-600 h-6 rounded-full flex items-center justify-end pr-2"
                            style={{ width: `${percentage}%` }}
                          >
                            <span className="text-xs text-white font-medium">
                              {(metric.averageResponseTime / 1000).toFixed(1)}s
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Cost Performance Comparison */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Cost Performance Score</p>
              <div className="space-y-2">
                {metrics
                  .sort((a, b) => b.costPerformanceScore - a.costPerformanceScore)
                  .map(metric => (
                    <div key={metric.provider} className="flex items-center space-x-3">
                      <span className="text-sm text-gray-600 w-32">
                        {AI_PROVIDERS[metric.provider].name}
                      </span>
                      <div className="flex-1 bg-gray-200 rounded-full h-6 relative">
                        <div
                          className="bg-green-600 h-6 rounded-full flex items-center justify-end pr-2"
                          style={{ width: `${metric.costPerformanceScore}%` }}
                        >
                          <span className="text-xs text-white font-medium">
                            {metric.costPerformanceScore}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Target className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900">Performance Insights</p>
            <ul className="mt-2 space-y-1 text-sm text-blue-800">
              {metrics
                .sort((a, b) => b.costPerformanceScore - a.costPerformanceScore)
                .slice(0, 3)
                .map((metric, index) => (
                  <li key={index}>
                    • {AI_PROVIDERS[metric.provider].name} excels at {
                      metric.documentTypes[0]?.type || 'general queries'
                    } with {metric.successRate.toFixed(0)}% success rate
                  </li>
                ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};