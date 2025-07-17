/**
 * Daily Report Type Definitions
 * 日报相关的类型定义
 */

/**
 * 日报统计数据
 */
export interface DailyReportStats {
  /** 节省的时间（分钟） */
  timeSaved: number;
  /** 过滤的邮件数量 */
  emailsFiltered: number;
  /** 总邮件数量 */
  totalEmails: number;
}

/**
 * 重要邮件
 */
export interface ImportantEmail {
  /** 邮件ID */
  id: string;
  /** 邮件主题 */
  subject: string;
  /** 发件人 */
  sender: string;
  /** 接收时间 */
  receivedAt: Date | string;
  /** 是否已读 */
  isRead: boolean;
  /** 重要原因（LLM生成） */
  importanceReason: string;
}

/**
 * 分类邮件中的单个邮件
 */
export interface CategorizedEmail {
  /** 邮件ID */
  id: string;
  /** 邮件主题 */
  subject: string;
  /** 发件人 */
  sender: string;
  /** 接收时间 */
  receivedAt: Date | string;
  /** 是否已读 */
  isRead: boolean;
}

/**
 * 邮件分类
 */
export interface EmailCategory {
  /** 分类名称（LLM生成） */
  categoryName: string;
  /** 分类摘要（LLM生成） */
  summary: string;
  /** 该分类下的邮件列表 */
  emails: CategorizedEmail[];
}

/**
 * 完整的日报数据
 */
export interface DailyReport {
  /** 统计数据 */
  stats: DailyReportStats;
  /** 重要邮件列表 */
  importantEmails: ImportantEmail[];
  /** 分类邮件列表 */
  categorizedEmails: EmailCategory[];
  /** 日报生成时间 */
  generatedAt: Date | string;
}

/**
 * API响应格式
 */
export interface DailyReportResponse {
  /** 响应状态 */
  status: 'success' | 'error';
  /** 日报数据 */
  data?: DailyReport;
  /** 错误信息 */
  error?: string;
}

/**
 * 标记已读请求参数
 */
export interface MarkAsReadRequest {
  /** 分类名称 */
  categoryName: string;
  /** 邮件ID列表 */
  emailIds: string[];
}