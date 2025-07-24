import React, { useState } from 'react';
import { FileText, Download, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';
import { useToast } from '../Toast';

interface SampleDocument {
  id: string;
  name: string;
  description: string;
  type: string;
  size: string;
  category: 'contracts' | 'litigation' | 'corporate' | 'real-estate' | 'ip';
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  tags: string[];
}

const sampleDocuments: SampleDocument[] = [
  {
    id: 'sample-1',
    name: 'Standard Service Agreement',
    description: 'A typical service agreement between a company and a contractor with standard terms and conditions.',
    type: 'Contract',
    size: '245 KB',
    category: 'contracts',
    difficulty: 'beginner',
    tags: ['service agreement', 'contractor', 'terms'],
  },
  {
    id: 'sample-2',
    name: 'Commercial Lease Agreement',
    description: 'Commercial property lease with detailed provisions for rent, maintenance, and tenant improvements.',
    type: 'Real Estate',
    size: '412 KB',
    category: 'real-estate',
    difficulty: 'intermediate',
    tags: ['lease', 'commercial', 'property'],
  },
  {
    id: 'sample-3',
    name: 'Software License Agreement',
    description: 'Enterprise software licensing agreement with usage restrictions and support terms.',
    type: 'Technology',
    size: '328 KB',
    category: 'ip',
    difficulty: 'advanced',
    tags: ['software', 'license', 'SaaS'],
  },
  {
    id: 'sample-4',
    name: 'Employment Contract',
    description: 'Executive employment agreement with compensation, benefits, and termination clauses.',
    type: 'Employment',
    size: '189 KB',
    category: 'corporate',
    difficulty: 'intermediate',
    tags: ['employment', 'executive', 'compensation'],
  },
  {
    id: 'sample-5',
    name: 'Non-Disclosure Agreement',
    description: 'Mutual NDA for business negotiations with standard confidentiality provisions.',
    type: 'Corporate',
    size: '98 KB',
    category: 'corporate',
    difficulty: 'beginner',
    tags: ['NDA', 'confidentiality', 'mutual'],
  },
  {
    id: 'sample-6',
    name: 'Patent License Agreement',
    description: 'Technology patent licensing with royalty structures and territorial restrictions.',
    type: 'Intellectual Property',
    size: '567 KB',
    category: 'ip',
    difficulty: 'advanced',
    tags: ['patent', 'license', 'royalties'],
  },
];

interface SampleDocumentsProps {
  onSelectDocument: (doc: SampleDocument) => void;
}

export const SampleDocuments: React.FC<SampleDocumentsProps> = ({ onSelectDocument }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const { showInfo } = useToast();

  const categories = [
    { id: 'all', name: 'All Documents', count: sampleDocuments.length },
    { id: 'contracts', name: 'Contracts', count: sampleDocuments.filter(d => d.category === 'contracts').length },
    { id: 'real-estate', name: 'Real Estate', count: sampleDocuments.filter(d => d.category === 'real-estate').length },
    { id: 'corporate', name: 'Corporate', count: sampleDocuments.filter(d => d.category === 'corporate').length },
    { id: 'ip', name: 'Intellectual Property', count: sampleDocuments.filter(d => d.category === 'ip').length },
  ];

  const filteredDocuments = selectedCategory === 'all' 
    ? sampleDocuments 
    : sampleDocuments.filter(doc => doc.category === selectedCategory);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner':
        return 'bg-green-100 text-green-700';
      case 'intermediate':
        return 'bg-yellow-100 text-yellow-700';
      case 'advanced':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const handleDocumentSelect = (doc: SampleDocument) => {
    setShowDisclaimer(false);
    showInfo(`Loading sample: ${doc.name}`);
    onSelectDocument(doc);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Sample Legal Documents</h2>
        <p className="text-gray-600">
          Practice with these sample documents to explore AI analysis capabilities
        </p>
      </div>

      {/* Disclaimer */}
      {showDisclaimer && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-amber-900 mb-1">
                Educational Purpose Only
              </h4>
              <p className="text-sm text-amber-800">
                These sample documents are for demonstration purposes only and should not be used for actual legal matters. 
                Always consult with a qualified attorney for legal advice.
              </p>
            </div>
            <button
              onClick={() => setShowDisclaimer(false)}
              className="ml-3 text-amber-600 hover:text-amber-700"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Category Filter */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-2">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                selectedCategory === category.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {category.name}
              <span className="ml-2 text-sm opacity-75">({category.count})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Document Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDocuments.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-lg border border-gray-200 p-5 hover:shadow-lg transition-all cursor-pointer group"
            onClick={() => handleDocumentSelect(doc)}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getDifficultyColor(doc.difficulty)}`}>
                {doc.difficulty}
              </span>
            </div>

            <h3 className="font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
              {doc.name}
            </h3>
            
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">
              {doc.description}
            </p>

            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>{doc.type} • {doc.size}</span>
              <Download className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>

            {/* Tags */}
            <div className="mt-3 flex flex-wrap gap-1">
              {doc.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Tips */}
      <div className="mt-8 p-6 bg-blue-50 rounded-lg border border-blue-200">
        <div className="flex items-start">
          <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-blue-900 mb-2">Tips for Testing</h4>
            <ul className="space-y-1 text-sm text-blue-800">
              <li>• Start with beginner-level documents to understand basic analysis</li>
              <li>• Try asking the AI to extract key terms, dates, and parties</li>
              <li>• Test risk identification and clause comparison features</li>
              <li>• Experiment with different question types for comprehensive analysis</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

// Sample document viewer for demo purposes
export const SampleDocumentContent: React.FC<{ document: SampleDocument }> = ({ document }) => {
  return (
    <div className="p-6 bg-gray-50 rounded-lg">
      <div className="mb-4 p-3 bg-amber-100 border border-amber-300 rounded-lg">
        <p className="text-sm text-amber-800 font-medium">
          This is a sample document for demonstration purposes only
        </p>
      </div>
      
      <div className="prose max-w-none">
        <h1 className="text-2xl font-bold mb-4">{document.name}</h1>
        
        {/* Sample content based on document type */}
        {document.id === 'sample-1' && (
          <div className="space-y-4">
            <section>
              <h2 className="text-xl font-semibold mb-2">SERVICE AGREEMENT</h2>
              <p>This Service Agreement ("Agreement") is entered into as of [DATE] by and between:</p>
              <p><strong>Client:</strong> [CLIENT NAME] ("Client")</p>
              <p><strong>Service Provider:</strong> [PROVIDER NAME] ("Provider")</p>
            </section>
            
            <section>
              <h3 className="text-lg font-semibold mb-2">1. Services</h3>
              <p>Provider agrees to perform the following services:</p>
              <ul className="list-disc pl-6">
                <li>Professional consulting services</li>
                <li>Project management and coordination</li>
                <li>Deliverables as specified in Schedule A</li>
              </ul>
            </section>
            
            <section>
              <h3 className="text-lg font-semibold mb-2">2. Compensation</h3>
              <p>Client shall pay Provider:</p>
              <ul className="list-disc pl-6">
                <li>Hourly rate: $[RATE] per hour</li>
                <li>Monthly retainer: $[AMOUNT]</li>
                <li>Expenses: Reimbursable with prior approval</li>
              </ul>
            </section>
            
            <section>
              <h3 className="text-lg font-semibold mb-2">3. Term and Termination</h3>
              <p>This Agreement shall commence on [START DATE] and continue until [END DATE], unless earlier terminated.</p>
              <p>Either party may terminate with 30 days written notice.</p>
            </section>
          </div>
        )}
        
        {/* Add more sample content for other document types */}
      </div>
    </div>
  );
};