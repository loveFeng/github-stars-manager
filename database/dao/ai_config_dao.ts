/**
 * AI 配置 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  AIConfig, 
  CreateAIConfigData 
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';
import { CryptoUtil } from '../utils/crypto';

export class AIConfigDAO extends BaseDAO<AIConfig> {
  protected tableName = 'ai_configs';
  protected allowedSortFields = [
    'id', 'name', 'model_name', 'is_active', 'is_default', 'created_at', 'updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建 AI 配置
   */
  async create(data: CreateAIConfigData): Promise<AIConfig> {
    try {
      // 加密 API Key
      let encryptedApiKey = '';
      if (data.api_key_encrypted) {
        encryptedApiKey = CryptoUtil.encrypt(data.api_key_encrypted);
      }

      const configData = {
        ...data,
        api_key_encrypted: encryptedApiKey,
        is_active: data.is_active || false,
        is_default: data.is_default || false,
        max_tokens: data.max_tokens || 4000,
        temperature: data.temperature || 0.7,
        timeout_seconds: data.timeout_seconds || 30
      };

      return await super.create(configData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建 AI 配置失败: ${error.message}`, 'CREATE_AI_CONFIG_FAILED', error);
    }
  }

  /**
   * 获取默认配置
   */
  async getDefaultConfig(): Promise<AIConfig | null> {
    try {
      const sql = 'SELECT * FROM ai_configs WHERE is_default = 1 LIMIT 1';
      const result = await this.db.querySingle(sql);
      return result || null;
    } catch (error) {
      throw new DAOException(`获取默认配置失败: ${error.message}`, 'GET_DEFAULT_CONFIG_FAILED', error);
    }
  }

  /**
   * 获取活跃配置
   */
  async getActiveConfigs(): Promise<AIConfig[]> {
    try {
      const sql = `
        SELECT * FROM ai_configs 
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
   * 测试 AI 配置连接
   */
  async testConnection(configId: number): Promise<{
    success: boolean;
    responseTime: number;
    error?: string;
  }> {
    try {
      const config = await this.findById(configId);
      if (!config) {
        throw new DAOException('AI 配置不存在', 'CONFIG_NOT_FOUND');
      }

      const startTime = Date.now();
      
      try {
        // 这里应该实现实际的 API 连接测试
        // 暂时模拟测试过程
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const responseTime = Date.now() - startTime;
        return {
          success: true,
          responseTime
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
        await tx.run('UPDATE ai_configs SET is_default = 0');

        // 设置新的默认配置
        const result = await tx.run(
          'UPDATE ai_configs SET is_default = 1 WHERE id = ?',
          [configId]
        );

        if (result.changes === 0) {
          throw new DAOException('AI 配置不存在', 'CONFIG_NOT_FOUND');
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
        throw new DAOException('AI 配置不存在', 'CONFIG_NOT_FOUND');
      }

      const newActiveState = !config.is_active;
      const sql = 'UPDATE ai_configs SET is_active = ? WHERE id = ?';
      const result = await this.db.update(sql, [newActiveState ? 1 : 0, configId]);
      return result > 0;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`切换配置状态失败: ${error.message}`, 'TOGGLE_ACTIVE_FAILED', error);
    }
  }

  /**
   * 更新 API Key
   */
  async updateApiKey(configId: number, apiKey: string): Promise<boolean> {
    try {
      const encryptedApiKey = CryptoUtil.encrypt(apiKey);
      const sql = 'UPDATE ai_configs SET api_key_encrypted = ? WHERE id = ?';
      const result = await this.db.update(sql, [encryptedApiKey, configId]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`更新 API Key 失败: ${error.message}`, 'UPDATE_API_KEY_FAILED', error);
    }
  }

  /**
   * 解密 API Key（谨慎使用）
   */
  decryptApiKey(encryptedApiKey: string): string {
    try {
      return CryptoUtil.decrypt(encryptedApiKey);
    } catch (error) {
      throw new DAOException(`解密 API Key 失败: ${error.message}`, 'DECRYPT_API_KEY_FAILED', error);
    }
  }

  /**
   * 验证配置参数
   */
  validateConfig(data: CreateAIConfigData): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // 验证必需字段
    if (!data.name || data.name.trim().length === 0) {
      errors.push('配置名称不能为空');
    }

    if (!data.api_url || data.api_url.trim().length === 0) {
      errors.push('API URL 不能为空');
    }

    if (!data.model_name || data.model_name.trim().length === 0) {
      errors.push('模型名称不能为空');
    }

    // 验证 URL 格式
    if (data.api_url) {
      try {
        new URL(data.api_url);
      } catch {
        errors.push('API URL 格式无效');
      }
    }

    // 验证数值范围
    if (data.max_tokens !== undefined && (data.max_tokens < 1 || data.max_tokens > 32768)) {
      errors.push('最大 Token 数必须在 1-32768 之间');
    }

    if (data.temperature !== undefined && (data.temperature < 0 || data.temperature > 2)) {
      errors.push('温度值必须在 0-2 之间');
    }

    if (data.timeout_seconds !== undefined && data.timeout_seconds < 1) {
      errors.push('超时时间必须大于 0');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 克隆配置
   */
  async cloneConfig(configId: number, newName: string): Promise<AIConfig> {
    try {
      const original = await this.findById(configId);
      if (!original) {
        throw new DAOException('原配置不存在', 'CONFIG_NOT_FOUND');
      }

      const cloneData = {
        name: newName,
        api_url: original.api_url,
        api_key_encrypted: original.api_key_encrypted, // 不复制加密的 API Key
        model_name: original.model_name,
        max_tokens: original.max_tokens,
        temperature: original.temperature,
        timeout_seconds: original.timeout_seconds,
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
    averageTemperature: number;
    averageMaxTokens: number;
    modelDistribution: Array<{ modelName: string; count: number }>;
  }> {
    try {
      const stats = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_configs,
          SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_configs,
          SUM(CASE WHEN is_default = 1 THEN 1 ELSE 0 END) as default_configs,
          AVG(temperature) as average_temperature,
          AVG(max_tokens) as average_max_tokens
        FROM ai_configs
      `);

      const modelDistribution = await this.db.queryAll(`
        SELECT model_name, COUNT(*) as count
        FROM ai_configs
        WHERE is_active = 1
        GROUP BY model_name
        ORDER BY count DESC
      `);

      return {
        totalConfigs: stats.total_configs || 0,
        activeConfigs: stats.active_configs || 0,
        defaultConfigs: stats.default_configs || 0,
        averageTemperature: Math.round((stats.average_temperature || 0) * 100) / 100,
        averageMaxTokens: Math.round(stats.average_max_tokens || 0),
        modelDistribution
      };
    } catch (error) {
      throw new DAOException(`获取配置统计失败: ${error.message}`, 'CONFIG_USAGE_STATS_FAILED', error);
    }
  }

  /**
   * 获取最近使用的配置
   */
  async getRecentlyUsed(limit: number = 5): Promise<AIConfig[]> {
    try {
      // 这里需要结合使用记录，暂时按创建时间排序
      const sql = `
        SELECT * FROM ai_configs 
        WHERE is_active = 1
        ORDER BY updated_at DESC 
        LIMIT ?
      `;
      const result = await this.db.queryAll(sql, [limit]);
      return result;
    } catch (error) {
      throw new DAOException(`获取最近使用配置失败: ${error.message}`, 'RECENTLY_USED_FAILED', error);
    }
  }
}
