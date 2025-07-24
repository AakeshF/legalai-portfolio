import React, { useState, useEffect } from 'react';
import { 
  FileText, Gavel, Calendar, Building, Search, 
  Loader2, CheckCircle, Info, ChevronRight 
} from 'lucide-react';
import { StepProps } from '../CaseIntakeWizard';
import { useCourtCaseLookup, CourtCase } from '../../../services/mcp';
import { useSimpleMode } from '../../../contexts/SimpleModeContext';
import { SimpleModeInput, SimpleModeAlert, SimpleModeCard } from '../../SimpleModeWrapper';
import debounce from 'lodash.debounce';

export const MatterDetailsStep: React.FC<StepProps> = ({ 
  data, 
  updateData, 
  onNext,
  onBack 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const [matterDetails, setMatterDetails] = useState({
    description: data.matter?.description || '',
    caseNumber: data.matter?.caseNumber || '',
    courtName: data.matter?.courtName || '',
    judge: data.matter?.judge || '',
    nextHearing: data.matter?.nextHearing || '',
    filingDeadline: data.matter?.filingDeadline || ''
  });

  const [lookupCaseNumber, setLookupCaseNumber] = useState('');

  // Court case lookup
  const { 
    data: courtCaseData, 
    isLoading: isLoadingCase,
    isFetching: isFetchingCase
  } = useCourtCaseLookup(lookupCaseNumber);

  // Debounced case number lookup
  const debouncedCaseLookup = React.useCallback(
    debounce((caseNumber: string) => {
      if (caseNumber.length > 5) {
        setLookupCaseNumber(caseNumber);
      }
    }, 1000),
    []
  );

  useEffect(() => {
    debouncedCaseLookup(matterDetails.caseNumber);
  }, [matterDetails.caseNumber, debouncedCaseLookup]);

  // Auto-populate from court data
  useEffect(() => {
    if (courtCaseData?.data) {
      const courtData = courtCaseData.data;
      setMatterDetails(prev => ({
        ...prev,
        courtName: courtData.courtName || prev.courtName,
        judge: courtData.judge || prev.judge,
        nextHearing: courtData.nextHearing 
          ? new Date(courtData.nextHearing).toISOString().split('T')[0]
          : prev.nextHearing
      }));
    }
  }, [courtCaseData]);

  // Update parent data
  useEffect(() => {
    updateData({ matter: matterDetails });
  }, [matterDetails, updateData]);

  const handleChange = (field: string, value: string) => {
    setMatterDetails(prev => ({ ...prev, [field]: value }));
  };

  const canProceed = matterDetails.description.trim().length > 0;

  return (
    <div className="space-y-8">
      {/* Matter Description */}
      <div>
        <h2 className={`font-semibold text-gray-900 mb-6 flex items-center ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          <FileText className="w-6 h-6 mr-3" />
          {getSimpleText('Matter Details')}
        </h2>

        <div className="space-y-6">
          <div>
            <label className={`block font-medium text-gray-700 mb-2 ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              {getSimpleText('Matter Description')} *
            </label>
            <textarea
              value={matterDetails.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder={getSimpleText('Describe the legal matter in detail...')}
              rows={4}
              className={`
                w-full rounded-lg border border-gray-300 
                focus:outline-none focus:ring-2 focus:ring-blue-500
                ${isSimpleMode ? 'px-4 py-3 text-lg' : 'px-3 py-2 text-base'}
              `}
              required
            />
            <p className={`mt-2 text-gray-500 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
              {getSimpleText('Provide a clear summary of the legal issue and desired outcome')}
            </p>
          </div>
        </div>
      </div>

      {/* Court Information */}
      <div>
        <h2 className={`font-semibold text-gray-900 mb-6 flex items-center ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          <Building className="w-6 h-6 mr-3" />
          {getSimpleText('Court Information')}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="md:col-span-2">
            <div className="relative">
              <SimpleModeInput
                label="Case Number"
                value={matterDetails.caseNumber}
                onChange={(e) => handleChange('caseNumber', e.target.value)}
                placeholder="Enter existing case number (if any)"
              />
              {(isLoadingCase || isFetchingCase) && matterDetails.caseNumber.length > 5 && (
                <div className="absolute right-3 top-9 text-blue-600">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
              )}
              {courtCaseData?.data && !isLoadingCase && !isFetchingCase && (
                <div className="absolute right-3 top-9 text-green-600">
                  <CheckCircle className="w-5 h-5" />
                </div>
              )}
            </div>
            
            {/* Court Case Info Card */}
            {courtCaseData?.data && (
              <CourtCaseInfoCard courtCase={courtCaseData.data} />
            )}
          </div>

          <SimpleModeInput
            label="Court Name"
            value={matterDetails.courtName}
            onChange={(e) => handleChange('courtName', e.target.value)}
            placeholder="e.g., Superior Court of California"
          />

          <SimpleModeInput
            label="Judge Name"
            value={matterDetails.judge}
            onChange={(e) => handleChange('judge', e.target.value)}
            placeholder="Judge's name (if known)"
          />

          <SimpleModeInput
            label="Next Hearing Date"
            type="date"
            value={matterDetails.nextHearing}
            onChange={(e) => handleChange('nextHearing', e.target.value)}
          />

          <SimpleModeInput
            label="Filing Deadline"
            type="date"
            value={matterDetails.filingDeadline}
            onChange={(e) => handleChange('filingDeadline', e.target.value)}
          />
        </div>
      </div>

      {/* Court-specific Requirements Alert */}
      {matterDetails.courtName && data.jurisdiction && (
        <SimpleModeAlert type="info">
          <div className="flex items-start">
            <Info className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium mb-1">
                {getSimpleText('Court Requirements')}
              </p>
              <p>
                {getSimpleText(`The ${matterDetails.courtName} in ${data.jurisdiction} may have specific filing requirements. These will be shown in the next step.`)}
              </p>
            </div>
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

// Court Case Info Card Component
interface CourtCaseInfoCardProps {
  courtCase: CourtCase;
}

const CourtCaseInfoCard: React.FC<CourtCaseInfoCardProps> = ({ courtCase }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  return (
    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg animate-fade-in">
      <div className="flex items-start">
        <Gavel className="w-5 h-5 text-blue-600 mr-3 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className={`font-semibold text-blue-900 mb-2 ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            {getSimpleText('Case Information Found')}
          </h4>
          
          <div className="space-y-2">
            <div className="flex items-start">
              <span className={`text-blue-700 font-medium min-w-[100px] ${
                isSimpleMode ? 'text-base' : 'text-sm'
              }`}>
                {getSimpleText('Status')}:
              </span>
              <span className={`text-blue-900 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                {getSimpleText(courtCase.status)}
              </span>
            </div>
            
            {courtCase.filingDate && (
              <div className="flex items-start">
                <span className={`text-blue-700 font-medium min-w-[100px] ${
                  isSimpleMode ? 'text-base' : 'text-sm'
                }`}>
                  {getSimpleText('Filed')}:
                </span>
                <span className={`text-blue-900 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                  {new Date(courtCase.filingDate).toLocaleDateString()}
                </span>
              </div>
            )}
            
            {courtCase.parties && courtCase.parties.length > 0 && (
              <div>
                <p className={`text-blue-700 font-medium mb-1 ${
                  isSimpleMode ? 'text-base' : 'text-sm'
                }`}>
                  {getSimpleText('Parties')}:
                </p>
                <ul className="ml-4 space-y-1">
                  {courtCase.parties.map((party, index) => (
                    <li key={index} className={`text-blue-900 ${
                      isSimpleMode ? 'text-base' : 'text-sm'
                    }`}>
                      • {party.name} ({getSimpleText(party.role)})
                      {party.represented && party.attorney && (
                        <span className="text-blue-700">
                          {' '}- {getSimpleText('Represented by')}: {party.attorney}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
          <p className={`mt-3 text-blue-600 italic ${
            isSimpleMode ? 'text-sm' : 'text-xs'
          }`}>
            {getSimpleText('This information has been auto-populated from court records')}
          </p>
        </div>
      </div>
    </div>
  );
};