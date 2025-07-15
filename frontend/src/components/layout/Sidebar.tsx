/**
 * Sidebar Component
 * 侧边栏导航组件
 */

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  HomeIcon,
  InboxIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  CogIcon,
  UserIcon,
  ChartBarIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { ROUTES } from '../../config';
import clsx from 'clsx';

interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
}

const navigation: NavigationItem[] = [
  { name: 'Dashboard', href: ROUTES.DASHBOARD, icon: HomeIcon },
  { name: 'Emails', href: ROUTES.EMAILS, icon: InboxIcon, badge: '12' },
  { name: 'Daily Report', href: ROUTES.DAILY_REPORT, icon: DocumentTextIcon },
  { name: 'Chat', href: ROUTES.CHAT, icon: ChatBubbleLeftRightIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Tasks', href: '/tasks', icon: ClockIcon },
];

const secondaryNavigation: NavigationItem[] = [
  { name: 'Settings', href: ROUTES.SETTINGS, icon: CogIcon },
  { name: 'Preferences', href: ROUTES.PREFERENCES, icon: UserIcon },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();

  const isActive = (href: string) => {
    return location.pathname === href || 
           (href !== ROUTES.DASHBOARD && location.pathname.startsWith(href));
  };

  return (
    <div className="fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-200 overflow-y-auto">
      <nav className="px-3 py-4">
        {/* Main navigation */}
        <div className="space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive: navIsActive }) =>
                clsx(
                  'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors duration-200',
                  navIsActive || isActive(item.href)
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <item.icon
                className={clsx(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive(item.href)
                    ? 'text-blue-500'
                    : 'text-gray-400 group-hover:text-gray-500'
                )}
              />
              <span className="flex-1">{item.name}</span>
              {item.badge && (
                <span className="ml-3 inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200 my-6" />

        {/* Secondary navigation */}
        <div className="space-y-1">
          <h3 className="px-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Account
          </h3>
          <div className="mt-2 space-y-1">
            {secondaryNavigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive: navIsActive }) =>
                  clsx(
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors duration-200',
                    navIsActive || isActive(item.href)
                      ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )
                }
              >
                <item.icon
                  className={clsx(
                    'mr-3 h-5 w-5 flex-shrink-0',
                    isActive(item.href)
                      ? 'text-blue-500'
                      : 'text-gray-400 group-hover:text-gray-500'
                  )}
                />
                <span className="flex-1">{item.name}</span>
                {item.badge && (
                  <span className="ml-3 inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        </div>

        {/* Quick actions */}
        <div className="mt-8 px-2">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ChatBubbleLeftRightIcon className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  Quick Chat
                </h3>
                <p className="text-xs text-blue-600">
                  Ask your AI assistant
                </p>
              </div>
            </div>
            <div className="mt-3">
              <button className="w-full bg-blue-600 text-white text-sm font-medium py-2 px-3 rounded-md hover:bg-blue-700 transition-colors duration-200">
                Start Chat
              </button>
            </div>
          </div>
        </div>

        {/* Status indicator */}
        <div className="mt-6 px-2">
          <div className="flex items-center text-sm text-gray-500">
            <div className="w-2 h-2 bg-green-400 rounded-full mr-2" />
            <span>System Online</span>
          </div>
        </div>
      </nav>
    </div>
  );
};