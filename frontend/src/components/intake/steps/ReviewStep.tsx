import React, { useState } from 'react';
import { 
  CheckCircle, AlertTriangle, FileText, User, 
  Gavel, MapPin, Calendar, Loader2, Send,
  Download, Eye, Shield
} from 'lucide-react';
import { StepProps } from '../CaseIntakeWizard';
import { useSaveCaseIntake } from '../../../services/mcp';
import { useSimpleMode } from '../../../contexts/SimpleModeContext';
import { SimpleModeCard, SimpleModeAlert, SimpleModeButton } from '../../SimpleModeWrapper';
import { useNavigate } from 'react-router-dom';

export const ReviewStep: React.FC<StepProps> = ({ 
  data, 
  onBack 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  
  const saveCaseIntake = useSaveCaseIntake();

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    
    try {
      await saveCaseIntake.mutateAsync(data);
      setSubmitSuccess(true);
      
      // Redirect after success
      setTimeout(() => {
        navigate('/');
      }, 3000);
    } catch (error: any) {
      setSubmitError(error.message || 'Failed to submit case intake');
      setIsSubmitting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (submitSuccess) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
        <h2 className={`font-bold text-gray-900 mb-2 ${
          isSimpleMode ? 'text-3xl' : 'text-2xl'
        }`}>
          {getSimpleText('Case Intake Submitted Successfully!')}
        </h2>
        <p className={`text-gray-600 mb-6 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
          {getSimpleText('Your new case has been created and is ready for processing.')}
        </p>
        <p className={`text-gray-500 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
          {getSimpleText('Redirecting to dashboard...')}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className={`font-semibold text-gray-900 mb-2 ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          {getSimpleText('Review Your Information')}
        </h2>
        <p className={`text-gray-600 mb-6 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
          {getSimpleText('Please review all information before submitting')}
        </p>
      </div>

      {/* Case Type & Jurisdiction */}
      <SimpleModeCard title="Case Information">
        <div className="space-y-3">
          <InfoRow 
            icon={<FileText className="w-5 h-5" />}
            label="Case Type"
            value={data.caseType || 'Not selected'}
          />
          <InfoRow 
            icon={<MapPin className="w-5 h-5" />}
            label="Jurisdiction"
            value={data.jurisdiction || 'Not selected'}
          />
        </div>
      </SimpleModeCard>

      {/* Client Information */}
      <SimpleModeCard title="Client Information">
        <div className="space-y-3">
          <InfoRow 
            icon={<User className="w-5 h-5" />}
            label="Client Name"
            value={data.client?.name || 'Not provided'}
          />
          <InfoRow 
            label="Email"
            value={data.client?.email || 'Not provided'}
          />
          <InfoRow 
            label="Phone"
            value={data.client?.phone || 'Not provided'}
          />
          <InfoRow 
            label="Address"
            value={data.client?.address || 'Not provided'}
          />
          {data.client?.dateOfBirth && (
            <InfoRow 
              label="Date of Birth"
              value={new Date(data.client.dateOfBirth).toLocaleDateString()}
            />
          )}
        </div>
      </SimpleModeCard>

      {/* Adverse Party */}
      {data.adverseParty?.name && (
        <SimpleModeCard title="Adverse Party">
          <div className="space-y-3">
            <InfoRow 
              icon={<Shield className="w-5 h-5" />}
              label="Name"
              value={data.adverseParty.name}
            />
            {data.adverseParty.attorney && (
              <InfoRow 
                label="Attorney"
                value={data.adverseParty.attorney}
              />
            )}
          </div>
        </SimpleModeCard>
      )}

      {/* Matter Details */}
      <SimpleModeCard title="Matter Details">
        <div className="space-y-3">
          <div>
            <p className={`font-medium text-gray-700 mb-1 ${
              isSimpleMode ? 'text-lg' : 'text-base'
            }`}>
              {getSimpleText('Description')}
            </p>
            <p className={`text-gray-900 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
              {data.matter?.description || 'Not provided'}
            </p>
          </div>
          
          {data.matter?.caseNumber && (
            <InfoRow 
              icon={<Gavel className="w-5 h-5" />}
              label="Case Number"
              value={data.matter.caseNumber}
            />
          )}
          {data.matter?.courtName && (
            <InfoRow 
              label="Court"
              value={data.matter.courtName}
            />
          )}
          {data.matter?.judge && (
            <InfoRow 
              label="Judge"
              value={data.matter.judge}
            />
          )}
          {data.matter?.nextHearing && (
            <InfoRow 
              icon={<Calendar className="w-5 h-5" />}
              label="Next Hearing"
              value={new Date(data.matter.nextHearing).toLocaleDateString()}
            />
          )}
          {data.matter?.filingDeadline && (
            <InfoRow 
              label="Filing Deadline"
              value={new Date(data.matter.filingDeadline).toLocaleDateString()}
            />
          )}
        </div>
      </SimpleModeCard>

      {/* Conflicts */}
      {data.conflicts && data.conflicts.length > 0 && (
        <SimpleModeCard 
          title="Conflict Check Results"
          className="border-yellow-200 bg-yellow-50"
        >
          <div className="space-y-2">
            {data.conflicts.map((conflict, index) => (
              <div key={index} className="flex items-start">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
                <div>
                  <p className={`font-medium text-yellow-900 ${
                    isSimpleMode ? 'text-base' : 'text-sm'
                  }`}>
                    {conflict.name} ({getSimpleText(conflict.type)})
                  </p>
                  <p className={`text-yellow-700 ${
                    isSimpleMode ? 'text-sm' : 'text-xs'
                  }`}>
                    {getSimpleText(conflict.conflictDetails)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </SimpleModeCard>
      )}

      {/* Submit Error */}
      {submitError && (
        <SimpleModeAlert type="error">
          <div>
            <p className="font-medium">{getSimpleText('Submission Failed')}</p>
            <p className="mt-1">{getSimpleText(submitError)}</p>
          </div>
        </SimpleModeAlert>
      )}

      {/* Action Buttons */}
      <div className="space-y-4">
        <div className="flex justify-between">
          <button
            onClick={onBack}
            disabled={isSubmitting}
            className={`
              flex items-center px-6 py-3 rounded-lg font-medium transition-all
              ${isSubmitting 
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }
              ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
            `}
          >
            {getSimpleText('Back')}
          </button>

          <div className="flex space-x-3">
            <button
              onClick={handlePrint}
              disabled={isSubmitting}
              className={`
                flex items-center px-6 py-3 rounded-lg font-medium transition-all
                bg-white border-2 border-gray-300 text-gray-700 hover:bg-gray-50
                ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
              `}
            >
              <Download className="w-5 h-5 mr-2" />
              {getSimpleText('Print')}
            </button>

            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className={`
                flex items-center px-6 py-3 rounded-lg font-medium transition-all
                ${isSubmitting 
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
                  : 'bg-green-600 text-white hover:bg-green-700'
                }
                ${isSimpleMode ? 'text-lg min-h-[56px]' : 'text-base'}
              `}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  {getSimpleText('Submitting...')}
                </>
              ) : (
                <>
                  <Send className="w-5 h-5 mr-2" />
                  {getSimpleText('Submit Case Intake')}
                </>
              )}
            </button>
          </div>
        </div>

        {/* Submission Notice */}
        <p className={`text-center text-gray-600 ${
          isSimpleMode ? 'text-base' : 'text-sm'
        }`}>
          {getSimpleText('By submitting, you confirm that all information provided is accurate and complete.')}
        </p>
      </div>
    </div>
  );
};

// Info Row Component
interface InfoRowProps {
  icon?: React.ReactNode;
  label: string;
  value: string;
}

const InfoRow: React.FC<InfoRowProps> = ({ icon, label, value }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  return (
    <div className="flex items-start">
      {icon && (
        <div className="text-gray-400 mr-3 mt-0.5">
          {icon}
        </div>
      )}
      <div className="flex-1 grid grid-cols-3 gap-4">
        <span className={`font-medium text-gray-600 ${
          isSimpleMode ? 'text-base' : 'text-sm'
        }`}>
          {getSimpleText(label)}:
        </span>
        <span className={`col-span-2 text-gray-900 ${
          isSimpleMode ? 'text-base' : 'text-sm'
        }`}>
          {value}
        </span>
      </div>
    </div>
  );
};