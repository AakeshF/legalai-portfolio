import React, { useState, useEffect } from 'react';
import { Shield, Smartphone, Key, CheckCircle, AlertCircle, Copy, Download, RefreshCw } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';
import { securityService } from '../../services/security.service';

interface TwoFactorStatus {
  enabled: boolean;
  method: 'app' | 'sms' | null;
  phoneNumber?: string;
  backupCodesRemaining?: number;
  lastEnabled?: string;
  lastUsed?: string;
}

export const TwoFactorAuth: React.FC = () => {
  const { user } = useAuth();
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(false);
  const [setupStep, setSetupStep] = useState<'method' | 'verify' | 'backup'>('method');
  const [selectedMethod, setSelectedMethod] = useState<'app' | 'sms'>('app');
  const [qrCode, setQrCode] = useState<string>('');
  const [secret, setSecret] = useState<string>('');
  const [verificationCode, setVerificationCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('success');

  useEffect(() => {
    fetchTwoFactorStatus();
  }, []);

  const fetchTwoFactorStatus = async () => {
    try {
      const data = await securityService.get2FAStatus();
      setStatus(data);
    } catch (error) {
      console.error('Failed to fetch 2FA status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const startSetup = async () => {
    setShowSetup(true);
    setSetupStep('method');
  };

  const generateQRCode = async () => {
    try {
      const response = await api.post(API_ENDPOINTS.security.twoFactor.setup, {
        method: selectedMethod,
        phoneNumber: selectedMethod === 'sms' ? phoneNumber : undefined
      });

      if (response.data) {
        if (selectedMethod === 'app') {
          setQrCode(response.data.qrCode);
          setSecret(response.data.secret);
        }
        setSetupStep('verify');
      }
    } catch (error) {
      showNotification('Failed to initialize 2FA setup', 'error');
    }
  };

  const verifyAndEnable = async () => {
    try {
      const response = await api.post(API_ENDPOINTS.security.twoFactor.verify, {
        code: verificationCode,
        method: selectedMethod
      });

      if (response.data) {
        setBackupCodes(response.data.backupCodes);
        setSetupStep('backup');
      }
    } catch (error) {
      showNotification('Invalid verification code', 'error');
    }
  };

  const completeSetup = async () => {
    setShowSetup(false);
    setStatus({
      ...status!,
      enabled: true,
      method: selectedMethod,
      phoneNumber: selectedMethod === 'sms' ? phoneNumber : undefined,
      backupCodesRemaining: 10
    });
    showNotification('Two-factor authentication enabled successfully', 'success');
  };

  const disable2FA = async () => {
    if (!confirm('Are you sure you want to disable two-factor authentication? This will make your account less secure.')) {
      return;
    }

    try {
      await api.post(API_ENDPOINTS.security.twoFactor.disable);
      setStatus({ ...status!, enabled: false, method: null });
      showNotification('Two-factor authentication disabled', 'success');
    } catch (error) {
      showNotification('Failed to disable 2FA', 'error');
    }
  };

  const regenerateBackupCodes = async () => {
    if (!confirm('This will invalidate your existing backup codes. Continue?')) {
      return;
    }

    try {
      const response = await api.post(API_ENDPOINTS.security.twoFactor.regenerateBackupCodes);
      if (response.data) {
        setBackupCodes(response.data.codes);
        showNotification('Backup codes regenerated successfully', 'success');
      }
    } catch (error) {
      showNotification('Failed to regenerate backup codes', 'error');
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showNotification('Copied to clipboard', 'success');
    } catch (error) {
      showNotification('Failed to copy', 'error');
    }
  };

  const downloadBackupCodes = () => {
    const content = backupCodes.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'legal-ai-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const showNotification = (message: string, type: 'success' | 'error') => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
  };

  if (isLoading) {
    return <div className="animate-pulse h-64 bg-gray-200 rounded-lg"></div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
          <Shield className="h-6 w-6 mr-2 text-blue-600" />
          Two-Factor Authentication
        </h2>
        {status?.enabled && (
          <span className="flex items-center text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">
            <CheckCircle className="h-4 w-4 mr-1" />
            Enabled
          </span>
        )}
      </div>

      {!status?.enabled ? (
        <div className="text-center py-8">
          <Shield className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Enhance Your Account Security
          </h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Two-factor authentication adds an extra layer of security to your account by requiring a second form of verification.
          </p>
          <button
            onClick={startSetup}
            className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
          >
            Enable Two-Factor Authentication
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-3">Current Settings</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Method</span>
                <span className="text-sm font-medium text-gray-900 flex items-center">
                  {status.method === 'app' ? (
                    <>
                      <Smartphone className="h-4 w-4 mr-1" />
                      Authenticator App
                    </>
                  ) : (
                    <>
                      <Key className="h-4 w-4 mr-1" />
                      SMS to {status.phoneNumber}
                    </>
                  )}
                </span>
              </div>
              {status.backupCodesRemaining !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Backup Codes Remaining</span>
                  <span className={`text-sm font-medium ${
                    status.backupCodesRemaining <= 3 ? 'text-orange-600' : 'text-gray-900'
                  }`}>
                    {status.backupCodesRemaining}
                  </span>
                </div>
              )}
              {status.lastUsed && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Last Used</span>
                  <span className="text-sm font-medium text-gray-900">
                    {new Date(status.lastUsed).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={regenerateBackupCodes}
              className="flex items-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate Backup Codes
            </button>
            <button
              onClick={disable2FA}
              className="px-4 py-2 text-red-600 border border-red-300 rounded-md hover:bg-red-50"
            >
              Disable 2FA
            </button>
          </div>
        </div>
      )}

      {/* Setup Modal */}
      {showSetup && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            {setupStep === 'method' && (
              <>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Choose Authentication Method
                </h3>
                <div className="space-y-3">
                  <label className="flex items-center p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      value="app"
                      checked={selectedMethod === 'app'}
                      onChange={(e) => setSelectedMethod(e.target.value as 'app')}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium text-gray-900">Authenticator App</div>
                      <div className="text-sm text-gray-600">
                        Use apps like Google Authenticator or Authy
                      </div>
                    </div>
                  </label>
                  <label className="flex items-center p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      value="sms"
                      checked={selectedMethod === 'sms'}
                      onChange={(e) => setSelectedMethod(e.target.value as 'sms')}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium text-gray-900">SMS Text Message</div>
                      <div className="text-sm text-gray-600">
                        Receive codes via text message
                      </div>
                    </div>
                  </label>
                </div>
                
                {selectedMethod === 'sms' && (
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      placeholder="[PHONE-NUMBER]"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                )}

                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    onClick={() => setShowSetup(false)}
                    className="px-4 py-2 text-gray-700 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={generateQRCode}
                    disabled={selectedMethod === 'sms' && !phoneNumber}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    Continue
                  </button>
                </div>
              </>
            )}

            {setupStep === 'verify' && (
              <>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Verify Setup
                </h3>
                
                {selectedMethod === 'app' && qrCode && (
                  <div className="text-center mb-4">
                    <img src={qrCode} alt="QR Code" className="mx-auto mb-4" />
                    <p className="text-sm text-gray-600 mb-2">
                      Scan this QR code with your authenticator app
                    </p>
                    <div className="bg-gray-50 p-3 rounded-md">
                      <p className="text-xs text-gray-500 mb-1">Or enter this code manually:</p>
                      <div className="flex items-center justify-center space-x-2">
                        <code className="text-sm font-mono">{secret}</code>
                        <button
                          onClick={() => copyToClipboard(secret)}
                          className="text-blue-600 hover:text-blue-700"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {selectedMethod === 'sms' && (
                  <p className="text-gray-600 mb-4">
                    We've sent a verification code to {phoneNumber}
                  </p>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Enter Verification Code
                  </label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    placeholder="123456"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-center text-lg font-mono"
                    maxLength={6}
                  />
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    onClick={() => setSetupStep('method')}
                    className="px-4 py-2 text-gray-700 hover:text-gray-800"
                  >
                    Back
                  </button>
                  <button
                    onClick={verifyAndEnable}
                    disabled={verificationCode.length !== 6}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    Verify & Enable
                  </button>
                </div>
              </>
            )}

            {setupStep === 'backup' && (
              <>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Save Backup Codes
                </h3>
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                  <p className="text-sm text-yellow-800">
                    Save these backup codes in a secure location. Each code can only be used once.
                  </p>
                </div>
                
                <div className="bg-gray-50 rounded-md p-4 mb-4">
                  <div className="grid grid-cols-2 gap-2 font-mono text-sm">
                    {backupCodes.map((code, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <span>{code}</span>
                        <button
                          onClick={() => copyToClipboard(code)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  onClick={downloadBackupCodes}
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 mb-4"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download Backup Codes
                </button>

                <button
                  onClick={completeSetup}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Complete Setup
                </button>
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