import React, { useState, useEffect } from 'react';
import { TrendingDown, DollarSign, AlertTriangle, Info, Zap, Target } from 'lucide-react';
import { AI_MODELS, AIProvider } from './types';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';
import { BarChart3, PieChart } from 'lucide-react';

interface CostAnalysis {
  currentMonthSpend: number;
  projectedMonthSpend: number;
  lastMonthSpend: number;
  averageRequestCost: number;
  mostExpensiveProvider: {
    provider: AIProvider;
    spend: number;
    percentage: number;
  };
  costByProvider: Array<{
    provider: AIProvider;
    spend: number;
    requests: number;
  }>;
  recommendations: Array<{
    id: string;
    title: string;
    description: string;
    potentialSavings: number;
    impact: 'high' | 'medium' | 'low';
    actionRequired: boolean;
  }>;
}

export const CostOptimizer: React.FC = () => {
  const { user } = useAuth();
  const [costAnalysis, setCostAnalysis] = useState<CostAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRecommendation, setSelectedRecommendation] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [optimizationMode, setOptimizationMode] = useState<'cost' | 'performance' | 'balanced'>('balanced');

  useEffect(() => {
    fetchCostAnalysis();
  }, []);

  const fetchCostAnalysis = async () => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/ai-cost-analysis`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCostAnalysis(data);
        generateRecommendations(data);
      }
    } catch (error) {
      console.error('Failed to fetch cost analysis:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateRecommendations = (analysis: CostAnalysis) => {
    const recommendations = [];
    
    // Check if using expensive models for simple tasks
    if (analysis.averageRequestCost > 0.01) {
      recommendations.push({
        id: 'use-cheaper-models',
        title: 'Use cheaper models for simple queries',
        description: 'Consider using GPT-3.5 or Claude Haiku for basic document summaries and simple questions.',
        potentialSavings: analysis.currentMonthSpend * 0.3,
        impact: 'high' as const,
        actionRequired: true
      });
    }

    // Check if one provider dominates costs
    if (analysis.mostExpensiveProvider.percentage > 70) {
      recommendations.push({
        id: 'diversify-providers',
        title: 'Diversify AI provider usage',
        description: `${analysis.mostExpensiveProvider.provider} accounts for ${analysis.mostExpensiveProvider.percentage}% of costs. Consider alternatives for some use cases.`,
        potentialSavings: analysis.currentMonthSpend * 0.2,
        impact: 'medium' as const,
        actionRequired: false
      });
    }

    // Suggest batch processing
    if (analysis.costByProvider.some(p => p.requests > 100)) {
      recommendations.push({
        id: 'batch-processing',
        title: 'Enable batch processing for documents',
        description: 'Process multiple documents in a single request to reduce API calls and costs.',
        potentialSavings: analysis.currentMonthSpend * 0.15,
        impact: 'medium' as const,
        actionRequired: true
      });
    }

    setCostAnalysis(prev => prev ? { ...prev, recommendations } : null);
  };

  const applyRecommendation = async (recommendationId: string) => {
    try {
      const response = await fetch(`/api/organizations/${user?.organizationId}/apply-cost-optimization`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({ recommendationId, mode: optimizationMode })
      });

      if (response.ok) {
        setToastMessage('Optimization applied successfully');
        setShowToast(true);
        await fetchCostAnalysis();
      }
    } catch (error) {
      setToastMessage('Failed to apply optimization');
      setShowToast(true);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  if (isLoading || !costAnalysis) {
    return <div className="animate-pulse h-96 bg-gray-100 rounded-lg"></div>;
  }

  const savingsPercentage = ((costAnalysis.lastMonthSpend - costAnalysis.currentMonthSpend) / costAnalysis.lastMonthSpend * 100) || 0;

  return (
    <div className="space-y-6">
      {/* Cost Overview */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">AI Cost Optimization</h3>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Optimization Mode:</span>
            <select
              value={optimizationMode}
              onChange={(e) => setOptimizationMode(e.target.value as any)}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="cost">Cost Priority</option>
              <option value="performance">Performance Priority</option>
              <option value="balanced">Balanced</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <DollarSign className="h-8 w-8 text-gray-400" />
              <span className={`text-sm font-medium ${savingsPercentage > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {savingsPercentage > 0 ? '↓' : '↑'} {Math.abs(savingsPercentage).toFixed(1)}%
              </span>
            </div>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(costAnalysis.currentMonthSpend)}
            </p>
            <p className="text-sm text-gray-600">Current Month</p>
          </div>

          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <TrendingDown className="h-8 w-8 text-blue-600" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(costAnalysis.projectedMonthSpend)}
            </p>
            <p className="text-sm text-gray-600">Projected Month</p>
          </div>

          <div className="bg-purple-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <BarChart3 className="h-8 w-8 text-purple-600" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(costAnalysis.averageRequestCost)}
            </p>
            <p className="text-sm text-gray-600">Avg per Request</p>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <Target className="h-8 w-8 text-green-600" />
            </div>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(
                costAnalysis.recommendations.reduce((sum, r) => sum + r.potentialSavings, 0)
              )}
            </p>
            <p className="text-sm text-gray-600">Potential Savings</p>
          </div>
        </div>

        {/* Cost by Provider */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Cost Distribution by Provider</h4>
          <div className="space-y-2">
            {costAnalysis.costByProvider.map((provider) => {
              const percentage = (provider.spend / costAnalysis.currentMonthSpend * 100) || 0;
              return (
                <div key={provider.provider} className="flex items-center space-x-3">
                  <span className="text-sm text-gray-600 w-24">
                    {AI_PROVIDERS[provider.provider]?.name || provider.provider}
                  </span>
                  <div className="flex-1 bg-gray-200 rounded-full h-6 relative">
                    <div
                      className="bg-blue-600 h-6 rounded-full flex items-center justify-end pr-2"
                      style={{ width: `${percentage}%` }}
                    >
                      <span className="text-xs text-white font-medium">
                        {formatCurrency(provider.spend)}
                      </span>
                    </div>
                  </div>
                  <span className="text-sm text-gray-500 w-16 text-right">
                    {percentage.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Cost Optimization Recommendations</h3>
          <Zap className="h-5 w-5 text-yellow-500" />
        </div>

        <div className="space-y-4">
          {costAnalysis.recommendations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
              <p>Your AI usage is already well-optimized!</p>
            </div>
          ) : (
            costAnalysis.recommendations.map((recommendation) => (
              <div
                key={recommendation.id}
                className={`border rounded-lg p-4 transition-all cursor-pointer ${
                  selectedRecommendation === recommendation.id 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setSelectedRecommendation(
                  selectedRecommendation === recommendation.id ? null : recommendation.id
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <h4 className="font-medium text-gray-900">{recommendation.title}</h4>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        getImpactColor(recommendation.impact)
                      }`}>
                        {recommendation.impact} impact
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{recommendation.description}</p>
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-green-600 font-medium">
                        Save ~{formatCurrency(recommendation.potentialSavings)}/month
                      </span>
                      {recommendation.actionRequired && (
                        <span className="flex items-center space-x-1 text-yellow-600">
                          <AlertTriangle className="h-3 w-3" />
                          <span>Action required</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {selectedRecommendation === recommendation.id && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        applyRecommendation(recommendation.id);
                      }}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
                    >
                      Apply Recommendation
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Cost Saving Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Info className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900">Cost Optimization Tips</p>
            <ul className="mt-2 space-y-1 text-sm text-blue-800">
              <li>• Use GPT-3.5 or Claude Haiku for simple queries and summaries</li>
              <li>• Reserve GPT-4 and Claude Opus for complex legal analysis</li>
              <li>• Enable caching for frequently asked questions</li>
              <li>• Batch process similar documents together</li>
              <li>• Set monthly spending limits to avoid surprises</li>
            </ul>
          </div>
        </div>
      </div>

      {showToast && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
};

// Also need to import AI_PROVIDERS
import { AI_PROVIDERS } from './types';