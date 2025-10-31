# GitHub 提交指南

## 🚀 快速提交到 GitHub

### 1. 初始化 Git 仓库（如果还没有）

```bash
# 在项目根目录初始化 Git
git init

# 添加所有文件
git add .

# 首次提交
git commit -m "feat: 初始版本 - GitHub Stars Manager SQLite版

✨ 核心功能:
- SQLite 数据库架构设计
- AI 智能仓库分析
- WebDAV 远程备份
- Docker 容器化部署
- 跨平台兼容性
- 性能优化 (70%+ 提升)

📊 技术栈:
- 前端: React 18.3 + TypeScript + Tailwind CSS
- 后端: Python + Node.js
- 数据库: SQLite + FTS5
- 部署: Docker Compose

🌐 在线演示: https://unkmn8l5lzrt.space.minimax.io"
```

### 2. 创建 GitHub 仓库

在 GitHub 上创建一个新的仓库，仓库名为：`github-stars-manager`

### 3. 关联远程仓库

```bash
# 关联 GitHub 仓库（替换 your-username 为您的 GitHub 用户名）
git remote add origin https://github.com/loveFeng/github-stars-manager.git

# 设置默认分支
git branch -M main

# 推送到 GitHub
git push -u origin main
```

### 4. 创建 Release 版本

```bash
# 创建标签
git tag -a v2.0.0 -m "Release v2.0.0 - 完整功能版本

🎉 特性:
✅ SQLite 数据库迁移
✅ AI 驱动分析
✅ WebDAV 备份集成  
✅ Docker 容器化
✅ 性能优化 70%+
✅ 跨平台兼容
✅ 生产环境就绪

🌐 在线地址: https://unkmn8l5lzrt.space.minimax.io"

# 推送标签
git push origin v2.0.0
```

## 📝 提交规范

### 提交信息格式

```
type(scope): description

[optional body]

[optional footer]
```

### 提交类型

- **feat**: 新功能
- **fix**: 错误修复
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 代码重构
- **test**: 测试相关
- **chore**: 构建或辅助工具变动

### 示例

```bash
# 新功能
git commit -m "feat(database): 添加FTS5全文搜索支持

- 实现仓库描述和README的全文搜索
- 添加搜索索引和优化查询性能
- 支持中文搜索和语义匹配"

# 错误修复
git commit -m "fix(frontend): 修复Windows系统下路径问题

- 替换rm -rf命令为rimraf
- 添加跨平台兼容性处理"

# 文档更新
git commit -m "docs: 更新安装指南和部署文档

- 添加Windows和macOS详细安装步骤
- 完善Docker部署配置说明
- 添加常见问题解答"
```

## 🏷️ 版本标签管理

### 语义化版本

- **主版本号** (X.y.z): 不兼容的 API 变更
- **次版本号** (x.Y.z): 向后兼容的功能性新增
- **修订版本号** (x.y.Z): 向后兼容的问题修正

### 标签管理

```bash
# 查看所有标签
git tag

# 创建注释标签
git tag -a v1.0.0 -m "初始发布版本"

# 推送所有标签
git push origin --tags

# 删除本地标签
git tag -d v1.0.0

# 删除远程标签
git push origin --delete v1.0.0
```

## 🔧 分支管理策略

### 主分支

- **main**: 主分支，始终保持稳定可发布状态
- **develop**: 开发分支，集成最新开发功能

### 功能分支

```bash
# 创建功能分支
git checkout -b feature/ai-analysis

# 开发完成后合并到develop
git checkout develop
git merge feature/ai-analysis
git branch -d feature/ai-analysis

# 推送到远程
git push origin develop
```

### 发布分支

```bash
# 创建发布分支
git checkout -b release/v2.1.0

# 完成后合并到main和develop
git checkout main
git merge release/v2.1.0
git tag v2.1.0

git checkout develop  
git merge release/v2.1.0

# 清理分支
git branch -d release/v2.1.0
```

## 📦 .gitignore 配置

创建 `.gitignore` 文件：

```gitignore
# Dependencies
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids/
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Backup files
*.backup
*.bak
```

## 🎯 GitHub 仓库设置

### 1. 添加仓库描述

```
强大的 GitHub 星标仓库管理系统 | SQLite + AI + Docker

✨ 特性: 智能同步、AI分析、WebDAV备份、跨平台兼容
🐳 部署: Docker Compose + 在线演示
📊 性能: 70%+ 优化提升
🌐 在线: https://unkmn8l5lzrt.space.minimax.io
```

### 2. 添加 Topics/标签

```
github-stars-manager
react
typescript
sqlite
docker
ai-analysis
webdav-backup
github-api
cross-platform
performance-optimization
```

### 3. 启用功能

- ✅ Issues（问题追踪）
- ✅ Wiki（文档）
- ✅ Projects（项目管理）
- ✅ Discussions（社区讨论）

### 4. 配置分支保护

为 `main` 分支设置：
- 要求 Pull Request 审查
- 要求状态检查通过
- 限制推送到 main 分支

## 🚀 持续集成 (可选)

创建 `.github/workflows/ci.yml`：

```yaml
name: CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [16.x, 18.x, 20.x]
        
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm test
    
    - name: Build
      run: npm run build
    
    - name: Build Docker image
      run: docker build -t github-stars-manager .
```

## 📋 提交检查清单

提交前请检查：

- [ ] 代码已经测试通过
- [ ] 遵循提交信息规范
- [ ] 更新相关文档
- [ ] 检查是否有敏感信息泄露
- [ ] 运行 linting 和格式化工具
- [ ] 更新版本号（如果需要）

完成上述步骤后，您的项目将成功提交到 GitHub！🎉
