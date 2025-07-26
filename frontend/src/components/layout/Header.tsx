/**
 * Header Component
 * 应用顶部导航栏
 */

import React from 'react';
import { Menu, Transition } from '@headlessui/react';
import { 
  ChevronDownIcon, 
  UserIcon,
  CogIcon,
  ArrowRightOnRectangleIcon 
} from '@heroicons/react/24/outline';
import useAuthStore from '../../stores/authStore';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../config';
import clsx from 'clsx';

export const Header: React.FC = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate(ROUTES.LOGIN);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white shadow-sm border-b border-gray-200">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and title */}
          <div className="flex items-center">
            <div className="flex-shrink-0 flex items-center">
              <button 
                onClick={() => navigate(ROUTES.DAILY_REPORT)}
                className="flex items-center space-x-2 hover:opacity-80 transition-opacity focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg p-1"
                aria-label="返回主页"
              >
                <img 
                  src="/logo.svg" 
                  alt="MailAssistant Logo" 
                  className="h-8 w-8 object-contain"
                />
                <h1 className="text-xl font-semibold text-gray-900">
                  MailAssistant
                </h1>
              </button>
            </div>
          </div>

          {/* Right section */}
          <div className="flex items-center space-x-4">
            {/* User menu */}
            <Menu as="div" className="relative">
              <div>
                <Menu.Button className="flex items-center space-x-3 p-2 text-sm text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="h-8 w-8 bg-gray-300 rounded-full flex items-center justify-center">
                      {user?.email ? (
                        <span className="text-sm font-medium text-gray-700">
                          {user.email.charAt(0).toUpperCase()}
                        </span>
                      ) : (
                        <UserIcon className="h-5 w-5 text-gray-500" />
                      )}
                    </div>
                    <span className="hidden md:block text-sm font-medium text-gray-700">
                      {user?.email}
                    </span>
                  </div>
                  <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                </Menu.Button>
              </div>

              <Transition
                as={React.Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={() => navigate(ROUTES.SETTINGS)}
                        className={clsx(
                          active ? 'bg-gray-100' : '',
                          'flex items-center w-full px-4 py-2 text-sm text-gray-700'
                        )}
                      >
                        <CogIcon className="h-4 w-4 mr-3" />
                        Settings
                      </button>
                    )}
                  </Menu.Item>
                  
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={() => navigate(ROUTES.PREFERENCES)}
                        className={clsx(
                          active ? 'bg-gray-100' : '',
                          'flex items-center w-full px-4 py-2 text-sm text-gray-700'
                        )}
                      >
                        <UserIcon className="h-4 w-4 mr-3" />
                        Preferences
                      </button>
                    )}
                  </Menu.Item>
                  
                  <div className="border-t border-gray-100 my-1" />
                  
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={handleLogout}
                        className={clsx(
                          active ? 'bg-gray-100' : '',
                          'flex items-center w-full px-4 py-2 text-sm text-gray-700'
                        )}
                      >
                        <ArrowRightOnRectangleIcon className="h-4 w-4 mr-3" />
                        Sign out
                      </button>
                    )}
                  </Menu.Item>
                </Menu.Items>
              </Transition>
            </Menu>
          </div>
        </div>
      </div>
    </header>
  );
};