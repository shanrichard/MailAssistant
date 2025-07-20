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

  // Connect WebSocket when layout mounts
  React.useEffect(() => {
    if (!user) return;
    
    let cancelled = false;
    
    // 直接从store获取最新的函数，避免依赖
    const store = useChatStore.getState();
    store.connectWebSocket().catch(error => {
      if (!cancelled) {
        console.error('[MainLayout] WebSocket connection failed:', error);
      }
    });
    
    return () => {
      cancelled = true;
      const store = useChatStore.getState();
      store.disconnectWebSocket();
    };
  }, [user?.id]); // 只依赖user.id，避免对象引用变化

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