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
    <nav 
      className="md:hidden bg-white border-t border-gray-200 shadow-lg z-[9999]"
      style={{
        position: 'fixed',
        bottom: '0px',
        left: '0px',
        right: '0px',
        zIndex: 9999,
        transform: 'translateZ(0)',
        willChange: 'transform'
      }}
    >
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