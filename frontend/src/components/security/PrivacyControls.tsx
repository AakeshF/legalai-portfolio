import React, { useState, useEffect } from 'react';
import { Shield, Globe, Database, Clock, FileText, AlertCircle, CheckCircle, Info, Download, Trash2 } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { Toast } from '../SimpleToast';
import { API_ENDPOINTS } from '../../config/api.config';

interface PrivacySettings {
  dataResidency: {
    region: 'us-east' | 'us-west' | 'eu-west' | 'ap-southeast';
    encryptionAtRest: boolean;
    encryptionInTransit: boolean;
  };
  dataProcessing: {
    analyticsEnabled: boolean;
    performanceMonitoring: boolean;
    errorTracking: boolean;
    aiTrainingConsent: boolean;
  };
  dataRetention: {
    documentRetentionDays: number;
    chatHistoryRetentionDays: number;
    auditLogRetentionDays: number;
    autoDeleteEnabled: boolean;
  };
  consent: {
    marketingEmails: boolean;
    productUpdates: boolean;
    securityAlerts: boolean;
    dataProcessingAgreement: boolean;
    lastUpdated: string;
  };
}

interface ComplianceStatus {
  gdprCompliant: boolean;
  ccpaCompliant: boolean;
  hipaaCompliant: boolean;
  socCompliant: boolean;
  lastAudit: string;
  nextAudit: string;
}

export const PrivacyControls: React.FC = () => {
  const { user, organization } = useAuth();
  const [settings, setSettings] = useState<PrivacySettings | null>(null);
  const [compliance, setCompliance] = useState<ComplianceStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');
  const [activeTab, setActiveTab] = useState<'residency' | 'processing' | 'retention' | 'consent'>('residency');

  useEffect(() => {
    fetchPrivacySettings();
  }, []);

  const fetchPrivacySettings = async () => {
    try {
      const [settingsResponse, complianceResponse] = await Promise.all([
        api.get(API_ENDPOINTS.privacy.settings),
        api.get(API_ENDPOINTS.privacy.compliance)
      ]);

      if (settingsResponse.data) {
        setSettings(settingsResponse.data);
      }
      if (complianceResponse.data) {
        setCompliance(complianceResponse.data);
      }
    } catch (error) {
      console.error('Failed to fetch privacy settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateSettings = async (updates: Partial<PrivacySettings>) => {
    if (!settings) return;

    setIsSaving(true);
    try {
      const response = await api.patch(API_ENDPOINTS.privacy.settings, updates);
      if (response.data) {
        setSettings({ ...settings, ...updates });
        showNotification('Privacy settings updated successfully', 'success');
      }
    } catch (error) {
      showNotification('Failed to update privacy settings', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const showNotification = (message: string, type: 'success' | 'error') => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
  };

  const getRegionDisplay = (region: string) => {
    const regions = {
      'us-east': 'US East (Virginia)',
      'us-west': 'US West (Oregon)',
      'eu-west': 'EU West (Ireland)',
      'ap-southeast': 'Asia Pacific (Singapore)'
    };
    return regions[region as keyof typeof regions] || region;
  };

  const getComplianceBadge = (compliant: boolean, label: string) => (
    <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg ${
      compliant ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
    }`}>
      {compliant ? (
        <CheckCircle className="h-4 w-4 text-green-600" />
      ) : (
        <AlertCircle className="h-4 w-4 text-gray-400" />
      )}
      <span className={`text-sm font-medium ${compliant ? 'text-green-700' : 'text-gray-600'}`}>
        {label}
      </span>
    </div>
  );

  if (isLoading || !settings) {
    return <div className="animate-pulse h-96 bg-gray-200 rounded-lg"></div>;
  }

  return (
    <div className="space-y-6">
      {/* Compliance Overview */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold text-gray-900 mb-4 flex items-center">
          <Shield className="h-6 w-6 mr-2 text-blue-600" />
          Privacy & Compliance
        </h2>

        {compliance && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Compliance Status</h3>
            <div className="flex flex-wrap gap-3">
              {getComplianceBadge(compliance.gdprCompliant, 'GDPR')}
              {getComplianceBadge(compliance.ccpaCompliant, 'CCPA')}
              {getComplianceBadge(compliance.hipaaCompliant, 'HIPAA')}
              {getComplianceBadge(compliance.socCompliant, 'SOC 2')}
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Last audit: {new Date(compliance.lastAudit).toLocaleDateString()} • 
              Next audit: {new Date(compliance.nextAudit).toLocaleDateString()}
            </p>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'residency', label: 'Data Residency', icon: Globe },
              { id: 'processing', label: 'Processing', icon: Database },
              { id: 'retention', label: 'Retention', icon: Clock },
              { id: 'consent', label: 'Consent', icon: FileText }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'residency' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Data Residency & Encryption</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Data Storage Region
                  </label>
                  <select
                    value={settings.dataResidency.region}
                    onChange={(e) => updateSettings({
                      dataResidency: { ...settings.dataResidency, region: e.target.value as any }
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="us-east">US East (Virginia)</option>
                    <option value="us-west">US West (Oregon)</option>
                    <option value="eu-west">EU West (Ireland)</option>
                    <option value="ap-southeast">Asia Pacific (Singapore)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    All data will be stored and processed in this region
                  </p>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div className="ml-3">
                      <h4 className="font-medium text-blue-900">Data Sovereignty</h4>
                      <p className="text-sm text-blue-700 mt-1">
                        Your data never leaves the selected region. All processing, backups, and redundancy 
                        occur within the chosen geographic boundary to ensure compliance with local regulations.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.dataResidency.encryptionAtRest}
                      onChange={(e) => updateSettings({
                        dataResidency: { ...settings.dataResidency, encryptionAtRest: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Encryption at rest (AES-256)
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.dataResidency.encryptionInTransit}
                      onChange={(e) => updateSettings({
                        dataResidency: { ...settings.dataResidency, encryptionInTransit: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Encryption in transit (TLS 1.3)
                    </span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'processing' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Data Processing Preferences</h3>
              
              <div className="space-y-4">
                <div className="space-y-3">
                  <label className="flex items-start">
                    <input
                      type="checkbox"
                      checked={settings.dataProcessing.analyticsEnabled}
                      onChange={(e) => updateSettings({
                        dataProcessing: { ...settings.dataProcessing, analyticsEnabled: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5"
                    />
                    <div className="ml-2">
                      <span className="text-sm font-medium text-gray-700">Usage Analytics</span>
                      <p className="text-xs text-gray-500">
                        Help us improve by sharing anonymous usage statistics
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start">
                    <input
                      type="checkbox"
                      checked={settings.dataProcessing.performanceMonitoring}
                      onChange={(e) => updateSettings({
                        dataProcessing: { ...settings.dataProcessing, performanceMonitoring: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5"
                    />
                    <div className="ml-2">
                      <span className="text-sm font-medium text-gray-700">Performance Monitoring</span>
                      <p className="text-xs text-gray-500">
                        Monitor application performance to ensure optimal service
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start">
                    <input
                      type="checkbox"
                      checked={settings.dataProcessing.errorTracking}
                      onChange={(e) => updateSettings({
                        dataProcessing: { ...settings.dataProcessing, errorTracking: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5"
                    />
                    <div className="ml-2">
                      <span className="text-sm font-medium text-gray-700">Error Tracking</span>
                      <p className="text-xs text-gray-500">
                        Automatically report errors to help us fix issues faster
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start">
                    <input
                      type="checkbox"
                      checked={settings.dataProcessing.aiTrainingConsent}
                      onChange={(e) => updateSettings({
                        dataProcessing: { ...settings.dataProcessing, aiTrainingConsent: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5"
                    />
                    <div className="ml-2">
                      <span className="text-sm font-medium text-gray-700">AI Model Training</span>
                      <p className="text-xs text-gray-500">
                        Allow anonymized data to improve AI models (never includes sensitive content)
                      </p>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'retention' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Data Retention Policies</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Document Retention Period
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      value={settings.dataRetention.documentRetentionDays}
                      onChange={(e) => updateSettings({
                        dataRetention: { ...settings.dataRetention, documentRetentionDays: parseInt(e.target.value) }
                      })}
                      className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      min="30"
                      max="3650"
                    />
                    <span className="text-sm text-gray-600">days</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Chat History Retention Period
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      value={settings.dataRetention.chatHistoryRetentionDays}
                      onChange={(e) => updateSettings({
                        dataRetention: { ...settings.dataRetention, chatHistoryRetentionDays: parseInt(e.target.value) }
                      })}
                      className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      min="7"
                      max="730"
                    />
                    <span className="text-sm text-gray-600">days</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Audit Log Retention Period
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      value={settings.dataRetention.auditLogRetentionDays}
                      onChange={(e) => updateSettings({
                        dataRetention: { ...settings.dataRetention, auditLogRetentionDays: parseInt(e.target.value) }
                      })}
                      className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      min="90"
                      max="2555"
                    />
                    <span className="text-sm text-gray-600">days</span>
                  </div>
                </div>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.dataRetention.autoDeleteEnabled}
                    onChange={(e) => updateSettings({
                      dataRetention: { ...settings.dataRetention, autoDeleteEnabled: e.target.checked }
                    })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    Automatically delete data after retention period expires
                  </span>
                </label>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div className="ml-3">
                      <h4 className="font-medium text-yellow-900">Legal Hold</h4>
                      <p className="text-sm text-yellow-700 mt-1">
                        Data under legal hold will not be deleted regardless of retention settings. 
                        Contact your administrator to place data under legal hold.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'consent' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Consent & Communications</h3>
              
              <div className="space-y-4">
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.consent.marketingEmails}
                      onChange={(e) => updateSettings({
                        consent: { ...settings.consent, marketingEmails: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Marketing communications
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.consent.productUpdates}
                      onChange={(e) => updateSettings({
                        consent: { ...settings.consent, productUpdates: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Product updates and new features
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.consent.securityAlerts}
                      onChange={(e) => updateSettings({
                        consent: { ...settings.consent, securityAlerts: e.target.checked }
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Security alerts and notifications
                    </span>
                  </label>
                </div>

                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Data Processing Agreement</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    By using our service, you acknowledge our data processing practices as outlined in our 
                    Privacy Policy and Data Processing Agreement.
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Last updated: {new Date(settings.consent.lastUpdated).toLocaleDateString()}
                    </span>
                    <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                      View Full Agreement →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="mt-6 pt-6 border-t border-gray-200 flex justify-between">
          <div className="flex space-x-3">
            <button className="flex items-center px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50">
              <Download className="h-4 w-4 mr-2" />
              Export Privacy Settings
            </button>
          </div>
          <button
            onClick={() => showNotification('All changes are saved automatically', 'success')}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

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