/**
 * 仓库 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  Repository, 
  CreateRepositoryData, 
  UpdateRepositoryData, 
  RepositorySearchParams,
  parseJSONField,
  stringifyJSONField
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';
import { DateUtil } from '../utils/date';

export class RepositoryDAO extends BaseDAO<Repository> {
  protected tableName = 'repositories';
  protected allowedSortFields = [
    'id', 'owner', 'name', 'full_name', 'stars_count', 'forks_count', 
    'watchers_count', 'size_kb', 'created_at', 'updated_at', 'last_updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建仓库记录
   */
  async create(data: CreateRepositoryData): Promise<Repository> {
    try {
      const repositoryData = {
        ...data,
        first_seen_at: DateUtil.formatForSQLite(new Date()),
        last_updated_at: DateUtil.formatForSQLite(new Date())
      };

      return await super.create(repositoryData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建仓库失败: ${error.message}`, 'CREATE_REPOSITORY_FAILED', error);
    }
  }

  /**
   * 根据 GitHub ID 查找仓库
   */
  async findByGithubId(githubId: number): Promise<Repository | null> {
    try {
      const sql = 'SELECT * FROM repositories WHERE github_id = ?';
      const result = await this.db.querySingle(sql, [githubId]);
      return this._processRepository(result);
    } catch (error) {
      throw new DAOException(`根据 GitHub ID 查找仓库失败: ${error.message}`, 'FIND_BY_GITHUB_ID_FAILED', error);
    }
  }

  /**
   * 根据 owner 和 name 查找仓库
   */
  async findByOwnerAndName(owner: string, name: string): Promise<Repository | null> {
    try {
      const sql = 'SELECT * FROM repositories WHERE owner = ? AND name = ?';
      const result = await this.db.querySingle(sql, [owner, name]);
      return this._processRepository(result);
    } catch (error) {
      throw new DAOException(`根据 owner/name 查找仓库失败: ${error.message}`, 'FIND_BY_OWNER_NAME_FAILED', error);
    }
  }

  /**
   * 搜索仓库
   */
  async searchRepositories(params?: RepositorySearchParams): Promise<Repository[]> {
    try {
      const searchFields = params?.searchFields || ['owner', 'name', 'full_name', 'description'];
      const result = await this.findPaginated({
        ...params,
        query: params?.query,
        searchFields
      });
      return result.data.map(repo => this._processRepository(repo));
    } catch (error) {
      throw new DAOException(`搜索仓库失败: ${error.message}`, 'SEARCH_REPOSITORIES_FAILED', error);
    }
  }

  /**
   * 按编程语言查找仓库
   */
  async findByLanguage(language: string, params?: SearchParams): Promise<Repository[]> {
    try {
      const searchParams = { ...params, language };
      const result = await this.findPaginated(searchParams);
      return result.data.map(repo => this._processRepository(repo));
    } catch (error) {
      throw new DAOException(`按语言查找仓库失败: ${error.message}`, 'FIND_BY_LANGUAGE_FAILED', error);
    }
  }

  /**
   * 按 Star 数量范围查找仓库
   */
  async findByStarRange(minStars: number, maxStars?: number, params?: SearchParams): Promise<Repository[]> {
    try {
      let sql = 'SELECT * FROM repositories WHERE stars_count >= ?';
      const params_ = [minStars];
      
      if (maxStars !== undefined) {
        sql += ' AND stars_count <= ?';
        params_.push(maxStars);
      }

      sql += ' ORDER BY stars_count DESC';
      
      if (params?.limit) {
        sql += ' LIMIT ?';
        params_.push(params.limit);
      }

      const result = await this.db.queryAll(sql, params_);
      return result.map(repo => this._processRepository(repo));
    } catch (error) {
      throw new DAOException(`按 Star 范围查找仓库失败: ${error.message}`, 'FIND_BY_STARS_FAILED', error);
    }
  }

  /**
   * 按用户评分查找仓库
   */
  async findByRating(rating: number, params?: SearchParams): Promise<Repository[]> {
    try {
      const searchParams = { ...params, user_rating: rating };
      const result = await this.findPaginated(searchParams);
      return result.data.map(repo => this._processRepository(repo));
    } catch (error) {
      throw new DAOException(`按评分查找仓库失败: ${error.message}`, 'FIND_BY_RATING_FAILED', error);
    }
  }

  /**
   * 获取最近更新的仓库
   */
  async getRecentlyUpdated(limit: number = 20): Promise<Repository[]> {
    try {
      const sql = `
        SELECT * FROM repositories 
        ORDER BY last_updated_at DESC 
        LIMIT ?
      `;
      const result = await this.db.queryAll(sql, [limit]);
      return result.map(repo => this._processRepository(repo));
    } catch (error) {
      throw new DAOException(`获取最近更新仓库失败: ${error.message}`, 'RECENTLY_UPDATED_FAILED', error);
    }
  }

  /**
   * 获取热门仓库（按 Star 数量）
   */
  async getPopularRepositories(limit: number = 20, minStars: number = 100): Promise<Repository[]> {
    try {
      const sql = `
        SELECT * FROM repositories 
        WHERE stars_count >= ? 
        ORDER BY stars_count DESC 
        LIMIT ?
      `;
      const result = await this.db.queryAll(sql, [minStars, limit]);
      return result.map(repo => this._processRepository(repo));
    } catch (error) {
      throw new DAOException(`获取热门仓库失败: ${error.message}`, 'POPULAR_REPOS_FAILED', error);
    }
  }

  /**
   * 统计语言分布
   */
  async getLanguageStatistics(): Promise<Array<{ language: string; count: number; percentage: number }>> {
    try {
      const totalResult = await this.db.querySingle('SELECT COUNT(*) as total FROM repositories');
      const total = totalResult.total || 0;

      if (total === 0) return [];

      const languageStats = await this.db.queryAll(`
        SELECT 
          language,
          COUNT(*) as count,
          ROUND(COUNT(*) * 100.0 / ?, 2) as percentage
        FROM repositories 
        WHERE language IS NOT NULL AND language != ''
        GROUP BY language 
        ORDER BY count DESC
      `, [total]);

      return languageStats;
    } catch (error) {
      throw new DAOException(`获取语言统计失败: ${error.message}`, 'LANGUAGE_STATS_FAILED', error);
    }
  }

  /**
   * 获取仓库统计摘要
   */
  async getRepositorySummary(): Promise<{
    totalRepositories: number;
    totalStars: number;
    totalForks: number;
    topLanguages: Array<{ language: string; count: number }>;
    archivedCount: number;
    privateCount: number;
    averageStars: number;
  }> {
    try {
      const summary = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_repositories,
          SUM(stars_count) as total_stars,
          SUM(forks_count) as total_forks,
          SUM(CASE WHEN archived = 1 THEN 1 ELSE 0 END) as archived_count,
          SUM(CASE WHEN is_private = 1 THEN 1 ELSE 0 END) as private_count,
          AVG(stars_count) as average_stars
        FROM repositories
      `);

      const topLanguages = await this.db.queryAll(`
        SELECT language, COUNT(*) as count
        FROM repositories 
        WHERE language IS NOT NULL AND language != ''
        GROUP BY language 
        ORDER BY count DESC 
        LIMIT 10
      `);

      return {
        totalRepositories: summary.total_repositories || 0,
        totalStars: summary.total_stars || 0,
        totalForks: summary.total_forks || 0,
        topLanguages,
        archivedCount: summary.archived_count || 0,
        privateCount: summary.private_count || 0,
        averageStars: Math.round(summary.average_stars || 0)
      };
    } catch (error) {
      throw new DAOException(`获取仓库摘要失败: ${error.message}`, 'REPOSITORY_SUMMARY_FAILED', error);
    }
  }

  /**
   * 批量更新仓库统计信息
   */
  async batchUpdateStats(updates: Array<{
    github_id: number;
    stars_count?: number;
    forks_count?: number;
    watchers_count?: number;
    open_issues_count?: number;
    size_kb?: number;
    last_updated_at?: string;
  }>): Promise<number> {
    try {
      let updatedCount = 0;

      await this.db.executeInTransaction(async (tx) => {
        for (const update of updates) {
          const { github_id, ...stats } = update;
          const updateData = {
            ...stats,
            last_updated_at: stats.last_updated_at || DateUtil.formatForSQLite(new Date())
          };

          const fields = Object.keys(updateData);
          const assignments = fields.map(field => `${field} = ?`).join(', ');
          const values = Object.values(updateData);

          const sql = `UPDATE repositories SET ${assignments} WHERE github_id = ?`;
          const result = await tx.run(sql, [...values, github_id]);
          
          if (result.changes > 0) {
            updatedCount++;
          }
        }
      });

      return updatedCount;
    } catch (error) {
      throw new DAOException(`批量更新统计信息失败: ${error.message}`, 'BATCH_UPDATE_STATS_FAILED', error);
    }
  }

  /**
   * 同步或创建仓库
   */
  async syncRepository(data: CreateRepositoryData): Promise<Repository> {
    try {
      // 尝试查找现有仓库
      let repository = await this.findByGithubId(data.github_id);

      if (repository) {
        // 更新现有仓库
        const updateData: UpdateRepositoryData = {
          description: data.description,
          language: data.language,
          languages: data.languages,
          topics: data.topics,
          stars_count: data.stars_count,
          forks_count: data.forks_count,
          watchers_count: data.watchers_count,
          open_issues_count: data.open_issues_count,
          size_kb: data.size_kb,
          license: data.license,
          default_branch: data.default_branch,
          archived: data.archived,
          disabled: data.disabled,
          is_private: data.is_private,
          last_updated_at: DateUtil.formatForSQLite(new Date())
        };

        repository = await this.update(repository.id!, updateData);
      } else {
        // 创建新仓库
        repository = await this.create(data);
      }

      return repository;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`同步仓库失败: ${error.message}`, 'SYNC_REPOSITORY_FAILED', error);
    }
  }

  /**
   * 获取仓库及其分类
   */
  async getRepositoryWithCategories(repositoryId: number): Promise<{
    repository: Repository;
    categories: Array<{ id: number; name: string; color: string; confidence?: number }>;
  }> {
    try {
      const repository = await this.findById(repositoryId);
      if (!repository) {
        throw new DAOException('仓库不存在', 'REPOSITORY_NOT_FOUND');
      }

      const categories = await this.db.queryAll(`
        SELECT c.id, c.name, c.color, rc.confidence
        FROM repository_categories rc
        JOIN categories c ON rc.category_id = c.id
        WHERE rc.repository_id = ?
        ORDER BY c.sort_order ASC, c.name ASC
      `, [repositoryId]);

      return {
        repository: this._processRepository(repository),
        categories
      };
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`获取仓库分类失败: ${error.message}`, 'GET_REPO_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 清理过期的仓库
   */
  async cleanupOldRepositories(daysOld: number = 365): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysOld);

      const sql = `
        DELETE FROM repositories 
        WHERE last_updated_at < ? 
        AND disabled = 1
      `;

      const result = await this.db.delete(sql, [cutoffDate.toISOString()]);
      return result;
    } catch (error) {
      throw new DAOException(`清理过期仓库失败: ${error.message}`, 'CLEANUP_REPOS_FAILED', error);
    }
  }

  /**
   * 处理仓库数据（解析 JSON 字段）
   */
  private _processRepository(repository: Repository | null): Repository | null {
    if (!repository) return null;

    return {
      ...repository,
      languages: repository.languages ? parseJSONField(repository.languages) : null,
      topics: repository.topics ? parseJSONField(repository.topics) : null
    };
  }

  /**
   * 搜索仓库（支持全文搜索）
   */
  async fullTextSearch(query: string, limit: number = 50): Promise<Repository[]> {
    try {
      // 使用 FTS5 进行全文搜索
      const sql = `
        SELECT r.*
        FROM repositories r
        JOIN repositories_fts fts ON r.id = fts.rowid
        WHERE repositories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
      `;

      const result = await this.db.queryAll(sql, [query, limit]);
      return result.map(repo => this._processRepository(repo));
    } catch (error) {
      // 如果 FTS 不可用，回退到 LIKE 搜索
      return this.searchRepositories({
        query,
        limit,
        searchFields: ['full_name', 'description', 'topics']
      });
    }
  }
}
