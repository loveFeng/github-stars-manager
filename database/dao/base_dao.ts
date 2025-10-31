/**
 * 基础 DAO 类
 * 提供通用的 CRUD 操作
 */

import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder?: 'ASC' | 'DESC';
}

export interface SearchParams extends PaginationParams {
  query?: string;
  searchFields?: string[];
}

export interface FilterParams {
  [key: string]: any;
}

export interface PaginatedResult<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface SortOptions {
  [key: string]: 'ASC' | 'DESC';
}

export abstract class BaseDAO<T extends { id?: number; created_at?: string; updated_at?: string }> {
  protected abstract tableName: string;
  protected abstract allowedSortFields: string[];
  
  constructor(protected db: SQLiteConnectionManager) {}

  /**
   * 创建记录
   */
  async create(data: Omit<T, 'id' | 'created_at' | 'updated_at'>): Promise<T> {
    try {
      const now = DateUtil.formatForSQLite(new Date());
      const insertData = {
        ...data,
        created_at: now,
        updated_at: now
      };

      const fields = Object.keys(insertData);
      const placeholders = fields.map(() => '?').join(', ');
      const values = Object.values(insertData);

      const sql = `INSERT INTO ${this.tableName} (${fields.join(', ')}) VALUES (${placeholders})`;
      const result = await this.db.insert(sql, values);

      if (!result) {
        throw new DAOException('创建记录失败', 'INSERT_FAILED');
      }

      return await this.findById(result) as T;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建记录失败: ${error.message}`, 'CREATE_FAILED', error);
    }
  }

  /**
   * 根据 ID 查找记录
   */
  async findById(id: number): Promise<T | null> {
    try {
      const sql = `SELECT * FROM ${this.tableName} WHERE id = ?`;
      const result = await this.db.querySingle(sql, [id]);
      return result || null;
    } catch (error) {
      throw new DAOException(`查找记录失败: ${error.message}`, 'FIND_BY_ID_FAILED', error);
    }
  }

  /**
   * 查找所有记录
   */
  async findAll(params?: PaginationParams): Promise<T[]> {
    try {
      const sql = this._buildSelectQuery(params);
      const result = await this.db.queryAll(sql.sql, sql.params);
      return result;
    } catch (error) {
      throw new DAOException(`查找记录失败: ${error.message}`, 'FIND_ALL_FAILED', error);
    }
  }

  /**
   * 分页查询
   */
  async findPaginated(params?: SearchParams): Promise<PaginatedResult<T>> {
    try {
      const {
        page = 1,
        limit = 20,
        offset,
        sortBy = 'created_at',
        sortOrder = 'DESC',
        query,
        searchFields
      } = params || {};

      const actualOffset = offset !== undefined ? offset : (page - 1) * limit;
      const validatedSortBy = this._validateSortField(sortBy);
      const validatedSortOrder = sortOrder.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';

      // 构建 WHERE 条件
      let whereClause = '';
      let queryParams: any[] = [];

      if (query && searchFields && searchFields.length > 0) {
        const conditions = searchFields.map(field => `${field} LIKE ?`);
        whereClause = `WHERE (${conditions.join(' OR ')})`;
        const searchPattern = `%${query}%`;
        queryParams = Array(searchFields.length).fill(searchPattern);
      }

      // 构建查询
      const countSql = `
        SELECT COUNT(*) as total 
        FROM ${this.tableName} 
        ${whereClause}
      `;
      const dataSql = `
        SELECT * 
        FROM ${this.tableName} 
        ${whereClause}
        ORDER BY ${validatedSortBy} ${validatedSortOrder}
        LIMIT ? OFFSET ?
      `;

      // 执行查询
      const countResult = await this.db.querySingle(countSql, queryParams);
      const dataResult = await this.db.queryAll(dataSql, [...queryParams, limit, actualOffset]);

      const total = countResult.total;
      const totalPages = Math.ceil(total / limit);

      return {
        data: dataResult,
        total,
        page,
        limit,
        totalPages,
        hasNext: page < totalPages,
        hasPrev: page > 1
      };
    } catch (error) {
      throw new DAOException(`分页查询失败: ${error.message}`, 'FIND_PAGINATED_FAILED', error);
    }
  }

  /**
   * 更新记录
   */
  async update(id: number, data: Partial<T>): Promise<T> {
    try {
      const updateData = {
        ...data,
        updated_at: DateUtil.formatForSQLite(new Date())
      };

      const fields = Object.keys(updateData);
      const assignments = fields.map(field => `${field} = ?`).join(', ');
      const values = Object.values(updateData);

      const sql = `UPDATE ${this.tableName} SET ${assignments} WHERE id = ?`;
      const result = await this.db.update(sql, [...values, id]);

      if (result === 0) {
        throw new DAOException('记录不存在', 'RECORD_NOT_FOUND');
      }

      return await this.findById(id) as T;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`更新记录失败: ${error.message}`, 'UPDATE_FAILED', error);
    }
  }

  /**
   * 删除记录
   */
  async delete(id: number): Promise<boolean> {
    try {
      const sql = `DELETE FROM ${this.tableName} WHERE id = ?`;
      const result = await this.db.delete(sql, [id]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`删除记录失败: ${error.message}`, 'DELETE_FAILED', error);
    }
  }

  /**
   * 批量创建记录
   */
  async createBatch(dataList: Omit<T, 'id' | 'created_at' | 'updated_at'>[]): Promise<T[]> {
    try {
      if (dataList.length === 0) return [];

      const now = DateUtil.formatForSQLite(new Date());
      const insertDataList = dataList.map(data => ({
        ...data,
        created_at: now,
        updated_at: now
      }));

      const fields = Object.keys(insertDataList[0]);
      const placeholders = fields.map(() => '?').join(', ');
      const sql = `INSERT INTO ${this.tableName} (${fields.join(', ')}) VALUES (${placeholders})`;

      const allValues: any[] = [];
      insertDataList.forEach(data => {
        allValues.push(...Object.values(data));
      });

      await this.db.executeInTransaction(async (tx) => {
        for (let i = 0; i < insertDataList.length; i++) {
          const values = Object.values(insertDataList[i]);
          await tx.run(sql, values);
        }
      });

      // 返回创建的记录
      const results: T[] = [];
      for (let i = 0; i < dataList.length; i++) {
        // 这里简化处理，实际应该使用 tx 获取最后插入的 ID
        const count = await this.db.querySingle(`SELECT COUNT(*) as count FROM ${this.tableName}`);
        if (count.count >= dataList.length) {
          // 获取最新插入的记录
          const recentRecords = await this.db.queryAll(
            `SELECT * FROM ${this.tableName} ORDER BY created_at DESC LIMIT ?`,
            [dataList.length]
          );
          results.push(...recentRecords.slice(0, dataList.length));
        }
      }

      return results;
    } catch (error) {
      throw new DAOException(`批量创建记录失败: ${error.message}`, 'BATCH_CREATE_FAILED', error);
    }
  }

  /**
   * 批量更新记录
   */
  async updateBatch(updates: { id: number; data: Partial<T> }[]): Promise<T[]> {
    try {
      if (updates.length === 0) return [];

      await this.db.executeInTransaction(async (tx) => {
        for (const update of updates) {
          const { id, data } = update;
          const updateData = {
            ...data,
            updated_at: DateUtil.formatForSQLite(new Date())
          };

          const fields = Object.keys(updateData);
          const assignments = fields.map(field => `${field} = ?`).join(', ');
          const values = Object.values(updateData);

          const sql = `UPDATE ${this.tableName} SET ${assignments} WHERE id = ?`;
          await tx.run(sql, [...values, id]);
        }
      });

      // 获取更新后的记录
      const ids = updates.map(u => u.id);
      const placeholders = ids.map(() => '?').join(', ');
      const sql = `SELECT * FROM ${this.tableName} WHERE id IN (${placeholders})`;
      const results = await this.db.queryAll(sql, ids);

      return results;
    } catch (error) {
      throw new DAOException(`批量更新记录失败: ${error.message}`, 'BATCH_UPDATE_FAILED', error);
    }
  }

  /**
   * 批量删除记录
   */
  async deleteBatch(ids: number[]): Promise<number> {
    try {
      if (ids.length === 0) return 0;

      const placeholders = ids.map(() => '?').join(', ');
      const sql = `DELETE FROM ${this.tableName} WHERE id IN (${placeholders})`;
      const result = await this.db.delete(sql, ids);

      return result;
    } catch (error) {
      throw new DAOException(`批量删除记录失败: ${error.message}`, 'BATCH_DELETE_FAILED', error);
    }
  }

  /**
   * 统计记录数量
   */
  async count(filter?: FilterParams): Promise<number> {
    try {
      let sql = `SELECT COUNT(*) as count FROM ${this.tableName}`;
      const params: any[] = [];

      if (filter) {
        const conditions: string[] = [];
        for (const [key, value] of Object.entries(filter)) {
          if (value !== null && value !== undefined) {
            conditions.push(`${key} = ?`);
            params.push(value);
          }
        }

        if (conditions.length > 0) {
          sql += ` WHERE ${conditions.join(' AND ')}`;
        }
      }

      const result = await this.db.querySingle(sql, params);
      return result.count;
    } catch (error) {
      throw new DAOException(`统计记录数量失败: ${error.message}`, 'COUNT_FAILED', error);
    }
  }

  /**
   * 检查记录是否存在
   */
  async exists(id: number): Promise<boolean> {
    try {
      const sql = `SELECT 1 FROM ${this.tableName} WHERE id = ? LIMIT 1`;
      const result = await this.db.querySingle(sql, [id]);
      return !!result;
    } catch (error) {
      throw new DAOException(`检查记录存在性失败: ${error.message}`, 'EXISTS_FAILED', error);
    }
  }

  /**
   * 获取字段列表
   */
  async getColumns(): Promise<string[]> {
    try {
      const sql = `PRAGMA table_info(${this.tableName})`;
      const result = await this.db.queryAll(sql);
      return result.map((row: any) => row.name);
    } catch (error) {
      throw new DAOException(`获取字段列表失败: ${error.message}`, 'GET_COLUMNS_FAILED', error);
    }
  }

  /**
   * 清空表
   */
  async truncate(): Promise<void> {
    try {
      const sql = `DELETE FROM ${this.tableName}`;
      await this.db.delete(sql);
    } catch (error) {
      throw new DAOException(`清空表失败: ${error.message}`, 'TRUNCATE_FAILED', error);
    }
  }

  /**
   * 获取表统计信息
   */
  async getTableStats(): Promise<any> {
    try {
      const sql = `SELECT 
        COUNT(*) as total_rows,
        MAX(created_at) as last_created,
        MAX(updated_at) as last_updated
      FROM ${this.tableName}`;
      
      return await this.db.querySingle(sql);
    } catch (error) {
      throw new DAOException(`获取表统计信息失败: ${error.message}`, 'TABLE_STATS_FAILED', error);
    }
  }

  /**
   * 构建查询 SQL
   */
  protected _buildSelectQuery(params?: PaginationParams): { sql: string; params: any[] } {
    let sql = `SELECT * FROM ${this.tableName}`;
    const sqlParams: any[] = [];

    // 排序
    if (params?.sortBy) {
      const sortField = this._validateSortField(params.sortBy);
      const sortOrder = params.sortOrder?.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';
      sql += ` ORDER BY ${sortField} ${sortOrder}`;
    } else {
      sql += ` ORDER BY created_at DESC`;
    }

    // 分页
    if (params?.limit) {
      sql += ` LIMIT ?`;
      sqlParams.push(params.limit);

      if (params?.offset !== undefined) {
        sql += ` OFFSET ?`;
        sqlParams.push(params.offset);
      }
    }

    return { sql, params: sqlParams };
  }

  /**
   * 验证排序字段
   */
  protected _validateSortField(field: string): string {
    if (!this.allowedSortFields.includes(field)) {
      throw new DAOException(`不允许的排序字段: ${field}`, 'INVALID_SORT_FIELD');
    }
    return field;
  }

  /**
   * 构建过滤条件
   */
  protected _buildWhereClause(filter?: FilterParams): { clause: string; params: any[] } {
    if (!filter || Object.keys(filter).length === 0) {
      return { clause: '', params: [] };
    }

    const conditions: string[] = [];
    const params: any[] = [];

    for (const [key, value] of Object.entries(filter)) {
      if (value !== null && value !== undefined) {
        conditions.push(`${key} = ?`);
        params.push(value);
      }
    }

    return {
      clause: conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '',
      params
    };
  }
}

// 导入 DateUtil
import { DateUtil } from '../utils/date';
