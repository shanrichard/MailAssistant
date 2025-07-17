# MailAssistant Frontend

## 概述

MailAssistant的前端应用，使用React + TypeScript + Tailwind CSS构建的现代化单页应用。

## 技术栈

- **框架**: React 18 + TypeScript
- **样式**: Tailwind CSS
- **路由**: React Router v6
- **HTTP客户端**: Axios
- **开发工具**: Vite
- **代码规范**: ESLint + Prettier

## 快速开始

### 环境要求

- Node.js 18+
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

### 构建生产版本

```bash
npm run build
```

### 运行测试

```bash
npm test
```

## 项目结构

```
frontend/
├── public/                  # 静态资源
├── src/
│   ├── components/         # 可复用组件
│   │   ├── layout/        # 布局组件
│   │   ├── common/        # 通用UI组件
│   │   └── ...
│   ├── pages/             # 页面组件
│   │   ├── Login.tsx      # 登录页
│   │   ├── AuthCallback.tsx # OAuth回调页
│   │   ├── DailyReport.tsx  # 日报页
│   │   └── ...
│   ├── services/          # API服务层
│   │   ├── apiClient.ts   # API客户端基类
│   │   ├── authService.ts # 认证服务
│   │   ├── emailService.ts # 邮件服务
│   │   └── ...
│   ├── hooks/             # 自定义React Hooks
│   ├── utils/             # 工具函数
│   ├── types/             # TypeScript类型定义
│   ├── config/            # 配置文件
│   ├── App.tsx            # 应用主组件
│   └── main.tsx           # 应用入口
├── .env.example           # 环境变量示例
├── vite.config.ts         # Vite配置
├── tsconfig.json          # TypeScript配置
├── tailwind.config.js     # Tailwind CSS配置
└── package.json           # 项目依赖

```

## 核心功能

### 已实现

1. **用户认证**
   - Google OAuth2登录
   - JWT Token管理
   - 自动刷新Token
   - 登出功能

2. **基础页面**
   - 登录页面
   - OAuth回调处理
   - 日报页面（基础版）

3. **API集成**
   - Axios客户端封装
   - 自动认证头注入
   - 错误处理机制
   - 请求/响应拦截器

### 开发中

1. **邮件管理**
   - 邮件列表展示
   - 邮件详情查看
   - 邮件分类和标签

2. **智能功能**
   - AI对话界面
   - 实时通知
   - 批量操作

3. **用户设置**
   - 个人信息管理
   - 偏好设置
   - Gmail连接管理

## 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# API配置
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# 应用配置
VITE_APP_NAME=MailAssistant
VITE_APP_VERSION=1.0.0
```

## API服务说明

### AuthService

处理用户认证相关操作：

```typescript
- googleLogin(): 发起Google OAuth登录
- handleOAuthCallback(code): 处理OAuth回调
- logout(): 用户登出
- getAccessToken(): 获取当前访问令牌
- getCurrentUser(): 获取当前用户信息
```

### EmailService

处理邮件相关操作：

```typescript
- getDailyReport(): 获取今日邮件日报
- getEmails(params): 获取邮件列表
- getEmailDetail(id): 获取邮件详情
```

## 开发规范

### 代码风格

- 使用TypeScript严格模式
- 遵循ESLint配置
- 使用Prettier格式化代码

### 组件规范

- 使用函数组件和Hooks
- 组件文件使用PascalCase命名
- 导出类型定义到types目录

### 提交规范

遵循约定式提交：
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关
- chore: 构建/工具链相关

## 常见问题

### 1. CORS错误

确保后端CORS配置正确，允许 `http://localhost:3000` 访问。

### 2. 认证失败

检查：
- 后端服务是否运行
- 环境变量配置是否正确
- Google OAuth配置是否有效

### 3. 热重载不工作

尝试：
- 清除node_modules并重新安装
- 检查Vite配置
- 确保文件保存触发更新

## 测试

### 单元测试

```bash
npm run test:unit
```

### 集成测试

```bash
npm run test:integration
```

### E2E测试

```bash
npm run test:e2e
```

## 部署

### 构建优化

生产构建会自动：
- 压缩代码
- 优化图片
- 代码分割
- Tree shaking

### 部署到Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/mailassistant;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 相关链接

- [项目主文档](../README.md)
- [后端文档](../backend/README.md)
- [API文档](http://localhost:8000/docs)

---

更新时间：2025-07-16