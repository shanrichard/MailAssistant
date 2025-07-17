/**
 * Sidebar Component
 * 侧边栏导航组件 - 简化版，只包含核心功能
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  CogIcon
} from '@heroicons/react/24/outline';
import { ROUTES } from '../../config';
import clsx from 'clsx';

interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigation: NavigationItem[] = [
  { name: '日报', href: ROUTES.DAILY_REPORT, icon: DocumentTextIcon },
  { name: '对话', href: ROUTES.CHAT, icon: ChatBubbleLeftRightIcon },
  { name: '设置', href: ROUTES.SETTINGS, icon: CogIcon },
];

export const Sidebar: React.FC = () => {
  return (
    <div className="fixed left-0 top-16 bottom-0 w-48 bg-white border-r border-gray-200">
      <nav className="px-3 py-6">
        <div className="space-y-2">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                clsx(
                  'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <item.icon
                className={clsx(
                  'mr-3 h-5 w-5 flex-shrink-0 transition-colors duration-200',
                  'text-gray-400 group-hover:text-gray-600 group-[.active]:text-blue-600'
                )}
              />
              <span className="flex-1">{item.name}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
};