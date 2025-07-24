import React from 'react';
import { Layers, User, Building, Zap, Server } from 'lucide-react';
import { AIProvider, AI_PROVIDERS } from './types';
import { useAuth } from '../../contexts/MockAuthContext';
import { useAIPreferences } from '../../contexts/AIPreferencesContext';

interface HierarchyLevel {
  level: number;
  name: string;
  icon: React.ElementType;
  provider?: AIProvider;
  model?: string;
  source: 'request' | 'user' | 'organization' | 'system';
  active: boolean;
  description: string;
}

export const ProviderHierarchy: React.FC = () => {
  const { user, organization } = useAuth();
  const { userPreferences, organizationSettings, effectiveSettings } = useAIPreferences();

  const getHierarchy = (): HierarchyLevel[] => {
    const hierarchy: HierarchyLevel[] = [];

    // Level 1: Per-Request Override
    hierarchy.push({
      level: 1,
      name: 'Per-Request Override',
      icon: Zap,
      source: 'request',
      active: false, // This would be true during an active request
      description: 'Switch providers in real-time for specific requests'
    });

    // Level 2: User Preference
    if (userPreferences?.overrideOrganizationSettings && userPreferences.preferredProvider) {
      hierarchy.push({
        level: 2,
        name: 'User Preference',
        icon: User,
        provider: userPreferences.preferredProvider.provider,
        model: userPreferences.preferredProvider.modelId,
        source: 'user',
        active: true,
        description: `${user?.name || 'User'}'s personal AI settings`
      });
    } else {
      hierarchy.push({
        level: 2,
        name: 'User Preference',
        icon: User,
        source: 'user',
        active: false,
        description: organizationSettings?.allowUserOverrides 
          ? 'Not configured - using organization default'
          : 'Disabled by organization policy'
      });
    }

    // Level 3: Organization Default
    if (organizationSettings?.primaryProvider) {
      hierarchy.push({
        level: 3,
        name: 'Organization Default',
        icon: Building,
        provider: organizationSettings.primaryProvider.provider,
        model: organizationSettings.primaryProvider.modelId,
        source: 'organization',
        active: !userPreferences?.overrideOrganizationSettings,
        description: `${organization?.name || 'Organization'} default settings`
      });
    } else {
      hierarchy.push({
        level: 3,
        name: 'Organization Default',
        icon: Building,
        source: 'organization',
        active: false,
        description: 'Not configured - using system default'
      });
    }

    // Level 4: System Default
    hierarchy.push({
      level: 4,
      name: 'System Default',
      icon: Server,
      provider: 'openai', // This would come from backend config
      model: 'gpt-4-turbo',
      source: 'system',
      active: !organizationSettings?.primaryProvider && !userPreferences?.overrideOrganizationSettings,
      description: 'Platform fallback configuration'
    });

    return hierarchy;
  };

  const hierarchy = getHierarchy();
  const activeLevel = hierarchy.find(h => h.active);

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Layers className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Provider Selection Hierarchy</h3>
        </div>
        {activeLevel && activeLevel.provider && (
          <div className="flex items-center space-x-2 px-3 py-1 bg-blue-50 rounded-full">
            <span className="text-sm font-medium text-blue-700">Active:</span>
            <span className="text-sm text-blue-600">
              {AI_PROVIDERS[activeLevel.provider].name}
            </span>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {hierarchy.map((level, index) => {
          const Icon = level.icon;
          const isActive = level.active;
          const hasProvider = !!level.provider;

          return (
            <div key={level.level} className="relative">
              {/* Connection Line */}
              {index < hierarchy.length - 1 && (
                <div className="absolute left-8 top-12 bottom-0 w-0.5 bg-gray-200" />
              )}

              <div className={`relative flex items-start space-x-4 p-4 rounded-lg transition-all ${
                isActive ? 'bg-blue-50 border-2 border-blue-300' : 'bg-gray-50 border border-gray-200'
              }`}>
                <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${
                  isActive ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  <Icon className="h-6 w-6" />
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className={`font-medium ${isActive ? 'text-blue-900' : 'text-gray-900'}`}>
                        Level {level.level}: {level.name}
                      </h4>
                      <p className="text-sm text-gray-600 mt-1">{level.description}</p>
                    </div>

                    {hasProvider && (
                      <div className="text-right">
                        <div className="flex items-center space-x-2">
                          <span className="text-lg">{AI_PROVIDERS[level.provider!].icon}</span>
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {AI_PROVIDERS[level.provider!].name}
                            </p>
                            <p className="text-xs text-gray-500">{level.model}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {!hasProvider && level.source !== 'request' && (
                    <div className="mt-2">
                      <span className="text-xs text-gray-500 italic">Not configured</span>
                    </div>
                  )}

                  {level.source === 'request' && (
                    <div className="mt-2 text-xs text-gray-500">
                      <p>Available in chat interface • Overrides all other settings</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Current Selection Logic</h4>
        <pre className="text-xs text-gray-600 font-mono">
{`preferred_provider = request.preferred_provider      # Per-request
  || user.ai_provider_preference     # User-level
  || org_settings.preferred_provider # Org default  
  || "openai"                        # System default`}
        </pre>
      </div>
    </div>
  );
};
