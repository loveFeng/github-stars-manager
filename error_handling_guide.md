# 错误处理和用户反馈指南

> GitHub Stars Manager 错误处理与用户反馈最佳实践指南  
> 版本：1.0  
> 最后更新：2025-10-31

## 目录

1. [错误处理体系](#错误处理体系)
2. [前端错误处理](#前端错误处理)
3. [后端错误处理](#后端错误处理)
4. [用户反馈机制](#用户反馈机制)
5. [错误日志记录](#错误日志记录)
6. [错误监控上报](#错误监控上报)
7. [容错设计](#容错设计)
8. [最佳实践](#最佳实践)

---

## 错误处理体系

### 错误分类

我们将错误分为以下几个层级：

#### 1. 致命错误（Critical）
- **影响范围**：导致应用崩溃或核心功能无法使用
- **示例**：数据库连接失败、内存溢出
- **处理策略**：立即记录、通知管理员、显示友好的错误页面
- **用户体验**：提供明确的错误信息和解决建议

#### 2. 严重错误（Error）
- **影响范围**：功能不可用，但不影响其他功能
- **示例**：API调用失败、文件读写错误
- **处理策略**：记录日志、显示错误提示、提供重试选项
- **用户体验**：Toast通知 + 重试按钮

#### 3. 警告（Warning）
- **影响范围**：部分功能受限或性能下降
- **示例**：GitHub API速率限制、网络延迟
- **处理策略**：记录日志、显示警告提示
- **用户体验**：温和的提示信息

#### 4. 信息（Info）
- **影响范围**：不影响功能，仅供参考
- **示例**：同步完成、操作成功
- **处理策略**：简单记录、可选的提示
- **用户体验**：简短的成功提示

### 错误码规范

使用统一的错误码体系：

```
[系统模块][错误类型][具体错误]
```

**系统模块代码**：
- `01` - 认证模块（Auth）
- `02` - 仓库管理（Repository）
- `03` - Release管理
- `04` - AI服务
- `05` - 备份服务
- `06` - 同步服务
- `07` - 数据库
- `08` - 网络请求
- `09` - 文件系统

**错误类型代码**：
- `1` - 验证错误（Validation）
- `2` - 权限错误（Permission）
- `3` - 资源不存在（NotFound）
- `4` - 业务逻辑错误（Business）
- `5` - 系统错误（System）

**示例**：
- `011001` - 认证模块-验证错误-Token无效
- `021003` - 仓库管理-资源不存在-仓库不存在
- `081005` - 网络请求-系统错误-请求超时

---

## 前端错误处理

### 1. React 错误边界（Error Boundary）

在应用顶层使用错误边界捕获未处理的React组件错误：

```typescript
// components/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // 记录错误到日志服务
    console.error('React Error Boundary caught:', error, errorInfo);
    
    // 发送到错误监控服务
    this.reportError(error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });
  }

  reportError(error: Error, errorInfo: React.ErrorInfo) {
    // TODO: 集成错误监控服务（如 Sentry）
    if (window.errorReporter) {
      window.errorReporter.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-8 h-8 text-red-500" />
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                应用出错了
              </h1>
            </div>
            
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              很抱歉，应用遇到了一个意外错误。您可以尝试刷新页面或联系技术支持。
            </p>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded">
                <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300">
                  错误详情（开发模式）
                </summary>
                <pre className="mt-2 text-xs text-red-600 dark:text-red-400 overflow-auto">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
            
            <div className="flex gap-3">
              <button
                onClick={this.handleReload}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                刷新页面
              </button>
              <button
                onClick={this.handleReset}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
              >
                重置状态
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### 2. API 错误处理

创建统一的 API 错误处理工具：

```typescript
// services/errorHandler.ts
import { toast } from '@/hooks/use-toast';
import { AxiosError } from 'axios';

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

export class ErrorHandler {
  /**
   * 处理 API 错误
   */
  static handleApiError(error: unknown): ApiError {
    if (error instanceof AxiosError) {
      const response = error.response;
      
      if (!response) {
        // 网络错误
        return {
          code: '081001',
          message: '网络连接失败，请检查您的网络设置',
          timestamp: new Date().toISOString(),
        };
      }

      // 根据状态码处理
      switch (response.status) {
        case 400:
          return {
            code: '011001',
            message: response.data?.message || '请求参数错误',
            details: response.data?.details,
            timestamp: new Date().toISOString(),
          };
        
        case 401:
          // 认证失败，跳转登录
          localStorage.removeItem('github_token');
          window.location.href = '/login';
          return {
            code: '011002',
            message: '认证已过期，请重新登录',
            timestamp: new Date().toISOString(),
          };
        
        case 403:
          return {
            code: '012001',
            message: '您没有权限执行此操作',
            timestamp: new Date().toISOString(),
          };
        
        case 404:
          return {
            code: '021003',
            message: response.data?.message || '请求的资源不存在',
            timestamp: new Date().toISOString(),
          };
        
        case 429:
          return {
            code: '081002',
            message: 'API 调用频率过高，请稍后再试',
            details: response.headers['x-ratelimit-reset'],
            timestamp: new Date().toISOString(),
          };
        
        case 500:
        case 502:
        case 503:
        case 504:
          return {
            code: '081005',
            message: '服务器错误，请稍后重试',
            timestamp: new Date().toISOString(),
          };
        
        default:
          return {
            code: '081000',
            message: response.data?.message || '未知错误',
            details: response.data,
            timestamp: new Date().toISOString(),
          };
      }
    }

    // 其他类型的错误
    if (error instanceof Error) {
      return {
        code: '091000',
        message: error.message,
        timestamp: new Date().toISOString(),
      };
    }

    return {
      code: '099999',
      message: '未知错误',
      details: error,
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * 显示错误提示
   */
  static showError(error: unknown, title = '操作失败') {
    const apiError = this.handleApiError(error);
    
    toast({
      title,
      description: apiError.message,
      variant: 'destructive',
    });

    // 记录到日志
    this.logError(apiError);
  }

  /**
   * 记录错误日志
   */
  static logError(error: ApiError) {
    console.error('[Error Log]', {
      ...error,
      userAgent: navigator.userAgent,
      url: window.location.href,
    });

    // TODO: 发送到日志服务器
  }

  /**
   * 包装异步操作，自动处理错误
   */
  static async tryAsync<T>(
    operation: () => Promise<T>,
    options?: {
      errorMessage?: string;
      showError?: boolean;
      onError?: (error: ApiError) => void;
    }
  ): Promise<T | null> {
    try {
      return await operation();
    } catch (error) {
      const apiError = this.handleApiError(error);
      
      if (options?.showError !== false) {
        this.showError(error, options?.errorMessage);
      }

      if (options?.onError) {
        options.onError(apiError);
      }

      return null;
    }
  }
}

// GitHub 特定错误处理
export class GitHubErrorHandler {
  static handleGitHubError(error: any) {
    if (error.message?.includes('rate limit')) {
      toast({
        title: 'API 速率限制',
        description: 'GitHub API 调用次数已达上限，请稍后再试',
        variant: 'destructive',
      });
      return;
    }

    if (error.message?.includes('Not Found')) {
      toast({
        title: '仓库不存在',
        description: '请求的仓库不存在或已被删除',
        variant: 'destructive',
      });
      return;
    }

    if (error.message?.includes('Bad credentials')) {
      toast({
        title: 'Token 无效',
        description: '您的 GitHub Token 无效或已过期，请重新登录',
        variant: 'destructive',
      });
      localStorage.removeItem('github_token');
      window.location.href = '/login';
      return;
    }

    // 默认错误处理
    ErrorHandler.showError(error);
  }
}
```

### 3. 表单验证错误

```typescript
// utils/validation.ts
import { z } from 'zod';

export class ValidationError extends Error {
  constructor(
    message: string,
    public field?: string,
    public code = 'VALIDATION_ERROR'
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * 验证 GitHub Token 格式
 */
export function validateGitHubToken(token: string): boolean {
  if (!token || token.trim().length === 0) {
    throw new ValidationError('Token 不能为空', 'token');
  }

  // GitHub Personal Access Token 格式验证
  if (!/^(ghp_|github_pat_)[a-zA-Z0-9]{36,}$/.test(token)) {
    throw new ValidationError(
      'Token 格式不正确，请检查您的 GitHub Personal Access Token',
      'token'
    );
  }

  return true;
}

/**
 * 显示表单验证错误
 */
export function showValidationError(error: z.ZodError) {
  const firstError = error.errors[0];
  toast({
    title: '表单验证失败',
    description: firstError.message,
    variant: 'destructive',
  });
}
```

### 4. 异步操作包装

```typescript
// hooks/useAsyncOperation.ts
import { useState } from 'react';
import { ErrorHandler } from '@/services/errorHandler';

export function useAsyncOperation<T>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = async (
    operation: () => Promise<T>,
    options?: {
      successMessage?: string;
      errorMessage?: string;
      onSuccess?: (result: T) => void;
      onError?: () => void;
    }
  ) => {
    setLoading(true);
    setError(null);

    try {
      const result = await operation();
      
      if (options?.successMessage) {
        toast({
          title: '操作成功',
          description: options.successMessage,
        });
      }

      options?.onSuccess?.(result);
      return result;
    } catch (err) {
      const errorMessage = options?.errorMessage || '操作失败';
      ErrorHandler.showError(err, errorMessage);
      setError(errorMessage);
      options?.onError?.();
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { loading, error, execute };
}
```

---

## 后端错误处理

### 1. Python 异常体系

```python
# services/exceptions.py

class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: dict = None,
        http_status: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.http_status = http_status
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ValidationError(AppException):
    """验证错误"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {},
            http_status=400,
            **kwargs
        )


class AuthenticationError(AppException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            http_status=401,
            **kwargs
        )


class PermissionError(AppException):
    """权限错误"""
    
    def __init__(self, message: str = "权限不足", **kwargs):
        super().__init__(
            message=message,
            code="PERMISSION_ERROR",
            http_status=403,
            **kwargs
        )


class NotFoundError(AppException):
    """资源不存在错误"""
    
    def __init__(self, resource: str = "资源", **kwargs):
        super().__init__(
            message=f"{resource}不存在",
            code="NOT_FOUND",
            http_status=404,
            **kwargs
        )


class RateLimitError(AppException):
    """速率限制错误"""
    
    def __init__(self, retry_after: int = None, **kwargs):
        super().__init__(
            message="请求过于频繁，请稍后再试",
            code="RATE_LIMIT",
            details={"retry_after": retry_after} if retry_after else {},
            http_status=429,
            **kwargs
        )


class ExternalServiceError(AppException):
    """外部服务错误"""
    
    def __init__(self, service_name: str, original_error: str = None, **kwargs):
        super().__init__(
            message=f"{service_name}服务调用失败",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service_name, "original_error": original_error},
            http_status=502,
            **kwargs
        )
```

### 2. 数据库异常处理

```python
# services/db_error_handler.py
import sqlite3
from typing import Any, Callable, TypeVar

T = TypeVar('T')

class DatabaseError(AppException):
    """数据库错误"""
    
    def __init__(self, message: str, query: str = None, **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"query": query} if query else {},
            http_status=500,
            **kwargs
        )


def handle_db_errors(func: Callable[..., T]) -> Callable[..., T]:
    """数据库操作装饰器"""
    
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValidationError("数据已存在，请勿重复添加")
            elif "FOREIGN KEY constraint failed" in str(e):
                raise ValidationError("关联的数据不存在")
            else:
                raise DatabaseError(f"数据完整性错误: {str(e)}")
        except sqlite3.OperationalError as e:
            raise DatabaseError(f"数据库操作错误: {str(e)}")
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected database error: {e}", exc_info=True)
            raise DatabaseError("数据库操作失败，请稍后重试")
    
    return wrapper
```

---

## 用户反馈机制

### 1. Toast 通知

使用 shadcn/ui 的 Toast 组件提供即时反馈：

```typescript
// 成功提示
toast({
  title: "操作成功",
  description: "仓库已成功添加到收藏",
});

// 错误提示
toast({
  title: "操作失败",
  description: "无法连接到 GitHub API",
  variant: "destructive",
});

// 警告提示
toast({
  title: "注意",
  description: "您的 API 调用次数即将达到限制",
  variant: "warning",
});

// 信息提示
toast({
  title: "提示",
  description: "同步将在后台进行",
});
```

### 2. Loading 状态

```typescript
// components/LoadingSpinner.tsx
export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex items-center justify-center">
      <div
        className={`${sizeClasses[size]} border-4 border-gray-300 border-t-blue-600 rounded-full animate-spin`}
      />
    </div>
  );
}

// 按钮 Loading 状态
<button disabled={loading} className="...">
  {loading ? (
    <>
      <LoadingSpinner size="sm" />
      <span>处理中...</span>
    </>
  ) : (
    '提交'
  )}
</button>
```

### 3. Progress 进度条

```typescript
// components/ProgressBar.tsx
import { Progress } from '@/components/ui/progress';

interface ProgressBarProps {
  current: number;
  total: number;
  label?: string;
}

export function ProgressBar({ current, total, label }: ProgressBarProps) {
  const percentage = Math.round((current / total) * 100);

  return (
    <div className="space-y-2">
      {label && (
        <div className="flex justify-between text-sm text-gray-600">
          <span>{label}</span>
          <span>{current} / {total}</span>
        </div>
      )}
      <Progress value={percentage} />
      <p className="text-xs text-center text-gray-500">{percentage}%</p>
    </div>
  );
}

// 使用示例：同步进度
function SyncProgress() {
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(100);

  return (
    <ProgressBar
      current={current}
      total={total}
      label="正在同步仓库..."
    />
  );
}
```

### 4. 确认对话框

```typescript
// components/ConfirmDialog.tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'destructive';
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  confirmText = '确认',
  cancelText = '取消',
  variant = 'default',
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{cancelText}</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className={variant === 'destructive' ? 'bg-red-600 hover:bg-red-700' : ''}
          >
            {confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// 使用示例
function DeleteButton({ repositoryId }: { repositoryId: number }) {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleDelete = async () => {
    await repositoryAPI.delete(repositoryId);
    toast({ title: '删除成功' });
    setShowConfirm(false);
  };

  return (
    <>
      <button onClick={() => setShowConfirm(true)}>删除</button>
      <ConfirmDialog
        open={showConfirm}
        onOpenChange={setShowConfirm}
        title="确认删除"
        description="此操作无法撤销，确定要删除这个仓库吗？"
        onConfirm={handleDelete}
        variant="destructive"
      />
    </>
  );
}
```

### 5. 撤销操作

```typescript
// hooks/useUndoable.ts
import { useState } from 'react';

interface UndoableState<T> {
  present: T;
  past: T[];
  future: T[];
}

export function useUndoable<T>(initialState: T) {
  const [state, setState] = useState<UndoableState<T>>({
    present: initialState,
    past: [],
    future: [],
  });

  const set = (newState: T) => {
    setState({
      present: newState,
      past: [...state.past, state.present],
      future: [],
    });
  };

  const undo = () => {
    if (state.past.length === 0) return;

    const previous = state.past[state.past.length - 1];
    const newPast = state.past.slice(0, state.past.length - 1);

    setState({
      present: previous,
      past: newPast,
      future: [state.present, ...state.future],
    });

    toast({
      title: '已撤销',
      description: '操作已撤销',
    });
  };

  const redo = () => {
    if (state.future.length === 0) return;

    const next = state.future[0];
    const newFuture = state.future.slice(1);

    setState({
      present: next,
      past: [...state.past, state.present],
      future: newFuture,
    });

    toast({
      title: '已重做',
      description: '操作已重做',
    });
  };

  return {
    state: state.present,
    set,
    undo,
    redo,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  };
}
```

---

## 错误日志记录

### 1. 日志级别

```python
# services/logger.py
import logging
from datetime import datetime
from pathlib import Path

# 日志级别
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

class AppLogger:
    def __init__(self, name: str, log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 创建日志目录
        Path(log_dir).mkdir(exist_ok=True)
        
        # 文件处理器 - 所有日志
        file_handler = logging.FileHandler(
            f"{log_dir}/app_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 文件处理器 - 仅错误
        error_handler = logging.FileHandler(
            f"{log_dir}/error_{datetime.now().strftime('%Y%m%d')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info=False, **kwargs):
        self.logger.error(message, exc_info=exc_info, extra=kwargs)

    def critical(self, message: str, exc_info=True, **kwargs):
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)

# 全局日志实例
logger = AppLogger("GitHubStarsManager")
```

### 2. 结构化日志

```python
# 记录操作日志
logger.info(
    "Repository synced",
    user_id=user.id,
    repository_count=len(repositories),
    duration_ms=elapsed_time
)

# 记录错误日志
logger.error(
    "GitHub API request failed",
    url=request_url,
    status_code=response.status_code,
    error=str(error),
    exc_info=True
)
```

---

## 错误监控上报

### 1. 前端错误监控

```typescript
// services/errorReporter.ts

interface ErrorReport {
  message: string;
  stack?: string;
  url: string;
  userAgent: string;
  timestamp: string;
  userId?: string;
  additionalData?: any;
}

class ErrorReporter {
  private endpoint = '/api/errors';
  private userId?: string;

  setUserId(userId: string) {
    this.userId = userId;
  }

  async report(error: Error, additionalData?: any) {
    const report: ErrorReport = {
      message: error.message,
      stack: error.stack,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      userId: this.userId,
      additionalData,
    };

    try {
      await fetch(this.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(report),
      });
    } catch (err) {
      console.error('Failed to report error:', err);
    }
  }

  // 监听全局错误
  init() {
    window.addEventListener('error', (event) => {
      this.report(event.error, {
        type: 'uncaught',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
    });

    window.addEventListener('unhandledrejection', (event) => {
      this.report(
        new Error(event.reason),
        { type: 'unhandledRejection' }
      );
    });
  }
}

export const errorReporter = new ErrorReporter();

// 在应用启动时初始化
errorReporter.init();
```

### 2. 性能监控

```typescript
// services/performanceMonitor.ts

export class PerformanceMonitor {
  static logPageLoad() {
    window.addEventListener('load', () => {
      const perfData = window.performance.timing;
      const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
      
      console.log('Page Load Metrics:', {
        pageLoadTime,
        domReady: perfData.domContentLoadedEventEnd - perfData.navigationStart,
        resourcesLoaded: perfData.loadEventEnd - perfData.domContentLoadedEventEnd,
      });
    });
  }

  static measureApiCall(name: string, duration: number) {
    if (duration > 5000) {
      console.warn(`Slow API call detected: ${name} took ${duration}ms`);
    }
  }
}
```

---

## 容错设计

### 1. 重试机制

```typescript
// utils/retry.ts

interface RetryOptions {
  maxAttempts?: number;
  delayMs?: number;
  backoff?: boolean;
  onRetry?: (attempt: number, error: any) => void;
}

export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    delayMs = 1000,
    backoff = true,
    onRetry,
  } = options;

  let lastError: any;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt < maxAttempts) {
        const delay = backoff ? delayMs * Math.pow(2, attempt - 1) : delayMs;
        
        onRetry?.(attempt, error);
        
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

// 使用示例
const data = await withRetry(
  () => githubAPI.getStarredRepos(token),
  {
    maxAttempts: 3,
    delayMs: 1000,
    backoff: true,
    onRetry: (attempt, error) => {
      console.log(`Retry attempt ${attempt}:`, error);
    },
  }
);
```

### 2. 降级策略

```typescript
// 缓存降级
async function getRepositories() {
  try {
    // 尝试从 API 获取最新数据
    const data = await repositoryAPI.getAll();
    localStorage.setItem('repositories_cache', JSON.stringify(data));
    return data;
  } catch (error) {
    // API 失败，使用缓存数据
    console.warn('API failed, using cached data');
    const cached = localStorage.getItem('repositories_cache');
    if (cached) {
      toast({
        title: '离线模式',
        description: '正在显示缓存数据',
        variant: 'warning',
      });
      return JSON.parse(cached);
    }
    throw error;
  }
}
```

### 3. 熔断器模式

```python
# services/circuit_breaker.py
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.successes = 0

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

---

## 最佳实践

### ✅ DO（推荐做法）

1. **始终提供友好的错误信息**
   - ❌ "Error: 500"
   - ✅ "服务器暂时无法响应，请稍后重试"

2. **错误要包含上下文信息**
   ```typescript
   throw new Error(`Failed to sync repository ${repoName}: ${error.message}`);
   ```

3. **异步操作要有加载状态**
   ```typescript
   const [loading, setLoading] = useState(false);
   // 显示加载指示器
   ```

4. **提供操作确认（危险操作）**
   - 删除、清空等不可逆操作需要确认

5. **重要操作提供撤销功能**
   - 批量操作后提供撤销按钮

6. **错误要记录到日志**
   ```python
   logger.error(f"Failed to process: {error}", exc_info=True)
   ```

7. **敏感信息不要暴露给用户**
   - 数据库连接字符串、API密钥等

### ❌ DON'T（避免的做法）

1. **不要吞掉异常**
   ```typescript
   // ❌ 错误
   try {
     await operation();
   } catch (e) {
     // 什么都不做
   }

   // ✅ 正确
   try {
     await operation();
   } catch (e) {
     ErrorHandler.showError(e);
   }
   ```

2. **不要使用 alert() 显示错误**
   - 使用 Toast 或模态对话框

3. **不要让应用崩溃**
   - 使用 ErrorBoundary 捕获错误

4. **不要忽略网络错误**
   - 提供离线提示和重试选项

5. **不要过度使用弹窗**
   - 非关键信息使用 Toast

### 🎯 错误处理检查清单

在实现新功能时，请检查：

- [ ] API 调用有错误处理
- [ ] 异步操作有 loading 状态
- [ ] 表单有验证错误提示
- [ ] 危险操作有确认对话框
- [ ] 错误有友好的提示信息
- [ ] 错误被记录到日志
- [ ] 关键错误有监控上报
- [ ] 网络错误有重试机制
- [ ] 失败操作可以重试
- [ ] 敏感信息已脱敏

---

## 示例：完整的功能实现

```typescript
// 示例：同步 GitHub 仓库
export function SyncRepositoriesButton() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [showProgress, setShowProgress] = useState(false);

  const handleSync = async () => {
    // 1. 确认操作
    const confirmed = await confirm({
      title: '同步仓库',
      description: '这将从 GitHub 同步您的所有星标仓库，可能需要几分钟时间。确定继续吗？',
    });

    if (!confirmed) return;

    setLoading(true);
    setShowProgress(true);

    try {
      // 2. 执行同步，带进度反馈
      const token = localStorage.getItem('github_token');
      if (!token) {
        throw new AuthenticationError('请先登录');
      }

      const githubApi = new GitHubAPI({ token });

      // 获取所有仓库
      const repos = await githubApi.getAllStarredRepos((current) => {
        setProgress({ current, total: current });
      });

      setProgress({ current: 0, total: repos.length });

      // 保存到数据库
      for (let i = 0; i < repos.length; i++) {
        await repositoryAPI.create(transformGitHubRepo(repos[i]));
        setProgress({ current: i + 1, total: repos.length });
      }

      // 3. 成功反馈
      toast({
        title: '同步成功',
        description: `已同步 ${repos.length} 个仓库`,
      });
    } catch (error) {
      // 4. 错误处理
      if (error instanceof RateLimitError) {
        toast({
          title: 'API 速率限制',
          description: `请在 ${error.retryAfter} 秒后重试`,
          variant: 'destructive',
        });
      } else {
        ErrorHandler.showError(error, '同步失败');
      }

      // 5. 记录日志
      logger.error('Repository sync failed', { error });
    } finally {
      setLoading(false);
      setTimeout(() => setShowProgress(false), 1000);
    }
  };

  return (
    <>
      <button
        onClick={handleSync}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? (
          <>
            <LoadingSpinner size="sm" />
            <span>同步中...</span>
          </>
        ) : (
          '同步仓库'
        )}
      </button>

      {showProgress && (
        <ProgressBar
          current={progress.current}
          total={progress.total}
          label="正在同步仓库"
        />
      )}
    </>
  );
}
```

---

## 总结

良好的错误处理和用户反馈机制是提升用户体验的关键。请遵循以下原则：

1. **预防为主**：通过验证和检查避免错误发生
2. **优雅降级**：错误发生时应用仍能部分可用
3. **及时反馈**：让用户知道发生了什么
4. **提供解决方案**：告诉用户如何解决问题
5. **记录和监控**：帮助开发者快速定位和修复问题

通过统一的错误处理体系，我们可以：
- 提升用户体验和满意度
- 减少客户支持成本
- 快速定位和修复问题
- 提高应用的稳定性和可靠性

---

**文档版本**：1.0  
**最后更新**：2025-10-31  
**维护者**：GitHub Stars Manager Team
