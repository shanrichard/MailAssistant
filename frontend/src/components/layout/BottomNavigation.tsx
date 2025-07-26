/**
 * Bottom Navigation Component
 * 移动端底部导航组件
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { navigationItems } from '../../config/navigation';
import clsx from 'clsx';

export const BottomNavigation: React.FC = () => {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="flex justify-around py-2">
        {navigationItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              clsx(
                'flex flex-col items-center px-3 py-2 text-xs font-medium transition-colors min-h-[44px] justify-center',
                isActive
                  ? 'text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              )
            }
          >
            <item.icon className="h-6 w-6 mb-1" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
};