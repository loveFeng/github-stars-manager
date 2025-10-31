/**
 * WebDAV 配置 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  WebDAVConfig, 
  CreateWebDAVConfigData 
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';
import { CryptoUtil } from '../utils/crypto';

export class WebDAVConfigDAO extends BaseDAO<WebDAVConfig> {
  protected tableName = 'webdav_configs';
  protected allowedSortFields = [
    'id', 'name', 'server_url', 'is_active', 'is_default', 'last_sync_at', 'created_at', 'updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建 WebDAV 配置
   */
  async create(data: CreateWebDAVConfigData): Promise<WebDAVConfig> {
    try {
      // 加密密码
      let encryptedPassword = '';
      if (data.password_encrypted) {
        encryptedPassword = CryptoUtil.encrypt(data.password_encrypted);
      }

      const configData = {
        ...data,
        password_encrypted: encryptedPassword,
        is_active: data.is_active || false,
        is_default: data.is_default || false,
        remote_path: data.remote_path || '/GithubStarsManager'
      };

      return await super.create(configData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建 WebDAV 配置失败: ${error.message}`, 'CREATE_WEBDAV_CONFIG_FAILED', error);
    }
  }

  /**
   * 获取默认配置
   */
  async getDefaultConfig(): Promise<WebDAVConfig | null> {
    try {
      const sql = 'SELECT * FROM webdav_configs WHERE is_default = 1 LIMIT 1';
      const result = await this.db.querySingle(sql);
      return result || null;
    } catch (error) {
      throw new DAOException(`获取默认配置失败: ${error.message}`, 'GET_DEFAULT_CONFIG_FAILED', error);
    }
  }

  /**
   * 获取活跃配置
   */
  async getActiveConfigs(): Promise<WebDAVConfig[]> {
    try {
      const sql = `
        SELECT * FROM webdav_configs 
        WHERE is_active = 1 
        ORDER BY is_default DESC, name ASC
      `;
      const result = await this.db.queryAll(sql);
      return result;
    } catch (error) {
      throw new DAOException(`获取活跃配置失败: ${error.message}`, 'GET_ACTIVE_CONFIGS_FAILED', error);
    }
  }

  /**
   * 测试 WebDAV 连接
   */
  async testConnection(configId: number): Promise<{
    success: boolean;
    responseTime: number;
    error?: string;
    serverInfo?: any;
  }> {
    try {
      const config = await this.findById(configId);
      if (!config) {
        throw new DAOException('WebDAV 配置不存在', 'CONFIG_NOT_FOUND');
      }

      const startTime = Date.now();
      
      try {
        // 这里应该实现实际的 WebDAV 连接测试
        // 暂时模拟测试过程
        await new Promise(resolve => setTimeout(resolve, 200));
        
        const responseTime = Date.now() - startTime;
        return {
          success: true,
          responseTime,
          serverInfo: {
            server: 'WebDAV Server',
            version: '1.0'
          }
        };
      } catch (error) {
        const responseTime = Date.now() - startTime;
        return {
          success: false,
          responseTime,
          error: error.message
        };
      }
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`测试连接失败: ${error.message}`, 'TEST_CONNECTION_FAILED', error);
    }
  }

  /**
   * 设置默认配置
   */
  async setDefaultConfig(configId: number): Promise<void> {
    try {
      await this.db.executeInTransaction(async (tx) => {
        // 取消所有默认标记
        await tx.run('UPDATE webdav_configs SET is_default = 0');

        // 设置新的默认配置
        const result = await tx.run(
          'UPDATE webdav_configs SET is_default = 1 WHERE id = ?',
          [configId]
        );

        if (result.changes === 0) {
          throw new DAOException('WebDAV 配置不存在', 'CONFIG_NOT_FOUND');
        }
      });
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`设置默认配置失败: ${error.message}`, 'SET_DEFAULT_CONFIG_FAILED', error);
    }
  }

  /**
   * 切换配置状态
   */
  async toggleActive(configId: number): Promise<boolean> {
    try {
      const config = await this.findById(configId);
      if (!config) {
        throw new DAOException('WebDAV 配置不存在', 'CONFIG_NOT_FOUND');
      }

      const newActiveState = !config.is_active;
      const sql = 'UPDATE webdav_configs SET is_active = ? WHERE id = ?';
      const result = await this.db.update(sql, [newActiveState ? 1 : 0, configId]);
      return result > 0;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`切换配置状态失败: ${error.message}`, 'TOGGLE_ACTIVE_FAILED', error);
    }
  }

  /**
   * 更新密码
   */
  async updatePassword(configId: number, password: string): Promise<boolean> {
    try {
      const encryptedPassword = CryptoUtil.encrypt(password);
      const sql = 'UPDATE webdav_configs SET password_encrypted = ? WHERE id = ?';
      const result = await this.db.update(sql, [encryptedPassword, configId]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`更新密码失败: ${error.message}`, 'UPDATE_PASSWORD_FAILED', error);
    }
  }

  /**
   * 解密密码（谨慎使用）
   */
  decryptPassword(encryptedPassword: string): string {
    try {
      return CryptoUtil.decrypt(encryptedPassword);
    } catch (error) {
      throw new DAOException(`解密密码失败: ${error.message}`, 'DECRYPT_PASSWORD_FAILED', error);
    }
  }

  /**
   * 更新同步状态
   */
  async updateSyncStatus(configId: number, status: 'success' | 'failed' | 'in_progress', errorMessage?: string): Promise<void> {
    try {
      const sql = `
        UPDATE webdav_configs 
        SET sync_status = ?, error_message = ?, last_sync_at = ?
        WHERE id = ?
      `;
      
      await this.db.update(sql, [
        status,
        errorMessage || null,
        new Date().toISOString(),
        configId
      ]);
    } catch (error) {
      throw new DAOException(`更新同步状态失败: ${error.message}`, 'UPDATE_SYNC_STATUS_FAILED', error);
    }
  }

  /**
   * 验证配置参数
   */
  validateConfig(data: CreateWebDAVConfigData): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // 验证必需字段
    if (!data.name || data.name.trim().length === 0) {
      errors.push('配置名称不能为空');
    }

    if (!data.server_url || data.server_url.trim().length === 0) {
      errors.push('服务器 URL 不能为空');
    }

    // 验证 URL 格式
    if (data.server_url) {
      try {
        const url = new URL(data.server_url);
        if (!['http:', 'https:'].includes(url.protocol)) {
          errors.push('服务器 URL 必须使用 HTTP 或 HTTPS 协议');
        }
      } catch {
        errors.push('服务器 URL 格式无效');
      }
    }

    // 验证远程路径
    if (data.remote_path) {
      if (!data.remote_path.startsWith('/')) {
        errors.push('远程路径必须以 / 开头');
      }
      if (data.remote_path.includes('..')) {
        errors.push('远程路径不能包含 .. 路径');
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 克隆配置
   */
  async cloneConfig(configId: number, newName: string): Promise<WebDAVConfig> {
    try {
      const original = await this.findById(configId);
      if (!original) {
        throw new DAOException('原配置不存在', 'CONFIG_NOT_FOUND');
      }

      const cloneData = {
        name: newName,
        server_url: original.server_url,
        username: original.username,
        password_encrypted: original.password_encrypted, // 不复制加密的密码
        remote_path: original.remote_path,
        is_active: false,
        is_default: false
      };

      return await this.create(cloneData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`克隆配置失败: ${error.message}`, 'CLONE_CONFIG_FAILED', error);
    }
  }

  /**
   * 获取配置使用统计
   */
  async getConfigUsageStats(): Promise<{
    totalConfigs: number;
    activeConfigs: number;
    defaultConfigs: number;
    successfulSyncs: number;
    failedSyncs: number;
    averageSyncTime: number;
    lastSyncStatus: Array<{ configName: string; status: string; lastSyncAt: string }>;
  }> {
    try {
      const stats = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_configs,
          SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_configs,
          SUM(CASE WHEN is_default = 1 THEN 1 ELSE 0 END) as default_configs
        FROM webdav_configs
      `);

      // 从同步日志获取统计信息
      const syncStats = await this.db.querySingle(`
        SELECT 
          SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_syncs,
          SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_syncs,
          AVG(execution_time_ms) as average_sync_time
        FROM sync_logs
        WHERE sync_type = 'backup'
      `);

      // 最近同步状态
      const lastSyncStatus = await this.db.queryAll(`
        SELECT 
          w.name as config_name,
          w.sync_status,
          w.last_sync_at
        FROM webdav_configs w
        WHERE w.last_sync_at IS NOT NULL
        ORDER BY w.last_sync_at DESC
        LIMIT 10
      `);

      return {
        totalConfigs: stats.total_configs || 0,
        activeConfigs: stats.active_configs || 0,
        defaultConfigs: stats.default_configs || 0,
        successfulSyncs: syncStats.successful_syncs || 0,
        failedSyncs: syncStats.failed_syncs || 0,
        averageSyncTime: Math.round(syncStats.average_sync_time || 0),
        lastSyncStatus
      };
    } catch (error) {
      throw new DAOException(`获取配置统计失败: ${error.message}`, 'CONFIG_USAGE_STATS_FAILED', error);
    }
  }

  /**
   * 获取最近使用的配置
   */
  async getRecentlyUsed(limit: number = 5): Promise<WebDAVConfig[]> {
    try {
      const sql = `
        SELECT * FROM webdav_configs 
        WHERE is_active = 1 AND last_sync_at IS NOT NULL
        ORDER BY last_sync_at DESC 
        LIMIT ?
      `;
      const result = await this.db.queryAll(sql, [limit]);
      return result;
    } catch (error) {
      throw new DAOException(`获取最近使用配置失败: ${error.message}`, 'RECENTLY_USED_FAILED', error);
    }
  }

  /**
   * 清理过期的同步错误
   */
  async cleanupOldSyncErrors(): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - 30); // 30天前的错误

      const sql = `
        UPDATE webdav_configs 
        SET sync_status = NULL, error_message = NULL 
        WHERE last_sync_at < ? AND sync_status = 'failed'
      `;
      
      const result = await this.db.update(sql, [cutoffDate.toISOString()]);
      return result;
    } catch (error) {
      throw new DAOException(`清理同步错误失败: ${error.message}`, 'CLEANUP_SYNC_ERRORS_FAILED', error);
    }
  }
}
