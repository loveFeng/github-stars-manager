/**
 * 数据迁移执行器
 * 负责执行数据库迁移脚本，管理数据库版本，支持回滚操作
 */

import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from '../dao/dao_exception';
import * as fs from 'fs';
import * as path from 'path';
import { DateUtil } from '../utils/date';

export interface Migration {
  id: string;
  version: string;
  description: string;
  script: string;
  applied_at?: string;
  checksum?: string;
}

export interface MigrationResult {
  success: boolean;
  migration?: Migration;
  error?: string;
  executionTime: number;
}

export interface MigrationStatus {
  currentVersion: string;
  targetVersion: string;
  pendingMigrations: Migration[];
  appliedMigrations: Migration[];
  rollbackAvailable: boolean;
}

export class DatabaseMigrator {
  private db: SQLiteConnectionManager;
  private migrationsPath: string;
  private migrationsTable = 'schema_version';
  private backupDir: string;

  constructor(db: SQLiteConnectionManager, migrationsPath?: string, backupDir?: string) {
    this.db = db;
    this.migrationsPath = migrationsPath || path.join(process.cwd(), 'database', 'migrations');
    this.backupDir = backupDir || path.join(process.cwd(), 'database', 'backups');
    
    // 确保目录存在
    if (!fs.existsSync(this.migrationsPath)) {
      fs.mkdirSync(this.migrationsPath, { recursive: true });
    }
    if (!fs.existsSync(this.backupDir)) {
      fs.mkdirSync(this.backupDir, { recursive: true });
    }
  }

  /**
   * 初始化迁移系统
   */
  async initialize(): Promise<void> {
    try {
      // 检查是否已初始化
      const tables = await this.db.queryAll("SELECT name FROM sqlite_master WHERE type='table'");
      const tableExists = tables.some(table => table.name === this.migrationsTable);

      if (!tableExists) {
        await this.createMigrationTable();
        await this.createInitialMigration();
      }
    } catch (error) {
      throw new DAOException(`初始化迁移系统失败: ${error.message}`, 'MIGRATION_INIT_FAILED', error);
    }
  }

  /**
   * 创建迁移表
   */
  private async createMigrationTable(): Promise<void> {
    const sql = `
      CREATE TABLE ${this.migrationsTable} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        script TEXT NOT NULL,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        checksum TEXT,
        executed_by TEXT,
        execution_time INTEGER
      )
    `;
    await this.db.execute(sql);
  }

  /**
   * 创建初始迁移
   */
  private async createInitialMigration(): Promise<void> {
    const initialScript = this.getInitialSchemaScript();
    const version = '1.0.0';
    const description = 'Initial database schema creation';

    await this.recordMigration({
      id: '001_initial_schema',
      version,
      description,
      script: initialScript,
      applied_at: DateUtil.formatForSQLite(),
      checksum: this.calculateChecksum(initialScript),
      executed_by: 'system',
      execution_time: 0
    });
  }

  /**
   * 获取初始数据库脚本
   */
  private getInitialSchemaScript(): string {
    // 读取现有的 init.sql 文件
    const initSqlPath = path.join(process.cwd(), 'database', 'init.sql');
    if (fs.existsSync(initSqlPath)) {
      return fs.readFileSync(initSqlPath, 'utf-8');
    }

    // 如果文件不存在，返回基本的表创建脚本
    return `
      -- 初始数据库架构
      PRAGMA foreign_keys = ON;
      PRAGMA journal_mode = WAL;
      PRAGMA synchronous = NORMAL;
      PRAGMA cache_size = 20000;
      
      -- 用户表
      CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        github_id INTEGER UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        access_token TEXT,
        token_expires_at DATETIME,
        email TEXT,
        avatar_url TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      -- 仓库表
      CREATE TABLE repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        github_id INTEGER UNIQUE NOT NULL,
        owner TEXT NOT NULL,
        name TEXT NOT NULL,
        full_name TEXT UNIQUE NOT NULL,
        description TEXT,
        html_url TEXT NOT NULL,
        clone_url TEXT,
        ssh_url TEXT,
        stars_count INTEGER DEFAULT 0,
        forks_count INTEGER DEFAULT 0,
        watchers_count INTEGER DEFAULT 0,
        open_issues_count INTEGER DEFAULT 0,
        language TEXT,
        topics TEXT, -- JSON 数组
        archived BOOLEAN DEFAULT FALSE,
        disabled BOOLEAN DEFAULT FALSE,
        private BOOLEAN DEFAULT FALSE,
        is_starred BOOLEAN DEFAULT FALSE,
        last_synced_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      -- 分类表
      CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        color TEXT,
        is_default BOOLEAN DEFAULT FALSE,
        parent_id INTEGER,
        sort_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES categories (id) ON DELETE CASCADE
      );
      
      -- 仓库分类关联表
      CREATE TABLE repository_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (repository_id) REFERENCES repositories (id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE,
        UNIQUE (repository_id, category_id)
      );
      
      -- 发布版本表
      CREATE TABLE releases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        github_id INTEGER UNIQUE NOT NULL,
        repository_id INTEGER NOT NULL,
        tag_name TEXT NOT NULL,
        name TEXT,
        body TEXT,
        draft BOOLEAN DEFAULT FALSE,
        prerelease BOOLEAN DEFAULT FALSE,
        published_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (repository_id) REFERENCES repositories (id) ON DELETE CASCADE
      );
      
      -- 发布资产表
      CREATE TABLE release_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        github_id INTEGER UNIQUE NOT NULL,
        release_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        download_url TEXT NOT NULL,
        browser_download_url TEXT,
        size BIGINT NOT NULL,
        content_type TEXT,
        asset_type TEXT, -- JSON 配置
        is_downloaded BOOLEAN DEFAULT FALSE,
        local_path TEXT,
        download_progress INTEGER DEFAULT 0,
        download_status TEXT, -- pending, downloading, completed, failed
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (release_id) REFERENCES releases (id) ON DELETE CASCADE
      );
      
      -- 资产过滤器表
      CREATE TABLE asset_filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        asset_type TEXT NOT NULL, -- JSON 配置
        regex_pattern TEXT,
        match_rules TEXT, -- JSON 数组
        is_active BOOLEAN DEFAULT TRUE,
        priority INTEGER DEFAULT 0,
        auto_download BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      -- AI 配置表
      CREATE TABLE ai_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL, -- openai, anthropic, etc.
        api_key_encrypted TEXT,
        model TEXT,
        endpoint TEXT,
        max_tokens INTEGER DEFAULT 4000,
        temperature REAL DEFAULT 0.7,
        is_default BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      -- WebDAV 配置表
      CREATE TABLE webdav_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        username_encrypted TEXT,
        password_encrypted TEXT,
        base_path TEXT DEFAULT '/',
        is_default BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        last_sync_at DATETIME,
        sync_status TEXT, -- idle, syncing, error
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      -- 应用设置表
      CREATE TABLE app_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT, -- JSON 值
        data_type TEXT DEFAULT 'string', -- string, number, boolean, json
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      -- 创建索引
      CREATE INDEX idx_repositories_owner_name ON repositories(owner, name);
      CREATE INDEX idx_repositories_stars_count ON repositories(stars_count DESC);
      CREATE INDEX idx_repositories_language ON repositories(language);
      CREATE INDEX idx_releases_repository_id ON releases(repository_id);
      CREATE INDEX idx_release_assets_release_id ON release_assets(release_id);
      CREATE INDEX idx_repository_categories_repository_id ON repository_categories(repository_id);
      CREATE INDEX idx_repository_categories_category_id ON repository_categories(category_id);
      
      -- 创建全文搜索虚拟表
      CREATE VIRTUAL TABLE repositories_fts USING fts5(
        full_name, description, language, 
        content='repositories',
        content_rowid='id'
      );
      
      CREATE VIRTUAL TABLE releases_fts USING fts5(
        name, body, tag_name,
        content='releases',
        content_rowid='id'
      );
      
      -- 创建触发器
      CREATE TRIGGER repositories_fts_insert AFTER INSERT ON repositories
      BEGIN
        INSERT INTO repositories_fts(rowid, full_name, description, language)
        VALUES (new.id, new.full_name, new.description, new.language);
      END;
      
      CREATE TRIGGER repositories_fts_update AFTER UPDATE ON repositories
      BEGIN
        DELETE FROM repositories_fts WHERE rowid = old.id;
        INSERT INTO repositories_fts(rowid, full_name, description, language)
        VALUES (new.id, new.full_name, new.description, new.language);
      END;
      
      CREATE TRIGGER repositories_fts_delete AFTER DELETE ON repositories
      BEGIN
        DELETE FROM repositories_fts WHERE rowid = old.id;
      END;
      
      CREATE TRIGGER releases_fts_insert AFTER INSERT ON releases
      BEGIN
        INSERT INTO releases_fts(rowid, name, body, tag_name)
        VALUES (new.id, new.name, new.body, new.tag_name);
      END;
      
      CREATE TRIGGER releases_fts_update AFTER UPDATE ON releases
      BEGIN
        DELETE FROM releases_fts WHERE rowid = old.id;
        INSERT INTO releases_fts(rowid, name, body, tag_name)
        VALUES (new.id, new.name, new.body, new.tag_name);
      END;
      
      CREATE TRIGGER releases_fts_delete AFTER DELETE ON releases
      BEGIN
        DELETE FROM releases_fts WHERE rowid = old.id;
      END;
      
      -- 插入默认分类
      INSERT INTO categories (name, description, color, is_default, sort_order)
      VALUES ('默认分类', '未分类的仓库', '#gray', TRUE, 0);
    `;
  }

  /**
   * 获取迁移状态
   */
  async getStatus(): Promise<MigrationStatus> {
    try {
      const currentVersion = await this.getCurrentVersion();
      const availableMigrations = await this.getAvailableMigrations();
      const appliedMigrations = await this.getAppliedMigrations();

      const pendingMigrations = availableMigrations.filter(
        migration => !appliedMigrations.some(applied => applied.version === migration.version)
      );

      return {
        currentVersion,
        targetVersion: this.getLatestVersion(availableMigrations),
        pendingMigrations,
        appliedMigrations,
        rollbackAvailable: appliedMigrations.length > 0
      };
    } catch (error) {
      throw new DAOException(`获取迁移状态失败: ${error.message}`, 'MIGRATION_STATUS_FAILED', error);
    }
  }

  /**
   * 执行迁移
   */
  async migrate(targetVersion?: string): Promise<MigrationResult[]> {
    try {
      const startTime = Date.now();
      const status = await this.getStatus();
      
      if (!targetVersion) {
        targetVersion = this.getLatestVersion(status.pendingMigrations);
      }

      const migrationsToExecute = status.pendingMigrations.filter(
        migration => {
          const migrationIndex = status.pendingMigrations.findIndex(m => m.version === migration.version);
          const targetIndex = status.pendingMigrations.findIndex(m => m.version === targetVersion);
          return migrationIndex <= targetIndex;
        }
      );

      const results: MigrationResult[] = [];

      // 创建备份
      await this.createBackup(`migration_${status.currentVersion}_to_${targetVersion}`);

      for (const migration of migrationsToExecute) {
        const result = await this.executeMigration(migration);
        results.push(result);
        
        if (!result.success) {
          // 迁移失败时中断
          await this.rollbackToVersion(status.currentVersion);
          break;
        }
      }

      const totalTime = Date.now() - startTime;
      console.log(`迁移完成，耗时 ${totalTime}ms`);

      return results;
    } catch (error) {
      throw new DAOException(`迁移失败: ${error.message}`, 'MIGRATION_FAILED', error);
    }
  }

  /**
   * 执行单个迁移
   */
  private async executeMigration(migration: Migration): Promise<MigrationResult> {
    const startTime = Date.now();
    const transactionName = `migration_${migration.version}`;

    try {
      console.log(`正在执行迁移: ${migration.version} - ${migration.description}`);

      // 创建备份
      await this.createBackup(`before_${migration.version}`);

      // 执行迁移脚本
      await this.db.executeInTransaction(async (tx) => {
        // 分割 SQL 语句并逐个执行
        const statements = this.splitSQLStatements(migration.script);
        
        for (const statement of statements) {
          if (statement.trim()) {
            await tx.execute(statement.trim());
          }
        }
      });

      // 记录迁移
      await this.recordMigration({
        ...migration,
        applied_at: DateUtil.formatForSQLite(),
        checksum: this.calculateChecksum(migration.script),
        executed_by: 'migration_system',
        execution_time: Date.now() - startTime
      });

      console.log(`迁移完成: ${migration.version}`);

      return {
        success: true,
        migration,
        executionTime: Date.now() - startTime
      };
    } catch (error) {
      console.error(`迁移失败: ${migration.version}`, error);
      
      return {
        success: false,
        migration,
        error: error.message,
        executionTime: Date.now() - startTime
      };
    }
  }

  /**
   * 回滚到指定版本
   */
  async rollbackToVersion(targetVersion: string): Promise<void> {
    try {
      const status = await this.getStatus();
      const appliedMigrations = await this.getAppliedMigrations();
      
      // 找到需要回滚的迁移
      const migrationsToRollback = appliedMigrations
        .filter(migration => this.compareVersions(migration.version, targetVersion) > 0)
        .sort((a, b) => this.compareVersions(b.version, a.version)); // 按版本降序

      if (migrationsToRollback.length === 0) {
        console.log('无需回滚，已在目标版本');
        return;
      }

      console.log(`正在回滚到版本 ${targetVersion}`);

      // 创建回滚备份
      await this.createBackup(`rollback_${status.currentVersion}_to_${targetVersion}`);

      for (const migration of migrationsToRollback) {
        await this.rollbackMigration(migration);
      }

      console.log(`回滚完成，当前版本: ${await this.getCurrentVersion()}`);
    } catch (error) {
      throw new DAOException(`回滚失败: ${error.message}`, 'ROLLBACK_FAILED', error);
    }
  }

  /**
   * 回滚单个迁移
   */
  private async rollbackMigration(migration: Migration): Promise<void> {
    try {
      const rollbackScript = await this.getRollbackScript(migration.version);
      
      if (rollbackScript) {
        await this.db.executeInTransaction(async (tx) => {
          const statements = this.splitSQLStatements(rollbackScript);
          
          for (const statement of statements) {
            if (statement.trim()) {
              await tx.execute(statement.trim());
            }
          }
        });
      }

      // 删除迁移记录
      await this.db.execute(
        `DELETE FROM ${this.migrationsTable} WHERE version = ?`,
        [migration.version]
      );

      console.log(`回滚完成: ${migration.version}`);
    } catch (error) {
      throw new DAOException(`回滚迁移失败 (${migration.version}): ${error.message}`, 'ROLLBACK_MIGRATION_FAILED', error);
    }
  }

  /**
   * 创建迁移脚本
   */
  createMigration(version: string, description: string, script: string): void {
    const migrationId = this.generateMigrationId(version);
    const filename = `${migrationId}_${description.toLowerCase().replace(/\s+/g, '_')}.sql`;
    const filePath = path.join(this.migrationsPath, filename);

    const content = `-- Migration: ${version}
-- Description: ${description}
-- Applied: No
-- Date: ${DateUtil.formatForSQLite()}

${script}
`;

    fs.writeFileSync(filePath, content);
    console.log(`创建迁移脚本: ${filePath}`);
  }

  /**
   * 获取当前版本
   */
  private async getCurrentVersion(): Promise<string> {
    const result = await this.db.querySingle(
      `SELECT version FROM ${this.migrationsTable} ORDER BY applied_at DESC LIMIT 1`
    );
    return result?.version || '0.0.0';
  }

  /**
   * 获取可用的迁移
   */
  private async getAvailableMigrations(): Promise<Migration[]> {
    if (!fs.existsSync(this.migrationsPath)) {
      return [];
    }

    const files = fs.readdirSync(this.migrationsPath)
      .filter(file => file.endsWith('.sql'))
      .sort();

    const migrations: Migration[] = [];

    for (const file of files) {
      const content = fs.readFileSync(path.join(this.migrationsPath, file), 'utf-8');
      const migration = this.parseMigrationFile(file, content);
      if (migration) {
        migrations.push(migration);
      }
    }

    return migrations.sort((a, b) => this.compareVersions(a.version, b.version));
  }

  /**
   * 获取已应用的迁移
   */
  private async getAppliedMigrations(): Promise<Migration[]> {
    const result = await this.db.queryAll(
      `SELECT * FROM ${this.migrationsTable} ORDER BY applied_at`
    );
    
    return result.map((row: any) => ({
      id: row.version,
      version: row.version,
      description: row.description,
      script: row.script,
      applied_at: row.applied_at,
      checksum: row.checksum
    }));
  }

  /**
   * 记录迁移
   */
  private async recordMigration(migration: any): Promise<void> {
    const sql = `
      INSERT INTO ${this.migrationsTable} 
      (version, description, script, applied_at, checksum, executed_by, execution_time)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    await this.db.execute(sql, [
      migration.version,
      migration.description,
      migration.script,
      migration.applied_at,
      migration.checksum,
      migration.executed_by,
      migration.execution_time
    ]);
  }

  /**
   * 创建备份
   */
  private async createBackup(backupName: string): Promise<void> {
    try {
      const timestamp = DateUtil.formatForSQLite().replace(/[:-]/g, '').replace(' ', '_');
      const backupFilename = `${backupName}_${timestamp}.db`;
      const backupPath = path.join(this.backupDir, backupFilename);

      // 使用 SQLite 的备份功能
      await this.db.backup(backupPath);
      
      console.log(`备份创建成功: ${backupPath}`);
    } catch (error) {
      console.warn(`创建备份失败: ${error.message}`);
    }
  }

  /**
   * 计算校验和
   */
  private calculateChecksum(content: string): string {
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(content).digest('hex');
  }

  /**
   * 分割 SQL 语句
   */
  private splitSQLStatements(script: string): string[] {
    // 简单的 SQL 分割，基于分号
    return script.split(';').filter(stmt => stmt.trim().length > 0);
  }

  /**
   * 比较版本号
   */
  private compareVersions(version1: string, version2: string): number {
    const v1 = version1.split('.').map(Number);
    const v2 = version2.split('.').map(Number);
    
    for (let i = 0; i < Math.max(v1.length, v2.length); i++) {
      const part1 = v1[i] || 0;
      const part2 = v2[i] || 0;
      
      if (part1 > part2) return 1;
      if (part1 < part2) return -1;
    }
    
    return 0;
  }

  /**
   * 获取最新版本
   */
  private getLatestVersion(migrations: Migration[]): string {
    if (migrations.length === 0) return '0.0.0';
    
    return migrations.reduce((latest, migration) => 
      this.compareVersions(migration.version, latest) > 0 ? migration.version : latest
    , migrations[0].version);
  }

  /**
   * 生成迁移 ID
   */
  private generateMigrationId(version: string): string {
    const versionParts = version.split('.');
    return versionParts.map((part, index) => 
      index === 0 ? part.padStart(3, '0') : part.padStart(2, '0')
    ).join('');
  }

  /**
   * 解析迁移文件
   */
  private parseMigrationFile(filename: string, content: string): Migration | null {
    // 解析文件名和内容头部信息
    const lines = content.split('\n');
    let version = '';
    let description = '';

    for (const line of lines) {
      if (line.startsWith('-- Migration:')) {
        version = line.replace('-- Migration:', '').trim();
      }
      if (line.startsWith('-- Description:')) {
        description = line.replace('-- Description:', '').trim();
      }
    }

    if (!version) {
      // 从文件名解析版本
      const match = filename.match(/^(\d+)_/);
      if (match) {
        const id = match[1];
        version = `${id.slice(0, 3)}.${id.slice(3, 5)}.${id.slice(5, 7)}`;
      }
    }

    if (!version) return null;

    return {
      id: filename.replace('.sql', ''),
      version,
      description: description || filename,
      script: content
    };
  }

  /**
   * 获取回滚脚本
   */
  private async getRollbackScript(version: string): Promise<string | null> {
    const rollbackFile = path.join(this.migrationsPath, `rollback_${version}.sql`);
    
    if (fs.existsSync(rollbackFile)) {
      return fs.readFileSync(rollbackFile, 'utf-8');
    }

    // 如果没有专门的回滚脚本，尝试从迁移记录中获取
    const migration = await this.db.querySingle(
      `SELECT script FROM ${this.migrationsTable} WHERE version = ?`,
      [version]
    );

    return migration?.script || null;
  }
}