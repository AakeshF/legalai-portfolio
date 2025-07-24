import React, { useState, useEffect } from 'react';
import { Download, Trash2, AlertTriangle, FileText, Database, Shield, Lock, CheckCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { Toast } from '../SimpleToast';
import { API_ENDPOINTS } from '../../config/api.config';

interface DataExportRequest {
  id: string;
  requestedAt: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  format: 'json' | 'csv' | 'pdf';
  dataTypes: string[];
  downloadUrl?: string;
  expiresAt?: string;
}

export const DataManagement: React.FC = () => {
  const { user, organization } = useAuth();
  const [activeTab, setActiveTab] = useState<'export' | 'deletion'>('export');
  const [exportRequests, setExportRequests] = useState<DataExportRequest[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  useEffect(() => {
    fetchExportHistory();
  }, []);

  const fetchExportHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const response = await api.get(API_ENDPOINTS.privacy.dataExportHistory);
      if (response.data) {
        setExportRequests(response.data.exports || []);
      }
    } catch (error) {
      console.error('Failed to fetch export history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };
  const [selectedDataTypes, setSelectedDataTypes] = useState<string[]>([]);
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'pdf'>('json');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmStep, setDeleteConfirmStep] = useState(1);
  const [confirmationCode, setConfirmationCode] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [password, setPassword] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');

  const dataTypes = [
    { id: 'documents', label: 'Documents', description: 'All uploaded legal documents' },
    { id: 'chat_history', label: 'Chat History', description: 'AI conversation history' },
    { id: 'user_data', label: 'User Profile', description: 'Personal information and settings' },
    { id: 'audit_logs', label: 'Audit Logs', description: 'Security and activity logs' },
    { id: 'organization_data', label: 'Organization Data', description: 'Firm settings and user list' }
  ];

  const requestDataExport = async () => {
    if (selectedDataTypes.length === 0) {
      showNotification('Please select at least one data type to export', 'error');
      return;
    }

    setIsProcessing(true);
    try {
      const response = await api.post(API_ENDPOINTS.privacy.dataExport, {
        dataTypes: selectedDataTypes,
        format: exportFormat
      });

      if (response.data) {
        setExportRequests([response.data, ...exportRequests]);
        showNotification('Data export request submitted successfully', 'success');
        setSelectedDataTypes([]);
      }
    } catch (error) {
      showNotification('Failed to request data export', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const initiateAccountDeletion = async () => {
    setShowDeleteConfirm(true);
    setDeleteConfirmStep(1);
    
    // Generate a random confirmation code
    const code = Math.random().toString(36).substring(2, 8).toUpperCase();
    setGeneratedCode(code);
    
    // Send email with confirmation code
    try {
      await api.post(API_ENDPOINTS.privacy.deletion.initiate, { code });
    } catch (error) {
      console.error('Failed to send confirmation email:', error);
    }
  };

  const confirmAccountDeletion = async () => {
    if (confirmationCode !== generatedCode) {
      showNotification('Invalid confirmation code', 'error');
      return;
    }

    if (!password) {
      showNotification('Please enter your password', 'error');
      return;
    }

    setIsProcessing(true);
    try {
      const response = await api.post(API_ENDPOINTS.privacy.deletion.confirm, {
        confirmationCode,
        password
      });

      if (response.data) {
        showNotification('Account deletion scheduled. You will receive a confirmation email.', 'success');
        setShowDeleteConfirm(false);
        
        // Log out user after 5 seconds
        setTimeout(() => {
          window.location.href = '/logout';
        }, 5000);
      }
    } catch (error) {
      showNotification('Failed to delete account. Please check your password.', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const downloadExport = async (exportRequest: DataExportRequest) => {
    if (!exportRequest.downloadUrl) return;

    try {
      const downloadUrl = `${API_ENDPOINTS.privacy.dataExportDownload}/${exportRequest.id}`;
      const response = await api.get(downloadUrl, {
        responseType: 'blob'
      });
      const blob = response.data;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `data-export-${exportRequest.id}.${exportRequest.format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      showNotification('Failed to download export', 'error');
    }
  };

  const showNotification = (message: string, type: 'success' | 'error') => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
            <Database className="h-6 w-6 mr-2 text-blue-600" />
            Data Management
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Export your data or manage account deletion
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex">
            <button
              onClick={() => setActiveTab('export')}
              className={`py-2 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'export'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Data Export
            </button>
            <button
              onClick={() => setActiveTab('deletion')}
              className={`py-2 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'deletion'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Account Deletion
            </button>
          </nav>
        </div>

        <div className="p-6">
          {/* Data Export Tab */}
          {activeTab === 'export' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Request Data Export</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Select the data you want to export. You'll receive a download link once the export is ready.
                </p>

                <div className="space-y-3 mb-6">
                  <h4 className="text-sm font-medium text-gray-700">Select Data Types</h4>
                  {dataTypes.map((type) => (
                    <label key={type.id} className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                      <input
                        type="checkbox"
                        checked={selectedDataTypes.includes(type.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDataTypes([...selectedDataTypes, type.id]);
                          } else {
                            setSelectedDataTypes(selectedDataTypes.filter(t => t !== type.id));
                          }
                        }}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5"
                      />
                      <div className="ml-3">
                        <p className="font-medium text-gray-900">{type.label}</p>
                        <p className="text-sm text-gray-600">{type.description}</p>
                      </div>
                    </label>
                  ))}
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Export Format
                  </label>
                  <select
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value as any)}
                    className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="json">JSON</option>
                    <option value="csv">CSV</option>
                    <option value="pdf">PDF Report</option>
                  </select>
                </div>

                <button
                  onClick={requestDataExport}
                  disabled={isProcessing || selectedDataTypes.length === 0}
                  className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  <Download className="h-4 w-4 mr-2" />
                  {isProcessing ? 'Processing...' : 'Request Export'}
                </button>
              </div>

              {/* Export History */}
              {exportRequests.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Export History</h3>
                  <div className="space-y-3">
                    {exportRequests.map((request) => (
                      <div key={request.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">
                            {request.dataTypes.join(', ')} ({request.format.toUpperCase()})
                          </p>
                          <p className="text-sm text-gray-600">
                            Requested: {new Date(request.requestedAt).toLocaleString()}
                          </p>
                          {request.expiresAt && (
                            <p className="text-xs text-gray-500">
                              Expires: {new Date(request.expiresAt).toLocaleString()}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center space-x-3">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            request.status === 'completed' ? 'bg-green-100 text-green-800' :
                            request.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                            request.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {request.status}
                          </span>
                          {request.status === 'completed' && request.downloadUrl && (
                            <button
                              onClick={() => downloadExport(request)}
                              className="text-blue-600 hover:text-blue-700"
                            >
                              <Download className="h-5 w-5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <Shield className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div className="ml-3">
                    <h4 className="font-medium text-blue-900">Data Security</h4>
                    <p className="text-sm text-blue-700 mt-1">
                      All exported data is encrypted and available for download for 7 days. 
                      Download links are unique and can only be accessed by your account.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Account Deletion Tab */}
          {activeTab === 'deletion' && (
            <div className="space-y-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <div className="flex items-start">
                  <AlertTriangle className="h-6 w-6 text-red-600 mt-0.5" />
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-red-900">Delete Your Account</h3>
                    <div className="mt-2 text-sm text-red-700 space-y-2">
                      <p>This action is permanent and cannot be undone. Deleting your account will:</p>
                      <ul className="list-disc list-inside ml-4 space-y-1">
                        <li>Remove all your personal data from our systems</li>
                        <li>Delete all documents and chat history</li>
                        <li>Cancel any active subscriptions</li>
                        <li>Remove you from your organization</li>
                        <li>Prevent you from accessing the platform</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">Before you proceed:</h4>
                <div className="space-y-3">
                  <label className="flex items-start">
                    <input type="checkbox" className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5" />
                    <span className="ml-2 text-sm text-gray-700">
                      I have exported all data I wish to keep
                    </span>
                  </label>
                  <label className="flex items-start">
                    <input type="checkbox" className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5" />
                    <span className="ml-2 text-sm text-gray-700">
                      I understand this action is permanent and irreversible
                    </span>
                  </label>
                  <label className="flex items-start">
                    <input type="checkbox" className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5" />
                    <span className="ml-2 text-sm text-gray-700">
                      I have informed my organization administrator (if applicable)
                    </span>
                  </label>
                </div>
              </div>

              <button
                onClick={initiateAccountDeletion}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                <Trash2 className="h-4 w-4 inline mr-2" />
                Delete My Account
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Confirm Account Deletion - Step {deleteConfirmStep} of 2
            </h3>

            {deleteConfirmStep === 1 && (
              <>
                <p className="text-sm text-gray-600 mb-4">
                  We've sent a confirmation code to your email address. Please enter it below:
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Confirmation Code
                  </label>
                  <input
                    type="text"
                    value={confirmationCode}
                    onChange={(e) => setConfirmationCode(e.target.value.toUpperCase())}
                    placeholder="Enter 6-character code"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                    maxLength={6}
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="px-4 py-2 text-gray-700 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (confirmationCode === generatedCode) {
                        setDeleteConfirmStep(2);
                      } else {
                        showNotification('Invalid confirmation code', 'error');
                      }
                    }}
                    disabled={confirmationCode.length !== 6}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Continue
                  </button>
                </div>
              </>
            )}

            {deleteConfirmStep === 2 && (
              <>
                <p className="text-sm text-gray-600 mb-4">
                  Please enter your password to confirm account deletion:
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                  />
                </div>
                <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                  <p className="text-sm text-red-700">
                    <strong>Final Warning:</strong> This will permanently delete your account and all associated data.
                  </p>
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="px-4 py-2 text-gray-700 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmAccountDeletion}
                    disabled={!password || isProcessing}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    {isProcessing ? 'Deleting...' : 'Delete Account'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showToast && (
        <Toast
          message={toastMessage}
          type={toastType}
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
};