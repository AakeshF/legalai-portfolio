import React, { useState, useRef, useEffect } from 'react';
import { Menu, Scale, Sparkles, User, Settings, Users, LogOut, Building2, ChevronDown, Shield, Eye, EyeOff } from 'lucide-react';
import { InlinePollingIndicator } from './PollingIndicator';
// import { useAuth } from '../contexts/AuthContext';
// import { useNavigate } from 'react-router-dom';
// import { SecurityStatusIndicator } from './security/SecurityStatusIndicator';
import { useSimpleMode } from '../contexts/SimpleModeContext';

interface HeaderProps {
  onMenuClick: () => void;
  currentView: 'chat' | 'documents' | 'upload';
  isPolling?: boolean;
  hasProcessingDocuments?: boolean;
}

const viewTitles = {
  chat: 'Legal Intelligence Command',
  documents: 'Arsenal Management', 
  upload: 'Feed the Beast'
};

const Header: React.FC<HeaderProps> = ({ onMenuClick, currentView, isPolling = false, hasProcessingDocuments = false }) => {
  // const { user, organization, logout } = useAuth();
  // const navigate = useNavigate();
  const user = null;
  const organization = null;
  const logout = async () => {};
  const { isSimpleMode, toggleSimpleMode, getSimpleText } = useSimpleMode();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserMenu]);

  const getUserInitials = () => {
    if (!user?.full_name) return 'U';
    return user.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase();
  };

  const getRoleDisplay = (role: string) => {
    const roleMap = {
      attorney: 'Attorney',
      admin: 'Administrator',
      paralegal: 'Paralegal'
    };
    return roleMap[role as keyof typeof roleMap] || role;
  };

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm h-16 flex items-center justify-between px-4 lg:px-6">
      {/* Left Section */}
      <div className="flex items-center space-x-4">
        {/* Mobile Menu Button */}
        <button
          onClick={onMenuClick}
          className="p-2 rounded-lg hover:bg-slate-100 lg:hidden"
        >
          <Menu className="w-5 h-5 text-slate-600" />
        </button>

        {/* Logo & Title */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-gradient-to-br from-brand-blue-600 to-brand-blue-700 rounded-lg shadow-sm">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div className="hidden sm:block">
              <h1 className="font-serif text-xl font-bold text-brand-gray-900">Legal AI</h1>
              <p className="text-xs text-brand-gray-600 -mt-1">{organization?.name || 'On-Premise Legal Assistant'}</p>
            </div>
          </div>
        </div>

        {/* Current View Title */}
        <div className="hidden md:block">
          <div className="h-6 w-px bg-slate-200 mx-4"></div>
          <h2 className="text-lg font-semibold text-slate-700">
            {viewTitles[currentView]}
          </h2>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center space-x-3">
        {/* Polling Status */}
        {hasProcessingDocuments && (
          <div className="hidden sm:flex items-center">
            <InlinePollingIndicator isPolling={isPolling} />
          </div>
        )}
        
        {/* Security Status */}
        {/* <SecurityStatusIndicator variant="mini" /> */}
        
        {/* Simple Mode Toggle */}
        <button
          onClick={toggleSimpleMode}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border transition-all ${
            isSimpleMode 
              ? 'bg-blue-50 border-blue-200 text-blue-700' 
              : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
          }`}
          aria-label={isSimpleMode ? 'Turn off Simple Mode' : 'Turn on Simple Mode'}
          title={isSimpleMode ? 'Simple Mode is ON - Click to turn off' : 'Simple Mode is OFF - Click to turn on'}
        >
          {isSimpleMode ? (
            <>
              <Eye className="w-4 h-4" />
              <span className="text-sm font-medium hidden sm:inline">Simple Mode</span>
            </>
          ) : (
            <>
              <EyeOff className="w-4 h-4" />
              <span className="text-sm font-medium hidden sm:inline">Standard</span>
            </>
          )}
        </button>
        
        {/* AI Status */}
        <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 bg-green-50 rounded-full border border-green-200 animate-pulse-ring">
          <Sparkles className="w-4 h-4 text-green-600 animate-pulse" />
          <span className="text-sm font-medium text-green-700">{getSimpleText('Beast Mode Active')}</span>
        </div>

        {/* User Menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-white">{getUserInitials()}</span>
            </div>
            <div className="hidden lg:block text-left">
              <p className="text-sm font-medium text-slate-900">{user?.full_name || 'User'}</p>
              <p className="text-xs text-slate-500">{getRoleDisplay(user?.role || '')}</p>
            </div>
            <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown Menu */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
              <div className="px-4 py-3 border-b border-gray-200">
                <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>

              <button
                onClick={() => {
                  // navigate('/profile');
                  setShowUserMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
              >
                <User className="w-4 h-4 mr-3" />
                {getSimpleText('Command Center')}
              </button>

              <button
                onClick={() => {
                  // navigate('/organization');
                  setShowUserMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
              >
                <Building2 className="w-4 h-4 mr-3" />
                {getSimpleText('Empire Control')}
              </button>

              {user?.role === 'admin' && (
                <button
                  onClick={() => {
                    // navigate('/organization/users');
                    setShowUserMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
                >
                  <Users className="w-4 h-4 mr-3" />
                  {getSimpleText('Deploy Forces')}
                </button>
              )}

              <button
                onClick={() => {
                  // navigate('/security');
                  setShowUserMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
              >
                <Shield className="w-4 h-4 mr-3" />
                {getSimpleText('Fortress Mode')}
              </button>

              <button
                onClick={() => {
                  // navigate('/settings');
                  setShowUserMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
              >
                <Settings className="w-4 h-4 mr-3" />
                {getSimpleText('Fine-Tune')}
              </button>

              <div className="border-t border-gray-200 mt-1">
                <button
                  onClick={() => {
                    logout();
                    setShowUserMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
                >
                  <LogOut className="w-4 h-4 mr-3" />
                  {getSimpleText('Eject')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
