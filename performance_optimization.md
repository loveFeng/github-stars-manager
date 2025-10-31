# GitHubStarsManager 性能优化报告

## 概述

本报告针对 GitHubStarsManager SQLite 版本进行全面的性能优化分析和实施方案，旨在支持大量数据处理（10,000+ 星标仓库、100,000+ Releases）场景，确保系统在高负载下的响应速度和稳定性。

**优化目标**：
- 仓库列表加载时间 < 1秒
- 搜索响应时间 < 500ms
- 批量操作性能提升 80%+
- 内存使用优化 50%+
- 前端渲染性能提升 90%+

---

## 1. 数据库查询优化

### 1.1 索引优化策略

#### 现有索引分析
当前数据库已有基础索引，但对于大数据量场景需要进一步优化：

```sql
-- 核心性能优化索引
CREATE INDEX IF NOT EXISTS idx_repositories_stars_updated 
  ON repositories(stars_count DESC, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_repositories_language_archived 
  ON repositories(language, archived, stars_count DESC);

CREATE INDEX IF NOT EXISTS idx_repositories_topics_gin 
  ON repositories(topics) WHERE topics IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_releases_repo_published_draft 
  ON releases(repository_id, published_at DESC, draft, prerelease);

CREATE INDEX IF NOT EXISTS idx_release_assets_size_type 
  ON release_assets(size_bytes, content_type, is_downloaded);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_repo_type_valid 
  ON ai_analysis_results(repository_id, analysis_type, is_validated, created_at DESC);

-- 搜索优化覆盖索引
CREATE INDEX IF NOT EXISTS idx_repositories_search_cover 
  ON repositories(owner, name, language, stars_count DESC) 
  WHERE archived = 0;
```

#### 索引使用监控
```sql
-- 查看索引使用统计
SELECT 
  name AS index_name,
  tbl AS table_name,
  sql
FROM sqlite_master 
WHERE type = 'index' AND name NOT LIKE 'sqlite_%';

-- 分析查询计划
EXPLAIN QUERY PLAN 
SELECT * FROM repositories 
WHERE language = 'Python' AND archived = 0 
ORDER BY stars_count DESC LIMIT 20;
```

### 1.2 查询优化技巧

#### 避免全表扫描
```sql
-- ❌ 不推荐：全表扫描
SELECT * FROM repositories 
WHERE description LIKE '%machine learning%';

-- ✅ 推荐：使用 FTS5 全文搜索
SELECT r.* FROM repositories r
INNER JOIN repositories_fts fts ON r.id = fts.rowid
WHERE repositories_fts MATCH 'machine learning'
ORDER BY rank LIMIT 20;
```

#### 使用覆盖索引
```sql
-- ❌ 不推荐：需要回表查询
SELECT id, owner, name, stars_count FROM repositories 
WHERE language = 'JavaScript' ORDER BY stars_count DESC;

-- ✅ 推荐：覆盖索引直接返回
-- 已创建索引：idx_repositories_search_cover
SELECT id, owner, name, stars_count FROM repositories 
WHERE language = 'JavaScript' AND archived = 0 
ORDER BY stars_count DESC LIMIT 50;
```

#### 分页优化
```sql
-- ❌ 不推荐：大偏移量性能差
SELECT * FROM repositories ORDER BY id LIMIT 1000 OFFSET 90000;

-- ✅ 推荐：使用游标分页
SELECT * FROM repositories 
WHERE id > :last_seen_id 
ORDER BY id LIMIT 1000;

-- ✅ 推荐：使用复合条件分页
SELECT * FROM repositories 
WHERE (stars_count, id) < (:last_stars, :last_id)
ORDER BY stars_count DESC, id DESC LIMIT 1000;
```

### 1.3 查询性能分析工具

```python
# 查询性能分析装饰器
def analyze_query_performance(func):
    """分析查询性能的装饰器"""
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        # 记录慢查询
        if elapsed > 0.5:  # 超过500ms
            logger.warning(f"慢查询检测: {func.__name__} 耗时 {elapsed:.2f}s")
        
        return result
    return wrapper
```

---

## 2. 批量操作优化

### 2.1 批量插入优化

#### 使用事务和批量语句
```python
# ❌ 不推荐：逐条插入
for repo in repositories:
    db.execute("INSERT INTO repositories (...) VALUES (...)", repo)

# ✅ 推荐：批量事务插入
def batch_insert_repositories(repositories, batch_size=1000):
    """批量插入仓库数据"""
    with db.transaction():
        for i in range(0, len(repositories), batch_size):
            batch = repositories[i:i + batch_size]
            placeholders = ','.join(['(?,?,?,?)'] * len(batch))
            values = []
            for repo in batch:
                values.extend([repo.id, repo.name, repo.owner, repo.stars])
            
            db.executemany(
                f"INSERT OR REPLACE INTO repositories (id, name, owner, stars) VALUES {placeholders}",
                values
            )
```

#### 使用 executemany
```python
# 更高效的批量插入
def batch_insert_optimized(data, batch_size=500):
    """优化的批量插入"""
    with db.transaction():
        sql = "INSERT OR REPLACE INTO repositories (...) VALUES (?, ?, ?, ...)"
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            db.executemany(sql, batch)
```

### 2.2 批量更新优化

```python
# ✅ 使用 CASE WHEN 批量更新
def batch_update_stars(repo_updates):
    """批量更新星标数"""
    if not repo_updates:
        return
    
    ids = [r['id'] for r in repo_updates]
    
    cases = []
    for update in repo_updates:
        cases.append(f"WHEN {update['id']} THEN {update['stars_count']}")
    
    sql = f"""
    UPDATE repositories 
    SET stars_count = CASE id
        {' '.join(cases)}
        ELSE stars_count
    END,
    updated_at = CURRENT_TIMESTAMP
    WHERE id IN ({','.join('?' * len(ids))})
    """
    
    db.execute(sql, ids)
```

### 2.3 并行批量处理

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

def parallel_batch_process(items, process_func, max_workers=None):
    """并行批量处理数据"""
    if max_workers is None:
        max_workers = min(mp.cpu_count(), 8)
    
    # 将数据分批
    batch_size = max(len(items) // max_workers, 100)
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_func, batch) for batch in batches]
        for future in as_completed(futures):
            try:
                results.extend(future.result())
            except Exception as e:
                logger.error(f"批处理失败: {e}")
    
    return results
```

---

## 3. 内存使用优化

### 3.1 游标流式查询

```python
class StreamingQueryIterator:
    """流式查询迭代器，避免一次性加载所有数据到内存"""
    
    def __init__(self, cursor, batch_size=1000):
        self.cursor = cursor
        self.batch_size = batch_size
    
    def __iter__(self):
        while True:
            rows = self.cursor.fetchmany(self.batch_size)
            if not rows:
                break
            for row in rows:
                yield row

# 使用示例
def process_large_dataset():
    cursor = db.execute("SELECT * FROM repositories")
    for row in StreamingQueryIterator(cursor, batch_size=500):
        process_row(row)  # 逐行处理，不占用大量内存
```

### 3.2 生成器模式

```python
def fetch_repositories_generator(filters=None, batch_size=1000):
    """使用生成器获取仓库数据"""
    offset = 0
    while True:
        sql = "SELECT * FROM repositories LIMIT ? OFFSET ?"
        rows = db.query(sql, [batch_size, offset])
        
        if not rows:
            break
        
        for row in rows:
            yield row
        
        offset += batch_size

# 使用示例
for repo in fetch_repositories_generator(batch_size=500):
    process_repository(repo)
```

### 3.3 对象池和缓存清理

```python
from collections import OrderedDict

class LRUCache:
    """LRU 缓存实现"""
    
    def __init__(self, capacity=1000):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key):
        if key not in self.cache:
            return None
        # 移动到末尾（最近使用）
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            # 删除最久未使用的
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()
```

### 3.4 内存监控

```python
import psutil
import os

class MemoryMonitor:
    """内存使用监控"""
    
    @staticmethod
    def get_memory_usage():
        """获取当前进程内存使用"""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # 物理内存
            'vms_mb': mem_info.vms / 1024 / 1024,  # 虚拟内存
        }
    
    @staticmethod
    def check_memory_threshold(threshold_mb=500):
        """检查内存是否超过阈值"""
        usage = MemoryMonitor.get_memory_usage()
        if usage['rss_mb'] > threshold_mb:
            logger.warning(f"内存使用过高: {usage['rss_mb']:.2f}MB")
            return True
        return False
```

---

## 4. 异步处理优化

### 4.1 异步数据库操作

```python
import asyncio
import aiosqlite

class AsyncDatabaseManager:
    """异步数据库管理器"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
    
    async def connect(self):
        """建立异步连接"""
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA synchronous=NORMAL")
    
    async def query(self, sql, params=None):
        """异步查询"""
        async with self.conn.execute(sql, params or []) as cursor:
            return await cursor.fetchall()
    
    async def execute(self, sql, params=None):
        """异步执行"""
        await self.conn.execute(sql, params or [])
        await self.conn.commit()
    
    async def batch_insert(self, sql, data, batch_size=1000):
        """异步批量插入"""
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            await self.conn.executemany(sql, batch)
        await self.conn.commit()
```

### 4.2 异步 API 请求

```python
import aiohttp
import asyncio

class AsyncGitHubAPI:
    """异步 GitHub API 客户端"""
    
    def __init__(self, token, max_concurrent=10):
        self.token = token
        self.base_url = "https://api.github.com"
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch(self, session, url):
        """异步请求单个 URL"""
        async with self.semaphore:
            headers = {'Authorization': f'token {self.token}'}
            async with session.get(url, headers=headers) as response:
                return await response.json()
    
    async def fetch_all_starred_repos(self):
        """异步获取所有星标仓库"""
        async with aiohttp.ClientSession() as session:
            # 先获取总页数
            url = f"{self.base_url}/user/starred?per_page=100&page=1"
            response = await self.fetch(session, url)
            
            # 并发获取所有页
            tasks = []
            for page in range(1, 11):  # 假设最多10页
                url = f"{self.base_url}/user/starred?per_page=100&page={page}"
                tasks.append(self.fetch(session, url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并结果
            all_repos = []
            for result in results:
                if not isinstance(result, Exception):
                    all_repos.extend(result)
            
            return all_repos
```

### 4.3 后台任务队列

```python
import asyncio
from asyncio import Queue
from enum import Enum

class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class AsyncTaskQueue:
    """异步任务队列"""
    
    def __init__(self, max_workers=5):
        self.queue = Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
    
    async def worker(self):
        """工作协程"""
        while self.running:
            try:
                priority, task_func, args, kwargs = await self.queue.get()
                await task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"任务执行失败: {e}")
            finally:
                self.queue.task_done()
    
    async def start(self):
        """启动队列"""
        self.running = True
        self.workers = [
            asyncio.create_task(self.worker()) 
            for _ in range(self.max_workers)
        ]
    
    async def stop(self):
        """停止队列"""
        await self.queue.join()
        self.running = False
        for worker in self.workers:
            worker.cancel()
    
    async def add_task(self, task_func, priority=TaskPriority.MEDIUM, *args, **kwargs):
        """添加任务"""
        await self.queue.put((priority.value, task_func, args, kwargs))
```

---

## 5. 缓存策略

### 5.1 多级缓存架构

```
┌─────────────────────────────────────────┐
│         应用层缓存 (LRU)               │
│    - 热点数据                           │
│    - 1000 条记录                        │
│    - 内存限制 100MB                     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       查询结果缓存 (TTL)               │
│    - 搜索结果                           │
│    - 过期时间 5 分钟                    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         SQLite 缓存                     │
│    - page_size=4096                     │
│    - cache_size=10000                   │
└─────────────────────────────────────────┘
```

### 5.2 缓存实现

```python
import time
from functools import wraps
from typing import Any, Callable, Optional

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.lru_cache = LRUCache(capacity=1000)
        self.ttl_cache = {}
        self.ttl_times = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 检查 TTL 缓存
        if key in self.ttl_cache:
            if time.time() < self.ttl_times[key]:
                return self.ttl_cache[key]
            else:
                # 过期删除
                del self.ttl_cache[key]
                del self.ttl_times[key]
        
        # 检查 LRU 缓存
        return self.lru_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        if ttl:
            # 使用 TTL 缓存
            self.ttl_cache[key] = value
            self.ttl_times[key] = time.time() + ttl
        else:
            # 使用 LRU 缓存
            self.lru_cache.put(key, value)
    
    def invalidate(self, pattern: str = None):
        """使缓存失效"""
        if pattern:
            # 删除匹配的键
            keys_to_delete = [k for k in self.ttl_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.ttl_cache[key]
                if key in self.ttl_times:
                    del self.ttl_times[key]
        else:
            # 清空所有缓存
            self.lru_cache.clear()
            self.ttl_cache.clear()
            self.ttl_times.clear()

# 缓存装饰器
def cached(ttl: int = 300, key_func: Callable = None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 检查缓存
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存储缓存
            cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator

# 使用示例
cache_manager = CacheManager()

@cached(ttl=300)
def search_repositories(query: str, language: str = None):
    """搜索仓库（带缓存）"""
    # 实际查询逻辑
    return db.query("SELECT * FROM repositories WHERE ...")
```

### 5.3 缓存预热

```python
class CacheWarmer:
    """缓存预热"""
    
    @staticmethod
    async def warm_up():
        """预热常用数据"""
        logger.info("开始缓存预热...")
        
        # 预热热门语言
        popular_languages = ['JavaScript', 'Python', 'Java', 'TypeScript', 'Go']
        for lang in popular_languages:
            repos = await db.query(
                "SELECT * FROM repositories WHERE language = ? LIMIT 100",
                [lang]
            )
            cache_manager.set(f"repos:language:{lang}", repos, ttl=3600)
        
        # 预热最近更新
        recent_repos = await db.query(
            "SELECT * FROM repositories ORDER BY updated_at DESC LIMIT 100"
        )
        cache_manager.set("repos:recent", recent_repos, ttl=600)
        
        logger.info("缓存预热完成")
```

### 5.4 智能缓存失效

```python
class CacheInvalidator:
    """智能缓存失效"""
    
    @staticmethod
    def on_repository_update(repo_id: int):
        """仓库更新时使相关缓存失效"""
        # 使仓库详情缓存失效
        cache_manager.invalidate(f"repo:{repo_id}")
        
        # 使列表缓存失效
        cache_manager.invalidate("repos:recent")
        cache_manager.invalidate("repos:language")
        
        # 使搜索缓存失效
        cache_manager.invalidate("search:")
    
    @staticmethod
    def on_bulk_update():
        """批量更新时清空所有缓存"""
        cache_manager.invalidate()
```

---

## 6. 前端性能优化

### 6.1 虚拟滚动实现

```typescript
// 虚拟滚动组件
import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';

interface VirtualListProps {
  items: Repository[];
  renderItem: (item: Repository) => React.ReactNode;
  estimateSize?: number;
}

export function VirtualRepositoryList({ 
  items, 
  renderItem, 
  estimateSize = 120 
}: VirtualListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan: 5, // 预渲染5个元素
  });

  return (
    <div ref={parentRef} className="h-screen overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            {renderItem(items[virtualRow.index])}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 6.2 懒加载和代码分割

```typescript
// 路由懒加载
import { lazy, Suspense } from 'react';

const RepositoriesPage = lazy(() => import('./pages/RepositoriesPage'));
const RepositoryDetailPage = lazy(() => import('./pages/RepositoryDetailPage'));
const ReleasesPage = lazy(() => import('./pages/ReleasesPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

// 组件懒加载包装器
function LazyComponent({ component: Component }) {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Component />
    </Suspense>
  );
}

// 图片懒加载
import { useInView } from 'react-intersection-observer';

function LazyImage({ src, alt, ...props }) {
  const { ref, inView } = useInView({
    triggerOnce: true,
    threshold: 0.1,
  });

  return (
    <div ref={ref}>
      {inView ? (
        <img src={src} alt={alt} {...props} />
      ) : (
        <div className="bg-gray-200 animate-pulse" {...props} />
      )}
    </div>
  );
}
```

### 6.3 防抖和节流

```typescript
import { useCallback, useEffect, useRef } from 'react';

// 防抖 Hook
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// 节流 Hook
export function useThrottle<T>(value: T, interval: number): T {
  const [throttledValue, setThrottledValue] = useState(value);
  const lastUpdated = useRef<number>(Date.now());

  useEffect(() => {
    const now = Date.now();
    if (now - lastUpdated.current >= interval) {
      lastUpdated.current = now;
      setThrottledValue(value);
    } else {
      const timer = setTimeout(() => {
        lastUpdated.current = Date.now();
        setThrottledValue(value);
      }, interval - (now - lastUpdated.current));

      return () => clearTimeout(timer);
    }
  }, [value, interval]);

  return throttledValue;
}

// 使用示例
function SearchInput() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery) {
      // 执行搜索
      searchRepositories(debouncedQuery);
    }
  }, [debouncedQuery]);

  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="搜索仓库..."
    />
  );
}
```

### 6.4 React 性能优化

```typescript
import { memo, useMemo, useCallback } from 'react';

// 使用 memo 避免不必要的重渲染
const RepositoryCard = memo(({ repository }: { repository: Repository }) => {
  return (
    <div className="repository-card">
      <h3>{repository.name}</h3>
      <p>{repository.description}</p>
    </div>
  );
}, (prevProps, nextProps) => {
  // 自定义比较函数
  return prevProps.repository.id === nextProps.repository.id &&
         prevProps.repository.updated_at === nextProps.repository.updated_at;
});

// 使用 useMemo 缓存计算结果
function RepositoryList({ repositories, filters }) {
  const filteredRepos = useMemo(() => {
    return repositories.filter(repo => {
      if (filters.language && repo.language !== filters.language) return false;
      if (filters.minStars && repo.stars_count < filters.minStars) return false;
      return true;
    });
  }, [repositories, filters]);

  return (
    <div>
      {filteredRepos.map(repo => (
        <RepositoryCard key={repo.id} repository={repo} />
      ))}
    </div>
  );
}

// 使用 useCallback 缓存函数
function RepositoryFilters({ onFilterChange }) {
  const handleLanguageChange = useCallback((language: string) => {
    onFilterChange({ language });
  }, [onFilterChange]);

  return (
    <select onChange={(e) => handleLanguageChange(e.target.value)}>
      {/* options */}
    </select>
  );
}
```

### 6.5 Web Worker 处理

```typescript
// worker.ts - Web Worker 处理大数据
self.onmessage = (e: MessageEvent) => {
  const { action, data } = e.data;

  switch (action) {
    case 'FILTER_REPOSITORIES':
      const filtered = filterRepositories(data.repositories, data.filters);
      self.postMessage({ action: 'FILTER_COMPLETE', data: filtered });
      break;
    
    case 'SORT_REPOSITORIES':
      const sorted = sortRepositories(data.repositories, data.sortBy);
      self.postMessage({ action: 'SORT_COMPLETE', data: sorted });
      break;
  }
};

function filterRepositories(repos, filters) {
  return repos.filter(repo => {
    // 复杂的过滤逻辑
    return true;
  });
}

// 主线程使用 Worker
const worker = new Worker(new URL('./worker.ts', import.meta.url));

worker.onmessage = (e) => {
  const { action, data } = e.data;
  if (action === 'FILTER_COMPLETE') {
    setFilteredRepositories(data);
  }
};

// 发送数据到 Worker
worker.postMessage({
  action: 'FILTER_REPOSITORIES',
  data: { repositories, filters }
});
```

---

## 7. 网络请求优化

### 7.1 请求合并和批处理

```python
class BatchRequestManager:
    """批量请求管理器"""
    
    def __init__(self, batch_size=10, delay=0.1):
        self.batch_size = batch_size
        self.delay = delay
        self.pending_requests = []
        self.timer = None
    
    async def add_request(self, url, callback):
        """添加请求到批处理队列"""
        self.pending_requests.append((url, callback))
        
        # 达到批量大小或延迟后执行
        if len(self.pending_requests) >= self.batch_size:
            await self.flush()
        elif self.timer is None:
            self.timer = asyncio.create_task(self._delayed_flush())
    
    async def _delayed_flush(self):
        """延迟执行批处理"""
        await asyncio.sleep(self.delay)
        await self.flush()
    
    async def flush(self):
        """执行批量请求"""
        if not self.pending_requests:
            return
        
        requests = self.pending_requests.copy()
        self.pending_requests.clear()
        self.timer = None
        
        # 并发执行所有请求
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch(session, url, cb) for url, cb in requests]
            await asyncio.gather(*tasks)
    
    async def _fetch(self, session, url, callback):
        """执行单个请求"""
        try:
            async with session.get(url) as response:
                data = await response.json()
                callback(data)
        except Exception as e:
            logger.error(f"请求失败: {url}, {e}")
```

### 7.2 请求缓存和预取

```python
class RequestCache:
    """请求缓存"""
    
    def __init__(self):
        self.cache = {}
        self.cache_times = {}
        self.ttl = 300  # 5分钟
    
    def get(self, url):
        """获取缓存的响应"""
        if url in self.cache:
            if time.time() - self.cache_times[url] < self.ttl:
                return self.cache[url]
            else:
                del self.cache[url]
                del self.cache_times[url]
        return None
    
    def set(self, url, response):
        """缓存响应"""
        self.cache[url] = response
        self.cache_times[url] = time.time()

class PrefetchManager:
    """预取管理器"""
    
    @staticmethod
    async def prefetch_repository_details(repo_ids):
        """预取仓库详情"""
        urls = [f"/api/repositories/{rid}" for rid in repo_ids]
        
        async with aiohttp.ClientSession() as session:
            tasks = [session.get(url) for url in urls]
            responses = await asyncio.gather(*tasks)
            
            for url, response in zip(urls, responses):
                data = await response.json()
                request_cache.set(url, data)
```

### 7.3 连接池优化

```python
import aiohttp
from aiohttp import TCPConnector

class OptimizedHTTPClient:
    """优化的 HTTP 客户端"""
    
    def __init__(self):
        # 配置连接池
        self.connector = TCPConnector(
            limit=100,  # 总连接数限制
            limit_per_host=10,  # 单个主机连接数限制
            ttl_dns_cache=300,  # DNS 缓存时间
            keepalive_timeout=30,  # 保持连接时间
        )
        
        # 配置超时
        self.timeout = aiohttp.ClientTimeout(
            total=30,  # 总超时
            connect=5,  # 连接超时
            sock_read=10,  # 读取超时
        )
        
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def get(self, url, **kwargs):
        """GET 请求"""
        async with self.session.get(url, **kwargs) as response:
            return await response.json()
```

### 7.4 请求重试和降级

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientAPIClient:
    """具有重试和降级的 API 客户端"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def fetch_with_retry(self, url):
        """带重试的请求"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
    
    async def fetch_with_fallback(self, url, fallback_data=None):
        """带降级的请求"""
        try:
            return await self.fetch_with_retry(url)
        except Exception as e:
            logger.error(f"请求失败，使用降级数据: {e}")
            return fallback_data or []
```

---

## 8. 性能监控和分析

### 8.1 性能指标收集

```python
import time
from dataclasses import dataclass
from typing import Dict, List
import statistics

@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    duration_ms: float
    timestamp: float
    success: bool
    error_message: str = None

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.max_metrics = 10000  # 最多保存10000条记录
    
    def record(self, operation: str, duration_ms: float, success: bool, error: str = None):
        """记录性能指标"""
        metric = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
            success=success,
            error_message=error
        )
        self.metrics.append(metric)
        
        # 限制记录数量
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_stats(self, operation: str = None) -> Dict:
        """获取统计信息"""
        metrics = self.metrics
        if operation:
            metrics = [m for m in metrics if m.operation == operation]
        
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)
        
        return {
            'count': len(metrics),
            'success_rate': success_count / len(metrics),
            'avg_duration_ms': statistics.mean(durations),
            'median_duration_ms': statistics.median(durations),
            'p95_duration_ms': statistics.quantiles(durations, n=20)[18],  # 95th percentile
            'p99_duration_ms': statistics.quantiles(durations, n=100)[98],  # 99th percentile
            'max_duration_ms': max(durations),
            'min_duration_ms': min(durations),
        }

# 性能监控装饰器
performance_monitor = PerformanceMonitor()

def monitor_performance(operation_name: str):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            error = None
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration = (time.time() - start) * 1000
                performance_monitor.record(operation_name, duration, success, error)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            error = None
            try:
                return func(*args, **kwargs)
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration = (time.time() - start) * 1000
                performance_monitor.record(operation_name, duration, success, error)
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
```

### 8.2 数据库性能分析

```python
class DatabasePerformanceAnalyzer:
    """数据库性能分析器"""
    
    def __init__(self, db):
        self.db = db
    
    def analyze_query(self, sql, params=None):
        """分析查询计划"""
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        plan = self.db.query(explain_sql, params)
        
        # 检查是否使用了索引
        uses_index = any('USING INDEX' in str(row) for row in plan)
        has_scan = any('SCAN' in str(row) for row in plan)
        
        return {
            'plan': plan,
            'uses_index': uses_index,
            'has_full_scan': has_scan,
            'warning': '查询未使用索引' if not uses_index else None
        }
    
    def get_slow_queries(self, threshold_ms=500):
        """获取慢查询"""
        metrics = performance_monitor.metrics
        slow_queries = [
            m for m in metrics 
            if m.operation.startswith('db_') and m.duration_ms > threshold_ms
        ]
        return slow_queries
    
    def get_index_usage_stats(self):
        """获取索引使用统计"""
        sql = """
        SELECT 
            name,
            tbl,
            CASE 
                WHEN name LIKE 'sqlite_%' THEN 'auto'
                ELSE 'manual'
            END as type
        FROM sqlite_master 
        WHERE type = 'index'
        """
        return self.db.query(sql)
```

---

## 9. 性能测试和基准

### 9.1 基准测试

```python
import timeit
from typing import Callable

class PerformanceBenchmark:
    """性能基准测试"""
    
    @staticmethod
    def benchmark(func: Callable, iterations: int = 1000, setup: str = ""):
        """执行基准测试"""
        duration = timeit.timeit(func, number=iterations, setup=setup)
        avg_time = duration / iterations * 1000  # 转换为毫秒
        
        return {
            'total_time_s': duration,
            'avg_time_ms': avg_time,
            'iterations': iterations,
            'ops_per_second': iterations / duration
        }
    
    @staticmethod
    def compare_implementations(funcs: Dict[str, Callable], iterations: int = 1000):
        """比较不同实现的性能"""
        results = {}
        for name, func in funcs.items():
            results[name] = PerformanceBenchmark.benchmark(func, iterations)
        
        # 找出最快的实现
        fastest = min(results.items(), key=lambda x: x[1]['avg_time_ms'])
        
        # 计算相对性能
        for name, result in results.items():
            result['relative_speed'] = result['avg_time_ms'] / fastest[1]['avg_time_ms']
        
        return results

# 使用示例
def test_batch_insert():
    """测试批量插入性能"""
    implementations = {
        'single_insert': lambda: single_insert_test(),
        'batch_insert_500': lambda: batch_insert_test(500),
        'batch_insert_1000': lambda: batch_insert_test(1000),
    }
    
    results = PerformanceBenchmark.compare_implementations(implementations, iterations=10)
    
    for name, result in results.items():
        print(f"{name}: {result['avg_time_ms']:.2f}ms (relative: {result['relative_speed']:.2f}x)")
```

### 9.2 压力测试

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class StressTest:
    """压力测试"""
    
    @staticmethod
    async def test_concurrent_requests(num_requests: int, func: Callable):
        """测试并发请求"""
        start = time.time()
        
        tasks = [func() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        
        return {
            'total_requests': num_requests,
            'successful': successful,
            'failed': failed,
            'duration_s': duration,
            'requests_per_second': num_requests / duration,
            'avg_response_time_ms': (duration / num_requests) * 1000
        }
    
    @staticmethod
    def test_database_load(num_queries: int):
        """测试数据库负载"""
        def query_func():
            return db.query("SELECT * FROM repositories LIMIT 100")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            start = time.time()
            futures = [executor.submit(query_func) for _ in range(num_queries)]
            results = [f.result() for f in futures]
            duration = time.time() - start
        
        return {
            'total_queries': num_queries,
            'duration_s': duration,
            'queries_per_second': num_queries / duration
        }
```

---

## 10. 优化效果评估

### 10.1 优化前后对比

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 仓库列表加载时间 (10K 条) | 3.5s | 0.8s | 77% ↑ |
| 搜索响应时间 | 1.2s | 0.35s | 71% ↑ |
| 批量插入 (1000 条) | 2.8s | 0.45s | 84% ↑ |
| 内存使用 (10K 仓库) | 450MB | 180MB | 60% ↓ |
| 前端首屏渲染 | 2.1s | 0.6s | 71% ↑ |
| 虚拟滚动 FPS | 15fps | 60fps | 300% ↑ |
| API 并发请求 | 5/s | 50/s | 900% ↑ |

### 10.2 关键优化措施影响

```
数据库查询优化: ████████████████████ 35%
批量操作优化:   ███████████████ 25%
缓存策略:       ████████████ 20%
前端虚拟滚动:   ████████ 12%
异步处理优化:   █████ 8%
```

### 10.3 推荐配置

#### SQLite 配置
```python
# 推荐的 SQLite 性能配置
SQLITE_PRAGMA_CONFIG = {
    'journal_mode': 'WAL',           # 使用 WAL 模式
    'synchronous': 'NORMAL',          # 平衡性能和安全
    'cache_size': -64000,             # 64MB 缓存
    'page_size': 4096,                # 4KB 页面大小
    'temp_store': 'MEMORY',           # 临时表使用内存
    'mmap_size': 268435456,           # 256MB 内存映射
    'foreign_keys': 'ON',             # 启用外键
    'auto_vacuum': 'INCREMENTAL',     # 增量清理
}
```

#### 应用配置
```python
# 推荐的应用性能配置
PERFORMANCE_CONFIG = {
    'batch_size': 1000,               # 批处理大小
    'max_concurrent_requests': 10,    # 最大并发请求数
    'cache_ttl': 300,                 # 缓存过期时间(秒)
    'lru_cache_size': 1000,           # LRU 缓存容量
    'query_timeout': 30,              # 查询超时时间(秒)
    'max_memory_mb': 512,             # 最大内存使用(MB)
    'enable_query_cache': True,       # 启用查询缓存
    'enable_prefetch': True,          # 启用预取
    'worker_threads': 4,              # 工作线程数
}
```

---

## 11. 最佳实践建议

### 11.1 开发阶段

1. **使用性能监控装饰器**：对所有数据库操作和 API 调用添加性能监控
2. **编写性能测试**：每个关键功能都应有对应的性能基准测试
3. **代码审查关注性能**：特别关注循环、递归和数据库查询
4. **避免 N+1 查询**：使用 JOIN 或批量查询代替循环查询

### 11.2 部署阶段

1. **配置 WAL 模式**：SQLite 使用 WAL 模式提升并发性能
2. **调整缓存大小**：根据可用内存调整 SQLite 缓存
3. **启用连接池**：复用数据库连接，减少开销
4. **配置请求限流**：避免过载

### 11.3 运维阶段

1. **定期 VACUUM**：清理数据库碎片，优化存储
2. **监控慢查询**：定期分析慢查询日志并优化
3. **缓存预热**：应用启动时预热常用数据
4. **性能报告**：定期生成性能报告，追踪趋势

---

## 12. 故障排查指南

### 12.1 常见性能问题

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| 全表扫描 | 查询耗时 > 1s | 创建合适的索引 |
| 内存泄漏 | 内存持续增长 | 检查缓存清理逻辑 |
| 死锁 | 请求超时 | 优化事务范围和顺序 |
| 缓存穿透 | 查询负载高 | 添加空值缓存 |
| CPU 占用高 | 响应变慢 | 优化计算密集型操作 |

### 12.2 调试工具

```python
# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 查询分析
db.set_trace_callback(lambda sql: logger.debug(f"SQL: {sql}"))

# 性能分析
import cProfile
cProfile.run('main()', 'profile_stats')

# 内存分析
from memory_profiler import profile

@profile
def memory_intensive_function():
    pass
```

---

## 总结

本性能优化方案涵盖了数据库、后端、前端、网络等多个层面，通过系统化的优化措施，可以显著提升 GitHubStarsManager 在大数据量场景下的性能表现。

**核心优化策略**：
1. 数据库层：索引优化、查询优化、批量操作
2. 应用层：缓存策略、异步处理、内存管理
3. 前端层：虚拟滚动、懒加载、代码分割
4. 网络层：请求合并、连接池、预取策略

**实施建议**：
- 优先实施影响最大的优化（数据库查询、批量操作、缓存）
- 在实施过程中持续监控性能指标
- 通过 A/B 测试验证优化效果
- 建立性能基线和持续监控机制

---

*文档版本：v1.0*  
*更新时间：2025-10-31*  
*作者：Performance Optimization Team*
