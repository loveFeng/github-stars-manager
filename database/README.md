# GitHub Stars Manager 数据库服务

## 概述

本数据库服务为 GitHub Stars Manager 桌面应用提供完整的 SQLite 数据库操作功能，包括用户管理、仓库管理、发布版本管理、分类管理、备份同步等功能。

## 特性

### 🔧 核心功能
- **连接管理**: 自动连接池管理和 WAL 模式优化
- **事务支持**: 完整的事务管理和回滚机制
- **迁移系统**: 版本控制和自动迁移功能
- **加密存储**: 敏感数据 AES-256-GCM 加密
- **全文搜索**: SQLite FTS5 支持高效搜索
- **性能优化**: 索引优化和查询优化

### 📊 数据管理
- **用户管理**: GitHub 用户信息存储和认证
- **仓库管理**: 仓库信息同步和分类管理
- **发布管理**: 版本发布和资产文件管理
- **配置管理**: 应用设置和外部服务配置
- **备份恢复**: 自动备份和恢复功能

### 🔒 安全特性
- 敏感数据加密存储
- SQL 注入防护
- 数据完整性检查
- 事务回滚保护

## 快速开始

### 安装依赖

```bash
npm install sqlite3 @types/sqlite3 sqlite
```

### 初始化数据库

```typescript
import { DatabaseManager } from './database/dao/database_manager';
import { DatabaseMigrator } from './database/migration/migrator';
import { SQLiteConnectionManager } from './services/database_service';

// 配置数据库
const dbConfig = {
  filename: './data/github_stars_manager.db',
  walMode: true,
  cacheSize: 20000,
  synchronousMode: 'NORMAL'
};

// 初始化
const db = new SQLiteConnectionManager(dbConfig);
const dbManager = new DatabaseManager(db);
const migrator = new DatabaseMigrator(db);

async function initializeDatabase() {
  // 连接数据库
  await db.connect();
  
  // 初始化迁移系统
  await migrator.initialize();
  
  // 执行迁移
  await migrator.migrate();
  
  console.log('数据库初始化完成！');
}
```

### 基本使用

```typescript
// 创建用户
const user = await dbManager.userDAO.create({
  github_id: 123456,
  username: 'john_doe',
  email: 'john@example.com',
  avatar_url: 'https://avatars.githubusercontent.com/u/123456'
});

// 创建仓库
const repository = await dbManager.repositoryDAO.create({
  github_id: 654321,
  owner: 'octocat',
  name: 'Hello-World',
  full_name: 'octocat/Hello-World',
  description: '我的第一个仓库',
  html_url: 'https://github.com/octocat/Hello-World',
  stars_count: 42,
  language: 'JavaScript'
});

// 分页查询仓库
const repos = await dbManager.repositoryDAO.findPaginated({
  page: 1,
  limit: 20,
  sortBy: 'stars_count',
  sortOrder: 'DESC'
});

console.log(`找到 ${repos.total} 个仓库`);
```

## 详细文档

### 数据库架构

#### 核心表结构

| 表名 | 描述 | 主要字段 |
|------|------|----------|
| `users` | GitHub 用户信息 | github_id, username, access_token, email |
| `repositories` | 仓库信息 | github_id, owner, name, full_name, stars_count |
| `categories` | 仓库分类 | name, description, color, parent_id |
| `repository_categories` | 仓库分类关联 | repository_id, category_id |
| `releases` | 发布版本 | github_id, repository_id, tag_name, name |
| `release_assets` | 发布资产 | github_id, release_id, name, download_url |
| `asset_filters` | 资产过滤器 | name, regex_pattern, match_rules |
| `ai_configs` | AI 配置 | provider, api_key_encrypted, model |
| `webdav_configs` | WebDAV 配置 | url, username_encrypted, password_encrypted |
| `app_settings` | 应用设置 | key, value, data_type |

#### 索引和性能

- 主要字段都有相应的索引
- 使用 FTS5 实现全文搜索
- 优化的连接查询和外键约束
- WAL 模式提高并发性能

### DAO 层使用

#### 用户 DAO (UserDAO)

```typescript
// 创建用户
const user = await dbManager.userDAO.create({
  github_id: 123456,
  username: 'john_doe',
  email: 'john@example.com'
});

// 根据 GitHub ID 查找
const user = await dbManager.userDAO.findByGithubId(123456);

// 根据用户名查找
const user = await dbManager.userDAO.findByUsername('john_doe');

// 更新访问令牌
await dbManager.userDAO.updateToken(123456, 'encrypted_token', expiresAt);

// 认证用户
const isValid = await dbManager.userDAO.authenticate('john_doe', 'password');
```

#### 仓库 DAO (RepositoryDAO)

```typescript
// 创建仓库
const repo = await dbManager.repositoryDAO.create({
  github_id: 654321,
  owner: 'octocat',
  name: 'Hello-World',
  full_name: 'octocat/Hello-World',
  stars_count: 42
});

// 查找所有仓库
const repos = await dbManager.repositoryDAO.findAll({
  limit: 50,
  sortBy: 'stars_count',
  sortOrder: 'DESC'
});

// 关键词搜索
const searchResults = await dbManager.repositoryDAO.searchByKeyword('React');

// 按所有者查找
const ownerRepos = await dbManager.repositoryDAO.findByOwner('facebook');

// 更新统计信息
await dbManager.repositoryDAO.updateStats(654321, {
  stars_count: 100,
  forks_count: 20
});
```

#### 分类 DAO (CategoryDAO)

```typescript
// 创建分类
const category = await dbManager.categoryDAO.create({
  name: '前端框架',
  description: 'React、Vue、Angular 等',
  color: '#61dafb',
  sort_order: 1
});

// 获取默认分类
const defaultCategory = await dbManager.categoryDAO.findDefault();

// 获取子分类
const children = await dbManager.categoryDAO.findChildren(parentId);

// 更新排序
await this.dbManager.categoryDAO.updateSortOrder([
  { id: 1, sort_order: 1 },
  { id: 2, sort_order: 2 }
]);
```

#### 发布和资产 DAO

```typescript
// 创建发布版本
const release = await dbManager.releaseDAO.create({
  github_id: 987654,
  repository_id: 1,
  tag_name: 'v1.0.0',
  name: '第一个版本',
  body: '版本说明',
  published_at: new Date().toISOString()
});

// 创建发布资产
const asset = await dbManager.releaseAssetDAO.create({
  github_id: 111111,
  release_id: release.id!,
  name: 'app-1.0.0.exe',
  download_url: 'https://example.com/app-1.0.0.exe',
  size: 1024000,
  content_type: 'application/x-msdownload'
});

// 标记为已下载
await dbManager.releaseAssetDAO.markAsDownloaded(asset.id!);

// 查找未读发布
const unreadReleases = await dbManager.releaseDAO.findUnread(10);
```

#### 资产过滤器 DAO

```typescript
// 创建过滤器
const filter = await dbManager.assetFilterDAO.create({
  name: 'Windows 安装包',
  regex_pattern: '.*\\.exe$',
  match_rules: JSON.stringify([
    { field: 'content_type', operator: 'contains', value: 'application' }
  ]),
  is_active: true,
  priority: 1
});

// 获取活跃过滤器
const activeFilters = await dbManager.assetFilterDAO.findActive();

// 测试资产匹配
const matchResult = await dbManager.assetFilterDAO.matchAsset({
  name: 'setup.exe',
  content_type: 'application/x-msdownload'
});
```

#### 应用设置 DAO

```typescript
// 设置各种类型配置
await dbManager.appSettingDAO.setSetting('theme', 'dark', 'string', '界面主题');
await dbManager.appSettingDAO.setSetting('auto_sync', true, 'boolean', '自动同步');
await dbManager.appSettingDAO.setSetting('sync_interval', 30, 'number', '同步间隔');

// 获取配置
const theme = await dbManager.appSettingDAO.getString('theme');
const autoSync = await dbManager.appSettingDAO.getBoolean('auto_sync');
const interval = await dbManager.appSettingDAO.getNumber('sync_interval');

// 获取 JSON 配置
const config = await dbManager.appSettingDAO.getJSON('ui_layout');
```

### 事务管理

```typescript
// 使用事务
await db.executeInTransaction(async (tx) => {
  // 创建用户
  const user = await dbManager.userDAO.create({
    github_id: 123456,
    username: 'test_user',
    email: 'test@example.com'
  });

  // 创建仓库
  const repo = await dbManager.repositoryDAO.create({
    github_id: 654321,
    owner: user.username,
    name: 'test_repo',
    full_name: `${user.username}/test_repo`
  });

  // 分配分类
  const defaultCategory = await dbManager.categoryDAO.findDefault();
  await dbManager.repositoryCategoryDAO.addCategory(repo.id!, defaultCategory!.id!);

  return { user, repo };
});
```

### 数据库迁移

```typescript
// 检查迁移状态
const status = await migrator.getStatus();
console.log(`当前版本: ${status.currentVersion}`);
console.log(`待执行迁移: ${status.pendingMigrations.length}`);

// 执行迁移
const results = await migrator.migrate('1.1.0');
results.forEach(result => {
  if (result.success) {
    console.log(`✅ ${result.migration?.version} 迁移成功`);
  } else {
    console.log(`❌ ${result.migration?.version} 迁移失败: ${result.error}`);
  }
});

// 回滚到指定版本
await migrator.rollbackToVersion('1.0.0');

// 创建新的迁移
migrator.createMigration('1.1.0', '添加新功能', `
  ALTER TABLE repositories ADD COLUMN new_feature TEXT;
  CREATE INDEX idx_new_feature ON repositories(new_feature);
`);
```

### 全文搜索

```typescript
// 搜索仓库
const vueRepos = await dbManager.repositoryDAO.searchByKeyword('Vue');

// 搜索发布
const releaseResults = await dbManager.releaseDAO.searchByKeyword('版本');

// 搜索包含特定语言的仓库
const jsRepos = await dbManager.repositoryDAO.findByLanguage('JavaScript');
```

### 数据备份

```typescript
// 创建备份
const backupPath = './backups/backup_' + Date.now() + '.db';
await db.backup(backupPath);

// 获取数据库统计
const stats = await dbManager.repositoryDAO.getTableStats();
console.log(`总记录数: ${stats.total_rows}`);
```

### 性能优化

#### 批量操作

```typescript
// 批量创建
const users = await dbManager.userDAO.createBatch([
  { github_id: 1, username: 'user1' },
  { github_id: 2, username: 'user2' },
  { github_id: 3, username: 'user3' }
]);

// 批量更新
const updates = await dbManager.userDAO.updateBatch([
  { id: 1, data: { email: 'user1@example.com' } },
  { id: 2, data: { email: 'user2@example.com' } }
]);

// 批量删除
const deleted = await dbManager.userDAO.deleteBatch([1, 2, 3]);
```

#### 分页查询

```typescript
// 获取分页结果
const page = await dbManager.repositoryDAO.findPaginated({
  page: 1,        // 页码 (1开始)
  limit: 20,      // 每页数量
  sortBy: 'stars_count',  // 排序字段
  sortOrder: 'DESC',      // 排序方向
  query: 'React',         // 搜索关键词
  searchFields: ['name', 'description']  // 搜索字段
});

console.log(`第 ${page.page} 页，共 ${page.totalPages} 页，总计 ${page.total} 条记录`);
```

## 错误处理

```typescript
try {
  const user = await dbManager.userDAO.create(userData);
} catch (error) {
  if (error instanceof DAOException) {
    switch (error.code) {
      case 'CREATE_FAILED':
        console.error('创建用户失败:', error.message);
        break;
      case 'DUPLICATE_ENTRY':
        console.error('用户已存在:', error.message);
        break;
      default:
        console.error('未知错误:', error.message);
    }
  } else {
    console.error('系统错误:', error);
  }
}
```

## 配置选项

### 数据库配置

```typescript
const dbConfig = {
  filename: './data/app.db',     // 数据库文件路径
  mode: OPEN_READWRITE | OPEN_CREATE,  // 打开模式
  timeout: 30000,                // 连接超时时间
  verbose: false,                // 是否启用详细日志
  walMode: true,                 // 启用 WAL 模式
  cacheSize: 20000,              // 缓存大小
  synchronousMode: 'NORMAL'      // 同步模式
};
```

### FTS5 配置

系统自动创建 FTS5 虚拟表用于全文搜索：

- `repositories_fts`: 仓库全文搜索
- `releases_fts`: 发布版本全文搜索

### 加密配置

敏感数据使用 AES-256-GCM 加密：

- API 密钥
- 访问令牌
- 密码
- 其他认证信息

## 监控和日志

### 性能监控

```typescript
// 获取连接指标
const metrics = await db.getMetrics();
console.log('连接数:', metrics.totalConnections);
console.log('活跃连接:', metrics.activeConnections);
console.log('平均查询时间:', metrics.averageQueryTime);
```

### 慢查询监控

```typescript
// 设置慢查询阈值
db.setSlowQueryThreshold(1000); // 1秒

// 监听慢查询事件
db.on('slowQuery', (query, time) => {
  console.log(`慢查询检测: ${query} (${time}ms)`);
});
```

## 故障排除

### 常见问题

1. **数据库锁定**
   - 确保 WAL 模式已启用
   - 检查是否有未关闭的连接
   - 等待操作完成或重启应用

2. **内存使用过高**
   - 调整 `cacheSize` 配置
   - 使用分页查询代替一次性查询大量数据

3. **迁移失败**
   - 检查迁移脚本语法
   - 确保有足够的磁盘空间
   - 查看具体错误信息进行修复

### 调试模式

```typescript
const dbConfig = {
  filename: './debug.db',
  verbose: true,  // 启用详细日志
  walMode: true
};

// 监听查询事件
db.on('query', (sql, params) => {
  console.log('SQL:', sql, '参数:', params);
});

db.on('result', (data) => {
  console.log('结果:', data);
});
```

## 最佳实践

1. **连接管理**
   - 使用连接池管理连接
   - 及时关闭连接
   - 设置合适的超时时间

2. **查询优化**
   - 使用索引优化查询性能
   - 避免 N+1 查询问题
   - 使用分页查询大数据集

3. **事务处理**
   - 保持事务简短
   - 合理使用事务边界
   - 处理事务失败情况

4. **数据安全**
   - 加密敏感数据
   - 验证输入数据
   - 定期备份数据

5. **错误处理**
   - 使用自定义异常类型
   - 提供详细的错误信息
   - 实现错误恢复机制

## 示例代码

完整的使用示例请参考 `/examples/database_usage.ts` 文件，该文件包含了所有主要功能的演示代码。

## 许可证

本项目采用 MIT 许可证。详情请参阅 LICENSE 文件。