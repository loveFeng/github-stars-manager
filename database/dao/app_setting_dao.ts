/**
 * 应用设置 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  AppSetting, 
  CreateAppSettingData, 
  UpdateAppSettingData,
  parseJSONField,
  stringifyJSONField
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';
import { CryptoUtil } from '../utils/crypto';

export class AppSettingDAO extends BaseDAO<AppSetting> {
  protected tableName = 'app_settings';
  protected allowedSortFields = [
    'id', 'setting_key', 'data_type', 'created_at', 'updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建设置
   */
  async create(data: CreateAppSettingData): Promise<AppSetting> {
    try {
      const settingData = {
        ...data,
        data_type: data.data_type || 'string',
        is_encrypted: data.is_encrypted || false
      };

      // 如果需要加密，加密设置值
      if (settingData.is_encrypted && settingData.setting_value) {
        settingData.setting_value = CryptoUtil.encrypt(settingData.setting_value);
      }

      return await super.create(settingData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建设置失败: ${error.message}`, 'CREATE_SETTING_FAILED', error);
    }
  }

  /**
   * 根据键查找设置
   */
  async findByKey(key: string): Promise<AppSetting | null> {
    try {
      const sql = 'SELECT * FROM app_settings WHERE setting_key = ?';
      const result = await this.db.querySingle(sql, [key]);
      return result ? this._processSetting(result) : null;
    } catch (error) {
      throw new DAOException(`根据键查找设置失败: ${error.message}`, 'FIND_BY_KEY_FAILED', error);
    }
  }

  /**
   * 获取多个设置值
   */
  async getSettings(keys: string[]): Promise<Record<string, any>> {
    try {
      if (keys.length === 0) return {};

      const placeholders = keys.map(() => '?').join(', ');
      const sql = `SELECT * FROM app_settings WHERE setting_key IN (${placeholders})`;
      const result = await this.db.queryAll(sql, keys);

      const settings: Record<string, any> = {};
      result.forEach(setting => {
        const processed = this._processSetting(setting);
        settings[processed.setting_key] = processed.setting_value;
      });

      return settings;
    } catch (error) {
      throw new DAOException(`获取设置失败: ${error.message}`, 'GET_SETTINGS_FAILED', error);
    }
  }

  /**
   * 设置或更新设置值
   */
  async setSetting(key: string, value: any, dataType: 'string' | 'number' | 'boolean' | 'json' = 'string', description?: string): Promise<AppSetting> {
    try {
      // 检查设置是否已存在
      let setting = await this.findByKey(key);

      let settingValue: string;
      if (dataType === 'json') {
        settingValue = JSON.stringify(value);
      } else if (dataType === 'boolean') {
        settingValue = value ? 'true' : 'false';
      } else if (dataType === 'number') {
        settingValue = String(value);
      } else {
        settingValue = String(value);
      }

      const updateData = {
        setting_value: settingValue,
        data_type: dataType,
        description: description || setting?.description
      };

      if (setting) {
        // 更新现有设置
        return await this.update(setting.id!, updateData);
      } else {
        // 创建新设置
        return await this.create({
          setting_key: key,
          setting_value: settingValue,
          data_type: dataType,
          description
        });
      }
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`设置值失败: ${error.message}`, 'SET_SETTING_FAILED', error);
    }
  }

  /**
   * 批量设置多个设置
   */
  async setSettings(settings: Record<string, any>): Promise<void> {
    try {
      await this.db.executeInTransaction(async (tx) => {
        for (const [key, value] of Object.entries(settings)) {
          await this.setSetting(key, value);
        }
      });
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`批量设置失败: ${error.message}`, 'SET_SETTINGS_FAILED', error);
    }
  }

  /**
   * 获取设置值（带类型转换）
   */
  async getSettingValue<T = any>(key: string, defaultValue?: T): Promise<T | undefined> {
    try {
      const setting = await this.findByKey(key);
      
      if (!setting) {
        return defaultValue;
      }

      const value = setting.setting_value;
      if (!value) {
        return defaultValue;
      }

      switch (setting.data_type) {
        case 'boolean':
          return value === 'true' ? true : value === 'false' ? false : !!value;
        case 'number':
          const num = parseFloat(value);
          return isNaN(num) ? defaultValue : num;
        case 'json':
          try {
            return JSON.parse(value);
          } catch {
            return defaultValue;
          }
        case 'string':
        default:
          return value as T;
      }
    } catch (error) {
      throw new DAOException(`获取设置值失败: ${error.message}`, 'GET_SETTING_VALUE_FAILED', error);
    }
  }

  /**
   * 删除设置
   */
  async deleteSetting(key: string): Promise<boolean> {
    try {
      const sql = 'DELETE FROM app_settings WHERE setting_key = ?';
      const result = await this.db.delete(sql, [key]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`删除设置失败: ${error.message}`, 'DELETE_SETTING_FAILED', error);
    }
  }

  /**
   * 检查设置是否存在
   */
  async hasSetting(key: string): Promise<boolean> {
    try {
      const setting = await this.findByKey(key);
      return !!setting;
    } catch (error) {
      throw new DAOException(`检查设置存在性失败: ${error.message}`, 'HAS_SETTING_FAILED', error);
    }
  }

  /**
   * 获取所有设置（按分类）
   */
  async getAllSettings(): Promise<{
    userSettings: Record<string, any>;
    systemSettings: Record<string, any>;
    encryptedSettings: string[];
  }> {
    try {
      const sql = 'SELECT * FROM app_settings ORDER BY setting_key';
      const result = await this.db.queryAll(sql);

      const userSettings: Record<string, any> = {};
      const systemSettings: Record<string, any> = {};
      const encryptedSettings: string[] = [];

      result.forEach(setting => {
        const processed = this._processSetting(setting);
        const value = processed.setting_value;
        
        // 跳过敏感设置值显示
        if (processed.is_encrypted) {
          encryptedSettings.push(processed.setting_key);
          return;
        }

        const settingsObj = setting.setting_key.startsWith('system.') ? systemSettings : userSettings;
        settingsObj[processed.setting_key] = value;
      });

      return {
        userSettings,
        systemSettings,
        encryptedSettings
      };
    } catch (error) {
      throw new DAOException(`获取所有设置失败: ${error.message}`, 'GET_ALL_SETTINGS_FAILED', error);
    }
  }

  /**
   * 重置设置到默认值
   */
  async resetToDefaults(): Promise<void> {
    try {
      const defaultSettings = {
        // UI 设置
        'theme': 'system',
        'language': 'zh-CN',
        
        // 同步设置
        'auto_sync_releases': true,
        'sync_interval_minutes': 60,
        'max_retry_attempts': 3,
        
        // AI 设置
        'auto_ai_analysis': true,
        'ai_analysis_confidence_threshold': 0.7,
        
        // Release 设置
        'show_prerelease': false,
        'default_sort_field': 'updated_at',
        'default_sort_order': 'desc',
        
        // 搜索设置
        'search_results_limit': 50,
        
        // 备份设置
        'backup_on_exit': false,
        
        // 系统设置
        'db_version': '1.0',
        'init_completed': true
      };

      await this.setSettings(defaultSettings);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`重置默认设置失败: ${error.message}`, 'RESET_DEFAULTS_FAILED', error);
    }
  }

  /**
   * 导出设置
   */
  async exportSettings(): Promise<Record<string, any>> {
    try {
      const sql = 'SELECT setting_key, setting_value, data_type FROM app_settings WHERE is_encrypted = 0';
      const result = await this.db.queryAll(sql);

      const exported: Record<string, any> = {};
      result.forEach(setting => {
        const value = setting.setting_value;
        
        switch (setting.data_type) {
          case 'boolean':
            exported[setting.setting_key] = value === 'true';
            break;
          case 'number':
            exported[setting.setting_key] = parseFloat(value);
            break;
          case 'json':
            try {
              exported[setting.setting_key] = JSON.parse(value);
            } catch {
              exported[setting.setting_key] = value;
            }
            break;
          case 'string':
          default:
            exported[setting.setting_key] = value;
            break;
        }
      });

      return exported;
    } catch (error) {
      throw new DAOException(`导出设置失败: ${error.message}`, 'EXPORT_SETTINGS_FAILED', error);
    }
  }

  /**
   * 导入设置
   */
  async importSettings(settings: Record<string, any>): Promise<{
    imported: number;
    skipped: number;
    errors: string[];
  }> {
    try {
      let imported = 0;
      let skipped = 0;
      const errors: string[] = [];

      await this.db.executeInTransaction(async (tx) => {
        for (const [key, value] of Object.entries(settings)) {
          try {
            // 跳过敏感设置
            if (key.includes('password') || key.includes('token') || key.includes('key')) {
              skipped++;
              continue;
            }

            await this.setSetting(key, value);
            imported++;
          } catch (error) {
            errors.push(`设置 ${key}: ${error.message}`);
          }
        }
      });

      return { imported, skipped, errors };
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`导入设置失败: ${error.message}`, 'IMPORT_SETTINGS_FAILED', error);
    }
  }

  /**
   * 获取设置统计信息
   */
  async getSettingsStats(): Promise<{
    totalSettings: number;
    byDataType: Record<string, number>;
    encryptedCount: number;
    recentlyModified: Array<{ key: string; modifiedAt: string }>;
  }> {
    try {
      const total = await this.count();

      const byDataType = await this.db.queryAll(`
        SELECT data_type, COUNT(*) as count
        FROM app_settings
        GROUP BY data_type
      `);

      const encryptedCount = await this.db.querySingle(`
        SELECT COUNT(*) as count
        FROM app_settings
        WHERE is_encrypted = 1
      `);

      const recentlyModified = await this.db.queryAll(`
        SELECT setting_key, updated_at
        FROM app_settings
        WHERE updated_at >= date('now', '-7 days')
        ORDER BY updated_at DESC
        LIMIT 10
      `);

      const typeStats: Record<string, number> = {};
      byDataType.forEach(item => {
        typeStats[item.data_type] = item.count;
      });

      return {
        totalSettings: total,
        byDataType: typeStats,
        encryptedCount: encryptedCount.count || 0,
        recentlyModified
      };
    } catch (error) {
      throw new DAOException(`获取设置统计失败: ${error.message}`, 'SETTINGS_STATS_FAILED', error);
    }
  }

  /**
   * 清理过期设置
   */
  async cleanupExpiredSettings(): Promise<number> {
    try {
      // 这里可以添加基于设置键前缀的清理逻辑
      const sql = `
        DELETE FROM app_settings 
        WHERE setting_key LIKE 'temp_%' 
        OR setting_key LIKE 'cache_%'
      `;
      
      const result = await this.db.delete(sql);
      return result;
    } catch (error) {
      throw new DAOException(`清理过期设置失败: ${error.message}`, 'CLEANUP_EXPIRED_FAILED', error);
    }
  }

  /**
   * 处理设置数据（解析 JSON 和解密）
   */
  private _processSetting(setting: AppSetting): AppSetting {
    let processedValue = setting.setting_value;

    // 如果是加密的，返回密文（不解密以保护敏感信息）
    if (setting.is_encrypted) {
      return {
        ...setting,
        setting_value: processedValue
      };
    }

    // 解析 JSON 和数据类型转换
    try {
      switch (setting.data_type) {
        case 'boolean':
          processedValue = setting.setting_value === 'true' ? true : setting.setting_value === 'false' ? false : !!setting.setting_value;
          break;
        case 'number':
          processedValue = parseFloat(setting.setting_value || '0');
          break;
        case 'json':
          processedValue = parseJSONField(setting.setting_value);
          break;
        case 'string':
        default:
          // 字符串类型不需要额外处理
          break;
      }
    } catch (error) {
      // 如果解析失败，返回原始值
      processedValue = setting.setting_value;
    }

    return {
      ...setting,
      setting_value: processedValue
    };
  }
}
