# 星标仓库自动同步功能使用文档

## 📋 目录

- [功能概述](#功能概述)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [API 参考](#api-参考)
- [使用示例](#使用示例)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## 功能概述

星标仓库自动同步功能提供了完整的 GitHub 星标仓库数据同步解决方案，支持定时自动同步、智能增量更新、冲突解决、进度追踪等功能。

### 主要组件

- **sync_service.py**: 核心同步服务，实现同步逻辑、冲突解决、状态管理
- **sync_scheduler.py**: 定时调度器，管理自动同步任务、重试策略
- **数据库集成**: 基于 SQLite 数据库持久化存储

---

## 核心特性

### 1. 定时同步调度器

支持多种同步间隔：

- ✅ **手动触发**: 完全由用户控制
- ✅ **每30分钟**: 高频同步，适合开发测试
- ✅ **每小时**: 保持数据较新
- ✅ **每6小时**: 推荐的默认间隔
- ✅ **每12小时**: 适合低频使用
- ✅ **每天**: 指定时间同步
- ✅ **每周**: 定期维护同步

### 2. 智能增量同步

- 🔄 **全量同步**: 重新同步所有仓库
- 🔄 **增量同步**: 仅同步变更的仓库
- 🔄 **智能模式**: 自动选择最优同步方式

### 3. 冲突解决策略

当本地数据与远程数据冲突时：

- 🔀 **保留本地**: 不更新本地修改
- 🔀 **使用远程**: 覆盖为远程数据
- 🔀 **合并策略**: 更新远程数据，保留本地自定义字段（推荐）
- 🔀 **询问用户**: 记录冲突，等待用户决策

### 4. 同步状态追踪

实时监控同步进度：

- 📊 总仓库数、已处理数
- 📊 新增、更新、删除、跳过、失败统计
- 📊 当前处理仓库
- 📊 预估剩余时间
- 📊 冲突数量

### 5. 错误处理和重试机制

- ⚡ 自动重试失败的同步任务
- ⚡ 可配置最大重试次数和延迟
- ⚡ 详细的错误日志记录
- ⚡ 超时保护

### 6. 同步历史记录

- 📝 完整的同步历史
- 📝 执行时间统计
- 📝 成功率分析
- 📝 错误信息追溯

### 7. 高级功能

- 🌙 **静默时段**: 避免在指定时间段同步
- 🚀 **启动时同步**: 应用启动时自动同步
- 🔔 **回调通知**: 同步事件回调
- ⏸️ **暂停/恢复**: 控制同步执行

---

## 快速开始

### 安装依赖

```bash
pip install schedule
```

项目已包含的依赖：
- `github_service.py` - GitHub API 服务
- `github_api.py` - GitHub API 客户端
- SQLite 数据库支持

### 基础使用

```python
import logging
from github_service import GitHubService
from sync_service import SyncService, SyncConfig, DatabaseManager
from sync_scheduler import SyncScheduler, SchedulerConfig, ScheduleInterval

# 配置日志
logging.basicConfig(level=logging.INFO)

# 1. 初始化 GitHub 服务
github_service = GitHubService(token="your-github-token")

# 2. 初始化数据库管理器
db_manager = DatabaseManager(db_path="./data/github_stars.db")

# 3. 创建同步服务
sync_service = SyncService(github_service, db_manager)

# 4. 创建调度器
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.HOURS_6,
    sync_on_startup=True
)
scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)

# 5. 启动调度器
scheduler.start()

# 6. 手动触发同步（可选）
scheduler.trigger_sync()

# 7. 获取状态
status = scheduler.get_status()
print(f"调度器状态: {status.to_dict()}")
```

---

## 详细配置

### SyncConfig - 同步配置

```python
from sync_service import SyncConfig, SyncMode, ConflictStrategy

config = SyncConfig(
    # 同步模式
    mode=SyncMode.SMART,  # FULL, INCREMENTAL, SMART
    
    # 冲突解决策略
    conflict_strategy=ConflictStrategy.MERGE,  # KEEP_LOCAL, KEEP_REMOTE, MERGE, ASK_USER
    
    # 批处理大小
    batch_size=50,
    
    # 重试设置
    max_retries=3,
    retry_delay=5,  # 秒
    
    # 超时时间
    timeout=300,  # 秒
    
    # 是否启用 AI 分析
    enable_ai_analysis=False,
    
    # 是否同步 Release 信息
    sync_releases=True,
    
    # 并行同步（实验性）
    parallel_sync=False,
    max_workers=3
)
```

### SchedulerConfig - 调度器配置

```python
from sync_scheduler import SchedulerConfig, ScheduleInterval

scheduler_config = SchedulerConfig(
    # 是否启用自动同步
    enabled=True,
    
    # 同步间隔
    interval=ScheduleInterval.HOURS_6,
    
    # 指定同步时间（用于 DAILY 和 WEEKLY）
    sync_time="02:00",  # HH:MM 格式
    
    # 失败重试
    retry_on_failure=True,
    max_retry_attempts=3,
    retry_delay_minutes=10,
    
    # 启动时同步
    sync_on_startup=False,
    
    # 静默时段（不执行同步）
    quiet_hours_start="23:00",
    quiet_hours_end="07:00"
)
```

---

## API 参考

### SyncService 类

#### 核心方法

```python
# 同步仓库
history = sync_service.sync_repositories(force_full=False)

# 停止同步
sync_service.stop_sync()

# 暂停同步
sync_service.pause_sync()

# 恢复同步
sync_service.resume_sync()

# 获取当前进度
progress = sync_service.get_progress()

# 获取同步历史
history_list = sync_service.get_sync_history(limit=50, offset=0)

# 获取未解决的冲突
conflicts = sync_service.get_unresolved_conflicts()
```

#### 进度回调

```python
def progress_callback(progress):
    print(f"进度: {progress.get_progress_percentage():.1f}%")
    print(f"处理: {progress.processed_repos}/{progress.total_repos}")
    print(f"当前: {progress.current_repo}")

sync_service.add_progress_callback(progress_callback)
```

### SyncScheduler 类

#### 核心方法

```python
# 启动调度器
scheduler.start()

# 停止调度器
scheduler.stop()

# 更新配置
new_config = SchedulerConfig(interval=ScheduleInterval.DAILY)
scheduler.update_config(new_config)

# 手动触发同步
scheduler.trigger_sync(force_full=False)

# 获取调度器状态
status = scheduler.get_status()

# 获取配置
config = scheduler.get_config()

# 获取同步进度
progress = scheduler.get_sync_progress()

# 获取统计信息
stats = scheduler.get_statistics()
```

#### 事件回调

```python
# 同步开始回调
def on_sync_start():
    print("同步开始...")

# 同步完成回调
def on_sync_complete(history):
    print(f"同步完成: {history.status}")

# 同步错误回调
def on_sync_error(error):
    print(f"同步错误: {error}")

scheduler.on_sync_start = on_sync_start
scheduler.on_sync_complete = on_sync_complete
scheduler.on_sync_error = on_sync_error
```

### DatabaseManager 类

```python
# 保存同步历史
record_id = db_manager.save_sync_history(history_record)

# 获取同步历史
history = db_manager.get_sync_history(limit=50, offset=0)

# 保存冲突
conflict_id = db_manager.save_conflict(conflict_record)

# 获取未解决的冲突
conflicts = db_manager.get_unresolved_conflicts()

# 获取仓库
repo = db_manager.get_repository_by_github_id(github_id)

# 保存仓库
repo_id = db_manager.save_repository(starred_repo)
```

---

## 使用示例

### 示例 1: 基础自动同步

```python
import logging
from github_service import GitHubService
from sync_service import SyncService, DatabaseManager
from sync_scheduler import SyncScheduler, SchedulerConfig, ScheduleInterval

logging.basicConfig(level=logging.INFO)

# 初始化服务
github_service = GitHubService(token="ghp_your_token_here")
db_manager = DatabaseManager()
sync_service = SyncService(github_service, db_manager)

# 配置每6小时自动同步
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.HOURS_6,
    sync_on_startup=True,
    retry_on_failure=True
)

scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)
scheduler.start()

# 保持运行
import time
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    scheduler.stop()
```

### 示例 2: 带进度监控的同步

```python
from sync_service import SyncService, SyncConfig, DatabaseManager
from github_service import GitHubService

github_service = GitHubService(token="your-token")
db_manager = DatabaseManager()
sync_service = SyncService(github_service, db_manager)

# 添加进度回调
def show_progress(progress):
    percentage = progress.get_progress_percentage()
    print(f"\r进度: {percentage:.1f}% | "
          f"处理: {progress.processed_repos}/{progress.total_repos} | "
          f"新增: {progress.added_repos} | "
          f"更新: {progress.updated_repos} | "
          f"失败: {progress.failed_repos}",
          end='', flush=True)

sync_service.add_progress_callback(show_progress)

# 执行同步
history = sync_service.sync_repositories()
print(f"\n同步完成: {history.status}")
```

### 示例 3: 自定义冲突解决

```python
from sync_service import SyncConfig, ConflictStrategy, SyncMode

# 配置合并策略
config = SyncConfig(
    mode=SyncMode.SMART,
    conflict_strategy=ConflictStrategy.MERGE,
    max_retries=5
)

sync_service = SyncService(github_service, db_manager, config)

# 执行同步
history = sync_service.sync_repositories()

# 检查冲突
conflicts = sync_service.get_unresolved_conflicts()
if conflicts:
    print(f"发现 {len(conflicts)} 个未解决的冲突:")
    for conflict in conflicts:
        print(f"  - {conflict.repo_full_name}: {conflict.field_name}")
```

### 示例 4: 每日定时同步

```python
from sync_scheduler import SchedulerConfig, ScheduleInterval

# 配置每天凌晨2点同步
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.DAILY,
    sync_time="02:00",
    quiet_hours_start="23:00",
    quiet_hours_end="07:00",
    retry_on_failure=True,
    max_retry_attempts=3
)

scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)

# 设置回调
def on_complete(history):
    if history.status == "success":
        print(f"✅ 同步成功: 新增 {history.items_added}, 更新 {history.items_updated}")
    else:
        print(f"❌ 同步失败: {history.error_message}")

scheduler.on_sync_complete = on_complete
scheduler.start()
```

### 示例 5: 获取统计信息

```python
# 获取调度器统计
stats = scheduler.get_statistics()

print(f"总同步次数: {stats['total_syncs']}")
print(f"成功次数: {stats['successful_syncs']}")
print(f"失败次数: {stats['failed_syncs']}")
print(f"成功率: {stats['success_rate']}%")
print(f"平均执行时间: {stats['avg_execution_time_ms']}ms")
print(f"同步仓库总数: {stats['total_repos_synced']}")
print(f"新增仓库总数: {stats['total_repos_added']}")
print(f"更新仓库总数: {stats['total_repos_updated']}")
print(f"上次同步: {stats['last_sync_time']}")
print(f"下次同步: {stats['next_sync_time']}")
```

### 示例 6: 完整的生产环境配置

```python
import logging
from pathlib import Path

# 配置日志
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "sync.log"),
        logging.StreamHandler()
    ]
)

# 初始化服务
github_service = GitHubService(
    token="your-token",
    ai_config=AIConfig(
        id="openai",
        name="OpenAI",
        api_url="https://api.openai.com/v1/chat/completions",
        api_key="your-openai-key",
        enabled=True
    )
)

db_manager = DatabaseManager(db_path="./data/github_stars.db")

sync_config = SyncConfig(
    mode=SyncMode.SMART,
    conflict_strategy=ConflictStrategy.MERGE,
    batch_size=50,
    max_retries=3,
    timeout=600,
    enable_ai_analysis=True,
    sync_releases=True
)

sync_service = SyncService(github_service, db_manager, sync_config)

scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.HOURS_6,
    sync_time="02:00",
    retry_on_failure=True,
    max_retry_attempts=5,
    retry_delay_minutes=15,
    sync_on_startup=True,
    quiet_hours_start="23:00",
    quiet_hours_end="07:00"
)

scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)

# 设置事件处理
def on_sync_start():
    logging.info("=" * 50)
    logging.info("同步任务开始")

def on_sync_complete(history):
    logging.info("同步任务完成")
    logging.info(f"状态: {history.status}")
    logging.info(f"处理: {history.items_processed}")
    logging.info(f"新增: {history.items_added}")
    logging.info(f"更新: {history.items_updated}")
    logging.info(f"耗时: {history.execution_time_ms}ms")
    logging.info("=" * 50)

def on_sync_error(error):
    logging.error(f"同步错误: {error}")
    # 可以在这里发送通知（邮件、Webhook等）

scheduler.on_sync_start = on_sync_start
scheduler.on_sync_complete = on_sync_complete
scheduler.on_sync_error = on_sync_error

# 启动调度器
scheduler.start()
logging.info("同步调度器已启动")

# 运行
try:
    import time
    while True:
        time.sleep(3600)  # 每小时打印一次状态
        stats = scheduler.get_statistics()
        logging.info(f"当前统计: {stats}")
except KeyboardInterrupt:
    logging.info("接收到停止信号")
    scheduler.stop()
    logging.info("调度器已停止")
```

---

## 最佳实践

### 1. 同步间隔选择

- **开发/测试**: 使用 `HOURLY` 或 `HOURS_6`
- **生产环境**: 推荐 `HOURS_6` 或 `HOURS_12`
- **低频使用**: 使用 `DAILY` 或 `WEEKLY`

### 2. 冲突解决策略

- **大多数情况**: 使用 `MERGE` 策略（推荐）
- **只读同步**: 使用 `KEEP_REMOTE`
- **完全手动**: 使用 `ASK_USER`

### 3. 错误处理

```python
# 配置合理的重试策略
scheduler_config = SchedulerConfig(
    retry_on_failure=True,
    max_retry_attempts=3,
    retry_delay_minutes=10
)

# 添加错误回调进行监控
def on_error(error):
    # 记录错误
    logging.error(f"同步错误: {error}")
    
    # 发送通知（可选）
    send_notification(f"同步失败: {error}")

scheduler.on_sync_error = on_error
```

### 4. 性能优化

```python
# 使用智能同步模式
sync_config = SyncConfig(
    mode=SyncMode.SMART,  # 自动选择最优策略
    batch_size=50,        # 批量处理
    timeout=600           # 适当的超时时间
)

# 启用数据库索引（已在 schema_design.md 中定义）
```

### 5. 日志管理

```python
import logging
from logging.handlers import RotatingFileHandler

# 使用日志轮转
handler = RotatingFileHandler(
    'sync.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[handler, logging.StreamHandler()]
)
```

### 6. 数据备份

定期备份数据库：

```python
import shutil
from datetime import datetime

def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"./backups/github_stars_{timestamp}.db"
    shutil.copy2(db_manager.db_path, backup_path)
    logging.info(f"数据库已备份到: {backup_path}")

# 在同步完成后备份
def on_sync_complete(history):
    if history.status == "success":
        backup_database()

scheduler.on_sync_complete = on_sync_complete
```

---

## 故障排查

### 问题 1: 同步任务无法启动

**症状**: 调用 `scheduler.start()` 后没有反应

**解决方案**:
```python
# 检查配置是否启用
config = scheduler.get_config()
print(f"调度器启用状态: {config.enabled}")

# 检查调度器状态
status = scheduler.get_status()
print(f"调度器运行状态: {status.is_running}")

# 检查日志
logging.basicConfig(level=logging.DEBUG)
```

### 问题 2: GitHub API 速率限制

**症状**: 同步失败，提示速率限制

**解决方案**:
```python
# 检查速率限制状态
rate_info = github_service.get_rate_limit_status()
print(f"剩余请求: {rate_info['remaining']}/{rate_info['limit']}")
print(f"重置时间: {rate_info['reset_time']}")

# 调整同步间隔
scheduler_config = SchedulerConfig(
    interval=ScheduleInterval.HOURS_12  # 降低频率
)
```

### 问题 3: 数据库锁定

**症状**: 同步时出现数据库锁定错误

**解决方案**:
```python
# 确保正确关闭连接
# DatabaseManager 已处理连接管理

# 如果问题持续，检查是否有其他进程访问数据库
import sqlite3
conn = sqlite3.connect("./data/github_stars.db")
conn.execute("PRAGMA journal_mode=WAL")  # 使用 WAL 模式
conn.close()
```

### 问题 4: 同步进度卡住

**症状**: 同步进度长时间不更新

**解决方案**:
```python
# 检查当前状态
progress = sync_service.get_progress()
print(f"状态: {progress.status}")
print(f"当前仓库: {progress.current_repo}")

# 停止并重新开始
sync_service.stop_sync()
time.sleep(5)
scheduler.trigger_sync(force_full=True)
```

### 问题 5: 内存占用过高

**症状**: 长时间运行后内存占用增加

**解决方案**:
```python
# 减小批处理大小
sync_config = SyncConfig(
    batch_size=20  # 降低批处理大小
)

# 清理缓存
github_service.cleanup_cache()

# 定期重启调度器
import schedule
schedule.every().day.at("03:00").do(restart_scheduler)
```

### 问题 6: 冲突过多

**症状**: 大量冲突记录

**解决方案**:
```python
# 检查未解决的冲突
conflicts = sync_service.get_unresolved_conflicts()
print(f"未解决冲突数: {len(conflicts)}")

# 批量解决冲突（使用合并策略）
sync_config = SyncConfig(
    conflict_strategy=ConflictStrategy.MERGE
)

# 或手动处理冲突
for conflict in conflicts:
    print(f"冲突: {conflict.repo_full_name}")
    # 根据业务逻辑处理
```

---

## 附录

### 数据库表结构

同步服务使用以下数据库表：

- `repositories`: 仓库主表
- `sync_logs`: 同步历史记录
- `sync_configs`: 同步配置
- `sync_status`: 同步状态
- `sync_conflicts`: 冲突记录

详细架构请参考 `database/schema_design.md`

### 依赖项

```
# requirements.txt
schedule>=1.1.0
```

### 相关文档

- [GitHub API 服务文档](./README.md)
- [数据库架构设计](../database/schema_design.md)
- [GitHub API 文档](https://docs.github.com/en/rest)

---

## 贡献与支持

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发起 Pull Request
- 查看项目文档

---

**最后更新**: 2025-10-31
**版本**: 1.0.0
