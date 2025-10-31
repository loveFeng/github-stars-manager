/**
 * Release DAO
 */

import { BaseDAO } from './base_dao';
import { 
  Release, 
  CreateReleaseData, 
  ReleaseSearchParams 
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';
import { DateUtil } from '../utils/date';

export class ReleaseDAO extends BaseDAO<Release> {
  protected tableName = 'releases';
  protected allowedSortFields = [
    'id', 'tag_name', 'published_at', 'created_at', 'updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建 Release
   */
  async create(data: CreateReleaseData): Promise<Release> {
    try {
      const releaseData = {
        ...data,
        draft: data.draft || false,
        prerelease: data.prerelease || false,
        is_subscribed: data.is_subscribed || false,
        is_read: data.is_read || false
      };

      return await super.create(releaseData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建 Release 失败: ${error.message}`, 'CREATE_RELEASE_FAILED', error);
    }
  }

  /**
   * 根据 GitHub Release ID 查找
   */
  async findByGithubId(githubReleaseId: number): Promise<Release | null> {
    try {
      const sql = 'SELECT * FROM releases WHERE github_release_id = ?';
      const result = await this.db.querySingle(sql, [githubReleaseId]);
      return result || null;
    } catch (error) {
      throw new DAOException(`根据 GitHub ID 查找 Release 失败: ${error.message}`, 'FIND_BY_GITHUB_ID_FAILED', error);
    }
  }

  /**
   * 根据仓库 ID 查找所有 Release
   */
  async findByRepository(repositoryId: number, params?: ReleaseSearchParams): Promise<Release[]> {
    try {
      const searchParams = { ...params, repository_id: repositoryId };
      const result = await this.findPaginated(searchParams);
      return result.data;
    } catch (error) {
      throw new DAOException(`根据仓库查找 Release 失败: ${error.message}`, 'FIND_BY_REPOSITORY_FAILED', error);
    }
  }

  /**
   * 获取仓库的最新 Release
   */
  async getLatestRelease(repositoryId: number): Promise<Release | null> {
    try {
      const sql = `
        SELECT * FROM releases 
        WHERE repository_id = ? AND draft = 0
        ORDER BY published_at DESC, created_at DESC
        LIMIT 1
      `;
      const result = await this.db.querySingle(sql, [repositoryId]);
      return result || null;
    } catch (error) {
      throw new DAOException(`获取最新 Release 失败: ${error.message}`, 'GET_LATEST_RELEASE_FAILED', error);
    }
  }

  /**
   * 获取未读的 Release
   */
  async getUnreadReleases(userId?: number): Promise<Release[]> {
    try {
      let sql = `
        SELECT DISTINCT r.*
        FROM releases r
        JOIN repositories rep ON r.repository_id = rep.id
        WHERE r.is_read = 0 AND r.draft = 0
      `;
      const params: any[] = [];

      if (userId) {
        sql += ' AND rep.user_id = ?';
        params.push(userId);
      }

      sql += ' ORDER BY r.published_at DESC, r.created_at DESC';

      const result = await this.db.queryAll(sql, params);
      return result;
    } catch (error) {
      throw new DAOException(`获取未读 Release 失败: ${error.message}`, 'GET_UNREAD_RELEASES_FAILED', error);
    }
  }

  /**
   * 获取订阅的 Release
   */
  async getSubscribedReleases(userId?: number): Promise<Release[]> {
    try {
      let sql = `
        SELECT DISTINCT r.*
        FROM releases r
        JOIN repositories rep ON r.repository_id = rep.id
        WHERE r.is_subscribed = 1 AND r.draft = 0
      `;
      const params: any[] = [];

      if (userId) {
        sql += ' AND rep.user_id = ?';
        params.push(userId);
      }

      sql += ' ORDER BY r.published_at DESC, r.created_at DESC';

      const result = await this.db.queryAll(sql, params);
      return result;
    } catch (error) {
      throw new DAOException(`获取订阅 Release 失败: ${error.message}`, 'GET_SUBSCRIBED_RELEASES_FAILED', error);
    }
  }

  /**
   * 获取预发布版本
   */
  async getPrereleases(userId?: number): Promise<Release[]> {
    try {
      let sql = `
        SELECT DISTINCT r.*
        FROM releases r
        JOIN repositories rep ON r.repository_id = rep.id
        WHERE r.prerelease = 1 AND r.draft = 0
      `;
      const params: any[] = [];

      if (userId) {
        sql += ' AND rep.user_id = ?';
        params.push(userId);
      }

      sql += ' ORDER BY r.published_at DESC, r.created_at DESC';

      const result = await this.db.queryAll(sql, params);
      return result;
    } catch (error) {
      throw new DAOException(`获取预发布版本失败: ${error.message}`, 'GET_PRERELEASES_FAILED', error);
    }
  }

  /**
   * 搜索 Release
   */
  async searchReleases(params?: ReleaseSearchParams): Promise<Release[]> {
    try {
      const searchFields = params?.searchFields || ['tag_name', 'name', 'body'];
      const result = await this.findPaginated({
        ...params,
        query: params?.query,
        searchFields
      });
      return result.data;
    } catch (error) {
      throw new DAOException(`搜索 Release 失败: ${error.message}`, 'SEARCH_RELEASES_FAILED', error);
    }
  }

  /**
   * 按时间范围查找 Release
   */
  async findByDateRange(startDate: Date, endDate: Date, params?: ReleaseSearchParams): Promise<Release[]> {
    try {
      const searchParams = {
        ...params,
        published_after: DateUtil.formatForSQLite(startDate),
        published_before: DateUtil.formatForSQLite(endDate)
      };
      const result = await this.findPaginated(searchParams);
      return result.data;
    } catch (error) {
      throw new DAOException(`按时间范围查找 Release 失败: ${error.message}`, 'FIND_BY_DATE_RANGE_FAILED', error);
    }
  }

  /**
   * 标记 Release 为已读
   */
  async markAsRead(releaseId: number): Promise<boolean> {
    try {
      const sql = 'UPDATE releases SET is_read = 1 WHERE id = ?';
      const result = await this.db.update(sql, [releaseId]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`标记已读失败: ${error.message}`, 'MARK_AS_READ_FAILED', error);
    }
  }

  /**
   * 订阅/取消订阅 Release
   */
  async setSubscription(releaseId: number, subscribed: boolean): Promise<boolean> {
    try {
      const sql = 'UPDATE releases SET is_subscribed = ? WHERE id = ?';
      const result = await this.db.update(sql, [subscribed ? 1 : 0, releaseId]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`设置订阅状态失败: ${error.message}`, 'SET_SUBSCRIPTION_FAILED', error);
    }
  }

  /**
   * 批量标记为已读
   */
  async markMultipleAsRead(releaseIds: number[]): Promise<number> {
    try {
      if (releaseIds.length === 0) return 0;

      const placeholders = releaseIds.map(() => '?').join(', ');
      const sql = `UPDATE releases SET is_read = 1 WHERE id IN (${placeholders})`;
      const result = await this.db.update(sql, releaseIds);
      return result;
    } catch (error) {
      throw new DAOException(`批量标记已读失败: ${error.message}`, 'MARK_MULTIPLE_READ_FAILED', error);
    }
  }

  /**
   * 同步或创建 Release
   */
  async syncRelease(data: CreateReleaseData): Promise<Release> {
    try {
      // 尝试查找现有 Release
      let release = await this.findByGithubId(data.github_release_id);

      if (release) {
        // 更新现有 Release
        const updateData = {
          name: data.name,
          body: data.body,
          draft: data.draft,
          prerelease: data.prerelease,
          published_at: data.published_at,
          html_url: data.html_url,
          zipball_url: data.zipball_url,
          tarball_url: data.tarball_url,
          target_commitish: data.target_commitish,
          author_login: data.author_login,
          author_avatar_url: data.author_avatar_url
        };

        release = await this.update(release.id!, updateData);
      } else {
        // 创建新 Release
        release = await this.create(data);
      }

      return release;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`同步 Release 失败: ${error.message}`, 'SYNC_RELEASE_FAILED', error);
    }
  }

  /**
   * 获取 Release 统计信息
   */
  async getReleaseStats(): Promise<{
    totalReleases: number;
    draftReleases: number;
    prereleaseCount: number;
    publishedCount: number;
    subscribedCount: number;
    unreadCount: number;
    releasesThisMonth: number;
    averageReleasesPerRepo: number;
    topReleasingRepos: Array<{ repositoryName: string; releaseCount: number }>;
  }> {
    try {
      const stats = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_releases,
          SUM(CASE WHEN draft = 1 THEN 1 ELSE 0 END) as draft_releases,
          SUM(CASE WHEN prerelease = 1 THEN 1 ELSE 0 END) as prerelease_count,
          SUM(CASE WHEN draft = 0 THEN 1 ELSE 0 END) as published_count,
          SUM(CASE WHEN is_subscribed = 1 THEN 1 ELSE 0 END) as subscribed_count,
          SUM(CASE WHEN is_read = 0 AND draft = 0 THEN 1 ELSE 0 END) as unread_count,
          SUM(CASE WHEN created_at >= date('now', 'start of month') THEN 1 ELSE 0 END) as releases_this_month
        FROM releases
      `);

      const repoStats = await this.db.querySingle(`
        SELECT 
          COUNT(DISTINCT repository_id) as unique_repos,
          AVG(release_count) as avg_releases_per_repo
        FROM (
          SELECT repository_id, COUNT(*) as release_count
          FROM releases
          WHERE draft = 0
          GROUP BY repository_id
        )
      `);

      const topReleasing = await this.db.queryAll(`
        SELECT 
          r.full_name as repository_name,
          COUNT(rel.id) as release_count
        FROM repositories r
        LEFT JOIN releases rel ON r.id = rel.repository_id AND rel.draft = 0
        GROUP BY r.id, r.full_name
        HAVING release_count > 0
        ORDER BY release_count DESC
        LIMIT 10
      `);

      return {
        totalReleases: stats.total_releases || 0,
        draftReleases: stats.draft_releases || 0,
        prereleaseCount: stats.prerelease_count || 0,
        publishedCount: stats.published_count || 0,
        subscribedCount: stats.subscribed_count || 0,
        unreadCount: stats.unread_count || 0,
        releasesThisMonth: stats.releases_this_month || 0,
        averageReleasesPerRepo: Math.round((repoStats.avg_releases_per_repo || 0) * 100) / 100,
        topReleasingRepos: topReleasing
      };
    } catch (error) {
      throw new DAOException(`获取 Release 统计失败: ${error.message}`, 'RELEASE_STATS_FAILED', error);
    }
  }

  /**
   * 获取活跃的发布仓库
   */
  async getActiveReleasingRepositories(limit: number = 20): Promise<Array<{
    repositoryId: number;
    repositoryName: string;
    lastReleaseDate: string;
    releaseCount: number;
    latestVersion?: string;
  }>> {
    try {
      const sql = `
        SELECT 
          r.id as repository_id,
          r.full_name as repository_name,
          MAX(rel.published_at) as last_release_date,
          COUNT(rel.id) as release_count,
          MAX(rel.tag_name) as latest_version
        FROM repositories r
        LEFT JOIN releases rel ON r.id = rel.repository_id AND rel.draft = 0
        GROUP BY r.id, r.full_name
        HAVING release_count > 0
        ORDER BY last_release_date DESC
        LIMIT ?
      `;

      const result = await this.db.queryAll(sql, [limit]);
      return result;
    } catch (error) {
      throw new DAOException(`获取活跃发布仓库失败: ${error.message}`, 'ACTIVE_RELEASING_REPOS_FAILED', error);
    }
  }

  /**
   * 清理过期的 Release
   */
  async cleanupOldReleases(daysOld: number = 365): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysOld);

      const sql = `
        DELETE FROM releases 
        WHERE created_at < ? 
        AND draft = 1
      `;

      const result = await this.db.delete(sql, [cutoffDate.toISOString()]);
      return result;
    } catch (error) {
      throw new DAOException(`清理过期 Release 失败: ${error.message}`, 'CLEANUP_OLD_RELEASES_FAILED', error);
    }
  }

  /**
   * 获取版本发布频率
   */
  async getReleaseFrequency(days: number = 30): Promise<Array<{
    date: string;
    releaseCount: number;
  }>> {
    try {
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);

      const sql = `
        SELECT 
          DATE(published_at) as date,
          COUNT(*) as release_count
        FROM releases
        WHERE published_at >= ?
        AND draft = 0
        GROUP BY DATE(published_at)
        ORDER BY date ASC
      `;

      const result = await this.db.queryAll(sql, [startDate.toISOString()]);
      return result;
    } catch (error) {
      throw new DAOException(`获取发布频率失败: ${error.message}`, 'RELEASE_FREQUENCY_FAILED', error);
    }
  }

  /**
   * 获取最近没有发布的仓库
   */
  async getInactiveRepositories(days: number = 90): Promise<Array<{
    repositoryId: number;
    repositoryName: string;
    lastReleaseDate: string;
    daysSinceLastRelease: number;
  }>> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);

      const sql = `
        SELECT 
          r.id as repository_id,
          r.full_name as repository_name,
          COALESCE(MAX(rel.published_at), r.created_at) as last_release_date,
          CASE 
            WHEN MAX(rel.published_at) IS NULL 
            THEN CAST(julianday('now') - julianday(r.created_at) AS INTEGER)
            ELSE CAST(julianday('now') - julianday(MAX(rel.published_at)) AS INTEGER)
          END as days_since_last_release
        FROM repositories r
        LEFT JOIN releases rel ON r.id = rel.repository_id AND rel.draft = 0
        GROUP BY r.id, r.full_name, r.created_at
        HAVING days_since_last_release > ?
        ORDER BY days_since_last_release DESC
      `;

      const result = await this.db.queryAll(sql, [days]);
      return result;
    } catch (error) {
      throw new DAOException(`获取不活跃仓库失败: ${error.message}`, 'INACTIVE_REPOSITORIES_FAILED', error);
    }
  }
}
