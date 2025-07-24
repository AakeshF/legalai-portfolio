import React, { createContext, useContext, useState, useEffect } from 'react';

// Simple AI provider config type
interface AIProviderConfig {
  provider: string;
  model?: string;
  settings?: Record<string, any>;
}

interface UserAIPreferences {
  id: string;
  userId: string;
  overrideOrganizationSettings: boolean;
  preferredProvider?: AIProviderConfig;
  createdAt: string;
  updatedAt: string;
}

interface AIPreferencesContextType {
  userPreferences: UserAIPreferences | null;
  organizationSettings: any | null;
  effectiveSettings: AIProviderConfig | null;
  isLoading: boolean;
  updateUserPreferences: (preferences: Partial<UserAIPreferences>) => Promise<void>;
  toggleOverride: (override: boolean) => Promise<void>;
  refreshSettings: () => Promise<void>;
}

const AIPreferencesContext = createContext<AIPreferencesContextType | undefined>(undefined);

export const useAIPreferences = () => {
  const context = useContext(AIPreferencesContext);
  if (!context) {
    throw new Error('useAIPreferences must be used within AIPreferencesProvider');
  }
  return context;
};

export const AIPreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Authentication disabled - create mock user
  const user = { id: 'anonymous-user', organizationId: 'anonymous-org' };
  
  const [userPreferences, setUserPreferences] = useState<UserAIPreferences | null>(null);
  const [organizationSettings, setOrganizationSettings] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Always fetch settings in no-auth mode
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setIsLoading(true);
    try {
      // In no-auth mode, set default AI preferences
      console.info('Authentication disabled - using default AI preferences');
      
      // Set reasonable defaults for no-auth mode - LOCAL AI ONLY
      setUserPreferences({
        id: 'anonymous-prefs',
        userId: 'anonymous-user',
        overrideOrganizationSettings: false,
        preferredProvider: {
          provider: 'ollama',
          model: 'llama3.1'
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      });
      
      setOrganizationSettings({
        allowedProviders: ['ollama'],
        defaultProvider: 'ollama',
        requireApproval: false,
        costLimits: {
          dailyLimit: 0,
          monthlyLimit: 0
        },
        primaryProvider: {
          provider: 'ollama',
          model: 'llama3.1'
        }
      });

    } catch (error) {
      console.error('Failed to set AI preferences defaults:', error);
      // Set minimal defaults on error
      setUserPreferences({
        id: 'anonymous-prefs',
        userId: 'anonymous-user',
        overrideOrganizationSettings: false,
        preferredProvider: undefined,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      });
      setOrganizationSettings({
        allowedProviders: ['ollama'],
        defaultProvider: 'ollama',
        requireApproval: false,
        costLimits: {
          dailyLimit: 0,
          monthlyLimit: 0
        },
        primaryProvider: {
          provider: 'ollama',
          model: 'llama3.1'
        }
      });
    } finally {
      setIsLoading(false);
    }
  };

  const updateUserPreferences = async (preferences: Partial<UserAIPreferences>) => {
    try {
      // In no-auth mode, just update local state
      console.info('Authentication disabled - updating local AI preferences');
      setUserPreferences(prev => prev ? { ...prev, ...preferences, updatedAt: new Date().toISOString() } : null);
    } catch (error) {
      console.error('Failed to update user preferences:', error);
      throw error;
    }
  };

  const toggleOverride = async (override: boolean) => {
    await updateUserPreferences({ overrideOrganizationSettings: override });
  };

  const refreshSettings = async () => {
    await fetchSettings();
  };

  // Calculate effective settings based on override status
  const effectiveSettings = userPreferences?.overrideOrganizationSettings && userPreferences.preferredProvider
    ? userPreferences.preferredProvider
    : organizationSettings?.primaryProvider || null;

  return (
    <AIPreferencesContext.Provider
      value={{
        userPreferences,
        organizationSettings,
        effectiveSettings,
        isLoading,
        updateUserPreferences,
        toggleOverride,
        refreshSettings
      }}
    >
      {children}
    </AIPreferencesContext.Provider>
  );
};
