/**
 * 用户 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  User, 
  CreateUserData, 
  UserSearchParams 
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { CryptoUtil } from '../utils/crypto';
import { DAOException } from './dao_exception';

export interface UserSearchParams extends SearchParams {
  is_authenticated?: boolean;
}

export class UserDAO extends BaseDAO<User> {
  protected tableName = 'users';
  protected allowedSortFields = ['id', 'username', 'created_at', 'updated_at'];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建用户
   */
  async create(data: CreateUserData): Promise<User> {
    try {
      // 加密 GitHub Token
      let encryptedToken = '';
      if (data.github_token_encrypted) {
        encryptedToken = CryptoUtil.encrypt(data.github_token_encrypted);
      }

      const userData = {
        ...data,
        github_token_encrypted: encryptedToken
      };

      return await super.create(userData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建用户失败: ${error.message}`, 'CREATE_USER_FAILED', error);
    }
  }

  /**
   * 根据 GitHub ID 查找用户
   */
  async findByGithubId(githubId: number): Promise<User | null> {
    try {
      const sql = 'SELECT * FROM users WHERE github_id = ?';
      const result = await this.db.querySingle(sql, [githubId]);
      return result || null;
    } catch (error) {
      throw new DAOException(`根据 GitHub ID 查找用户失败: ${error.message}`, 'FIND_BY_GITHUB_ID_FAILED', error);
    }
  }

  /**
   * 根据用户名查找用户
   */
  async findByUsername(username: string): Promise<User | null> {
    try {
      const sql = 'SELECT * FROM users WHERE username = ?';
      const result = await this.db.querySingle(sql, [username]);
      return result || null;
    } catch (error) {
      throw new DAOException(`根据用户名查找用户失败: ${error.message}`, 'FIND_BY_USERNAME_FAILED', error);
    }
  }

  /**
   * 获取认证用户列表
   */
  async findAuthenticatedUsers(): Promise<User[]> {
    try {
      const sql = 'SELECT * FROM users WHERE is_authenticated = 1 ORDER BY created_at DESC';
      const result = await this.db.queryAll(sql);
      return result;
    } catch (error) {
      throw new DAOException(`获取认证用户失败: ${error.message}`, 'FIND_AUTHENTICATED_FAILED', error);
    }
  }

  /**
   * 搜索用户
   */
  async searchUsers(params?: UserSearchParams): Promise<User[]> {
    try {
      const searchFields = params?.searchFields || ['username', 'name', 'email'];
      const result = await this.findPaginated({
        ...params,
        query: params?.query,
        searchFields
      });
      return result.data;
    } catch (error) {
      throw new DAOException(`搜索用户失败: ${error.message}`, 'SEARCH_USERS_FAILED', error);
    }
  }

  /**
   * 认证用户
   */
  async authenticateUser(githubId: number, token: string): Promise<User> {
    try {
      // 查找用户
      let user = await this.findByGithubId(githubId);
      
      if (!user) {
        // 创建新用户
        user = await this.create({
          github_id: githubId,
          username: `user_${githubId}`, // 临时用户名，实际应该从 GitHub API 获取
          is_authenticated: true,
          github_token_encrypted: token
        });
      } else {
        // 更新现有用户
        const encryptedToken = CryptoUtil.encrypt(token);
        user = await this.update(user.id!, {
          is_authenticated: true,
          github_token_encrypted: encryptedToken
        });
      }

      return user;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`用户认证失败: ${error.message}`, 'AUTHENTICATE_USER_FAILED', error);
    }
  }

  /**
   * 取消用户认证
   */
  async deauthenticateUser(userId: number): Promise<boolean> {
    try {
      const result = await this.update(userId, {
        is_authenticated: false,
        github_token_encrypted: null
      });
      return true;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`取消用户认证失败: ${error.message}`, 'DEAUTHENTICATE_USER_FAILED', error);
    }
  }

  /**
   * 更新用户信息
   */
  async updateUserProfile(userId: number, profileData: {
    username?: string;
    name?: string;
    email?: string;
    avatar_url?: string;
  }): Promise<User> {
    try {
      return await this.update(userId, profileData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`更新用户资料失败: ${error.message}`, 'UPDATE_PROFILE_FAILED', error);
    }
  }

  /**
   * 获取用户统计信息
   */
  async getUserStats(userId: number): Promise<{
    totalRepositories: number;
    totalReleases: number;
    totalAIAnalyses: number;
    lastActivity: string;
  }> {
    try {
      const stats = await this.db.queryAll(`
        SELECT 
          (SELECT COUNT(*) FROM repositories WHERE user_id = ?) as total_repositories,
          (SELECT COUNT(*) FROM releases r JOIN repositories rep ON r.repository_id = rep.id WHERE rep.user_id = ?) as total_releases,
          (SELECT COUNT(*) FROM ai_analysis_results WHERE user_id = ?) as total_ai_analyses,
          (SELECT MAX(updated_at) FROM repositories WHERE user_id = ?) as last_activity
      `, [userId, userId, userId, userId]);

      return {
        totalRepositories: stats[0]?.total_repositories || 0,
        totalReleases: stats[0]?.total_releases || 0,
        totalAIAnalyses: stats[0]?.total_ai_analyses || 0,
        lastActivity: stats[0]?.last_activity || ''
      };
    } catch (error) {
      throw new DAOException(`获取用户统计失败: ${error.message}`, 'USER_STATS_FAILED', error);
    }
  }

  /**
   * 检查用户名是否可用
   */
  async isUsernameAvailable(username: string, excludeUserId?: number): Promise<boolean> {
    try {
      let sql = 'SELECT 1 FROM users WHERE username = ?';
      const params = [username];
      
      if (excludeUserId) {
        sql += ' AND id != ?';
        params.push(excludeUserId);
      }
      
      const result = await this.db.querySingle(sql, params);
      return !result;
    } catch (error) {
      throw new DAOException(`检查用户名可用性失败: ${error.message}`, 'CHECK_USERNAME_FAILED', error);
    }
  }

  /**
   * 获取用户统计摘要
   */
  async getUserSummary(): Promise<{
    totalUsers: number;
    authenticatedUsers: number;
    recentlyActive: number;
  }> {
    try {
      const summary = await this.db.queryAll(`
        SELECT 
          COUNT(*) as total_users,
          SUM(CASE WHEN is_authenticated = 1 THEN 1 ELSE 0 END) as authenticated_users,
          SUM(CASE WHEN updated_at > datetime('now', '-30 days') THEN 1 ELSE 0 END) as recently_active
        FROM users
      `);

      return {
        totalUsers: summary[0]?.total_users || 0,
        authenticatedUsers: summary[0]?.authenticated_users || 0,
        recentlyActive: summary[0]?.recently_active || 0
      };
    } catch (error) {
      throw new DAOException(`获取用户摘要失败: ${error.message}`, 'USER_SUMMARY_FAILED', error);
    }
  }

  /**
   * 清理未认证的旧用户
   */
  async cleanupOldInactiveUsers(daysOld: number = 30): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysOld);
      
      const sql = `
        DELETE FROM users 
        WHERE is_authenticated = 0 
        AND created_at < ?
      `;
      
      const result = await this.db.delete(sql, [cutoffDate.toISOString()]);
      return result;
    } catch (error) {
      throw new DAOException(`清理无效用户失败: ${error.message}`, 'CLEANUP_USERS_FAILED', error);
    }
  }

  /**
   * 解密用户 GitHub Token（谨慎使用）
   */
  decryptGitHubToken(encryptedToken: string): string {
    try {
      return CryptoUtil.decrypt(encryptedToken);
    } catch (error) {
      throw new DAOException(`解密 GitHub Token 失败: ${error.message}`, 'DECRYPT_TOKEN_FAILED', error);
    }
  }
}

// 导入 SearchParams 类型
import { SearchParams } from './base_dao';
