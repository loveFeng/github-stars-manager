-- GitHubStarsManager SQLite 数据库初始化脚本
-- 版本: 1.0
-- 创建时间: 2025-10-31

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 启用 WAL 模式以提高并发性能
PRAGMA journal_mode = WAL;

-- 设置同步模式
PRAGMA synchronous = NORMAL;

-- 设置缓存大小 (20MB)
PRAGMA cache_size = 20000;

-- 设置临时存储模式
PRAGMA temp_store = memory;

-- =============================================================================
-- 1. 用户与认证相关表
-- =============================================================================

-- 用户表
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

-- =============================================================================
-- 2. 仓库管理相关表
-- =============================================================================

-- 仓库表
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

-- AI 分析结果表
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

-- =============================================================================
-- 3. 分类系统相关表
-- =============================================================================

-- 分类表
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

-- 仓库分类关联表
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

-- =============================================================================
-- 4. Release 管理相关表
-- =============================================================================

-- Release 表
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

-- Release 资产表
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

-- =============================================================================
-- 5. 过滤器系统相关表
-- =============================================================================

-- 资产过滤器表
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

-- 过滤器匹配记录表
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

-- =============================================================================
-- 6. 配置管理相关表
-- =============================================================================

-- AI 配置表
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

-- WebDAV 配置表
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

-- =============================================================================
-- 7. 系统管理相关表
-- =============================================================================

-- 同步日志表
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

-- 搜索索引表
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

-- 应用设置表
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

-- =============================================================================
-- 8. 索引创建
-- =============================================================================

-- 仓库表索引
CREATE INDEX idx_repositories_github_id ON repositories(github_id);
CREATE INDEX idx_repositories_owner_name ON repositories(owner, name);
CREATE INDEX idx_repositories_language_stars ON repositories(language, stars_count DESC);
CREATE INDEX idx_repositories_updated_at ON repositories(updated_at DESC);

-- AI 分析结果索引
CREATE INDEX idx_ai_analysis_repository_id ON ai_analysis_results(repository_id);
CREATE INDEX idx_ai_analysis_type_model ON ai_analysis_results(analysis_type, ai_model);
CREATE INDEX idx_ai_analysis_validated ON ai_analysis_results(is_validated, created_at DESC);

-- 分类关联索引
CREATE INDEX idx_repository_categories_repository_id ON repository_categories(repository_id);
CREATE INDEX idx_repository_categories_category_id ON repository_categories(category_id);

-- Release 相关索引
CREATE INDEX idx_releases_repository_id ON releases(repository_id);
CREATE INDEX idx_releases_github_id ON releases(github_release_id);
CREATE INDEX idx_releases_published_at ON releases(published_at DESC);
CREATE INDEX idx_releases_repo_published ON releases(repository_id, published_at DESC);

-- Release 资产索引
CREATE INDEX idx_release_assets_release_id ON release_assets(release_id);
CREATE INDEX idx_release_assets_name ON release_assets(name);
CREATE INDEX idx_release_assets_size ON release_assets(size_bytes);
CREATE INDEX idx_release_assets_downloaded ON release_assets(is_downloaded, created_at DESC);

-- 过滤器匹配索引
CREATE INDEX idx_filter_matches_filter_id ON filter_matches(filter_id);
CREATE INDEX idx_filter_matches_asset_id ON filter_matches(asset_id);

-- 同步日志索引
CREATE INDEX idx_sync_logs_user_id ON sync_logs(user_id);
CREATE INDEX idx_sync_logs_type_status ON sync_logs(sync_type, status);

-- 搜索索引
CREATE INDEX idx_search_index_entity ON search_index(entity_type, entity_id);
CREATE INDEX idx_search_index_content ON search_index(content_type);

-- =============================================================================
-- 9. 全文搜索索引 (FTS5)
-- =============================================================================

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

-- =============================================================================
-- 10. 触发器创建
-- =============================================================================

-- 更新时间戳触发器
CREATE TRIGGER update_repositories_timestamp 
    AFTER UPDATE ON repositories
    FOR EACH ROW
    BEGIN
        UPDATE repositories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_ai_analysis_timestamp 
    AFTER UPDATE ON ai_analysis_results
    FOR EACH ROW
    BEGIN
        UPDATE ai_analysis_results SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_categories_timestamp 
    AFTER UPDATE ON categories
    FOR EACH ROW
    BEGIN
        UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_releases_timestamp 
    AFTER UPDATE ON releases
    FOR EACH ROW
    BEGIN
        UPDATE releases SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_release_assets_timestamp 
    AFTER UPDATE ON release_assets
    FOR EACH ROW
    BEGIN
        UPDATE release_assets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_asset_filters_timestamp 
    AFTER UPDATE ON asset_filters
    FOR EACH ROW
    BEGIN
        UPDATE asset_filters SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_ai_configs_timestamp 
    AFTER UPDATE ON ai_configs
    FOR EACH ROW
    BEGIN
        UPDATE ai_configs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_webdav_configs_timestamp 
    AFTER UPDATE ON webdav_configs
    FOR EACH ROW
    BEGIN
        UPDATE webdav_configs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- 搜索索引同步触发器
CREATE TRIGGER repositories_fts_insert AFTER INSERT ON repositories
    BEGIN
        INSERT INTO repositories_fts(rowid, full_name, description, topics)
        VALUES (NEW.id, NEW.full_name, NEW.description, NEW.topics);
    END;

CREATE TRIGGER repositories_fts_update AFTER UPDATE ON repositories
    BEGIN
        UPDATE repositories_fts 
        SET full_name = NEW.full_name, description = NEW.description, topics = NEW.topics
        WHERE rowid = NEW.id;
    END;

CREATE TRIGGER repositories_fts_delete AFTER DELETE ON repositories
    BEGIN
        DELETE FROM repositories_fts WHERE rowid = OLD.id;
    END;

CREATE TRIGGER releases_fts_insert AFTER INSERT ON releases
    BEGIN
        INSERT INTO releases_fts(rowid, tag_name, name, body)
        VALUES (NEW.id, NEW.tag_name, NEW.name, NEW.body);
    END;

CREATE TRIGGER releases_fts_update AFTER UPDATE ON releases
    BEGIN
        UPDATE releases_fts 
        SET tag_name = NEW.tag_name, name = NEW.name, body = NEW.body
        WHERE rowid = NEW.id;
    END;

CREATE TRIGGER releases_fts_delete AFTER DELETE ON releases
    BEGIN
        DELETE FROM releases_fts WHERE rowid = OLD.id;
    END;

CREATE TRIGGER ai_analysis_fts_insert AFTER INSERT ON ai_analysis_results
    BEGIN
        INSERT INTO ai_analysis_fts(rowid, analysis_result)
        VALUES (NEW.id, NEW.analysis_result);
    END;

CREATE TRIGGER ai_analysis_fts_update AFTER UPDATE ON ai_analysis_results
    BEGIN
        UPDATE ai_analysis_fts SET analysis_result = NEW.analysis_result WHERE rowid = NEW.id;
    END;

CREATE TRIGGER ai_analysis_fts_delete AFTER DELETE ON ai_analysis_results
    BEGIN
        DELETE FROM ai_analysis_fts WHERE rowid = OLD.id;
    END;

-- =============================================================================
-- 11. 默认数据插入
-- =============================================================================

-- 插入默认分类
INSERT INTO categories (name, description, color, icon, is_default, sort_order) VALUES
('前端开发', '前端框架、库和工具', '#3B82F6', 'Code', 1, 1),
('后端开发', '后端框架、API和服务器', '#10B981', 'Server', 1, 2),
('移动开发', '移动应用开发相关', '#F59E0B', 'Smartphone', 1, 3),
('机器学习', '机器学习和深度学习', '#8B5CF6', 'Brain', 1, 4),
('数据科学', '数据分析和可视化', '#EF4444', 'BarChart', 1, 5),
('DevOps', 'CI/CD、容器化和部署', '#06B6D4', 'Settings', 1, 6),
('工具类', '开发工具和实用程序', '#84CC16', 'Wrench', 1, 7),
('文档', '文档和教程', '#F97316', 'Book', 1, 8),
('游戏开发', '游戏引擎和框架', '#EC4899', 'Gamepad', 1, 9),
('区块链', '区块链和加密货币', '#6366F1', 'Coins', 1, 10);

-- 插入默认应用设置
INSERT INTO app_settings (setting_key, setting_value, data_type, description) VALUES
('db_version', '"1.0"', 'string', '数据库版本号'),
('theme', '"system"', 'string', 'UI主题设置：light/dark/system'),
('language', '"zh-CN"', 'string', '界面语言设置'),
('auto_sync_releases', 'true', 'boolean', '是否自动同步Release信息'),
('auto_ai_analysis', 'true', 'boolean', '是否自动进行AI分析'),
('search_results_limit', '50', 'number', '搜索结果显示数量限制'),
('sync_interval_minutes', '60', 'number', '自动同步间隔（分钟）'),
('max_retry_attempts', '3', 'number', 'API调用最大重试次数'),
('backup_on_exit', 'false', 'boolean', '退出时是否自动备份'),
('show_prerelease', 'false', 'boolean', '是否显示预发布版本'),
('default_sort_field', 'updated_at', 'string', '默认排序字段'),
('default_sort_order', 'desc', 'string', '默认排序顺序：asc/desc');

-- 插入默认资产过滤器
INSERT INTO asset_filters (name, description, keywords, match_type, case_sensitive, sort_order) VALUES
('macOS 安装包', '适用于 macOS 的安装包文件', '["dmg", "pkg", "app", "mac", "osx"]', 'keyword', 0, 1),
('Windows 安装包', '适用于 Windows 的安装包文件', '["exe", "msi", "setup", "win", "windows"]', 'keyword', 0, 2),
('Linux 包', '适用于 Linux 的安装包', '["deb", "rpm", "AppImage", "tar.gz", "zip"]', 'keyword', 0, 3),
('ARM 架构', 'ARM 架构相关的文件', '["arm64", "aarch64", "arm"]', 'keyword', 0, 4),
('压缩包', '各种压缩包文件', '["tar.gz", "tar.bz2", "zip", "rar", "7z"]', 'keyword', 0, 5),
('源码包', '源代码压缩包', '["source", "src", "code"]', 'keyword', 0, 6),
('Docker 镜像', 'Docker 相关文件', '["docker", "image", "container"]', 'keyword', 0, 7);

-- 插入示例 AI 配置模板（需要用户自行配置 API Key）
INSERT INTO ai_configs (name, api_url, model_name, description, is_default) VALUES
('OpenAI GPT-4', 'https://api.openai.com/v1', 'gpt-4', 'OpenAI GPT-4 模型配置模板', 0),
('OpenAI GPT-3.5', 'https://api.openai.com/v1', 'gpt-3.5-turbo', 'OpenAI GPT-3.5 Turbo 模型配置模板', 1),
('本地 Ollama', 'http://localhost:11434/v1', 'llama2', '本地 Ollama 模型配置模板', 0);

-- 插入示例 WebDAV 配置模板（需要用户自行配置）
INSERT INTO webdav_configs (name, server_url, username, remote_path, description, is_default) VALUES
('坚果云', 'https://dav.jianguoyun.com/dav/', '', '/GithubStarsManager', '坚果云 WebDAV 配置模板', 0),
('Nextcloud', 'https://your-nextcloud.com/remote.php/dav/', '', '/GithubStarsManager', 'Nextcloud WebDAV 配置模板', 0),
('ownCloud', 'https://your-owncloud.com/remote.php/dav/', '', '/GithubStarsManager', 'ownCloud WebDAV 配置模板', 0);

-- =============================================================================
-- 12. 初始化完成提示
-- =============================================================================

-- 创建初始化标记
INSERT INTO app_settings (setting_key, setting_value, data_type, description) VALUES
('init_completed', 'true', 'boolean', '数据库初始化完成标记'),
('init_timestamp', '"2025-10-31T09:33:22Z"', 'string', '初始化时间戳');

-- 显示初始化结果
SELECT 'Database initialization completed successfully!' as message,
       COUNT(*) as tables_created
FROM sqlite_master 
WHERE type='table' AND name NOT LIKE 'sqlite_%';
