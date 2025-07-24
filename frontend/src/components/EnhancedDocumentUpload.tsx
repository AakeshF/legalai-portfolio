import React, { useState, useRef } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle, X, File, Shield, Lock } from 'lucide-react';
import { useToast } from '../components/Toast';
import { api, ApiError, NetworkError } from '../utils/api';
import { ProgressBar } from './LoadingStates';
import { useAuth } from '../contexts/MockAuthContext';
import { API_ENDPOINTS } from '../config/api.config';
import { DocumentConsent, DocumentConsentSettings } from './consent/DocumentConsent';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  processing_status: string;
  upload_timestamp: string;
  summary?: string;
  legal_metadata?: any;
  consent?: DocumentConsentSettings;
}

interface DocumentUploadProps {
  onUploadComplete: (document: Document) => void;
  onViewChange: (view: 'chat' | 'documents' | 'upload') => void;
}

interface UploadFile {
  file: File;
  progress: number;
  status: 'configuring' | 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
  document?: Document;
  tempId: string;
  sensitivityLevel: DocumentConsentSettings['sensitivityLevel'];
  consentSettings?: DocumentConsentSettings;
}

const EnhancedDocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete, onViewChange }) => {
  const [uploads, setUploads] = useState<UploadFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [globalSensitivity, setGlobalSensitivity] = useState<DocumentConsentSettings['sensitivityLevel']>('internal');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showSuccess, showError } = useToast();
  const { organization, user } = useAuth();

  const sensitivityOptions = {
    'public': { label: 'Public', icon: '🌐', color: 'text-green-600' },
    'internal': { label: 'Internal', icon: '🏢', color: 'text-blue-600' },
    'confidential': { label: 'Confidential', icon: '🔒', color: 'text-yellow-600' },
    'highly-sensitive': { label: 'Highly Sensitive', icon: '⚠️', color: 'text-red-600' }
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const newUploads = fileArray.map(file => ({
      file,
      progress: 0,
      status: 'configuring' as const,
      tempId: `${Date.now()}-${Math.random()}`,
      sensitivityLevel: globalSensitivity
    }));

    setUploads(prev => [...prev, ...newUploads]);
  };

  const updateUploadConsent = (tempId: string, settings: Partial<DocumentConsentSettings>) => {
    setUploads(prev => prev.map(upload => 
      upload.tempId === tempId 
        ? { ...upload, consentSettings: { ...upload.consentSettings, ...settings } as DocumentConsentSettings }
        : upload
    ));
  };

  const uploadFile = async (uploadFile: UploadFile, index: number) => {
    try {
      // Update status to uploading
      setUploads(prev => prev.map((u, i) => 
        i === index ? { ...u, status: 'uploading' } : u
      ));

      const formData = new FormData();
      formData.append('file', uploadFile.file);
      formData.append('organizationId', organization?.id || '');
      formData.append('sensitivityLevel', uploadFile.sensitivityLevel);
      
      // Add consent settings
      if (uploadFile.consentSettings) {
        formData.append('consentSettings', JSON.stringify(uploadFile.consentSettings));
      }

      const apiUrl = organization?.usesDemoMode 
        ? API_ENDPOINTS.documents.upload.demo
        : API_ENDPOINTS.documents.upload.prod;
      
      const response = await api.postFormDataWithProgress<Document>(
        apiUrl,
        formData,
        (progress) => {
          setUploads(prev => prev.map((u, i) => 
            i === index ? { ...u, progress } : u
          ));
        }
      );

      // Update to processing
      setUploads(prev => prev.map((u, i) => 
        i === index ? { ...u, status: 'processing', progress: 100 } : u
      ));

      // Poll for processing completion
      const processedDoc = await pollDocumentStatus(response.id);
      
      // Update to completed
      setUploads(prev => prev.map((u, i) => 
        i === index ? { ...u, status: 'completed', document: processedDoc } : u
      ));

      showSuccess({
        title: 'Upload Complete',
        message: `${uploadFile.file.name} has been uploaded and processed successfully.`
      });

      onUploadComplete(processedDoc);
    } catch (error) {
      const errorMessage = error instanceof ApiError 
        ? error.message 
        : error instanceof NetworkError 
        ? 'Network error. Please check your connection.'
        : 'Upload failed. Please try again.';

      setUploads(prev => prev.map((u, i) => 
        i === index ? { ...u, status: 'error', error: errorMessage } : u
      ));

      showError({
        title: 'Upload Failed',
        message: errorMessage
      });
    }
  };

  const pollDocumentStatus = async (documentId: string): Promise<Document> => {
    const maxAttempts = 30;
    const interval = 2000;

    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, interval));
      
      const response = await api.get<Document>(`/api/documents/${documentId}`);
      if (response.processing_status === 'completed') {
        return response;
      } else if (response.processing_status === 'failed') {
        throw new Error('Document processing failed');
      }
    }

    throw new Error('Document processing timeout');
  };

  const startUpload = (index: number) => {
    const upload = uploads[index];
    if (upload.status === 'configuring') {
      uploadFile(upload, index);
    }
  };

  const removeUpload = (index: number) => {
    setUploads(prev => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Upload Documents</h1>
        <p className="text-slate-600">
          Upload your legal documents for AI-powered analysis. Set privacy levels before uploading.
        </p>
      </div>

      {/* Global Sensitivity Selector */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Default Privacy Level for New Uploads
        </label>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(sensitivityOptions).map(([level, config]) => (
            <button
              key={level}
              onClick={() => setGlobalSensitivity(level as DocumentConsentSettings['sensitivityLevel'])}
              className={`px-3 py-2 rounded-md border-2 transition-all text-sm font-medium ${
                globalSensitivity === level
                  ? `border-current ${config.color} bg-white`
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              <span className="mr-1">{config.icon}</span>
              {config.label}
            </button>
          ))}
        </div>
      </div>

      {/* Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-all
          ${isDragOver 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-slate-300 bg-slate-50 hover:border-slate-400'
          }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />
        
        <div className="flex flex-col items-center">
          <Upload className="w-16 h-16 text-slate-400 mb-4" />
          <div className="mb-4">
            <p className="text-slate-600">
              Drag and drop files here, or click to select files
            </p>
            <p className="text-sm text-slate-500 mt-2">
              Supports: PDF, DOCX, TXT (Max: 50MB each)
            </p>
          </div>
          
          <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Choose Files
          </button>
        </div>
      </div>

      {/* Upload Progress */}
      {uploads.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Upload Queue</h2>
          
          <div className="space-y-4">
            {uploads.map((upload, index) => (
              <div key={upload.tempId} className="bg-white rounded-lg border border-slate-200 p-4 animate-slide-up">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-slate-600" />
                    <div>
                      <p className="font-medium text-slate-900">{upload.file.name}</p>
                      <p className="text-sm text-slate-500">{formatFileSize(upload.file.size)}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <div className={`flex items-center space-x-1 px-2 py-1 rounded-md text-xs font-medium ${
                      sensitivityOptions[upload.sensitivityLevel].color
                    } bg-opacity-10`}>
                      <Shield className="h-3 w-3" />
                      <span>{sensitivityOptions[upload.sensitivityLevel].label}</span>
                    </div>
                    
                    {upload.status === 'completed' && (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    )}
                    {upload.status === 'error' && (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    )}
                    {upload.status === 'uploading' && (
                      <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    )}
                    
                    <button
                      onClick={() => removeUpload(index)}
                      className="p-1 hover:bg-slate-100 rounded"
                    >
                      <X className="w-4 h-4 text-slate-500" />
                    </button>
                  </div>
                </div>

                {/* Privacy Configuration for Configuring State */}
                {upload.status === 'configuring' && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-md">
                    <div className="flex items-center justify-between">
                      <div className="text-sm">
                        <p className="font-medium text-gray-700 mb-1">Privacy Settings</p>
                        <div className="flex items-center space-x-4 text-xs text-gray-600">
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              defaultChecked
                              className="mr-1 h-3 w-3"
                            />
                            AI Processing
                          </label>
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              defaultChecked={upload.sensitivityLevel === 'public'}
                              className="mr-1 h-3 w-3"
                            />
                            Analytics
                          </label>
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              defaultChecked={false}
                              className="mr-1 h-3 w-3"
                            />
                            Model Training
                          </label>
                        </div>
                      </div>
                      <button
                        onClick={() => startUpload(index)}
                        className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                      >
                        Upload
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Progress Bar */}
                {(upload.status === 'uploading' || upload.status === 'processing') && (
                  <ProgressBar 
                    progress={upload.progress} 
                    animated={true}
                    showPercentage={true}
                    className="mt-2"
                  />
                )}
                
                {/* Status Messages */}
                <div className="mt-2">
                  {upload.status === 'completed' && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-green-600 font-medium">✓ Upload completed</span>
                      <button
                        onClick={() => onViewChange('documents')}
                        className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                      >
                        View Document →
                      </button>
                    </div>
                  )}
                  {upload.status === 'error' && (
                    <span className="text-sm text-red-600">❌ {upload.error}</span>
                  )}
                  {upload.status === 'uploading' && (
                    <span className="text-sm text-blue-600">📤 Uploading...</span>
                  )}
                  {upload.status === 'processing' && (
                    <span className="text-sm text-yellow-600">⚙️ Processing with AI...</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedDocumentUpload;
