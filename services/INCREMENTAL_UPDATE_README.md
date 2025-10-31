# 增量更新机制文档

## 概述

增量更新服务（IncrementalUpdateService）提供高效的增量更新机制，最小化数据传输和处理。该服务实现了完整的变更检测、差异计算、批量更新优化、数据一致性保证、更新日志记录和回滚机制。

## 核心功能

### 1. 变更检测（ChangeDetector）

自动检测以下类型的变更：

- **仓库元数据变更**：描述、语言、星标数、主题、更新时间等
- **Release 更新**：新增 Release、Release 版本变更
- **星标状态变更**：仓库的星标状态改变
- **仓库新增/删除**：新星标的仓库或取消星标的仓库
- **标签更新**：仓库标签的变化
- **描述更新**：仓库描述的修改

#### 变更类型枚举

```python
class ChangeType(Enum):
    METADATA_UPDATE = "metadata_update"      # 仓库元数据变更
    RELEASE_UPDATE = "release_update"        # Release 更新
    STAR_STATUS = "star_status"              # 星标状态变更
    NEW_REPO = "new_repo"                    # 新增仓库
    REMOVED_REPO = "removed_repo"            # 移除仓库
    TAGS_UPDATE = "tags_update"              # 标签更新
    DESCRIPTION_UPDATE = "description_update" # 描述更新
```

### 2. 差异计算（DiffCalculator）

提供精确的数据差异计算：

- **校验和计算**：使用 SHA256 计算数据指纹
- **差异分析**：识别新增、删除、修改的字段
- **显著性判断**：评估变更是否需要处理
- **智能合并**：合并多个变更以减少处理次数

#### 差异格式

```python
diff = {
    'added': {},      # 新增的字段
    'removed': {},    # 删除的字段
    'modified': {}    # 修改的字段
}
```

### 3. 时间戳管理（SyncState）

精确跟踪每个仓库的同步状态：

- **last_sync**：最后同步时间
- **last_modified**：最后修改时间
- **sync_checksum**：同步校验和
- **version**：版本号（单调递增）
- **metadata**：扩展元数据

#### 同步状态示例

```python
sync_state = SyncState(
    repo_id=123,
    repo_full_name="user/repo",
    last_sync=datetime.now(),
    last_modified=datetime.now(),
    sync_checksum="abc123...",
    version=1
)
```

### 4. 批量更新优化（BatchUpdateOptimizer）

智能优化更新处理：

- **批次创建**：将变更分组为合理大小的批次
- **顺序优化**：按优先级排序更新（新增 > 元数据 > Release > 星标）
- **去重处理**：移除重复变更，保留最新的
- **并发控制**：限制并发更新数量

#### 配置参数

```python
optimizer = BatchUpdateOptimizer(
    batch_size=50,        # 每批处理 50 个变更
    max_concurrent=5      # 最多 5 个并发批次
)
```

### 5. 数据一致性保证（ConsistencyGuard）

确保数据更新的一致性：

- **一致性验证**：通过校验和验证数据完整性
- **快照创建**：在更新前创建数据快照
- **快照比较**：比对更新前后的数据状态
- **冲突检测**：识别并处理数据冲突

### 6. 更新日志记录（UpdateLogger）

完整记录所有更新活动：

#### 数据库表结构

**change_logs** - 变更日志表
```sql
CREATE TABLE change_logs (
    change_id TEXT PRIMARY KEY,
    change_type TEXT NOT NULL,
    repo_id INTEGER NOT NULL,
    repo_full_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**update_batches** - 更新批次表
```sql
CREATE TABLE update_batches (
    batch_id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    applied_at TIMESTAMP,
    changes_count INTEGER DEFAULT 0
)
```

**sync_states** - 同步状态表
```sql
CREATE TABLE sync_states (
    repo_id INTEGER PRIMARY KEY,
    repo_full_name TEXT NOT NULL,
    last_sync TIMESTAMP NOT NULL,
    last_modified TIMESTAMP NOT NULL,
    sync_checksum TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    metadata TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**rollback_points** - 回滚点表
```sql
CREATE TABLE rollback_points (
    rollback_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    snapshot_data TEXT NOT NULL,
    description TEXT
)
```

### 7. 回滚机制（RollbackManager）

提供完整的回滚能力：

- **回滚点创建**：在更新前自动创建回滚点
- **快照保存**：保存更新前的完整数据状态
- **回滚执行**：支持将数据恢复到指定回滚点
- **回滚验证**：验证回滚操作的成功性

## 使用示例

### 基本使用

```python
from incremental_update import IncrementalUpdateService

# 初始化服务
service = IncrementalUpdateService(
    log_db_path="./data/update_logs.db",
    batch_size=50,
    max_concurrent=5
)

# 模拟仓库数据
old_repos = [
    {
        'id': 1,
        'full_name': 'user/repo1',
        'description': 'Old description',
        'stargazers_count': 100,
        'language': 'Python'
    }
]

new_repos = [
    {
        'id': 1,
        'full_name': 'user/repo1',
        'description': 'New description',  # 描述变更
        'stargazers_count': 150,           # 星标数变更
        'language': 'Python'
    },
    {
        'id': 2,
        'full_name': 'user/repo2',
        'description': 'A new repository',
        'stargazers_count': 50,
        'language': 'JavaScript'
    }
]

# 检测变更
changes = service.detect_and_record_changes(old_repos, new_repos)
print(f"检测到 {len(changes)} 个变更")

# 处理增量更新
def update_callback(changes):
    """更新回调函数，处理实际的数据更新"""
    for change in changes:
        print(f"应用变更: {change.change_type.value} - {change.repo_full_name}")
        # 在这里执行实际的数据库更新操作

results = service.process_incremental_update(changes, update_callback)
print(f"更新结果: {results}")
```

### 检测 Release 变更

```python
# 检测 Release 更新
old_releases = [
    {'id': 1, 'tag_name': 'v1.0.0', 'published_at': '2025-01-01'}
]

new_releases = [
    {'id': 1, 'tag_name': 'v1.0.0', 'published_at': '2025-01-01'},
    {'id': 2, 'tag_name': 'v1.1.0', 'published_at': '2025-02-01'}  # 新 Release
]

release_changes = service.change_detector.detect_release_changes(
    repo_id=1,
    repo_full_name='user/repo',
    old_releases=old_releases,
    new_releases=new_releases
)

print(f"检测到 {len(release_changes)} 个 Release 变更")
```

### 检测星标状态变更

```python
# 检测星标状态变更
star_change = service.change_detector.detect_star_status_change(
    repo_id=1,
    repo_full_name='user/repo',
    was_starred=True,
    is_starred=False  # 取消星标
)

if star_change:
    print(f"星标状态变更: {star_change.metadata['action']}")
```

### 获取更新统计

```python
from datetime import datetime, timedelta

# 获取最近 7 天的更新统计
stats = service.get_update_statistics(
    since=datetime.now() - timedelta(days=7)
)

print(f"统计信息:")
print(f"  总变更数: {stats['total_changes']}")
print(f"  受影响仓库: {stats['affected_repos']}")
print(f"  按类型分布: {stats['by_type']}")
```

### 手动创建回滚点

```python
from incremental_update import UpdateBatch

# 创建更新批次
batch = UpdateBatch(
    batch_id="batch_123",
    changes=changes,
    created_at=datetime.now(),
    status='pending'
)

# 创建回滚点
snapshot_data = {
    'repos': old_repos,
    'timestamp': datetime.now().isoformat()
}

rollback_point = service.rollback_manager.create_rollback_point(
    batch=batch,
    snapshot_data=snapshot_data
)

print(f"回滚点已创建: {rollback_point.rollback_id}")
```

### 执行回滚

```python
# 执行回滚
success = service.rollback_manager.rollback(batch_id="batch_123")

if success:
    print("回滚成功")
else:
    print("回滚失败")
```

### 清理旧日志

```python
# 清理 30 天前的日志
deleted_count = service.cleanup_old_logs(days=30)
print(f"清理了 {deleted_count} 条旧日志记录")
```

## 数据结构

### Change（变更记录）

```python
@dataclass
class Change:
    change_id: str                  # 变更 ID
    change_type: ChangeType         # 变更类型
    repo_id: int                    # 仓库 ID
    repo_full_name: str            # 仓库全名
    old_value: Optional[Any]       # 旧值
    new_value: Optional[Any]       # 新值
    detected_at: datetime          # 检测时间
    metadata: Dict[str, Any]       # 元数据
```

### SyncState（同步状态）

```python
@dataclass
class SyncState:
    repo_id: int                   # 仓库 ID
    repo_full_name: str           # 仓库全名
    last_sync: datetime           # 最后同步时间
    last_modified: datetime       # 最后修改时间
    sync_checksum: str            # 同步校验和
    version: int                  # 版本号
    metadata: Dict[str, Any]      # 元数据
```

### UpdateBatch（更新批次）

```python
@dataclass
class UpdateBatch:
    batch_id: str                  # 批次 ID
    changes: List[Change]          # 变更列表
    created_at: datetime           # 创建时间
    status: str                    # 状态：pending/processing/completed/failed/rolled_back
    error_message: Optional[str]   # 错误消息
    applied_at: Optional[datetime] # 应用时间
```

### RollbackPoint（回滚点）

```python
@dataclass
class RollbackPoint:
    rollback_id: str              # 回滚点 ID
    batch_id: str                 # 批次 ID
    created_at: datetime          # 创建时间
    snapshot_data: Dict[str, Any] # 快照数据
    description: str              # 描述
```

## 性能优化建议

### 1. 批次大小调优

根据数据量和系统资源调整批次大小：

- **小批次**（20-30）：适用于资源受限环境
- **中批次**（50-100）：适用于一般场景（推荐）
- **大批次**（100+）：适用于高性能环境

### 2. 并发控制

根据数据库连接池大小设置并发数：

```python
service = IncrementalUpdateService(
    batch_size=50,
    max_concurrent=5  # 不超过数据库连接池大小的 50%
)
```

### 3. 定期清理

定期清理旧日志以保持数据库性能：

```python
# 每周清理一次
service.cleanup_old_logs(days=30)
```

### 4. 索引优化

确保数据库索引正确创建：

```sql
CREATE INDEX idx_change_logs_repo ON change_logs (repo_id);
CREATE INDEX idx_change_logs_type ON change_logs (change_type);
CREATE INDEX idx_change_logs_detected ON change_logs (detected_at);
```

## 错误处理

### 变更检测失败

```python
try:
    changes = service.detect_and_record_changes(old_repos, new_repos)
except Exception as e:
    logger.error(f"变更检测失败: {e}")
    # 处理错误
```

### 批次处理失败

```python
results = service.process_incremental_update(changes, update_callback)

if results['failed_batches'] > 0:
    print("部分批次处理失败:")
    for error in results['errors']:
        print(f"  批次 {error['batch_id']}: {error['error']}")
```

### 回滚失败

```python
success = service.rollback_manager.rollback(batch_id)

if not success:
    logger.error(f"回滚失败，batch_id: {batch_id}")
    # 可能需要手动干预
```

## 最佳实践

### 1. 定期同步

建议按以下频率进行增量同步：

- **活跃仓库**：每小时一次
- **普通仓库**：每 6-12 小时一次
- **归档仓库**：每天一次

### 2. 变更优先级

按重要性处理变更：

1. 新增/删除仓库（立即处理）
2. Release 更新（高优先级）
3. 元数据更新（中优先级）
4. 星标状态（低优先级）

### 3. 回滚策略

- 每个批次自动创建回滚点
- 保留最近 10 个回滚点
- 超过 7 天的回滚点可以清理

### 4. 监控指标

关键监控指标：

- 变更检测速率
- 批次处理时间
- 失败率
- 回滚频率
- 数据库大小

### 5. 日志保留

建议的日志保留策略：

- **变更日志**：保留 30 天
- **批次日志**：保留 90 天
- **同步状态**：永久保留
- **回滚点**：保留 7 天

## 集成示例

### 与 GitHub Service 集成

```python
from github_service import GitHubService
from incremental_update import IncrementalUpdateService

# 初始化服务
github_service = GitHubService(token="your-token")
update_service = IncrementalUpdateService()

# 获取旧数据（从数据库）
old_repos = load_repos_from_database()

# 获取新数据（从 GitHub API）
sync_result = github_service.sync_starred_repos()
new_repos = sync_result.repos

# 检测变更
changes = update_service.detect_and_record_changes(old_repos, new_repos)

# 处理更新
def update_callback(changes):
    # 更新数据库
    update_database(changes)

results = update_service.process_incremental_update(changes, update_callback)
```

### 定时任务集成

```python
import schedule
import time

def incremental_sync_job():
    """增量同步定时任务"""
    try:
        # 执行增量同步
        changes = service.detect_and_record_changes(old_repos, new_repos)
        results = service.process_incremental_update(changes, update_callback)
        
        logger.info(f"增量同步完成: {results['successful_batches']} 个批次成功")
        
    except Exception as e:
        logger.error(f"增量同步失败: {e}")

# 每小时执行一次
schedule.every().hour.do(incremental_sync_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 故障排查

### 问题：变更检测不准确

**可能原因**：
- 数据格式不一致
- 时间戳比较错误
- 校验和计算失败

**解决方案**：
1. 验证输入数据格式
2. 检查时间戳字段
3. 重新计算校验和

### 问题：批次处理缓慢

**可能原因**：
- 批次大小过大
- 并发数过低
- 数据库性能问题

**解决方案**：
1. 减小批次大小
2. 增加并发数
3. 优化数据库索引
4. 使用连接池

### 问题：回滚失败

**可能原因**：
- 回滚点数据损坏
- 数据库锁定
- 快照数据不完整

**解决方案**：
1. 验证回滚点数据
2. 检查数据库连接
3. 手动恢复数据

## API 参考

### IncrementalUpdateService

主服务类，提供完整的增量更新功能。

#### 初始化

```python
service = IncrementalUpdateService(
    log_db_path="./data/update_logs.db",
    batch_size=50,
    max_concurrent=5
)
```

#### 方法

**detect_and_record_changes(old_repos, new_repos)**
- 检测并记录变更
- 参数：
  - `old_repos`: 旧仓库列表
  - `new_repos`: 新仓库列表
- 返回：`List[Change]` 变更列表

**process_incremental_update(changes, update_callback)**
- 处理增量更新
- 参数：
  - `changes`: 变更列表
  - `update_callback`: 更新回调函数（可选）
- 返回：`Dict[str, Any]` 更新结果

**get_update_statistics(since)**
- 获取更新统计信息
- 参数：
  - `since`: 起始时间（可选）
- 返回：`Dict[str, Any]` 统计信息

**cleanup_old_logs(days)**
- 清理旧日志
- 参数：
  - `days`: 保留天数（默认 30）
- 返回：`int` 清理的记录数

### ChangeDetector

变更检测器，负责识别各类变更。

#### 方法

**detect_repo_changes(old_repo, new_repo)**
- 检测仓库变更
- 参数：
  - `old_repo`: 旧仓库数据
  - `new_repo`: 新仓库数据
- 返回：`List[Change]` 变更列表

**detect_release_changes(repo_id, repo_full_name, old_releases, new_releases)**
- 检测 Release 变更
- 参数：
  - `repo_id`: 仓库 ID
  - `repo_full_name`: 仓库全名
  - `old_releases`: 旧 Release 列表
  - `new_releases`: 新 Release 列表
- 返回：`List[Change]` 变更列表

**detect_star_status_change(repo_id, repo_full_name, was_starred, is_starred)**
- 检测星标状态变更
- 参数：
  - `repo_id`: 仓库 ID
  - `repo_full_name`: 仓库全名
  - `was_starred`: 之前是否星标
  - `is_starred`: 现在是否星标
- 返回：`Optional[Change]` 变更记录或 None

### DiffCalculator

差异计算器，提供数据差异分析。

#### 静态方法

**calculate_checksum(data)**
- 计算数据校验和
- 参数：
  - `data`: 数据字典
- 返回：`str` 校验和

**calculate_diff(old_data, new_data)**
- 计算数据差异
- 参数：
  - `old_data`: 旧数据
  - `new_data`: 新数据
- 返回：`Dict[str, Any]` 差异字典

**is_significant_change(diff, threshold)**
- 判断变更是否显著
- 参数：
  - `diff`: 差异字典
  - `threshold`: 变更阈值（默认 0.1）
- 返回：`bool` 是否显著变更

### RollbackManager

回滚管理器，提供数据回滚功能。

#### 方法

**create_rollback_point(batch, snapshot_data)**
- 创建回滚点
- 参数：
  - `batch`: 更新批次
  - `snapshot_data`: 快照数据
- 返回：`RollbackPoint` 回滚点

**rollback(batch_id)**
- 执行回滚
- 参数：
  - `batch_id`: 批次 ID
- 返回：`bool` 是否回滚成功

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。

## 变更日志

### v1.0.0 (2025-10-31)

- 初始版本发布
- 实现变更检测
- 实现差异计算
- 实现时间戳管理
- 实现批量更新优化
- 实现数据一致性保证
- 实现更新日志记录
- 实现回滚机制
