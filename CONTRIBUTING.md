# 贡献指南

感谢您对 GitHub Stars Manager 项目的兴趣！我们欢迎所有形式的贡献。

## 🚀 开始贡献

### 开发环境设置

1. **Fork 仓库**
   ```bash
   # 访问 https://github.com/loveFeng/github-stars-manager
   # 点击 "Fork" 按钮
   ```

2. **克隆您的 Fork**
   ```bash
   git clone https://github.com/loveFeng/github-stars-manager.git
   cd github-stars-manager-sqlite
   ```

3. **设置上游分支**
   ```bash
   git remote add upstream https://github.com/loveFeng/github-stars-manager.git
   ```

### 本地开发设置

```bash
# 安装依赖
cd github-stars-manager-frontend && npm install
cd ../backend && npm install
cd ../services && pip install -r requirements.txt

# 初始化数据库
cd database && npm run init

# 启动开发服务
npm run dev:all
```

## 📋 开发规范

### 代码风格

- **TypeScript/JavaScript**: 使用 ESLint + Prettier 配置
- **Python**: 遵循 PEP 8 规范，使用 Black 格式化
- **SQL**: 使用大写关键词和明确的命名约定
- **CSS**: 使用 Tailwind CSS 类名和设计系统

### 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 功能新增
feat(ui): 添加仓库搜索过滤器

# 错误修复
fix(api): 修复GitHub API速率限制问题

# 文档更新
docs(api): 更新API文档和示例

# 重构代码
refactor(database): 优化查询性能

# 测试相关
test(ai): 添加AI分析单元测试

# 构建相关
build(docker): 更新生产环境配置

# 持续集成
ci(workflow): 添加自动测试工作流
```

### 分支管理策略

```
main (生产分支)
├── develop (开发分支)
│   ├── feature/新功能分支
│   ├── bugfix/错误修复分支
│   └── hotfix/紧急修复分支
└── release/v版本号 (发布分支)
```

#### 创建功能分支

```bash
# 从develop分支创建
git checkout develop
git pull upstream develop
git checkout -b feature/仓库标签系统

# 开发完成后
git push origin feature/仓库标签系统
```

#### 合并流程

1. 创建 Pull Request 到 `develop` 分支
2. 等待代码审查
3. 合并到 `develop`
4. 发布时合并到 `main`

## 🧪 测试要求

### 测试覆盖率要求

- **最低覆盖率**: 80%
- **核心功能**: 95%+
- **新增功能**: 必须包含测试

### 运行测试

```bash
# 前端测试
cd github-stars-manager-frontend
npm test
npm run test:coverage

# 后端测试
cd backend
npm test

# 数据库测试
cd database
npm run test

# 集成测试
npm run test:integration

# 性能测试
npm run test:performance
```

### 测试类型

- **单元测试**: 组件和服务级别的测试
- **集成测试**: API 和数据库交互测试
- **端到端测试**: 完整用户流程测试
- **性能测试**: 加载时间和内存使用测试

## 🐛 报告问题

### 提 Issue

在创建 Issue 时，请包含：

1. **问题描述**: 清晰描述遇到的问题
2. **重现步骤**: 详细的操作步骤
3. **期望行为**: 您期望的结果
4. **实际行为**: 实际发生的结果
5. **环境信息**:
   - 操作系统
   - 浏览器版本
   - Node.js 版本
   - Docker 版本

#### Issue 模板

```markdown
## 问题描述
简要描述问题

## 重现步骤
1. 执行 ...
2. 点击 ...
3. 滚动到 ...
4. 看到错误

## 期望行为
描述您期望发生的事情

## 实际行为
描述实际发生的事情

## 环境信息
- OS: [e.g. macOS 12.0]
- Browser: [e.g. Chrome 95.0]
- Node.js: [e.g. 16.13.0]
- Docker: [e.g. 20.10]

## 截图/日志
如果适用，请添加截图或相关日志
```

## 🔧 拉取请求

### PR 流程

1. **确保分支最新**
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout feature/your-feature
   git rebase develop
   ```

2. **运行完整测试**
   ```bash
   npm run test:all
   npm run lint
   npm run build
   ```

3. **提交 PR**
   - 清晰的标题和描述
   - 链接相关 Issue
   - 添加测试
   - 更新文档

#### PR 模板

```markdown
## 🎯 变更类型
- [ ] 🐛 Bug 修复
- [ ] ✨ 新功能
- [ ] 💥 破坏性变更
- [ ] 📚 文档更新
- [ ] 🎨 代码风格改进
- [ ] ♻️ 重构
- [ ] ✅ 测试
- [ ] 🔧 构建工具
- [ ] ♾️ 持续集成

## 📝 变更描述
清晰描述本次变更

## 🔍 变更类型详情

### 修复的问题
列出修复的所有问题 (e.g. fixes #123)

### 新增功能
列出新增的所有功能

### 破坏性变更
如果存在破坏性变更，描述影响

## 📊 测试
- [ ] 单元测试已更新
- [ ] 集成测试已更新  
- [ ] 端到端测试已更新
- [ ] 手动测试完成

## 📸 截图 (如适用)
添加相关截图

## 📋 检查清单
- [ ] 代码遵循项目规范
- [ ] 已运行所有测试
- [ ] 已更新相关文档
- [ ] 已添加必要的注释
- [ ] 已检查性能和可访问性
```

## 🏗️ 架构指南

### 项目结构

```
github-stars-manager-sqlite/
├── github-stars-manager-frontend/  # React 前端
│   ├── src/components/            # 可复用组件
│   ├── src/pages/                 # 页面组件
│   ├── src/store/                 # 状态管理
│   └── src/utils/                 # 工具函数
├── backend/                       # Node.js 后端
│   ├── src/routes/                # API 路由
│   ├── src/services/              # 业务逻辑
│   └── src/middleware/            # 中间件
├── database/                      # SQLite 架构
│   ├── dao/                       # 数据访问对象
│   ├── migration/                 # 迁移脚本
│   └── types.ts                   # 类型定义
├── services/                      # Python 服务
│   ├── ai_service.py              # AI 分析服务
│   ├── github_service.py          # GitHub API 服务
│   ├── sync_service.py            # 同步服务
│   └── backup_manager.py          # 备份管理
└── Docker/                        # 容器化配置
    ├── docker-compose.yml         # 开发环境
    └── docker-compose.prod.yml    # 生产环境
```

### 最佳实践

#### React 组件
```typescript
// ✅ 好的示例
interface RepositoryCardProps {
  repository: Repository;
  onAnalyze?: (repo: Repository) => void;
}

export const RepositoryCard: React.FC<RepositoryCardProps> = ({ 
  repository, 
  onAnalyze 
}) => {
  const handleClick = useCallback(() => {
    onAnalyze?.(repository);
  }, [repository, onAnalyze]);

  return (
    <div className="card" onClick={handleClick}>
      {/* 组件内容 */}
    </div>
  );
};
```

#### Python 服务
```python
# ✅ 好的示例
class GitHubService:
    def __init__(self, token: str, rate_limiter: RateLimiter):
        self.token = token
        self.rate_limiter = rate_limiter
        self.logger = get_logger(__name__)

    async def get_starred_repos(
        self, 
        page: int = 1, 
        per_page: int = 30
    ) -> List[Repository]:
        """获取星标仓库列表
        
        Args:
            page: 页码
            per_page: 每页数量
            
        Returns:
            Repository 列表
            
        Raises:
            GitHubAPIException: API 调用失败
        """
        # 实现逻辑
```

#### 数据库访问
```typescript
// ✅ 好的示例
export class RepositoryDAO extends BaseDAO<Repository, RepositoryInsert> {
  constructor(db: DatabaseConnection) {
    super('repositories', RepositorySchema, db);
  }

  async findByOwnerAndName(
    owner: string, 
    name: string
  ): Promise<Repository | null> {
    return await this.findOne({ owner, name });
  }

  async searchByKeyword(keyword: string): Promise<Repository[]> {
    return await this.db.searchFTS('repositories_fts', keyword);
  }
}
```

## 📚 文档要求

### 更新文档

- **新增功能**: 更新相关文档
- **API 变更**: 更新 API 文档
- **配置变更**: 更新配置指南
- **破坏性变更**: 添加迁移指南

### 文档位置

- **用户指南**: `/docs/user-guide/`
- **API 文档**: `/docs/api/`
- **开发指南**: `/docs/development/`
- **部署指南**: `/Docker/README.md`

## 🎯 发布流程

### 版本号规则

遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号** (X.y.z): 不兼容的 API 变更
- **次版本号** (x.Y.z): 向后兼容的功能性新增  
- **修订版本号** (x.y.Z): 向后兼容的问题修正

### 发布步骤

1. **合并到 main**
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```

2. **创建发布标签**
   ```bash
   git tag -a v2.1.0 -m "Release v2.1.0

   ✨ 新功能:
   - 仓库标签系统
   - AI 智能推荐
   - 批量操作支持

   🐛 修复:
   - 修复 Docker 部署问题
   - 优化搜索性能
   "
   git push origin v2.1.0
   ```

3. **创建 Release**
   - 在 GitHub 创建新的 Release
   - 添加变更日志
   - 添加下载链接

## 📞 获取帮助

### 联系方式

- **GitHub Discussions**: 技术讨论和 Q&A
- **GitHub Issues**: 问题报告和功能请求
- **Wiki**: 详细文档和指南

### 社区规范

- **友善和包容**: 尊重所有贡献者
- **建设性反馈**: 提供有用的建议
- **问题解决**: 协作解决问题
- **文档优先**: 优先更新文档

## 🙏 致谢

感谢所有为项目做出贡献的开发者！

- **贡献者列表**: 将在发布说明中列出
- **特别鸣谢**: 核心维护者和主要贡献者
- **测试贡献**: 参与测试的用户

---

再次感谢您的贡献！🚀
