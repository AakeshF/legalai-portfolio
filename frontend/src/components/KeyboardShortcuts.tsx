import React, { useState, useEffect } from 'react';
import { Command, X } from 'lucide-react';

interface Shortcut {
  keys: string[];
  description: string;
}

const shortcuts: Shortcut[] = [
  { keys: ['⌘', 'K'], description: 'Quick search' },
  { keys: ['⌘', 'U'], description: 'Upload document' },
  { keys: ['⌘', 'D'], description: 'View documents' },
  { keys: ['⌘', '/'], description: 'Start chat' },
  { keys: ['Del'], description: 'Delete document (when viewing)' },
  { keys: ['Esc'], description: 'Close modal' },
  { keys: ['?'], description: 'Show keyboard shortcuts' }
];

interface KeyboardShortcutsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcuts: React.FC<KeyboardShortcutsProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full animate-slide-up">
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center space-x-2">
            <Command className="w-5 h-5 text-slate-700" />
            <h2 className="text-lg font-semibold text-slate-900">Keyboard Shortcuts</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 space-y-3">
          {shortcuts.map((shortcut, index) => (
            <div 
              key={index} 
              className="flex items-center justify-between py-2 animate-fade-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <span className="text-sm text-slate-700">{shortcut.description}</span>
              <div className="flex items-center space-x-1">
                {shortcut.keys.map((key, idx) => (
                  <React.Fragment key={idx}>
                    {idx > 0 && <span className="text-slate-400 text-xs">+</span>}
                    <kbd className="px-2 py-1 bg-slate-100 border border-slate-200 rounded text-xs font-mono text-slate-700">
                      {key}
                    </kbd>
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const useKeyboardShortcuts = (actions: {
  onSearch?: () => void;
  onUpload?: () => void;
  onDocuments?: () => void;
  onChat?: () => void;
  onHelp?: () => void;
}) => {
  const [showShortcuts, setShowShortcuts] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for meta key (Cmd on Mac, Ctrl on Windows/Linux)
      const metaKey = e.metaKey || e.ctrlKey;

      // Show shortcuts help
      if (e.key === '?' && !e.shiftKey && !metaKey) {
        e.preventDefault();
        setShowShortcuts(true);
        return;
      }

      // Other shortcuts require meta key
      if (!metaKey) return;

      switch (e.key.toLowerCase()) {
        case 'k':
          e.preventDefault();
          if (actions.onSearch) actions.onSearch();
          break;
        case 'u':
          e.preventDefault();
          if (actions.onUpload) actions.onUpload();
          break;
        case 'd':
          e.preventDefault();
          if (actions.onDocuments) actions.onDocuments();
          break;
        case '/':
          e.preventDefault();
          if (actions.onChat) actions.onChat();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [actions]);

  return {
    showShortcuts,
    setShowShortcuts
  };
};