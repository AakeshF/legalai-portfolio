import React, { useState, useEffect } from 'react';
import { Zap, Clock, TrendingUp, AlertTriangle, Activity } from 'lucide-react';

interface PerformanceMetrics {
  avgResponseTime: number;
  p95ResponseTime: number;
  successRate: number;
  errorRate: number;
  throughput: number;
  activeConnections: number;
  queueLength: number;
  cacheHitRate: number;
}

interface PerformanceAlert {
  id: string;
  severity: 'warning' | 'critical';
  metric: string;
  value: number;
  threshold: number;
  timestamp: string;
}

export const PerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const [historicalData, setHistoricalData] = useState<Array<{
    timestamp: string;
    responseTime: number;
    throughput: number;
  }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      const [metricsData, alertsData, historyData] = await Promise.all([
        fetch('/api/performance/metrics').then(r => r.json()),
        fetch('/api/performance/alerts').then(r => r.json()),
        fetch('/api/performance/history?limit=50').then(r => r.json())
      ]);
      
      setMetrics(metricsData);
      setAlerts(alertsData);
      setHistoricalData(historyData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
    }
  };

  const getHealthStatus = () => {
    if (!metrics) return 'unknown';
    if (metrics.errorRate > 5 || metrics.avgResponseTime > 2000) return 'critical';
    if (metrics.errorRate > 2 || metrics.avgResponseTime > 1000) return 'warning';
    return 'healthy';
  };

  const healthStatus = getHealthStatus();
  const healthColors = {
    healthy: 'text-green-600 bg-green-50',
    warning: 'text-amber-600 bg-amber-50',
    critical: 'text-red-600 bg-red-50',
    unknown: 'text-gray-600 bg-gray-50'
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Performance Monitor</h3>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${healthColors[healthStatus]}`}>
          {healthStatus.charAt(0).toUpperCase() + healthStatus.slice(1)}
        </div>
      </div>

      {metrics && (
        <>
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              title="Avg Response Time"
              value={`${metrics.avgResponseTime}ms`}
              icon={<Clock className="w-5 h-5" />}
              trend={metrics.avgResponseTime < 500 ? 'good' : metrics.avgResponseTime < 1000 ? 'warning' : 'bad'}
            />
            <MetricCard
              title="Success Rate"
              value={`${metrics.successRate.toFixed(1)}%`}
              icon={<TrendingUp className="w-5 h-5" />}
              trend={metrics.successRate > 99 ? 'good' : metrics.successRate > 95 ? 'warning' : 'bad'}
            />
            <MetricCard
              title="Throughput"
              value={`${metrics.throughput}/min`}
              icon={<Activity className="w-5 h-5" />}
              trend="neutral"
            />
            <MetricCard
              title="Cache Hit Rate"
              value={`${metrics.cacheHitRate.toFixed(1)}%`}
              icon={<Zap className="w-5 h-5" />}
              trend={metrics.cacheHitRate > 80 ? 'good' : metrics.cacheHitRate > 60 ? 'warning' : 'bad'}
            />
          </div>

          {/* Real-time Metrics */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h4 className="font-medium mb-3">Real-time Performance</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">Active Connections</p>
                <p className="text-2xl font-semibold">{metrics.activeConnections}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Queue Length</p>
                <p className="text-2xl font-semibold">{metrics.queueLength}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">P95 Response Time</p>
                <p className="text-2xl font-semibold">{metrics.p95ResponseTime}ms</p>
              </div>
            </div>
          </div>

          {/* Active Alerts */}
          {alerts.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                Active Alerts
              </h4>
              <div className="space-y-2">
                {alerts.map(alert => (
                  <div
                    key={alert.id}
                    className={`p-3 rounded-lg flex items-start gap-3 ${
                      alert.severity === 'critical' 
                        ? 'bg-red-50 border border-red-200' 
                        : 'bg-amber-50 border border-amber-200'
                    }`}
                  >
                    <AlertTriangle className={`w-4 h-4 mt-0.5 ${
                      alert.severity === 'critical' ? 'text-red-600' : 'text-amber-600'
                    }`} />
                    <div className="flex-1">
                      <p className="font-medium text-sm">
                        {alert.metric} exceeded threshold
                      </p>
                      <p className="text-sm text-gray-600">
                        Current: {alert.value} | Threshold: {alert.threshold}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Performance Chart (simplified representation) */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h4 className="font-medium mb-3">Response Time Trend</h4>
            <div className="h-48 flex items-end gap-1">
              {historicalData.slice(-20).map((data, index) => {
                const height = (data.responseTime / 2000) * 100;
                return (
                  <div
                    key={index}
                    className="flex-1 bg-blue-200 hover:bg-blue-300 rounded-t transition-all"
                    style={{ height: `${Math.min(height, 100)}%` }}
                    title={`${data.responseTime}ms at ${new Date(data.timestamp).toLocaleTimeString()}`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>20 min ago</span>
              <span>10 min ago</span>
              <span>Now</span>
            </div>
          </div>
        </>
      )}

      {/* Optimization Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">Performance Optimization Tips</h4>
        <ul className="space-y-1 text-sm text-blue-700">
          <li>• Enable caching for frequently accessed prompts</li>
          <li>• Use batch operations for multiple prompt reviews</li>
          <li>• Consider upgrading to dedicated infrastructure for &lt; 100ms response times</li>
          <li>• Implement client-side caching for better perceived performance</li>
        </ul>
      </div>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend: 'good' | 'warning' | 'bad' | 'neutral';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon, trend }) => {
  const trendColors = {
    good: 'text-green-600',
    warning: 'text-amber-600',
    bad: 'text-red-600',
    neutral: 'text-gray-600'
  };

  return (
    <div className="bg-white p-4 rounded-lg border border-gray-200">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className={`text-2xl font-semibold mt-1 ${trendColors[trend]}`}>
            {value}
          </p>
        </div>
        <div className={`p-2 rounded-lg ${
          trend === 'good' ? 'bg-green-50' :
          trend === 'warning' ? 'bg-amber-50' :
          trend === 'bad' ? 'bg-red-50' :
          'bg-gray-50'
        }`}>
          {React.cloneElement(icon as React.ReactElement, {
            className: `w-5 h-5 ${trendColors[trend]}`
          })}
        </div>
      </div>
    </div>
  );
};