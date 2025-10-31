/**
 * 分类 DAO
 */

import { BaseDAO } from './base_dao';
import { 
  Category, 
  CreateCategoryData, 
  UpdateCategoryData, 
  CategorySearchParams 
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';

export class CategoryDAO extends BaseDAO<Category> {
  protected tableName = 'categories';
  protected allowedSortFields = [
    'id', 'name', 'sort_order', 'created_at', 'updated_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建分类
   */
  async create(data: CreateCategoryData): Promise<Category> {
    try {
      const categoryData = {
        ...data,
        sort_order: data.sort_order || 0
      };

      return await super.create(categoryData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建分类失败: ${error.message}`, 'CREATE_CATEGORY_FAILED', error);
    }
  }

  /**
   * 获取默认分类列表
   */
  async getDefaultCategories(): Promise<Category[]> {
    try {
      const sql = `
        SELECT * FROM categories 
        WHERE is_default = 1 
        ORDER BY sort_order ASC, name ASC
      `;
      const result = await this.db.queryAll(sql);
      return result;
    } catch (error) {
      throw new DAOException(`获取默认分类失败: ${error.message}`, 'GET_DEFAULT_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 获取子分类列表
   */
  async getSubCategories(parentId: number): Promise<Category[]> {
    try {
      const sql = `
        SELECT * FROM categories 
        WHERE parent_id = ? 
        ORDER BY sort_order ASC, name ASC
      `;
      const result = await this.db.queryAll(sql, [parentId]);
      return result;
    } catch (error) {
      throw new DAOException(`获取子分类失败: ${error.message}`, 'GET_SUB_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 获取顶级分类列表
   */
  async getTopLevelCategories(): Promise<Category[]> {
    try {
      const sql = `
        SELECT * FROM categories 
        WHERE parent_id IS NULL OR parent_id = 0 
        ORDER BY sort_order ASC, name ASC
      `;
      const result = await this.db.queryAll(sql);
      return result;
    } catch (error) {
      throw new DAOException(`获取顶级分类失败: ${error.message}`, 'GET_TOP_LEVEL_FAILED', error);
    }
  }

  /**
   * 获取分类树结构
   */
  async getCategoryTree(): Promise<Array<Category & { children: Category[] }>> {
    try {
      const topLevel = await this.getTopLevelCategories();
      const categoriesWithChildren = [];

      for (const category of topLevel) {
        const children = await this.getSubCategories(category.id!);
        categoriesWithChildren.push({
          ...category,
          children
        });
      }

      return categoriesWithChildren;
    } catch (error) {
      throw new DAOException(`获取分类树失败: ${error.message}`, 'GET_CATEGORY_TREE_FAILED', error);
    }
  }

  /**
   * 搜索分类
   */
  async searchCategories(params?: CategorySearchParams): Promise<Category[]> {
    try {
      const searchFields = params?.searchFields || ['name', 'description'];
      const result = await this.findPaginated({
        ...params,
        query: params?.query,
        searchFields
      });
      return result.data;
    } catch (error) {
      throw new DAOException(`搜索分类失败: ${error.message}`, 'SEARCH_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 更新分类顺序
   */
  async updateSortOrder(categoryIds: number[]): Promise<void> {
    try {
      await this.db.executeInTransaction(async (tx) => {
        for (let i = 0; i < categoryIds.length; i++) {
          const sql = 'UPDATE categories SET sort_order = ? WHERE id = ?';
          await tx.run(sql, [i + 1, categoryIds[i]]);
        }
      });
    } catch (error) {
      throw new DAOException(`更新分类顺序失败: ${error.message}`, 'UPDATE_SORT_ORDER_FAILED', error);
    }
  }

  /**
   * 重置默认分类（创建默认分类）
   */
  async resetDefaultCategories(): Promise<Category[]> {
    try {
      // 删除现有默认分类
      await this.db.delete('DELETE FROM categories WHERE is_default = 1');

      // 创建默认分类
      const defaultCategories = [
        { name: '前端开发', description: '前端框架、库和工具', color: '#3B82F6', icon: 'Code', sort_order: 1 },
        { name: '后端开发', description: '后端框架、API和服务器', color: '#10B981', icon: 'Server', sort_order: 2 },
        { name: '移动开发', description: '移动应用开发相关', color: '#F59E0B', icon: 'Smartphone', sort_order: 3 },
        { name: '机器学习', description: '机器学习和深度学习', color: '#8B5CF6', icon: 'Brain', sort_order: 4 },
        { name: '数据科学', description: '数据分析和可视化', color: '#EF4444', icon: 'BarChart', sort_order: 5 },
        { name: 'DevOps', description: 'CI/CD、容器化和部署', color: '#06B6D4', icon: 'Settings', sort_order: 6 },
        { name: '工具类', description: '开发工具和实用程序', color: '#84CC16', icon: 'Wrench', sort_order: 7 },
        { name: '文档', description: '文档和教程', color: '#F97316', icon: 'Book', sort_order: 8 },
        { name: '游戏开发', description: '游戏引擎和框架', color: '#EC4899', icon: 'Gamepad', sort_order: 9 },
        { name: '区块链', description: '区块链和加密货币', color: '#6366F1', icon: 'Coins', sort_order: 10 }
      ];

      const createdCategories = [];
      for (const catData of defaultCategories) {
        const category = await this.create({
          ...catData,
          is_default: true
        });
        createdCategories.push(category);
      }

      return createdCategories;
    } catch (error) {
      throw new DAOException(`重置默认分类失败: ${error.message}`, 'RESET_DEFAULT_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 删除分类及其关联
   */
  async deleteCategoryWithAssociations(categoryId: number): Promise<boolean> {
    try {
      await this.db.executeInTransaction(async (tx) => {
        // 删除仓库分类关联
        await tx.run('DELETE FROM repository_categories WHERE category_id = ?', [categoryId]);
        
        // 删除子分类
        await tx.run('DELETE FROM categories WHERE parent_id = ?', [categoryId]);
        
        // 删除分类本身
        const result = await tx.run('DELETE FROM categories WHERE id = ?', [categoryId]);
        
        if (result.changes === 0) {
          throw new DAOException('分类不存在', 'CATEGORY_NOT_FOUND');
        }
      });

      return true;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`删除分类失败: ${error.message}`, 'DELETE_CATEGORY_FAILED', error);
    }
  }

  /**
   * 获取分类统计信息
   */
  async getCategoryStats(): Promise<Array<{
    category: Category;
    repositoryCount: number;
    repositoryCountPercentage: number;
  }>> {
    try {
      const stats = await this.db.queryAll(`
        SELECT 
          c.*,
          COUNT(rc.repository_id) as repository_count
        FROM categories c
        LEFT JOIN repository_categories rc ON c.id = rc.category_id
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.name ASC
      `);

      const totalRepos = await this.db.querySingle(`
        SELECT COUNT(DISTINCT repository_id) as total 
        FROM repository_categories
      `);

      const total = totalRepos.total || 0;

      return stats.map(stat => ({
        category: stat,
        repositoryCount: stat.repository_count,
        repositoryCountPercentage: total > 0 ? Math.round((stat.repository_count * 100) / total) : 0
      }));
    } catch (error) {
      throw new DAOException(`获取分类统计失败: ${error.message}`, 'CATEGORY_STATS_FAILED', error);
    }
  }

  /**
   * 合并分类
   */
  async mergeCategories(sourceCategoryId: number, targetCategoryId: number): Promise<void> {
    try {
      if (sourceCategoryId === targetCategoryId) {
        throw new DAOException('不能将分类合并到自身', 'INVALID_MERGE_TARGET');
      }

      await this.db.executeInTransaction(async (tx) => {
        // 移动关联的仓库
        await tx.run(`
          UPDATE repository_categories 
          SET category_id = ? 
          WHERE category_id = ?
        `, [targetCategoryId, sourceCategoryId]);

        // 移动子分类
        await tx.run(`
          UPDATE categories 
          SET parent_id = ? 
          WHERE parent_id = ?
        `, [targetCategoryId, sourceCategoryId]);

        // 删除源分类
        const result = await tx.run('DELETE FROM categories WHERE id = ?', [sourceCategoryId]);
        
        if (result.changes === 0) {
          throw new DAOException('源分类不存在', 'SOURCE_CATEGORY_NOT_FOUND');
        }
      });
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`合并分类失败: ${error.message}`, 'MERGE_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 检查分类名称是否可用
   */
  async isNameAvailable(name: string, parentId?: number, excludeId?: number): Promise<boolean> {
    try {
      let sql = 'SELECT 1 FROM categories WHERE name = ? AND (parent_id IS NULL OR parent_id = ?)';
      const params = [name, parentId || 0];
      
      if (excludeId) {
        sql += ' AND id != ?';
        params.push(excludeId);
      }
      
      const result = await this.db.querySingle(sql, params);
      return !result;
    } catch (error) {
      throw new DAOException(`检查分类名称可用性失败: ${error.message}`, 'CHECK_NAME_AVAILABLE_FAILED', error);
    }
  }

  /**
   * 获取最受欢迎的分类（按仓库数量排序）
   */
  async getPopularCategories(limit: number = 10): Promise<Array<{
    category: Category;
    repositoryCount: number;
  }>> {
    try {
      const sql = `
        SELECT 
          c.*,
          COUNT(rc.repository_id) as repository_count
        FROM categories c
        LEFT JOIN repository_categories rc ON c.id = rc.category_id
        GROUP BY c.id
        HAVING repository_count > 0
        ORDER BY repository_count DESC, c.sort_order ASC
        LIMIT ?
      `;

      const result = await this.db.queryAll(sql, [limit]);
      return result.map(row => ({
        category: row,
        repositoryCount: row.repository_count
      }));
    } catch (error) {
      throw new DAOException(`获取热门分类失败: ${error.message}`, 'GET_POPULAR_CATEGORIES_FAILED', error);
    }
  }

  /**
   * 获取分类使用频率统计
   */
  async getCategoryUsageStats(): Promise<{
    totalCategories: number;
    categoriesWithRepositories: number;
    averageRepositoriesPerCategory: number;
    mostUsedCategory: Category | null;
    leastUsedCategory: Category | null;
  }> {
    try {
      const stats = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_categories,
          SUM(CASE WHEN rc_count.repository_count > 0 THEN 1 ELSE 0 END) as categories_with_repos,
          AVG(rc_count.repository_count) as avg_repos_per_category
        FROM categories c
        LEFT JOIN (
          SELECT 
            category_id, 
            COUNT(*) as repository_count
          FROM repository_categories
          GROUP BY category_id
        ) rc_count ON c.id = rc_count.category_id
      `);

      // 获取最常用和最不常用的分类
      const extremes = await this.db.queryAll(`
        SELECT 
          c.*,
          rc_count.repository_count
        FROM categories c
        JOIN (
          SELECT 
            category_id, 
            COUNT(*) as repository_count
          FROM repository_categories
          GROUP BY category_id
        ) rc_count ON c.id = rc_count.category_id
        ORDER BY rc_count.repository_count DESC, c.sort_order ASC
        LIMIT 1
      `);

      const leastUsed = await this.db.queryAll(`
        SELECT 
          c.*,
          rc_count.repository_count
        FROM categories c
        JOIN (
          SELECT 
            category_id, 
            COUNT(*) as repository_count
          FROM repository_categories
          GROUP BY category_id
        ) rc_count ON c.id = rc_count.category_id
        ORDER BY rc_count.repository_count ASC, c.sort_order ASC
        LIMIT 1
      `);

      return {
        totalCategories: stats.total_categories || 0,
        categoriesWithRepositories: stats.categories_with_repos || 0,
        averageRepositoriesPerCategory: Math.round(stats.avg_repos_per_category || 0),
        mostUsedCategory: extremes[0] || null,
        leastUsedCategory: leastUsed[0] || null
      };
    } catch (error) {
      throw new DAOException(`获取分类使用统计失败: ${error.message}`, 'CATEGORY_USAGE_STATS_FAILED', error);
    }
  }
}
