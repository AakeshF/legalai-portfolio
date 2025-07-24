import React, { useState } from 'react';
import { MessageSquare, ThumbsUp, ThumbsDown, Send, X, CheckCircle } from 'lucide-react';
import { api } from '../../utils/api';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../Toast';

interface FeedbackWidgetProps {
  context?: string; // e.g., 'document-analysis', 'chat-response', 'general'
  referenceId?: string; // e.g., document ID, chat message ID
}

export const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ context = 'general', referenceId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'positive' | 'negative' | null>(null);
  const [message, setMessage] = useState('');
  const [category, setCategory] = useState('general');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();

  const categories = [
    { value: 'general', label: 'General Feedback' },
    { value: 'feature-request', label: 'Feature Request' },
    { value: 'bug-report', label: 'Bug Report' },
    { value: 'document-analysis', label: 'Document Analysis' },
    { value: 'ai-accuracy', label: 'AI Accuracy' },
    { value: 'performance', label: 'Performance' },
    { value: 'ui-ux', label: 'User Interface' },
  ];

  const handleSubmit = async () => {
    if (!message.trim()) return;

    setIsSubmitting(true);
    try {
      // In production, this would be an API call
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      const feedbackData = {
        type: feedbackType,
        category,
        message,
        context,
        referenceId,
        userId: user?.id,
        timestamp: new Date().toISOString(),
      };

      console.log('Feedback submitted:', feedbackData);
      
      showSuccess('Thank you for your feedback!');
      setSubmitted(true);
      
      // Reset after delay
      setTimeout(() => {
        setIsOpen(false);
        setSubmitted(false);
        setFeedbackType(null);
        setMessage('');
        setCategory('general');
      }, 2000);
    } catch (error) {
      showError('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="fixed bottom-6 right-6 bg-white rounded-lg shadow-xl p-6 max-w-sm z-50 animate-slide-up">
        <div className="text-center">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <CheckCircle className="h-6 w-6 text-green-600" />
          </div>
          <h4 className="font-semibold text-gray-900 mb-1">Thank You!</h4>
          <p className="text-sm text-gray-600">Your feedback helps us improve</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 p-4 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-110 z-40"
          aria-label="Open feedback"
        >
          <MessageSquare className="h-6 w-6" />
        </button>
      )}

      {/* Feedback Form */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 bg-white rounded-lg shadow-xl w-96 max-h-[600px] z-50 animate-slide-up">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Send Feedback</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-4 space-y-4">
            {/* Quick Feedback */}
            <div>
              <p className="text-sm text-gray-700 mb-3">How's your experience?</p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setFeedbackType('positive')}
                  className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                    feedbackType === 'positive'
                      ? 'bg-green-50 border-green-300 text-green-700'
                      : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <ThumbsUp className="h-4 w-4" />
                  <span>Good</span>
                </button>
                <button
                  onClick={() => setFeedbackType('negative')}
                  className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                    feedbackType === 'negative'
                      ? 'bg-red-50 border-red-300 text-red-700'
                      : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <ThumbsDown className="h-4 w-4" />
                  <span>Could be better</span>
                </button>
              </div>
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {categories.map(cat => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Your feedback
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Tell us what you think..."
              />
              <p className="mt-1 text-xs text-gray-500">
                Your feedback is anonymous and helps us improve
              </p>
            </div>

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={!message.trim() || isSubmitting}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span>Send Feedback</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </>
  );
};

// Inline feedback for specific features
export const InlineFeedback: React.FC<{
  prompt: string;
  onFeedback: (type: 'positive' | 'negative') => void;
}> = ({ prompt, onFeedback }) => {
  const [selected, setSelected] = useState<'positive' | 'negative' | null>(null);

  const handleFeedback = (type: 'positive' | 'negative') => {
    setSelected(type);
    onFeedback(type);
  };

  return (
    <div className="inline-flex items-center space-x-3 p-2 bg-gray-50 rounded-lg">
      <span className="text-sm text-gray-600">{prompt}</span>
      <div className="flex space-x-1">
        <button
          onClick={() => handleFeedback('positive')}
          className={`p-1.5 rounded transition-colors ${
            selected === 'positive'
              ? 'bg-green-100 text-green-600'
              : 'hover:bg-gray-200 text-gray-400'
          }`}
          disabled={selected !== null}
        >
          <ThumbsUp className="h-4 w-4" />
        </button>
        <button
          onClick={() => handleFeedback('negative')}
          className={`p-1.5 rounded transition-colors ${
            selected === 'negative'
              ? 'bg-red-100 text-red-600'
              : 'hover:bg-gray-200 text-gray-400'
          }`}
          disabled={selected !== null}
        >
          <ThumbsDown className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

// Feature request modal
export const FeatureRequestModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const { showSuccess } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    showSuccess('Feature request submitted! We\'ll review it soon.');
    onClose();
    
    // Reset form
    setTitle('');
    setDescription('');
    setPriority('medium');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Request a Feature</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Feature Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Brief title for your feature request"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={5}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Describe the feature and how it would help your legal practice..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="low">Nice to have</option>
              <option value="medium">Would be helpful</option>
              <option value="high">Critical for my practice</option>
            </select>
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Submit Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};