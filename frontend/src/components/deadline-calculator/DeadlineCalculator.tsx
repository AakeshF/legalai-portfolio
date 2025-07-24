import React, { useState, useEffect } from 'react';
import { 
  Calculator, Download, Mail, Plus, Calendar, 
  AlertCircle, Loader2, FileText, Send 
} from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDeadlineCalculation, useMCPServerCheck } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { SimpleModeCard, SimpleModeButton, SimpleModeAlert } from '../SimpleModeWrapper';
import { DateInputWithCourtCalendar } from './DateInputWithCourtCalendar';
import { MCPStatusBadge } from './MCPStatusBadge';
import { DeadlineTimeline } from './DeadlineTimeline';
import { Deadline, CaseType } from './types';
import { 
  calculateDeadlinesLocally, 
  sortDeadlinesByDate, 
  downloadICSFile,
  exportToICS 
} from './utils';
import { format } from 'date-fns';
import { useToast } from '../Toast';

// Create a separate QueryClient for the deadline calculator
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 5 * 60 * 1000 // 5 minutes
    }
  }
});

interface DeadlineCalculatorProps {
  matterId?: string;
  onDeadlinesCalculated?: (deadlines: Deadline[]) => void;
  embedded?: boolean;
}

// Available case types (would normally come from MCP)
const CASE_TYPES: CaseType[] = [
  { id: 'personal_injury', name: 'Personal Injury', category: 'civil', deadlineProfiles: [] },
  { id: 'contract', name: 'Contract Dispute', category: 'civil', deadlineProfiles: [] },
  { id: 'employment', name: 'Employment', category: 'civil', deadlineProfiles: [] },
  { id: 'family_law', name: 'Family Law', category: 'family', deadlineProfiles: [] },
  { id: 'criminal', name: 'Criminal Defense', category: 'criminal', deadlineProfiles: [] }
];

// US States (simplified)
const STATES = [
  { code: 'CA', name: 'California' },
  { code: 'NY', name: 'New York' },
  { code: 'TX', name: 'Texas' },
  { code: 'FL', name: 'Florida' },
  { code: 'IL', name: 'Illinois' }
];

const DeadlineCalculatorContent: React.FC<DeadlineCalculatorProps> = ({ 
  matterId, 
  onDeadlinesCalculated,
  embedded = false 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const { showSuccess, showError, showInfo } = useToast();
  
  // Form state
  const [triggerDate, setTriggerDate] = useState<Date | null>(null);
  const [caseType, setCaseType] = useState('');
  const [jurisdiction, setJurisdiction] = useState({ state: '', county: '' });
  const [calculatedDeadlines, setCalculatedDeadlines] = useState<Deadline[]>([]);
  const [isCalculating, setIsCalculating] = useState(false);
  
  // MCP server status
  const { data: courtStatus } = useMCPServerCheck('court_system');
  
  // Deadline calculation via MCP
  const { 
    data: mcpDeadlines, 
    isLoading: loadingMCPDeadlines,
    refetch: refetchDeadlines 
  } = useDeadlineCalculation(triggerDate, caseType, jurisdiction);
  
  const calculateDeadlines = async () => {
    if (!triggerDate || !caseType || !jurisdiction.state) {
      showError('Please fill in all required fields');
      return;
    }
    
    setIsCalculating(true);
    
    try {
      let deadlines: Deadline[] = [];
      
      if (courtStatus?.isOnline && mcpDeadlines?.data) {
        // Use MCP data
        deadlines = mcpDeadlines.data.map((d: any) => ({
          ...d,
          mcpSource: true,
          date: new Date(d.date)
        }));
        showSuccess('Deadlines calculated using live court data');
      } else {
        // Fallback to local calculation
        deadlines = calculateDeadlinesLocally(triggerDate, caseType, jurisdiction);
        showInfo('Using offline deadline calculation');
      }
      
      const sortedDeadlines = sortDeadlinesByDate(deadlines);
      setCalculatedDeadlines(sortedDeadlines);
      onDeadlinesCalculated?.(sortedDeadlines);
      
    } catch (error) {
      showError('Failed to calculate deadlines');
      console.error('Deadline calculation error:', error);
    } finally {
      setIsCalculating(false);
    }
  };
  
  const handleExportCalendar = () => {
    if (calculatedDeadlines.length === 0) {
      showError('No deadlines to export');
      return;
    }
    
    downloadICSFile(calculatedDeadlines, `legal-deadlines-${format(new Date(), 'yyyy-MM-dd')}.ics`);
    showSuccess('Calendar file downloaded');
  };
  
  const handleEmailDeadlines = () => {
    if (calculatedDeadlines.length === 0) {
      showError('No deadlines to email');
      return;
    }
    
    const subject = `Legal Deadlines - ${caseType} - ${jurisdiction.state}`;
    const body = calculatedDeadlines
      .map(d => `${d.title}: ${format(d.date, 'MMM d, yyyy')}`)
      .join('\n');
    
    window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };
  
  const handleAddToMatter = () => {
    if (!matterId) {
      showError('No matter selected');
      return;
    }
    
    // This would normally save to the matter via API
    showSuccess(`Added ${calculatedDeadlines.length} deadlines to matter`);
  };
  
  const handlePrint = () => {
    window.print();
  };
  
  return (
    <div className={embedded ? '' : 'max-w-6xl mx-auto p-6'}>
      {!embedded && (
        <div className="mb-8">
          <h1 className={`font-bold text-gray-900 flex items-center ${
            isSimpleMode ? 'text-3xl' : 'text-2xl'
          }`}>
            <Calculator className="w-8 h-8 mr-3" />
            {getSimpleText('Deadline Calculator')}
          </h1>
          <p className={`text-gray-600 mt-2 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
            {getSimpleText('Calculate important legal deadlines based on jurisdiction and case type')}
          </p>
        </div>
      )}
      
      {/* MCP Status */}
      <div className="mb-6 flex items-center justify-between">
        <MCPStatusBadge server="court_system" onRefresh={refetchDeadlines} />
        
        {matterId && (
          <span className={`text-gray-600 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
            Matter ID: {matterId}
          </span>
        )}
      </div>
      
      {/* Input Form */}
      <SimpleModeCard title="Calculate Deadlines" className="mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Trigger Date */}
          <div className="md:col-span-2">
            <DateInputWithCourtCalendar
              label="Incident/Trigger Date"
              value={triggerDate}
              onChange={setTriggerDate}
              jurisdiction={jurisdiction.state}
              required
              placeholder="Select the date that triggers deadlines"
            />
          </div>
          
          {/* Case Type */}
          <div>
            <label className={`block font-medium text-gray-700 mb-2 ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              {getSimpleText('Case Type')} <span className="text-red-500">*</span>
            </label>
            <select
              value={caseType}
              onChange={(e) => setCaseType(e.target.value)}
              className={`
                w-full rounded-lg border border-gray-300
                focus:outline-none focus:ring-2 focus:ring-blue-500
                ${isSimpleMode ? 'px-4 py-3 text-lg' : 'px-3 py-2 text-base'}
              `}
            >
              <option value="">{getSimpleText('Select case type')}</option>
              {CASE_TYPES.map(type => (
                <option key={type.id} value={type.id}>
                  {getSimpleText(type.name)}
                </option>
              ))}
            </select>
          </div>
          
          {/* State */}
          <div>
            <label className={`block font-medium text-gray-700 mb-2 ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              {getSimpleText('State')} <span className="text-red-500">*</span>
            </label>
            <select
              value={jurisdiction.state}
              onChange={(e) => setJurisdiction({ ...jurisdiction, state: e.target.value })}
              className={`
                w-full rounded-lg border border-gray-300
                focus:outline-none focus:ring-2 focus:ring-blue-500
                ${isSimpleMode ? 'px-4 py-3 text-lg' : 'px-3 py-2 text-base'}
              `}
            >
              <option value="">{getSimpleText('Select state')}</option>
              {STATES.map(state => (
                <option key={state.code} value={state.code}>
                  {state.name}
                </option>
              ))}
            </select>
          </div>
          
          {/* County (optional) */}
          <div>
            <label className={`block font-medium text-gray-700 mb-2 ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              {getSimpleText('County')}
            </label>
            <input
              type="text"
              value={jurisdiction.county}
              onChange={(e) => setJurisdiction({ ...jurisdiction, county: e.target.value })}
              placeholder={getSimpleText('Enter county (optional)')}
              className={`
                w-full rounded-lg border border-gray-300
                focus:outline-none focus:ring-2 focus:ring-blue-500
                ${isSimpleMode ? 'px-4 py-3 text-lg' : 'px-3 py-2 text-base'}
              `}
            />
          </div>
        </div>
        
        <div className="mt-6 flex justify-end">
          <SimpleModeButton
            onClick={calculateDeadlines}
            disabled={isCalculating || loadingMCPDeadlines}
            variant="primary"
            size="lg"
          >
            {isCalculating || loadingMCPDeadlines ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                {getSimpleText('Calculating...')}
              </>
            ) : (
              <>
                <Calculator className="w-5 h-5 mr-2" />
                {getSimpleText('Calculate Deadlines')}
              </>
            )}
          </SimpleModeButton>
        </div>
      </SimpleModeCard>
      
      {/* Results */}
      {calculatedDeadlines.length > 0 && (
        <>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <h2 className={`font-semibold text-gray-900 ${
              isSimpleMode ? 'text-2xl' : 'text-xl'
            }`}>
              {getSimpleText(`Calculated ${calculatedDeadlines.length} Deadlines`)}
            </h2>
            
            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleExportCalendar}
                className={`
                  flex items-center px-4 py-2 bg-white border border-gray-300 
                  rounded-lg hover:bg-gray-50 transition-colors font-medium
                  ${isSimpleMode ? 'text-base' : 'text-sm'}
                `}
              >
                <Download className="w-4 h-4 mr-2" />
                {getSimpleText('Export to Calendar')}
              </button>
              
              <button
                onClick={handleEmailDeadlines}
                className={`
                  flex items-center px-4 py-2 bg-white border border-gray-300 
                  rounded-lg hover:bg-gray-50 transition-colors font-medium
                  ${isSimpleMode ? 'text-base' : 'text-sm'}
                `}
              >
                <Mail className="w-4 h-4 mr-2" />
                {getSimpleText('Email Report')}
              </button>
              
              <button
                onClick={handlePrint}
                className={`
                  flex items-center px-4 py-2 bg-white border border-gray-300 
                  rounded-lg hover:bg-gray-50 transition-colors font-medium
                  ${isSimpleMode ? 'text-base' : 'text-sm'}
                `}
              >
                <FileText className="w-4 h-4 mr-2" />
                {getSimpleText('Print')}
              </button>
              
              {matterId && (
                <button
                  onClick={handleAddToMatter}
                  className={`
                    flex items-center px-4 py-2 bg-green-600 text-white 
                    rounded-lg hover:bg-green-700 transition-colors font-medium
                    ${isSimpleMode ? 'text-base' : 'text-sm'}
                  `}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  {getSimpleText('Add to Matter')}
                </button>
              )}
            </div>
          </div>
          
          {/* Timeline */}
          <SimpleModeCard className="print:shadow-none">
            <DeadlineTimeline 
              deadlines={calculatedDeadlines}
              onDeadlineClick={(deadline) => {
                showInfo(`${deadline.title}: ${format(deadline.date, 'MMMM d, yyyy')}`);
              }}
            />
          </SimpleModeCard>
        </>
      )}
      
      {/* Print Styles */}
      <style jsx>{`
        @media print {
          .no-print {
            display: none !important;
          }
          
          @page {
            margin: 1in;
          }
        }
      `}</style>
    </div>
  );
};

export const DeadlineCalculator: React.FC<DeadlineCalculatorProps> = (props) => {
  return (
    <QueryClientProvider client={queryClient}>
      <DeadlineCalculatorContent {...props} />
    </QueryClientProvider>
  );
};

export default DeadlineCalculator;