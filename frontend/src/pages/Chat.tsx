/**
 * Chat Page
 * 聊天页面 - 支持Agent对话和工具调用可视化
 */

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import useChatStore from '../stores/chatStore';
import { ChatMessage, ToolCall, AgentThought } from '../types';
import { useSyncTrigger } from '../hooks/useSyncTrigger';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

const Chat: React.FC = () => {
  const { 
    messages, 
    isConnected, 
    sendMessage, 
    connectWebSocket,
    disconnectWebSocket,
    retryStatus 
  } = useChatStore();
  
  const { isSyncing } = useSyncTrigger();
  const [input, setInput] = useState('');
  const [hasTriggeredSync, setHasTriggeredSync] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // 页面访问时触发同步
  useEffect(() => {
    const triggerSyncOnPageLoad = async () => {
      if (!hasTriggeredSync) {
        setHasTriggeredSync(true);
        try {
          // await checkAndSync('page-visit'); // 暂时注释，等待新同步实现
        } catch (error) {
          console.warn('Auto sync failed:', error);
        }
      }
    };

    triggerSyncOnPageLoad();
  }, [hasTriggeredSync]);
  
  // WebSocket连接已在MainLayout中处理，这里不需要重复连接
  // useEffect(() => {
  //   if (!isConnected) {
  //     connectWebSocket();
  //   }
  //   
  //   return () => {
  //     // 组件卸载时断开连接
  //     // disconnectWebSocket();
  //   };
  // }, []);
  
  const handleSend = async () => {
    if (!input.trim()) return;
    
    await sendMessage(input);
    setInput('');
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* 同步状态指示器 */}
      {isSyncing && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2">
          <div className="flex items-center space-x-2 text-sm text-blue-700">
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
            <span>正在同步邮件数据...</span>
          </div>
        </div>
      )}
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="border-t p-4">
        {/* 重试状态提示 */}
        {retryStatus?.isRetrying && (
          <div className="mb-2 px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg flex items-center">
            <svg className="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>正在重试连接...</span>
          </div>
        )}
        
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入消息..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={!isConnected || !input.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
};

// 消息项组件
const MessageItem: React.FC<{ message: ChatMessage }> = ({ message }) => {
  switch (message.type) {
    case 'user':
      return <UserMessage message={message} />;
    case 'agent':
      return <AgentMessage message={message} />;
    case 'tool_call':
      return <ToolCallCard toolCall={message.toolCall!} />;
    case 'agent_thought':
      return <AgentThoughtCard thought={message.thought!} />;
    case 'error':
      return <ErrorMessage message={message} onRetry={message.onRetry} />;
    case 'system':
      return <SystemMessage message={message} />;
    default:
      return null;
  }
};

// 用户消息组件
const UserMessage: React.FC<{ message: ChatMessage }> = ({ message }) => (
  <div className="flex justify-end">
    <div className="max-w-[70%] bg-blue-600 text-white rounded-lg px-4 py-2">
      <p>{message.content}</p>
      <time className="text-xs text-blue-200">
        {new Date(message.timestamp).toLocaleTimeString()}
      </time>
    </div>
  </div>
);

// Agent消息组件 - 支持Markdown渲染
const AgentMessage: React.FC<{ message: ChatMessage }> = ({ message }) => (
  <div className="flex justify-start">
    <div className="max-w-[70%] bg-gray-100 rounded-lg px-4 py-2">
      <div className="prose prose-sm max-w-none text-gray-800">
        <ReactMarkdown
          components={{
            // 自定义组件样式，确保在聊天界面中显示合适
            h1: ({children}: any) => <h1 className="text-lg font-bold mt-2 mb-1">{children}</h1>,
            h2: ({children}: any) => <h2 className="text-base font-semibold mt-2 mb-1">{children}</h2>,
            h3: ({children}: any) => <h3 className="text-sm font-semibold mt-1 mb-1">{children}</h3>,
            p: ({children}: any) => <p className="my-1">{children}</p>,
            ul: ({children}: any) => <ul className="my-1 ml-4 list-disc">{children}</ul>,
            ol: ({children}: any) => <ol className="my-1 ml-4 list-decimal">{children}</ol>,
            li: ({children}: any) => <li className="my-0.5">{children}</li>,
            blockquote: ({children}: any) => (
              <blockquote className="border-l-4 border-blue-500 pl-3 my-2 italic text-gray-700">
                {children}
              </blockquote>
            ),
            code: ({children, className}: any) => {
              const isInline = !className || !className.includes('language-');
              return isInline 
                ? <code className="bg-gray-200 px-1 py-0.5 rounded text-sm">{children}</code>
                : <code className="block bg-gray-200 p-2 rounded my-1 text-sm overflow-x-auto">{children}</code>;
            },
            pre: ({children}: any) => <pre className="overflow-x-auto">{children}</pre>,
            hr: () => <hr className="my-2 border-gray-300" />,
            strong: ({children}: any) => <strong className="font-semibold text-gray-900">{children}</strong>,
            em: ({children}: any) => <em className="italic">{children}</em>,
            a: ({href, children}: any) => (
              <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
            table: ({children}: any) => (
              <table className="min-w-full divide-y divide-gray-300 my-2">
                {children}
              </table>
            ),
            thead: ({children}: any) => <thead className="bg-gray-50">{children}</thead>,
            tbody: ({children}: any) => <tbody className="divide-y divide-gray-200">{children}</tbody>,
            tr: ({children}: any) => <tr>{children}</tr>,
            th: ({children}: any) => <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{children}</th>,
            td: ({children}: any) => <td className="px-3 py-2 text-sm text-gray-900">{children}</td>,
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
      <time className="text-xs text-gray-500 mt-1 block">
        {new Date(message.timestamp).toLocaleTimeString()}
      </time>
    </div>
  </div>
);

// 系统消息组件
const SystemMessage: React.FC<{ message: ChatMessage }> = ({ message }) => (
  <div className="flex justify-center">
    <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm text-blue-700">
      <p>{message.content}</p>
    </div>
  </div>
);

// 工具调用卡片
const ToolCallCard: React.FC<{ toolCall: ToolCall }> = ({ toolCall }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="mx-8 my-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <span className="text-lg">🔧</span>
          <span className="font-medium text-blue-800">
            {toolCall.status === 'running' ? '正在调用' : '已完成'}: {toolCall.name}
          </span>
        </div>
        <span className="text-gray-500">{isExpanded ? '▼' : '▶'}</span>
      </div>
      
      {isExpanded && (
        <div className="mt-3 space-y-2">
          <div>
            <p className="text-sm font-medium text-gray-600">参数：</p>
            <pre className="mt-1 p-2 bg-white rounded text-xs overflow-x-auto">
              {JSON.stringify(toolCall.arguments, null, 2)}
            </pre>
          </div>
          {toolCall.result && (
            <div>
              <p className="text-sm font-medium text-gray-600">结果：</p>
              <pre className="mt-1 p-2 bg-white rounded text-xs overflow-x-auto">
                {JSON.stringify(toolCall.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Agent思考过程卡片
const AgentThoughtCard: React.FC<{ thought: AgentThought }> = ({ thought }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="mx-8 my-2 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <span className="text-lg">🤔</span>
          <span className="font-medium text-yellow-800">Agent思考中...</span>
        </div>
        <span className="text-gray-500">{isExpanded ? '▼' : '▶'}</span>
      </div>
      
      {isExpanded && (
        <div className="mt-2">
          <p className="text-sm text-gray-700">{thought.content}</p>
        </div>
      )}
    </div>
  );
};

// 错误消息组件
const ErrorMessage: React.FC<{ message: ChatMessage; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="mx-8 my-2 bg-red-50 border border-red-200 rounded-lg p-3">
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <span className="text-lg">❌</span>
        <span className="text-red-800">{message.content}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
        >
          重试
        </button>
      )}
    </div>
  </div>
);

export default Chat;