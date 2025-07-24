import React, { useState, useEffect } from 'react';
import { 
  Scale, Users, Shield, Briefcase, Home, Globe, 
  Loader2, AlertCircle, ChevronRight 
} from 'lucide-react';
import { StepProps } from '../CaseIntakeWizard';
import { useMCPQuery } from '../../../services/mcp';
import { useSimpleMode } from '../../../contexts/SimpleModeContext';
import { SimpleModeCard } from '../../SimpleModeWrapper';

interface CaseType {
  id: string;
  name: string;
  icon: string;
  description?: string;
  requiresJurisdiction: boolean;
}

interface Jurisdiction {
  id: string;
  name: string;
  hasStateCourts: boolean;
  hasFederalCourts: boolean;
}

const iconMap: Record<string, React.ComponentType<any>> = {
  'user-x': Scale,
  'users': Users,
  'shield': Shield,
  'briefcase': Briefcase,
  'home': Home,
  'globe': Globe
};

export const CaseTypeStep: React.FC<StepProps> = ({ 
  data, 
  updateData, 
  onNext 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const [selectedType, setSelectedType] = useState(data.caseType || '');
  const [selectedJurisdiction, setSelectedJurisdiction] = useState(data.jurisdiction || '');

  // Query case types from MCP
  const { 
    data: caseTypesResponse, 
    isLoading: loadingTypes, 
    error: typesError 
  } = useMCPQuery<CaseType[]>(
    ['case_types'],
    {
      server: 'legal_data',
      action: 'get_case_types'
    }
  );

  // Query jurisdictions from MCP
  const { 
    data: jurisdictionsResponse, 
    isLoading: loadingJurisdictions, 
    error: jurisdictionsError 
  } = useMCPQuery<Jurisdiction[]>(
    ['jurisdictions'],
    {
      server: 'legal_data',
      action: 'get_jurisdictions'
    },
    {
      enabled: !!selectedType // Only fetch when case type is selected
    }
  );

  const caseTypes = caseTypesResponse?.data || [];
  const jurisdictions = jurisdictionsResponse?.data || [];

  // Query jurisdiction-specific requirements when both are selected
  const { 
    data: requirementsResponse,
    isLoading: loadingRequirements 
  } = useMCPQuery(
    ['jurisdiction_requirements', selectedType, selectedJurisdiction],
    {
      server: 'legal_data',
      action: 'get_jurisdiction_requirements',
      params: {
        caseType: selectedType,
        jurisdiction: selectedJurisdiction
      }
    },
    {
      enabled: !!selectedType && !!selectedJurisdiction
    }
  );

  const handleCaseTypeSelect = (typeId: string) => {
    setSelectedType(typeId);
    setSelectedJurisdiction(''); // Reset jurisdiction when case type changes
    updateData({ caseType: typeId, jurisdiction: undefined });
  };

  const handleJurisdictionSelect = (jurisdictionId: string) => {
    setSelectedJurisdiction(jurisdictionId);
    updateData({ jurisdiction: jurisdictionId });
  };

  const canProceed = selectedType && selectedJurisdiction;

  return (
    <div className="space-y-8">
      {/* Case Type Selection */}
      <div>
        <h2 className={`font-semibold text-gray-900 mb-4 ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          {getSimpleText('Select Case Type')}
        </h2>
        
        {loadingTypes ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">
              {getSimpleText('Loading case types...')}
            </span>
          </div>
        ) : typesError ? (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start">
              <AlertCircle className="w-5 h-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
              <div>
                <p className={`text-yellow-800 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                  {getSimpleText('Using offline case types')}
                </p>
                <p className={`text-yellow-700 mt-1 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                  {getSimpleText('Some features may be limited')}
                </p>
              </div>
            </div>
          </div>
        ) : null}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {caseTypes.map((type) => {
            const Icon = iconMap[type.icon] || Scale;
            const isSelected = selectedType === type.id;
            
            return (
              <button
                key={type.id}
                onClick={() => handleCaseTypeSelect(type.id)}
                className={`
                  p-6 rounded-lg border-2 transition-all text-left
                  ${isSelected 
                    ? 'border-blue-600 bg-blue-50' 
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                  }
                  ${isSimpleMode ? 'min-h-[120px]' : ''}
                `}
              >
                <div className="flex items-start space-x-4">
                  <div className={`
                    p-3 rounded-lg
                    ${isSelected ? 'bg-blue-600' : 'bg-gray-100'}
                  `}>
                    <Icon className={`
                      ${isSelected ? 'text-white' : 'text-gray-600'}
                      ${isSimpleMode ? 'w-8 h-8' : 'w-6 h-6'}
                    `} />
                  </div>
                  <div className="flex-1">
                    <h3 className={`
                      font-semibold
                      ${isSelected ? 'text-blue-900' : 'text-gray-900'}
                      ${isSimpleMode ? 'text-xl' : 'text-lg'}
                    `}>
                      {getSimpleText(type.name)}
                    </h3>
                    {type.description && (
                      <p className={`
                        mt-1
                        ${isSelected ? 'text-blue-700' : 'text-gray-600'}
                        ${isSimpleMode ? 'text-base' : 'text-sm'}
                      `}>
                        {getSimpleText(type.description)}
                      </p>
                    )}
                  </div>
                  {isSelected && (
                    <div className="text-blue-600">
                      <ChevronRight className="w-5 h-5" />
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Jurisdiction Selection */}
      {selectedType && (
        <div className="animate-fade-in">
          <h2 className={`font-semibold text-gray-900 mb-4 ${
            isSimpleMode ? 'text-2xl' : 'text-xl'
          }`}>
            {getSimpleText('Select Jurisdiction')}
          </h2>

          {loadingJurisdictions ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span className="ml-3 text-gray-600">
                {getSimpleText('Loading jurisdictions...')}
              </span>
            </div>
          ) : (
            <div className="space-y-3">
              {jurisdictions.map((jurisdiction) => (
                <button
                  key={jurisdiction.id}
                  onClick={() => handleJurisdictionSelect(jurisdiction.id)}
                  className={`
                    w-full p-4 rounded-lg border-2 transition-all text-left
                    ${selectedJurisdiction === jurisdiction.id
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                    }
                  `}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className={`
                        font-medium
                        ${selectedJurisdiction === jurisdiction.id ? 'text-blue-900' : 'text-gray-900'}
                        ${isSimpleMode ? 'text-xl' : 'text-lg'}
                      `}>
                        {jurisdiction.name}
                      </h3>
                      <div className={`flex items-center space-x-4 mt-1 ${
                        isSimpleMode ? 'text-base' : 'text-sm'
                      }`}>
                        {jurisdiction.hasFederalCourts && (
                          <span className="text-gray-600">
                            {getSimpleText('Federal Courts')}
                          </span>
                        )}
                        {jurisdiction.hasStateCourts && (
                          <span className="text-gray-600">
                            {getSimpleText('State Courts')}
                          </span>
                        )}
                      </div>
                    </div>
                    {selectedJurisdiction === jurisdiction.id && (
                      <div className="text-blue-600">
                        <ChevronRight className="w-5 h-5" />
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Jurisdiction-specific Requirements */}
      {selectedType && selectedJurisdiction && requirementsResponse?.data && (
        <SimpleModeCard 
          title="Jurisdiction Requirements"
          className="border-blue-200 bg-blue-50"
        >
          {loadingRequirements ? (
            <div className="flex items-center">
              <Loader2 className="w-5 h-5 animate-spin text-blue-600 mr-3" />
              <span className="text-blue-800">
                {getSimpleText('Loading requirements...')}
              </span>
            </div>
          ) : (
            <div className="space-y-3">
              {requirementsResponse.data.requirements?.map((req: any, index: number) => (
                <div key={index} className="flex items-start">
                  <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 mr-3 flex-shrink-0" />
                  <p className={`text-blue-800 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                    {getSimpleText(req)}
                  </p>
                </div>
              ))}
              {requirementsResponse.data.filingFee && (
                <div className="mt-4 pt-4 border-t border-blue-200">
                  <p className={`text-blue-900 font-medium ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                    {getSimpleText('Filing Fee')}: ${requirementsResponse.data.filingFee}
                  </p>
                </div>
              )}
            </div>
          )}
        </SimpleModeCard>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end">
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