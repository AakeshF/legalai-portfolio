import React, { useState, useMemo } from 'react';
import { Search, Book, ArrowUpDown, X } from 'lucide-react';

interface GlossaryTerm {
  term: string;
  definition: string;
  category: string;
  relatedTerms?: string[];
  example?: string;
}

const legalTerms: GlossaryTerm[] = [
  {
    term: 'Affidavit',
    definition: 'A written statement made under oath, sworn to be true before someone legally authorized to administer an oath.',
    category: 'Legal Documents',
    example: 'The witness provided an affidavit detailing what they observed at the scene.',
  },
  {
    term: 'Arbitration',
    definition: 'A form of alternative dispute resolution where parties agree to have their dispute decided by an impartial third party instead of going to court.',
    category: 'Dispute Resolution',
    relatedTerms: ['Mediation', 'Litigation'],
  },
  {
    term: 'Brief',
    definition: 'A written legal document presenting the facts and legal arguments supporting a party\'s position in a case.',
    category: 'Litigation',
    example: 'The attorney submitted a brief arguing for summary judgment.',
  },
  {
    term: 'Consideration',
    definition: 'Something of value exchanged between parties to a contract, making the agreement legally binding.',
    category: 'Contracts',
    relatedTerms: ['Contract', 'Agreement'],
  },
  {
    term: 'Deposition',
    definition: 'Sworn out-of-court testimony given by a witness that is recorded for later use in court or for discovery purposes.',
    category: 'Litigation',
    relatedTerms: ['Discovery', 'Testimony'],
  },
  {
    term: 'Discovery',
    definition: 'The pre-trial phase where parties exchange information and gather evidence relevant to the case.',
    category: 'Litigation',
    relatedTerms: ['Deposition', 'Interrogatories'],
  },
  {
    term: 'Escrow',
    definition: 'A legal arrangement where a third party temporarily holds money or property until a particular condition has been met.',
    category: 'Real Estate',
    example: 'The buyer\'s deposit was held in escrow until the closing date.',
  },
  {
    term: 'Force Majeure',
    definition: 'A contract clause that frees parties from liability when extraordinary circumstances beyond their control prevent fulfillment of obligations.',
    category: 'Contracts',
    example: 'The pandemic triggered the force majeure clause in many commercial leases.',
  },
  {
    term: 'Habeas Corpus',
    definition: 'A legal action through which a person can seek relief from unlawful detention of themselves or another person.',
    category: 'Criminal Law',
  },
  {
    term: 'Indemnification',
    definition: 'A contractual obligation of one party to compensate another party for losses or damages.',
    category: 'Contracts',
    relatedTerms: ['Liability', 'Hold Harmless'],
  },
  {
    term: 'Jurisdiction',
    definition: 'The official power to make legal decisions and judgments; the geographic area or subject matter over which legal authority extends.',
    category: 'Courts',
    example: 'The federal court has jurisdiction over cases involving federal law.',
  },
  {
    term: 'Lien',
    definition: 'A legal right or claim against a property that must be paid off when the property is sold.',
    category: 'Real Estate',
    relatedTerms: ['Mortgage', 'Security Interest'],
  },
  {
    term: 'Mediation',
    definition: 'A form of alternative dispute resolution where a neutral third party helps parties reach a mutually acceptable agreement.',
    category: 'Dispute Resolution',
    relatedTerms: ['Arbitration', 'Negotiation'],
  },
  {
    term: 'Motion',
    definition: 'A formal request made to a court asking for a specific ruling or order.',
    category: 'Litigation',
    example: 'The defense filed a motion to dismiss the case.',
  },
  {
    term: 'Negligence',
    definition: 'Failure to exercise the care that a reasonably prudent person would exercise in similar circumstances.',
    category: 'Torts',
    relatedTerms: ['Liability', 'Duty of Care'],
  },
  {
    term: 'Power of Attorney',
    definition: 'A legal document giving one person the authority to act on behalf of another person in legal or financial matters.',
    category: 'Legal Documents',
    example: 'She granted her son power of attorney to manage her affairs.',
  },
  {
    term: 'Precedent',
    definition: 'A legal principle or rule established in a previous case that is binding or persuasive for future similar cases.',
    category: 'Legal System',
    relatedTerms: ['Stare Decisis', 'Case Law'],
  },
  {
    term: 'Pro Bono',
    definition: 'Legal services provided free of charge for the public good, typically for clients who cannot afford to pay.',
    category: 'Legal Practice',
  },
  {
    term: 'Statute of Limitations',
    definition: 'A law that sets the maximum time after an event within which legal proceedings may be initiated.',
    category: 'Legal System',
    example: 'The statute of limitations for personal injury claims is typically 2-3 years.',
  },
  {
    term: 'Subpoena',
    definition: 'A legal document ordering someone to attend court as a witness or to produce documents.',
    category: 'Litigation',
    relatedTerms: ['Summons', 'Court Order'],
  },
  {
    term: 'Summary Judgment',
    definition: 'A court decision made without a full trial when there are no disputed facts and one party is entitled to judgment as a matter of law.',
    category: 'Litigation',
  },
  {
    term: 'Tort',
    definition: 'A civil wrong that causes harm or loss to another person, resulting in legal liability.',
    category: 'Torts',
    relatedTerms: ['Negligence', 'Liability'],
  },
  {
    term: 'Venue',
    definition: 'The geographic location where a legal case is tried.',
    category: 'Courts',
    relatedTerms: ['Jurisdiction', 'Forum'],
  },
  {
    term: 'Voir Dire',
    definition: 'The process of questioning prospective jurors to determine their suitability for jury service.',
    category: 'Litigation',
  },
];

export const LegalGlossary: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [selectedTerm, setSelectedTerm] = useState<GlossaryTerm | null>(null);

  const categories = useMemo(() => {
    const cats = Array.from(new Set(legalTerms.map(t => t.category))).sort();
    return ['all', ...cats];
  }, []);

  const filteredAndSortedTerms = useMemo(() => {
    let terms = legalTerms;

    // Filter by search term
    if (searchTerm) {
      terms = terms.filter(t => 
        t.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.definition.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      terms = terms.filter(t => t.category === selectedCategory);
    }

    // Sort
    terms.sort((a, b) => {
      const comparison = a.term.localeCompare(b.term);
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return terms;
  }, [searchTerm, selectedCategory, sortOrder]);

  const getRelatedTerms = (term: GlossaryTerm) => {
    if (!term.relatedTerms) return [];
    return term.relatedTerms
      .map(relatedTerm => legalTerms.find(t => t.term === relatedTerm))
      .filter(Boolean) as GlossaryTerm[];
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Book className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Legal Glossary</h1>
            <p className="text-gray-600">Common legal terms and their definitions</p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search terms or definitions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat}
              </option>
            ))}
          </select>
          
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <ArrowUpDown className="h-4 w-4 mr-2" />
            {sortOrder === 'asc' ? 'A-Z' : 'Z-A'}
          </button>
        </div>
      </div>

      {/* Results count */}
      <div className="mb-4 text-sm text-gray-600">
        Found {filteredAndSortedTerms.length} {filteredAndSortedTerms.length === 1 ? 'term' : 'terms'}
      </div>

      {/* Terms Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredAndSortedTerms.map((term) => (
          <div
            key={term.term}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => setSelectedTerm(term)}
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-gray-900">{term.term}</h3>
              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                {term.category}
              </span>
            </div>
            <p className="text-sm text-gray-700 line-clamp-2">
              {term.definition}
            </p>
            {term.relatedTerms && (
              <div className="mt-2 flex items-center space-x-1">
                <span className="text-xs text-gray-500">Related:</span>
                {term.relatedTerms.slice(0, 2).map((related, idx) => (
                  <span key={idx} className="text-xs text-blue-600">
                    {related}{idx < 1 && term.relatedTerms!.length > 1 && ','}
                  </span>
                ))}
                {term.relatedTerms.length > 2 && (
                  <span className="text-xs text-gray-500">+{term.relatedTerms.length - 2}</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Term Detail Modal */}
      {selectedTerm && (
        <TermDetailModal
          term={selectedTerm}
          relatedTerms={getRelatedTerms(selectedTerm)}
          onClose={() => setSelectedTerm(null)}
          onSelectRelated={(term) => {
            setSelectedTerm(term);
          }}
        />
      )}
    </div>
  );
};

// Term Detail Modal
const TermDetailModal: React.FC<{
  term: GlossaryTerm;
  relatedTerms: GlossaryTerm[];
  onClose: () => void;
  onSelectRelated: (term: GlossaryTerm) => void;
}> = ({ term, relatedTerms, onClose, onSelectRelated }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{term.term}</h2>
              <span className="inline-block mt-2 px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full">
                {term.category}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Definition */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-900 mb-2">Definition</h3>
            <p className="text-gray-700 leading-relaxed">{term.definition}</p>
          </div>

          {/* Example */}
          {term.example && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-2">Example</h3>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-gray-700 italic">"{term.example}"</p>
              </div>
            </div>
          )}

          {/* Related Terms */}
          {relatedTerms.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Related Terms</h3>
              <div className="space-y-2">
                {relatedTerms.map((related) => (
                  <button
                    key={related.term}
                    onClick={() => onSelectRelated(related)}
                    className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="font-medium text-blue-600">{related.term}</div>
                    <div className="text-sm text-gray-600 mt-1 line-clamp-2">
                      {related.definition}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};