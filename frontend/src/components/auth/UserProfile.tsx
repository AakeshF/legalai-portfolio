import React, { useState } from 'react';
import { User, Mail, Phone, Camera, Save, X } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Toast } from '../SimpleToast';
import { ConsentManager } from '../consent/ConsentManager';
import { UserAIPreferences } from '../ai-config/UserAIPreferences';

export const UserProfile: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: '',
    bio: ''
  });

  const handleSave = async () => {
    try {
      await updateUser({ name: formData.name });
      setToastMessage('Profile updated successfully');
      setShowToast(true);
      setIsEditing(false);
    } catch (error) {
      setToastMessage('Failed to update profile');
      setShowToast(true);
    }
  };

  const handleCancel = () => {
    setFormData({
      name: user?.name || '',
      email: user?.email || '',
      phone: '',
      bio: ''
    });
    setIsEditing(false);
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
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Profile Settings</h2>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            Edit Profile
          </button>
        ) : (
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCancel}
              className="p-2 text-gray-400 hover:text-gray-500"
            >
              <X className="h-5 w-5" />
            </button>
            <button
              onClick={handleSave}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center mb-8">
        <div className="relative">
          <div className="h-24 w-24 rounded-full bg-gray-200 flex items-center justify-center">
            {user?.avatarUrl ? (
              <img
                src={user.avatarUrl}
                alt={user.name}
                className="h-24 w-24 rounded-full object-cover"
              />
            ) : (
              <User className="h-12 w-12 text-gray-400" />
            )}
          </div>
          {isEditing && (
            <button className="absolute bottom-0 right-0 bg-blue-600 rounded-full p-2 text-white hover:bg-blue-700">
              <Camera className="h-4 w-4" />
            </button>
          )}
        </div>
        <div className="ml-6">
          <h3 className="text-xl font-medium text-gray-900">{user?.name}</h3>
          <p className="text-sm text-gray-500">{getRoleDisplay(user?.role || '')}</p>
        </div>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Full Name
          </label>
          {isEditing ? (
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          ) : (
            <p className="text-gray-900">{user?.name}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Email Address
          </label>
          <div className="flex items-center">
            <Mail className="h-5 w-5 text-gray-400 mr-2" />
            <p className="text-gray-900">{user?.email}</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Phone Number
          </label>
          {isEditing ? (
            <div className="flex items-center">
              <Phone className="h-5 w-5 text-gray-400 mr-2" />
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="[PHONE-NUMBER]"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          ) : (
            <div className="flex items-center">
              <Phone className="h-5 w-5 text-gray-400 mr-2" />
              <p className="text-gray-900">{formData.phone || 'Not provided'}</p>
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Bio
          </label>
          {isEditing ? (
            <textarea
              value={formData.bio}
              onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
              rows={4}
              placeholder="Tell us about your legal expertise..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          ) : (
            <p className="text-gray-900">{formData.bio || 'No bio provided'}</p>
          )}
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Security</h3>
        <button className="text-blue-600 hover:text-blue-500 text-sm font-medium">
          Change Password
        </button>
      </div>

      {showToast && (
        <Toast
          message={toastMessage}
          type={toastMessage.includes('success') ? 'success' : 'error'}
          onClose={() => setShowToast(false)}
        />
      )}
      </div>

      <UserAIPreferences />
      
      <ConsentManager />
    </div>
  );
};