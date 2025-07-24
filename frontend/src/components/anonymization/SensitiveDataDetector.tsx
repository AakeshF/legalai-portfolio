import React, { useMemo } from 'react';
import { AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { SensitiveDataPattern, RedactedSegment, AnonymizationResult } from '../../types/anonymization';

const DEFAULT_PATTERNS: SensitiveDataPattern[] = [
  {
    id: 'ssn',
    type: 'personal',
    pattern: /\b\d{3}-\d{2}-\d{4}\b/g,
    replacement: '[SSN]',
    severity: 'critical',
    description: 'Social Security Number'
  },
  {
    id: 'email',
    type: 'personal',
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    replacement: '[EMAIL]',
    severity: 'medium',
    description: 'Email Address'
  },
  {
    id: 'phone',
    type: 'personal',
    pattern: /\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b/g,
    replacement: '[PHONE]',
    severity: 'medium',
    description: 'Phone Number'
  },
  {
    id: 'credit-card',
    type: 'financial',
    pattern: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b/g,
    replacement: '[CREDIT_CARD]',
    severity: 'critical',
    description: 'Credit Card Number'
  },
  {
    id: 'case-number',
    type: 'legal',
    pattern: /\b(?:Case\s*(?:No\.?|Number)?:?\s*)?([A-Z]{2,}-?\d{2,}-?\d{3,})\b/gi,
    replacement: '[CASE_NUMBER]',
    severity: 'high',
    description: 'Legal Case Number'
  },
  {
    id: 'name',
    type: 'personal',
    pattern: /\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b/g,
    replacement: '[NAME]',
    severity: 'high',
    description: 'Personal Name with Title'
  },
  {
    id: 'address',
    type: 'personal',
    pattern: /\b\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Plaza|Pl)\b/gi,
    replacement: '[ADDRESS]',
    severity: 'high',
    description: 'Street Address'
  },
  {
    id: 'dob',
    type: 'personal',
    pattern: /\b(?:0[1-9]|1[0-2])[\/\-](?:0[1-9]|[12]\d|3[01])[\/\-](?:19|20)\d{2}\b/g,
    replacement: '[DOB]',
    severity: 'high',
    description: 'Date of Birth'
  },
  {
    id: 'bank-account',
    type: 'financial',
    pattern: /\b(?:Account\s*(?:No\.?|Number)?:?\s*)?[0-9]{8,17}\b/gi,
    replacement: '[ACCOUNT_NUMBER]',
    severity: 'critical',
    description: 'Bank Account Number'
  }
];

export function detectSensitiveData(
  text: string,
  patterns: SensitiveDataPattern[] = DEFAULT_PATTERNS,
  customPatterns: SensitiveDataPattern[] = []
): AnonymizationResult {
  const allPatterns = [...patterns, ...customPatterns];
  const segments: RedactedSegment[] = [];
  const detectedTypes = new Set<string>();
  
  let workingText = text;
  const replacements: Array<{ start: number; end: number; pattern: SensitiveDataPattern; match: string }> = [];
  
  allPatterns.forEach(pattern => {
    const regex = typeof pattern.pattern === 'string' 
      ? new RegExp(pattern.pattern, 'gi') 
      : new RegExp(pattern.pattern.source, pattern.pattern.flags || 'gi');
    
    let match;
    while ((match = regex.exec(text)) !== null) {
      replacements.push({
        start: match.index,
        end: match.index + match[0].length,
        pattern,
        match: match[0]
      });
      detectedTypes.add(pattern.type);
    }
  });
  
  replacements.sort((a, b) => a.start - b.start);
  
  let offset = 0;
  replacements.forEach(({ start, end, pattern, match }) => {
    const adjustedStart = start + offset;
    const adjustedEnd = end + offset;
    
    segments.push({
      start: adjustedStart,
      end: adjustedStart + pattern.replacement.length,
      type: pattern.type,
      original: match,
      redacted: pattern.replacement
    });
    
    workingText = 
      workingText.slice(0, adjustedStart) + 
      pattern.replacement + 
      workingText.slice(adjustedEnd);
    
    offset += pattern.replacement.length - (end - start);
  });
  
  const confidenceScore = Math.min(100, segments.length * 10);
  
  return {
    original: text,
    redacted: workingText,
    segments,
    detectedSensitiveTypes: Array.from(detectedTypes),
    confidenceScore
  };
}

interface SensitiveDataDetectorProps {
  text: string;
  onRedactionToggle?: (segment: RedactedSegment) => void;
  customPatterns?: SensitiveDataPattern[];
  showOriginal?: boolean;
}

export const SensitiveDataDetector: React.FC<SensitiveDataDetectorProps> = ({
  text,
  onRedactionToggle,
  customPatterns = [],
  showOriginal = false
}) => {
  const result = useMemo(() => 
    detectSensitiveData(text, DEFAULT_PATTERNS, customPatterns),
    [text, customPatterns]
  );

  const renderHighlightedText = () => {
    if (result.segments.length === 0) {
      return <span>{text}</span>;
    }

    const elements: React.ReactNode[] = [];
    let lastIndex = 0;

    result.segments.forEach((segment, index) => {
      if (segment.start > lastIndex) {
        elements.push(
          <span key={`text-${index}`}>
            {(showOriginal ? result.original : result.redacted).slice(lastIndex, segment.start)}
          </span>
        );
      }

      const severity = DEFAULT_PATTERNS.find(p => p.type === segment.type)?.severity || 'medium';
      const severityColors = {
        low: 'bg-yellow-100 text-yellow-800 border-yellow-300',
        medium: 'bg-orange-100 text-orange-800 border-orange-300',
        high: 'bg-red-100 text-red-800 border-red-300',
        critical: 'bg-red-200 text-red-900 border-red-400'
      };

      elements.push(
        <span
          key={`segment-${index}`}
          className={`inline-flex items-center px-1 py-0.5 mx-0.5 rounded border cursor-pointer transition-all ${
            severityColors[severity]
          } hover:opacity-80`}
          onClick={() => onRedactionToggle?.(segment)}
          title={`Click to toggle: ${segment.original}`}
        >
          {showOriginal ? segment.original : segment.redacted}
          {segment.isManuallyToggled && (
            showOriginal ? <EyeOff className="w-3 h-3 ml-1" /> : <Eye className="w-3 h-3 ml-1" />
          )}
        </span>
      );

      lastIndex = segment.start + (showOriginal ? segment.original.length : segment.redacted.length);
    });

    if (lastIndex < (showOriginal ? result.original : result.redacted).length) {
      elements.push(
        <span key="text-end">
          {(showOriginal ? result.original : result.redacted).slice(lastIndex)}
        </span>
      );
    }

    return <>{elements}</>;
  };

  return (
    <div className="space-y-2">
      {result.segments.length > 0 && (
        <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-md">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          <span className="text-sm text-amber-800">
            {result.segments.length} sensitive data element{result.segments.length > 1 ? 's' : ''} detected
          </span>
        </div>
      )}
      <div className="p-3 bg-gray-50 border border-gray-200 rounded-md font-mono text-sm">
        {renderHighlightedText()}
      </div>
    </div>
  );
};