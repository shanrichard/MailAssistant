/**
 * Email Category Component
 * 分类邮件展示组件
 */

import React, { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, CheckIcon } from '@heroicons/react/24/outline';
import { EmailCategory as EmailCategoryType } from '../../types/dailyReport';
import EmailListItem from './EmailListItem';

interface EmailCategoryProps {
  category: EmailCategoryType;
  onMarkAsRead: (categoryName: string) => void;
  isMarking?: boolean;
  defaultExpanded?: boolean;
}

const EmailCategory: React.FC<EmailCategoryProps> = ({ 
  category, 
  onMarkAsRead, 
  isMarking = false,
  defaultExpanded = true
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  const unreadCount = category.emails.filter(email => !email.isRead).length;
  const hasUnreadEmails = unreadCount > 0;

  const handleToggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const handleMarkAsRead = (e: React.MouseEvent) => {
    e.stopPropagation();
    onMarkAsRead(category.categoryName);
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* 分类头部 */}
      <div
        data-testid="category-header"
        className="px-6 py-4 bg-gray-50 border-b border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={handleToggleExpand}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {isExpanded ? (
              <ChevronUpIcon className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="h-5 w-5 text-gray-400" />
            )}
            
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-medium text-gray-900">
                  {category.categoryName}
                </h3>
                <span className="text-sm text-gray-500">
                  {category.emails.length} 封邮件
                </span>
                {hasUnreadEmails && (
                  <span
                    data-testid="unread-count"
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500 text-white"
                  >
                    {unreadCount}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mt-1">
                {category.summary}
              </p>
            </div>
          </div>

          {/* 标记已读按钮 */}
          {hasUnreadEmails && (
            <button
              onClick={handleMarkAsRead}
              disabled={isMarking}
              className={`
                ml-4 inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md
                ${isMarking 
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                  : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                }
                transition-colors duration-200
              `}
            >
              {isMarking ? (
                <>
                  <div className="animate-spin h-3 w-3 mr-1.5 border-2 border-blue-500 border-t-transparent rounded-full" />
                  标记中...
                </>
              ) : (
                <>
                  <CheckIcon className="h-3 w-3 mr-1.5" />
                  标记已读
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* 邮件列表 */}
      {isExpanded && (
        <div className="divide-y divide-gray-200">
          {category.emails.map((email) => (
            <EmailListItem key={email.id} email={email} />
          ))}
        </div>
      )}
    </div>
  );
};

export default EmailCategory;