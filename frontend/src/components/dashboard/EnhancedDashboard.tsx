import React, { useMemo } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { 
  BarChart3, TrendingUp, FileText, Clock, 
  Calendar, Users, AlertCircle 
} from 'lucide-react';
import { startOfDay, endOfDay, addDays } from 'date-fns';
import { 
  useCourtCalendar, 
  useUpcomingDeadlines, 
  useFilingStatus 
} from '../../services/mcp';
import { MCPStatusBar } from './MCPStatusBar';
import { TodaySection } from './TodaySection';
import { QuickActions } from './QuickActions';
import { MCPNotificationCenter } from './MCPNotificationCenter';
import { DeadlineAlert, RecentMatter, DashboardMetrics } from './types';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { SimpleModeCard } from '../SimpleModeWrapper';
import { Deadline } from '../deadline-calculator/types';

// Create a separate QueryClient for the dashboard
const dashboardQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      staleTime: 2 * 60 * 1000, // 2 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    }
  }
});

// Mock data for recent matters (would come from API)
const mockRecentMatters: RecentMatter[] = [
  {
    id: '1',
    name: 'Smith v. Johnson',
    clientName: 'Sarah Smith',
    type: 'Personal Injury',
    status: 'active',
    lastActivity: new Date(),
    nextDeadline: addDays(new Date(), 7),
    assignedAttorney: 'John Doe',
    caseNumber: '2024-CV-1234'
  },
  {
    id: '2',
    name: 'ABC Corp Acquisition',
    clientName: 'ABC Corporation',
    type: 'Corporate',
    status: 'active',
    lastActivity: addDays(new Date(), -2),
    nextDeadline: addDays(new Date(), 14),
    assignedAttorney: 'Jane Smith',
    caseNumber: '2024-M&A-5678'
  }
];

// Mock follow-up reminders
const mockFollowUps = [
  {
    id: '1',
    clientName: 'Sarah Smith',
    type: 'call' as const,
    description: 'Discuss settlement offer',
    dueDate: new Date(),
    priority: 'high' as const,
    matterId: '1'
  },
  {
    id: '2',
    clientName: 'ABC Corporation',
    type: 'email' as const,
    description: 'Send draft agreement for review',
    dueDate: new Date(),
    priority: 'medium' as const,
    matterId: '2'
  }
];

const DashboardContent: React.FC = () => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  // Fetch data from MCP
  const today = new Date();
  const { data: courtCalendarData } = useCourtCalendar(
    startOfDay(today),
    endOfDay(addDays(today, 7))
  );
  
  const { data: deadlinesData } = useUpcomingDeadlines(30);
  
  const { data: filingStatusData } = useFilingStatus(
    mockRecentMatters.map(m => m.id)
  );
  
  // Transform MCP data
  const courtAppearances = useMemo(() => {
    if (!courtCalendarData?.data) return [];
    return courtCalendarData.data.map((item: any) => ({
      ...item,
      date: new Date(item.date)
    }));
  }, [courtCalendarData]);
  
  const deadlineAlerts: DeadlineAlert[] = useMemo(() => {
    if (!deadlinesData?.data) return [];
    return deadlinesData.data.map((deadline: Deadline) => ({
      id: deadline.id,
      title: deadline.title,
      description: deadline.description,
      date: new Date(deadline.date),
      daysRemaining: deadline.daysFromTrigger,
      severity: deadline.severity === 'critical' ? 'urgent' : deadline.severity,
      type: deadline.type,
      matterId: deadline.id, // Would normally come from data
      matterName: 'Sample Matter', // Would normally come from data
      isFromMCP: deadline.mcpSource
    }));
  }, [deadlinesData]);
  
  // Calculate metrics
  const metrics: DashboardMetrics = {
    activeMatters: mockRecentMatters.filter(m => m.status === 'active').length,
    upcomingDeadlines: deadlineAlerts.filter(d => d.daysRemaining <= 7).length,
    todayAppearances: courtAppearances.filter(a => 
      a.date.toDateString() === today.toDateString()
    ).length,
    pendingFilings: filingStatusData?.data?.filter((f: any) => 
      f.status === 'pending'
    ).length || 0,
    overdueTasks: deadlineAlerts.filter(d => d.daysRemaining < 0).length
  };
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* MCP Status Bar */}
      <MCPStatusBar />
      
      {/* Header with Notifications */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`font-bold text-gray-900 ${
              isSimpleMode ? 'text-3xl' : 'text-2xl'
            }`}>
              {getSimpleText('Dashboard')}
            </h1>
            <p className={`text-gray-600 mt-1 ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              {getSimpleText('Welcome back! Here\'s your legal command center.')}
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            <MCPNotificationCenter />
          </div>
        </div>
      </div>
      
      <div className="p-6 max-w-7xl mx-auto">
        {/* Metrics Overview */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <MetricCard
            icon={<FileText className="w-5 h-5" />}
            label="Active Matters"
            value={metrics.activeMatters}
            color="blue"
          />
          <MetricCard
            icon={<Clock className="w-5 h-5" />}
            label="Upcoming Deadlines"
            value={metrics.upcomingDeadlines}
            color="yellow"
          />
          <MetricCard
            icon={<Calendar className="w-5 h-5" />}
            label="Today's Appearances"
            value={metrics.todayAppearances}
            color="green"
          />
          <MetricCard
            icon={<FileText className="w-5 h-5" />}
            label="Pending Filings"
            value={metrics.pendingFilings}
            color="purple"
          />
          <MetricCard
            icon={<AlertCircle className="w-5 h-5" />}
            label="Overdue Tasks"
            value={metrics.overdueTasks}
            color="red"
          />
        </div>
        
        {/* Quick Actions */}
        <QuickActions />
        
        {/* Today Section */}
        <div className="mb-8">
          <TodaySection 
            courtData={courtAppearances}
            deadlines={deadlineAlerts}
            followUps={mockFollowUps}
          />
        </div>
        
        {/* Recent Matters */}
        <SimpleModeCard title="Recent Matters">
          <div className="space-y-3">
            {mockRecentMatters.map(matter => (
              <div 
                key={matter.id}
                className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className={`font-semibold text-gray-900 ${
                      isSimpleMode ? 'text-lg' : 'text-base'
                    }`}>
                      {matter.name}
                    </h4>
                    <p className={`text-gray-600 ${
                      isSimpleMode ? 'text-base' : 'text-sm'
                    }`}>
                      {matter.clientName} • {matter.type}
                    </p>
                    {matter.nextDeadline && (
                      <p className={`text-gray-500 mt-1 ${
                        isSimpleMode ? 'text-sm' : 'text-xs'
                      }`}>
                        Next deadline: {matter.nextDeadline.toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <span className={`
                    px-2 py-1 rounded-full text-xs font-medium
                    ${matter.status === 'active' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-gray-100 text-gray-700'
                    }
                  `}>
                    {getSimpleText(matter.status)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </SimpleModeCard>
      </div>
    </div>
  );
};

// Metric Card Component
interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: 'blue' | 'yellow' | 'green' | 'purple' | 'red';
}

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, value, color }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
    red: 'bg-red-50 text-red-600 border-red-200'
  };
  
  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        {icon}
        <TrendingUp className="w-4 h-4" />
      </div>
      <div className={`font-bold ${isSimpleMode ? 'text-3xl' : 'text-2xl'}`}>
        {value}
      </div>
      <p className={`${isSimpleMode ? 'text-sm' : 'text-xs'} mt-1`}>
        {getSimpleText(label)}
      </p>
    </div>
  );
};

export const EnhancedDashboard: React.FC = () => {
  return (
    <QueryClientProvider client={dashboardQueryClient}>
      <DashboardContent />
    </QueryClientProvider>
  );
};

export default EnhancedDashboard;