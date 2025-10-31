# DAO 层架构设计文档

## 概述

基于当前项目的错误监控和 API 捕获功能，设计一套完整的 DAO（Data Access Object）层架构，用于替代前端 Zustand 状态管理，实现数据的后端持久化和管理。

## 架构设计

### 1. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     业务逻辑层 (Service Layer)                │
├─────────────────────────────────────────────────────────────┤
│                     DAO 接口层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ ErrorLogDAO │ │ NetworkDAO  │ │SessionDAO   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│                     基础 DAO 类                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           BaseDAO (通用 CRUD 操作)                      │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     数据源层                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │Connection   │ │Transaction  │ │QueryBuilder │            │
│  │Manager      │ │Manager      │ │            │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│                     数据库层                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           PostgreSQL / SQLite                          │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2. DAO 接口设计

#### 2.1 通用 DAO 接口

```typescript
/**
 * 通用数据访问对象接口
 */
export interface IBaseDAO<T extends BaseEntity> {
  // 基础 CRUD 操作
  create(entity: Omit<T, 'id' | 'createdAt' | 'updatedAt'>): Promise<T>;
  findById(id: string): Promise<T | null>;
  findAll(params?: PaginationParams & FilterParams): Promise<PaginatedResult<T>>;
  update(id: string, entity: Partial<T>): Promise<T>;
  delete(id: string): Promise<boolean>;
  count(filter?: FilterParams): Promise<number>;
  
  // 批量操作
  createBatch(entities: Omit<T, 'id' | 'createdAt' | 'updatedAt'>[]): Promise<T[]>;
  updateBatch(entities: Partial<T>[]): Promise<T[]>;
  deleteBatch(ids: string[]): Promise<boolean[]>;
  
  // 事务支持
  executeInTransaction<T>(operation: (tx: Transaction) => Promise<T>): Promise<T>;
}
```

#### 2.2 专用 DAO 接口

```typescript
/**
 * 错误日志 DAO 接口
 */
export interface IErrorLogDAO extends IBaseDAO<ErrorLog> {
  findByType(type: string, params?: PaginationParams): Promise<PaginatedResult<ErrorLog>>;
  findByTabId(tabId: number, params?: PaginationParams): Promise<PaginatedResult<ErrorLog>>;
  findByTimeRange(startDate: Date, endDate: Date, params?: PaginationParams): Promise<PaginatedResult<ErrorLog>>;
  getErrorStatistics(startDate?: Date, endDate?: Date): Promise<Statistics>;
  cleanupOldLogs(olderThanDays: number): Promise<number>;
}

/**
 * 网络请求 DAO 接口
 */
export interface INetworkRequestDAO extends IBaseDAO<NetworkRequest> {
  findByApiType(apiType: string, params?: PaginationParams): Promise<PaginatedResult<NetworkRequest>>;
  findByTabId(tabId: number, params?: PaginationParams): Promise<PaginatedResult<NetworkRequest>>;
  findSlowRequests(minDuration: number, params?: PaginationParams): Promise<PaginatedResult<NetworkRequest>>;
  getApiStatistics(startDate?: Date, endDate?: Date): Promise<Statistics>;
}

/**
 * 用户会话 DAO 接口
 */
export interface IUserSessionDAO extends IBaseDAO<UserSession> {
  findActiveSessions(): Promise<UserSession[]>;
  findByTabId(tabId: number): Promise<UserSession | null>;
  closeSession(sessionId: string, endTime?: Date): Promise<UserSession>;
  getSessionStatistics(startDate?: Date, endDate?: Date): Promise<Statistics>;
}

/**
 * API 成功日志 DAO 接口
 */
export interface IApiSuccessLogDAO extends IBaseDAO<ApiSuccessLog> {
  findByProjectId(projectId: string, params?: PaginationParams): Promise<PaginatedResult<ApiSuccessLog>>;
  findByApiPath(apiPath: string, params?: PaginationParams): Promise<PaginatedResult<ApiSuccessLog>>;
  getApiPerformanceMetrics(startDate?: Date, endDate?: Date): Promise<Statistics>;
}
```

### 3. 基础数据访问类

```typescript
/**
 * 基础 DAO 实现类
 * 提供通用的 CRUD 操作和事务管理
 */
export abstract class BaseDAO<T extends BaseEntity> implements IBaseDAO<T> {
  protected abstract tableName: string;
  
  constructor(
    protected connectionManager: IConnectionManager,
    protected queryBuilder: IQueryBuilder
  ) {}

  async create(entity: Omit<T, 'id' | 'createdAt' | 'updatedAt'>): Promise<T> {
    const now = new Date();
    const data = {
      ...entity,
      id: generateId(),
      createdAt: now,
      updatedAt: now
    };
    
    const sql = this.queryBuilder
      .insert(this.tableName, data)
      .returning('*')
      .toString();
    
    const result = await this.connectionManager.query(sql, Object.values(data));
    return this.mapToEntity(result.rows[0]);
  }

  async findById(id: string): Promise<T | null> {
    const sql = this.queryBuilder
      .select()
      .from(this.tableName)
      .where({ id })
      .toString();
    
    const result = await this.connectionManager.query(sql, [id]);
    return result.rows.length > 0 ? this.mapToEntity(result.rows[0]) : null;
  }

  async findAll(params?: PaginationParams & FilterParams): Promise<PaginatedResult<T>> {
    const { page = 1, limit = 20, sortBy = 'createdAt', sortOrder = 'desc', ...filters } = params || {};
    const offset = (page - 1) * limit;
    
    let query = this.queryBuilder
      .select()
      .from(this.tableName);
    
    // 应用过滤条件
    if (filters.startDate) {
      query = query.and({ createdAt: { $gte: filters.startDate } });
    }
    if (filters.endDate) {
      query = query.and({ createdAt: { $lte: filters.endDate } });
    }
    
    query = query
      .orderBy(sortBy, sortOrder)
      .limit(limit)
      .offset(offset);
    
    const countQuery = this.queryBuilder
      .select('COUNT(*)')
      .from(this.tableName);
    
    const count = await this.connectionManager.query(countQuery.toString());
    const total = parseInt(count.rows[0].count);
    
    const result = await this.connectionManager.query(query.toString());
    
    return {
      data: result.rows.map(row => this.mapToEntity(row)),
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
      hasNext: page * limit < total,
      hasPrev: page > 1
    };
  }

  async update(id: string, entity: Partial<T>): Promise<T> {
    const updatedEntity = {
      ...entity,
      updatedAt: new Date()
    };
    
    const sql = this.queryBuilder
      .update(this.tableName, updatedEntity)
      .where({ id })
      .returning('*')
      .toString();
    
    const result = await this.connectionManager.query(sql, Object.values(updatedEntity));
    return this.mapToEntity(result.rows[0]);
  }

  async delete(id: string): Promise<boolean> {
    const sql = this.queryBuilder
      .delete(this.tableName)
      .where({ id })
      .toString();
    
    const result = await this.connectionManager.query(sql, [id]);
    return result.rowCount > 0;
  }

  async count(filter?: FilterParams): Promise<number> {
    let query = this.queryBuilder.select('COUNT(*)').from(this.tableName);
    
    if (filter) {
      if (filter.startDate) {
        query = query.and({ createdAt: { $gte: filter.startDate } });
      }
      if (filter.endDate) {
        query = query.and({ createdAt: { $lte: filter.endDate } });
      }
    }
    
    const result = await this.connectionManager.query(query.toString());
    return parseInt(result.rows[0].count);
  }

  async createBatch(entities: Omit<T, 'id' | 'createdAt' | 'updatedAt'>[]): Promise<T[]> {
    const now = new Date();
    const data = entities.map(entity => ({
      ...entity,
      id: generateId(),
      createdAt: now,
      updatedAt: now
    }));
    
    const sql = this.queryBuilder
      .insertBatch(this.tableName, data)
      .returning('*')
      .toString();
    
    const result = await this.connectionManager.query(sql, data.flatMap(item => Object.values(item)));
    return result.rows.map(row => this.mapToEntity(row));
  }

  async executeInTransaction<R>(operation: (tx: Transaction) => Promise<R>): Promise<R> {
    return this.connectionManager.executeInTransaction(operation);
  }

  protected abstract mapToEntity(row: any): T;
}

/**
 * 错误日志 DAO 实现
 */
export class ErrorLogDAO extends BaseDAO<ErrorLog> implements IErrorLogDAO {
  protected tableName = 'error_logs';
  
  constructor(
    connectionManager: IConnectionManager,
    queryBuilder: IQueryBuilder
  ) {
    super(connectionManager, queryBuilder);
  }
  
  async findByType(type: string, params?: PaginationParams): Promise<PaginatedResult<ErrorLog>> {
    return this.findAll({ ...params, errorType: type });
  }
  
  async findByTabId(tabId: number, params?: PaginationParams): Promise<PaginatedResult<ErrorLog>> {
    return this.findAll({ ...params, tabId });
  }
  
  async findByTimeRange(startDate: Date, endDate: Date, params?: PaginationParams): Promise<PaginatedResult<ErrorLog>> {
    return this.findAll({ ...params, startDate, endDate });
  }
  
  async getErrorStatistics(startDate?: Date, endDate?: Date): Promise<Statistics> {
    const filter = startDate || endDate ? { startDate, endDate } : undefined;
    const total = await this.count(filter);
    
    const sql = `
      SELECT 
        type,
        COUNT(*) as count
      FROM error_logs
      ${startDate ? 'WHERE created_at >= $1' : ''}
      ${startDate && endDate ? ' AND ' : ''}
      ${endDate ? 'created_at <= $2' : ''}
      GROUP BY type
    `;
    
    const result = await this.connectionManager.query(sql, [startDate, endDate].filter(Boolean));
    
    return {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: total,
      totalErrors: total,
      averageResponseTime: 0,
      errorRate: 100,
      period: `${startDate?.toISOString() || 'beginning'} - ${endDate?.toISOString() || 'now'}`,
      createdAt: new Date()
    };
  }
  
  async cleanupOldLogs(olderThanDays: number): Promise<number> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);
    
    const sql = this.queryBuilder
      .delete(this.tableName)
      .where({ createdAt: { $lt: cutoffDate } })
      .toString();
    
    const result = await this.connectionManager.query(sql, [cutoffDate]);
    return result.rowCount || 0;
  }
  
  protected mapToEntity(row: any): ErrorLog {
    return {
      ...row,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at),
      timestamp: row.timestamp || row.created_at,
      stack: row.stack || undefined,
      error: row.error ? JSON.parse(row.error) : undefined,
      element: row.element ? JSON.parse(row.element) : undefined
    };
  }
}
```

### 4. 事务管理

```typescript
/**
 * 事务管理器接口
 */
export interface ITransactionManager {
  startTransaction(): Promise<Transaction>;
  commit(transaction: Transaction): Promise<void>;
  rollback(transaction: Transaction): Promise<void>;
  executeInTransaction<T>(operation: (tx: Transaction) => Promise<T>): Promise<T>;
}

/**
 * 事务管理器实现
 */
export class TransactionManager implements ITransactionManager {
  private activeTransactions = new Map<string, Transaction>();
  private transactionCounter = 0;
  
  constructor(private connectionManager: IConnectionManager) {}
  
  async startTransaction(): Promise<Transaction> {
    const transactionId = `tx_${++this.transactionCounter}`;
    const transaction: Transaction = {
      id: transactionId,
      status: 'pending',
      startTime: new Date(),
      operations: []
    };
    
    try {
      await this.connectionManager.beginTransaction();
      this.activeTransactions.set(transactionId, transaction);
      return transaction;
    } catch (error) {
      throw new DaoException('Failed to start transaction', 'TX_START_FAILED', error);
    }
  }
  
  async commit(transaction: Transaction): Promise<void> {
    if (transaction.status !== 'pending') {
      throw new DaoException('Transaction is not in pending state', 'TX_INVALID_STATE');
    }
    
    try {
      await this.connectionManager.commit();
      transaction.status = 'committed';
      transaction.endTime = new Date();
      this.activeTransactions.delete(transaction.id);
    } catch (error) {
      transaction.status = 'failed';
      throw new DaoException('Failed to commit transaction', 'TX_COMMIT_FAILED', error);
    }
  }
  
  async rollback(transaction: Transaction): Promise<void> {
    if (transaction.status !== 'pending') {
      throw new DaoException('Transaction is not in pending state', 'TX_INVALID_STATE');
    }
    
    try {
      await this.connectionManager.rollback();
      transaction.status = 'rolled_back';
      transaction.endTime = new Date();
      this.activeTransactions.delete(transaction.id);
    } catch (error) {
      transaction.status = 'failed';
      throw new DaoException('Failed to rollback transaction', 'TX_ROLLBACK_FAILED', error);
    }
  }
  
  async executeInTransaction<T>(operation: (tx: Transaction) => Promise<T>): Promise<T> {
    const transaction = await this.startTransaction();
    
    try {
      const result = await operation(transaction);
      await this.commit(transaction);
      return result;
    } catch (error) {
      await this.rollback(transaction);
      throw error;
    }
  }
}

/**
 * 分布式事务协调器（可选）
 */
export class DistributedTransactionCoordinator {
  private participants = new Map<string, ITransactionParticipant>();
  
  registerParticipant(id: string, participant: ITransactionParticipant): void {
    this.participants.set(id, participant);
  }
  
  async executeTwoPhaseCommit(transaction: Transaction): Promise<void> {
    // Phase 1: Prepare
    const prepareResults = await Promise.all(
      Array.from(this.participants.values()).map(participant =>
        participant.prepare(transaction)
      )
    );
    
    // 检查所有参与者是否准备好
    if (prepareResults.some(result => !result.success)) {
      // 如果有参与者准备失败，回滚所有
      await Promise.all(
        Array.from(this.participants.values()).map(participant =>
          participant.rollback(transaction)
        )
      );
      throw new DaoException('Distributed transaction prepare phase failed', 'DTX_PREPARE_FAILED');
    }
    
    // Phase 2: Commit
    await Promise.all(
      Array.from(this.participants.values()).map(participant =>
        participant.commit(transaction)
      )
    );
  }
}
```

### 5. 数据库连接管理

```typescript
/**
 * 连接管理器接口
 */
export interface IConnectionManager {
  // 基础连接操作
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  
  // 查询执行
  query(sql: string, params?: any[]): Promise<QueryResult>;
  execute(sql: string, params?: any[]): Promise<QueryResult>;
  
  // 事务支持
  beginTransaction(): Promise<void>;
  commit(): Promise<void>;
  rollback(): Promise<void>;
  
  // 连接池管理
  getConnection(): Promise<PoolClient>;
  releaseConnection(client: PoolClient): void;
  
  // 事务中的操作
  executeInTransaction<R>(operation: (client: PoolClient) => Promise<R>): Promise<R>;
}

/**
 * 连接池管理器实现
 */
export class ConnectionManager implements IConnectionManager {
  private pool: Pool | null = null;
  private config: DatabaseConfig;
  private poolConfig: PoolConfig;
  
  constructor(config: DatabaseConfig, poolConfig: PoolConfig) {
    this.config = config;
    this.poolConfig = poolConfig;
  }
  
  async connect(): Promise<void> {
    try {
      this.pool = new Pool({
        host: this.config.host,
        port: this.config.port,
        database: this.config.database,
        user: this.config.username,
        password: this.config.password,
        ssl: this.config.ssl,
        min: this.poolConfig.min,
        max: this.poolConfig.max,
        idleTimeoutMillis: this.poolConfig.idleTimeoutMillis,
        connectionTimeoutMillis: this.poolConfig.acquireTimeoutMillis
      });
      
      // 测试连接
      const client = await this.pool.connect();
      client.release();
      
      console.log('Database connection established');
    } catch (error) {
      throw new DaoException('Failed to connect to database', 'DB_CONNECTION_FAILED', error);
    }
  }
  
  async disconnect(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
      this.pool = null;
    }
  }
  
  async query(sql: string, params?: any[]): Promise<QueryResult> {
    if (!this.pool) {
      throw new DaoException('Database not connected', 'DB_NOT_CONNECTED');
    }
    
    try {
      const result = await this.pool.query(sql, params);
      return {
        rows: result.rows,
        rowCount: result.rowCount,
        fields: result.fields
      };
    } catch (error) {
      throw new DaoException(`Query failed: ${error.message}`, 'DB_QUERY_FAILED', error);
    }
  }
  
  async execute(sql: string, params?: any[]): Promise<QueryResult> {
    return this.query(sql, params);
  }
  
  async beginTransaction(): Promise<void> {
    await this.query('BEGIN');
  }
  
  async commit(): Promise<void> {
    await this.query('COMMIT');
  }
  
  async rollback(): Promise<void> {
    await this.query('ROLLBACK');
  }
  
  async getConnection(): Promise<PoolClient> {
    if (!this.pool) {
      throw new DaoException('Database not connected', 'DB_NOT_CONNECTED');
    }
    
    return this.pool.connect();
  }
  
  releaseConnection(client: PoolClient): void {
    client.release();
  }
  
  async executeInTransaction<R>(operation: (client: PoolClient) => Promise<R>): Promise<R> {
    const client = await this.getConnection();
    
    try {
      await client.query('BEGIN');
      const result = await operation(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
  
  // 连接健康检查
  async healthCheck(): Promise<{ status: string; responseTime: number }> {
    const startTime = Date.now();
    
    try {
      await this.query('SELECT 1');
      const responseTime = Date.now() - startTime;
      
      return {
        status: 'healthy',
        responseTime
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime
      };
    }
  }
}

/**
 * 连接池监控
 */
export class ConnectionMonitor {
  private metrics = {
    totalConnections: 0,
    activeConnections: 0,
    idleConnections: 0,
    waitingRequests: 0,
    totalRequests: 0,
    averageWaitTime: 0
  };
  
  constructor(private connectionManager: ConnectionManager) {}
  
  async collectMetrics(): Promise<typeof this.metrics> {
    if (this.connectionManager['pool']) {
      const pool = this.connectionManager['pool'];
      this.metrics.totalConnections = pool.totalCount;
      this.metrics.activeConnections = pool.busyCount;
      this.metrics.idleConnections = pool.idleCount;
      this.metrics.waitingRequests = pool.waitingCount;
    }
    
    return { ...this.metrics };
  }
  
  generateReport(): string {
    return `
      Connection Pool Report:
      - Total Connections: ${this.metrics.totalConnections}
      - Active Connections: ${this.metrics.activeConnections}
      - Idle Connections: ${this.metrics.idleConnections}
      - Waiting Requests: ${this.metrics.waitingRequests}
      - Total Requests: ${this.metrics.totalRequests}
      - Average Wait Time: ${this.metrics.averageWaitTime}ms
    `;
  }
}
```

### 6. 查询构建器

```typescript
/**
 * 查询构建器接口
 */
export interface IQueryBuilder {
  // SELECT 查询
  select(fields?: string[]): IQueryBuilder;
  
  // FROM 子句
  from(table: string): IQueryBuilder;
  
  // WHERE 子句
  where(conditions: Record<string, any>): IQueryBuilder;
  and(conditions: Record<string, any>): IQueryBuilder;
  or(conditions: Record<string, any>): IQueryBuilder;
  
  // ORDER BY 子句
  orderBy(field: string, direction?: 'asc' | 'desc'): IQueryBuilder;
  
  // GROUP BY 子句
  groupBy(fields: string[]): IQueryBuilder;
  
  // HAVING 子句
  having(conditions: Record<string, any>): IQueryBuilder;
  
  // LIMIT/OFFSET
  limit(count: number): IQueryBuilder;
  offset(count: number): IQueryBuilder;
  
  // INSERT 操作
  insert(table: string, data: Record<string, any>): IQueryBuilder;
  insertBatch(table: string, data: Record<string, any>[]): IQueryBuilder;
  
  // UPDATE 操作
  update(table: string, data: Record<string, any>): IQueryBuilder;
  
  // DELETE 操作
  delete(table: string): IQueryBuilder;
  
  // JOIN 操作
  join(table: string, condition: string): IQueryBuilder;
  leftJoin(table: string, condition: string): IQueryBuilder;
  rightJoin(table: string, condition: string): IQueryBuilder;
  
  // 聚合函数
  count(field?: string): IQueryBuilder;
  sum(field: string): IQueryBuilder;
  avg(field: string): IQueryBuilder;
  max(field: string): IQueryBuilder;
  min(field: string): IQueryBuilder;
  
  // 返回 SQL 字符串
  toString(): string;
  
  // 返回参数数组
  getParams(): any[];
}

/**
 * SQL 查询构建器实现
 */
export class QueryBuilder implements IQueryBuilder {
  private query: {
    type: 'select' | 'insert' | 'update' | 'delete';
    table?: string;
    fields?: string[];
    whereConditions: string[];
    whereParams: any[];
    orderByFields?: { field: string; direction: string }[];
    groupByFields?: string[];
    havingConditions?: string[];
    limitCount?: number;
    offsetCount?: number;
    joins?: { type: 'JOIN' | 'LEFT JOIN' | 'RIGHT JOIN'; table: string; condition: string }[];
    insertData?: Record<string, any>[];
    updateData?: Record<string, any>;
  } = {
    type: 'select',
    whereConditions: [],
    whereParams: []
  };
  
  static table(name: string): QueryBuilder {
    const builder = new QueryBuilder();
    builder.query.table = name;
    return builder;
  }
  
  select(fields?: string[]): IQueryBuilder {
    this.query.type = 'select';
    this.query.fields = fields || ['*'];
    return this;
  }
  
  from(table: string): IQueryBuilder {
    this.query.table = table;
    return this;
  }
  
  where(conditions: Record<string, any>): IQueryBuilder {
    const { clause, params } = this.buildConditions(conditions);
    this.query.whereConditions.push(clause);
    this.query.whereParams.push(...params);
    return this;
  }
  
  and(conditions: Record<string, any>): IQueryBuilder {
    const { clause, params } = this.buildConditions(conditions, 'AND');
    this.query.whereConditions.push(`AND ${clause}`);
    this.query.whereParams.push(...params);
    return this;
  }
  
  or(conditions: Record<string, any>): IQueryBuilder {
    const { clause, params } = this.buildConditions(conditions, 'OR');
    this.query.whereConditions.push(`OR ${clause}`);
    this.query.whereParams.push(...params);
    return this;
  }
  
  orderBy(field: string, direction: 'asc' | 'desc' = 'asc'): IQueryBuilder {
    if (!this.query.orderByFields) {
      this.query.orderByFields = [];
    }
    this.query.orderByFields.push({ field, direction });
    return this;
  }
  
  groupBy(fields: string[]): IQueryBuilder {
    this.query.groupByFields = fields;
    return this;
  }
  
  having(conditions: Record<string, any>): IQueryBuilder {
    const { clause } = this.buildConditions(conditions);
    this.query.havingConditions = [clause];
    return this;
  }
  
  limit(count: number): IQueryBuilder {
    this.query.limitCount = count;
    return this;
  }
  
  offset(count: number): IQueryBuilder {
    this.query.offsetCount = count;
    return this;
  }
  
  insert(table: string, data: Record<string, any>): IQueryBuilder {
    this.query.type = 'insert';
    this.query.table = table;
    this.query.insertData = [data];
    return this;
  }
  
  insertBatch(table: string, data: Record<string, any>[]): IQueryBuilder {
    this.query.type = 'insert';
    this.query.table = table;
    this.query.insertData = data;
    return this;
  }
  
  update(table: string, data: Record<string, any>): IQueryBuilder {
    this.query.type = 'update';
    this.query.table = table;
    this.query.updateData = data;
    return this;
  }
  
  delete(table: string): IQueryBuilder {
    this.query.type = 'delete';
    this.query.table = table;
    return this;
  }
  
  join(table: string, condition: string): IQueryBuilder {
    if (!this.query.joins) {
      this.query.joins = [];
    }
    this.query.joins.push({ type: 'JOIN', table, condition });
    return this;
  }
  
  leftJoin(table: string, condition: string): IQueryBuilder {
    if (!this.query.joins) {
      this.query.joins = [];
    }
    this.query.joins.push({ type: 'LEFT JOIN', table, condition });
    return this;
  }
  
  rightJoin(table: string, condition: string): IQueryBuilder {
    if (!this.query.joins) {
      this.query.joins = [];
    }
    this.query.joins.push({ type: 'RIGHT JOIN', table, condition });
    return this;
  }
  
  count(field?: string): IQueryBuilder {
    this.query.fields = [`COUNT(${field || '*'})`];
    return this;
  }
  
  sum(field: string): IQueryBuilder {
    this.query.fields = [`SUM(${field})`];
    return this;
  }
  
  avg(field: string): IQueryBuilder {
    this.query.fields = [`AVG(${field})`];
    return this;
  }
  
  max(field: string): IQueryBuilder {
    this.query.fields = [`MAX(${field})`];
    return this;
  }
  
  min(field: string): IQueryBuilder {
    this.query.fields = [`MIN(${field})`];
    return this;
  }
  
  toString(): string {
    switch (this.query.type) {
      case 'select':
        return this.buildSelectQuery();
      case 'insert':
        return this.buildInsertQuery();
      case 'update':
        return this.buildUpdateQuery();
      case 'delete':
        return this.buildDeleteQuery();
      default:
        throw new Error('Invalid query type');
    }
  }
  
  getParams(): any[] {
    return [...this.query.whereParams];
  }
  
  private buildConditions(conditions: Record<string, any>, connector: 'AND' | 'OR' = 'AND'): { clause: string; params: any[] } {
    const clauses: string[] = [];
    const params: any[] = [];
    
    for (const [key, value] of Object.entries(conditions)) {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        // 处理复杂条件 { $gte: value, $lte: value }
        const subClauses: string[] = [];
        for (const [operator, opValue] of Object.entries(value)) {
          switch (operator) {
            case '$eq':
              subClauses.push(`${key} = $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$ne':
              subClauses.push(`${key} <> $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$gt':
              subClauses.push(`${key} > $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$gte':
              subClauses.push(`${key} >= $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$lt':
              subClauses.push(`${key} < $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$lte':
              subClauses.push(`${key} <= $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$like':
              subClauses.push(`${key} LIKE $${params.length + 1}`);
              params.push(opValue);
              break;
            case '$in':
              const placeholders = Array.isArray(opValue) 
                ? opValue.map(() => `$${params.length + 1}`).join(', ')
                : `$${params.length + 1}`;
              subClauses.push(`${key} IN (${placeholders})`);
              params.push(...(Array.isArray(opValue) ? opValue : [opValue]));
              break;
          }
        }
        if (subClauses.length > 0) {
          clauses.push(`(${subClauses.join(' AND ')})`);
        }
      } else {
        clauses.push(`${key} = $${params.length + 1}`);
        params.push(value);
      }
    }
    
    return {
      clause: clauses.join(` ${connector} `),
      params
    };
  }
  
  private buildSelectQuery(): string {
    let sql = `SELECT ${this.query.fields?.join(', ') || '*'} FROM ${this.query.table}`;
    
    // 添加 JOIN
    if (this.query.joins) {
      for (const join of this.query.joins) {
        sql += ` ${join.type} ${join.table} ON ${join.condition}`;
      }
    }
    
    // 添加 WHERE
    if (this.query.whereConditions.length > 0) {
      sql += ` WHERE ${this.query.whereConditions.join(' ')}`;
    }
    
    // 添加 GROUP BY
    if (this.query.groupByFields && this.query.groupByFields.length > 0) {
      sql += ` GROUP BY ${this.query.groupByFields.join(', ')}`;
    }
    
    // 添加 HAVING
    if (this.query.havingConditions && this.query.havingConditions.length > 0) {
      sql += ` HAVING ${this.query.havingConditions.join(' ')}`;
    }
    
    // 添加 ORDER BY
    if (this.query.orderByFields && this.query.orderByFields.length > 0) {
      const orderClauses = this.query.orderByFields.map(item => `${item.field} ${item.direction}`);
      sql += ` ORDER BY ${orderClauses.join(', ')}`;
    }
    
    // 添加 LIMIT
    if (this.query.limitCount) {
      sql += ` LIMIT ${this.query.limitCount}`;
    }
    
    // 添加 OFFSET
    if (this.query.offsetCount) {
      sql += ` OFFSET ${this.query.offsetCount}`;
    }
    
    return sql;
  }
  
  private buildInsertQuery(): string {
    if (!this.query.insertData || this.query.insertData.length === 0) {
      throw new Error('No data to insert');
    }
    
    const data = this.query.insertData[0];
    const columns = Object.keys(data);
    const placeholders = columns.map((_, index) => `$${index + 1}`).join(', ');
    
    if (this.query.insertData.length === 1) {
      // 单行插入
      return `INSERT INTO ${this.query.table} (${columns.join(', ')}) VALUES (${placeholders})`;
    } else {
      // 批量插入
      const valuesClauses = this.query.insertData.map((row, rowIndex) => {
        const rowPlaceholders = columns.map((_, colIndex) => 
          `$${rowIndex * columns.length + colIndex + 1}`
        ).join(', ');
        return `(${rowPlaceholders})`;
      }).join(', ');
      
      return `INSERT INTO ${this.query.table} (${columns.join(', ')}) VALUES ${valuesClauses}`;
    }
  }
  
  private buildUpdateQuery(): string {
    if (!this.query.updateData) {
      throw new Error('No data to update');
    }
    
    const updates = Object.keys(this.query.updateData).map((key, index) => 
      `${key} = $${index + 1}`
    );
    
    let sql = `UPDATE ${this.query.table} SET ${updates.join(', ')}`;
    
    // 添加 WHERE
    if (this.query.whereConditions.length > 0) {
      sql += ` WHERE ${this.query.whereConditions.join(' ')}`;
    }
    
    return sql;
  }
  
  private buildDeleteQuery(): string {
    let sql = `DELETE FROM ${this.query.table}`;
    
    // 添加 WHERE
    if (this.query.whereConditions.length > 0) {
      sql += ` WHERE ${this.query.whereConditions.join(' ')}`;
    }
    
    return sql;
  }
}
```

### 7. 数据缓存层

```typescript
/**
 * 缓存管理器接口
 */
export interface ICacheManager {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, ttl?: number): Promise<void>;
  delete(key: string): Promise<boolean>;
  clear(): Promise<void>;
  has(key: string): Promise<boolean>;
}

/**
 * 内存缓存实现
 */
export class MemoryCache implements ICacheManager {
  private cache = new Map<string, { value: any; expiresAt: number }>();
  
  constructor(private config: CacheConfig) {}
  
  async get<T>(key: string): Promise<T | null> {
    const item = this.cache.get(key);
    
    if (!item) {
      return null;
    }
    
    if (Date.now() > item.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    
    return item.value;
  }
  
  async set<T>(key: string, value: T, ttl?: number): Promise<void> {
    const expiresAt = Date.now() + (ttl || this.config.ttl) * 1000;
    this.cache.set(key, { value, expiresAt });
    
    // 如果缓存超过最大大小，删除最旧的条目
    if (this.cache.size > this.config.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }
  
  async delete(key: string): Promise<boolean> {
    return this.cache.delete(key);
  }
  
  async clear(): Promise<void> {
    this.cache.clear();
  }
  
  async has(key: string): Promise<boolean> {
    const item = this.cache.get(key);
    
    if (!item) {
      return false;
    }
    
    if (Date.now() > item.expiresAt) {
      this.cache.delete(key);
      return false;
    }
    
    return true;
  }
}

/**
 * Redis 缓存实现（可选）
 */
export class RedisCache implements ICacheManager {
  private client: Redis;
  
  constructor(
    private redis: Redis,
    private config: CacheConfig
  ) {
    this.client = redis;
  }
  
  async get<T>(key: string): Promise<T | null> {
    const value = await this.client.get(key);
    return value ? JSON.parse(value) : null;
  }
  
  async set<T>(key: string, value: T, ttl?: number): Promise<void> {
    const serialized = JSON.stringify(value);
    const expiration = ttl || this.config.ttl;
    
    if (expiration > 0) {
      await this.client.setex(key, expiration, serialized);
    } else {
      await this.client.set(key, serialized);
    }
  }
  
  async delete(key: string): Promise<boolean> {
    const result = await this.client.del(key);
    return result > 0;
  }
  
  async clear(): Promise<void> {
    await this.client.flushdb();
  }
  
  async has(key: string): Promise<boolean> {
    const result = await this.client.exists(key);
    return result === 1;
  }
}
```

### 8. 数据库模式定义

```sql
-- 创建数据库模式
CREATE SCHEMA IF NOT EXISTS matrix_monitor;

-- 错误日志表
CREATE TABLE matrix_monitor.error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    filename VARCHAR(500),
    lineno INTEGER,
    colno INTEGER,
    stack TEXT,
    element JSONB,
    error JSONB,
    error_message VARCHAR(500),
    tab_id INTEGER,
    url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 网络请求表
CREATE TABLE matrix_monitor.network_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(100) UNIQUE NOT NULL,
    url VARCHAR(1000) NOT NULL,
    method VARCHAR(10) NOT NULL,
    tab_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    initiator VARCHAR(500),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    start_time BIGINT NOT NULL,
    duration INTEGER,
    success BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API 请求信息表
CREATE TABLE matrix_monitor.api_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES matrix_monitor.network_requests(id),
    project_id VARCHAR(100) NOT NULL,
    api_type VARCHAR(50) NOT NULL,
    api_path VARCHAR(500) NOT NULL,
    query TEXT,
    request_body JSONB,
    headers JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API 响应信息表
CREATE TABLE matrix_monitor.api_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES matrix_monitor.network_requests(id),
    status_code INTEGER NOT NULL,
    status_text VARCHAR(200),
    response_headers JSONB,
    response_body JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户会话表
CREATE TABLE matrix_monitor.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    tab_id INTEGER NOT NULL,
    url VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTEGER,
    request_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API 成功日志表
CREATE TABLE matrix_monitor.api_success_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(100) DEFAULT 'supabase.api.success',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    request JSONB NOT NULL,
    response JSONB NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 统计数据表
CREATE TABLE matrix_monitor.statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    average_response_time DECIMAL(10,2) DEFAULT 0,
    error_rate DECIMAL(5,2) DEFAULT 0,
    period VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_error_logs_type ON matrix_monitor.error_logs(type);
CREATE INDEX idx_error_logs_timestamp ON matrix_monitor.error_logs(timestamp);
CREATE INDEX idx_error_logs_tab_id ON matrix_monitor.error_logs(tab_id);

CREATE INDEX idx_network_requests_tab_id ON matrix_monitor.network_requests(tab_id);
CREATE INDEX idx_network_requests_timestamp ON matrix_monitor.network_requests(timestamp);
CREATE INDEX idx_network_requests_success ON matrix_monitor.network_requests(success);
CREATE INDEX idx_network_requests_api_type ON matrix_monitor.network_requests(api_type);

CREATE INDEX idx_api_requests_project_id ON matrix_monitor.api_requests(project_id);
CREATE INDEX idx_api_requests_api_type ON matrix_monitor.api_requests(api_type);
CREATE INDEX idx_api_requests_api_path ON matrix_monitor.api_requests(api_path);

CREATE INDEX idx_user_sessions_tab_id ON matrix_monitor.user_sessions(tab_id);
CREATE INDEX idx_user_sessions_session_id ON matrix_monitor.user_sessions(session_id);
CREATE INDEX idx_user_sessions_start_time ON matrix_monitor.user_sessions(start_time);

CREATE INDEX idx_api_success_logs_timestamp ON matrix_monitor.api_success_logs(timestamp);
CREATE INDEX idx_api_success_logs_project_id ON matrix_monitor.api_success_logs USING gin((request->>'projectId'));

-- 创建触发器函数来自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表创建触发器
CREATE TRIGGER update_error_logs_updated_at 
    BEFORE UPDATE ON matrix_monitor.error_logs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_network_requests_updated_at 
    BEFORE UPDATE ON matrix_monitor.network_requests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_sessions_updated_at 
    BEFORE UPDATE ON matrix_monitor.user_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 9. 使用示例

```typescript
/**
 * DAO 层使用示例
 */
class ErrorMonitoringService {
  private errorLogDAO: IErrorLogDAO;
  private networkRequestDAO: INetworkRequestDAO;
  private sessionDAO: IUserSessionDAO;
  private cacheManager: ICacheManager;
  
  constructor(
    connectionManager: IConnectionManager,
    queryBuilder: IQueryBuilder,
    cacheManager: ICacheManager
  ) {
    this.errorLogDAO = new ErrorLogDAO(connectionManager, queryBuilder);
    this.networkRequestDAO = new NetworkRequestDAO(connectionManager, queryBuilder);
    this.sessionDAO = new UserSessionDAO(connectionManager, queryBuilder);
    this.cacheManager = cacheManager;
  }
  
  /**
   * 记录错误日志
   */
  async logError(errorData: Omit<ErrorLog, 'id' | 'createdAt' | 'updatedAt'>): Promise<ErrorLog> {
    try {
      // 在事务中记录错误
      return await this.errorLogDAO.executeInTransaction(async (tx) => {
        const error = await this.errorLogDAO.create(errorData);
        
        // 更新会话统计
        await this.updateSessionStatistics(error.tabId, { errorIncrement: 1 });
        
        // 清除相关缓存
        await this.clearErrorCache(error.tabId);
        
        return error;
      });
    } catch (error) {
      console.error('Failed to log error:', error);
      throw new DaoException('Failed to log error', 'LOG_ERROR_FAILED', error);
    }
  }
  
  /**
   * 记录网络请求
   */
  async logNetworkRequest(requestData: Omit<NetworkRequest, 'id' | 'createdAt' | 'updatedAt'>): Promise<NetworkRequest> {
    try {
      return await this.networkRequestDAO.create(requestData);
    } catch (error) {
      console.error('Failed to log network request:', error);
      throw new DaoException('Failed to log network request', 'LOG_REQUEST_FAILED', error);
    }
  }
  
  /**
   * 获取错误统计信息（带缓存）
   */
  async getErrorStatistics(startDate?: Date, endDate?: Date): Promise<Statistics> {
    const cacheKey = `error_stats_${startDate?.toISOString() || 'start'}_${endDate?.toISOString() || 'end'}`;
    
    // 尝试从缓存获取
    const cached = await this.cacheManager.get<Statistics>(cacheKey);
    if (cached) {
      return cached;
    }
    
    // 从数据库获取
    const statistics = await this.errorLogDAO.getErrorStatistics(startDate, endDate);
    
    // 缓存结果（5分钟）
    await this.cacheManager.set(cacheKey, statistics, 300);
    
    return statistics;
  }
  
  /**
   * 批量导入错误日志
   */
  async batchImportErrors(errors: Omit<ErrorLog, 'id' | 'createdAt' | 'updatedAt'>[]): Promise<ErrorLog[]> {
    try {
      return await this.errorLogDAO.createBatch(errors);
    } catch (error) {
      console.error('Failed to batch import errors:', error);
      throw new DaoException('Failed to batch import errors', 'BATCH_IMPORT_FAILED', error);
    }
  }
  
  /**
   * 清理旧数据
   */
  async cleanupOldData(daysToKeep: number = 30): Promise<void> {
    try {
      await this.errorLogDAO.cleanupOldLogs(daysToKeep);
      // 可以添加其他表的清理逻辑
    } catch (error) {
      console.error('Failed to cleanup old data:', error);
      throw new DaoException('Failed to cleanup old data', 'CLEANUP_FAILED', error);
    }
  }
  
  private async updateSessionStatistics(tabId: number, updates: { errorIncrement?: number; requestIncrement?: number; successIncrement?: number }): Promise<void> {
    // 更新用户会话统计信息的逻辑
    // 这里可以实现具体的统计更新逻辑
  }
  
  private async clearErrorCache(tabId: number): Promise<void> {
    // 清除相关的错误缓存
    const keys = [`error_stats_*_${tabId}`, `error_list_*_${tabId}`];
    for (const keyPattern of keys) {
      // 这里可以实现批量清除缓存的逻辑
      await this.cacheManager.delete(keyPattern);
    }
  }
}
```

## 总结

这套 DAO 层架构设计具有以下特点：

1. **模块化设计**: 各层职责清晰，便于维护和扩展
2. **事务支持**: 完整的事务管理机制，保证数据一致性
3. **连接池管理**: 高效的数据库连接管理，支持高并发
4. **查询构建器**: 类型安全的查询构建，减少 SQL 注入风险
5. **缓存机制**: 多层缓存设计，提升性能
6. **错误处理**: 统一的异常处理机制
7. **可扩展性**: 易于添加新的 DAO 和功能

通过这套架构，可以有效地替代前端的 Zustand 状态管理，将数据持久化到后端数据库，同时提供更好的数据管理和查询能力。