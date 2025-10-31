# GitHubStarsManager SQLite 数据库架构设计

## 1. 设计概述

基于对 GitHubStarsManager 项目的深度分析，设计一套完整的 SQLite 数据库架构，用于存储和管理用户的 GitHub 星标仓库、AI 分析结果、Release 信息、分类、过滤器、设置等数据。该设计支持桌面应用的数据持久化，并为后续功能扩展提供可扩展性。

## 2. 核心数据实体

### 2.1 用户与认证 (User & Authentication)
- **用户信息**: GitHub 账户基本信息
- **认证状态**: Token 管理与会话状态
- **偏好设置**: UI 主题、语言等

### 2.2 仓库管理 (Repository Management) 
- **星标仓库**: GitHub 仓库详细信息
- **AI 分析结果**: 自动生成的摘要、分类、标签
- **手动编辑**: 用户自定义元数据

### 2.3 发布管理 (Release Management)
- **Release 信息**: 仓库版本发布数据
- **订阅管理**: 用户关注的仓库发布
- **文件资产**: 发布包文件信息

### 2.4 分类与过滤 (Categories & Filters)
- **分类系统**: 默认和自定义分类
- **过滤器**: 资产过滤规则
- **搜索索引**: 语义搜索优化

### 2.5 备份与同步 (Backup & Sync)
- **WebDAV 配置**: 云端备份设置
- **同步状态**: 最后同步时间与状态
- **数据导出**: 备份记录

## 3. 数据库表结构设计

### 3.1 users - 用户表
存储用户基本信息和认证状态。

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_id INTEGER UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    avatar_url TEXT,
    github_token_encrypted TEXT, -- 加密存储
    is_authenticated BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 repositories - 仓库表
存储 GitHub 星标仓库的详细信息。

```sql
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_id INTEGER UNIQUE NOT NULL,
    owner VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL, -- owner/name
    description TEXT,
    html_url TEXT NOT NULL,
    clone_url TEXT,
    ssh_url TEXT,
    language VARCHAR(100),
    languages TEXT, -- JSON: 其他语言占比
    topics TEXT, -- JSON: 仓库标签
    stars_count INTEGER DEFAULT 0,
    forks_count INTEGER DEFAULT 0,
    watchers_count INTEGER DEFAULT 0,
    open_issues_count INTEGER DEFAULT 0,
    size_kb INTEGER DEFAULT 0,
    license VARCHAR(100),
    default_branch VARCHAR(100),
    archived BOOLEAN DEFAULT 0,
    disabled BOOLEAN DEFAULT 0,
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_notes TEXT, -- 用户备注
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5), -- 用户评分
    is_private BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 复合唯一约束
    UNIQUE(owner, name)
);
```

### 3.3 ai_analysis_results - AI 分析结果表
存储 AI 对仓库的分析结果。

```sql
CREATE TABLE ai_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    analysis_type VARCHAR(50) NOT NULL, -- 'summary', 'category', 'tags', 'platform_support'
    ai_model VARCHAR(100) NOT NULL,
    input_prompt TEXT NOT NULL,
    analysis_result TEXT NOT NULL, -- JSON: 分析结果
    confidence_score DECIMAL(3,2), -- 置信度 0.00-1.00
    tokens_used INTEGER DEFAULT 0,
    processing_time_ms INTEGER DEFAULT 0,
    is_validated BOOLEAN DEFAULT 0, -- 是否经过人工验证
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
    UNIQUE(repository_id, analysis_type, ai_model)
);
```

### 3.4 categories - 分类表
存储仓库分类信息。

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3B82F6', -- 十六进制颜色值
    icon VARCHAR(50), -- 图标名称
    is_default BOOLEAN DEFAULT 0, -- 是否为默认分类
    sort_order INTEGER DEFAULT 0,
    parent_id INTEGER, -- 支持层级分类
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(name, parent_id)
);
```

### 3.5 repository_categories - 仓库分类关联表
多对多关系：仓库与分类的关联。

```sql
CREATE TABLE repository_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    confidence DECIMAL(3,2), -- AI 分类置信度
    is_auto_generated BOOLEAN DEFAULT 0, -- 是否为 AI 自动分类
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(repository_id, category_id)
);
```

### 3.6 releases - Release 表
存储仓库的发布版本信息。

```sql
CREATE TABLE releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_release_id INTEGER UNIQUE NOT NULL,
    repository_id INTEGER NOT NULL,
    tag_name VARCHAR(255) NOT NULL,
    name VARCHAR(500),
    body TEXT, -- 发布说明
    draft BOOLEAN DEFAULT 0,
    prerelease BOOLEAN DEFAULT 0,
    created_at DATETIME,
    published_at DATETIME,
    html_url TEXT NOT NULL,
    zipball_url TEXT,
    tarball_url TEXT,
    target_commitish VARCHAR(255),
    author_login VARCHAR(255),
    author_avatar_url TEXT,
    is_subscribed BOOLEAN DEFAULT 0, -- 用户是否订阅
    is_read BOOLEAN DEFAULT 0, -- 是否已读
    user_notes TEXT, -- 用户备注
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
);
```

### 3.7 release_assets - Release 资产表
存储 Release 的文件资产信息。

```sql
CREATE TABLE release_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_asset_id INTEGER UNIQUE NOT NULL,
    release_id INTEGER NOT NULL,
    name VARCHAR(500) NOT NULL,
    label VARCHAR(500),
    content_type VARCHAR(100),
    size_bytes INTEGER NOT NULL,
    download_count INTEGER DEFAULT 0,
    browser_download_url TEXT NOT NULL,
    created_at DATETIME,
    is_downloaded BOOLEAN DEFAULT 0, -- 是否已下载
    local_path TEXT, -- 本地下载路径
    download_time DATETIME,
    file_hash VARCHAR(64), -- SHA256 哈希值
    user_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (release_id) REFERENCES releases(id) ON DELETE CASCADE
);
```

### 3.8 asset_filters - 资产过滤器表
存储用户自定义的资产过滤规则。

```sql
CREATE TABLE asset_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords TEXT NOT NULL, -- JSON: 关键词数组
    match_type VARCHAR(20) DEFAULT 'keyword', -- 'keyword', 'regex', 'extension'
    case_sensitive BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    user_id INTEGER, -- 如果为空则为全局过滤器
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 3.9 filter_matches - 过滤器匹配记录表
记录过滤器与资产的匹配历史。

```sql
CREATE TABLE filter_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    match_score DECIMAL(3,2), -- 匹配度评分
    matched_keywords TEXT, -- JSON: 匹配的关键词
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (filter_id) REFERENCES asset_filters(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES release_assets(id) ON DELETE CASCADE,
    UNIQUE(filter_id, asset_id)
);
```

### 3.10 ai_configs - AI 配置表
存储 AI 模型配置信息。

```sql
CREATE TABLE ai_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    api_url TEXT NOT NULL,
    api_key_encrypted TEXT, -- 加密存储
    model_name VARCHAR(255) NOT NULL,
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(2,1) DEFAULT 0.7,
    timeout_seconds INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT 0,
    is_default BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name)
);
```

### 3.11 webdav_configs - WebDAV 配置表
存储 WebDAV 备份配置。

```sql
CREATE TABLE webdav_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    server_url TEXT NOT NULL,
    username VARCHAR(255),
    password_encrypted TEXT, -- 加密存储
    remote_path VARCHAR(500) DEFAULT '/GithubStarsManager',
    is_active BOOLEAN DEFAULT 0,
    is_default BOOLEAN DEFAULT 0,
    last_sync_at DATETIME,
    sync_status VARCHAR(50), -- 'success', 'failed', 'in_progress'
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name)
);
```

### 3.12 sync_logs - 同步日志表
记录各类同步操作日志。

```sql
CREATE TABLE sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type VARCHAR(50) NOT NULL, -- 'repositories', 'releases', 'backup'
    status VARCHAR(20) NOT NULL, -- 'started', 'success', 'failed', 'cancelled'
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    items_processed INTEGER DEFAULT 0,
    items_added INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_ms INTEGER,
    user_id INTEGER,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

### 3.13 search_index - 搜索索引表
为语义搜索建立索引。

```sql
CREATE TABLE search_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type VARCHAR(50) NOT NULL, -- 'repository', 'release', 'asset'
    entity_id INTEGER NOT NULL,
    content_type VARCHAR(50) NOT NULL, -- 'name', 'description', 'summary', 'tags'
    content_text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'zh',
    keywords TEXT, -- JSON: 提取的关键词
    embedding_vector BLOB, -- 向量嵌入（如果支持）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 复合索引
    UNIQUE(entity_type, entity_id, content_type)
);
```

### 3.14 app_settings - 应用设置表
存储全局应用设置。

```sql
CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT, -- JSON: 支持复杂数据结构
    data_type VARCHAR(50) DEFAULT 'string', -- 'string', 'number', 'boolean', 'json'
    description TEXT,
    is_encrypted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 4. 数据关系定义

### 4.1 用户关系
```
users (1) ──── (N) repositories
users (1) ──── (N) sync_logs
users (1) ──── (N) asset_filters
```

### 4.2 仓库关系
```
repositories (1) ──── (N) ai_analysis_results
repositories (1) ──── (N) releases
repositories (N) ──── (M) categories (通过 repository_categories)
```

### 4.3 Release 关系
```
releases (1) ──── (N) release_assets
releases (1) ──── (N) filter_matches
```

### 4.4 分类关系
```
categories (1) ──── (N) repository_categories
categories (1) ──── (N) categories (parent_id 自引用)
```

### 4.5 过滤器关系
```
asset_filters (1) ──── (N) filter_matches
```

## 5. 索引策略

### 5.1 主键索引
所有表的主键索引自动创建。

### 5.2 外键索引
为提升关联查询性能，创建以下外键索引：

```sql
-- 仓库表外键索引
CREATE INDEX idx_repositories_github_id ON repositories(github_id);
CREATE INDEX idx_repositories_owner_name ON repositories(owner, name);

-- AI 分析结果索引
CREATE INDEX idx_ai_analysis_repository_id ON ai_analysis_results(repository_id);
CREATE INDEX idx_ai_analysis_type_model ON ai_analysis_results(analysis_type, ai_model);

-- 分类关联索引
CREATE INDEX idx_repository_categories_repository_id ON repository_categories(repository_id);
CREATE INDEX idx_repository_categories_category_id ON repository_categories(category_id);

-- Release 相关索引
CREATE INDEX idx_releases_repository_id ON releases(repository_id);
CREATE INDEX idx_releases_github_id ON releases(github_release_id);
CREATE INDEX idx_releases_published_at ON releases(published_at);

-- Release 资产索引
CREATE INDEX idx_release_assets_release_id ON release_assets(release_id);
CREATE INDEX idx_release_assets_name ON release_assets(name);
CREATE INDEX idx_release_assets_size ON release_assets(size_bytes);

-- 过滤器匹配索引
CREATE INDEX idx_filter_matches_filter_id ON filter_matches(filter_id);
CREATE INDEX idx_filter_matches_asset_id ON filter_matches(asset_id);

-- 同步日志索引
CREATE INDEX idx_sync_logs_user_id ON sync_logs(user_id);
CREATE INDEX idx_sync_logs_type_status ON sync_logs(sync_type, status);

-- 搜索索引
CREATE INDEX idx_search_index_entity ON search_index(entity_type, entity_id);
CREATE INDEX idx_search_index_content ON search_index(content_type);
```

### 5.3 复合索引
为优化常用查询场景，创建复合索引：

```sql
-- 仓库搜索优化
CREATE INDEX idx_repositories_language_stars ON repositories(language, stars_count DESC);
CREATE INDEX idx_repositories_updated_at ON repositories(updated_at DESC);

-- Release 搜索优化
CREATE INDEX idx_releases_repo_published ON releases(repository_id, published_at DESC);

-- AI 分析结果查询优化
CREATE INDEX idx_ai_analysis_validated ON ai_analysis_results(is_validated, created_at DESC);

-- 资产过滤优化
CREATE INDEX idx_release_assets_downloaded ON release_assets(is_downloaded, created_at DESC);
```

### 5.4 全文搜索索引 (FTS5)
为支持全文搜索，创建虚拟表：

```sql
-- 仓库全文搜索
CREATE VIRTUAL TABLE repositories_fts USING fts5(
    full_name,
    description,
    topics,
    content='repositories',
    content_rowid='id'
);

-- Release 全文搜索
CREATE VIRTUAL TABLE releases_fts USING fts5(
    tag_name,
    name,
    body,
    content='releases',
    content_rowid='id'
);

-- AI 分析结果全文搜索
CREATE VIRTUAL TABLE ai_analysis_fts USING fts5(
    analysis_result,
    content='ai_analysis_results',
    content_rowid='id'
);
```

## 6. 数据库约束

### 6.1 检查约束
```sql
-- 用户评分范围检查
ALTER TABLE repositories ADD CONSTRAINT chk_user_rating 
    CHECK (user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5));

-- 置信度范围检查
ALTER TABLE ai_analysis_results ADD CONSTRAINT chk_confidence_score 
    CHECK (confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0));

-- 温度参数范围检查
ALTER TABLE ai_configs ADD CONSTRAINT chk_temperature 
    CHECK (temperature >= 0.0 AND temperature <= 2.0);

-- 文件大小非负检查
ALTER TABLE release_assets ADD CONSTRAINT chk_size_bytes 
    CHECK (size_bytes >= 0);

-- Token 计数非负检查
ALTER TABLE ai_analysis_results ADD CONSTRAINT chk_tokens_used 
    CHECK (tokens_used >= 0);
```

### 6.2 唯一约束
- `users.github_id`: GitHub 用户ID唯一
- `repositories.github_id`: GitHub 仓库ID唯一
- `repositories(owner, name)`: 仓库所有者+名称组合唯一
- `ai_analysis_results(repository_id, analysis_type, ai_model)`: 同一仓库的AI分析结果类型+模型组合唯一
- `repository_categories(repository_id, category_id)`: 仓库-分类关联唯一
- `releases.github_release_id`: GitHub Release ID唯一
- `release_assets.github_asset_id`: GitHub 资产ID唯一
- `asset_filters.name`: 过滤器名称唯一

### 6.3 外键约束
数据库启用外键约束，确保数据完整性：

```sql
PRAGMA foreign_keys = ON;
```

## 7. 数据类型说明

### 7.1 时间字段
- `DATETIME`: 存储精确到秒的时间戳
- `CURRENT_TIMESTAMP`: 自动记录创建时间
- 支持时区：所有时间以 UTC 存储，应用层处理时区转换

### 7.2 JSON 字段
以下字段使用 TEXT 类型存储 JSON 数据：
- `repositories.languages`: 语言占比 JSON
- `repositories.topics`: 标签数组 JSON
- `ai_analysis_results.analysis_result`: AI 分析结果 JSON
- `asset_filters.keywords`: 关键词数组 JSON
- `app_settings.setting_value`: 设置值 JSON

### 7.3 加密字段
以下敏感字段需要加密存储：
- `users.github_token_encrypted`: GitHub 访问令牌
- `ai_configs.api_key_encrypted`: AI API 密钥
- `webdav_configs.password_encrypted`: WebDAV 密码

## 8. 性能优化策略

### 8.1 分页查询优化
- 使用 `LIMIT` + `OFFSET` 进行分页
- 关键字段建立索引，支持高效排序

### 8.2 查询优化
- 常用查询场景创建复合索引
- 使用 `EXPLAIN QUERY PLAN` 分析查询性能
- 避免 SELECT *，只查询必要字段

### 8.3 数据清理策略
- 定期清理过期的同步日志
- 软删除已卸载的仓库相关数据
- 归档历史数据，保持活跃数据轻量

### 8.4 缓存策略
- 应用层实现数据缓存
- 搜索结果缓存
- AI 分析结果缓存，避免重复调用

## 9. 数据迁移与版本控制

### 9.1 版本管理
使用 `app_settings` 表管理数据库版本：

```sql
INSERT INTO app_settings (setting_key, setting_value, data_type) 
VALUES ('db_version', '1.0', 'string');
```

### 9.2 迁移脚本
- 每次数据库结构变更都创建迁移脚本
- 记录迁移历史和变更说明
- 支持向前和向后迁移

## 10. 安全考虑

### 10.1 数据加密
- 敏感字段使用对称加密（如 AES-256）
- 加密密钥安全管理
- 定期轮换加密密钥

### 10.2 访问控制
- 数据库文件权限控制
- 用户认证状态验证
- API 密钥使用监控

### 10.3 数据备份
- 定期数据库备份
- 加密备份文件
- 备份完整性验证

## 11. 扩展性设计

### 11.1 水平扩展
- 支持多用户数据隔离
- 可扩展为服务端数据库
- 数据分片策略预留

### 11.2 功能扩展
- 新增 AI 模型支持
- 更多文件格式支持
- 社区功能预留接口

### 11.3 性能扩展
- 向量搜索支持预留
- 分布式搜索架构
- 缓存层扩展接口

## 12. 监控与维护

### 12.1 性能监控
- 慢查询日志记录
- 索引使用率统计
- 数据库大小增长监控

### 12.2 维护任务
- 定期 VACUUM 操作
- 索引重建优化
- 数据完整性检查

### 12.3 错误处理
- 事务回滚机制
- 数据一致性检查
- 错误日志记录

---

该数据库架构设计充分考虑了 GitHubStarsManager 项目的功能需求、性能要求和扩展性需求，为项目的稳定运行和未来发展奠定了坚实的数据库基础。