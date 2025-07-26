/**
 * Sidebar Component
 * 侧边栏导航组件 - 简化版，只包含核心功能
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { navigationItems } from '../../config/navigation';
import clsx from 'clsx';

export const Sidebar: React.FC = () => {
  return (
    <div className="hidden md:block fixed left-0 top-16 bottom-0 w-48 bg-white border-r border-gray-200">
      <nav className="px-3 py-6">
        <div className="space-y-2">
          {navigationItems.map((item) => (
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