# 星标仓库自动同步 - 快速启动指南

## 🚀 5分钟快速开始

### 步骤 1: 安装依赖

```bash
pip install schedule requests
```

### 步骤 2: 准备 GitHub Token

1. 访问 GitHub Settings -> Developer settings -> Personal access tokens
2. 生成新 token，至少勾选 `repo` 和 `read:user` 权限
3. 保存 token（只显示一次）

### 步骤 3: 创建基础同步脚本

创建 `sync_demo.py` 文件：

```python
import logging
from services.github_service import GitHubService
from services.sync_service import SyncService, SyncConfig, DatabaseManager
from services.sync_scheduler import SyncScheduler, SchedulerConfig, ScheduleInterval

# 配置日志
logging.basicConfig(level=logging.INFO)

# 替换为你的 GitHub Token
GITHUB_TOKEN = "ghp_your_token_here"

# 初始化服务
github_service = GitHubService(token=GITHUB_TOKEN)
db_manager = DatabaseManager(db_path="./data/github_stars.db")
sync_service = SyncService(github_service, db_manager)

# 创建调度器（每6小时自动同步）
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.HOURS_6,
    sync_on_startup=True
)
scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)

# 启动调度器
scheduler.start()

# 保持运行
import time
try:
    print("调度器已启动，按 Ctrl+C 停止")
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("\n正在停止...")
    scheduler.stop()
    print("已停止")
```

### 步骤 4: 运行

```bash
python sync_demo.py
```

---

## 📋 常见使用场景

### 场景 1: 每天凌晨2点自动同步

```python
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.DAILY,
    sync_time="02:00",
    sync_on_startup=False
)
```

### 场景 2: 手动触发同步

```python
# 不启用自动同步
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.MANUAL
)
scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)
scheduler.start()

# 手动触发
scheduler.trigger_sync(force_full=True)
```

### 场景 3: 带进度显示的同步

```python
def show_progress(progress):
    print(f"进度: {progress.get_progress_percentage():.1f}% | "
          f"处理: {progress.processed_repos}/{progress.total_repos} | "
          f"新增: {progress.added_repos} | "
          f"更新: {progress.updated_repos}")

sync_service.add_progress_callback(show_progress)
history = sync_service.sync_repositories()
```

### 场景 4: 查看同步历史

```python
# 获取最近10次同步记录
history_list = scheduler.get_sync_history(limit=10)

for record in history_list:
    print(f"时间: {record.started_at}")
    print(f"状态: {record.status}")
    print(f"处理: {record.items_processed}, 新增: {record.items_added}")
    print("-" * 50)
```

### 场景 5: 获取统计信息

```python
stats = scheduler.get_statistics()

print(f"总同步次数: {stats['total_syncs']}")
print(f"成功率: {stats['success_rate']}%")
print(f"同步仓库总数: {stats['total_repos_synced']}")
print(f"上次同步: {stats['last_sync_time']}")
print(f"下次同步: {stats['next_sync_time']}")
```

---

## ⚙️ 配置选项说明

### 同步间隔选项

| 选项 | 说明 | 适用场景 |
|------|------|----------|
| `MANUAL` | 手动触发 | 完全手动控制 |
| `MINUTES_30` | 每30分钟 | 开发测试 |
| `HOURLY` | 每小时 | 频繁更新 |
| `HOURS_6` | 每6小时 | 推荐默认 |
| `HOURS_12` | 每12小时 | 低频使用 |
| `DAILY` | 每天 | 定时维护 |
| `WEEKLY` | 每周 | 最低频率 |

### 冲突解决策略

| 策略 | 说明 | 推荐场景 |
|------|------|----------|
| `KEEP_LOCAL` | 保留本地修改 | 本地数据优先 |
| `KEEP_REMOTE` | 使用远程数据 | 只读同步 |
| `MERGE` | 智能合并 | 推荐默认 |
| `ASK_USER` | 询问用户 | 需要手动确认 |

---

## 🔧 环境变量配置（推荐）

创建 `.env` 文件：

```bash
GITHUB_TOKEN=ghp_your_token_here
SYNC_INTERVAL=HOURS_6
SYNC_TIME=02:00
DB_PATH=./data/github_stars.db
```

在代码中读取：

```python
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
SYNC_INTERVAL = os.getenv('SYNC_INTERVAL', 'HOURS_6')
SYNC_TIME = os.getenv('SYNC_TIME', '02:00')
DB_PATH = os.getenv('DB_PATH', './data/github_stars.db')
```

---

## 📊 监控和日志

### 配置日志输出到文件

```python
import logging
from logging.handlers import RotatingFileHandler

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

### 添加事件回调

```python
def on_sync_start():
    print("🔄 同步开始")

def on_sync_complete(history):
    print(f"✅ 同步完成: 新增 {history.items_added}, 更新 {history.items_updated}")

def on_sync_error(error):
    print(f"❌ 同步失败: {error}")

scheduler.on_sync_start = on_sync_start
scheduler.on_sync_complete = on_sync_complete
scheduler.on_sync_error = on_sync_error
```

---

## 🐛 故障排查

### 问题 1: 同步失败

**检查**:
```python
# 检查 GitHub API 速率限制
rate_info = github_service.get_rate_limit_status()
print(f"剩余请求: {rate_info['remaining']}/{rate_info['limit']}")
```

### 问题 2: 数据库锁定

**解决**: 确保只有一个进程访问数据库

### 问题 3: Token 过期

**解决**: 重新生成 GitHub Token

---

## 📚 更多资源

- [完整使用文档](./SYNC_README.md)
- [GitHub API 服务文档](./README.md)
- [数据库架构设计](../database/schema_design.md)

---

## 💡 提示

1. ✅ 推荐使用环境变量存储敏感信息
2. ✅ 定期备份数据库文件
3. ✅ 监控 API 速率限制
4. ✅ 使用日志文件记录同步历史
5. ✅ 配置合适的同步间隔

---

**开始使用吧！** 🎉
