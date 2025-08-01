/**
 * Main App Component
 * 主应用组件
 */

import React from 'react';
import { Toaster } from 'react-hot-toast';
import AppRoutes from './routes';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <div className="App">
        <AppRoutes />
        <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />
      </div>
    </ErrorBoundary>
  );
};

export default App;