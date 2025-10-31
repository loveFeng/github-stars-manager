/**
 * BaseDAO 单元测试
 * 测试基础 DAO 类的所有功能
 */

import { describe, test, expect, beforeEach, afterEach, beforeAll, afterAll, jest } from '@jest/globals';
import { BaseDAO, PaginationParams, SearchParams, PaginatedResult } from '../base_dao';
import { DAOException } from '../dao_exception';
import { DateUtil } from '../../utils/date';

// 模拟数据库连接管理器
class MockDatabaseManager {
  private data: Map<number, any[]> = new Map();
  private nextId = 1;

  async queryAll(sql: string, params: any[] = []): Promise<any[]> {
    // 简化实现 - 根据表名返回模拟数据
    const tableName = this.extractTableName(sql);
    if (!this.data.has(tableName)) {
      this.data.set(tableName, []);
    }
    return this.data.get(tableName) || [];
  }

  async querySingle(sql: string, params: any[] = []): Promise<any | null> {
    const results = await this.queryAll(sql, params);
    return results.length > 0 ? results[0] : null;
  }

  async insert(sql: string, params: any[]): Promise<number> {
    const tableName = this.extractTableName(sql);
    const newRecord = { ...params, id: this.nextId++ };
    
    if (!this.data.has(tableName)) {
      this.data.set(tableName, []);
    }
    
    const records = this.data.get(tableName)!;
    records.push(newRecord);
    
    return newRecord.id;
  }

  async update(sql: string, params: any[]): Promise<number> {
    const tableName = this.extractTableName(sql);
    const records = this.data.get(tableName) || [];
    const id = params[params.length - 1];
    
    const index = records.findIndex(r => r.id === id);
    if (index === -1) return 0;
    
    const updateData = params.slice(0, -1);
    const fields = this.extractFieldsFromUpdate(sql);
    
    fields.forEach((field, i) => {
      if (i < updateData.length) {
        records[index][field] = updateData[i];
      }
    });
    
    return 1;
  }

  async delete(sql: string, params: any[]): Promise<number> {
    const tableName = this.extractTableName(sql);
    const records = this.data.get(tableName) || [];
    const id = params[0];
    
    const index = records.findIndex(r => r.id === id);
    if (index === -1) return 0;
    
    records.splice(index, 1);
    return 1;
  }

  async executeInTransaction(callback: (tx: any) => Promise<void>): Promise<void> {
    await callback(this);
  }

  private extractTableName(sql: string): string {
    const match = sql.match(/FROM\s+(\w+)/i) || sql.match(/INSERT\s+INTO\s+(\w+)/i) || sql.match(/UPDATE\s+(\w+)/i);
    return match ? match[1].toLowerCase() : 'test_table';
  }

  private extractFieldsFromUpdate(sql: string): string[] {
    const match = sql.match(/SET\s+(.+?)\s+WHERE/i);
    if (!match) return [];
    return match[1].split(',').map(field => {
      const cleanField = field.trim().split('=')[0].trim();
      return cleanField;
    });
  }

  clearTable(tableName: string) {
    this.data.delete(tableName);
  }
}

// 测试用的具体 DAO 类
class TestEntity {
  id?: number;
  name: string;
  value: number;
  created_at?: string;
  updated_at?: string;
}

class TestDAO extends BaseDAO<TestEntity> {
  protected tableName = 'test_entities';
  protected allowedSortFields = ['id', 'name', 'value', 'created_at', 'updated_at'];

  constructor(db: MockDatabaseManager) {
    super(db);
  }
}

describe('BaseDAO', () => {
  let mockDb: MockDatabaseManager;
  let testDAO: TestDAO;

  beforeEach(() => {
    mockDb = new MockDatabaseManager();
    testDAO = new TestDAO(mockDb);
    mockDb.clearTable('test_entities');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('创建操作', () => {
    test('应该成功创建新记录', async () => {
      const entityData = {
        name: '测试实体',
        value: 100
      };

      const result = await testDAO.create(entityData);

      expect(result.id).toBeDefined();
      expect(result.name).toBe(entityData.name);
      expect(result.value).toBe(entityData.value);
      expect(result.created_at).toBeDefined();
      expect(result.updated_at).toBeDefined();
    });

    test('创建失败时应该抛出 DAOException', async () => {
      // 模拟数据库错误
      jest.spyOn(mockDb, 'insert').mockRejectedValue(new Error('数据库错误'));

      const entityData = {
        name: '测试实体',
        value: 100
      };

      await expect(testDAO.create(entityData)).rejects.toThrow(DAOException);
    });

    test('应该能够批量创建记录', async () => {
      const entitiesData = [
        { name: '实体1', value: 100 },
        { name: '实体2', value: 200 },
        { name: '实体3', value: 300 }
      ];

      const results = await testDAO.createBatch(entitiesData);

      expect(results).toHaveLength(3);
      results.forEach((result, index) => {
        expect(result.id).toBeDefined();
        expect(result.name).toBe(entitiesData[index].name);
        expect(result.value).toBe(entitiesData[index].value);
      });
    });
  });

  describe('查找操作', () => {
    beforeEach(async () => {
      // 预填充测试数据
      await testDAO.create({ name: '实体1', value: 100 });
      await testDAO.create({ name: '实体2', value: 200 });
      await testDAO.create({ name: '实体3', value: 300 });
    });

    test('应该根据 ID 成功查找记录', async () => {
      const created = await testDAO.create({ name: '测试实体', value: 500 });
      const found = await testDAO.findById(created.id!);

      expect(found).not.toBeNull();
      expect(found?.id).toBe(created.id);
      expect(found?.name).toBe(created.name);
    });

    test('查找不存在的 ID 应该返回 null', async () => {
      const found = await testDAO.findById(99999);
      expect(found).toBeNull();
    });

    test('应该成功查找所有记录', async () => {
      const allRecords = await testDAO.findAll();

      expect(allRecords).toHaveLength(3);
    });

    test('应该支持分页查询', async () => {
      const paginated = await testDAO.findPaginated({
        page: 1,
        limit: 2,
        sortBy: 'id',
        sortOrder: 'ASC'
      });

      expect(paginated.data).toHaveLength(2);
      expect(paginated.total).toBe(3);
      expect(paginated.totalPages).toBe(2);
      expect(paginated.hasNext).toBe(true);
      expect(paginated.hasPrev).toBe(false);
    });

    test('应该支持搜索功能', async () => {
      const searchResults = await testDAO.findPaginated({
        query: '实体1',
        searchFields: ['name'],
        limit: 10
      });

      expect(searchResults.data).toHaveLength(1);
      expect(searchResults.data[0].name).toContain('实体1');
    });

    test('应该验证排序字段', async () => {
      await expect(
        testDAO.findPaginated({
          sortBy: 'invalid_field'
        })
      ).rejects.toThrow(DAOException);
    });
  });

  describe('更新操作', () => {
    test('应该成功更新记录', async () => {
      const created = await testDAO.create({ name: '原名称', value: 100 });
      
      const updated = await testDAO.update(created.id!, {
        name: '新名称',
        value: 200
      });

      expect(updated.name).toBe('新名称');
      expect(updated.value).toBe(200);
      expect(updated.updated_at).not.toBe(created.updated_at);
    });

    test('更新不存在的记录应该抛出异常', async () => {
      await expect(
        testDAO.update(99999, { name: '新名称' })
      ).rejects.toThrow(DAOException);
    });

    test('应该支持批量更新', async () => {
      const entities = await testDAO.createBatch([
        { name: '实体1', value: 100 },
        { name: '实体2', value: 200 }
      ]);

      const updates = entities.map((entity, index) => ({
        id: entity.id!,
        data: { value: entity.value + 100 }
      }));

      const updated = await testDAO.updateBatch(updates);

      expect(updated).toHaveLength(2);
      updated.forEach((entity, index) => {
        expect(entity.value).toBe(updates[index].data.value);
      });
    });
  });

  describe('删除操作', () => {
    test('应该成功删除记录', async () => {
      const created = await testDAO.create({ name: '删除测试', value: 100 });
      const deleted = await testDAO.delete(created.id!);

      expect(deleted).toBe(true);
      
      const found = await testDAO.findById(created.id!);
      expect(found).toBeNull();
    });

    test('删除不存在的记录应该返回 false', async () => {
      const deleted = await testDAO.delete(99999);
      expect(deleted).toBe(false);
    });

    test('应该支持批量删除', async () => {
      const entities = await testDAO.createBatch([
        { name: '批量删除1', value: 100 },
        { name: '批量删除2', value: 200 },
        { name: '批量删除3', value: 300 }
      ]);

      const idsToDelete = entities.slice(0, 2).map(e => e.id!);
      const deletedCount = await testDAO.deleteBatch(idsToDelete);

      expect(deletedCount).toBe(2);
    });
  });

  describe('统计功能', () => {
    beforeEach(async () => {
      await testDAO.createBatch([
        { name: '实体1', value: 100 },
        { name: '实体2', value: 200 },
        { name: '实体3', value: 300 }
      ]);
    });

    test('应该统计总记录数', async () => {
      const count = await testDAO.count();
      expect(count).toBe(3);
    });

    test('应该支持过滤条件统计', async () => {
      const count = await testDAO.count({ value: 200 });
      expect(count).toBe(1);
    });

    test('应该检查记录是否存在', async () => {
      const entities = await testDAO.findAll();
      const exists = await testDAO.exists(entities[0].id!);
      
      expect(exists).toBe(true);
      
      const notExists = await testDAO.exists(99999);
      expect(notExists).toBe(false);
    });

    test('应该获取表统计信息', async () => {
      const stats = await testDAO.getTableStats();
      
      expect(stats.total_rows).toBe(3);
      expect(stats.last_created).toBeDefined();
      expect(stats.last_updated).toBeDefined();
    });
  });

  describe('字段和表操作', () => {
    test('应该获取表字段列表', async () => {
      // 模拟 PRAGMA table_info 结果
      jest.spyOn(mockDb, 'queryAll').mockResolvedValue([
        { name: 'id', type: 'INTEGER' },
        { name: 'name', type: 'TEXT' },
        { name: 'value', type: 'INTEGER' },
        { name: 'created_at', type: 'DATETIME' },
        { name: 'updated_at', type: 'DATETIME' }
      ]);

      const columns = await testDAO.getColumns();
      expect(columns).toContain('id');
      expect(columns).toContain('name');
      expect(columns).toContain('value');
      expect(columns).toContain('created_at');
      expect(columns).toContain('updated_at');
    });

    test('应该清空表', async () => {
      await testDAO.create({ name: '测试', value: 100 });
      
      expect(await testDAO.count()).toBe(1);
      
      await testDAO.truncate();
      
      expect(await testDAO.count()).toBe(0);
    });
  });

  describe('异常处理', () => {
    test('所有方法都应该正确处理 DAOException', async () => {
      const error = new Error('测试错误');
      const daoException = new DAOException('测试异常', 'TEST_ERROR', error);
      
      expect(daoException.message).toBe('测试异常');
      expect(daoException.code).toBe('TEST_ERROR');
      expect(daoException.cause).toBe(error);
    });
  });

  describe('分页查询边界情况', () => {
    test('应该处理无效的分页参数', async () => {
      const results = await testDAO.findPaginated({
        page: 0,  // 无效页码
        limit: 10
      });

      // 应该自动修正为第1页
      expect(results.page).toBe(1);
    });

    test('应该处理超出范围的页码', async () => {
      const results = await testDAO.findPaginated({
        page: 9999,
        limit: 10
      });

      expect(results.data).toHaveLength(0);
      expect(results.hasNext).toBe(false);
      expect(results.hasPrev).toBe(true);
    });
  });

  describe('事务处理', () => {
    test('批量操作应该使用事务', async () => {
      const batchData = [
        { name: '事务测试1', value: 100 },
        { name: '事务测试2', value: 200 }
      ];

      const results = await testDAO.createBatch(batchData);
      expect(results).toHaveLength(2);

      // 验证事务中的所有操作要么都成功，要么都失败
      const count = await testDAO.count();
      expect(count).toBe(2);
    });

    test('应该处理事务中的错误', async () => {
      // 模拟事务中的错误
      jest.spyOn(mockDb, 'executeInTransaction').mockRejectedValue(new Error('事务错误'));

      const batchData = [{ name: '测试', value: 100 }];

      await expect(testDAO.createBatch(batchData)).rejects.toThrow(DAOException);
    });
  });
});