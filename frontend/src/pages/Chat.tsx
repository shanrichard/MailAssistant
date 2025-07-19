/**
 * Chat Page
 * 聊天页面 - 支持Agent对话和工具调用可视化
 */

import React, { useState, useRef, useEffect } from 'react';
import useChatStore from '../stores/chatStore';
import { ChatMessage, ToolCall, AgentThought } from '../types';

const Chat: React.FC = () => {
  const { 
    messages, 
    isConnected, 
    sendMessage, 
    connectWebSocket,
    disconnectWebSocket 
  } = useChatStore();
  
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // 连接WebSocket
  useEffect(() => {
    if (!isConnected) {
      connectWebSocket();
    }
    
    return () => {
      // 组件卸载时断开连接
      // disconnectWebSocket();
    };
  }, []);
  
  const handleSend = async () => {
    if (!input.trim()) return;
    
    await sendMessage(input);
    setInput('');
  };
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="border-t p-4">
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

// Agent消息组件
const AgentMessage: React.FC<{ message: ChatMessage }> = ({ message }) => (
  <div className="flex justify-start">
    <div className="max-w-[70%] bg-gray-100 rounded-lg px-4 py-2">
      <p className="text-gray-800">{message.content}</p>
      <time className="text-xs text-gray-500">
        {new Date(message.timestamp).toLocaleTimeString()}
      </time>
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