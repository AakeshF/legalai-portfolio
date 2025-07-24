import React, { useMemo, CSSProperties } from 'react';
import { FixedSizeList as List } from 'react-window';
import { FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react';

interface Document {
  id: string | number;
  filename: string;
  file_size?: number;
  processing_status: string;
  created_at?: string;
  summary?: string;
}

interface VirtualDocumentListProps {
  documents: Document[];
  onDocumentClick: (doc: Document) => void;
  height: number;
  itemHeight?: number;
}

interface RowProps {
  index: number;
  style: CSSProperties;
  data: {
    documents: Document[];
    onDocumentClick: (doc: Document) => void;
  };
}

const Row: React.FC<RowProps> = ({ index, style, data }) => {
  const document = data.documents[index];
  
  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
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

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown date';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div 
      style={style} 
      className="px-4 py-2 border-b border-gray-200 hover:bg-gray-50 cursor-pointer"
      onClick={() => data.onDocumentClick(document)}
    >
      <div className="flex items-start space-x-3">
        <FileText className="w-5 h-5 text-gray-400 mt-1 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900 truncate">
              {document.filename}
            </h3>
            <div className="flex items-center space-x-1">
              {getStatusIcon(document.processing_status)}
              <span className="text-xs text-gray-500">
                {document.processing_status}
              </span>
            </div>
          </div>
          <div className="mt-1 flex items-center space-x-4 text-xs text-gray-500">
            <span>{formatFileSize(document.file_size)}</span>
            <span>{formatDate(document.created_at)}</span>
          </div>
          {document.summary && (
            <p className="mt-1 text-xs text-gray-600 line-clamp-2">
              {document.summary}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export const VirtualDocumentList: React.FC<VirtualDocumentListProps> = ({
  documents,
  onDocumentClick,
  height,
  itemHeight = 80,
}) => {
  const itemData = useMemo(
    () => ({ documents, onDocumentClick }),
    [documents, onDocumentClick]
  );

  return (
    <List
      height={height}
      itemCount={documents.length}
      itemSize={itemHeight}
      width="100%"
      itemData={itemData}
      overscanCount={5}
    >
      {Row}
    </List>
  );
};