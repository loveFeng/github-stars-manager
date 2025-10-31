# GitHubStarsManager 服务包

基于 [GitHubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager) 项目实现的完整服务解决方案，包含 GitHub API 集成服务和 AI 能力。

## 🌟 核心服务

### 1. GitHub API 集成服务
- ✅ **完整的 GitHub API 客户端** - 封装所有 GitHub REST API
- ✅ **星标仓库管理** - 自动同步和分类管理
- ✅ **发布跟踪系统** - Release 信息获取和更新通知
- ✅ **智能资产过滤** - 根据文件名自动识别平台资产
- ✅ **速率限制处理** - 自动处理 API 调用限制
- ✅ **数据缓存导出** - 智能缓存和数据导出功能

### 2. AI 集成服务
- ✅ **OpenAI 兼容接口** - 支持 GPT 系列模型和嵌入模型
- ✅ **仓库摘要生成** - 自动分析 GitHub 仓库并生成结构化摘要
- ✅ **自动分类标签** - 智能文本分类和标签生成
- ✅ **语义搜索** - 基于嵌入向量的语义搜索
- ✅ **批量处理** - 高效的异步任务处理
- ✅ **成本控制** - 实时监控 API 使用成本

### 3. 星标仓库自动同步服务 🆕
- ✅ **定时同步调度器** - 支持多种同步间隔（每30分钟、每小时、每6小时等）
- ✅ **智能增量同步** - 仅更新变更的仓库，节省API配额
- ✅ **冲突解决策略** - 本地修改 vs 远程更新的智能处理
- ✅ **同步状态追踪** - 实时进度反馈和状态监控
- ✅ **错误处理和重试** - 自动重试机制，确保同步可靠性
- ✅ **同步历史记录** - 完整的同步日志和统计分析
- ✅ **手动同步触发** - 支持随时手动触发同步任务

### 4. 数据备份服务
- ✅ **WebDAV 集成** - 支持坚果云、Nextcloud 等服务
- ✅ **自动备份** - 定时数据备份和同步
- ✅ **增量备份** - 高效的增量备份机制

## 🚀 快速开始

### GitHub API 服务

```python
from services import GitHubService, AIConfig

# 初始化 GitHub 服务
github_service = GitHubService(
    token="your-github-token",
    ai_config=AIConfig(
        id="openai",
        name="OpenAI",
        api_url="https://api.openai.com/v1/chat/completions",
        api_key="your-openai-key"
    )
)

# 认证并同步仓库
user = github_service.authenticate()
sync_result = github_service.sync_starred_repos()

print(f"同步了 {sync_result.synced_repos} 个仓库")
```

### 自动同步服务

```python
from services import GitHubService, SyncService, SyncScheduler
from services.sync_service import DatabaseManager, SyncConfig, SyncMode, ConflictStrategy
from services.sync_scheduler import SchedulerConfig, ScheduleInterval

# 初始化服务
github_service = GitHubService(token="your-github-token")
db_manager = DatabaseManager(db_path="./data/github_stars.db")

# 配置同步服务
sync_config = SyncConfig(
    mode=SyncMode.SMART,
    conflict_strategy=ConflictStrategy.MERGE
)
sync_service = SyncService(github_service, db_manager, sync_config)

# 配置调度器（每6小时自动同步）
scheduler_config = SchedulerConfig(
    enabled=True,
    interval=ScheduleInterval.HOURS_6,
    sync_on_startup=True
)
scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)

# 启动调度器
scheduler.start()

# 获取同步状态
status = scheduler.get_status()
print(f"调度器状态: {status.to_dict()}")
```

### AI 服务

```python
import asyncio
from services import AIService, Priority

async def main():
    ai_service = AIService(
        api_key="your-openai-api-key",
        cost_budget=100.0
    )
    
    # 生成文本
    response = await ai_service.ai_client.generate_text(
        prompt="解释什么是机器学习",
        model=ModelType.GPT_3_5_TURBO
    )
    
    if response.success:
        print(response.content)

asyncio.run(main())
```

## 功能特性

### GitHub API 服务特性

#### 🔐 认证与管理
- Personal Access Token 认证
- 用户信息获取
- 权限验证

#### 📦 仓库管理
- 星标仓库同步
- 仓库信息获取
- 搜索和过滤
- 自定义分类

#### 🏷️ AI 集成
- 仓库摘要生成
- 自动标签生成
- 智能分类
- 批量处理

#### 📈 发布跟踪
- Release 信息获取
- 发布更新检测
- 资产下载管理
- 平台识别

#### 🔍 智能搜索
- 多维度搜索
- 语义搜索
- 过滤器管理
- 统计分析

#### ⚡ 自动同步功能
- **定时同步调度器**: 支持多种同步间隔（手动/30分钟/1小时/6小时/12小时/每天/每周）
- **智能增量同步**: 自动检测变更，仅同步更新的仓库
- **冲突解决策略**: 支持保留本地/使用远程/智能合并/询问用户四种策略
- **进度追踪**: 实时监控同步进度、预估剩余时间
- **错误处理**: 自动重试机制，最多可配置5次重试
- **同步历史**: 完整的同步日志和统计分析
- **静默时段**: 可配置静默时段避免在指定时间同步
- **事件回调**: 支持同步开始、完成、错误的事件回调

详细文档请参考: [SYNC_README.md](./SYNC_README.md)

### 🚀 核心功能
- **OpenAI兼容API客户端** - 支持GPT系列模型和嵌入模型
- **仓库摘要生成** - 自动分析GitHub仓库并生成结构化摘要
- **自动分类和标签** - 智能文本分类和标签生成
- **语义搜索向量化** - 基于嵌入向量的语义搜索
- **批量处理任务队列** - 高效的异步任务处理
- **成本控制和错误处理** - 完善的资源管理和错误恢复

### 🛡️ 企业级特性
- **速率限制** - 内置API调用频率控制
- **缓存机制** - 减少重复请求，节省成本
- **重试机制** - 自动处理临时失败
- **成本监控** - 实时跟踪API使用成本
- **健康检查** - 服务状态监控
- **任务状态追踪** - 完整的任务生命周期管理

## 快速开始

### 安装依赖

```bash
pip install aiohttp numpy
```

### 基本使用

```python
import asyncio
from services import AIService, Priority

async def main():
    # 初始化AI服务
    ai_service = AIService(
        api_key="your-openai-api-key",
        cost_budget=100.0,  # 设置成本预算
        rate_limit=60       # 每分钟请求限制
    )
    
    # 健康检查
    if await ai_service.health_check():
        print("AI服务连接成功")
    
    # 生成文本
    response = await ai_service.ai_client.generate_text(
        prompt="解释什么是机器学习",
        model=ModelType.GPT_3_5_TURBO,
        max_tokens=500
    )
    
    if response.success:
        print(response.content)

asyncio.run(main())
```

### GitHub API 服务详细功能

#### 1. 仓库同步和管理

```python
# 同步所有星标仓库
sync_result = github_service.sync_starred_repos()

# 搜索和过滤
results = github_service.search_repos(
    repos, 
    query="Python",
    language="Python",
    topic="machine-learning"
)

# 生成 AI 摘要
summary = github_service.generate_ai_summary(repo)

# 批量生成摘要
result = github_service.bulk_generate_ai_summary(repos, max_workers=5)
```

#### 2. 发布跟踪

```python
# 订阅仓库发布
github_service.subscribe_repo("microsoft", "vscode")
github_service.subscribe_repo("facebook", "react")

# 检查发布更新
updates = github_service.check_release_updates()

# 获取发布资产
assets = github_service.get_repo_assets("microsoft", "vscode")
```

#### 3. 智能过滤

```python
# 创建平台过滤器
windows_filter = github_service.add_asset_filter(
    "Windows 安装包", 
    ["exe", "msi", "win32", "win64"]
)

macos_filter = github_service.add_asset_filter(
    "macOS 安装包",
    ["dmg", "pkg", "mac", "osx"]
)

# 自动匹配资产
for asset in assets:
    if asset.matched_filters:
        print(f"{asset.asset_name}: {', '.join(asset.matched_filters)}")
```

#### 4. 数据统计

```python
# 获取仓库统计
stats = github_service.get_repository_stats(repos)

print(f"总仓库数: {stats['total_repos']}")
print(f"平均星标: {stats['avg_stars']:.1f}")
print(f"最流行语言: {stats['languages'][0]}")
print(f"最热门主题: {stats['topics'][0]}")
```

#### 5. 数据导出

```python
# 导出数据
json_file = github_service.export_data(repos, format="json")
csv_file = github_service.export_data(repos, format="csv")
```

#### 6. 速率限制监控

```python
# 获取 API 状态
rate_status = github_service.get_rate_limit_status()
print(f"剩余请求: {rate_status['remaining']}")
print(f"重置时间: {rate_status['reset_time']}")
```

#### 7. 缓存管理

```python
# 清理缓存
cleanup_result = github_service.cleanup_cache()
print(f"清理过期缓存: {cleanup_result['expired_cleaned']} 项")
```

### AI 服务详细功能

#### 1. 文本生成

```python
# 简单文本生成
response = await ai_service.ai_client.generate_text(
    prompt="写一个关于Python的简短介绍",
    model=ModelType.GPT_4,
    max_tokens=200,
    temperature=0.7,
    system_prompt="你是一个专业的技术写作助手"
)
```

### 2. 仓库分析

```python
# 直接分析
summary = await ai_service.analyze_repository(
    repo_info={
        "name": "awesome-python",
        "description": "A curated list of awesome Python resources",
        "language": "Python",
        "html_url": "https://github.com/vinta/awesome-python"
    },
    readme_content="# README content here...",
    file_structure="package/\nsrc/\ntests/"
)

print(f"仓库: {summary.repo_name}")
print(f"主要功能: {', '.join(summary.features)}")
print(f"技术栈: {', '.join(summary.technologies)}")

# 异步任务方式
task_id = ai_service.create_analysis_task(
    repo_info=repo_info,
    readme_content=readme,
    priority=Priority.HIGH,
    callback=lambda task: print(f"分析完成: {task.result}")
)

await ai_service.start_task_processor()
```

### 3. 语义搜索

```python
# 添加文档到搜索索引
await ai_service.add_to_search_index(
    content_id="doc1",
    content="Python是一种高级编程语言",
    metadata={"type": "language_info", "category": "programming"}
)

# 搜索相关文档
results = await ai_service.semantic_search(
    query="什么是编程语言",
    top_k=5,
    threshold=0.7
)

for result in results:
    print(f"相似度: {result['similarity']:.3f}")
    print(f"内容: {result['content']}")
```

### 4. 批量文本分类

```python
# 准备数据
texts = [
    "这部电影太棒了！剧情精彩",
    "今天的天气真好",
    "这个产品设计有问题"
]
categories = ["娱乐", "生活", "科技"]

# 批量分类
def progress_callback(progress, current, total):
    print(f"进度: {progress:.1%} ({current}/{total})")

results = await ai_service.batch_classify_texts(
    texts=texts,
    categories=categories,
    progress_callback=progress_callback
)

for result in results:
    print(f"文本: {result.text[:50]}...")
    print(f"分类: {result.primary_category} (置信度: {result.confidence:.2f})")
    print(f"标签: {', '.join(result.tags)}")
```

### 5. 任务队列管理

```python
# 创建多个任务
task_ids = []
for i in range(5):
    task_id = ai_service.create_analysis_task(
        repo_info={"name": f"repo-{i}", "description": f"Test repo {i}"},
        priority=Priority.MEDIUM
    )
    task_ids.append(task_id)

# 启动任务处理器
await ai_service.start_task_processor()

# 监控任务状态
while True:
    stats = ai_service.get_queue_stats()
    print(f"队列状态: {stats}")
    
    if stats["completed_tasks"] >= len(task_ids):
        break
    
    await asyncio.sleep(2)

# 获取任务结果
for task_id in task_ids:
    status = ai_service.get_task_status(task_id)
    print(f"任务 {task_id}: {status['status']}")
```

### 6. 成本控制

```python
# 设置成本预算
ai_service = AIService(
    api_key="your-api-key",
    cost_budget=50.0  # 50美元预算
)

# 查看使用统计
stats = ai_service.get_usage_stats()
print(f"当前成本: ${stats['total_cost']:.2f}")
print(f"剩余预算: ${stats['budget_remaining']:.2f}")
print(f"已用Token数: {stats['total_tokens']}")

# 重置统计
ai_service.ai_client.reset_usage_stats()

# 清空缓存
ai_service.ai_client.clear_cache()
```

## 配置选项

### APIConfig 参数

```python
config = APIConfig(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",  # OpenAI兼容的API地址
    timeout=30,                    # 请求超时时间(秒)
    max_retries=3,                 # 最大重试次数
    retry_delay=1.0,               # 重试延迟(秒)
    rate_limit=60,                 # 每分钟请求限制
    max_tokens=4000                # 最大Token数
)
```

### AI服务参数

```python
ai_service = AIService(
    api_key="your-api-key",
    cost_budget=100.0,             # 成本预算(美元)
    timeout=60,                    # 全局超时设置
    rate_limit=30                  # 全局限流设置
)
```

## 模型支持

### 文本生成模型
- `ModelType.GPT_3_5_TURBO` - GPT-3.5 Turbo (成本效益高)
- `ModelType.GPT_4` - GPT-4 (高质量)
- `ModelType.GPT_4_TURBO` - GPT-4 Turbo (最新)

### 嵌入模型
- `ModelType.TEXT_EMBEDDING_3_SMALL` - text-embedding-3-small (快速)
- `ModelType.TEXT_EMBEDDING_3_LARGE` - text-embedding-3-large (高精度)

## 成本估算

| 模型 | 输入成本 (1K tokens) | 输出成本 (1K tokens) |
|------|---------------------|---------------------|
| GPT-3.5 Turbo | $0.0015 | $0.002 |
| GPT-4 | $0.03 | $0.06 |
| GPT-4 Turbo | $0.01 | $0.03 |
| Embedding-3-Small | $0.02/1M tokens | - |
| Embedding-3-Large | $0.13/1M tokens | - |

## 错误处理

服务内置了完善的错误处理机制：

- **网络错误** - 自动重试，支持指数退避
- **配额超限** - 优雅降级，提示用户
- **成本超预算** - 立即停止，保护预算
- **超时处理** - 可配置的请求超时
- **任务失败** - 多次重试，自动恢复

## 最佳实践

### 1. 成本优化
```python
# 使用缓存避免重复请求
response = await ai_service.ai_client.generate_text(prompt)

# 监控成本使用
stats = ai_service.get_usage_stats()
if stats['total_cost'] > stats['cost_budget'] * 0.8:
    print("⚠️ 成本预算使用超过80%")
```

### 2. 性能优化
```python
# 批量处理提高效率
await ai_service.batch_classify_texts(texts, categories)

# 并行任务处理
await ai_service.start_task_processor()
for task_id in task_ids:
    ai_service.create_analysis_task(repo_info, priority=Priority.HIGH)
```

### 3. 可靠性保证
```python
# 健康检查
if not await ai_service.health_check():
    raise Exception("AI服务不可用")

# 任务状态监控
status = ai_service.get_task_status(task_id)
if status['status'] == 'failed':
    # 处理失败任务
    pass
```

## 完整示例

### GitHub API 服务示例

参考 `services/github_demo.py` 文件获取完整使用示例：

```bash
# 运行完整演示
python services/github_demo.py
```

示例包括：
- 基本认证和用户信息获取
- 星标仓库同步流程
- AI 摘要生成演示
- 发布跟踪和资产过滤
- 搜索和统计分析
- 速率限制监控
- 缓存管理
- 数据导出

### AI 服务示例

参考 `services/examples.py` 文件获取完整使用示例，包括：

- 基本文本生成
- 仓库分析流程
- 语义搜索实现
- 批量处理示例
- 成本控制演示
- 任务队列管理

## 注意事项

### GitHub API 服务注意事项

1. **Token 安全** - 不要将 GitHub Token 提交到版本控制系统
2. **速率限制** - 注意 GitHub API 的速率限制（5000请求/小时）
3. **错误处理** - 始终使用 try-catch 处理可能的 API 错误
4. **缓存清理** - 定期清理缓存文件，避免占用过多磁盘空间
5. **数据备份** - 重要数据建议定期导出备份

### AI 服务注意事项

1. **API密钥安全** - 不要在代码中硬编码API密钥，使用环境变量
2. **成本控制** - 设置合理的成本预算，避免意外支出
3. **错误处理** - 在生产环境中增加适当的错误处理和日志记录
4. **限流设置** - 根据API限制调整请求频率
5. **缓存管理** - 定期清理缓存以释放内存

## 许可证

MIT License

## 致谢

感谢 [GitHubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager) 项目提供的设计灵感和功能参考。本服务包基于该项目的核心功能需求实现，提供了完整的 GitHub API 集成解决方案。