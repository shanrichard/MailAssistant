/**
 * Email List Item Component
 * 单个邮件列表项展示
 */

import React from 'react';
import { CategorizedEmail } from '../../types/dailyReport';

interface EmailListItemProps {
  email: CategorizedEmail;
}

const EmailListItem: React.FC<EmailListItemProps> = ({ email }) => {
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else {
      return date.toLocaleDateString('zh-CN', { 
        month: 'numeric', 
        day: 'numeric' 
      });
    }
  };

  return (
    <div className="py-3 px-4 hover:bg-gray-50 transition-colors duration-150">
      <div className="flex items-center space-x-3">
        {/* 未读指示器 */}
        <div className="flex-shrink-0 w-2">
          {!email.isRead && (
            <div
              data-testid="unread-indicator"
              className="h-2 w-2 bg-blue-500 rounded-full"
            />
          )}
        </div>

        {/* 邮件内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className={`
              text-sm truncate pr-2
              ${email.isRead ? 'font-normal text-gray-900' : 'font-semibold text-gray-900'}
            `}>
              {email.subject}
            </h4>
            <span className="text-xs text-gray-500 flex-shrink-0">
              {formatTime(email.receivedAt)}
            </span>
          </div>
          <p className="text-sm text-gray-600 truncate mt-0.5">
            {email.sender}
          </p>
        </div>
      </div>
    </div>
  );
};

export default EmailListItem;