import React, { useState, useEffect, useMemo } from 'react';
import { FileText, Download, Trash2, RefreshCw, Clock, CheckCircle, AlertCircle, Search, Filter, Calendar, X, ChevronDown, AlertTriangle } from 'lucide-react';
import { useToast } from '../components/Toast';
import { ApiError, NetworkError } from '../utils/api';
import { documentService } from '../services/document.service';
import { PollingIndicator } from './PollingIndicator';

interface Document {
  id: string | number;
  filename: string;
  file_size?: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  upload_timestamp?: string;
  created_at?: string;
  summary?: string;
  legal_metadata?: {
    document_type?: string;
    risk_score?: number;
    parties?: Array<{ name: string; role: string }>;
    jurisdiction?: string;
    key_terms?: string[];
  } | string;
  extracted_entities?: any;
  ai_analysis?: any;
}

interface DocumentListProps {
  documents: Document[];
  onRefresh: () => void;
  onDocumentSelect: (document: Document) => void;
  onDocumentDelete?: (documentId: string) => void;
  isPolling?: boolean;
  hasProcessingDocuments?: boolean;
}

const DocumentList: React.FC<DocumentListProps> = ({ 
  documents, 
  onRefresh, 
  onDocumentSelect, 
  onDocumentDelete,
  isPolling = false,
  hasProcessingDocuments = false
}) => {
  // Get initial state from URL params
  const getInitialStateFromURL = () => {
    const params = new URLSearchParams(window.location.search);
    return {
      search: params.get('search') || '',
      status: params.get('status') || 'all',
      docType: params.get('type') || 'all',
      dateFrom: params.get('from') || '',
      dateTo: params.get('to') || '',
      sortBy: (params.get('sort') as 'name' | 'date' | 'size' | 'risk') || 'date'
    };
  };

  const initialState = getInitialStateFromURL();
  
  const [searchTerm, setSearchTerm] = useState(initialState.search);
  const [statusFilter, setStatusFilter] = useState<string>(initialState.status);
  const [documentTypeFilter, setDocumentTypeFilter] = useState<string>(initialState.docType);
  const [dateFrom, setDateFrom] = useState(initialState.dateFrom);
  const [dateTo, setDateTo] = useState(initialState.dateTo);
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'size' | 'risk'>(initialState.sortBy);
  const [showFilters, setShowFilters] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{show: boolean; document: Document | null}>({
    show: false,
    document: null
  });
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const { showSuccess, showError } = useToast();

  // Note: Polling is now handled by the parent component using useDocumentPolling hook

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (searchTerm) params.set('search', searchTerm);
    if (statusFilter !== 'all') params.set('status', statusFilter);
    if (documentTypeFilter !== 'all') params.set('type', documentTypeFilter);
    if (dateFrom) params.set('from', dateFrom);
    if (dateTo) params.set('to', dateTo);
    if (sortBy !== 'date') params.set('sort', sortBy);
    
    const newURL = params.toString() ? `?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, '', newURL);
  }, [searchTerm, statusFilter, documentTypeFilter, dateFrom, dateTo, sortBy]);

  const handleDeleteClick = (e: React.MouseEvent, document: Document) => {
    e.stopPropagation();
    setDeleteConfirm({ show: true, document });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm.document) return;

    const documentName = deleteConfirm.document.filename;
    const documentId = deleteConfirm.document.id;

    setIsDeleting(true);
    try {
      await documentService.deleteDocument(Number(documentId));

      // Optimistically update UI by removing from local state
      setDeleteConfirm({ show: false, document: null });
      
      // Call parent callback if provided to update parent state
      if (onDocumentDelete) {
        onDocumentDelete(String(documentId));
      } else {
        // If no callback, refresh to get updated list
        onRefresh();
      }

      showSuccess('Document deleted', `"${documentName}" has been deleted successfully`);
    } catch (error) {
      console.error('Error deleting document:', error);
      
      if (error instanceof NetworkError) {
        showError('Network error', 'Please check your internet connection and try again');
      } else if (error instanceof ApiError) {
        if (error.status === 404) {
          showError('Document not found', 'This document may have already been deleted');
          // Remove from UI since it doesn't exist on server
          if (onDocumentDelete) {
            onDocumentDelete(String(documentId));
          } else {
            onRefresh();
          }
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
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirm({ show: false, document: null });
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  };

  // Parse legal_metadata if it's a string
  const parseMetadata = (doc: Document) => {
    if (!doc.legal_metadata) return null;
    if (typeof doc.legal_metadata === 'string') {
      try {
        return JSON.parse(doc.legal_metadata);
      } catch {
        return null;
      }
    }
    return doc.legal_metadata;
  };

  // Extract unique document types from all documents
  const documentTypes = useMemo(() => {
    const types = new Set<string>();
    documents.forEach(doc => {
      const metadata = parseMetadata(doc);
      if (metadata?.document_type) {
        types.add(metadata.document_type);
      }
    });
    return Array.from(types).sort();
  }, [documents]);

  // Clear all filters
  const clearAllFilters = () => {
    setSearchTerm('');
    setStatusFilter('all');
    setDocumentTypeFilter('all');
    setDateFrom('');
    setDateTo('');
    setSortBy('date');
  };

  // Check if any filters are active
  const hasActiveFilters = searchTerm || statusFilter !== 'all' || 
    documentTypeFilter !== 'all' || dateFrom || dateTo || sortBy !== 'date';

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusIcon = (status: string) => {
    const normalizedStatus = status?.toLowerCase() || '';
    switch (normalizedStatus) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-600 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Clock className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusText = (status: string) => {
    const normalizedStatus = status?.toLowerCase() || '';
    switch (normalizedStatus) {
      case 'completed':
        return 'Ready';
      case 'processing':
        return 'Processing';
      case 'failed':
        return 'Failed';
      default:
        return 'Pending';
    }
  };

  const getStatusColor = (status: string) => {
    const normalizedStatus = status?.toLowerCase() || '';
    switch (normalizedStatus) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Filter and sort documents
  const filteredDocuments = documents
    .filter(doc => {
      // Comprehensive search across filename, summary, and metadata
      const metadata = parseMetadata(doc);
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = !searchTerm || 
        doc.filename.toLowerCase().includes(searchLower) ||
        doc.summary?.toLowerCase().includes(searchLower) ||
        metadata?.parties?.some((p: { name: string; role: string }) => p.name.toLowerCase().includes(searchLower)) ||
        metadata?.jurisdiction?.toLowerCase().includes(searchLower) ||
        metadata?.key_terms?.some((term: string) => term.toLowerCase().includes(searchLower));

      // Status filter
      const docStatus = doc.processing_status?.toLowerCase() || '';
      const filterStatus = statusFilter.toLowerCase();
      const matchesStatus = statusFilter === 'all' || docStatus === filterStatus;
      
      // Document type filter
      const matchesType = documentTypeFilter === 'all' || 
        metadata?.document_type === documentTypeFilter;
      
      // Date range filter
      let matchesDate = true;
      if ((dateFrom || dateTo) && doc.upload_timestamp) {
        const uploadDate = new Date(doc.upload_timestamp);
        if (dateFrom && uploadDate < new Date(dateFrom)) matchesDate = false;
        if (dateTo && uploadDate > new Date(dateTo + 'T23:59:59')) matchesDate = false;
      }
      
      return matchesSearch && matchesStatus && matchesType && matchesDate;
    })
    .sort((a, b) => {
      const metadataA = parseMetadata(a);
      const metadataB = parseMetadata(b);
      
      switch (sortBy) {
        case 'name':
          return a.filename.localeCompare(b.filename);
        case 'size':
          return (b.file_size ?? 0) - (a.file_size ?? 0);
        case 'risk':
          // Sort by risk score (higher first), fallback to date if no risk score
          const riskA = metadataA?.risk_score ?? -1;
          const riskB = metadataB?.risk_score ?? -1;
          if (riskA !== riskB) return riskB - riskA;
          return new Date(b.upload_timestamp ?? 0).getTime() - new Date(a.upload_timestamp ?? 0).getTime();
        case 'date':
        default:
          return new Date(b.upload_timestamp ?? 0).getTime() - new Date(a.upload_timestamp ?? 0).getTime();
      }
    });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-serif font-bold text-brand-gray-900 mb-2">Document Vault</h1>
          <p className="text-brand-gray-600 font-medium">
            Your fortress of legal intelligence. Every byte stays on your machine.
          </p>
          {/* Polling indicator */}
          <PollingIndicator 
            isPolling={isPolling} 
            hasProcessingDocuments={hasProcessingDocuments}
            className="mt-2"
          />
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-brand-blue-600 to-brand-blue-700 text-white rounded-lg hover:from-brand-blue-700 hover:to-brand-blue-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md btn-press"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {/* Filters and Search */}
      <div className="mb-6 space-y-4">
        {/* Primary Search and Filters Row */}
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-4 h-4 text-brand-gray-400" />
            <input
              type="text"
              placeholder="Hunt down your legal intel..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-brand-gray-300 rounded-lg focus:ring-2 focus:ring-brand-blue-500 focus:border-brand-blue-500 bg-white placeholder-brand-gray-500"
            />
          </div>

          {/* Advanced Filters Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center space-x-2 px-4 py-2 border rounded-lg transition-all duration-200 ${
              showFilters || hasActiveFilters
                ? 'bg-brand-blue-50 border-brand-blue-300 text-brand-blue-700 shadow-sm'
                : 'border-brand-gray-300 text-brand-gray-700 hover:bg-brand-gray-50 hover:border-brand-gray-400'
            }`}
          >
            <Filter className="w-4 h-4" />
            <span className="font-medium">Filters</span>
            {hasActiveFilters && (
              <span className="bg-gradient-to-r from-brand-blue-600 to-brand-blue-700 text-white text-xs px-2 py-0.5 rounded-full">
                Active
              </span>
            )}
          </button>
        </div>

        {/* Advanced Filters Panel */}
        {showFilters && (
          <div className="bg-brand-gray-50 rounded-lg border border-brand-gray-200 p-4 space-y-4 animate-slide-up">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Status Filter */}
              <div>
                <label className="block text-sm font-medium text-brand-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-brand-gray-300 rounded-lg focus:ring-2 focus:ring-brand-blue-500 focus:border-brand-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="completed">Completed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                  <option value="pending">Pending</option>
                </select>
              </div>

              {/* Document Type Filter */}
              <div>
                <label className="block text-sm font-medium text-brand-gray-700 mb-1">
                  Document Type
                </label>
                <select
                  value={documentTypeFilter}
                  onChange={(e) => setDocumentTypeFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-brand-gray-300 rounded-lg focus:ring-2 focus:ring-brand-blue-500 focus:border-brand-blue-500"
                >
                  <option value="all">All Types</option>
                  {documentTypes.map(type => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date From */}
              <div>
                <label className="block text-sm font-medium text-brand-gray-700 mb-1">
                  From Date
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-2.5 w-4 h-4 text-brand-gray-400" />
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="w-full pl-10 pr-3 py-2 border border-brand-gray-300 rounded-lg focus:ring-2 focus:ring-brand-blue-500 focus:border-brand-blue-500"
                  />
                </div>
              </div>

              {/* Date To */}
              <div>
                <label className="block text-sm font-medium text-brand-gray-700 mb-1">
                  To Date
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-2.5 w-4 h-4 text-brand-gray-400" />
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="w-full pl-10 pr-3 py-2 border border-brand-gray-300 rounded-lg focus:ring-2 focus:ring-brand-blue-500 focus:border-brand-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Sort and Clear Filters Row */}
            <div className="flex items-center justify-between pt-2 border-t border-brand-gray-200">
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-brand-gray-700">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'name' | 'date' | 'size' | 'risk')}
            className="px-3 py-2 border border-brand-gray-300 rounded-lg focus:ring-2 focus:ring-brand-blue-500 focus:border-brand-blue-500"
          >
            <option value="date">Upload Date</option>
            <option value="name">Name</option>
            <option value="size">File Size</option>
            <option value="risk">Risk Score</option>
          </select>
        </div>

              {/* Clear Filters Button */}
              {hasActiveFilters && (
                <button
                  onClick={clearAllFilters}
                  className="flex items-center space-x-2 px-4 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                  <span>Clear All Filters</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-sm text-brand-gray-600">Active filters:</span>
          {searchTerm && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-brand-blue-100 text-brand-blue-700">
              Search: "{searchTerm}"
              <button onClick={() => setSearchTerm('')} className="ml-2 hover:text-brand-blue-900">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {statusFilter !== 'all' && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-green-100 text-green-700">
              Status: {statusFilter}
              <button onClick={() => setStatusFilter('all')} className="ml-2 hover:text-green-900">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {documentTypeFilter !== 'all' && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-purple-100 text-purple-700">
              Type: {documentTypeFilter}
              <button onClick={() => setDocumentTypeFilter('all')} className="ml-2 hover:text-purple-900">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {(dateFrom || dateTo) && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-orange-100 text-orange-700">
              Date: {dateFrom || 'Any'} - {dateTo || 'Any'}
              <button onClick={() => { setDateFrom(''); setDateTo(''); }} className="ml-2 hover:text-orange-900">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          <span className="text-sm text-brand-gray-600 ml-2">
            ({filteredDocuments.length} of {documents.length} documents)
          </span>
        </div>
      )}

      {/* Documents Grid */}
      {filteredDocuments.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-brand-gray-300 mx-auto mb-4" />
          <h3 className="font-serif text-xl font-bold text-brand-gray-900 mb-2">
            {documents.length === 0 ? 'The Vault Awaits' : 'Nothing Matches Your Hunt'}
          </h3>
          <p className="text-brand-gray-600 max-w-md mx-auto font-medium">
            {documents.length === 0 
              ? 'Feed the beast your first legal document and watch the intelligence unfold.'
              : 'Your search came up empty. Time to adjust the filters and try again.'
            }
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDocuments.map((document) => (
            <div
              key={`${document.id}-${document.processing_status}`}
              onClick={() => onDocumentSelect(document)}
              className="bg-white rounded-lg border border-brand-gray-200 p-4 hover:shadow-md transition-all duration-200 cursor-pointer group hover-lift animate-fade-in"
            >
              {/* Document Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start space-x-3 flex-1 min-w-0">
                  <div className={`p-2 rounded-lg flex-shrink-0 ${
                    document.processing_status?.toLowerCase() === 'processing' 
                      ? 'bg-yellow-50 animate-pulse' 
                      : 'bg-brand-blue-50'
                  }`}>
                    <FileText className={`w-5 h-5 ${
                      document.processing_status?.toLowerCase() === 'processing'
                        ? 'text-yellow-600'
                        : 'text-brand-blue-600'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-brand-gray-900 truncate group-hover:text-brand-blue-600 transition-colors">
                      {document.filename}
                    </h3>
                    <p className="text-sm text-brand-gray-500">
                      {formatFileSize(document.file_size ?? 0)}
                    </p>
                  </div>
                </div>
                
                {/* Status Badge */}
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium status-transition ${getStatusColor(document.processing_status)} ${
                  document.processing_status?.toLowerCase() === 'processing' ? 'animate-pulse' : ''
                }`}>
                  {getStatusIcon(document.processing_status)}
                  <span className="ml-1">{getStatusText(document.processing_status)}</span>
                </span>
              </div>

              {/* Document Info */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-brand-gray-600">
                    <span className="font-medium">Uploaded:</span> {document.upload_timestamp ? formatDate(document.upload_timestamp) : 'Unknown'}
                  </div>
                  
                  {/* Risk Score */}
                  {(() => {
                    const metadata = parseMetadata(document);
                    if (metadata?.risk_score !== undefined) {
                      const riskLevel = metadata.risk_score >= 7 ? 'high' : 
                                       metadata.risk_score >= 4 ? 'medium' : 'low';
                      const riskColor = riskLevel === 'high' ? 'text-red-600 bg-red-50' :
                                       riskLevel === 'medium' ? 'text-yellow-600 bg-yellow-50' :
                                       'text-green-600 bg-green-50';
                      return (
                        <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${riskColor}`}>
                          <AlertTriangle className="w-3 h-3" />
                          <span className="text-xs font-medium">Risk: {metadata.risk_score}/10</span>
                        </div>
                      );
                    }
                    return null;
                  })()}
                </div>
                
                {/* Document Type */}
                {(() => {
                  const metadata = parseMetadata(document);
                  if (metadata?.document_type) {
                    return (
                      <div className="text-xs text-brand-gray-500">
                        <span className="font-medium">Type:</span> {metadata.document_type}
                      </div>
                    );
                  }
                  return null;
                })()}
                
                {document.summary && (
                  <div>
                    <p className="text-sm text-brand-gray-600 font-medium mb-1">Intel Summary:</p>
                    <p className="text-sm text-brand-gray-500 line-clamp-2">
                      {document.summary}
                    </p>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="mt-4 pt-3 border-t border-brand-gray-100 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDocumentSelect(document);
                  }}
                  className="text-sm text-brand-blue-600 hover:text-brand-blue-700 font-medium"
                >
                  Dive Deeper
                </button>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // TODO: Implement download
                      console.log('Download:', document.filename);
                    }}
                    className="p-1 text-brand-gray-400 hover:text-brand-gray-600 rounded"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => handleDeleteClick(e, document)}
                    className="p-1 text-brand-gray-400 hover:text-red-600 rounded"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {documents.length > 0 && (
        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-brand-gray-200">
            <div className="text-2xl font-bold text-brand-gray-900">{documents.length}</div>
            <div className="text-sm text-brand-gray-600">Documents Secured</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-brand-gray-200">
            <div className="text-2xl font-bold text-green-600">
              {documents.filter(d => d.processing_status?.toLowerCase() === 'completed').length}
            </div>
            <div className="text-sm text-brand-gray-600">Intelligence Ready</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-brand-gray-200">
            <div className="text-2xl font-bold text-yellow-600">
              {documents.filter(d => d.processing_status?.toLowerCase() === 'processing').length}
            </div>
            <div className="text-sm text-brand-gray-600">Being Analyzed</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-brand-gray-200">
            <div className="text-2xl font-bold text-brand-gray-900">
              {(documents.reduce((acc, doc) => acc + (doc.file_size ?? 0), 0) / (1024 * 1024)).toFixed(1)} MB
            </div>
            <div className="text-sm text-brand-gray-600">Data Under Lock</div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm.show && deleteConfirm.document && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="font-serif text-xl font-bold text-brand-gray-900 mb-2">
              Confirm Destruction
            </h3>
            <p className="text-brand-gray-600 mb-6">
              You're about to permanently destroy "{deleteConfirm.document.filename}". This action cannot be undone. Are you absolutely certain?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleDeleteCancel}
                disabled={isDeleting}
                className="px-4 py-2 text-brand-gray-700 bg-brand-gray-100 rounded-lg hover:bg-brand-gray-200 transition-colors disabled:opacity-50"
              >
                Keep It
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Destroying...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Destroy
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

export default DocumentList;
