# 错误处理系统使用指南

> GitHub Stars Manager 统一错误处理与用户反馈系统

## 📚 文档结构

```
error_handling_guide.md              # 完整的错误处理指南（推荐阅读）
services/
├── error_handler.py                  # 核心错误处理工具
├── error_handler_examples.py         # 详细使用示例
├── test_error_handler.py             # 快速测试脚本
└── logs/                             # 日志输出目录
    ├── app_YYYYMMDD.log              # 所有日志
    └── error_YYYYMMDD.log            # 仅错误日志
```

## 🚀 快速开始

### 1. 基础使用

```python
from services.error_handler import (
    logger,
    ValidationError,
    AuthenticationError,
    ErrorHandler
)

# 记录日志
logger.info("用户登录", user_id=123)
logger.error("登录失败", reason="invalid_token")

# 抛出异常
if not token:
    raise ValidationError("Token 不能为空", field="token")

# 处理错误
try:
    result = some_operation()
except Exception as e:
    ErrorHandler.showError(e)
```

### 2. 使用装饰器

```python
from services.error_handler import handle_errors, retry_on_error, measure_performance

# 错误处理装饰器
@handle_errors(error_message="操作失败", category=ErrorCategory.DATABASE)
def save_repository(repo_data):
    # 自动捕获并记录错误
    return db.save(repo_data)

# 重试装饰器
@retry_on_error(max_attempts=3, delay_seconds=1, backoff=True)
def fetch_from_github(url):
    # 失败时自动重试
    return requests.get(url)

# 性能监控装饰器
@measure_performance
def sync_repositories():
    # 自动记录执行时间
    pass
```

### 3. 熔断器保护

```python
from services.error_handler import CircuitBreaker

# 创建熔断器
github_circuit = CircuitBreaker(
    failure_threshold=5,      # 失败5次后熔断
    success_threshold=2,       # 成功2次后恢复
    timeout_seconds=60,        # 熔断60秒后尝试恢复
    name="GitHubAPI"
)

# 使用熔断器
try:
    result = github_circuit.call(fetch_github_data, token)
except Exception as e:
    logger.error("熔断器已开启", error=str(e))
```

## 📖 核心功能

### 异常类型

| 异常类 | 用途 | HTTP状态码 |
|--------|------|-----------|
| `ValidationError` | 验证错误 | 400 |
| `AuthenticationError` | 认证错误 | 401 |
| `PermissionError` | 权限错误 | 403 |
| `NotFoundError` | 资源不存在 | 404 |
| `RateLimitError` | 速率限制 | 429 |
| `DatabaseError` | 数据库错误 | 500 |
| `NetworkError` | 网络错误 | 502 |
| `GitHubAPIError` | GitHub API错误 | 502 |
| `AIServiceError` | AI服务错误 | 502 |

### 装饰器

| 装饰器 | 功能 | 参数 |
|--------|------|------|
| `@handle_errors` | 统一错误处理 | error_message, log_error, raise_error, category |
| `@retry_on_error` | 自动重试 | max_attempts, delay_seconds, backoff |
| `@measure_performance` | 性能监控 | 无 |

### 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| `DEBUG` | 调试信息 | `logger.debug("查询参数", params=query)` |
| `INFO` | 一般信息 | `logger.info("同步完成", count=100)` |
| `WARNING` | 警告信息 | `logger.warning("API接近限制", calls=4500)` |
| `ERROR` | 错误信息 | `logger.error("保存失败", error=str(e))` |
| `CRITICAL` | 严重错误 | `logger.critical("数据库崩溃")` |

## 🧪 测试

运行快速测试脚本：

```bash
cd services
python test_error_handler.py
```

测试包括：
- ✅ 基础异常测试
- ✅ 装饰器功能测试
- ✅ 重试机制测试
- ✅ 熔断器测试
- ✅ 错误处理工具测试
- ✅ 日志功能测试

## 📝 前端集成

### React 错误边界

```typescript
import { ErrorBoundary } from '@/components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <YourApp />
    </ErrorBoundary>
  );
}
```

### API 错误处理

```typescript
import { ErrorHandler } from '@/services/errorHandler';

try {
  const data = await repositoryAPI.getAll();
} catch (error) {
  ErrorHandler.showError(error, '获取仓库列表失败');
}
```

### Toast 通知

```typescript
import { toast } from '@/hooks/use-toast';

// 成功提示
toast({
  title: "操作成功",
  description: "仓库已添加到收藏",
});

// 错误提示
toast({
  title: "操作失败",
  description: error.message,
  variant: "destructive",
});
```

## 🎯 最佳实践

### ✅ 推荐做法

1. **始终使用具体的异常类型**
   ```python
   # ✅ 好
   raise ValidationError("邮箱格式不正确", field="email")
   
   # ❌ 差
   raise Exception("邮箱格式不正确")
   ```

2. **记录足够的上下文信息**
   ```python
   # ✅ 好
   logger.error("同步失败", user_id=user.id, repo_count=len(repos))
   
   # ❌ 差
   logger.error("同步失败")
   ```

3. **为关键操作添加重试**
   ```python
   @retry_on_error(max_attempts=3)
   def sync_from_github():
       pass
   ```

4. **使用熔断器保护外部服务**
   ```python
   result = circuit_breaker.call(external_api_call)
   ```

### ❌ 避免的做法

1. **不要吞掉异常**
   ```python
   # ❌ 错误
   try:
       operation()
   except:
       pass
   ```

2. **不要暴露敏感信息**
   ```python
   # ❌ 错误
   logger.error(f"数据库密码: {db_password}")
   ```

3. **不要在循环中记录大量日志**
   ```python
   # ❌ 错误
   for item in items:
       logger.info(f"处理 {item}")  # 太多日志
   ```

## 📊 错误统计

```python
from services.error_handler import error_reporter

# 获取错误统计
stats = error_reporter.get_error_statistics()
print(f"总错误数: {stats['total']}")
print(f"按分类: {stats['by_category']}")
print(f"按错误码: {stats['by_code']}")
```

## 🔧 配置

### 日志级别配置

```python
from services.error_handler import AppLogger

# 自定义日志配置
logger = AppLogger(
    name="MyApp",
    log_dir="logs",
    console_level="INFO",    # 控制台日志级别
    file_level="DEBUG"       # 文件日志级别
)
```

### 熔断器配置

```python
circuit = CircuitBreaker(
    failure_threshold=5,      # 失败阈值
    success_threshold=2,       # 成功阈值
    timeout_seconds=60,        # 超时时间
    name="MyService"
)
```

## 📖 完整文档

详细文档请查看：
- **[error_handling_guide.md](error_handling_guide.md)** - 完整的错误处理指南
- **[error_handler_examples.py](services/error_handler_examples.py)** - 10个完整示例
- **[error_handler.py](services/error_handler.py)** - 源代码和注释

## 🤝 常见问题

### Q: 如何自定义错误码？
A: 在 `error_handling_guide.md` 中查看错误码规范，遵循 `[系统模块][错误类型][具体错误]` 格式。

### Q: 日志文件在哪里？
A: 默认在 `services/logs/` 目录，按日期自动分割。

### Q: 如何集成到现有代码？
A: 参考 `error_handler_examples.py` 中的综合应用示例。

### Q: 前端如何处理错误？
A: 查看 `error_handling_guide.md` 的"前端错误处理"部分。

### Q: 如何监控错误？
A: 使用 `error_reporter` 收集错误统计，或集成第三方监控服务。

## 📞 支持

遇到问题？
1. 查看 [error_handling_guide.md](error_handling_guide.md) 完整文档
2. 运行 `python test_error_handler.py` 验证功能
3. 查看示例代码 `error_handler_examples.py`

---

**版本**: 1.0  
**更新时间**: 2025-10-31  
**维护者**: GitHub Stars Manager Team
