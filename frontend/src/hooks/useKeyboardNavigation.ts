import { useEffect, useCallback } from 'react';

interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  action: () => void;
  description: string;
}

export const useKeyboardNavigation = (shortcuts: KeyboardShortcut[]) => {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isInputActive = 
        activeElement?.tagName === 'INPUT' ||
        activeElement?.tagName === 'TEXTAREA' ||
        activeElement?.getAttribute('contenteditable') === 'true';

      // Don't trigger shortcuts when typing in inputs
      if (isInputActive && !event.ctrlKey && !event.metaKey) {
        return;
      }

      for (const shortcut of shortcuts) {
        const matchesKey = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const matchesCtrl = shortcut.ctrl ? (event.ctrlKey || event.metaKey) : true;
        const matchesAlt = shortcut.alt ? event.altKey : !event.altKey;
        const matchesShift = shortcut.shift ? event.shiftKey : !event.shiftKey;

        if (matchesKey && matchesCtrl && matchesAlt && matchesShift) {
          event.preventDefault();
          shortcut.action();
          break;
        }
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};

// Common shortcuts for the app
export const commonShortcuts: KeyboardShortcut[] = [
  {
    key: 'k',
    ctrl: true,
    action: () => {
      const searchInput = document.querySelector('[data-search-input]') as HTMLInputElement;
      searchInput?.focus();
    },
    description: 'Focus search',
  },
  {
    key: 'n',
    ctrl: true,
    action: () => {
      const uploadButton = document.querySelector('[data-upload-button]') as HTMLElement;
      uploadButton?.click();
    },
    description: 'New document',
  },
  {
    key: '/',
    action: () => {
      const chatInput = document.querySelector('[data-chat-input]') as HTMLInputElement;
      chatInput?.focus();
    },
    description: 'Focus chat',
  },
  {
    key: 'Escape',
    action: () => {
      // Close any open modals
      const closeButtons = document.querySelectorAll('[data-modal-close]');
      closeButtons.forEach((button) => (button as HTMLElement).click());
    },
    description: 'Close modal',
  },
];