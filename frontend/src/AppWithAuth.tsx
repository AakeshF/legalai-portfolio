import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SimpleModeProvider } from './contexts/SimpleModeContext';
import { AIPreferencesProvider } from './contexts/AIPreferencesContext';
import { lazyWithRetry } from './utils/lazyWithRetry';
import { LoadingStates } from './components/LoadingStates';

// Auth Components (loaded immediately for security)
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';
import { ProtectedRoute } from './components/auth/ProtectedRoute';

// Lazy loaded components
const App = lazyWithRetry(() => import('./App'));
const UserProfile = lazyWithRetry(() => import('./components/auth/UserProfile').then(m => ({ default: m.UserProfile })));
const OrganizationSettings = lazyWithRetry(() => import('./components/auth/OrganizationSettings').then(m => ({ default: m.OrganizationSettings })));
const OrganizationDashboard = lazyWithRetry(() => import('./components/auth/OrganizationDashboard').then(m => ({ default: m.OrganizationDashboard })));
const SecurityPage = lazyWithRetry(() => import('./components/security/SecurityPage').then(m => ({ default: m.SecurityPage })));
const UnauthorizedPage = lazyWithRetry(() => import('./pages/UnauthorizedPage').then(m => ({ default: m.UnauthorizedPage })));
const NotFoundPage = lazyWithRetry(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));
const CaseIntakeWizard = lazyWithRetry(() => import('./components/intake/CaseIntakeWizard').then(m => ({ default: m.CaseIntakeWizard })));
const DeadlineCalculatorDemo = lazyWithRetry(() => import('./components/deadline-calculator/DeadlineCalculatorDemo').then(m => ({ default: m.DeadlineCalculatorDemo })));
const EnhancedDashboard = lazyWithRetry(() => import('./components/dashboard').then(m => ({ default: m.EnhancedDashboard })));
const AnonymizationPage = lazyWithRetry(() => import('./pages/AnonymizationPage').then(m => ({ default: m.AnonymizationPage })));
const SecureAIAssistantPage = lazyWithRetry(() => import('./pages/SecureAIAssistantPage').then(m => ({ default: m.SecureAIAssistantPage })));

// Loading fallback component
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <LoadingStates type="spinner" />
  </div>
);

// Layout wrapper for authenticated pages
const AuthenticatedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
};

// Settings page wrapper
const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>
        <UserProfile />
      </div>
    </div>
  );
};

// Organization page wrapper
const OrganizationPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Organization</h1>
        <OrganizationSettings />
      </div>
    </div>
  );
};

// Organization users page wrapper
const OrganizationUsersPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <OrganizationDashboard />
      </div>
    </div>
  );
};

export function AppWithAuth() {
  return (
    <Router>
      <AuthProvider>
        <AIPreferencesProvider>
          <SimpleModeProvider>
            <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginForm />} />
            <Route path="/register" element={<RegisterForm />} />
            
            {/* Protected routes */}
            <Route path="/" element={
              <ProtectedRoute>
                <AuthenticatedLayout>
                  <Suspense fallback={<PageLoader />}>
                    <App />
                  </Suspense>
                </AuthenticatedLayout>
              </ProtectedRoute>
            } />
            
            <Route path="/profile" element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } />
            
            <Route path="/settings" element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } />
            
            <Route path="/organization" element={
              <ProtectedRoute>
                <OrganizationPage />
              </ProtectedRoute>
            } />
            
            <Route path="/organization/users" element={
              <ProtectedRoute requiredRole={['admin']}>
                <OrganizationUsersPage />
              </ProtectedRoute>
            } />
            
            <Route path="/security" element={
              <ProtectedRoute>
                <SecurityPage />
              </ProtectedRoute>
            } />
            
            <Route path="/intake" element={
              <ProtectedRoute>
                <CaseIntakeWizard />
              </ProtectedRoute>
            } />
            
            <Route path="/deadlines" element={
              <ProtectedRoute>
                <DeadlineCalculatorDemo />
              </ProtectedRoute>
            } />
            
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <EnhancedDashboard />
              </ProtectedRoute>
            } />
            
            <Route path="/ai-assistant" element={
              <ProtectedRoute>
                <AnonymizationPage />
              </ProtectedRoute>
            } />
            
            <Route path="/secure-ai" element={
              <ProtectedRoute>
                <SecureAIAssistantPage />
              </ProtectedRoute>
            } />
            
            {/* Error pages */}
            <Route path="/unauthorized" element={<UnauthorizedPage />} />
            
            {/* Catch all - show 404 */}
            <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </SimpleModeProvider>
        </AIPreferencesProvider>
      </AuthProvider>
    </Router>
  );
}