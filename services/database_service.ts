/**
 * SQLite 数据库连接管理器
 * 负责数据库连接管理、连接池、事务处理等
 */

import sqlite3 from 'sqlite3';
import { open, Database, OPEN_READWRITE, OPEN_CREATE } from 'sqlite';
import { DateUtil } from './utils/date';
import { EventEmitter } from 'events';

export interface SQLiteConfig {
  filename: string;
  mode?: number;
  timeout?: number;
  verbose?: boolean;
  walMode?: boolean;
  cacheSize?: number;
  synchronousMode?: 'OFF' | 'NORMAL' | 'FULL' | 'EXTRA';
}

export interface ConnectionMetrics {
  totalConnections: number;
  activeConnections: number;
  idleConnections: number;
  waitingRequests: number;
  totalRequests: number;
  averageQueryTime: number;
  slowQueries: number;
}

export interface QueryResult {
  data?: any[];
  changes?: number;
  lastInsertRowid?: number;
  executionTime: number;
}

export class SQLiteConnectionManager extends EventEmitter {
  private db: Database | null = null;
  private config: SQLiteConfig;
  private metrics: ConnectionMetrics;
  private isConnected: boolean = false;
  private connectionPromise: Promise<void> | null = null;
  private slowQueryThreshold: number = 1000; // 1秒

  constructor(config: SQLiteConfig) {
    super();
    this.config = {
      mode: OPEN_READWRITE | OPEN_CREATE,
      timeout: 30000,
      verbose: false,
      walMode: true,
      cacheSize: 20000,
      synchronousMode: 'NORMAL',
      ...config
    };
    this.metrics = {
      totalConnections: 0,
      activeConnections: 0,
      idleConnections: 0,
      waitingRequests: 0,
      totalRequests: 0,
      averageQueryTime: 0,
      slowQueries: 0
    };
  }

  /**
   * 连接数据库
   */
  async connect(): Promise<void> {
    if (this.connectionPromise) {
      await this.connectionPromise;
      return;
    }

    this.connectionPromise = this._connectInternal();
    await this.connectionPromise;
  }

  private async _connectInternal(): Promise<void> {
    try {
      this.emit('connecting');
      
      // 设置 sqlite3 模式
      if (this.config.verbose) {
        sqlite3.verbose();
      }

      // 打开数据库连接
      this.db = await open({
        filename: this.config.filename,
        mode: this.config.mode,
        driver: sqlite3.Database
      });

      // 配置数据库参数
      await this._configureDatabase();

      // 测试连接
      await this.db.get('SELECT 1');

      this.isConnected = true;
      this.metrics.totalConnections = 1;
      
      this.emit('connected');
      console.log(`[Database] 成功连接到 SQLite 数据库: ${this.config.filename}`);
    } catch (error) {
      this.emit('error', error);
      throw new Error(`数据库连接失败: ${error.message}`);
    }
  }

  /**
   * 配置数据库参数
   */
  private async _configureDatabase(): Promise<void> {
    if (!this.db) throw new Error('数据库未连接');

    // 启用 WAL 模式以提高并发性能
    if (this.config.walMode) {
      await this.db.run('PRAGMA journal_mode = WAL;');
    }

    // 设置同步模式
    if (this.config.synchronousMode) {
      await this.db.run(`PRAGMA synchronous = ${this.config.synchronousMode};`);
    }

    // 设置缓存大小
    if (this.config.cacheSize) {
      await this.db.run(`PRAGMA cache_size = ${this.config.cacheSize};`);
    }

    // 设置临时存储模式
    await this.db.run('PRAGMA temp_store = memory;');

    // 启用外键约束
    await this.db.run('PRAGMA foreign_keys = ON;');

    // 设置超时时间
    if (this.config.timeout) {
      await this.db.run(`PRAGMA busy_timeout = ${this.config.timeout};`);
    }

    // 设置编译缓存大小
    await this.db.run('PRAGMA compile_options = ON;');
  }

  /**
   * 断开数据库连接
   */
  async disconnect(): Promise<void> {
    if (this.db && this.isConnected) {
      try {
        await this.db.close();
        this.db = null;
        this.isConnected = false;
        this.emit('disconnected');
        console.log('[Database] 数据库连接已断开');
      } catch (error) {
        this.emit('error', error);
        throw new Error(`断开数据库连接失败: ${error.message}`);
      }
    }
  }

  /**
   * 检查数据库连接状态
   */
  isReady(): boolean {
    return this.isConnected && this.db !== null;
  }

  /**
   * 执行查询
   */
  async query(sql: string, params: any[] = []): Promise<QueryResult> {
    const startTime = Date.now();
    
    try {
      this._ensureConnected();
      
      let result: QueryResult;
      
      if (sql.trim().toLowerCase().startsWith('select')) {
        // SELECT 查询
        const rows = await this.db!.all(sql, params);
        result = {
          data: rows,
          executionTime: Date.now() - startTime
        };
      } else {
        // INSERT, UPDATE, DELETE 等
        const stmt = await this.db!.run(sql, params);
        result = {
          changes: stmt.changes,
          lastInsertRowid: stmt.lastID,
          executionTime: Date.now() - startTime
        };
      }

      this._updateMetrics(result.executionTime, sql);
      return result;
    } catch (error) {
      this.emit('queryError', { sql, params, error });
      throw new Error(`查询执行失败: ${error.message}\nSQL: ${sql}`);
    }
  }

  /**
   * 执行单条查询并返回第一行
   */
  async querySingle(sql: string, params: any[] = []): Promise<any> {
    this._ensureConnected();
    return await this.db!.get(sql, params);
  }

  /**
   * 执行查询并返回所有行
   */
  async queryAll(sql: string, params: any[] = []): Promise<any[]> {
    this._ensureConnected();
    return await this.db!.all(sql, params);
  }

  /**
   * 执行插入操作
   */
  async insert(sql: string, params: any[] = []): Promise<number> {
    const result = await this.query(sql, params);
    return result.lastInsertRowid || 0;
  }

  /**
   * 执行更新操作
   */
  async update(sql: string, params: any[] = []): Promise<number> {
    const result = await this.query(sql, params);
    return result.changes || 0;
  }

  /**
   * 执行删除操作
   */
  async delete(sql: string, params: any[] = []): Promise<number> {
    const result = await this.query(sql, params);
    return result.changes || 0;
  }

  /**
   * 开始事务
   */
  async beginTransaction(): Promise<void> {
    await this.query('BEGIN TRANSACTION;');
  }

  /**
   * 提交事务
   */
  async commit(): Promise<void> {
    await this.query('COMMIT;');
  }

  /**
   * 回滚事务
   */
  async rollback(): Promise<void> {
    await this.query('ROLLBACK;');
  }

  /**
   * 在事务中执行操作
   */
  async transaction<T>(operations: () => Promise<T>): Promise<T> {
    await this.beginTransaction();
    
    try {
      const result = await operations();
      await this.commit();
      return result;
    } catch (error) {
      await this.rollback();
      throw error;
    }
  }

  /**
   * 执行事务性操作（带重试）
   */
  async executeInTransaction<T>(operation: (tx: Database) => Promise<T>, maxRetries: number = 3): Promise<T> {
    let retries = 0;
    
    while (retries < maxRetries) {
      try {
        this._ensureConnected();
        
        return await this.db!.transaction(operation)();
      } catch (error: any) {
        retries++;
        
        // 如果是锁定错误，则重试
        if (error.message.includes('database is locked') && retries < maxRetries) {
          console.log(`[Database] 数据库锁定，${1000 * retries}ms 后重试 (${retries}/${maxRetries})`);
          await new Promise(resolve => setTimeout(resolve, 1000 * retries));
          continue;
        }
        
        throw error;
      }
    }
    
    throw new Error(`事务执行失败，已重试 ${maxRetries} 次`);
  }

  /**
   * 获取数据库信息
   */
  async getDatabaseInfo(): Promise<any> {
    this._ensureConnected();
    
    return {
      filename: this.config.filename,
      mode: this.config.mode,
      isConnected: this.isConnected,
      timestamp: DateUtil.formatForSQLite(new Date())
    };
  }

  /**
   * 获取数据库大小
   */
  async getDatabaseSize(): Promise<number> {
    try {
      // SQLite 中获取数据库文件大小需要通过文件系统
      const fs = require('fs');
      const stats = fs.statSync(this.config.filename);
      return stats.size;
    } catch (error) {
      return 0;
    }
  }

  /**
   * 清理数据库
   */
  async vacuum(): Promise<void> {
    await this.query('VACUUM;');
  }

  /**
   * 分析数据库统计信息
   */
  async analyze(): Promise<void> {
    await this.query('ANALYZE;');
  }

  /**
   * 完整性检查
   */
  async integrityCheck(): Promise<any> {
    return await this.querySingle('PRAGMA integrity_check;');
  }

  /**
   * 获取数据库统计信息
   */
  async getStatistics(): Promise<any> {
    this._ensureConnected();
    
    const info = await Promise.all([
      this.querySingle('SELECT COUNT(*) as table_count FROM sqlite_master WHERE type="table"'),
      this.querySingle('SELECT COUNT(*) as index_count FROM sqlite_master WHERE type="index"'),
      this.querySingle('PRAGMA page_count'),
      this.querySingle('PRAGMA page_size'),
      this.querySingle('PRAGMA freelist_count')
    ]);

    return {
      tables: info[0].table_count,
      indexes: info[1].index_count,
      pageCount: info[2].page_count,
      pageSize: info[3].page_size,
      freePages: info[4].freelist_count,
      databaseSize: (info[2].page_count * info[3].page_size),
      freeSpace: (info[4].freelist_count * info[3].page_size),
      usedSpace: ((info[2].page_count - info[4].freelist_count) * info[3].page_size)
    };
  }

  /**
   * 获取性能指标
   */
  getMetrics(): ConnectionMetrics {
    return { ...this.metrics };
  }

  /**
   * 设置慢查询阈值
   */
  setSlowQueryThreshold(ms: number): void {
    this.slowQueryThreshold = ms;
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string; responseTime: number; details?: any }> {
    const startTime = Date.now();
    
    try {
      await this.query('SELECT 1');
      const responseTime = Date.now() - startTime;
      
      const details = await this.getStatistics();
      
      return {
        status: responseTime < 100 ? 'healthy' : responseTime < 500 ? 'warning' : 'unhealthy',
        responseTime,
        details
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime,
        details: { error: error.message }
      };
    }
  }

  /**
   * 获取原生数据库实例（谨慎使用）
   */
  getNativeDB(): Database | null {
    return this.db;
  }

  /**
   * 确保数据库已连接
   */
  private _ensureConnected(): void {
    if (!this.isConnected || !this.db) {
      throw new Error('数据库未连接');
    }
  }

  /**
   * 更新性能指标
   */
  private _updateMetrics(executionTime: number, sql: string): void {
    this.metrics.totalRequests++;
    
    // 更新平均查询时间
    this.metrics.averageQueryTime = 
      (this.metrics.averageQueryTime * (this.metrics.totalRequests - 1) + executionTime) / 
      this.metrics.totalRequests;
    
    // 检查慢查询
    if (executionTime > this.slowQueryThreshold) {
      this.metrics.slowQueries++;
      this.emit('slowQuery', { sql, executionTime, threshold: this.slowQueryThreshold });
    }
  }
}
