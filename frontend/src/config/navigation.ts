/**
 * Navigation Configuration
 * 导航配置 - 供Sidebar和BottomNavigation共享使用
 */

import { 
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  CogIcon
} from '@heroicons/react/24/outline';
import { ROUTES } from './index';

export interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const navigationItems: NavigationItem[] = [
  { name: '日报', href: ROUTES.DAILY_REPORT, icon: DocumentTextIcon },
  { name: '对话', href: ROUTES.CHAT, icon: ChatBubbleLeftRightIcon },
  { name: '设置', href: ROUTES.SETTINGS, icon: CogIcon },
];