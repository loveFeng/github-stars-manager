/**
 * SQLite 数据库管理器
 * 整合所有 DAO 和数据库操作功能
 */

import { SQLiteConnectionManager } from '../../services/database_service';
import { DatabaseConfig } from './types';

// DAO 导入
import { UserDAO } from './user_dao';
import { RepositoryDAO } from './repository_dao';
import { CategoryDAO } from './category_dao';
import { RepositoryCategoryDAO } from './repository_category_dao';
import { ReleaseDAO } from './release_dao';
import { ReleaseAssetDAO } from './release_asset_dao';
import { AssetFilterDAO } from './asset_filter_dao';
import { AIConfigDAO } from './ai_config_dao';
import { WebDAVConfigDAO } from './webdav_config_dao';
import { AppSettingDAO } from './app_setting_dao';

export interface DatabaseManagerConfig {
  databasePath: string;
  enableWAL?: boolean;
  cacheSize?: number;
  synchronousMode?: 'OFF' | 'NORMAL' | 'FULL' | 'EXTRA';
  timeout?: number;
  verbose?: boolean;
}

export class DatabaseManager {
  private connection: SQLiteConnectionManager;
  
  // DAO 实例
  public readonly users: UserDAO;
  public readonly repositories: RepositoryDAO;
  public readonly categories: CategoryDAO;
  public readonly repositoryCategories: RepositoryCategoryDAO;
  public readonly releases: ReleaseDAO;
  public readonly releaseAssets: ReleaseAssetDAO;
  public readonly assetFilters: AssetFilterDAO;
  public readonly aiConfigs: AIConfigDAO;
  public readonly webdavConfigs: WebDAVConfigDAO;
  public readonly appSettings: AppSettingDAO;

  constructor(config: DatabaseManagerConfig) {
    this.connection = new SQLiteConnectionManager({
      filename: config.databasePath,
      walMode: config.enableWAL !== false,
      cacheSize: config.cacheSize || 20000,
      synchronousMode: config.synchronousMode || 'NORMAL',
      timeout: config.timeout || 30000,
      verbose: config.verbose || false
    });

    // 初始化 DAO
    this.users = new UserDAO(this.connection);
    this.repositories = new RepositoryDAO(this.connection);
    this.categories = new CategoryDAO(this.connection);
    this.repositoryCategories = new RepositoryCategoryDAO(this.connection);
    this.releases = new ReleaseDAO(this.connection);
    this.releaseAssets = new ReleaseAssetDAO(this.connection);
    this.assetFilters = new AssetFilterDAO(this.connection);
    this.aiConfigs = new AIConfigDAO(this.connection);
    this.webdavConfigs = new WebDAVConfigDAO(this.connection);
    this.appSettings = new AppSettingDAO(this.connection);
  }

  /**
   * 初始化数据库连接
   */
  async connect(): Promise<void> {
    await this.connection.connect();
  }

  /**
   * 断开数据库连接
   */
  async disconnect(): Promise<void> {
    await this.connection.disconnect();
  }

  /**
   * 检查数据库连接状态
   */
  isConnected(): boolean {
    return this.connection.isReady();
  }

  /**
   * 执行事务
   */
  async transaction<T>(operation: () => Promise<T>): Promise<T> {
    return this.connection.transaction(operation);
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{
    status: 'healthy' | 'unhealthy';
    responseTime: number;
    details?: any;
  }> {
    const health = await this.connection.healthCheck();
    return {
      status: health.status as 'healthy' | 'unhealthy',
      responseTime: health.responseTime,
      details: health.details
    };
  }

  /**
   * 获取数据库统计信息
   */
  async getDatabaseStats(): Promise<{
    connectionMetrics: any;
    databaseInfo: any;
    tableStats: Record<string, any>;
  }> {
    const [connectionMetrics, databaseInfo] = await Promise.all([
      this.connection.getMetrics(),
      this.connection.getStatistics()
    ]);

    // 获取各表统计信息
    const tableStats: Record<string, any> = {};
    const tables = [
      'users', 'repositories', 'categories', 'repository_categories',
      'releases', 'release_assets', 'asset_filters', 'filter_matches',
      'ai_configs', 'webdav_configs', 'sync_logs', 'search_index',
      'app_settings'
    ];

    for (const table of tables) {
      try {
        const stats = await this.appSettings.getTableStats();
        tableStats[table] = stats;
      } catch {
        tableStats[table] = { error: '无法获取统计信息' };
      }
    }

    return {
      connectionMetrics,
      databaseInfo,
      tableStats
    };
  }

  /**
   * 备份数据库
   */
  async backup(backupPath: string): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('数据库未连接');
    }

    // 使用 SQLite 的备份功能
    // 这里简化实现，实际应该使用 SQLite 的在线备份 API
    const fs = require('fs');
    const path = require('path');

    const sourcePath = this.connection.getDatabaseInfo().then(info => info.filename);
    await fs.copyFile(await sourcePath, backupPath);
  }

  /**
   * 优化数据库
   */
  async optimize(): Promise<void> {
    await this.connection.vacuum();
    await this.connection.analyze();
  }

  /**
   * 完整性检查
   */
  async integrityCheck(): Promise<{
    isValid: boolean;
    messages: string[];
  }> {
    const result = await this.connection.integrityCheck();
    
    return {
      isValid: result === 'ok',
      messages: Array.isArray(result) ? result : [result]
    };
  }

  /**
   * 清理数据库
   */
  async cleanup(): Promise<{
    cleaned: Record<string, number>;
    total: number;
  }> {
    const cleaned: Record<string, number> = {};
    let total = 0;

    try {
      // 清理过期的同步日志（保留30天）
      const oldSyncLogs = await this.connection.delete(`
        DELETE FROM sync_logs 
        WHERE created_at < datetime('now', '-30 days')
      `);
      cleaned.sync_logs = oldSyncLogs;
      total += oldSyncLogs;

      // 清理未使用的过滤器匹配记录
      const orphanedMatches = await this.connection.delete(`
        DELETE FROM filter_matches 
        WHERE filter_id NOT IN (SELECT id FROM asset_filters)
        OR asset_id NOT IN (SELECT id FROM release_assets)
      `);
      cleaned.filter_matches = orphanedMatches;
      total += orphanedMatches;

      // 清理无效的关联
      const invalidAssociations = await this.repositoryCategories.cleanupInvalidAssociations();
      cleaned.invalid_associations = invalidAssociations;
      total += invalidAssociations;

      // 清理未使用的过滤器
      const unusedFilters = await this.assetFilters.cleanupUnusedFilters();
      cleaned.unused_filters = unusedFilters;
      total += unusedFilters;

      // 清理过期的 Release
      const oldReleases = await this.releases.cleanupOldReleases(365);
      cleaned.old_releases = oldReleases;
      total += oldReleases;

      // 清理未认证的旧用户
      const inactiveUsers = await this.users.cleanupOldInactiveUsers(30);
      cleaned.inactive_users = inactiveUsers;
      total += inactiveUsers;

      // 清理过期的设置
      const expiredSettings = await this.appSettings.cleanupExpiredSettings();
      cleaned.expired_settings = expiredSettings;
      total += expiredSettings;

    } catch (error) {
      throw new Error(`数据库清理失败: ${error.message}`);
    }

    return { cleaned, total };
  }

  /**
   * 重置数据库（谨慎使用）
   */
  async reset(): Promise<void> {
    await this.transaction(async () => {
      // 删除所有表数据（保留表结构）
      const tables = [
        'filter_matches', 'release_assets', 'releases', 'repository_categories',
        'ai_analysis_results', 'repositories', 'users', 'sync_logs', 'search_index'
      ];

      for (const table of tables) {
        await this.connection.query(`DELETE FROM ${table}`);
      }

      // 重置设置
      await this.appSettings.resetToDefaults();
      
      // 重新创建默认分类
      await this.categories.resetDefaultCategories();
      
      // 创建默认过滤器
      await this.assetFilters.createDefaultFilters();
    });
  }

  /**
   * 导出数据库为 SQL
   */
  async exportSQL(): Promise<string> {
    // 这里应该实现完整的 SQL 导出功能
    // 暂时返回占位符
    return '-- SQL Export not implemented yet';
  }

  /**
   * 获取原生数据库连接（谨慎使用）
   */
  getNativeConnection() {
    return this.connection.getNativeDB();
  }

  /**
   * 获取数据库路径
   */
  getDatabasePath(): Promise<string> {
    return this.connection.getDatabaseInfo().then(info => info.filename);
  }

  /**
   * 设置慢查询阈值
   */
  setSlowQueryThreshold(ms: number): void {
    this.connection.setSlowQueryThreshold(ms);
  }

  /**
   * 监听数据库事件
   */
  on(event: string, callback: (...args: any[]) => void): void {
    this.connection.on(event, callback);
  }

  /**
   * 移除事件监听
   */
  off(event: string, callback?: (...args: any[]) => void): void {
    this.connection.off(event, callback);
  }

  /**
   * 获取数据库大小
   */
  async getDatabaseSize(): Promise<number> {
    return await this.connection.getDatabaseSize();
  }

  /**
   * 创建数据库快照
   */
  async createSnapshot(name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const dbPath = await this.getDatabasePath();
    const snapshotPath = dbPath.replace('.sqlite', `_snapshot_${name}_${timestamp}.sqlite`);
    
    await this.backup(snapshotPath);
    return snapshotPath;
  }

  /**
   * 从快照恢复
   */
  async restoreFromSnapshot(snapshotPath: string): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('数据库未连接');
    }

    await this.connection.disconnect();
    
    const fs = require('fs');
    const dbPath = await this.getDatabasePath();
    
    await fs.copyFile(snapshotPath, dbPath);
    
    await this.connect();
  }

  /**
   * 获取数据库版本
   */
  async getVersion(): Promise<string> {
    return await this.appSettings.getSettingValue('db_version', '1.0');
  }

  /**
   * 设置数据库版本
   */
  async setVersion(version: string): Promise<void> {
    await this.appSettings.setSetting('db_version', version, 'string');
  }

  /**
   * 检查初始化状态
   */
  async isInitialized(): Promise<boolean> {
    return await this.appSettings.getSettingValue('init_completed', false);
  }

  /**
   * 标记为已初始化
   */
  async markAsInitialized(): Promise<void> {
    await this.appSettings.setSetting('init_completed', true, 'boolean');
    await this.appSettings.setSetting('init_timestamp', new Date().toISOString(), 'string');
  }
}

// 导出单例实例
let dbManager: DatabaseManager | null = null;

export function getDatabaseManager(config: DatabaseManagerConfig): DatabaseManager {
  if (!dbManager) {
    dbManager = new DatabaseManager(config);
  }
  return dbManager;
}

export function getDatabaseManagerInstance(): DatabaseManager | null {
  return dbManager;
}

export function destroyDatabaseManager(): void {
  if (dbManager) {
    dbManager.disconnect();
    dbManager = null;
  }
}
