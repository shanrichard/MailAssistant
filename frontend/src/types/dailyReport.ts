/**
 * Daily Report Type Definitions
 * 日报相关的类型定义
 */

/**
 * 日报API响应格式
 */
export interface DailyReportResponse {
  /** 状态 */
  status: 'completed' | 'processing' | 'failed';
  /** Markdown格式的日报内容 */
  content?: string;
  /** 状态消息 */
  message?: string;
  /** 生成时间 */
  generated_at?: string;
}

