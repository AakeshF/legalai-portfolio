import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface SimpleModeContextType {
  isSimpleMode: boolean;
  toggleSimpleMode: () => void;
  getSimpleText: (technicalText: string) => string;
}

const SimpleModeContext = createContext<SimpleModeContextType | undefined>(undefined);

const SIMPLE_MODE_KEY = 'legalAI_simpleMode';

// Text replacements for technical jargon
const textReplacements: Record<string, string> = {
  // Navigation and actions
  'Upload': 'Add Document',
  'Upload Document': 'Add Your Document',
  'Download': 'Save to Computer',
  'Export': 'Save Copy',
  'Import': 'Add from Computer',
  'Submit': 'Send',
  'Cancel': 'Go Back',
  'Delete': 'Remove',
  'Edit': 'Change',
  'Update': 'Save Changes',
  'Refresh': 'Check for Updates',
  'Sync': 'Update Information',
  
  // Status messages
  'Processing': 'Working on it',
  'Loading': 'Getting Ready',
  'Pending': 'Waiting',
  'Complete': 'Done',
  'Failed': 'Something Went Wrong',
  'Error': 'Problem',
  'Success': 'All Set',
  
  // Technical terms
  'API Error': 'Connection Problem',
  'Network Error': 'Internet Problem',
  'Authentication Error': 'Sign-in Problem',
  'Authorization Error': 'Permission Problem',
  'Validation Error': 'Information Problem',
  'Server Error': 'System Problem',
  'Client Error': 'Computer Problem',
  
  // Document related
  'Metadata': 'Document Information',
  'Analytics': 'Document Details',
  'Insights': 'Key Points',
  'Summary': 'Main Points',
  'Extract': 'Pull Out Information',
  'Parse': 'Read Document',
  'Analyze': 'Review Document',
  
  // Chat and AI
  'AI Assistant': 'Legal Helper',
  'Query': 'Question',
  'Response': 'Answer',
  'Prompt': 'Your Question',
  'Generate': 'Create',
  'Chat History': 'Past Conversations',
  
  // Account and settings
  'Profile': 'Your Information',
  'Settings': 'Options',
  'Preferences': 'Your Choices',
  'Configuration': 'Setup',
  'Integration': 'Connection',
  'API Key': 'Access Code',
  'Token': 'Security Code',
  'Session': 'Current Visit',
  'Logout': 'Sign Out',
  'Login': 'Sign In',
  
  // Legal specific
  'Jurisdiction': 'Legal Area',
  'Citation': 'Legal Reference',
  'Precedent': 'Previous Case',
  'Statute': 'Law',
  'Regulation': 'Rule',
  'Compliance': 'Following Rules',
  'Litigation': 'Legal Case',
  'Discovery': 'Finding Evidence',
  'Deposition': 'Witness Statement',
  'Brief': 'Legal Document',
  'Motion': 'Legal Request',
  'Filing': 'Court Document',
  
  // Security
  'Encryption': 'Security Protection',
  'Two-Factor Authentication': 'Extra Security Step',
  '2FA': 'Extra Security',
  'Permissions': 'Who Can See This',
  'Access Control': 'Who Can Use This',
  'Audit Log': 'Activity History',
  'Security Status': 'Safety Check',
  
  // Billing
  'Subscription': 'Monthly Plan',
  'Invoice': 'Bill',
  'Payment Method': 'How You Pay',
  'Usage': 'How Much You Used',
  'Credits': 'Available Uses',
  'Billing Cycle': 'Payment Period'
};

export const SimpleModeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isSimpleMode, setIsSimpleMode] = useState<boolean>(() => {
    const stored = localStorage.getItem(SIMPLE_MODE_KEY);
    return stored === 'true';
  });

  useEffect(() => {
    localStorage.setItem(SIMPLE_MODE_KEY, isSimpleMode.toString());
    
    // Apply or remove simple mode class to document root
    if (isSimpleMode) {
      document.documentElement.classList.add('simple-mode');
      document.documentElement.setAttribute('data-simple-mode', 'true');
    } else {
      document.documentElement.classList.remove('simple-mode');
      document.documentElement.removeAttribute('data-simple-mode');
    }
    
    // Announce mode change to screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = isSimpleMode 
      ? 'Simple mode is now active. Text is larger and language is simplified.'
      : 'Simple mode is now inactive. Standard view restored.';
    document.body.appendChild(announcement);
    setTimeout(() => document.body.removeChild(announcement), 1000);
  }, [isSimpleMode]);

  const toggleSimpleMode = () => {
    setIsSimpleMode(prev => !prev);
  };

  const getSimpleText = (technicalText: string): string => {
    if (!isSimpleMode) return technicalText;
    
    // Check for exact match first
    if (textReplacements[technicalText]) {
      return textReplacements[technicalText];
    }
    
    // Check for partial matches and replace
    let simpleText = technicalText;
    Object.entries(textReplacements).forEach(([technical, simple]) => {
      const regex = new RegExp(`\\b${technical}\\b`, 'gi');
      simpleText = simpleText.replace(regex, simple);
    });
    
    return simpleText;
  };

  return (
    <SimpleModeContext.Provider value={{ isSimpleMode, toggleSimpleMode, getSimpleText }}>
      {children}
    </SimpleModeContext.Provider>
  );
};

export const useSimpleMode = (): SimpleModeContextType => {
  const context = useContext(SimpleModeContext);
  if (!context) {
    throw new Error('useSimpleMode must be used within a SimpleModeProvider');
  }
  return context;
};

export default SimpleModeContext;