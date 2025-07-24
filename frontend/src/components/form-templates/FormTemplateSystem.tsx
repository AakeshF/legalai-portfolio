import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { FileText, Save, Send, AlertCircle, CheckCircle } from 'lucide-react';
import { FormTemplate as LocalFormTemplate, FormData } from './types';
import { TemplateSelector } from './TemplateSelector';
import { DynamicFormBuilder } from './DynamicFormBuilder';
import { validateFormWithMCP, populateFromMatter } from './utils';
import { api } from '../../utils/api';
import { useToast } from '../Toast';
import { LoadingStates } from '../LoadingStates';
import { 
  useFormTemplates, 
  useGenerateDocument, 
  useSaveFormDraft,
  useCheckTemplateUpdates,
  FormTemplate as MCPFormTemplate 
} from '../../services/mcp';

interface FormTemplateSystemProps {
  matterId?: string;
  onDocumentGenerated?: (documentId: string) => void;
}

export const FormTemplateSystem: React.FC<FormTemplateSystemProps> = ({
  matterId: propMatterId,
  onDocumentGenerated
}) => {
  const { matterId: paramMatterId } = useParams();
  const effectiveMatterId = propMatterId || paramMatterId;
  
  const [selectedTemplate, setSelectedTemplate] = useState<LocalFormTemplate | null>(null);
  const [matterData, setMatterData] = useState<any>(null);
  const [formData, setFormData] = useState<FormData>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  
  const { showToast } = useToast();
  
  // Load matter data
  const [caseType, setCaseType] = useState<string>('');
  const [jurisdiction, setJurisdiction] = useState<string>('');
  
  useEffect(() => {
    if (effectiveMatterId) {
      loadMatterData();
    }
  }, [effectiveMatterId]);
  
  const loadMatterData = async () => {
    try {
      const matter = await api.get(`/api/matters/${effectiveMatterId}`);
      setMatterData(matter);
      setCaseType(matter.type);
      setJurisdiction(matter.jurisdiction);
    } catch (error) {
      console.error('Failed to load matter data:', error);
      showToast({
        title: 'Error loading matter',
        description: 'Unable to fetch matter data. Please try again.',
        variant: 'error'
      });
    }
  };
  
  // Use MCP hooks
  const { data: mcpTemplates, isLoading, error } = useFormTemplates(caseType, jurisdiction, true);
  const generateDocumentMutation = useGenerateDocument();
  const saveFormDraftMutation = useSaveFormDraft();
  
  // Convert MCP templates to local format
  const templates: LocalFormTemplate[] = React.useMemo(() => {
    if (!mcpTemplates) return [];
    return mcpTemplates.map(t => ({
      ...t,
      lastUpdated: new Date(t.lastUpdated),
      mcpLastUpdated: new Date(t.lastUpdated)
    }));
  }, [mcpTemplates]);
  
  // Check for template updates
  const templateIds = templates.map(t => t.id);
  const { data: templateUpdates } = useCheckTemplateUpdates(templateIds);

  const handleTemplateSelect = (template: LocalFormTemplate) => {
    setSelectedTemplate(template);
    
    // Auto-populate from matter data
    if (matterData) {
      const populated = populateFromMatter(template, matterData);
      setFormData(populated);
    }
  };

  const handleFormChange = (newFormData: FormData) => {
    setFormData(newFormData);
    setValidationErrors({}); // Clear errors on change
  };

  const validateForm = async () => {
    if (!selectedTemplate) return false;

    const errors = await validateFormWithMCP(formData, selectedTemplate, api);
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleGenerateDocument = async () => {
    if (!selectedTemplate) return;

    const isValid = await validateForm();
    if (!isValid) {
      showToast({
        title: 'Validation failed',
        description: 'Please fix the errors before generating the document.',
        variant: 'error'
      });
      return;
    }

    try {
      const generatedDoc = await generateDocumentMutation.mutateAsync({
        templateId: selectedTemplate.id,
        formData: formData,
        format: 'pdf',
        includeEfilingXml: true
      });

      // Save to matter
      await api.post(`/api/matters/${effectiveMatterId}/documents`, {
        documentId: generatedDoc.documentId,
        metadata: {
          templateId: selectedTemplate.id,
          generatedFrom: 'form_template',
          efilingReady: generatedDoc.efilingReady
        }
      });

      showToast({
        title: 'Document generated successfully',
        description: 'The form has been generated and saved to the matter.',
        variant: 'success'
      });

      if (onDocumentGenerated) {
        onDocumentGenerated(generatedDoc.documentId);
      }

      // Reset form
      setSelectedTemplate(null);
      setFormData({});
    } catch (error) {
      console.error('Failed to generate document:', error);
      showToast({
        title: 'Generation failed',
        description: 'Unable to generate the document. Please try again.',
        variant: 'error'
      });
    }
  };

  const handleSaveDraft = async () => {
    if (!selectedTemplate || !effectiveMatterId) return;

    try {
      await saveFormDraftMutation.mutateAsync({
        matterId: effectiveMatterId,
        templateId: selectedTemplate.id,
        formData: formData
      });

      showToast({
        title: 'Draft saved',
        description: 'Your form draft has been saved.',
        variant: 'success'
      });
    } catch (error) {
      console.error('Failed to save draft:', error);
      showToast({
        title: 'Save failed',
        description: 'Unable to save the draft. Please try again.',
        variant: 'error'
      });
    }
  };

  if (isLoading) {
    return <LoadingStates type="page" message="Loading form templates..." />;
  }

  return (
    <div className="form-template-system">
      {!selectedTemplate ? (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Select a Form Template
          </h2>
          <TemplateSelector
            templates={templates}
            onSelect={handleTemplateSelect}
          />
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {selectedTemplate.name}
              </h2>
              {selectedTemplate.description && (
                <p className="text-gray-600 mt-1">{selectedTemplate.description}</p>
              )}
            </div>
            <button
              onClick={() => {
                setSelectedTemplate(null);
                setFormData({});
                setValidationErrors({});
              }}
              className="text-blue-600 hover:text-blue-700"
            >
              Change Template
            </button>
          </div>

          {/* Version Alert */}
          {templateUpdates && templateUpdates[selectedTemplate.id] && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start">
              <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 mr-3" />
              <div className="flex-1">
                <p className="text-sm text-yellow-800">
                  A newer version of this form is available (updated {selectedTemplate.lastUpdated.toLocaleDateString()}).
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="text-sm text-yellow-700 underline hover:text-yellow-800 mt-1"
                >
                  Refresh to Update Template
                </button>
              </div>
            </div>
          )}

          <DynamicFormBuilder
            template={selectedTemplate}
            formData={formData}
            onChange={handleFormChange}
            errors={validationErrors}
          />

          {/* Action Buttons */}
          <div className="mt-8 flex items-center justify-between border-t pt-6">
            <div className="flex items-center space-x-4">
              <button
                onClick={handleSaveDraft}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Draft
              </button>
            </div>
            
            <button
              onClick={handleGenerateDocument}
              disabled={generateDocumentMutation.isPending}
              className="inline-flex items-center px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generateDocumentMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Generate Document
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};