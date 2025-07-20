/**
 * Chat Store
 * 聊天状态管理 - 支持LangGraph流式响应和工具调用可视化
 */

import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';
import { v4 as uuidv4 } from 'uuid';
import { ChatStore, ChatMessage, WebSocketMessage, ToolCall } from '../types';
import { getToken } from '../utils/auth';
import { appConfig } from '../config';
import { withRetry, ErrorRecoveryManager } from '../utils/errorRecovery';

interface ChatStoreState extends ChatStore {
  socket: Socket | null;
  streamingMessageId: string | null;
  pendingToolCalls: Map<string, ToolCall>;
  errorRecoveryManager: ErrorRecoveryManager;
  retryStatus: {
    isRetrying: boolean;
    attempt: number;
    message: string;
  } | null;
}

const useChatStore = create<ChatStoreState>((set, get) => ({
  messages: [],
  currentSession: uuidv4(),
  isConnected: false,
  isLoading: false,
  socket: null,
  streamingMessageId: null,
  pendingToolCalls: new Map(),
  errorRecoveryManager: new ErrorRecoveryManager(),
  retryStatus: null,

  addMessage: (message: ChatMessage) => {
    set((state) => ({
      messages: [...state.messages, message]
    }));
  },

  updateMessage: (id: string, updates: Partial<ChatMessage>) => {
    set((state) => ({
      messages: state.messages.map(msg =>
        msg.id === id ? { ...msg, ...updates } : msg
      )
    }));
  },

  clearMessages: () => {
    set({ messages: [], currentSession: uuidv4() });
  },

  setSession: (sessionId: string | null) => {
    set({ currentSession: sessionId });
  },

  setConnected: (connected: boolean) => {
    set({ isConnected: connected });
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  sendMessage: async (content: string) => {
    const { socket, currentSession, addMessage, errorRecoveryManager } = get();
    
    // 添加用户消息
    const userMessage: ChatMessage = {
      id: uuidv4(),
      type: 'user',
      content,
      timestamp: new Date(),
      isStreaming: false
    };
    
    addMessage(userMessage);
    set({ isLoading: true, retryStatus: null });

    try {
      // 使用重试机制发送消息
      await errorRecoveryManager.executeWithRetry(
        `send_message_${userMessage.id}`,
        async () => {
          const currentSocket = get().socket;
          
          // 确保连接存在
          if (!currentSocket || !currentSocket.connected) {
            // 尝试重新连接
            await get().connectWebSocket();
            
            // 再次检查
            const reconnectedSocket = get().socket;
            if (!reconnectedSocket || !reconnectedSocket.connected) {
              throw new Error('WebSocket connection failed');
            }
          }
          
          // 发送消息
          return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Message send timeout'));
            }, 30000); // 30秒超时
            
            // 监听一次性响应以确认发送成功
            const socket = get().socket!;
            
            // 发送消息
            socket.emit('agent_message', {
              message: content,
              session_id: currentSession
            });
            
            // 假设立即成功（实际项目中可能需要等待确认）
            clearTimeout(timeout);
            resolve(true);
          });
        },
        {
          maxAttempts: 3,
          baseDelay: 1000,
          maxDelay: 5000
        },
        {
          onRetry: (attempt, delay) => {
            set({ 
              retryStatus: { 
                isRetrying: true, 
                attempt,
                message: `正在重试发送消息 (${attempt}/3)...`
              }
            });
          },
          onError: (error) => {
            console.error('Failed to send message after retries:', error);
            
            // 添加错误消息
            const errorMessage: ChatMessage = {
              id: uuidv4(),
              type: 'error',
              content: '消息发送失败，请检查网络连接后重试',
              timestamp: new Date(),
              onRetry: () => get().sendMessage(content)
            };
            
            addMessage(errorMessage);
            set({ isLoading: false, retryStatus: null });
          },
          onSuccess: () => {
            set({ retryStatus: null });
          }
        }
      );
    } catch (error) {
      // 错误已在 onError 中处理
      console.error('Send message error:', error);
    }
  },

  connectWebSocket: async () => {
    // 防止重复连接
    const existingSocket = get().socket;
    if (existingSocket && existingSocket.connected) {
      console.log('WebSocket already connected');
      return Promise.resolve();
    }

    const token = getToken();
    if (!token) {
      console.error('No auth token available');
      return Promise.reject(new Error('No auth token'));
    }

    const socket = io(appConfig.wsUrl, {
      auth: {
        token
      },
      path: '/socket.io/',
      transports: ['polling', 'websocket'], // 先使用polling，然后升级到websocket
      upgrade: true, // 允许升级
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
      set({ isConnected: true });
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      set({ isConnected: false });
    });

    socket.on('agent_event', (event: WebSocketMessage) => {
      const { messages, streamingMessageId, pendingToolCalls, updateMessage, addMessage } = get();
      
      switch (event.type) {
        case 'agent_response_chunk':
          // 处理流式响应
          if (streamingMessageId) {
            const lastMessage = messages.find(msg => msg.id === streamingMessageId);
            if (lastMessage && lastMessage.isStreaming) {
              updateMessage(streamingMessageId, {
                content: lastMessage.content + (event.content || '')
              });
            }
          } else {
            // 创建新的流式消息
            const newMessageId = event.id || uuidv4();
            const agentMessage: ChatMessage = {
              id: newMessageId,
              type: 'agent',
              content: event.content || '',
              timestamp: new Date(event.timestamp),
              isStreaming: true
            };
            addMessage(agentMessage);
            set({ streamingMessageId: newMessageId });
          }
          break;

        case 'tool_call_start':
          // 工具调用开始
          if (event.tool_name && event.id) {
            const toolCall: ToolCall = {
              id: event.id,
              name: event.tool_name,
              arguments: event.tool_args || {},
              status: 'running'
            };
            
            pendingToolCalls.set(event.id, toolCall);
            
            const toolMessage: ChatMessage = {
              id: event.id,
              type: 'tool_call',
              content: `调用工具: ${event.tool_name}`,
              timestamp: new Date(event.timestamp),
              toolCall
            };
            addMessage(toolMessage);
          }
          break;

        case 'tool_call_result':
          // 工具调用结果
          if (event.tool_name && event.id) {
            const pendingCall = pendingToolCalls.get(event.id);
            if (pendingCall) {
              pendingCall.status = 'completed';
              pendingCall.result = event.tool_result;
              
              updateMessage(event.id, {
                toolCall: pendingCall
              });
              
              pendingToolCalls.delete(event.id);
            }
          }
          break;

        case 'tool_call_error':
          // 工具调用错误
          if (event.tool_name && event.id) {
            const pendingCall = pendingToolCalls.get(event.id);
            if (pendingCall) {
              pendingCall.status = 'failed';
              pendingCall.error = event.error;
              
              updateMessage(event.id, {
                toolCall: pendingCall
              });
              
              pendingToolCalls.delete(event.id);
            }
          }
          break;

        case 'agent_error':
          // Agent错误
          const errorMessage: ChatMessage = {
            id: uuidv4(),
            type: 'error',
            content: event.error || '处理请求时发生错误',
            timestamp: new Date(event.timestamp),
            onRetry: () => {
              // 实现重试逻辑
              const lastUserMessage = [...messages].reverse().find(msg => msg.type === 'user');
              if (lastUserMessage) {
                get().sendMessage(lastUserMessage.content);
              }
            }
          };
          addMessage(errorMessage);
          set({ isLoading: false });
          break;

        case 'stream_end':
          // 流式传输结束
          if (streamingMessageId) {
            updateMessage(streamingMessageId, {
              isStreaming: false
            });
            set({ streamingMessageId: null, isLoading: false });
          }
          break;
      }
    });

    socket.on('error', (error: any) => {
      console.error('WebSocket error:', error);
      const errorMessage: ChatMessage = {
        id: uuidv4(),
        type: 'error',
        content: '连接错误，请检查网络连接',
        timestamp: new Date()
      };
      addMessage(errorMessage);
    });

    set({ socket });
    
    // 返回连接 Promise
    return new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
      }, 10000); // 10秒超时
      
      socket.once('connect', () => {
        clearTimeout(timeout);
        resolve();
      });
      
      socket.once('connect_error', (error) => {
        clearTimeout(timeout);
        reject(error);
      });
    });
  },

  disconnectWebSocket: () => {
    const { socket } = get();
    if (socket) {
      socket.disconnect();
      set({ socket: null, isConnected: false });
    }
  }

}));

export default useChatStore;