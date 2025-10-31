# AI 任务队列系统使用文档

## 概述

AI 任务队列系统是一个完整的异步任务管理解决方案，专为 AI 分析任务设计。它提供了优先级队列、并发控制、速率限制、成本管理、失败重试等核心功能。

## 核心特性

### 1. 任务队列管理
- ✅ **优先级队列**: 支持 4 个优先级级别（LOW、MEDIUM、HIGH、URGENT）
- ✅ **容量控制**: 可配置最大队列容量，防止内存溢出
- ✅ **线程安全**: 使用锁机制确保并发安全

### 2. 批量仓库分析调度
- ✅ **批量提交**: 支持一次性提交多个分析任务
- ✅ **进度追踪**: 实时监控批量任务执行进度
- ✅ **并行处理**: 自动并发执行多个仓库分析

### 3. 并发控制和速率限制
- ✅ **并发限制**: 控制同时执行的任务数量
- ✅ **速率限制**: 
  - 每分钟请求数限制
  - 每小时请求数限制
  - 每分钟 token 使用量限制
- ✅ **自动限流**: 超出限制时自动等待

### 4. 任务状态追踪
支持的任务状态：
- `QUEUED`: 已加入队列等待处理
- `RUNNING`: 正在处理中
- `PAUSED`: 已暂停
- `COMPLETED`: 已完成
- `FAILED`: 失败
- `CANCELLED`: 已取消
- `RETRYING`: 重试中

### 5. 失败重试机制
- ✅ **自动重试**: 失败任务自动重试
- ✅ **指数退避**: 重试延迟递增，避免过载
- ✅ **重试次数限制**: 可配置最大重试次数

### 6. 进度监控和报告
- ✅ **实时统计**: 队列大小、执行状态、成功率等
- ✅ **成本追踪**: 实时监控 API 成本消耗
- ✅ **性能指标**: 排队时间、执行时间、token 使用量

### 7. 任务取消和暂停
- ✅ **单个取消**: 取消指定任务
- ✅ **批量取消**: 一次取消多个任务
- ✅ **全局暂停**: 暂停/恢复整个任务处理

### 8. 成本预估和控制
- ✅ **预算限制**: 总预算、日预算、小时预算
- ✅ **成本预估**: 提交前预估任务成本
- ✅ **超预算保护**: 超出预算自动拒绝任务

## 快速开始

### 安装依赖

```bash
pip install aiohttp numpy
```

### 基本使用

```python
import asyncio
from services.ai_task_manager import create_ai_task_manager
from services.task_queue import TaskType, Priority

async def main():
    # 创建并启动任务管理器
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=5,      # 最大并发数
        budget_limit=100.0     # 总预算限制（美元）
    )
    
    # 提交单个任务
    task_id = await manager.submit_task(
        task_type=TaskType.REPOSITORY_ANALYSIS,
        data={
            "repo_info": {
                "name": "example-repo",
                "description": "An example repository",
                "language": "Python",
                "stargazers_count": 1000
            },
            "readme_content": "# Example Repo\n\nThis is an example..."
        },
        priority=Priority.HIGH
    )
    
    print(f"任务已提交: {task_id}")
    
    # 等待任务完成
    result = await manager.wait_for_task(task_id, timeout=60)
    print(f"分析结果: {result}")
    
    # 停止管理器
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## 详细使用指南

### 1. 初始化任务管理器

#### 方式一：使用便捷函数

```python
from services.ai_task_manager import create_ai_task_manager

manager = await create_ai_task_manager(
    api_key="your-api-key",
    max_concurrent=5,
    budget_limit=100.0,
    # AI 客户端额外配置
    base_url="https://api.openai.com/v1",
    timeout=30,
    rate_limit=60
)
```

#### 方式二：手动创建

```python
from services.ai_client import OpenAICompatibleClient, APIConfig
from services.ai_task_manager import AITaskManager

# 创建 AI 客户端
config = APIConfig(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    timeout=30,
    rate_limit=60
)
ai_client = OpenAICompatibleClient(config)

# 创建任务管理器
manager = AITaskManager(
    ai_client=ai_client,
    max_concurrent=5,
    max_queue_size=10000,
    requests_per_minute=60,
    budget_limit=100.0
)

# 启动管理器
await manager.start()
```

### 2. 提交任务

#### 单个任务提交

```python
from services.task_queue import TaskType, Priority, TaskConfig

task_id = await manager.submit_task(
    task_type=TaskType.REPOSITORY_ANALYSIS,
    data={
        "repo_info": {...},
        "readme_content": "..."
    },
    priority=Priority.HIGH,
    config=TaskConfig(
        max_retries=3,
        retry_delay=1.0,
        timeout=60.0,
        estimated_tokens=2000
    ),
    metadata={
        "user_id": "user123",
        "source": "github_stars"
    }
)
```

#### 批量任务提交

```python
tasks = [
    {
        "task_type": "REPOSITORY_ANALYSIS",
        "data": {
            "repo_info": repo1_info,
            "readme_content": repo1_readme
        }
    },
    {
        "task_type": "REPOSITORY_ANALYSIS",
        "data": {
            "repo_info": repo2_info,
            "readme_content": repo2_readme
        }
    }
]

task_ids = await manager.submit_batch(tasks, priority=Priority.MEDIUM)
print(f"已提交 {len(task_ids)} 个任务")
```

#### 带回调的任务

```python
async def on_complete(task):
    print(f"任务 {task.task_id} 完成!")
    print(f"结果: {task.result}")
    print(f"成本: ${task.metrics.actual_cost:.4f}")

async def on_error(task):
    print(f"任务 {task.task_id} 失败: {task.error}")

task_id = await manager.submit_task(
    task_type=TaskType.REPOSITORY_ANALYSIS,
    data={...},
    config=TaskConfig(
        callback=on_complete,
        error_callback=on_error
    )
)
```

#### 带进度回调的批量任务

```python
async def progress_callback(progress, current, total):
    print(f"进度: {progress*100:.1f}% ({current}/{total})")

task_id = await manager.submit_task(
    task_type=TaskType.BATCH_ANALYSIS,
    data={
        "repositories": [repo1, repo2, repo3, ...]
    },
    config=TaskConfig(
        progress_callback=progress_callback
    )
)
```

### 3. 任务类型

#### REPOSITORY_ANALYSIS - 仓库分析

```python
task_id = await manager.submit_task(
    task_type=TaskType.REPOSITORY_ANALYSIS,
    data={
        "repo_info": {
            "name": "repo-name",
            "description": "repo description",
            "language": "Python",
            "stargazers_count": 1000,
            ...
        },
        "readme_content": "# README content..."
    }
)
```

#### BATCH_ANALYSIS - 批量分析

```python
task_id = await manager.submit_task(
    task_type=TaskType.BATCH_ANALYSIS,
    data={
        "repositories": [
            {
                "name": "repo1",
                "description": "...",
                "readme": "..."
            },
            {
                "name": "repo2",
                "description": "...",
                "readme": "..."
            }
        ]
    }
)
```

#### TEXT_CLASSIFICATION - 文本分类

```python
task_id = await manager.submit_task(
    task_type=TaskType.TEXT_CLASSIFICATION,
    data={
        "text": "This is a web framework for Python",
        "categories": ["web", "data", "ml", "devops"]
    }
)
```

#### EMBEDDING_GENERATION - 嵌入向量生成

```python
task_id = await manager.submit_task(
    task_type=TaskType.EMBEDDING_GENERATION,
    data={
        "text": "Generate embedding for this text"
    }
)
```

#### SEMANTIC_SEARCH - 语义搜索

```python
task_id = await manager.submit_task(
    task_type=TaskType.SEMANTIC_SEARCH,
    data={
        "query": "Python web framework",
        "documents": [
            {"id": "1", "text": "...", "embedding": [...]},
            {"id": "2", "text": "...", "embedding": [...]}
        ],
        "top_k": 5
    }
)
```

### 4. 任务状态查询

#### 查询单个任务状态

```python
status = manager.get_task_status(task_id)
print(f"状态: {status['status']}")
print(f"创建时间: {status['created_at']}")
print(f"执行时间: {status['metrics']['execution_time']}秒")
print(f"Token使用: {status['metrics']['tokens_used']}")
print(f"成本: ${status['metrics']['actual_cost']:.4f}")
```

#### 获取任务结果

```python
result = manager.get_task_result(task_id)
if result:
    print(f"任务结果: {result}")
else:
    print("任务未完成或失败")
```

#### 等待任务完成

```python
# 等待任务完成（带超时）
result = await manager.wait_for_task(task_id, timeout=60)

# 无限等待
result = await manager.wait_for_task(task_id)
```

### 5. 任务控制

#### 取消单个任务

```python
success = await manager.cancel_task(task_id)
if success:
    print("任务已取消")
else:
    print("取消失败（任务可能正在执行或已完成）")
```

#### 批量取消任务

```python
results = await manager.cancel_batch([task_id1, task_id2, task_id3])
for task_id, success in results.items():
    print(f"{task_id}: {'已取消' if success else '取消失败'}")
```

#### 暂停和恢复处理

```python
# 暂停任务处理
manager.pause()

# 恢复任务处理
manager.resume()

# 检查状态
if manager.is_paused():
    print("任务处理已暂停")
```

### 6. 统计和监控

#### 获取完整统计信息

```python
stats = manager.get_statistics()

print("=== 系统状态 ===")
print(f"运行中: {stats['status']['running']}")
print(f"暂停: {stats['status']['paused']}")
print(f"运行时间: {stats['status']['uptime_seconds']}秒")

print("\n=== 队列状态 ===")
print(f"队列大小: {stats['queue']['size']}")
print(f"按优先级分布: {stats['queue']['by_priority']}")

print("\n=== 并发状态 ===")
print(f"运行中任务: {stats['concurrency']['running_tasks']}")
print(f"最大并发: {stats['concurrency']['max_concurrent']}")

print("\n=== 速率限制 ===")
rate = stats['rate_limit']
print(f"每分钟请求: {rate['requests_per_minute']['current']}/{rate['requests_per_minute']['limit']}")
print(f"每分钟Token: {rate['tokens_per_minute']['current']}/{rate['tokens_per_minute']['limit']}")

print("\n=== 成本统计 ===")
cost = stats['cost']
print(f"总成本: ${cost['total']['cost']:.4f} / ${cost['total']['limit']:.2f}")
print(f"今日成本: ${cost['daily']['cost']:.4f} / ${cost['daily']['limit']:.2f}")
print(f"本小时成本: ${cost['hourly']['cost']:.4f} / ${cost['hourly']['limit']:.2f}")

print("\n=== 任务统计 ===")
tasks = stats['tasks']
print(f"总任务: {tasks['total']}")
print(f"按状态: {tasks['by_status']}")
print(f"按类型: {tasks['by_type']}")

print("\n=== 性能指标 ===")
perf = stats['performance']
print(f"已处理: {perf['total_processed']}")
print(f"成功: {perf['total_succeeded']}")
print(f"失败: {perf['total_failed']}")
print(f"成功率: {perf['success_rate']:.1f}%")
```

#### 获取队列状态

```python
queue_status = manager.get_queue_status()
print(f"队列大小: {queue_status['total_size']}")
print(f"是否已满: {queue_status['is_full']}")
print(f"是否为空: {queue_status['is_empty']}")
```

### 7. 动态调整设置

```python
# 调整最大并发数
manager.adjust_settings(max_concurrent=10)

# 调整速率限制
manager.adjust_settings(requests_per_minute=120)

# 调整预算限制
manager.adjust_settings(
    budget_limit=200.0,
    daily_limit=20.0
)

# 同时调整多个参数
manager.adjust_settings(
    max_concurrent=10,
    requests_per_minute=120,
    budget_limit=200.0,
    daily_limit=20.0
)
```

### 8. 清理和维护

#### 清理旧任务

```python
# 清理 24 小时前的已完成任务
count = await manager.cleanup_old_tasks(older_than_hours=24)
print(f"已清理 {count} 个旧任务")

# 清理 1 小时前的已完成任务
count = await manager.cleanup_old_tasks(older_than_hours=1)
```

#### 停止管理器

```python
await manager.stop()
```

## 完整示例

### 示例 1: 批量分析 GitHub 仓库

```python
import asyncio
from services.ai_task_manager import create_ai_task_manager
from services.task_queue import TaskType, Priority, TaskConfig

async def analyze_repositories():
    # 创建管理器
    manager = await create_ai_task_manager(
        api_key="your-api-key",
        max_concurrent=3,
        budget_limit=10.0
    )
    
    # 准备仓库列表
    repositories = [
        {
            "name": "flask",
            "description": "A micro web framework",
            "language": "Python",
            "stargazers_count": 60000,
            "readme": "# Flask\n\nFlask is a lightweight WSGI..."
        },
        {
            "name": "django",
            "description": "The Web framework for perfectionists",
            "language": "Python",
            "stargazers_count": 70000,
            "readme": "# Django\n\nDjango is a high-level Python..."
        }
    ]
    
    # 进度回调
    async def on_progress(progress, current, total):
        print(f"[进度] {current}/{total} ({progress*100:.0f}%)")
    
    # 完成回调
    async def on_complete(task):
        print(f"[完成] 任务 {task.task_id}")
        print(f"  - 成本: ${task.metrics.actual_cost:.4f}")
        print(f"  - 执行时间: {task.metrics.execution_time:.2f}秒")
    
    # 提交批量分析任务
    task_id = await manager.submit_task(
        task_type=TaskType.BATCH_ANALYSIS,
        data={"repositories": repositories},
        priority=Priority.HIGH,
        config=TaskConfig(
            progress_callback=on_progress,
            callback=on_complete,
            max_retries=3
        )
    )
    
    print(f"批量分析任务已提交: {task_id}")
    
    # 等待完成
    results = await manager.wait_for_task(task_id, timeout=300)
    
    # 处理结果
    if results:
        print("\n=== 分析结果 ===")
        for i, result in enumerate(results, 1):
            if result['success']:
                print(f"\n{i}. {result['repo_name']}")
                print(f"   摘要: {result['result'].get('summary', 'N/A')}")
            else:
                print(f"\n{i}. {result['repo_name']} - 分析失败")
                print(f"   错误: {result.get('error', 'Unknown')}")
    
    # 显示统计
    stats = manager.get_statistics()
    print(f"\n=== 统计信息 ===")
    print(f"总成本: ${stats['cost']['total']['cost']:.4f}")
    print(f"成功率: {stats['performance']['success_rate']:.1f}%")
    
    # 停止管理器
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(analyze_repositories())
```

### 示例 2: 并发任务处理与监控

```python
import asyncio
from services.ai_task_manager import create_ai_task_manager
from services.task_queue import TaskType, Priority

async def concurrent_processing():
    manager = await create_ai_task_manager(
        api_key="your-api-key",
        max_concurrent=5,
        budget_limit=50.0
    )
    
    # 提交多个独立任务
    task_ids = []
    for i in range(20):
        task_id = await manager.submit_task(
            task_type=TaskType.REPOSITORY_ANALYSIS,
            data={
                "repo_info": {
                    "name": f"repo-{i}",
                    "description": f"Repository {i}",
                    "language": "Python"
                },
                "readme_content": f"# Repo {i}\n\nExample repository"
            },
            priority=Priority.MEDIUM if i < 10 else Priority.LOW
        )
        task_ids.append(task_id)
    
    print(f"已提交 {len(task_ids)} 个任务")
    
    # 监控进度
    while True:
        stats = manager.get_statistics()
        
        # 显示实时状态
        print(f"\r队列: {stats['queue']['size']} | "
              f"运行: {stats['concurrency']['running_tasks']} | "
              f"完成: {stats['tasks']['by_status'].get('completed', 0)} | "
              f"失败: {stats['tasks']['by_status'].get('failed', 0)} | "
              f"成本: ${stats['cost']['total']['cost']:.4f}",
              end="")
        
        # 检查是否全部完成
        pending = stats['queue']['size']
        running = stats['concurrency']['running_tasks']
        if pending == 0 and running == 0:
            break
        
        await asyncio.sleep(1)
    
    print("\n\n所有任务已完成!")
    
    # 获取结果
    completed_count = 0
    failed_count = 0
    
    for task_id in task_ids:
        result = manager.get_task_result(task_id)
        if result:
            completed_count += 1
        else:
            status = manager.get_task_status(task_id)
            if status and status['status'] == 'failed':
                failed_count += 1
    
    print(f"成功: {completed_count}, 失败: {failed_count}")
    
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(concurrent_processing())
```

### 示例 3: 成本控制与预算管理

```python
import asyncio
from services.ai_task_manager import create_ai_task_manager
from services.task_queue import TaskType, Priority

async def budget_control():
    # 设置严格的预算限制
    manager = await create_ai_task_manager(
        api_key="your-api-key",
        max_concurrent=3,
        budget_limit=5.0  # 总预算 $5
    )
    
    # 调整日预算和小时预算
    manager.adjust_settings(
        daily_limit=2.0,   # 每日 $2
        hourly_limit=0.5   # 每小时 $0.5
    )
    
    task_count = 0
    rejected_count = 0
    
    # 持续提交任务直到预算用完
    for i in range(100):
        try:
            task_id = await manager.submit_task(
                task_type=TaskType.REPOSITORY_ANALYSIS,
                data={
                    "repo_info": {"name": f"repo-{i}"},
                    "readme_content": "Example"
                }
            )
            task_count += 1
            print(f"任务 {i+1} 已提交")
            
            # 显示当前成本
            stats = manager.get_statistics()
            cost = stats['cost']
            print(f"  当前成本: ${cost['total']['cost']:.4f} / ${cost['total']['limit']:.2f}")
            print(f"  剩余预算: ${cost['total']['remaining']:.4f}")
            
        except Exception as e:
            rejected_count += 1
            print(f"任务 {i+1} 被拒绝: {str(e)}")
            break
        
        await asyncio.sleep(0.5)
    
    print(f"\n提交的任务: {task_count}")
    print(f"被拒绝的任务: {rejected_count}")
    
    # 等待所有任务完成
    while True:
        stats = manager.get_statistics()
        if stats['queue']['size'] == 0 and stats['concurrency']['running_tasks'] == 0:
            break
        await asyncio.sleep(1)
    
    # 最终统计
    final_stats = manager.get_statistics()
    print(f"\n最终成本: ${final_stats['cost']['total']['cost']:.4f}")
    print(f"成功率: {final_stats['performance']['success_rate']:.1f}%")
    
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(budget_control())
```

## 最佳实践

### 1. 合理设置并发数

```python
# 根据 API 限制设置并发数
# OpenAI: 通常 3-5 个并发即可
manager = await create_ai_task_manager(
    api_key="your-api-key",
    max_concurrent=3  # 保守设置
)
```

### 2. 使用优先级

```python
# 重要任务使用 HIGH 或 URGENT
await manager.submit_task(
    task_type=TaskType.REPOSITORY_ANALYSIS,
    data={...},
    priority=Priority.URGENT  # 优先处理
)

# 批量分析使用 MEDIUM 或 LOW
await manager.submit_task(
    task_type=TaskType.BATCH_ANALYSIS,
    data={...},
    priority=Priority.LOW  # 后台处理
)
```

### 3. 设置合理的预算

```python
# 设置多层预算保护
manager.adjust_settings(
    budget_limit=100.0,   # 总预算
    daily_limit=10.0,     # 每日预算
)
```

### 4. 使用回调处理结果

```python
# 避免轮询，使用回调
async def on_complete(task):
    # 立即处理结果
    save_to_database(task.result)
    notify_user(task.task_id)

await manager.submit_task(
    task_type=TaskType.REPOSITORY_ANALYSIS,
    data={...},
    config=TaskConfig(callback=on_complete)
)
```

### 5. 定期清理旧任务

```python
# 定期清理已完成的任务，释放内存
async def cleanup_task():
    while manager.is_running():
        await asyncio.sleep(3600)  # 每小时
        await manager.cleanup_old_tasks(older_than_hours=24)

asyncio.create_task(cleanup_task())
```

### 6. 监控和告警

```python
async def monitor_task():
    while manager.is_running():
        stats = manager.get_statistics()
        
        # 检查成本告警
        cost = stats['cost']['total']
        if cost['percentage'] > 80:
            send_alert(f"成本预警: {cost['percentage']:.0f}%")
        
        # 检查失败率
        perf = stats['performance']
        if perf['success_rate'] < 90:
            send_alert(f"成功率过低: {perf['success_rate']:.1f}%")
        
        await asyncio.sleep(60)

asyncio.create_task(monitor_task())
```

## 故障排除

### 问题 1: 任务一直处于 QUEUED 状态

**原因**: 
- 管理器未启动
- 管理器已暂停
- 达到并发限制

**解决**:
```python
# 检查管理器状态
if not manager.is_running():
    await manager.start()

if manager.is_paused():
    manager.resume()

# 检查并发设置
stats = manager.get_statistics()
print(f"运行中: {stats['concurrency']['running_tasks']}")
print(f"最大并发: {stats['concurrency']['max_concurrent']}")
```

### 问题 2: 任务频繁失败

**原因**:
- API 密钥无效
- 网络问题
- 速率限制过严

**解决**:
```python
# 增加重试次数和延迟
await manager.submit_task(
    task_type=TaskType.REPOSITORY_ANALYSIS,
    data={...},
    config=TaskConfig(
        max_retries=5,
        retry_delay=2.0
    )
)

# 放宽速率限制
manager.adjust_settings(requests_per_minute=30)
```

### 问题 3: 预算耗尽

**原因**:
- 任务消耗超出预期
- 预算设置过低

**解决**:
```python
# 调整预算限制
manager.adjust_settings(
    budget_limit=200.0,
    daily_limit=20.0
)

# 或重置成本统计
manager.cost_controller.reset_total_cost()
```

## API 参考

完整的 API 文档请参考源代码注释：
- `services/task_queue.py` - 任务队列核心组件
- `services/ai_task_manager.py` - AI 任务管理器

## 许可证

MIT License

## 支持

如有问题或建议，请提交 Issue。
