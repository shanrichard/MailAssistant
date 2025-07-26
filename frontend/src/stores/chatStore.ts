/**
 * Chat Store
 * 聊天状态管理 - 完整的Socket.IO实现，支持认证和流式响应
 */

import { create } from 'zustand';
import { ChatMessage, ToolCall, AgentThought, WebSocketMessage } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { io, Socket } from 'socket.io-client';
import useAuthStore from './authStore';
import { appConfig } from '../config';

interface ChatStore {
  // 状态
  messages: ChatMessage[];
  isConnected: boolean;
  socket: Socket | null;
  streamingMessageId: string | null;
  pendingToolCalls: Map<string, ToolCall>;
  retryStatus: {
    isRetrying: boolean;
    retryCount: number;
    maxRetries: number;
  };
  
  // 方法
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  appendToMessage: (id: string, content: string) => void;
  finalizeStreamingMessage: (id: string) => void;
  clearMessages: () => void;
  sendMessage: (content: string) => Promise<void>;
  connectWebSocket: () => Promise<void>;
  disconnectWebSocket: () => void;
  handleReconnect: () => void;
}

const useChatStore = create<ChatStore>()((set, get) => ({
  // 初始状态
  messages: [],
  isConnected: false,
  socket: null,
  streamingMessageId: null,
  pendingToolCalls: new Map(),
  retryStatus: {
    isRetrying: false,
    retryCount: 0,
    maxRetries: 3
  },

  // 消息管理
  addMessage: (message: ChatMessage) => {
    set(state => ({
      messages: [...state.messages, message]
    }));
  },

  updateMessage: (id: string, updates: Partial<ChatMessage>) => {
    set(state => ({
      messages: state.messages.map(msg =>
        msg.id === id ? { ...msg, ...updates } : msg
      )
    }));
  },

  appendToMessage: (id: string, content: string) => {
    set(state => ({
      messages: state.messages.map(msg =>
        msg.id === id 
          ? { ...msg, content: msg.content + content }
          : msg
      )
    }));
  },

  finalizeStreamingMessage: (id: string) => {
    set(state => ({
      messages: state.messages.map(msg =>
        msg.id === id 
          ? { ...msg, isStreaming: false }
          : msg
      ),
      streamingMessageId: null
    }));
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  // 发送消息（使用 Socket.IO）
  sendMessage: async (content: string) => {
    const { socket, isConnected, addMessage } = get();
    
    if (!socket || !isConnected) {
      const errorMessage: ChatMessage = {
        id: uuidv4(),
        type: 'error',
        content: '连接已断开，请稍等重连后再试。',
        timestamp: new Date()
      };
      addMessage(errorMessage);
      return;
    }

    try {
      const userMessage: ChatMessage = {
        id: uuidv4(),
        type: 'user',
        content,
        timestamp: new Date()
      };
      
      addMessage(userMessage);
      
      // 通过 Socket.IO 发送消息
      socket.emit('user_message', {
        content,
        timestamp: new Date().toISOString(),
        message_id: userMessage.id,
        session_id: 'default'  // 可以根据需要调整会话ID
      });
      
    } catch (error) {
      console.error('Send message error:', error);
      
      const errorMessage: ChatMessage = {
        id: uuidv4(),
        type: 'error',
        content: '消息发送失败，请重试。',
        timestamp: new Date()
      };
      
      addMessage(errorMessage);
    }
  },

  // WebSocket 连接
  connectWebSocket: async () => {
    const { socket: currentSocket } = get();
    
    // 如果已经连接，直接返回
    if (currentSocket && currentSocket.connected) {
      return;
    }

    // 清理旧的连接
    if (currentSocket) {
      console.log('清理旧的Socket.IO连接');
      currentSocket.removeAllListeners();
      currentSocket.disconnect();
    }

    try {
      console.log('正在连接 Socket.IO...');
      
      // 从 authStore 获取 token
      const authStore = useAuthStore.getState();
      const token = authStore.token;
      
      const socket = io(appConfig.wsUrl, {
        transports: ['websocket', 'polling'],
        timeout: 10000,
        retries: 3,
        // 认证方式1：通过 auth 参数
        auth: token ? { token } : undefined,
        // 认证方式2：通过 extraHeaders（作为备选）
        extraHeaders: token ? {
          'Authorization': `Bearer ${token}`
        } : undefined
      });

      // 设置所有事件监听器
      setupEventListeners(socket, set, get);

      set({ socket });
      
    } catch (error) {
      console.error('Socket.IO 初始化错误:', error);
      set({ isConnected: false, socket: null });
    }
  },

  disconnectWebSocket: () => {
    const { socket } = get();
    if (socket) {
      console.log('断开 Socket.IO 连接');
      socket.removeAllListeners();
      socket.disconnect();
      set({ socket: null, isConnected: false });
    }
  },

  // 重连处理
  handleReconnect: () => {
    const { retryStatus } = get();
    
    if (retryStatus.retryCount >= retryStatus.maxRetries) {
      console.log('达到最大重试次数');
      get().addMessage({
        id: uuidv4(),
        type: 'error',
        content: '连接失败，请刷新页面重试',
        timestamp: new Date()
      });
      return;
    }

    set(state => ({
      retryStatus: {
        ...state.retryStatus,
        isRetrying: true,
        retryCount: state.retryStatus.retryCount + 1
      }
    }));

    // 指数退避重连
    const delay = Math.pow(2, retryStatus.retryCount) * 1000;
    console.log(`${delay}ms 后重连（第 ${retryStatus.retryCount + 1} 次）`);
    
    setTimeout(() => {
      get().connectWebSocket();
    }, delay);
  }

}));

// 设置Socket.IO事件监听器的函数
function setupEventListeners(
  socket: Socket,
  set: any,
  get: () => ChatStore
) {
  // 连接成功
  socket.on('connect', () => {
    console.log('Socket.IO 连接成功:', socket.id);
    set({ 
      isConnected: true, 
      retryStatus: { 
        isRetrying: false, 
        retryCount: 0, 
        maxRetries: 3 
      } 
    });
  });

  // 连接确认
  socket.on('connection_established', (data) => {
    console.log('收到连接确认:', data);
    
    const message = data.authenticated 
      ? `已连接到聊天服务器 (${data.user?.name || data.user?.email})`
      : '已连接到聊天服务器';
      
    get().addMessage({
      id: uuidv4(),
      type: 'system',
      content: message,
      timestamp: new Date()
    });
  });

  // Agent 响应片段（流式）
  socket.on('agent_response_chunk', (data) => {
    console.log('收到 Agent 响应片段:', data);
    const { streamingMessageId, appendToMessage, addMessage } = get();
    
    if (streamingMessageId && data.id === streamingMessageId) {
      // 追加内容到现有消息
      appendToMessage(streamingMessageId, data.content);
    } else {
      // 创建新的流式消息
      const newMessage: ChatMessage = {
        id: data.id || uuidv4(),
        type: 'agent',
        content: data.content,
        timestamp: new Date(data.timestamp),
        isStreaming: true
      };
      addMessage(newMessage);
      set({ streamingMessageId: newMessage.id });
    }
  });

  // 工具调用超时处理器存储
  const toolTimeouts = new Map<string, NodeJS.Timeout>();
  const TOOL_CALL_TIMEOUT = 30000; // 30秒超时

  // 安全删除工具调用的函数
  const safeDeleteToolCall = (id: string) => {
    const { pendingToolCalls } = get();
    if (pendingToolCalls.has(id)) {
      pendingToolCalls.delete(id);
      console.log(`安全删除工具调用: ${id}`);
    }
    
    // 清理对应的超时处理器
    const timeoutHandler = toolTimeouts.get(id);
    if (timeoutHandler) {
      clearTimeout(timeoutHandler);
      toolTimeouts.delete(id);
    }
  };

  // 设置工具调用超时处理
  const setToolTimeout = (id: string, toolName: string) => {
    // 清理可能存在的旧超时处理器
    const oldHandler = toolTimeouts.get(id);
    if (oldHandler) {
      clearTimeout(oldHandler);
    }
    
    const timeoutHandler = setTimeout(() => {
      const { pendingToolCalls } = get();
      const toolCall = pendingToolCalls.get(id);
      
      if (toolCall && toolCall.status === 'running') {
        // 标记为超时状态
        toolCall.status = 'timeout';
        toolCall.error = '工具执行超时';
        
        // 显示超时消息
        get().addMessage({
          id: uuidv4(),
          type: 'tool_call',
          content: `⏰ 工具执行超时：${toolName}`,
          timestamp: new Date(),
          toolCall: { ...toolCall }
        });
        
        // 安全删除
        safeDeleteToolCall(id);
      }
    }, TOOL_CALL_TIMEOUT);
    
    toolTimeouts.set(id, timeoutHandler);
  };

  // 工具调用开始 - 增强版
  socket.on('tool_call_start', (data) => {
    console.log('工具调用开始:', data);
    const toolCall: ToolCall = {
      id: data.id,
      name: data.tool_name,
      arguments: data.tool_args, // 可能为null（参数还在构建中）
      status: 'running',
      startTime: new Date(data.timestamp)
    };
    
    get().pendingToolCalls.set(data.id, toolCall);
    setToolTimeout(data.id, data.tool_name);
    
    // 显示工具调用状态消息
    get().addMessage({
      id: uuidv4(),
      type: 'tool_call',
      content: `🔧 正在执行：${data.tool_name}`,
      timestamp: new Date(data.timestamp),
      toolCall
    });
  });

  // 🎯 新增：工具调用参数完整事件
  socket.on('tool_call_args_complete', (data) => {
    console.log('工具调用参数完整:', data);
    const { pendingToolCalls, updateMessage } = get();
    const toolCall = pendingToolCalls.get(data.id);
    
    if (toolCall) {
      // 更新工具调用的参数
      toolCall.arguments = data.tool_args;
      
      console.log(`工具 ${data.tool_name} 参数构建完成:`, data.tool_args);
      
      // 可选：显示参数完整的消息（或静默更新）
      // 这里选择静默更新，避免UI过于嘈杂
    } else {
      console.warn('未找到匹配的工具调用ID:', data.id);
    }
  });

  // 工具调用结果 - 完善版
  socket.on('tool_call_result', (data) => {
    console.log('工具调用结果:', data);
    const { pendingToolCalls } = get();
    const toolCall = pendingToolCalls.get(data.id);
    
    if (toolCall) {
      // 更新工具调用状态
      toolCall.status = 'completed';
      toolCall.result = data.tool_result;
      toolCall.endTime = new Date(data.timestamp);
      
      // 显示完成消息
      get().addMessage({
        id: uuidv4(),
        type: 'tool_call',
        content: `✅ 工具执行完成：${toolCall.name}`,
        timestamp: new Date(data.timestamp),
        toolCall
      });
      
      // 安全清理
      safeDeleteToolCall(data.id);
    } else {
      // 容错处理：显示"孤儿"结果
      console.warn('未找到匹配的待处理工具调用:', data.id);
      if (data.tool_name) {
        get().addMessage({
          id: uuidv4(),
          type: 'tool_call',
          content: `✅ 工具执行完成：${data.tool_name}`,
          timestamp: new Date(data.timestamp),
          toolCall: {
            id: data.id,
            name: data.tool_name,
            status: 'completed',
            result: data.tool_result
          }
        });
      }
    }
  });

  // 工具调用错误 - 完善版
  socket.on('tool_error', (data) => {
    console.log('工具调用错误:', data);
    const { pendingToolCalls } = get();
    const toolCall = pendingToolCalls.get(data.id);
    
    if (toolCall) {
      toolCall.status = 'error';
      toolCall.error = data.error;
      toolCall.endTime = new Date(data.timestamp);
      
      get().addMessage({
        id: uuidv4(),
        type: 'tool_call',
        content: `❌ 工具执行失败：${data.message || data.error}`,
        timestamp: new Date(data.timestamp),
        toolCall
      });
      
      // 安全清理
      safeDeleteToolCall(data.id);
    } else {
      // 容错处理：显示"孤儿"错误
      console.warn('未找到匹配的待处理工具调用:', data.id);
      if (data.tool_name) {
        get().addMessage({
          id: uuidv4(),
          type: 'tool_call',
          content: `❌ 工具执行失败：${data.tool_name} - ${data.message || data.error}`,
          timestamp: new Date(data.timestamp),
          toolCall: {
            id: data.id,
            name: data.tool_name,
            status: 'error',
            error: data.error
          }
        });
      }
    }
  });

  // 对话完成
  socket.on('conversation_complete', (data) => {
    console.log('对话完成:', data);
    const { streamingMessageId, finalizeStreamingMessage } = get();
    if (streamingMessageId) {
      finalizeStreamingMessage(streamingMessageId);
    }
  });

  // 连接断开 - 增强版
  socket.on('disconnect', (reason) => {
    console.log('Socket.IO 连接断开:', reason);
    set({ isConnected: false });
    
    // 清理所有待处理的工具调用
    const { pendingToolCalls } = get();
    pendingToolCalls.forEach((toolCall, id) => {
      if (toolCall.status === 'running') {
        get().addMessage({
          id: uuidv4(),
          type: 'tool_call',
          content: `🔌 连接断开，工具调用中断：${toolCall.name}`,
          timestamp: new Date(),
          toolCall: { ...toolCall, status: 'cancelled' }
        });
      }
    });
    
    // 清理所有状态
    pendingToolCalls.clear();
    toolTimeouts.forEach(handler => clearTimeout(handler));
    toolTimeouts.clear();
    
    if (reason !== 'io client disconnect') {
      // 自动重连
      get().handleReconnect();
    }
  });

  // 连接错误
  socket.on('connect_error', async (error) => {
    console.error('Socket.IO 连接错误:', error);
    
    // 检查是否是认证错误
    if (error.message === 'Authentication error' || (error as any).type === 'UnauthorizedError') {
      console.log('认证失败，尝试刷新token');
      try {
        // 刷新token
        const authStore = useAuthStore.getState();
        await authStore.refreshToken();
        
        // 使用新token重新连接
        const newToken = authStore.token;
        if (newToken && socket) {
          console.log('使用新token重新连接');
          socket.auth = { token: newToken };
          socket.connect();
        }
      } catch (refreshError) {
        console.error('Token刷新失败:', refreshError);
        // 引导用户重新登录
        get().addMessage({
          id: uuidv4(),
          type: 'error',
          content: '认证已过期，请重新登录',
          timestamp: new Date()
        });
      }
    }
    
    set({ isConnected: false });
    get().handleReconnect();
  });

  // 服务器错误
  socket.on('error', (data) => {
    console.error('服务器错误:', data);
    
    let errorMessage = '服务器发生错误';
    if (data.type === 'authentication_required') {
      errorMessage = '请先登录后再发送消息';
    } else if (data.type === 'processing_error') {
      errorMessage = '消息处理出错，请稍后重试';
    } else if (data.type === 'validation_error') {
      errorMessage = data.message || '输入验证失败';
    } else if (data.message) {
      errorMessage = data.message;
    }
    
    get().addMessage({
      id: uuidv4(),
      type: 'error',
      content: errorMessage,
      timestamp: new Date()
    });
  });

  // 兼容旧的agent_response事件
  socket.on('agent_response', (data) => {
    console.log('收到 Agent 响应:', data);
    get().addMessage({
      id: uuidv4(),
      type: 'agent',
      content: data.content,
      timestamp: new Date(data.timestamp)
    });
  });
}

export default useChatStore;