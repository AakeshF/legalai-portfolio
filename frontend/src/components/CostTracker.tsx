import React, { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, AlertCircle } from 'lucide-react';

interface CostTrackerProps {
  sessionCost: number;
  monthlyCost: number;
  monthlyBudget?: number;
}

export const CostTracker: React.FC<CostTrackerProps> = ({
  sessionCost,
  monthlyCost,
  monthlyBudget
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const budgetUsagePercent = monthlyBudget ? (monthlyCost / monthlyBudget) * 100 : 0;
  const isNearBudget = budgetUsagePercent > 80;
  const isOverBudget = budgetUsagePercent > 100;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(amount);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-green-600" />
          <span className="font-medium">AI Usage Cost</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">
            Session: {formatCurrency(sessionCost)}
          </span>
          <TrendingUp className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {showDetails && (
        <div className="mt-4 space-y-3 pt-3 border-t">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Current Session</span>
            <span className="font-medium">{formatCurrency(sessionCost)}</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Month to Date</span>
            <span className="font-medium">{formatCurrency(monthlyCost)}</span>
          </div>

          {monthlyBudget && (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Monthly Budget</span>
                <span className="font-medium">{formatCurrency(monthlyBudget)}</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Budget Used</span>
                  <span className={isOverBudget ? 'text-red-600 font-medium' : 'text-gray-600'}>
                    {budgetUsagePercent.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      isOverBudget ? 'bg-red-600' : isNearBudget ? 'bg-amber-500' : 'bg-green-600'
                    }`}
                    style={{ width: `${Math.min(budgetUsagePercent, 100)}%` }}
                  />
                </div>
              </div>

              {isNearBudget && (
                <div className={`flex items-start gap-2 p-2 rounded ${
                  isOverBudget ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                }`}>
                  <AlertCircle className="w-4 h-4 mt-0.5" />
                  <span className="text-sm">
                    {isOverBudget 
                      ? 'Monthly budget exceeded. Additional charges will apply.'
                      : 'Approaching monthly budget limit.'}
                  </span>
                </div>
              )}
            </>
          )}

          <div className="text-xs text-gray-500 pt-2">
            Costs are estimated based on token usage. Actual billing may vary slightly.
          </div>
        </div>
      )}
    </div>
  );
};