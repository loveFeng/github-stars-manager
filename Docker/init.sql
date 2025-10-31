-- =============================================================================
-- 数据库初始化脚本
-- 创建用户、表结构、索引等
-- =============================================================================

-- 创建应用用户 (如果不存在)
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'app_user') THEN
      CREATE USER app_user WITH PASSWORD 'secure_password';
   END IF;
END
$do$;

-- 创建数据库 (如果不存在)
SELECT 'CREATE DATABASE myapp_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'myapp_db')\gexec

-- 切换到应用数据库
\c myapp_db;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- 创建模式
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;

-- 设置搜索路径
SET search_path TO app, public;

-- =============================================================================
-- 用户表
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 用户索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- =============================================================================
-- 会话表
-- =============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 会话索引
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- API 密钥表
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb,
    rate_limit INTEGER DEFAULT 100,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API 密钥索引
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- 操作日志表
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 操作日志索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_table ON audit_logs(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- =============================================================================
-- 系统配置表
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 系统配置索引
CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(key);
CREATE INDEX IF NOT EXISTS idx_system_configs_public ON system_configs(is_public) WHERE is_public = TRUE;

-- =============================================================================
-- 插入默认系统配置
-- =============================================================================
INSERT INTO system_configs (key, value, description, is_public) VALUES
('app.name', '"MyApp"', '应用名称', true),
('app.version', '"1.0.0"', '应用版本', true),
('auth.max_login_attempts', '5', '最大登录尝试次数', false),
('auth.lockout_duration', '900', '锁定持续时间(秒)', false),
('auth.password_min_length', '8', '密码最小长度', false),
('api.rate_limit.default', '100', '默认 API 速率限制', false),
('api.rate_limit.auth', '5', '认证 API 速率限制', false),
('upload.max_file_size', '10485760', '最大文件上传大小(字节)', false),
('upload.allowed_types', '["jpg","jpeg","png","gif","pdf","doc","docx"]', '允许的文件类型', false)
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- 创建触发器函数
-- =============================================================================

-- 自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON system_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 创建审计触发器
-- =============================================================================

-- 审计日志函数
CREATE OR REPLACE FUNCTION log_data_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (
            user_id,
            action,
            table_name,
            record_id,
            old_values
        ) VALUES (
            COALESCE(current_setting('app.user_id', true)::UUID, NULL),
            'DELETE',
            TG_TABLE_NAME,
            OLD.id,
            row_to_json(OLD)
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_logs (
            user_id,
            action,
            table_name,
            record_id,
            old_values,
            new_values
        ) VALUES (
            COALESCE(current_setting('app.user_id', true)::UUID, NULL),
            'UPDATE',
            TG_TABLE_NAME,
            NEW.id,
            row_to_json(OLD),
            row_to_json(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (
            user_id,
            action,
            table_name,
            record_id,
            new_values
        ) VALUES (
            COALESCE(current_setting('app.user_id', true)::UUID, NULL),
            'INSERT',
            TG_TABLE_NAME,
            NEW.id,
            row_to_json(NEW)
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

-- 为关键表添加审计触发器
CREATE TRIGGER audit_users AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION log_data_changes();

CREATE TRIGGER audit_api_keys AFTER INSERT OR UPDATE OR DELETE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION log_data_changes();

CREATE TRIGGER audit_system_configs AFTER INSERT OR UPDATE OR DELETE ON system_configs
    FOR EACH ROW EXECUTE FUNCTION log_data_changes();

-- =============================================================================
-- 创建视图
-- =============================================================================

-- 用户详细信息视图
CREATE OR REPLACE VIEW user_details AS
SELECT 
    u.id,
    u.email,
    u.username,
    u.first_name,
    u.last_name,
    u.avatar_url,
    u.is_active,
    u.is_admin,
    u.last_login_at,
    u.login_count,
    u.created_at,
    u.updated_at,
    CASE 
        WHEN u.deleted_at IS NOT NULL THEN 'deleted'
        WHEN u.is_active = false THEN 'inactive'
        ELSE 'active'
    END AS status
FROM users u;

-- 活跃会话统计视图
CREATE OR REPLACE VIEW active_sessions AS
SELECT 
    s.id,
    s.user_id,
    u.username,
    u.email,
    s.ip_address,
    s.user_agent,
    s.last_used_at,
    s.expires_at,
    CASE 
        WHEN s.expires_at < NOW() THEN 'expired'
        WHEN s.is_active = false THEN 'inactive'
        ELSE 'active'
    END AS status
FROM sessions s
JOIN users u ON s.user_id = u.id
WHERE s.is_active = true
ORDER BY s.last_used_at DESC;

-- =============================================================================
-- 权限和角色设置
-- =============================================================================

-- 授予权限
GRANT USAGE ON SCHEMA app TO app_user;
GRANT USAGE ON SCHEMA audit TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO app_user;

-- 只读权限给报告用户
CREATE ROLE report_user;
GRANT CONNECT ON DATABASE myapp_db TO report_user;
GRANT USAGE ON SCHEMA app TO report_user;
GRANT SELECT ON user_details TO report_user;
GRANT SELECT ON active_sessions TO report_user;

-- =============================================================================
-- 创建函数和存储过程
-- =============================================================================

-- 清理过期会话
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions 
    WHERE expires_at < NOW() - INTERVAL '1 day';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 获取用户统计信息
CREATE OR REPLACE FUNCTION get_user_stats(user_uuid UUID DEFAULT NULL)
RETURNS TABLE (
    total_users BIGINT,
    active_users BIGINT,
    new_users_today BIGINT,
    new_users_week BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM users)::BIGINT as total_users,
        (SELECT COUNT(*) FROM users WHERE is_active = TRUE)::BIGINT as active_users,
        (SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE)::BIGINT as new_users_today,
        (SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '7 days')::BIGINT as new_users_week;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 创建管理员用户 (密码: admin123)
-- 请在生产环境中立即修改！
-- =============================================================================
INSERT INTO users (
    id,
    email,
    username,
    password_hash,
    first_name,
    last_name,
    email_verified,
    is_active,
    is_admin
) VALUES (
    uuid_generate_v4(),
    'admin@example.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/eJ1E5v5y6', -- admin123
    'System',
    'Administrator',
    true,
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- =============================================================================
-- 创建索引优化
-- =============================================================================

-- 复合索引
CREATE INDEX IF NOT EXISTS idx_users_email_active ON users(email, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON sessions(user_id, is_active) WHERE is_active = TRUE;

-- 部分索引
CREATE INDEX IF NOT EXISTS idx_users_admin ON users(id) WHERE is_admin = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_recent ON sessions(last_used_at) WHERE last_used_at > NOW() - INTERVAL '7 days';

-- =============================================================================
-- 注释
-- =============================================================================
COMMENT ON TABLE users IS '用户表';
COMMENT ON TABLE sessions IS '会话表';
COMMENT ON TABLE api_keys IS 'API 密钥表';
COMMENT ON TABLE audit_logs IS '审计日志表';
COMMENT ON TABLE system_configs IS '系统配置表';

COMMENT ON VIEW user_details IS '用户详细信息视图';
COMMENT ON VIEW active_sessions IS '活跃会话统计视图';

COMMENT ON FUNCTION cleanup_expired_sessions() IS '清理过期会话';
COMMENT ON FUNCTION get_user_stats(UUID) IS '获取用户统计信息';