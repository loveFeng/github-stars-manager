/**
 * 资产过滤器 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  AssetFilter, 
  CreateAssetFilterData, 
  AssetFilterSearchParams,
  parseJSONField,
  stringifyJSONField
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';

export class AssetFilterDAO extends BaseDAO<AssetFilter> {
  protected tableName = 'asset_filters';
  protected allowedSortFields = [
    'id', 'name', 'sort_order', 'match_type', 'created_at', 'updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建资产过滤器
   */
  async create(data: CreateAssetFilterData): Promise<AssetFilter> {
    try {
      const filterData = {
        ...data,
        match_type: data.match_type || 'keyword',
        case_sensitive: data.case_sensitive || false,
        is_active: data.is_active !== false,
        sort_order: data.sort_order || 0
      };

      // 解析关键词 JSON
      if (typeof filterData.keywords === 'string') {
        // 如果已经是 JSON 字符串，保持不变
        try {
          JSON.parse(filterData.keywords);
        } catch {
          // 如果不是有效的 JSON，则包装为数组
          filterData.keywords = JSON.stringify([filterData.keywords]);
        }
      } else if (Array.isArray(filterData.keywords)) {
        filterData.keywords = JSON.stringify(filterData.keywords);
      }

      return await super.create(filterData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建过滤器失败: ${error.message}`, 'CREATE_FILTER_FAILED', error);
    }
  }

  /**
   * 获取活跃的过滤器
   */
  async getActiveFilters(userId?: number): Promise<AssetFilter[]> {
    try {
      let sql = `
        SELECT * FROM asset_filters 
        WHERE is_active = 1
      `;
      const params: any[] = [];

      if (userId) {
        sql += ' AND (user_id = ? OR user_id IS NULL)';
        params.push(userId);
      }

      sql += ' ORDER BY sort_order ASC, name ASC';

      const result = await this.db.queryAll(sql, params);
      return result.map(filter => this._processFilter(filter));
    } catch (error) {
      throw new DAOException(`获取活跃过滤器失败: ${error.message}`, 'GET_ACTIVE_FILTERS_FAILED', error);
    }
  }

  /**
   * 按匹配类型查找过滤器
   */
  async findByMatchType(matchType: 'keyword' | 'regex' | 'extension'): Promise<AssetFilter[]> {
    try {
      const sql = `
        SELECT * FROM asset_filters 
        WHERE match_type = ? AND is_active = 1
        ORDER BY sort_order ASC, name ASC
      `;
      const result = await this.db.queryAll(sql, [matchType]);
      return result.map(filter => this._processFilter(filter));
    } catch (error) {
      throw new DAOException(`按匹配类型查找过滤器失败: ${error.message}`, 'FIND_BY_MATCH_TYPE_FAILED', error);
    }
  }

  /**
   * 获取用户的过滤器
   */
  async getUserFilters(userId: number): Promise<AssetFilter[]> {
    try {
      const sql = `
        SELECT * FROM asset_filters 
        WHERE user_id = ? OR user_id IS NULL
        ORDER BY sort_order ASC, name ASC
      `;
      const result = await this.db.queryAll(sql, [userId]);
      return result.map(filter => this._processFilter(filter));
    } catch (error) {
      throw new DAOException(`获取用户过滤器失败: ${error.message}`, 'GET_USER_FILTERS_FAILED', error);
    }
  }

  /**
   * 获取全局过滤器（用户ID为NULL）
   */
  async getGlobalFilters(): Promise<AssetFilter[]> {
    try {
      const sql = `
        SELECT * FROM asset_filters 
        WHERE user_id IS NULL
        ORDER BY sort_order ASC, name ASC
      `;
      const result = await this.db.queryAll(sql);
      return result.map(filter => this._processFilter(filter));
    } catch (error) {
      throw new DAOException(`获取全局过滤器失败: ${error.message}`, 'GET_GLOBAL_FILTERS_FAILED', error);
    }
  }

  /**
   * 搜索过滤器
   */
  async searchFilters(params?: AssetFilterSearchParams): Promise<AssetFilter[]> {
    try {
      const searchFields = params?.searchFields || ['name', 'description'];
      const result = await this.findPaginated({
        ...params,
        query: params?.query,
        searchFields
      });
      return result.data.map(filter => this._processFilter(filter));
    } catch (error) {
      throw new DAOException(`搜索过滤器失败: ${error.message}`, 'SEARCH_FILTERS_FAILED', error);
    }
  }

  /**
   * 测试过滤器匹配
   */
  async testFilterMatch(filterId: number, testString: string): Promise<{
    matches: boolean;
    matchedKeywords: string[];
    confidence: number;
  }> {
    try {
      const filter = await this.findById(filterId);
      if (!filter) {
        throw new DAOException('过滤器不存在', 'FILTER_NOT_FOUND');
      }

      const keywords = parseJSONField<string[]>(filter.keywords) || [];
      const matchedKeywords: string[] = [];
      let matchCount = 0;

      for (const keyword of keywords) {
        const testValue = filter.case_sensitive ? testString : testString.toLowerCase();
        const keywordValue = filter.case_sensitive ? keyword : keyword.toLowerCase();

        let isMatch = false;
        switch (filter.match_type) {
          case 'keyword':
            isMatch = testValue.includes(keywordValue);
            break;
          case 'regex':
            try {
              const regex = new RegExp(keyword, filter.case_sensitive ? '' : 'i');
              isMatch = regex.test(testString);
            } catch {
              isMatch = false;
            }
            break;
          case 'extension':
            isMatch = testValue.endsWith(`.${keywordValue}`);
            break;
        }

        if (isMatch) {
          matchedKeywords.push(keyword);
          matchCount++;
        }
      }

      const confidence = keywords.length > 0 ? matchCount / keywords.length : 0;
      const matches = matchCount > 0;

      return {
        matches,
        matchedKeywords,
        confidence
      };
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`测试过滤器匹配失败: ${error.message}`, 'TEST_FILTER_MATCH_FAILED', error);
    }
  }

  /**
   * 批量测试过滤器
   */
  async batchTestFilters(filters: AssetFilter[], testString: string): Promise<Array<{
    filter: AssetFilter;
    matches: boolean;
    matchedKeywords: string[];
    confidence: number;
  }>> {
    const results = [];

    for (const filter of filters) {
      const testResult = await this.testFilterMatch(filter.id!, testString);
      results.push({
        filter,
        ...testResult
      });
    }

    return results;
  }

  /**
   * 获取过滤器使用统计
   */
  async getFilterUsageStats(): Promise<{
    totalFilters: number;
    activeFilters: number;
    globalFilters: number;
    userFilters: number;
    matchTypeDistribution: Array<{ matchType: string; count: number }>;
    mostUsedFilters: Array<{ name: string; matchCount: number }>;
  }> {
    try {
      const basicStats = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_filters,
          SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_filters,
          SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as global_filters,
          SUM(CASE WHEN user_id IS NOT NULL THEN 1 ELSE 0 END) as user_filters
        FROM asset_filters
      `);

      // 匹配类型分布
      const matchTypeStats = await this.db.queryAll(`
        SELECT match_type, COUNT(*) as count
        FROM asset_filters
        WHERE is_active = 1
        GROUP BY match_type
        ORDER BY count DESC
      `);

      // 最常用过滤器（基于匹配记录）
      const mostUsed = await this.db.queryAll(`
        SELECT af.name, COUNT(fm.id) as match_count
        FROM asset_filters af
        LEFT JOIN filter_matches fm ON af.id = fm.filter_id
        WHERE af.is_active = 1
        GROUP BY af.id, af.name
        ORDER BY match_count DESC
        LIMIT 10
      `);

      return {
        totalFilters: basicStats.total_filters || 0,
        activeFilters: basicStats.active_filters || 0,
        globalFilters: basicStats.global_filters || 0,
        userFilters: basicStats.user_filters || 0,
        matchTypeDistribution: matchTypeStats,
        mostUsedFilters: mostUsed
      };
    } catch (error) {
      throw new DAOException(`获取过滤器统计失败: ${error.message}`, 'FILTER_USAGE_STATS_FAILED', error);
    }
  }

  /**
   * 验证关键词格式
   */
  validateKeywords(keywords: string | string[], matchType: 'keyword' | 'regex' | 'extension'): {
    isValid: boolean;
    error?: string;
    processedKeywords?: string[];
  } {
    try {
      let keywordArray: string[];

      if (typeof keywords === 'string') {
        try {
          // 尝试解析为 JSON
          keywordArray = JSON.parse(keywords);
        } catch {
          // 如果不是 JSON，则按逗号分割
          keywordArray = keywords.split(',').map(k => k.trim()).filter(k => k.length > 0);
        }
      } else {
        keywordArray = keywords;
      }

      if (keywordArray.length === 0) {
        return { isValid: false, error: '关键词不能为空' };
      }

      // 验证每个关键词
      for (const keyword of keywordArray) {
        if (!keyword || keyword.trim().length === 0) {
          return { isValid: false, error: '关键词不能为空' };
        }

        // 根据匹配类型验证关键词格式
        switch (matchType) {
          case 'regex':
            try {
              new RegExp(keyword);
            } catch {
              return { isValid: false, error: `无效的正则表达式: ${keyword}` };
            }
            break;
          case 'extension':
            if (!keyword.match(/^[a-zA-Z0-9]+$/)) {
              return { isValid: false, error: `无效的扩展名: ${keyword}` };
            }
            break;
          case 'keyword':
            if (keyword.length > 100) {
              return { isValid: false, error: `关键词过长: ${keyword}` };
            }
            break;
        }
      }

      return {
        isValid: true,
        processedKeywords: keywordArray
      };
    } catch (error) {
      return { isValid: false, error: `关键词验证失败: ${error.message}` };
    }
  }

  /**
   * 创建默认过滤器
   */
  async createDefaultFilters(): Promise<AssetFilter[]> {
    try {
      const defaultFilters = [
        {
          name: 'macOS 安装包',
          description: '适用于 macOS 的安装包文件',
          keywords: JSON.stringify(['dmg', 'pkg', 'app', 'mac', 'osx']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 1
        },
        {
          name: 'Windows 安装包',
          description: '适用于 Windows 的安装包文件',
          keywords: JSON.stringify(['exe', 'msi', 'setup', 'win', 'windows']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 2
        },
        {
          name: 'Linux 包',
          description: '适用于 Linux 的安装包',
          keywords: JSON.stringify(['deb', 'rpm', 'AppImage', 'tar.gz', 'zip']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 3
        },
        {
          name: 'ARM 架构',
          description: 'ARM 架构相关的文件',
          keywords: JSON.stringify(['arm64', 'aarch64', 'arm']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 4
        },
        {
          name: '压缩包',
          description: '各种压缩包文件',
          keywords: JSON.stringify(['tar.gz', 'tar.bz2', 'zip', 'rar', '7z']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 5
        },
        {
          name: '源码包',
          description: '源代码压缩包',
          keywords: JSON.stringify(['source', 'src', 'code']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 6
        },
        {
          name: 'Docker 镜像',
          description: 'Docker 相关文件',
          keywords: JSON.stringify(['docker', 'image', 'container']),
          match_type: 'keyword' as const,
          case_sensitive: false,
          is_active: true,
          sort_order: 7
        }
      ];

      const createdFilters = [];
      for (const filterData of defaultFilters) {
        // 检查是否已存在
        const existing = await this.db.querySingle(
          'SELECT id FROM asset_filters WHERE name = ? AND user_id IS NULL',
          [filterData.name]
        );

        if (!existing) {
          const filter = await this.create(filterData);
          createdFilters.push(filter);
        }
      }

      return createdFilters;
    } catch (error) {
      throw new DAOException(`创建默认过滤器失败: ${error.message}`, 'CREATE_DEFAULT_FILTERS_FAILED', error);
    }
  }

  /**
   * 复制过滤器
   */
  async cloneFilter(filterId: number, newName: string, userId?: number): Promise<AssetFilter> {
    try {
      const originalFilter = await this.findById(filterId);
      if (!originalFilter) {
        throw new DAOException('原过滤器不存在', 'FILTER_NOT_FOUND');
      }

      const cloneData = {
        name: newName,
        description: originalFilter.description,
        keywords: originalFilter.keywords,
        match_type: originalFilter.match_type,
        case_sensitive: originalFilter.case_sensitive,
        is_active: originalFilter.is_active,
        sort_order: originalFilter.sort_order,
        user_id: userId
      };

      return await this.create(cloneData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`复制过滤器失败: ${error.message}`, 'CLONE_FILTER_FAILED', error);
    }
  }

  /**
   * 更新过滤器顺序
   */
  async updateSortOrder(filterIds: number[]): Promise<void> {
    try {
      await this.db.executeInTransaction(async (tx) => {
        for (let i = 0; i < filterIds.length; i++) {
          const sql = 'UPDATE asset_filters SET sort_order = ? WHERE id = ?';
          await tx.run(sql, [i + 1, filterIds[i]]);
        }
      });
    } catch (error) {
      throw new DAOException(`更新过滤器顺序失败: ${error.message}`, 'UPDATE_SORT_ORDER_FAILED', error);
    }
  }

  /**
   * 清理未使用的过滤器（没有匹配记录的过滤器）
   */
  async cleanupUnusedFilters(userId?: number): Promise<number> {
    try {
      let sql = `
        DELETE FROM asset_filters 
        WHERE id NOT IN (
          SELECT DISTINCT filter_id 
          FROM filter_matches
          WHERE filter_id IS NOT NULL
        )
      `;
      const params: any[] = [];

      if (userId) {
        sql += ' AND user_id = ?';
        params.push(userId);
      }

      const result = await this.db.delete(sql, params);
      return result;
    } catch (error) {
      throw new DAOException(`清理未使用过滤器失败: ${error.message}`, 'CLEANUP_UNUSED_FILTERS_FAILED', error);
    }
  }

  /**
   * 获取过滤器性能统计
   */
  async getFilterPerformance(): Promise<Array<{
    filter: AssetFilter;
    totalMatches: number;
    recentMatches: number;
    averageConfidence: number;
    lastUsed: string;
  }>> {
    try {
      const sql = `
        SELECT 
          af.*,
          COUNT(fm.id) as total_matches,
          SUM(CASE WHEN fm.created_at >= date('now', '-30 days') THEN 1 ELSE 0 END) as recent_matches,
          AVG(fm.match_score) as average_confidence,
          MAX(fm.created_at) as last_used
        FROM asset_filters af
        LEFT JOIN filter_matches fm ON af.id = fm.filter_id
        GROUP BY af.id
        ORDER BY total_matches DESC, recent_matches DESC
      `;

      const result = await this.db.queryAll(sql);
      return result.map(row => ({
        filter: this._processFilter(row),
        totalMatches: row.total_matches || 0,
        recentMatches: row.recent_matches || 0,
        averageConfidence: Math.round((row.average_confidence || 0) * 100) / 100,
        lastUsed: row.last_used || ''
      }));
    } catch (error) {
      throw new DAOException(`获取过滤器性能失败: ${error.message}`, 'FILTER_PERFORMANCE_FAILED', error);
    }
  }

  /**
   * 处理过滤器数据（解析关键词 JSON）
   */
  private _processFilter(filter: AssetFilter): AssetFilter {
    return {
      ...filter,
      keywords: typeof filter.keywords === 'string' 
        ? parseJSONField<string[]>(filter.keywords) || [] 
        : filter.keywords
    };
  }
}
