import React, { useState } from 'react';
import { 
  FileText, 
  Calendar, 
  Users, 
  DollarSign, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  ChevronLeft,
  Scale,
  Building,
  User,
  CalendarDays,
  FileSignature,
  Hash,
  Briefcase,
  Shield,
  AlertTriangle,
  MapPin,
  Trash2,
  Download,
  Code,
  Gavel,
  BookOpen,
  FileCheck,
  AlertOctagon
} from 'lucide-react';
import { useToast } from '../components/Toast';
import { ApiError, NetworkError } from '../utils/api';
import { documentService } from '../services/document.service';
import {
  MetadataSection,
  MetadataField,
  RiskBadge,
  PartyCard,
  DateTimeline,
  FinancialAmount
} from './MetadataComponents';

interface Party {
  name: string;
  role: string;
  type?: 'individual' | 'organization';
  contact?: {
    email?: string;
    phone?: string;
    address?: string;
  };
}

interface DateEvent {
  date: string;
  type: string;
  description?: string;
}

interface MoneyAmount {
  amount: number;
  currency: string;
  context: string;
  payment_schedule?: string;
}

interface RiskIndicator {
  category: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
}

interface ExtractedMetadata {
  document_type?: string;
  case_number?: string;
  jurisdiction?: string;
  jurisdictions?: string[];
  parties?: Party[];
  dates?: DateEvent[];
  money_amounts?: MoneyAmount[];
  key_terms?: string[];
  obligations?: string[];
  risk_indicators?: RiskIndicator[];
  // Additional metadata fields
  court?: string;
  judge?: string;
  status?: string;
  filing_number?: string;
  clauses?: Array<{
    type: string;
    text: string;
    risk_level?: 'low' | 'medium' | 'high';
  }>;
  deadlines?: Array<{
    date: string;
    description: string;
    priority?: 'low' | 'medium' | 'high';
  }>;
  risk_score?: number;
}

interface Document {
  id: string | number;
  filename: string;
  file_size?: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  upload_timestamp?: string;
  created_at?: string;
  summary?: string;
  metadata?: ExtractedMetadata;
  legal_metadata?: ExtractedMetadata | string;
  extracted_entities?: any;
  ai_analysis?: any;
}

interface DocumentViewProps {
  document: Document;
  onBack: () => void;
  onDelete?: (documentId: string) => void;
}

const DocumentView: React.FC<DocumentViewProps> = ({ document, onBack, onDelete }) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const { showSuccess, showError, showInfo } = useToast();
  
  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Delete key to show confirmation dialog
      if (e.key === 'Delete' && onDelete && !showDeleteConfirm && !isDeleting) {
        e.preventDefault();
        setShowDeleteConfirm(true);
      }
      
      // Escape key to close confirmation dialog
      if (e.key === 'Escape' && showDeleteConfirm) {
        e.preventDefault();
        setShowDeleteConfirm(false);
      }
      
      // Enter key to confirm deletion when dialog is open
      if (e.key === 'Enter' && showDeleteConfirm && !isDeleting) {
        e.preventDefault();
        handleDelete();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showDeleteConfirm, isDeleting, onDelete, document.id]);

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getStatusIcon = (status: string) => {
    const normalizedStatus = status?.toLowerCase() || '';
    switch (normalizedStatus) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'processing':
        return <Clock className="w-5 h-5 text-yellow-600 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Clock className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    const normalizedStatus = status?.toLowerCase() || '';
    switch (normalizedStatus) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getDocumentTypeIcon = (type?: string) => {
    switch (type?.toLowerCase()) {
      case 'contract':
        return <FileSignature className="w-5 h-5" />;
      case 'lawsuit':
      case 'complaint':
        return <Scale className="w-5 h-5" />;
      case 'brief':
      case 'motion':
        return <Briefcase className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  };

  // Parse legal_metadata if it's a string
  const parseLegalMetadata = (): ExtractedMetadata => {
    if (document.legal_metadata) {
      if (typeof document.legal_metadata === 'string') {
        try {
          return JSON.parse(document.legal_metadata);
        } catch (e) {
          console.error('Failed to parse legal_metadata:', e);
          return {};
        }
      }
      return document.legal_metadata;
    }
    return document.metadata || {};
  };

  const metadata = parseLegalMetadata();

  const handleExportMetadata = () => {
    const exportData = {
      document_info: {
        id: document.id,
        filename: document.filename,
        file_size: document.file_size,
        upload_timestamp: document.upload_timestamp,
        processing_status: document.processing_status
      },
      summary: document.summary || null,
      legal_metadata: metadata,
      exported_at: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement('a');
    a.href = url;
    a.download = `${document.filename.replace(/\.[^/.]+$/, '')}_metadata.json`;
    window.document.body.appendChild(a);
    a.click();
    window.document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showSuccess('Metadata exported', 'Document metadata has been downloaded as JSON');
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await documentService.deleteDocument(Number(document.id));

      showSuccess('Document deleted', `"${document.filename}" has been deleted successfully`);
      
      // Call the parent callback to handle the deletion
      if (onDelete) {
        onDelete(document.id);
      }
      
      // Go back to the document list
      onBack();
    } catch (error) {
      console.error('Error deleting document:', error);
      
      if (error instanceof NetworkError) {
        showError('Network error', 'Please check your internet connection and try again');
      } else if (error instanceof ApiError) {
        if (error.status === 404) {
          showError('Document not found', 'This document may have already been deleted');
          if (onDelete) {
            onDelete(document.id);
          }
          onBack();
        } else if (error.status === 403) {
          showError('Permission denied', 'You do not have permission to delete this document');
        } else {
          showError('Failed to delete document', error.message);
        }
      } else {
        showError('Failed to delete document', 'An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-slate-50">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center text-slate-600 hover:text-slate-900 transition-colors mb-4"
          >
            <ChevronLeft className="w-5 h-5 mr-1" />
            Back to Documents
          </button>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <FileText className="w-8 h-8 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-900 mb-1">
                    {document.filename}
                  </h1>
                  <div className="flex items-center space-x-4 text-sm text-slate-600">
                    <span>Uploaded {formatDate(document.upload_timestamp)}</span>
                    <span>•</span>
                    <span>{(document.file_size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                {/* Action Buttons */}
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => {
                      // TODO: Implement download
                      console.log('Download:', document.filename);
                    }}
                    className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    title="Download Document"
                  >
                    <Download className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => handleExportMetadata()}
                    className="p-2 text-slate-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                    title="Export Metadata as JSON"
                  >
                    <Code className="w-5 h-5" />
                  </button>
                  {onDelete && (
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors group relative"
                      title="Delete Document (Del key)"
                    >
                      <Trash2 className="w-5 h-5" />
                      <span className="absolute -bottom-8 right-0 text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                        Press Del key
                      </span>
                    </button>
                  )}
                </div>
                
                {/* Processing Status */}
                <div className={`inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium border ${getStatusColor(document.processing_status)}`}>
                  {getStatusIcon(document.processing_status)}
                  <span className="ml-1.5">
                    {document.processing_status === 'completed' ? 'Analysis Complete' :
                     document.processing_status === 'processing' ? 'Processing...' :
                   document.processing_status === 'failed' ? 'Analysis Failed' : 'Pending'}
                  </span>
                </div>
              </div>
            </div>

            {/* Document Type Badge */}
            {metadata.document_type && (
              <div className="mt-4 flex items-center space-x-3">
                <div className="inline-flex items-center px-4 py-2 bg-slate-900 text-white rounded-lg">
                  {getDocumentTypeIcon(metadata.document_type)}
                  <span className="ml-2 font-medium">{metadata.document_type}</span>
                </div>
                {metadata.risk_score !== undefined && (
                  <RiskBadge 
                    severity={metadata.risk_score >= 7 ? 'high' : metadata.risk_score >= 4 ? 'medium' : 'low'} 
                  />
                )}
              </div>
            )}
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Key Information */}
          <div className="lg:col-span-2 space-y-6">
            {/* Summary */}
            {document.summary && (
              <MetadataSection
                title="Document Summary"
                icon={<FileText className="w-5 h-5" />}
                defaultExpanded={true}
              >
                <p className="text-slate-700 leading-relaxed pt-4">{document.summary}</p>
              </MetadataSection>
            )}

            {/* Parties */}
            {metadata.parties && metadata.parties.length > 0 && (
              <MetadataSection
                title="Parties Involved"
                icon={<Users className="w-5 h-5" />}
                defaultExpanded={true}
                badge={<span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">{metadata.parties.length}</span>}
              >
                <div className="grid md:grid-cols-2 gap-4 pt-4">
                  {metadata.parties.map((party, index) => (
                    <PartyCard key={index} party={party} />
                  ))}
                </div>
              </MetadataSection>
            )}

            {/* Timeline */}
            {metadata.dates && metadata.dates.length > 0 && (
              <MetadataSection
                title="Important Dates"
                icon={<CalendarDays className="w-5 h-5" />}
                defaultExpanded={true}
              >
                <div className="pt-4">
                  <DateTimeline dates={metadata.dates} />
                </div>
              </MetadataSection>
            )}

            {/* Obligations */}
            {metadata.obligations && metadata.obligations.length > 0 && (
              <MetadataSection
                title="Key Obligations"
                icon={<FileCheck className="w-5 h-5" />}
                defaultExpanded={true}
              >
                <ul className="space-y-3 pt-4">
                  {metadata.obligations.map((obligation, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-blue-600 mr-3 mt-0.5">•</span>
                      <span className="text-slate-700">{obligation}</span>
                    </li>
                  ))}
                </ul>
              </MetadataSection>
            )}

            {/* Clauses */}
            {metadata.clauses && metadata.clauses.length > 0 && (
              <MetadataSection
                title="Important Clauses"
                icon={<BookOpen className="w-5 h-5" />}
                defaultExpanded={false}
              >
                <div className="space-y-4 pt-4">
                  {metadata.clauses.map((clause, index) => (
                    <div key={index} className="border-l-4 border-slate-300 pl-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-slate-900">{clause.type}</h4>
                        {clause.risk_level && (
                          <RiskBadge severity={clause.risk_level} className="scale-90" />
                        )}
                      </div>
                      <p className="text-sm text-slate-700">{clause.text}</p>
                    </div>
                  ))}
                </div>
              </MetadataSection>
            )}
          </div>

          {/* Right Column - Financial & Additional Info */}
          <div className="space-y-6">
            {/* Case Information */}
            {(metadata.case_number || metadata.jurisdiction || metadata.jurisdictions || metadata.court || metadata.judge) && (
              <MetadataSection
                title="Case Information"
                icon={<Gavel className="w-5 h-5" />}
                defaultExpanded={true}
              >
                <div className="space-y-3 pt-4">
                  <MetadataField
                    label="Case Number"
                    value={metadata.case_number}
                    icon={<Hash className="w-4 h-4" />}
                    copyable
                  />
                  <MetadataField
                    label="Filing Number"
                    value={metadata.filing_number}
                    icon={<Hash className="w-4 h-4" />}
                    copyable
                  />
                  <MetadataField
                    label="Court"
                    value={metadata.court}
                    icon={<Building className="w-4 h-4" />}
                  />
                  <MetadataField
                    label="Judge"
                    value={metadata.judge}
                    icon={<User className="w-4 h-4" />}
                  />
                  {metadata.jurisdictions && metadata.jurisdictions.length > 0 ? (
                    <div className="flex items-start space-x-3 py-2">
                      <MapPin className="w-4 h-4 text-slate-500 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm text-slate-600">Jurisdictions</p>
                        <div className="space-y-1">
                          {metadata.jurisdictions.map((j, idx) => (
                            <p key={idx} className="font-medium text-slate-900">{j}</p>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <MetadataField
                      label="Jurisdiction"
                      value={metadata.jurisdiction}
                      icon={<MapPin className="w-4 h-4" />}
                    />
                  )}
                  <MetadataField
                    label="Status"
                    value={metadata.status}
                    icon={<AlertCircle className="w-4 h-4" />}
                  />
                </div>
              </MetadataSection>
            )}

            {/* Financial Information */}
            {metadata.money_amounts && metadata.money_amounts.length > 0 && (
              <MetadataSection
                title="Financial Details"
                icon={<DollarSign className="w-5 h-5" />}
                defaultExpanded={true}
                badge={
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                    {metadata.money_amounts.length}
                  </span>
                }
              >
                <div className="space-y-3 pt-4">
                  {metadata.money_amounts.map((amount, index) => (
                    <FinancialAmount key={index} amount={amount} />
                  ))}
                </div>
              </MetadataSection>
            )}

            {/* Risk Indicators */}
            {metadata.risk_indicators && metadata.risk_indicators.length > 0 && (
              <MetadataSection
                title="Risk Analysis"
                icon={<Shield className="w-5 h-5" />}
                defaultExpanded={true}
                badge={
                  <RiskBadge 
                    severity={
                      metadata.risk_indicators.some(r => r.severity === 'high') ? 'high' :
                      metadata.risk_indicators.some(r => r.severity === 'medium') ? 'medium' : 'low'
                    } 
                    className="scale-90"
                  />
                }
              >
                <div className="space-y-3 pt-4">
                  {metadata.risk_indicators.map((risk, index) => (
                    <div key={index} className={`p-4 rounded-lg border ${
                      risk.severity === 'high' ? 'bg-red-50 border-red-200' :
                      risk.severity === 'medium' ? 'bg-yellow-50 border-yellow-200' :
                      'bg-green-50 border-green-200'
                    }`}>
                      <div className="flex items-start space-x-2">
                        {risk.severity === 'high' ? (
                          <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
                        ) : risk.severity === 'medium' ? (
                          <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5" />
                        ) : (
                          <Shield className="w-4 h-4 text-green-600 mt-0.5" />
                        )}
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="font-semibold text-slate-900">{risk.category}</h4>
                            <RiskBadge severity={risk.severity} className="scale-75" />
                          </div>
                          <p className="text-sm text-slate-700">{risk.description}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </MetadataSection>
            )}

            {/* Deadlines */}
            {metadata.deadlines && metadata.deadlines.length > 0 && (
              <MetadataSection
                title="Deadlines"
                icon={<AlertOctagon className="w-5 h-5" />}
                defaultExpanded={true}
                badge={
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full">
                    {metadata.deadlines.length}
                  </span>
                }
              >
                <div className="space-y-3 pt-4">
                  {metadata.deadlines.map((deadline, index) => (
                    <div key={index} className={`p-3 rounded-lg border ${
                      deadline.priority === 'high' ? 'bg-red-50 border-red-200' :
                      deadline.priority === 'medium' ? 'bg-yellow-50 border-yellow-200' :
                      'bg-slate-50 border-slate-200'
                    }`}>
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-slate-900">{deadline.description}</p>
                          <p className="text-sm text-slate-600 mt-1">
                            <Clock className="w-3 h-3 inline mr-1" />
                            {formatDate(deadline.date)}
                          </p>
                        </div>
                        {deadline.priority && (
                          <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                            deadline.priority === 'high' ? 'bg-red-100 text-red-700' :
                            deadline.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {deadline.priority}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </MetadataSection>
            )}

            {/* Key Terms */}
            {metadata.key_terms && metadata.key_terms.length > 0 && (
              <MetadataSection
                title="Key Terms"
                icon={<BookOpen className="w-5 h-5" />}
                defaultExpanded={false}
              >
                <div className="flex flex-wrap gap-2 pt-4">
                  {metadata.key_terms.map((term, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-50 text-blue-700 text-sm font-medium rounded-full border border-blue-200"
                    >
                      {term}
                    </span>
                  ))}
                </div>
              </MetadataSection>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Confirm Deletion
            </h3>
            <p className="text-slate-600 mb-6">
              Are you sure you want to delete "{document.filename}"? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <Clock className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentView;