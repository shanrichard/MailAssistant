/**
 * Chat Store
 * 聊天状态管理
 */

import { create } from 'zustand';
import { ChatStore, AgentMessage, WebSocketMessage, AppError } from '../types';
import { chatService } from '../services/chatService';
import { APP_CONSTANTS } from '../config';

interface ExtendedChatStore extends ChatStore {
  // Additional state
  isTyping: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  error: AppError | null;
  activeAgent: 'email_processor' | 'conversation_handler' | null;
  
  // Additional actions
  setTyping: (typing: boolean) => void;
  setConnectionStatus: (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void;
  setError: (error: AppError | null) => void;
  setActiveAgent: (agent: 'email_processor' | 'conversation_handler' | null) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  sendMessageToAgent: (content: string, agentType: 'email_processor' | 'conversation_handler') => Promise<void>;
  handleWebSocketMessage: (message: WebSocketMessage) => void;
  retryConnection: () => void;
  clearError: () => void;
  clearSession: () => void;
  getMessageHistory: (limit?: number) => AgentMessage[];
  deleteMessage: (messageId: string) => void;
  editMessage: (messageId: string, newContent: string) => void;
}

const useChatStore = create<ExtendedChatStore>()((set, get) => ({
  // Initial state
  messages: [],
  currentSession: null,
  isConnected: false,
  isLoading: false,
  isTyping: false,
  connectionStatus: 'disconnected',
  error: null,
  activeAgent: null,

  // Basic actions
  addMessage: (message: AgentMessage) => {
    const { messages } = get();
    set({ messages: [...messages, message] });
  },

  updateMessage: (id: string, updates: Partial<AgentMessage>) => {
    const { messages } = get();
    const updatedMessages = messages.map(msg =>
      msg.id === id ? { ...msg, ...updates } : msg
    );
    set({ messages: updatedMessages });
  },

  clearMessages: () => {
    set({ messages: [] });
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

  setTyping: (typing: boolean) => {
    set({ isTyping: typing });
  },

  setConnectionStatus: (status: 'connecting' | 'connected' | 'disconnected' | 'error') => {
    set({ connectionStatus: status });
  },

  setError: (error: AppError | null) => {
    set({ error });
  },

  setActiveAgent: (agent: 'email_processor' | 'conversation_handler' | null) => {
    set({ activeAgent: agent });
  },

  // WebSocket actions
  connectWebSocket: () => {
    try {
      set({ connectionStatus: 'connecting' });
      
      chatService.connect({
        onOpen: () => {
          set({ 
            isConnected: true, 
            connectionStatus: 'connected',
            error: null 
          });
        },
        onMessage: (message: WebSocketMessage) => {
          get().handleWebSocketMessage(message);
        },
        onError: (error: Error) => {
          set({
            isConnected: false,
            connectionStatus: 'error',
            error: {
              code: 'WEBSOCKET_ERROR',
              message: error.message,
              timestamp: new Date(),
            }
          });
        },
        onClose: () => {
          set({ 
            isConnected: false,
            connectionStatus: 'disconnected'
          });
        },
      });
    } catch (error) {
      set({
        connectionStatus: 'error',
        error: {
          code: 'WEBSOCKET_CONNECTION_FAILED',
          message: error instanceof Error ? error.message : 'Failed to connect',
          timestamp: new Date(),
        }
      });
    }
  },

  disconnectWebSocket: () => {
    chatService.disconnect();
    set({ 
      isConnected: false,
      connectionStatus: 'disconnected',
      currentSession: null
    });
  },

  handleWebSocketMessage: (message: WebSocketMessage) => {
    const { addMessage, updateMessage, setTyping, setLoading } = get();
    
    switch (message.type) {
      case 'agent_response':
        const responseMessage: AgentMessage = {
          id: `msg_${Date.now()}`,
          type: 'agent',
          content: message.content,
          timestamp: message.timestamp,
          agentType: message.agentType,
          toolCalls: message.toolCalls,
        };
        addMessage(responseMessage);
        setTyping(false);
        setLoading(false);
        break;
        
      case 'agent_response_chunk':
        // Handle streaming response
        const lastMessage = get().messages[get().messages.length - 1];
        if (lastMessage && lastMessage.type === 'agent' && lastMessage.isStreaming) {
          updateMessage(lastMessage.id, {
            content: lastMessage.content + message.content,
          });
        } else {
          const streamMessage: AgentMessage = {
            id: `msg_${Date.now()}`,
            type: 'agent',
            content: message.content,
            timestamp: message.timestamp,
            agentType: message.agentType,
            isStreaming: true,
          };
          addMessage(streamMessage);
        }
        break;
        
      case 'task_progress':
        // Handle task progress updates
        setLoading(true);
        break;
        
      case 'daily_report':
        // Handle daily report completion
        const reportMessage: AgentMessage = {
          id: `msg_${Date.now()}`,
          type: 'agent',
          content: message.content,
          timestamp: message.timestamp,
          agentType: 'email_processor',
        };
        addMessage(reportMessage);
        break;
        
      case 'error':
        set({
          error: {
            code: 'AGENT_ERROR',
            message: message.content,
            timestamp: message.timestamp,
          }
        });
        setLoading(false);
        setTyping(false);
        break;
        
      default:
        console.warn('Unknown message type:', message.type);
    }
  },

  retryConnection: () => {
    get().disconnectWebSocket();
    setTimeout(() => {
      get().connectWebSocket();
    }, 1000);
  },

  // Message actions
  sendMessage: async (content: string) => {
    try {
      const { isConnected, activeAgent } = get();
      
      if (!isConnected) {
        throw new Error('WebSocket not connected');
      }
      
      if (!activeAgent) {
        throw new Error('No active agent selected');
      }
      
      // Add user message
      const userMessage: AgentMessage = {
        id: `msg_${Date.now()}`,
        type: 'user',
        content,
        timestamp: new Date(),
      };
      
      get().addMessage(userMessage);
      set({ isLoading: true, isTyping: true });
      
      // Send to appropriate agent
      await get().sendMessageToAgent(content, activeAgent);
      
    } catch (error) {
      set({
        error: {
          code: 'SEND_MESSAGE_FAILED',
          message: error instanceof Error ? error.message : 'Failed to send message',
          timestamp: new Date(),
        },
        isLoading: false,
        isTyping: false,
      });
    }
  },

  sendMessageToAgent: async (content: string, agentType: 'email_processor' | 'conversation_handler') => {
    const { currentSession } = get();
    
    const message = {
      message: content,
      session_id: currentSession,
      agent_type: agentType,
    };
    
    chatService.sendMessage(message);
  },

  // Utility actions
  clearError: () => {
    set({ error: null });
  },

  clearSession: () => {
    set({ 
      currentSession: null,
      messages: [],
      activeAgent: null
    });
  },

  getMessageHistory: (limit?: number) => {
    const { messages } = get();
    return limit ? messages.slice(-limit) : messages;
  },

  deleteMessage: (messageId: string) => {
    const { messages } = get();
    const filteredMessages = messages.filter(msg => msg.id !== messageId);
    set({ messages: filteredMessages });
  },

  editMessage: (messageId: string, newContent: string) => {
    const { messages } = get();
    const updatedMessages = messages.map(msg =>
      msg.id === messageId ? { ...msg, content: newContent } : msg
    );
    set({ messages: updatedMessages });
  },
}));

export default useChatStore;