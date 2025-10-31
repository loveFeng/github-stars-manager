# GitHub Stars Manager - 前端应用

基于 SQLite 的 GitHub 星标仓库管理器的现代化前端界面。

## 功能特性

### 核心功能
- 🔐 **GitHub 认证** - 支持 Personal Access Token 和 OAuth 登录
- ⭐ **星标仓库管理** - 浏览、搜索、过滤你的 GitHub 星标仓库
- 📊 **仓库详情** - 查看详细的仓库信息、统计数据和 AI 分析结果
- 🚀 **Release 订阅** - 追踪关注仓库的发布动态
- 📥 **一键下载** - 快速下载 Release 资产文件
- 🏷️ **智能分类** - 默认和自定义分类系统
- 🔍 **强大搜索** - 支持关键词搜索、语言过滤、多维度排序
- 🤖 **AI 集成** - 配置 OpenAI 兼容的 AI 服务生成仓库摘要
- ☁️ **WebDAV 备份** - 支持数据云端备份和跨设备同步
- 🎨 **现代化 UI** - 响应式设计，支持深色/浅色主题

### 技术栈
- **React 18** - 现代化的 UI 框架
- **TypeScript** - 类型安全的开发体验
- **Tailwind CSS** - 实用优先的 CSS 框架
- **Zustand** - 轻量级状态管理，支持持久化
- **React Router** - 客户端路由
- **Shadcn/UI** - 高质量的 UI 组件库
- **Lucide React** - 美观的图标库

## 在线演示

访问部署地址：https://unkmn8l5lzrt.space.minimax.io

## 快速开始

### 本地开发

1. 安装依赖
```bash
cd github-stars-manager-frontend
pnpm install
```

2. 启动开发服务器
```bash
pnpm run dev
```

3. 构建生产版本
```bash
pnpm run build
```

## 使用指南

### 登录

1. 访问应用首页
2. 选择登录方式：
   - **Personal Access Token**: 
     - 在 GitHub 创建 Token: https://github.com/settings/tokens/new
     - 需要权限: `repo` 和 `user`
     - 在登录页输入 Token
   - **OAuth**: 使用 GitHub OAuth 授权（需要配置）

### 仓库管理

登录后，你可以：
- 查看所有星标仓库
- 使用搜索框搜索仓库
- 按语言、星标数、更新时间等维度过滤
- 点击仓库卡片查看详细信息
- 使用侧边栏的分类快速筛选

### Release 订阅

1. 进入 "Release 订阅" 页面
2. 查看所有仓库的 Release 信息
3. 点击 "订阅" 按钮关注感兴趣的 Release
4. 一键下载 Release 资产文件

### 设置配置

在设置页面可以配置：

#### AI 配置
- 添加 OpenAI 兼容的 AI 服务
- 配置 API URL、API Key 和模型名称
- 用于自动生成仓库摘要和标签

#### WebDAV 备份
- 配置 WebDAV 服务器信息
- 支持坚果云、Nextcloud、ownCloud 等
- 实现数据云端备份和跨设备同步

#### 外观设置
- 主题：浅色/深色/跟随系统
- 语言：中文/English

#### 常规设置
- 自动同步开关
- 同步间隔设置
- 桌面通知设置

## 项目结构

```
src/
├── components/          # UI 组件
│   ├── ui/             # Shadcn UI 组件
│   ├── layouts/        # 布局组件
│   ├── Header.tsx      # 顶部导航
│   └── Sidebar.tsx     # 侧边栏
├── pages/              # 页面组件
│   ├── LoginPage.tsx
│   ├── RepositoriesPage.tsx
│   ├── RepositoryDetailPage.tsx
│   ├── ReleasesPage.tsx
│   └── SettingsPage.tsx
├── store/              # 状态管理
│   └── useAppStore.ts  # Zustand store
├── types/              # TypeScript 类型定义
│   └── index.ts
├── lib/                # 工具函数
└── App.tsx             # 应用入口
```

## 数据持久化

应用使用 Zustand 的持久化中间件将以下数据存储在浏览器本地：
- 用户信息和认证状态
- 仓库数据
- 自定义分类
- 过滤器配置
- AI 和 WebDAV 配置
- 应用设置

**重要提示**：建议配置 WebDAV 备份以防数据丢失。

## 后端集成

本前端应用设计用于与 GitHubStarsManager 的 SQLite 后端服务集成。

### 后端服务包括：
- SQLite 数据库架构
- DAO 数据访问层
- GitHub API 集成服务
- AI API 集成服务
- WebDAV 备份服务

### 集成方式
前端通过 REST API 或直接数据库连接与后端服务通信（具体方式取决于后端实现）。

## 开发说明

### 添加新页面
1. 在 `src/pages/` 创建页面组件
2. 在 `src/App.tsx` 添加路由配置

### 添加新的状态
1. 在 `src/types/index.ts` 定义类型
2. 在 `src/store/useAppStore.ts` 添加状态和 actions

### 添加 UI 组件
使用 Shadcn CLI 添加组件：
```bash
npx shadcn@latest add [component-name]
```

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## 许可证

MIT License

## 致谢

- 基于 [GitHubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager) 项目设计
- UI 组件来自 [Shadcn/UI](https://ui.shadcn.com/)
- 图标来自 [Lucide](https://lucide.dev/)
