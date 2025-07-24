import React, { useState } from 'react';
import { 
  HelpCircle, Book, Video, MessageCircle, FileText, 
  Shield, Zap, Search, ChevronRight, ExternalLink,
  Download, Mail, Phone
} from 'lucide-react';

interface HelpArticle {
  id: string;
  title: string;
  category: string;
  content: string;
  readTime: string;
  helpful?: number;
  tags: string[];
}

interface VideoTutorial {
  id: string;
  title: string;
  duration: string;
  thumbnail: string;
  description: string;
  level: 'beginner' | 'intermediate' | 'advanced';
}

const helpArticles: HelpArticle[] = [
  {
    id: 'getting-started',
    title: 'Getting Started with Legal AI Assistant',
    category: 'Basics',
    readTime: '5 min',
    tags: ['onboarding', 'basics', 'setup'],
    content: `
      Welcome to Legal AI Assistant! This guide will help you get started with analyzing legal documents using AI.
      
      ## First Steps
      1. Upload your first document (PDF, DOCX, or TXT)
      2. Wait for AI processing to complete
      3. Start asking questions about your document
      
      ## Best Practices
      - Start with clear, specific questions
      - Review AI responses carefully
      - Always verify important findings with legal counsel
    `
  },
  {
    id: 'document-analysis',
    title: 'How to Analyze Legal Documents',
    category: 'Features',
    readTime: '8 min',
    tags: ['analysis', 'documents', 'ai'],
    content: `
      Learn how to effectively analyze legal documents using our AI assistant.
      
      ## Key Analysis Features
      - Contract term extraction
      - Risk identification
      - Compliance checking
      - Key date and deadline tracking
      
      ## Tips for Better Results
      - Upload complete documents
      - Ask specific questions
      - Use legal terminology when appropriate
    `
  },
  {
    id: 'security-privacy',
    title: 'Security and Privacy Guide',
    category: 'Security',
    readTime: '6 min',
    tags: ['security', 'privacy', 'compliance'],
    content: `
      Understanding how we protect your legal documents and data.
      
      ## Security Measures
      - End-to-end encryption
      - SOC 2 Type II compliance
      - HIPAA compliant infrastructure
      - Regular security audits
      
      ## Your Privacy
      - Documents are never shared
      - AI doesn't train on your data
      - Complete data deletion available
    `
  },
];

const videoTutorials: VideoTutorial[] = [
  {
    id: 'intro-video',
    title: 'Introduction to Legal AI Assistant',
    duration: '3:45',
    thumbnail: '/tutorials/intro-thumb.jpg',
    description: 'Get started with the basics of document upload and analysis',
    level: 'beginner',
  },
  {
    id: 'contract-review',
    title: 'Automated Contract Review Process',
    duration: '7:20',
    thumbnail: '/tutorials/contract-thumb.jpg',
    description: 'Learn how to review contracts efficiently using AI insights',
    level: 'intermediate',
  },
  {
    id: 'advanced-queries',
    title: 'Advanced Query Techniques',
    duration: '5:15',
    thumbnail: '/tutorials/advanced-thumb.jpg',
    description: 'Master complex document analysis with advanced prompting',
    level: 'advanced',
  },
];

export const HelpCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'articles' | 'videos' | 'contact'>('articles');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<HelpArticle | null>(null);

  const filteredArticles = helpArticles.filter(article => 
    article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    article.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const categories = Array.from(new Set(helpArticles.map(a => a.category)));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <HelpCircle className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Help Center</h1>
                <p className="text-gray-600">Find answers and learn how to use Legal AI</p>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="mt-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search help articles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Tabs */}
          <div className="mt-6 flex space-x-1 bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('articles')}
              className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'articles'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Book className="h-4 w-4 mr-2" />
              Articles
            </button>
            <button
              onClick={() => setActiveTab('videos')}
              className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'videos'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Video className="h-4 w-4 mr-2" />
              Video Tutorials
            </button>
            <button
              onClick={() => setActiveTab('contact')}
              className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'contact'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <MessageCircle className="h-4 w-4 mr-2" />
              Contact Support
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'articles' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Categories Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Categories</h3>
                <nav className="space-y-2">
                  {categories.map(category => (
                    <button
                      key={category}
                      className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <span className="text-gray-700">{category}</span>
                      <span className="float-right text-gray-400">
                        {helpArticles.filter(a => a.category === category).length}
                      </span>
                    </button>
                  ))}
                </nav>

                {/* Quick Links */}
                <div className="mt-8">
                  <h3 className="font-semibold text-gray-900 mb-4">Quick Links</h3>
                  <div className="space-y-3">
                    <a href="#" className="flex items-center text-blue-600 hover:text-blue-700">
                      <Download className="h-4 w-4 mr-2" />
                      Download User Guide
                    </a>
                    <a href="#" className="flex items-center text-blue-600 hover:text-blue-700">
                      <FileText className="h-4 w-4 mr-2" />
                      API Documentation
                    </a>
                    <a href="#" className="flex items-center text-blue-600 hover:text-blue-700">
                      <Shield className="h-4 w-4 mr-2" />
                      Security Whitepaper
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Articles List */}
            <div className="lg:col-span-2">
              {selectedArticle ? (
                <ArticleView 
                  article={selectedArticle} 
                  onBack={() => setSelectedArticle(null)} 
                />
              ) : (
                <div className="space-y-4">
                  {filteredArticles.map(article => (
                    <article
                      key={article.id}
                      onClick={() => setSelectedArticle(article)}
                      className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow cursor-pointer"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            {article.title}
                          </h3>
                          <p className="text-gray-600 mb-3">
                            {article.content.slice(0, 150)}...
                          </p>
                          <div className="flex items-center space-x-4 text-sm text-gray-500">
                            <span>{article.category}</span>
                            <span>•</span>
                            <span>{article.readTime} read</span>
                          </div>
                        </div>
                        <ChevronRight className="h-5 w-5 text-gray-400 flex-shrink-0 ml-4" />
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'videos' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {videoTutorials.map(video => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        )}

        {activeTab === 'contact' && (
          <ContactSupport />
        )}
      </div>
    </div>
  );
};

// Article View Component
const ArticleView: React.FC<{ article: HelpArticle; onBack: () => void }> = ({ article, onBack }) => {
  const [helpful, setHelpful] = useState<boolean | null>(null);

  return (
    <div className="bg-white rounded-lg shadow-sm p-8">
      <button
        onClick={onBack}
        className="flex items-center text-blue-600 hover:text-blue-700 mb-6"
      >
        <ChevronRight className="h-4 w-4 mr-1 rotate-180" />
        Back to articles
      </button>

      <article className="prose max-w-none">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">{article.title}</h1>
        
        <div className="flex items-center space-x-4 text-sm text-gray-500 mb-8">
          <span>{article.category}</span>
          <span>•</span>
          <span>{article.readTime} read</span>
        </div>

        <div className="whitespace-pre-wrap text-gray-700">
          {article.content}
        </div>

        <div className="mt-8 pt-8 border-t border-gray-200">
          <p className="text-gray-700 mb-4">Was this article helpful?</p>
          <div className="flex space-x-3">
            <button
              onClick={() => setHelpful(true)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                helpful === true
                  ? 'bg-green-50 border-green-300 text-green-700'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              Yes, it helped
            </button>
            <button
              onClick={() => setHelpful(false)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                helpful === false
                  ? 'bg-red-50 border-red-300 text-red-700'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              No, I need more help
            </button>
          </div>
        </div>
      </article>
    </div>
  );
};

// Video Card Component
const VideoCard: React.FC<{ video: VideoTutorial }> = ({ video }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow cursor-pointer">
      <div className="aspect-video bg-gray-200 relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="p-4 bg-black bg-opacity-50 rounded-full">
            <Video className="h-8 w-8 text-white" />
          </div>
        </div>
        <div className="absolute bottom-2 right-2 px-2 py-1 bg-black bg-opacity-75 text-white text-xs rounded">
          {video.duration}
        </div>
      </div>
      
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-2">{video.title}</h3>
        <p className="text-sm text-gray-600 mb-3">{video.description}</p>
        
        <div className="flex items-center justify-between">
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
            video.level === 'beginner' ? 'bg-green-100 text-green-700' :
            video.level === 'intermediate' ? 'bg-yellow-100 text-yellow-700' :
            'bg-red-100 text-red-700'
          }`}>
            {video.level}
          </span>
          
          <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            Watch Now →
          </button>
        </div>
      </div>
    </div>
  );
};

// Contact Support Component
const ContactSupport: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Contact Support</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="text-center p-6 bg-gray-50 rounded-lg">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Mail className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Email Support</h3>
            <p className="text-sm text-gray-600 mb-3">Get help via email</p>
            <a href={`mailto:${import.meta.env.VITE_SUPPORT_EMAIL}`} className="text-blue-600 hover:text-blue-700">
              {import.meta.env.VITE_SUPPORT_EMAIL || '[SUPPORT-EMAIL]'}
            </a>
          </div>
          
          <div className="text-center p-6 bg-gray-50 rounded-lg">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Phone className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Phone Support</h3>
            <p className="text-sm text-gray-600 mb-3">Mon-Fri, 9am-5pm EST</p>
            <a href={`tel:${import.meta.env.VITE_SUPPORT_PHONE}`} className="text-blue-600 hover:text-blue-700">
              {import.meta.env.VITE_SUPPORT_PHONE || '[SUPPORT-PHONE]'}
            </a>
          </div>
          
          <div className="text-center p-6 bg-gray-50 rounded-lg">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <MessageCircle className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Live Chat</h3>
            <p className="text-sm text-gray-600 mb-3">Chat with our team</p>
            <button className="text-blue-600 hover:text-blue-700">
              Start Chat
            </button>
          </div>
        </div>

        {/* Contact Form */}
        <form className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Your name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="[YOUR-EMAIL]"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Subject
            </label>
            <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
              <option>Technical Support</option>
              <option>Billing Question</option>
              <option>Feature Request</option>
              <option>Other</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Message
            </label>
            <textarea
              rows={5}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Describe your issue or question..."
            />
          </div>
          
          <button
            type="submit"
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Send Message
          </button>
        </form>
      </div>
    </div>
  );
};