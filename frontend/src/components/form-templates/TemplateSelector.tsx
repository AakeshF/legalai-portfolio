import React, { useState, useMemo } from 'react';
import { Search, Filter, CheckCircle, Clock, FileText, Calendar, Users, AlertCircle } from 'lucide-react';
import { FormTemplate } from './types';
import { groupTemplatesByCategory, sortTemplates } from './utils';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../utils/api';
import { useToast } from '../Toast';
import { Skeleton } from '../Skeleton';

interface TemplateSelectorProps {
  jurisdiction: {
    state: string;
    county?: string;
    court?: string;
  };
  caseType: string;
  onSelect: (template: FormTemplate) => void;
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  jurisdiction,
  caseType,
  onSelect
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showRequiredOnly, setShowRequiredOnly] = useState(false);
  const { isSimpleMode, getSimpleText } = useSimpleMode();
  const { showError } = useToast();

  // Fetch templates from API
  const { data: templates = [], isLoading, error } = useQuery<FormTemplate[]>({
    queryKey: ['form-templates', jurisdiction.state, jurisdiction.county, caseType],
    queryFn: async () => {
      const params = new URLSearchParams({
        state: jurisdiction.state,
        caseType,
        ...(jurisdiction.county && { county: jurisdiction.county }),
        ...(jurisdiction.court && { court: jurisdiction.court })
      });
      
      const response = await api.get(`/api/form-templates?${params}`);
      if (!response.ok) throw new Error('Failed to fetch templates');
      
      const data = await response.json();
      return data.templates;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    onError: () => {
      showError('Failed to load templates', 'Please try again');
    }
  });

  // Filter templates
  const filteredTemplates = useMemo(() => {
    let filtered = templates;

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(template => 
        template.name.toLowerCase().includes(term) ||
        template.description.toLowerCase().includes(term) ||
        template.category.toLowerCase().includes(term)
      );
    }

    // Filter by required only
    if (showRequiredOnly) {
      filtered = filtered.filter(template => template.isRequired);
    }

    return sortTemplates(filtered);
  }, [templates, searchTerm, showRequiredOnly]);

  // Group templates by category
  const groupedTemplates = useMemo(() => 
    groupTemplatesByCategory(filteredTemplates),
    [filteredTemplates]
  );

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {getSimpleText('Unable to Load Forms')}
        </h3>
        <p className="text-gray-600">
          {getSimpleText('Please check your connection and try again')}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder={getSimpleText('Search forms...')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg 
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
              ${isSimpleMode ? 'text-lg' : 'text-base'}`}
          />
        </div>
        
        <button
          onClick={() => setShowRequiredOnly(!showRequiredOnly)}
          className={`flex items-center px-4 py-3 border rounded-lg transition-all
            ${showRequiredOnly 
              ? 'bg-blue-50 border-blue-300 text-blue-700' 
              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}
            ${isSimpleMode ? 'text-lg min-h-[48px]' : 'text-base'}`}
        >
          <Filter className="w-5 h-5 mr-2" />
          {getSimpleText('Required Only')}
        </button>
      </div>

      {/* Template List */}
      {isLoading ? (
        <TemplateListSkeleton />
      ) : (
        <div className="space-y-8">
          {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
            <div key={category}>
              <h3 className={`font-semibold text-gray-900 mb-4
                ${isSimpleMode ? 'text-xl' : 'text-lg'}`}>
                {getSimpleText(category)}
              </h3>
              
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {categoryTemplates.map((template) => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    onSelect={() => onSelect(template)}
                  />
                ))}
              </div>
            </div>
          ))}
          
          {filteredTemplates.length === 0 && (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">
                {searchTerm 
                  ? getSimpleText('No forms match your search')
                  : getSimpleText('No forms available for this jurisdiction')}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Template Card Component
interface TemplateCardProps {
  template: FormTemplate;
  onSelect: () => void;
}

const TemplateCard: React.FC<TemplateCardProps> = ({ template, onSelect }) => {
  const { isSimpleMode, getSimpleText } = useSimpleMode();
  
  return (
    <button
      onClick={onSelect}
      className="w-full p-6 bg-white border border-gray-200 rounded-lg hover:shadow-md 
        transition-all duration-200 text-left group hover:border-blue-300"
    >
      <div className="flex items-start justify-between mb-3">
        <FileText className="w-6 h-6 text-blue-600 flex-shrink-0" />
        {template.isRequired && (
          <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded">
            {getSimpleText('Required')}
          </span>
        )}
      </div>
      
      <h4 className={`font-semibold text-gray-900 mb-2 group-hover:text-blue-600
        ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
        {template.name}
      </h4>
      
      <p className={`text-gray-600 mb-4 line-clamp-2
        ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
        {template.description}
      </p>
      
      <div className="flex items-center gap-4 text-sm text-gray-500">
        {template.metadata?.estimatedTime && (
          <div className="flex items-center">
            <Clock className="w-4 h-4 mr-1" />
            {template.metadata.estimatedTime} {getSimpleText('min')}
          </div>
        )}
        
        {template.hasNewerVersion && (
          <div className="flex items-center text-amber-600">
            <AlertCircle className="w-4 h-4 mr-1" />
            {getSimpleText('Update available')}
          </div>
        )}
      </div>
    </button>
  );
};

// Skeleton loader
const TemplateListSkeleton: React.FC = () => {
  return (
    <div className="space-y-8">
      {[1, 2].map((section) => (
        <div key={section}>
          <div className="h-7 w-32 bg-gray-200 rounded mb-4 animate-pulse" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <div key={item} className="p-6 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-6 h-6 bg-gray-200 rounded animate-pulse" />
                  <div className="w-16 h-5 bg-gray-200 rounded animate-pulse" />
                </div>
                <div className="h-5 w-3/4 bg-gray-200 rounded mb-2 animate-pulse" />
                <div className="h-4 w-full bg-gray-200 rounded mb-1 animate-pulse" />
                <div className="h-4 w-2/3 bg-gray-200 rounded mb-4 animate-pulse" />
                <div className="flex gap-4">
                  <div className="h-4 w-16 bg-gray-200 rounded animate-pulse" />
                  <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};