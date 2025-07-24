import React, { useState, useEffect, useCallback } from 'react';
import { Shield, Eye, EyeOff, Edit3, Check, X, AlertCircle } from 'lucide-react';
import { SensitiveDataDetector, detectSensitiveData } from './SensitiveDataDetector';
import { RedactedSegment, AnonymizationResult, SensitiveDataPattern } from '../../types/anonymization';

interface PromptAnonymizerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (original: string, redacted: string, segments: RedactedSegment[]) => void;
  autoRedaction?: boolean;
  customPatterns?: SensitiveDataPattern[];
  className?: string;
}

export const PromptAnonymizer: React.FC<PromptAnonymizerProps> = ({
  value,
  onChange,
  onSubmit,
  autoRedaction = true,
  customPatterns = [],
  className = ''
}) => {
  const [viewMode, setViewMode] = useState<'original' | 'redacted' | 'side-by-side'>('side-by-side');
  const [isEditing, setIsEditing] = useState(false);
  const [editedRedacted, setEditedRedacted] = useState('');
  const [segments, setSegments] = useState<RedactedSegment[]>([]);
  const [anonymizationResult, setAnonymizationResult] = useState<AnonymizationResult | null>(null);

  useEffect(() => {
    if (value && autoRedaction) {
      const result = detectSensitiveData(value, undefined, customPatterns);
      setAnonymizationResult(result);
      setSegments(result.segments);
      setEditedRedacted(result.redacted);
    } else {
      setAnonymizationResult(null);
      setSegments([]);
      setEditedRedacted(value);
    }
  }, [value, autoRedaction, customPatterns]);

  const handleSegmentToggle = useCallback((segment: RedactedSegment) => {
    const updatedSegments = segments.map(s => 
      s.start === segment.start ? { ...s, isManuallyToggled: !s.isManuallyToggled } : s
    );
    setSegments(updatedSegments);
    
    let redactedText = value;
    let offset = 0;
    
    updatedSegments.forEach(seg => {
      const replacement = seg.isManuallyToggled ? seg.original : seg.redacted;
      const start = seg.start + offset;
      const end = start + (seg.isManuallyToggled ? seg.redacted.length : seg.original.length);
      
      redactedText = redactedText.slice(0, start) + replacement + redactedText.slice(end);
      offset += replacement.length - (seg.isManuallyToggled ? seg.redacted.length : seg.original.length);
    });
    
    setEditedRedacted(redactedText);
  }, [segments, value]);

  const handleEditSave = () => {
    setIsEditing(false);
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    if (anonymizationResult) {
      setEditedRedacted(anonymizationResult.redacted);
    }
  };

  const handleSubmitClick = () => {
    onSubmit(value, editedRedacted, segments);
  };

  const hasSensitiveData = segments.length > 0;

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Prompt Anonymization</h3>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('original')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'original' 
                  ? 'bg-white text-gray-900 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Eye className="w-4 h-4 inline mr-1" />
              Original
            </button>
            <button
              onClick={() => setViewMode('redacted')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'redacted' 
                  ? 'bg-white text-gray-900 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <EyeOff className="w-4 h-4 inline mr-1" />
              Redacted
            </button>
            <button
              onClick={() => setViewMode('side-by-side')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'side-by-side' 
                  ? 'bg-white text-gray-900 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Side by Side
            </button>
          </div>
        </div>
      </div>

      {hasSensitiveData && (
        <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-800">Sensitive Data Detected</p>
            <p className="text-sm text-amber-700 mt-1">
              We've automatically redacted {segments.length} sensitive element{segments.length > 1 ? 's' : ''}.
              Click on highlighted items to toggle redaction.
            </p>
          </div>
        </div>
      )}

      <div className={`grid ${viewMode === 'side-by-side' ? 'grid-cols-2 gap-4' : 'grid-cols-1'}`}>
        {(viewMode === 'original' || viewMode === 'side-by-side') && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700">Original Prompt</label>
              <span className="text-xs text-gray-500">{value.length} characters</span>
            </div>
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full h-48 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your prompt here..."
            />
          </div>
        )}

        {(viewMode === 'redacted' || viewMode === 'side-by-side') && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700">Redacted Version</label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">{editedRedacted.length} characters</span>
                {!isEditing ? (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                ) : (
                  <div className="flex gap-1">
                    <button
                      onClick={handleEditSave}
                      className="text-green-600 hover:text-green-700"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleEditCancel}
                      className="text-red-600 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
            
            {isEditing ? (
              <textarea
                value={editedRedacted}
                onChange={(e) => setEditedRedacted(e.target.value)}
                className="w-full h-48 p-3 border border-blue-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            ) : (
              <div className="h-48 p-3 border border-gray-300 rounded-lg overflow-y-auto bg-gray-50">
                <SensitiveDataDetector
                  text={value}
                  onRedactionToggle={handleSegmentToggle}
                  customPatterns={customPatterns}
                  showOriginal={false}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {viewMode !== 'side-by-side' && hasSensitiveData && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Detected Sensitive Data</h4>
          <SensitiveDataDetector
            text={value}
            onRedactionToggle={handleSegmentToggle}
            customPatterns={customPatterns}
            showOriginal={viewMode === 'original'}
          />
        </div>
      )}

      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          onClick={() => onChange('')}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
        >
          Clear
        </button>
        <button
          onClick={handleSubmitClick}
          disabled={!value.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Shield className="w-4 h-4" />
          Submit Anonymized Prompt
        </button>
      </div>
    </div>
  );
};