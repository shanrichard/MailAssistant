/**
 * Important Emails Component
 * 展示需要优先处理的重要邮件
 */

import React, { useState } from 'react';
import { StarIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/solid';
import { ImportantEmail } from '../../types/dailyReport';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ImportantEmailsProps {
  emails: ImportantEmail[];
}

const ImportantEmails: React.FC<ImportantEmailsProps> = ({ emails }) => {
  const [expandedEmails, setExpandedEmails] = useState<Set<string>>(new Set());

  const toggleExpand = (emailId: string) => {
    const newExpanded = new Set(expandedEmails);
    if (newExpanded.has(emailId)) {
      newExpanded.delete(emailId);
    } else {
      newExpanded.add(emailId);
    }
    setExpandedEmails(newExpanded);
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const timeStr = date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    const relativeTime = formatDistanceToNow(date, { 
      locale: zhCN, 
      addSuffix: true 
    });
    return { timeStr, relativeTime };
  };

  if (emails.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">重要邮件</h2>
        <p className="text-gray-500 text-center py-8">暂无重要邮件</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">重要邮件</h2>
        <p className="text-sm text-gray-500">需要您优先处理</p>
      </div>
      
      <div className="divide-y divide-gray-200">
        {emails.map((email) => {
          const isExpanded = expandedEmails.has(email.id);
          const { timeStr, relativeTime } = formatTime(email.receivedAt);
          
          return (
            <div
              key={email.id}
              data-testid="important-email"
              className={`
                p-4 cursor-pointer transition-colors
                ${email.isRead ? 'bg-white' : 'bg-red-50 border-l-4 border-red-500'}
                hover:bg-gray-50
              `}
              onClick={() => toggleExpand(email.id)}
            >
              <div className="flex items-start space-x-3">
                <StarIcon 
                  data-testid="star-icon"
                  className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" 
                />
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className={`
                      text-sm truncate
                      ${email.isRead ? 'font-normal text-gray-900' : 'font-semibold text-gray-900'}
                    `}>
                      {email.subject}
                    </h3>
                    <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                      {timeStr}
                    </span>
                  </div>
                  
                  <div className="mt-1">
                    <p className="text-sm text-gray-600 truncate">
                      {email.sender}
                    </p>
                    <p className="text-xs text-red-600 mt-1">
                      {email.importanceReason}
                    </p>
                  </div>
                  
                  {isExpanded && (
                    <div className="mt-3 text-sm text-gray-700 space-y-1">
                      <p>发件人：{email.sender}</p>
                      <p>接收时间：{relativeTime}</p>
                      {!email.isRead && (
                        <p className="text-red-600 font-medium">未读邮件</p>
                      )}
                    </div>
                  )}
                </div>
                
                <div className="flex-shrink-0 ml-2">
                  {isExpanded ? (
                    <ChevronUpIcon className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ImportantEmails;