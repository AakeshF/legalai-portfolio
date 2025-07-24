import React, { useState } from 'react';
import { tokenService } from './services/auth/token.service';
import { apiClient } from './services/api/client';
import { documentService } from './services/document.service';
import { chatService } from './services/chat.service';

export function AuthTestComponent() {
  const [testResults, setTestResults] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const addResult = (result: string) => {
    setTestResults(prev => [...prev, `${new Date().toISOString()}: ${result}`]);
  };

  const runTests = async () => {
    setIsRunning(true);
    setTestResults([]);

    try {
      // Test 1: Login and receive tokens
      addResult('TEST 1: Testing login...');
      try {
        const loginResponse = await apiClient.post<{
          access_token: string;
          refresh_token: string;
        }>('/api/auth/login', {
          email: '[TEST-EMAIL]',
          password: 'password123'
        }, { skipAuth: true });

        tokenService.setTokens(loginResponse.access_token, loginResponse.refresh_token);
        addResult('✅ Login successful - tokens received and stored');
      } catch (error) {
        addResult(`❌ Login failed: ${error}`);
      }

      // Test 2: Verify tokens are attached to API requests
      addResult('TEST 2: Testing token attachment...');
      try {
        const meResponse = await apiClient.get('/api/auth/me');
        addResult('✅ Token attached successfully - /api/auth/me returned user data');
      } catch (error) {
        addResult(`❌ Token attachment failed: ${error}`);
      }

      // Test 3: Test document service with auth
      addResult('TEST 3: Testing document service...');
      try {
        const documents = await documentService.getDocuments();
        addResult(`✅ Document service working - retrieved ${documents.documents?.length || 0} documents`);
      } catch (error) {
        addResult(`❌ Document service failed: ${error}`);
      }

      // Test 4: Test chat service with auth
      addResult('TEST 4: Testing chat service...');
      try {
        const chatResponse = await chatService.sendMessage('Test message', 'test-session');
        addResult('✅ Chat service working - message sent successfully');
      } catch (error) {
        addResult(`❌ Chat service failed: ${error}`);
      }

      // Test 5: Force 401 to test refresh
      addResult('TEST 5: Testing token refresh on 401...');
      try {
        // Manually clear access token to force refresh
        const currentRefreshToken = tokenService.getRefreshToken();
        tokenService.setTokens('invalid-token', currentRefreshToken!);
        
        // This should trigger a refresh
        const response = await apiClient.get('/api/auth/me');
        addResult('✅ Token refresh working - request succeeded after 401');
      } catch (error) {
        addResult(`❌ Token refresh failed: ${error}`);
      }

      // Test 6: Logout
      addResult('TEST 6: Testing logout...');
      try {
        await apiClient.post('/api/auth/logout', {});
        tokenService.clearTokens();
        addResult('✅ Logout successful - tokens cleared');
      } catch (error) {
        addResult(`❌ Logout failed: ${error}`);
      }

      // Test 7: Verify protected route behavior
      addResult('TEST 7: Testing unauthorized access...');
      try {
        await apiClient.get('/api/documents');
        addResult('❌ Unauthorized access allowed - this should have failed!');
      } catch (error) {
        addResult('✅ Unauthorized access blocked correctly');
      }

    } catch (error) {
      addResult(`Test suite error: ${error}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Auth Integration Test Suite</h1>
      
      <button
        onClick={runTests}
        disabled={isRunning}
        className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {isRunning ? 'Running Tests...' : 'Run Auth Tests'}
      </button>

      <div className="bg-gray-100 rounded p-4">
        <h2 className="text-lg font-semibold mb-2">Test Results:</h2>
        {testResults.length === 0 ? (
          <p className="text-gray-500">Click "Run Auth Tests" to start</p>
        ) : (
          <pre className="whitespace-pre-wrap font-mono text-sm">
            {testResults.join('\n')}
          </pre>
        )}
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded">
        <h3 className="font-semibold mb-2">Test Checklist:</h3>
        <ul className="space-y-1 text-sm">
          <li>✓ Can login and receive tokens</li>
          <li>✓ Tokens attached to API requests</li>
          <li>✓ 401 triggers refresh automatically</li>
          <li>✓ Logout clears all tokens</li>
          <li>✓ Protected routes redirect when unauthorized</li>
        </ul>
      </div>
    </div>
  );
}