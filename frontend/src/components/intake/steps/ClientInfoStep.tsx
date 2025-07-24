import React, { useState, useEffect } from 'react';
import { 
  User, Mail, Phone, MapPin, Calendar, AlertTriangle, 
  CheckCircle, Loader2, Shield, ChevronRight 
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { StepProps } from '../CaseIntakeWizard';
import { useConflictCheck, ConflictCheckResult, Conflict } from '../../../services/mcp';
import { useSimpleMode } from '../../../contexts/SimpleModeContext';
import { SimpleModeInput, SimpleModeAlert } from '../../SimpleModeWrapper';
import debounce from 'lodash.debounce';

export const ClientInfoStep: React.FC<StepProps> = ({ 
  data, 
  updateData, 
  onNext,
  onBack 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const checkConflicts = useConflictCheck();
  
  const [clientInfo, setClientInfo] = useState({
    name: data.client?.name || '',
    email: data.client?.email || '',
    phone: data.client?.phone || '',
    address: data.client?.address || '',
    dateOfBirth: data.client?.dateOfBirth || ''
  });

  const [adverseParty, setAdverseParty] = useState({
    name: data.adverseParty?.name || '',
    attorney: data.adverseParty?.attorney || ''
  });

  // Query for client conflicts
  const { data: clientConflictData } = useQuery<ConflictCheckResult>({
    queryKey: ['conflicts', clientInfo.name],
    enabled: clientInfo.name.length >= 3
  });

  // Query for adverse party conflicts
  const { data: adverseConflictData } = useQuery<ConflictCheckResult>({
    queryKey: ['conflicts', adverseParty.name],
    enabled: adverseParty.name.length >= 3
  });

  // Trigger conflict check on name change (debounced)
  useEffect(() => {
    if (clientInfo.name.length >= 3) {
      checkConflicts(clientInfo.name);
    }
  }, [clientInfo.name, checkConflicts]);

  useEffect(() => {
    if (adverseParty.name.length >= 3) {
      checkConflicts(adverseParty.name);
    }
  }, [adverseParty.name, checkConflicts]);

  // Update parent data
  useEffect(() => {
    updateData({
      client: clientInfo,
      adverseParty: adverseParty,
      conflicts: [
        ...(clientConflictData?.data?.conflicts || []),
        ...(adverseConflictData?.data?.conflicts || [])
      ]
    });
  }, [clientInfo, adverseParty, clientConflictData, adverseConflictData]);

  const handleClientChange = (field: string, value: string) => {
    setClientInfo(prev => ({ ...prev, [field]: value }));
  };

  const handleAdverseChange = (field: string, value: string) => {
    setAdverseParty(prev => ({ ...prev, [field]: value }));
  };

  const allConflicts = [
    ...(clientConflictData?.data?.conflicts || []),
    ...(adverseConflictData?.data?.conflicts || [])
  ];
  const hasHighSeverityConflict = allConflicts.some(c => c.severity === 'high');
  const canProceed = clientInfo.name && (clientInfo.email || clientInfo.phone) && !hasHighSeverityConflict;

  return (
    <div className="space-y-8">
      {/* Client Information */}
      <div>
        <h2 className={`font-semibold text-gray-900 mb-6 flex items-center ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          <User className="w-6 h-6 mr-3" />
          {getSimpleText('Client Information')}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="md:col-span-2">
            <SimpleModeInput
              label="Full Name"
              value={clientInfo.name}
              onChange={(e) => handleClientChange('name', e.target.value)}
              placeholder="Enter client's full name"
              required
            />
            
            {/* Client Conflict Alert */}
            {clientInfo.name.length >= 3 && clientConflictData?.data?.conflicts && 
             clientConflictData.data.conflicts.length > 0 && (
              <ConflictAlert 
                conflicts={clientConflictData.data.conflicts}
                searchTerm={clientInfo.name}
                type="client"
              />
            )}
          </div>

          <SimpleModeInput
            label="Email Address"
            type="email"
            value={clientInfo.email}
            onChange={(e) => handleClientChange('email', e.target.value)}
            placeholder="[CLIENT-EMAIL]"
          />

          <SimpleModeInput
            label="Phone Number"
            type="tel"
            value={clientInfo.phone}
            onChange={(e) => handleClientChange('phone', e.target.value)}
            placeholder="[PHONE-NUMBER]"
          />

          <div className="md:col-span-2">
            <SimpleModeInput
              label="Address"
              value={clientInfo.address}
              onChange={(e) => handleClientChange('address', e.target.value)}
              placeholder="Street address, City, State ZIP"
            />
          </div>

          <SimpleModeInput
            label="Date of Birth"
            type="date"
            value={clientInfo.dateOfBirth}
            onChange={(e) => handleClientChange('dateOfBirth', e.target.value)}
          />
        </div>
      </div>

      {/* Adverse Party Information */}
      <div>
        <h2 className={`font-semibold text-gray-900 mb-6 flex items-center ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          <Shield className="w-6 h-6 mr-3" />
          {getSimpleText('Adverse Party Information')}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="md:col-span-2">
            <SimpleModeInput
              label="Adverse Party Name"
              value={adverseParty.name}
              onChange={(e) => handleAdverseChange('name', e.target.value)}
              placeholder="Enter adverse party's name"
            />
            
            {/* Adverse Party Conflict Alert */}
            {adverseParty.name.length >= 3 && adverseConflictData?.data?.conflicts && 
             adverseConflictData.data.conflicts.length > 0 && (
              <ConflictAlert 
                conflicts={adverseConflictData.data.conflicts}
                searchTerm={adverseParty.name}
                type="adverse"
              />
            )}
          </div>

          <div className="md:col-span-2">
            <SimpleModeInput
              label="Adverse Party's Attorney"
              value={adverseParty.attorney}
              onChange={(e) => handleAdverseChange('attorney', e.target.value)}
              placeholder="Attorney name (if known)"
            />
          </div>
        </div>
      </div>

      {/* High Severity Conflict Warning */}
      {hasHighSeverityConflict && (
        <SimpleModeAlert type="error">
          <div>
            <p className="font-semibold mb-2">
              {getSimpleText('Conflict Check Failed')}
            </p>
            <p>
              {getSimpleText('High severity conflicts must be resolved before proceeding. Please contact your conflicts administrator.')}
            </p>
          </div>
        </SimpleModeAlert>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between">
        <button
          onClick={onBack}
          className={`
            flex items-center px-6 py-3 rounded-lg font-medium transition-all
            bg-gray-200 text-gray-700 hover:bg-gray-300
            ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
          `}
        >
          {getSimpleText('Back')}
        </button>

        <button
          onClick={onNext}
          disabled={!canProceed}
          className={`
            flex items-center px-6 py-3 rounded-lg font-medium transition-all
            ${canProceed
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }
            ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
          `}
        >
          {getSimpleText('Continue')}
          <ChevronRight className="w-5 h-5 ml-2" />
        </button>
      </div>
    </div>
  );
};

// Conflict Alert Component
interface ConflictAlertProps {
  conflicts: Conflict[];
  searchTerm: string;
  type: 'client' | 'adverse';
}

const ConflictAlert: React.FC<ConflictAlertProps> = ({ conflicts, searchTerm, type }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const highSeverity = conflicts.filter(c => c.severity === 'high');
  const mediumSeverity = conflicts.filter(c => c.severity === 'medium');
  const lowSeverity = conflicts.filter(c => c.severity === 'low');
  
  const alertType = highSeverity.length > 0 ? 'error' : 
                   mediumSeverity.length > 0 ? 'warning' : 'info';
  
  return (
    <div className={`mt-4 p-4 rounded-lg border-2 ${
      alertType === 'error' ? 'bg-red-50 border-red-200' :
      alertType === 'warning' ? 'bg-yellow-50 border-yellow-200' :
      'bg-blue-50 border-blue-200'
    }`}>
      <div className="flex items-start">
        <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 mr-3 ${
          alertType === 'error' ? 'text-red-600' :
          alertType === 'warning' ? 'text-yellow-600' :
          'text-blue-600'
        }`} />
        
        <div className="flex-1">
          <h4 className={`font-semibold mb-2 ${
            alertType === 'error' ? 'text-red-900' :
            alertType === 'warning' ? 'text-yellow-900' :
            'text-blue-900'
          } ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
            {getSimpleText(`Potential conflicts found for "${searchTerm}"`)}
          </h4>
          
          <div className="space-y-2">
            {conflicts.map((conflict) => (
              <div 
                key={conflict.id}
                className={`p-3 rounded-lg ${
                  conflict.severity === 'high' ? 'bg-red-100' :
                  conflict.severity === 'medium' ? 'bg-yellow-100' :
                  'bg-blue-100'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className={`font-medium ${
                      conflict.severity === 'high' ? 'text-red-900' :
                      conflict.severity === 'medium' ? 'text-yellow-900' :
                      'text-blue-900'
                    } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                      {conflict.name} - {getSimpleText(conflict.type)}
                    </p>
                    <p className={`mt-1 ${
                      conflict.severity === 'high' ? 'text-red-700' :
                      conflict.severity === 'medium' ? 'text-yellow-700' :
                      'text-blue-700'
                    } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                      {getSimpleText(conflict.conflictDetails)}
                    </p>
                    {conflict.matterNumber && (
                      <p className={`mt-1 ${
                        conflict.severity === 'high' ? 'text-red-600' :
                        conflict.severity === 'medium' ? 'text-yellow-600' :
                        'text-blue-600'
                      } ${isSimpleMode ? 'text-sm' : 'text-xs'}`}>
                        Matter #: {conflict.matterNumber}
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ml-3 ${
                    conflict.severity === 'high' ? 'bg-red-200 text-red-800' :
                    conflict.severity === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                    'bg-blue-200 text-blue-800'
                  }`}>
                    {getSimpleText(conflict.severity)}
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          {type === 'client' && highSeverity.length === 0 && (
            <p className={`mt-3 text-gray-600 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
              {mediumSeverity.length > 0 
                ? getSimpleText('Review these potential conflicts with your supervisor before proceeding.')
                : getSimpleText('These are informational only and do not prevent proceeding.')
              }
            </p>
          )}
        </div>
      </div>
    </div>
  );
};