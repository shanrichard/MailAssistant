/**
 * Application Entry Point
 * 应用入口文件
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// 开发环境调试工具
import './utils/errorCollector'; // 自动初始化错误收集器
import './utils/debugHelper';    // 注册全局调试函数

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);