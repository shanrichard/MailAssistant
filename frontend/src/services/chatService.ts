/**
 * Chat Service
 * 聊天和WebSocket服务
 */

import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '../types';
import { appConfig, WS_EVENTS } from '../config';

interface ChatServiceCallbacks {
  onOpen: () => void;
  onMessage: (message: WebSocketMessage) => void;
  onError: (error: Error) => void;
  onClose: () => void;
}

class ChatService {
  private socket: Socket | null = null;
  private callbacks: ChatServiceCallbacks | null = null;

  /**
   * 连接WebSocket
   */
  connect(callbacks: ChatServiceCallbacks): void {
    this.callbacks = callbacks;
    
    // Get auth token
    const token = this.getAuthToken();
    if (!token) {
      callbacks.onError(new Error('No authentication token'));
      return;
    }

    // Create socket connection
    this.socket = io(appConfig.wsUrl, {
      auth: {
        token,
      },
      transports: ['websocket'],
    });

    // Setup event handlers
    this.setupEventHandlers();
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.callbacks = null;
  }

  /**
   * 发送消息
   */
  sendMessage(message: any): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit(WS_EVENTS.AGENT_MESSAGE, message);
    } else {
      throw new Error('WebSocket not connected');
    }
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.socket || !this.callbacks) return;

    // Connection events
    this.socket.on(WS_EVENTS.CONNECT, () => {
      console.log('WebSocket connected');
      this.callbacks?.onOpen();
    });

    this.socket.on(WS_EVENTS.DISCONNECT, () => {
      console.log('WebSocket disconnected');
      this.callbacks?.onClose();
    });

    this.socket.on(WS_EVENTS.ERROR, (error: any) => {
      console.error('WebSocket error:', error);
      this.callbacks?.onError(new Error(error.message || 'WebSocket error'));
    });

    // Agent response events
    this.socket.on(WS_EVENTS.AGENT_RESPONSE, (data: any) => {
      const message: WebSocketMessage = {
        type: 'agent_response',
        content: data.message || data.response,
        agentType: data.agent_type,
        sessionId: data.session_id,
        toolCalls: data.tool_calls,
        timestamp: new Date(data.timestamp || Date.now()),
      };
      
      this.callbacks?.onMessage(message);
    });

    this.socket.on(WS_EVENTS.AGENT_RESPONSE_CHUNK, (data: any) => {
      const message: WebSocketMessage = {
        type: 'agent_response_chunk',
        content: data.chunk || data.content,
        agentType: data.agent_type,
        sessionId: data.session_id,
        timestamp: new Date(data.timestamp || Date.now()),
      };
      
      this.callbacks?.onMessage(message);
    });

    // Task events
    this.socket.on(WS_EVENTS.TASK_PROGRESS, (data: any) => {
      const message: WebSocketMessage = {
        type: 'task_progress',
        content: data.message || 'Task in progress',
        progress: data.progress,
        timestamp: new Date(data.timestamp || Date.now()),
      };
      
      this.callbacks?.onMessage(message);
    });

    this.socket.on(WS_EVENTS.DAILY_REPORT_READY, (data: any) => {
      const message: WebSocketMessage = {
        type: 'daily_report',
        content: data.report || data.message,
        timestamp: new Date(data.timestamp || Date.now()),
      };
      
      this.callbacks?.onMessage(message);
    });

    // System events
    this.socket.on(WS_EVENTS.SYSTEM_STATUS, (data: any) => {
      console.log('System status:', data);
    });

    this.socket.on(WS_EVENTS.HEARTBEAT, () => {
      // Respond to heartbeat
      this.socket?.emit(WS_EVENTS.HEARTBEAT, { timestamp: Date.now() });
    });
  }

  /**
   * 获取认证token
   */
  private getAuthToken(): string | null {
    try {
      const authData = localStorage.getItem('mailassistant_auth_token');
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed.state?.token || null;
      }
      return null;
    } catch {
      return null;
    }
  }
}

export const chatService = new ChatService();
export default chatService;