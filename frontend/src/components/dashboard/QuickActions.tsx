import React, { useState } from 'react';
import { 
  Plus, FileText, Calendar, Search, Upload, 
  Calculator, Users, Loader2, AlertTriangle, X 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { checkRequiredMCPServers } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { useToast } from '../Toast';

interface QuickActionButtonProps {
  icon: React.ReactNode;
  label: string;
  description?: string;
  onClick: () => void;
  showMCPIndicator?: boolean;
  requiredServers?: string[];
  disabled?: boolean;
}

const QuickActionButton: React.FC<QuickActionButtonProps> = ({ 
  icon, 
  label, 
  description,
  onClick, 
  showMCPIndicator = false,
  requiredServers = [],
  disabled = false 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const [isChecking, setIsChecking] = useState(false);
  
  return (
    <button
      onClick={async () => {
        if (isChecking) return;
        setIsChecking(true);
        try {
          await onClick();
        } finally {
          setIsChecking(false);
        }
      }}
      disabled={disabled || isChecking}
      className={`
        group relative p-6 bg-white border-2 border-gray-200 rounded-lg
        hover:border-blue-500 hover:shadow-md transition-all
        disabled:opacity-50 disabled:cursor-not-allowed
        ${isSimpleMode ? 'min-h-[120px]' : ''}
      `}
    >
      <div className="flex flex-col items-center text-center">
        <div className={`
          p-3 rounded-lg mb-3
          ${isChecking ? 'bg-gray-100' : 'bg-blue-50 group-hover:bg-blue-100'}
          transition-colors
        `}>
          {isChecking ? (
            <Loader2 className="w-6 h-6 animate-spin text-gray-600" />
          ) : (
            <div className="text-blue-600">{icon}</div>
          )}
        </div>
        
        <h4 className={`font-semibold text-gray-900 ${
          isSimpleMode ? 'text-lg' : 'text-base'
        }`}>
          {getSimpleText(label)}
        </h4>
        
        {description && (
          <p className={`mt-1 text-gray-600 ${
            isSimpleMode ? 'text-sm' : 'text-xs'
          }`}>
            {getSimpleText(description)}
          </p>
        )}
        
        {showMCPIndicator && requiredServers.length > 0 && (
          <div className={`
            absolute top-2 right-2 w-2 h-2 rounded-full
            ${isChecking ? 'bg-gray-400' : 'bg-green-500'}
          `} />
        )}
      </div>
    </button>
  );
};

interface MCPPreflightDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onProceed: () => void;
  offlineServers: string[];
  action: string;
}

const MCPPreflightDialog: React.FC<MCPPreflightDialogProps> = ({
  isOpen,
  onClose,
  onProceed,
  offlineServers,
  action
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  if (!isOpen) return null;
  
  const getServerName = (serverId: string): string => {
    const names: Record<string, string> = {
      'court_system': 'Court System',
      'client_data': 'Client Database',
      'legal_research': 'Legal Research',
      'document_templates': 'Document Templates'
    };
    return names[serverId] || serverId;
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <div className="flex items-start mb-4">
          <AlertTriangle className="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0" />
          <div className="flex-1">
            <h3 className={`font-semibold text-gray-900 ${
              isSimpleMode ? 'text-xl' : 'text-lg'
            }`}>
              {getSimpleText('Limited Functionality')}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <p className={`text-gray-700 mb-4 ${
          isSimpleMode ? 'text-base' : 'text-sm'
        }`}>
          {getSimpleText(`Some features for ${action} may be unavailable because the following data sources are offline:`)}
        </p>
        
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
          <ul className="space-y-1">
            {offlineServers.map(server => (
              <li key={server} className="flex items-center">
                <div className="w-2 h-2 bg-red-500 rounded-full mr-2" />
                <span className={`text-gray-700 ${
                  isSimpleMode ? 'text-base' : 'text-sm'
                }`}>
                  {getServerName(server)}
                </span>
              </li>
            ))}
          </ul>
        </div>
        
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className={`
              px-4 py-2 bg-gray-200 text-gray-700 rounded-lg
              hover:bg-gray-300 transition-colors font-medium
              ${isSimpleMode ? 'text-base' : 'text-sm'}
            `}
          >
            {getSimpleText('Cancel')}
          </button>
          
          <button
            onClick={() => {
              onProceed();
              onClose();
            }}
            className={`
              px-4 py-2 bg-blue-600 text-white rounded-lg
              hover:bg-blue-700 transition-colors font-medium
              ${isSimpleMode ? 'text-base' : 'text-sm'}
            `}
          >
            {getSimpleText('Continue Anyway')}
          </button>
        </div>
      </div>
    </div>
  );
};

export const QuickActions: React.FC = () => {
  const navigate = useNavigate();
  const { showError } = useToast();
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const [preflightDialog, setPreflightDialog] = useState<{
    isOpen: boolean;
    action: string;
    offlineServers: string[];
    onProceed: () => void;
  }>({
    isOpen: false,
    action: '',
    offlineServers: [],
    onProceed: () => {}
  });
  
  const checkAndNavigate = async (
    path: string, 
    action: string, 
    requiredServers: string[]
  ) => {
    if (requiredServers.length === 0) {
      navigate(path);
      return;
    }
    
    try {
      const mcpStatus = await checkRequiredMCPServers(requiredServers);
      
      if (!mcpStatus.allOnline) {
        setPreflightDialog({
          isOpen: true,
          action,
          offlineServers: mcpStatus.offline,
          onProceed: () => navigate(path)
        });
      } else {
        navigate(path);
      }
    } catch (error) {
      showError('Failed to check data source availability');
      navigate(path); // Navigate anyway
    }
  };
  
  const actions = [
    {
      icon: <Plus className="w-6 h-6" />,
      label: 'New Case Intake',
      description: 'Start a new matter',
      path: '/intake',
      requiredServers: ['client_data', 'court_system']
    },
    {
      icon: <FileText className="w-6 h-6" />,
      label: 'Draft Document',
      description: 'Create legal documents',
      path: '/documents/new',
      requiredServers: ['document_templates']
    },
    {
      icon: <Calculator className="w-6 h-6" />,
      label: 'Calculate Deadlines',
      description: 'Compute legal deadlines',
      path: '/deadlines',
      requiredServers: ['court_system']
    },
    {
      icon: <Calendar className="w-6 h-6" />,
      label: 'Schedule Hearing',
      description: 'Book court appearance',
      path: '/calendar/new',
      requiredServers: ['court_system']
    },
    {
      icon: <Search className="w-6 h-6" />,
      label: 'Legal Research',
      description: 'Search case law',
      path: '/research',
      requiredServers: ['legal_research']
    },
    {
      icon: <Upload className="w-6 h-6" />,
      label: 'File with Court',
      description: 'Submit court documents',
      path: '/filing',
      requiredServers: ['court_system', 'document_templates']
    }
  ];
  
  return (
    <>
      <div className="mb-8">
        <h3 className={`font-semibold text-gray-900 mb-4 ${
          isSimpleMode ? 'text-xl' : 'text-lg'
        }`}>
          {getSimpleText('Quick Actions')}
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {actions.map(action => (
            <QuickActionButton
              key={action.path}
              icon={action.icon}
              label={action.label}
              description={action.description}
              onClick={() => checkAndNavigate(
                action.path, 
                action.label, 
                action.requiredServers
              )}
              showMCPIndicator={true}
              requiredServers={action.requiredServers}
            />
          ))}
        </div>
      </div>
      
      <MCPPreflightDialog
        isOpen={preflightDialog.isOpen}
        onClose={() => setPreflightDialog(prev => ({ ...prev, isOpen: false }))}
        onProceed={preflightDialog.onProceed}
        offlineServers={preflightDialog.offlineServers}
        action={preflightDialog.action}
      />
    </>
  );
};