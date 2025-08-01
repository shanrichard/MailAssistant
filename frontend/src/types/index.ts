/**
 * MailAssistant Frontend Types
 * 定义所有前端应用使用的TypeScript类型
 */

// 从 dailyReport 文件导入类型以供本文件使用
import type { DailyReportResponse } from './dailyReport';

// 用户相关类型
export interface User {
  id: string;
  email: string;
  googleId: string;
  createdAt: Date;
  dailyReportTime: string;
}

// 认证相关类型
export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  token: string | null;
  isLoading: boolean;
  error: AppError | null;
}

// 邮件相关类型
export interface EmailMessage {
  id: string;
  gmailId: string;
  subject: string;
  sender: string;
  bodyText: string;
  isImportant: boolean;
  importanceReason?: string;
  category: string;
  receivedAt: Date;
  processedAt?: Date;
  isRead: boolean;
  isStarred: boolean;
}

// 邮件分析结果
export interface EmailAnalysis {
  id: string;
  emailId: string;
  isImportant: boolean;
  importanceScore: number;
  category: string;
  summary: string;
  keyPoints: string[];
  actionItems: string[];
  sentiment: 'positive' | 'neutral' | 'negative';
  confidence: number;
  analysisDate: Date;
}

// 用户偏好
export interface UserPreference {
  id: string;
  userId: string;
  preferenceText: string;
  preferenceVector?: number[];
  category: string;
  priority: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// 日报相关类型 - 从独立文件导出
export type {
  DailyReportResponse
} from './dailyReport';

// Agent相关类型
export interface AgentMessage {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: Date;
  agentType?: 'email_processor' | 'conversation_handler';
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

// Chat相关类型定义
export interface ChatMessage {
  id: string;
  type: 'user' | 'agent' | 'tool_call' | 'agent_thought' | 'error' | 'system';
  content: string;
  timestamp: Date;
  toolCall?: ToolCall;
  thought?: AgentThought;
  isStreaming?: boolean;
  onRetry?: () => void;  // 错误重试回调
}

export interface ToolCall {
  id?: string;
  name?: string;
  toolName?: string; // 兼容旧版本
  arguments?: Record<string, any>;
  input?: any; // 兼容旧版本
  output?: any;
  executionTime?: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'success' | 'error' | 'timeout' | 'cancelled';
  result?: any;
  error?: string;
  startTime?: Date;
  endTime?: Date;
}

export interface AgentThought {
  content: string;
  confidence?: number;
}

// WebSocket相关类型
export interface WebSocketMessage {
  type: 'agent_response' | 'agent_response_chunk' | 'tool_call_start' | 
        'tool_call_result' | 'tool_call_error' | 'agent_thought' | 'agent_error' | 
        'stream_end' | 'daily_report' | 'task_progress' | 'error';
  id?: string;  // 消息ID
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, any>;
  tool_result?: any;
  thought?: string;
  error?: string;  // 错误信息
  timestamp: string;
  agentType?: 'email_processor' | 'conversation_handler';
  sessionId?: string;
  progress?: number;
  toolCalls?: ToolCall[];
}

// 任务相关类型
export interface TaskLog {
  id: string;
  userId: string;
  taskType: 'email_sync' | 'daily_report' | 'email_analysis' | 'bulk_operation';
  taskName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime: Date;
  endTime?: Date;
  progress: number;
  result?: any;
  errorMessage?: string;
  scheduledTime?: Date;
  retryCount: number;
  maxRetries: number;
}

// API相关类型
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// 路由相关类型
export interface RouteConfig {
  path: string;
  element: React.ComponentType;
  requireAuth?: boolean;
  title?: string;
}

// 组件Props类型
export interface EmailListProps {
  emails: EmailMessage[];
  onEmailClick: (email: EmailMessage) => void;
  onBulkAction: (action: string, emails: EmailMessage[]) => void;
  loading?: boolean;
  virtualizing?: boolean;
}

export interface ChatInterfaceProps {
  messages: AgentMessage[];
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export interface DailyReportProps {
  report: DailyReportResponse;
  onRefresh: () => void;
}

// 表单相关类型
export interface LoginFormData {
  email: string;
  password: string;
}

export interface PreferenceFormData {
  preferenceText: string;
  category: string;
  priority: number;
}

export interface SettingsFormData {
  dailyReportTime: string;
  enableNotifications: boolean;
  emailSyncInterval: number;
}

// 状态管理相关类型
export interface EmailStore {
  emails: EmailMessage[];
  currentEmail: EmailMessage | null;
  dailyReport: DailyReportResponse | null;
  categories: string[];
  isLoading: boolean;
  error: string | null;
  // Actions
  setEmails: (emails: EmailMessage[]) => void;
  setCurrentEmail: (email: EmailMessage | null) => void;
  setDailyReport: (report: DailyReportResponse | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  fetchEmails: () => Promise<void>;
  fetchDailyReport: () => Promise<void>;
  markAsRead: (emailIds: string[]) => Promise<void>;
  bulkAction: (action: string, emailIds: string[]) => Promise<void>;
}

export interface ChatStore {
  messages: ChatMessage[];
  currentSession: string | null;
  isConnected: boolean;
  isLoading: boolean;
  // Actions
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  setSession: (sessionId: string | null) => void;
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  sendMessage: (content: string) => Promise<void>;
  connectWebSocket: () => Promise<void>;
  disconnectWebSocket: () => void;
}

// 工具函数类型
export type DateFormatOptions = {
  includeTime?: boolean;
  format?: 'short' | 'medium' | 'long';
  relative?: boolean;
};

export type EmailFilterOptions = {
  category?: string;
  isImportant?: boolean;
  dateRange?: {
    start: Date;
    end: Date;
  };
  sender?: string;
  hasAttachments?: boolean;
};

export type SortOptions = {
  field: keyof EmailMessage;
  direction: 'asc' | 'desc';
};

// 配置类型
export interface AppConfig {
  apiBaseUrl: string;
  wsUrl: string;
  googleClientId: string;
  enableDebug: boolean;
  defaultPageSize: number;
  maxRetries: number;
  requestTimeout: number;
}

// 错误处理类型
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: Date;
}

export type ErrorHandler = (error: AppError) => void;