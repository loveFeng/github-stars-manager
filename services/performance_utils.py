"""
GitHubStarsManager 性能优化工具集
提供缓存、批处理、异步操作、性能监控等功能
"""

import time
import asyncio
import logging
import statistics
import psutil
import os
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from enum import Enum
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 缓存管理
# ============================================================================

class LRUCache:
    """LRU (Least Recently Used) 缓存实现"""
    
    def __init__(self, capacity: int = 1000):
        """
        初始化 LRU 缓存
        
        Args:
            capacity: 缓存容量
        """
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            self.misses += 1
            return None
        
        # 移动到末尾（标记为最近使用）
        self.cache.move_to_end(key)
        self.hits += 1
        return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """设置缓存值"""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        
        # 超过容量时删除最久未使用的
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def invalidate(self, key: str) -> None:
        """使指定缓存失效"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'capacity': self.capacity,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'usage_percent': len(self.cache) / self.capacity * 100
        }


class TTLCache:
    """带过期时间的缓存"""
    
    def __init__(self, default_ttl: int = 300):
        """
        初始化 TTL 缓存
        
        Args:
            default_ttl: 默认过期时间（秒）
        """
        self.cache: Dict[str, Any] = {}
        self.expire_times: Dict[str, float] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() >= self.expire_times[key]:
            self.invalidate(key)
            return None
        
        return self.cache[key]
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl
        
        self.cache[key] = value
        self.expire_times[key] = time.time() + ttl
    
    def invalidate(self, key: str) -> None:
        """使指定缓存失效"""
        if key in self.cache:
            del self.cache[key]
            del self.expire_times[key]
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
        self.expire_times.clear()
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, expire_time in self.expire_times.items()
            if current_time >= expire_time
        ]
        
        for key in expired_keys:
            self.invalidate(key)
        
        return len(expired_keys)


class CacheManager:
    """多级缓存管理器"""
    
    def __init__(self, lru_capacity: int = 1000, ttl_default: int = 300):
        """
        初始化缓存管理器
        
        Args:
            lru_capacity: LRU 缓存容量
            ttl_default: TTL 缓存默认过期时间
        """
        self.lru_cache = LRUCache(capacity=lru_capacity)
        self.ttl_cache = TTLCache(default_ttl=ttl_default)
    
    def get(self, key: str, use_ttl: bool = False) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            use_ttl: 是否使用 TTL 缓存
        """
        if use_ttl:
            return self.ttl_cache.get(key)
        else:
            return self.lru_cache.get(key)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 表示使用 LRU 缓存
        """
        if ttl is not None:
            self.ttl_cache.put(key, value, ttl)
        else:
            self.lru_cache.put(key, value)
    
    def invalidate(self, pattern: Optional[str] = None) -> None:
        """
        使缓存失效
        
        Args:
            pattern: 匹配模式，None 表示清空所有
        """
        if pattern:
            # 删除匹配的键
            lru_keys = [k for k in list(self.lru_cache.cache.keys()) if pattern in k]
            ttl_keys = [k for k in list(self.ttl_cache.cache.keys()) if pattern in k]
            
            for key in lru_keys:
                self.lru_cache.invalidate(key)
            for key in ttl_keys:
                self.ttl_cache.invalidate(key)
        else:
            self.lru_cache.clear()
            self.ttl_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'lru': self.lru_cache.get_stats(),
            'ttl': {
                'size': len(self.ttl_cache.cache),
                'default_ttl': self.ttl_cache.default_ttl
            }
        }


def cached(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    缓存装饰器
    
    Args:
        ttl: 过期时间（秒），None 表示使用 LRU 缓存
        key_func: 自定义键生成函数
    
    Example:
        @cached(ttl=300)
        def search_repositories(query: str, language: str = None):
            return db.query("SELECT * FROM repositories WHERE ...")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数作为键
                key_parts = [func.__name__]
                if args:
                    key_parts.append(str(args))
                if kwargs:
                    key_parts.append(str(sorted(kwargs.items())))
                cache_key = ':'.join(key_parts)
            
            # 检查缓存
            cached_value = cache_manager.get(cache_key, use_ttl=(ttl is not None))
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存储缓存
            cache_manager.put(cache_key, result, ttl=ttl)
            logger.debug(f"缓存存储: {cache_key}")
            
            return result
        return wrapper
    return decorator


# 全局缓存管理器实例
cache_manager = CacheManager(lru_capacity=1000, ttl_default=300)


# ============================================================================
# 2. 批量处理
# ============================================================================

class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, batch_size: int = 1000, max_workers: int = 4):
        """
        初始化批量处理器
        
        Args:
            batch_size: 批次大小
            max_workers: 最大工作线程数
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
    
    def process(self, items: List[Any], process_func: Callable, use_threads: bool = True) -> List[Any]:
        """
        批量处理数据
        
        Args:
            items: 待处理的数据列表
            process_func: 处理函数
            use_threads: 是否使用线程池
        
        Returns:
            处理结果列表
        """
        if not items:
            return []
        
        # 分批
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        logger.info(f"批量处理: {len(items)} 项, {len(batches)} 批次")
        
        results = []
        
        if use_threads:
            # 使用线程池并行处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(process_func, batch) for batch in batches]
                for future in as_completed(futures):
                    try:
                        batch_result = future.result()
                        if batch_result:
                            results.extend(batch_result)
                    except Exception as e:
                        logger.error(f"批处理失败: {e}")
        else:
            # 串行处理
            for batch in batches:
                try:
                    batch_result = process_func(batch)
                    if batch_result:
                        results.extend(batch_result)
                except Exception as e:
                    logger.error(f"批处理失败: {e}")
        
        return results


class DatabaseBatchOperations:
    """数据库批量操作"""
    
    def __init__(self, db_connection):
        """
        初始化数据库批量操作
        
        Args:
            db_connection: 数据库连接
        """
        self.db = db_connection
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            self.db.execute("BEGIN TRANSACTION")
            yield
            self.db.execute("COMMIT")
        except Exception as e:
            self.db.execute("ROLLBACK")
            logger.error(f"事务回滚: {e}")
            raise
    
    def batch_insert(self, table: str, columns: List[str], data: List[Tuple], batch_size: int = 500) -> int:
        """
        批量插入数据
        
        Args:
            table: 表名
            columns: 列名列表
            data: 数据列表
            batch_size: 批次大小
        
        Returns:
            插入的行数
        """
        if not data:
            return 0
        
        placeholders = ','.join(['?'] * len(columns))
        sql = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        
        inserted_count = 0
        
        with self.transaction():
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                cursor = self.db.executemany(sql, batch)
                inserted_count += cursor.rowcount
        
        logger.info(f"批量插入: {table} 表, {inserted_count} 行")
        return inserted_count
    
    def batch_update(self, table: str, updates: List[Dict[str, Any]], id_column: str = 'id') -> int:
        """
        批量更新数据
        
        Args:
            table: 表名
            updates: 更新数据列表，每项包含 id 和要更新的字段
            id_column: ID 列名
        
        Returns:
            更新的行数
        """
        if not updates:
            return 0
        
        # 获取所有需要更新的字段（除了 ID）
        fields = set()
        for update in updates:
            fields.update(k for k in update.keys() if k != id_column)
        
        if not fields:
            return 0
        
        # 构建 CASE WHEN 语句
        cases = {field: [] for field in fields}
        ids = []
        
        for update in updates:
            id_value = update[id_column]
            ids.append(id_value)
            
            for field in fields:
                if field in update:
                    value = update[field]
                    if isinstance(value, str):
                        value = f"'{value}'"
                    cases[field].append(f"WHEN {id_value} THEN {value}")
        
        # 构建 SQL
        set_clauses = []
        for field, case_list in cases.items():
            if case_list:
                case_sql = f"CASE {id_column} {' '.join(case_list)} ELSE {field} END"
                set_clauses.append(f"{field} = {case_sql}")
        
        if not set_clauses:
            return 0
        
        sql = f"""
        UPDATE {table}
        SET {', '.join(set_clauses)},
            updated_at = CURRENT_TIMESTAMP
        WHERE {id_column} IN ({','.join(['?'] * len(ids))})
        """
        
        with self.transaction():
            cursor = self.db.execute(sql, ids)
            updated_count = cursor.rowcount
        
        logger.info(f"批量更新: {table} 表, {updated_count} 行")
        return updated_count
    
    def batch_delete(self, table: str, ids: List[Any], id_column: str = 'id', batch_size: int = 500) -> int:
        """
        批量删除数据
        
        Args:
            table: 表名
            ids: ID 列表
            id_column: ID 列名
            batch_size: 批次大小
        
        Returns:
            删除的行数
        """
        if not ids:
            return 0
        
        deleted_count = 0
        
        with self.transaction():
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                placeholders = ','.join(['?'] * len(batch_ids))
                sql = f"DELETE FROM {table} WHERE {id_column} IN ({placeholders})"
                cursor = self.db.execute(sql, batch_ids)
                deleted_count += cursor.rowcount
        
        logger.info(f"批量删除: {table} 表, {deleted_count} 行")
        return deleted_count


# ============================================================================
# 3. 性能监控
# ============================================================================

@dataclass
class PerformanceMetric:
    """性能指标"""
    operation: str
    duration_ms: float
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_metrics: int = 10000):
        """
        初始化性能监控器
        
        Args:
            max_metrics: 最多保存的指标数量
        """
        self.metrics: List[PerformanceMetric] = []
        self.max_metrics = max_metrics
    
    def record(self, operation: str, duration_ms: float, success: bool = True, 
               error: Optional[str] = None, **metadata) -> None:
        """
        记录性能指标
        
        Args:
            operation: 操作名称
            duration_ms: 耗时（毫秒）
            success: 是否成功
            error: 错误信息
            **metadata: 额外元数据
        """
        metric = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
            success=success,
            error_message=error,
            metadata=metadata
        )
        
        self.metrics.append(metric)
        
        # 限制记录数量
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
        
        # 记录慢操作
        if duration_ms > 500:
            logger.warning(f"慢操作检测: {operation} 耗时 {duration_ms:.2f}ms")
    
    def get_stats(self, operation: Optional[str] = None, 
                  time_window: Optional[int] = None) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            operation: 操作名称过滤
            time_window: 时间窗口（秒）
        
        Returns:
            统计信息字典
        """
        metrics = self.metrics
        
        # 过滤操作名称
        if operation:
            metrics = [m for m in metrics if m.operation == operation]
        
        # 过滤时间窗口
        if time_window:
            cutoff_time = time.time() - time_window
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)
        
        return {
            'operation': operation or 'all',
            'count': len(metrics),
            'success_count': success_count,
            'fail_count': len(metrics) - success_count,
            'success_rate': success_count / len(metrics) * 100,
            'avg_duration_ms': statistics.mean(durations),
            'median_duration_ms': statistics.median(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'total_duration_ms': sum(durations),
        }
    
    def get_percentiles(self, operation: Optional[str] = None) -> Dict[str, float]:
        """
        获取百分位统计
        
        Args:
            operation: 操作名称过滤
        
        Returns:
            百分位字典
        """
        metrics = self.metrics
        if operation:
            metrics = [m for m in metrics if m.operation == operation]
        
        if not metrics:
            return {}
        
        durations = sorted([m.duration_ms for m in metrics])
        
        def percentile(data, p):
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] + c * (data[f + 1] - data[f])
            else:
                return data[f]
        
        return {
            'p50': percentile(durations, 0.50),
            'p75': percentile(durations, 0.75),
            'p90': percentile(durations, 0.90),
            'p95': percentile(durations, 0.95),
            'p99': percentile(durations, 0.99),
        }
    
    def get_slow_operations(self, threshold_ms: float = 500) -> List[PerformanceMetric]:
        """
        获取慢操作列表
        
        Args:
            threshold_ms: 慢操作阈值（毫秒）
        
        Returns:
            慢操作列表
        """
        return [m for m in self.metrics if m.duration_ms > threshold_ms]
    
    def export_metrics(self, filepath: str) -> None:
        """
        导出性能指标到文件
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'w') as f:
            for metric in self.metrics:
                f.write(json.dumps(asdict(metric)) + '\n')
        
        logger.info(f"性能指标已导出到: {filepath}")


def monitor_performance(operation_name: str, threshold_ms: float = 500):
    """
    性能监控装饰器
    
    Args:
        operation_name: 操作名称
        threshold_ms: 慢操作阈值
    
    Example:
        @monitor_performance('search_repositories', threshold_ms=300)
        def search_repositories(query: str):
            return db.query("SELECT * FROM repositories WHERE ...")
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                    function=func.__name__
                )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                    function=func.__name__
                )
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全局性能监控器实例
performance_monitor = PerformanceMonitor(max_metrics=10000)


# ============================================================================
# 4. 内存管理
# ============================================================================

class MemoryMonitor:
    """内存使用监控"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """
        获取当前进程内存使用
        
        Returns:
            内存使用字典（MB）
        """
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # 物理内存
            'vms_mb': mem_info.vms / 1024 / 1024,  # 虚拟内存
            'percent': process.memory_percent(),
        }
    
    @staticmethod
    def check_memory_threshold(threshold_mb: float = 500) -> bool:
        """
        检查内存是否超过阈值
        
        Args:
            threshold_mb: 阈值（MB）
        
        Returns:
            是否超过阈值
        """
        usage = MemoryMonitor.get_memory_usage()
        if usage['rss_mb'] > threshold_mb:
            logger.warning(f"内存使用过高: {usage['rss_mb']:.2f}MB (阈值: {threshold_mb}MB)")
            return True
        return False
    
    @staticmethod
    def log_memory_usage(label: str = "") -> None:
        """
        记录内存使用情况
        
        Args:
            label: 标签
        """
        usage = MemoryMonitor.get_memory_usage()
        logger.info(f"内存使用 {label}: RSS={usage['rss_mb']:.2f}MB, VMS={usage['vms_mb']:.2f}MB, {usage['percent']:.1f}%")


class StreamingQueryIterator:
    """流式查询迭代器，避免一次性加载所有数据到内存"""
    
    def __init__(self, cursor, batch_size: int = 1000):
        """
        初始化流式查询迭代器
        
        Args:
            cursor: 数据库游标
            batch_size: 批次大小
        """
        self.cursor = cursor
        self.batch_size = batch_size
    
    def __iter__(self):
        """迭代器接口"""
        while True:
            rows = self.cursor.fetchmany(self.batch_size)
            if not rows:
                break
            for row in rows:
                yield row


def fetch_in_batches(cursor, batch_size: int = 1000):
    """
    批量获取查询结果的生成器
    
    Args:
        cursor: 数据库游标
        batch_size: 批次大小
    
    Yields:
        查询结果行
    
    Example:
        cursor = db.execute("SELECT * FROM repositories")
        for row in fetch_in_batches(cursor, batch_size=500):
            process_row(row)
    """
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for row in rows:
            yield row


# ============================================================================
# 5. 数据库优化
# ============================================================================

class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self, db_connection):
        """
        初始化数据库优化器
        
        Args:
            db_connection: 数据库连接
        """
        self.db = db_connection
    
    def apply_performance_pragmas(self) -> None:
        """应用性能优化 PRAGMA 配置"""
        pragmas = {
            'journal_mode': 'WAL',           # 使用 WAL 模式
            'synchronous': 'NORMAL',          # 平衡性能和安全
            'cache_size': -64000,             # 64MB 缓存
            'temp_store': 'MEMORY',           # 临时表使用内存
            'mmap_size': 268435456,           # 256MB 内存映射
            'page_size': 4096,                # 4KB 页面大小
        }
        
        for pragma, value in pragmas.items():
            self.db.execute(f"PRAGMA {pragma} = {value}")
            logger.info(f"应用 PRAGMA: {pragma} = {value}")
    
    def analyze_table(self, table_name: str) -> None:
        """
        分析表统计信息
        
        Args:
            table_name: 表名
        """
        self.db.execute(f"ANALYZE {table_name}")
        logger.info(f"已分析表: {table_name}")
    
    def vacuum_database(self, full: bool = False) -> None:
        """
        清理数据库碎片
        
        Args:
            full: 是否执行完整 VACUUM
        """
        if full:
            self.db.execute("VACUUM")
            logger.info("已执行完整 VACUUM")
        else:
            self.db.execute("PRAGMA incremental_vacuum")
            logger.info("已执行增量 VACUUM")
    
    def get_index_list(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取索引列表
        
        Args:
            table_name: 表名，None 表示所有表
        
        Returns:
            索引信息列表
        """
        sql = """
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
        """
        
        if table_name:
            sql += f" AND tbl_name = '{table_name}'"
        
        cursor = self.db.execute(sql)
        return [{'name': row[0], 'table': row[1], 'sql': row[2]} for row in cursor.fetchall()]
    
    def analyze_query_plan(self, sql: str, params: Optional[List] = None) -> List[str]:
        """
        分析查询计划
        
        Args:
            sql: SQL 查询
            params: 查询参数
        
        Returns:
            查询计划列表
        """
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        cursor = self.db.execute(explain_sql, params or [])
        
        plan = []
        for row in cursor.fetchall():
            plan.append(' '.join(str(x) for x in row))
        
        # 检查性能问题
        plan_text = ' '.join(plan)
        warnings = []
        
        if 'SCAN' in plan_text and 'USING INDEX' not in plan_text:
            warnings.append("⚠️ 查询未使用索引，可能导致全表扫描")
        
        if 'TEMP B-TREE' in plan_text:
            warnings.append("⚠️ 使用临时 B-TREE，考虑添加索引优化")
        
        if warnings:
            logger.warning(f"查询计划警告: {', '.join(warnings)}")
        
        return plan
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """
        获取表大小信息
        
        Args:
            table_name: 表名
        
        Returns:
            表大小信息
        """
        # 获取行数
        cursor = self.db.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # 获取页数和页大小
        cursor = self.db.execute(f"PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        
        cursor = self.db.execute(f"PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        
        total_size_mb = (page_count * page_size) / 1024 / 1024
        
        return {
            'table': table_name,
            'row_count': row_count,
            'page_count': page_count,
            'page_size': page_size,
            'total_size_mb': total_size_mb
        }


# ============================================================================
# 6. 异步支持
# ============================================================================

class AsyncBatchProcessor:
    """异步批量处理器"""
    
    def __init__(self, batch_size: int = 1000, max_concurrent: int = 10):
        """
        初始化异步批量处理器
        
        Args:
            batch_size: 批次大小
            max_concurrent: 最大并发数
        """
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process(self, items: List[Any], process_func: Callable) -> List[Any]:
        """
        异步批量处理数据
        
        Args:
            items: 待处理的数据列表
            process_func: 异步处理函数
        
        Returns:
            处理结果列表
        """
        if not items:
            return []
        
        # 分批
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        logger.info(f"异步批量处理: {len(items)} 项, {len(batches)} 批次")
        
        async def process_batch(batch):
            async with self.semaphore:
                return await process_func(batch)
        
        # 并发处理所有批次
        results = await asyncio.gather(*[process_batch(batch) for batch in batches])
        
        # 合并结果
        all_results = []
        for result in results:
            if result:
                all_results.extend(result)
        
        return all_results


# ============================================================================
# 7. 性能工具函数
# ============================================================================

def generate_cache_key(*args, **kwargs) -> str:
    """
    生成缓存键
    
    Args:
        *args: 位置参数
        **kwargs: 关键字参数
    
    Returns:
        缓存键
    """
    key_parts = []
    
    if args:
        key_parts.append(str(args))
    
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(str(sorted_kwargs))
    
    key_string = ':'.join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def timeit(func: Callable) -> Callable:
    """
    简单的计时装饰器
    
    Example:
        @timeit
        def my_function():
            # do something
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        logger.info(f"{func.__name__} 耗时: {duration:.2f}ms")
        return result
    
    return wrapper


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    失败重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
    
    Example:
        @retry_on_failure(max_attempts=3, delay=1.0)
        def unstable_function():
            # may fail
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts}): {e}")
                    
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            # 所有尝试都失败
            logger.error(f"{func.__name__} 在 {max_attempts} 次尝试后仍然失败")
            raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# 8. 使用示例
# ============================================================================

def example_usage():
    """性能优化工具使用示例"""
    
    # 1. 缓存使用示例
    @cached(ttl=300)
    def search_repositories(query: str):
        # 模拟数据库查询
        return {"results": []}
    
    # 2. 性能监控示例
    @monitor_performance('search_repositories')
    def monitored_search(query: str):
        time.sleep(0.1)  # 模拟耗时操作
        return {"results": []}
    
    # 3. 批量处理示例
    def process_batch(items):
        return [item * 2 for item in items]
    
    processor = BatchProcessor(batch_size=100)
    results = processor.process(list(range(1000)), process_batch)
    
    # 4. 内存监控示例
    MemoryMonitor.log_memory_usage("开始处理")
    # ... 处理逻辑
    MemoryMonitor.log_memory_usage("处理完成")
    
    # 5. 获取性能统计
    stats = performance_monitor.get_stats('search_repositories')
    print(f"性能统计: {stats}")
    
    # 6. 获取缓存统计
    cache_stats = cache_manager.get_stats()
    print(f"缓存统计: {cache_stats}")


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行示例
    example_usage()
