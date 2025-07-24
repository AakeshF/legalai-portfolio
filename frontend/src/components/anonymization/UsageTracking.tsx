import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Calendar, AlertCircle, BarChart3, Activity, CheckCircle } from 'lucide-react';

interface UsageData {
  month: string;
  promptsSubmitted: number;
  tokensUsed: number;
  cost: number;
  approvalRate: number;
  modelsUsed: Record<string, number>;
}

interface UsageTrackingProps {
  userId: string;
  organizationId: string;
}

export const UsageTracking: React.FC<UsageTrackingProps> = ({
  userId,
  organizationId
}) => {
  const [currentMonth, setCurrentMonth] = useState<UsageData | null>(null);
  const [previousMonths, setPreviousMonths] = useState<UsageData[]>([]);
  const [loading, setLoading] = useState(true);
  const [rateLimit, setRateLimit] = useState<{
    limit: number;
    used: number;
    resetsAt: string;
  } | null>(null);

  useEffect(() => {
    fetchUsageData();
  }, [userId, organizationId]);

  const fetchUsageData = async () => {
    try {
      setLoading(true);
      const [usage, limits] = await Promise.all([
        fetch(`/api/usage/${userId}`).then(r => r.json()),
        fetch(`/api/rate-limits/${organizationId}`).then(r => r.json())
      ]);
      
      setCurrentMonth(usage.current);
      setPreviousMonths(usage.previous);
      setRateLimit(limits);
    } catch (error) {
      console.error('Failed to fetch usage data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const rateLimitPercentage = rateLimit 
    ? (rateLimit.used / rateLimit.limit) * 100 
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-blue-600" />
        <h3 className="text-lg font-semibold">Usage & Billing</h3>
      </div>

      {/* Current Month Stats */}
      {currentMonth && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-600">Prompts This Month</p>
                <p className="text-2xl font-semibold mt-1">
                  {formatNumber(currentMonth.promptsSubmitted)}
                </p>
              </div>
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-600">Tokens Used</p>
                <p className="text-2xl font-semibold mt-1">
                  {formatNumber(currentMonth.tokensUsed)}
                </p>
              </div>
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-600">Current Cost</p>
                <p className="text-2xl font-semibold mt-1">
                  {formatCurrency(currentMonth.cost)}
                </p>
              </div>
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-600">Approval Rate</p>
                <p className="text-2xl font-semibold mt-1">
                  {currentMonth.approvalRate}%
                </p>
              </div>
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
          </div>
        </div>
      )}

      {/* Rate Limits */}
      {rateLimit && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-medium">API Rate Limits</h4>
            <span className="text-sm text-gray-600">
              Resets {new Date(rateLimit.resetsAt).toLocaleDateString()}
            </span>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Used: {formatNumber(rateLimit.used)}</span>
              <span>Limit: {formatNumber(rateLimit.limit)}</span>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  rateLimitPercentage > 80 
                    ? 'bg-red-600' 
                    : rateLimitPercentage > 60 
                    ? 'bg-amber-600' 
                    : 'bg-green-600'
                }`}
                style={{ width: `${Math.min(rateLimitPercentage, 100)}%` }}
              />
            </div>
            
            {rateLimitPercentage > 80 && (
              <div className="flex items-center gap-2 p-2 bg-amber-50 text-amber-700 rounded text-sm mt-2">
                <AlertCircle className="w-4 h-4" />
                You're approaching your rate limit. Consider upgrading your plan.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Model Usage Breakdown */}
      {currentMonth?.modelsUsed && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h4 className="font-medium mb-3">Model Usage Distribution</h4>
          <div className="space-y-2">
            {Object.entries(currentMonth.modelsUsed).map(([model, count]) => {
              const percentage = (count / currentMonth.promptsSubmitted) * 100;
              return (
                <div key={model} className="flex items-center gap-3">
                  <span className="text-sm font-medium w-32">{model}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 bg-blue-600 rounded-full"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-600 w-16 text-right">
                    {percentage.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Historical Trend */}
      {previousMonths.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h4 className="font-medium mb-3">Monthly Trend</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">Month</th>
                  <th className="px-4 py-2 text-right">Prompts</th>
                  <th className="px-4 py-2 text-right">Tokens</th>
                  <th className="px-4 py-2 text-right">Cost</th>
                  <th className="px-4 py-2 text-right">Approval Rate</th>
                </tr>
              </thead>
              <tbody>
                {previousMonths.map(month => (
                  <tr key={month.month} className="border-t border-gray-200">
                    <td className="px-4 py-2">{month.month}</td>
                    <td className="px-4 py-2 text-right">
                      {formatNumber(month.promptsSubmitted)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {formatNumber(month.tokensUsed)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {formatCurrency(month.cost)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {month.approvalRate}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Calendar className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <p className="font-medium text-blue-900">Billing Cycle</p>
            <p className="text-sm text-blue-700 mt-1">
              Your billing cycle resets on the 1st of each month. 
              Usage is calculated based on tokens consumed across all AI providers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};