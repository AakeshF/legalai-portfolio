export type AIProvider = 'openai' | 'anthropic' | 'google' | 'azure' | 'ollama';

export interface AIModel {
  id: string;
  name: string;
  provider: AIProvider;
  capabilities: string[];
  contextWindow: number;
  costPer1kTokens: {
    input: number;
    output: number;
  };
}

export interface AIProviderConfig {
  provider: AIProvider;
  modelId: string;
  apiKey?: string;
  endpoint?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface OrganizationAISettings {
  id: string;
  organizationId: string;
  primaryProvider: AIProviderConfig;
  fallbackProvider?: AIProviderConfig;
  allowUserOverrides: boolean;
  createdAt: string;
  updatedAt: string;
}

export const AI_PROVIDERS: Record<AIProvider, { name: string; icon: string }> = {
  openai: { name: 'OpenAI', icon: '🤖' },
  anthropic: { name: 'Anthropic', icon: '🧠' },
  google: { name: 'Google AI', icon: '🔍' },
  azure: { name: 'Azure OpenAI', icon: '☁️' },
  ollama: { name: 'Local AI', icon: '🏠' }
};

export const AI_MODELS: AIModel[] = [
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    provider: 'openai',
    capabilities: ['chat', 'analysis', 'summarization'],
    contextWindow: 128000,
    costPer1kTokens: { input: 0.01, output: 0.03 }
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    provider: 'openai',
    capabilities: ['chat', 'analysis', 'summarization'],
    contextWindow: 16385,
    costPer1kTokens: { input: 0.0005, output: 0.0015 }
  },
  {
    id: 'claude-3-opus',
    name: 'Claude 3 Opus',
    provider: 'anthropic',
    capabilities: ['chat', 'analysis', 'summarization', 'legal-reasoning'],
    contextWindow: 200000,
    costPer1kTokens: { input: 0.015, output: 0.075 }
  },
  {
    id: 'claude-3-sonnet',
    name: 'Claude 3 Sonnet',
    provider: 'anthropic',
    capabilities: ['chat', 'analysis', 'summarization', 'legal-reasoning'],
    contextWindow: 200000,
    costPer1kTokens: { input: 0.003, output: 0.015 }
  },
  {
    id: 'gemini-pro',
    name: 'Gemini Pro',
    provider: 'google',
    capabilities: ['chat', 'analysis', 'summarization'],
    contextWindow: 32768,
    costPer1kTokens: { input: 0.00025, output: 0.0005 }
  },
  {
    id: 'llama3.1',
    name: 'Llama 3.1',
    provider: 'ollama',
    capabilities: ['chat', 'analysis', 'summarization'],
    contextWindow: 128000,
    costPer1kTokens: { input: 0, output: 0 }
  },
  {
    id: 'mistral',
    name: 'Mistral',
    provider: 'ollama',
    capabilities: ['chat', 'analysis', 'summarization'],
    contextWindow: 32768,
    costPer1kTokens: { input: 0, output: 0 }
  }
];
