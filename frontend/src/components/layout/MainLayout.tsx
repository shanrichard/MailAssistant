/**
 * Main Layout Component
 * 主应用布局组件
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import useAuthStore from '../../stores/authStore';
import useChatStore from '../../stores/chatStore';

const MainLayout: React.FC = () => {
  const { user } = useAuthStore();
  const { connectWebSocket, disconnectWebSocket } = useChatStore();

  // Connect WebSocket when layout mounts
  React.useEffect(() => {
    if (user) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [user, connectWebSocket, disconnectWebSocket]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <Header />
      
      <div className="flex">
        {/* Sidebar */}
        <Sidebar />
        
        {/* Main content */}
        <main className="flex-1 ml-64 pt-16 min-h-screen">
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default MainLayout;