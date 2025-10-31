// 数据库连接配置类型
export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  poolSize?: number;
  ssl?: boolean;
}

// 基础实体类型
export interface BaseEntity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

// 网络请求类型
export interface NetworkRequest extends BaseEntity {
  requestId: string;
  url: string;
  method: string;
  tabId: number;
  type: 'xmlhttprequest' | 'main_frame' | 'sub_frame' | 'script' | 'image' | string;
  initiator?: string;
  timestamp: string;
  startTime: number;
  duration?: number;
  success: boolean;
}

// API 请求详细信息
export interface ApiRequestInfo extends BaseEntity {
  projectId: string;
  apiType: 'rest' | 'functions' | 'auth' | 'storage' | 'unknown';
  apiPath: string;
  query: string;
  requestBody?: any;
  headers: Record<string, string>;
}

// API 响应信息
export interface ApiResponseInfo extends BaseEntity {
  statusCode: number;
  statusText?: string;
  responseHeaders: Record<string, string>;
  responseBody?: any;
}

// 错误日志类型
export interface ErrorLog extends BaseEntity {
  type: 'console.error' | 'console.log' | 'image.error' | 'uncaught.error' | 'unhandled.promise' | 'supabase.api.error' | 'supabase.api.non200';
  message: string;
  timestamp: string;
  filename?: string;
  lineno?: number;
  colno?: number;
  stack?: string;
  element?: Record<string, any>;
  error?: {
    message: string;
    name: string;
  };
  errorMessage?: string;
  tabId?: number;
  url?: string;
}

// API 成功日志类型
export interface ApiSuccessLog extends BaseEntity {
  type: 'supabase.api.success';
  timestamp: string;
  request: ApiRequestInfo;
  response: ApiResponseInfo;
  success: boolean;
}

// 用户会话类型
export interface UserSession extends BaseEntity {
  sessionId: string;
  userId?: string;
  tabId: number;
  url: string;
  title?: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  requestCount: number;
  errorCount: number;
  successCount: number;
}

// 统计数据类型
export interface Statistics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  totalErrors: number;
  averageResponseTime: number;
  errorRate: number;
  period: string;
  createdAt: Date;
}

// 分页查询参数
export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// 分页结果
export interface PaginatedResult<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// 查询过滤参数
export interface FilterParams {
  startDate?: Date;
  endDate?: Date;
  errorType?: string;
  apiType?: string;
  statusCode?: number;
  minDuration?: number;
  maxDuration?: number;
  tabId?: number;
  url?: string;
}

// DAO 异常类型
export class DaoException extends Error {
  constructor(
    message: string,
    public code?: string,
    public cause?: Error
  ) {
    super(message);
    this.name = 'DaoException';
  }
}

// 事务管理相关类型
export interface Transaction {
  id: string;
  status: 'pending' | 'committed' | 'rolled_back' | 'failed';
  startTime: Date;
  endTime?: Date;
  operations: TransactionOperation[];
}

export interface TransactionOperation {
  id: string;
  type: 'insert' | 'update' | 'delete' | 'select';
  tableName: string;
  data?: any;
  conditions?: any;
  result?: any;
  timestamp: Date;
}

// 连接池配置
export interface PoolConfig {
  min: number;
  max: number;
  acquireTimeoutMillis: number;
  createTimeoutMillis: number;
  destroyTimeoutMillis: number;
  idleTimeoutMillis: number;
  reapIntervalMillis: number;
  createRetryIntervalMillis: number;
}

// 缓存配置
export interface CacheConfig {
  ttl: number; // Time to live in seconds
  maxSize: number;
  strategy: 'lru' | 'lfu' | 'fifo';
}

// 查询构建器类型
export interface QueryBuilder {
  select(fields?: string[]): QueryBuilder;
  from(table: string): QueryBuilder;
  where(conditions: Record<string, any>): QueryBuilder;
  and(conditions: Record<string, any>): QueryBuilder;
  or(conditions: Record<string, any>): QueryBuilder;
  orderBy(field: string, direction?: 'asc' | 'desc'): QueryBuilder;
  groupBy(fields: string[]): QueryBuilder;
  having(conditions: Record<string, any>): QueryBuilder;
  limit(count: number): QueryBuilder;
  offset(count: number): QueryBuilder;
  toString(): string;
}

// 索引定义
export interface IndexDefinition {
  name: string;
  columns: string[];
  unique?: boolean;
  type?: 'btree' | 'hash' | 'gist' | 'gin';
}

// 数据库迁移记录
export interface Migration extends BaseEntity {
  version: string;
  name: string;
  sql: string;
  appliedAt: Date;
  status: 'pending' | 'completed' | 'failed';
}