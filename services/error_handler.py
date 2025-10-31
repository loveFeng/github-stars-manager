"""
GitHub Stars Manager - 统一错误处理模块

提供完整的错误处理、日志记录、监控上报功能
版本：1.0
最后更新：2025-10-31
"""

import logging
import traceback
import functools
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from enum import Enum
import json


# ============================================================================
# 错误级别定义
# ============================================================================

class ErrorLevel(Enum):
    """错误级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """错误分类"""
    AUTH = "AUTH"              # 认证错误
    VALIDATION = "VALIDATION"  # 验证错误
    DATABASE = "DATABASE"      # 数据库错误
    NETWORK = "NETWORK"        # 网络错误
    GITHUB_API = "GITHUB_API"  # GitHub API 错误
    AI_SERVICE = "AI_SERVICE"  # AI 服务错误
    BACKUP = "BACKUP"          # 备份错误
    SYNC = "SYNC"              # 同步错误
    SYSTEM = "SYSTEM"          # 系统错误
    UNKNOWN = "UNKNOWN"        # 未知错误


# ============================================================================
# 异常类定义
# ============================================================================

class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        level: ErrorLevel = ErrorLevel.ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        http_status: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.level = level
        self.details = details or {}
        self.original_error = original_error
        self.http_status = http_status
        self.timestamp = datetime.now().isoformat()
        
        # 如果有原始错误，记录堆栈信息
        if original_error:
            self.details['original_error'] = str(original_error)
            self.details['original_traceback'] = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "level": self.level.value,
            "details": self.details,
            "timestamp": self.timestamp
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ValidationError(AppException):
    """验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            level=ErrorLevel.WARNING,
            details=details,
            http_status=400,
            **kwargs
        )


class AuthenticationError(AppException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            category=ErrorCategory.AUTH,
            level=ErrorLevel.ERROR,
            http_status=401,
            **kwargs
        )


class PermissionError(AppException):
    """权限错误"""
    
    def __init__(self, message: str = "权限不足", resource: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if resource:
            details['resource'] = resource
            
        super().__init__(
            message=message,
            code="PERMISSION_ERROR",
            category=ErrorCategory.AUTH,
            level=ErrorLevel.WARNING,
            details=details,
            http_status=403,
            **kwargs
        )


class NotFoundError(AppException):
    """资源不存在错误"""
    
    def __init__(self, resource: str = "资源", resource_id: Optional[Any] = None, **kwargs):
        details = kwargs.pop('details', {})
        if resource_id:
            details['resource_id'] = resource_id
            
        super().__init__(
            message=f"{resource}不存在",
            code="NOT_FOUND",
            category=ErrorCategory.VALIDATION,
            level=ErrorLevel.WARNING,
            details=details,
            http_status=404,
            **kwargs
        )


class RateLimitError(AppException):
    """速率限制错误"""
    
    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.pop('details', {})
        if retry_after:
            details['retry_after'] = retry_after
            
        super().__init__(
            message="请求过于频繁，请稍后再试",
            code="RATE_LIMIT",
            category=ErrorCategory.NETWORK,
            level=ErrorLevel.WARNING,
            details=details,
            http_status=429,
            **kwargs
        )


class DatabaseError(AppException):
    """数据库错误"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if query:
            details['query'] = query
            
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            level=ErrorLevel.ERROR,
            details=details,
            http_status=500,
            **kwargs
        )


class NetworkError(AppException):
    """网络错误"""
    
    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if url:
            details['url'] = url
            
        super().__init__(
            message=message,
            code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            level=ErrorLevel.ERROR,
            details=details,
            http_status=502,
            **kwargs
        )


class ExternalServiceError(AppException):
    """外部服务错误"""
    
    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        details['service'] = service_name
        if status_code:
            details['status_code'] = status_code
            
        super().__init__(
            message=message or f"{service_name}服务调用失败",
            code=f"{service_name.upper()}_ERROR",
            category=ErrorCategory.NETWORK,
            level=ErrorLevel.ERROR,
            details=details,
            http_status=502,
            **kwargs
        )


class GitHubAPIError(ExternalServiceError):
    """GitHub API 错误"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            service_name="GitHub",
            message=message,
            status_code=status_code,
            **kwargs
        )
        self.category = ErrorCategory.GITHUB_API


class AIServiceError(ExternalServiceError):
    """AI 服务错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            service_name="AI",
            message=message,
            **kwargs
        )
        self.category = ErrorCategory.AI_SERVICE


# ============================================================================
# 日志处理器
# ============================================================================

class AppLogger:
    """应用日志处理器"""
    
    def __init__(
        self,
        name: str = "GitHubStarsManager",
        log_dir: str = "logs",
        console_level: str = "INFO",
        file_level: str = "DEBUG"
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # 清除已有处理器
        
        # 创建日志目录
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 日期格式
        today = datetime.now().strftime('%Y%m%d')
        
        # 文件处理器 - 所有日志
        file_handler = logging.FileHandler(
            self.log_dir / f"app_{today}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, file_level))
        
        # 文件处理器 - 仅错误
        error_handler = logging.FileHandler(
            self.log_dir / f"error_{today}.log",
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level))
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def _format_extra(self, **kwargs) -> str:
        """格式化额外信息"""
        if not kwargs:
            return ""
        return " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self.logger.debug(message + self._format_extra(**kwargs))

    def info(self, message: str, **kwargs):
        """记录信息"""
        self.logger.info(message + self._format_extra(**kwargs))

    def warning(self, message: str, **kwargs):
        """记录警告"""
        self.logger.warning(message + self._format_extra(**kwargs))

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """记录错误"""
        self.logger.error(message + self._format_extra(**kwargs), exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """记录严重错误"""
        self.logger.critical(message + self._format_extra(**kwargs), exc_info=exc_info)

    def log_exception(self, exception: Exception, **kwargs):
        """记录异常"""
        if isinstance(exception, AppException):
            self.error(
                f"[{exception.code}] {exception.message}",
                exc_info=True,
                category=exception.category.value,
                **exception.details,
                **kwargs
            )
        else:
            self.error(
                f"Unexpected exception: {str(exception)}",
                exc_info=True,
                **kwargs
            )


# 全局日志实例
logger = AppLogger()


# ============================================================================
# 错误处理装饰器
# ============================================================================

T = TypeVar('T')


def handle_errors(
    error_message: str = "操作失败",
    log_error: bool = True,
    raise_error: bool = True,
    return_on_error: Any = None,
    category: ErrorCategory = ErrorCategory.UNKNOWN
):
    """
    错误处理装饰器
    
    Args:
        error_message: 错误消息
        log_error: 是否记录错误日志
        raise_error: 是否抛出错误
        return_on_error: 错误时返回的值（如果不抛出错误）
        category: 错误分类
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except AppException as e:
                # 应用异常直接处理
                if log_error:
                    logger.log_exception(e)
                if raise_error:
                    raise
                return return_on_error
            except Exception as e:
                # 其他异常包装为 AppException
                app_error = AppException(
                    message=error_message,
                    category=category,
                    original_error=e
                )
                if log_error:
                    logger.log_exception(app_error)
                if raise_error:
                    raise app_error from e
                return return_on_error
        
        return wrapper
    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff: bool = True,
    catch_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay_seconds: 重试延迟（秒）
        backoff: 是否使用指数退避
        catch_exceptions: 要捕获的异常类型
        on_retry: 重试时的回调函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except catch_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # 计算延迟时间
                        delay = delay_seconds * (2 ** (attempt - 1) if backoff else 1)
                        
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed, retrying in {delay}s...",
                            function=func.__name__,
                            error=str(e)
                        )
                        
                        # 调用重试回调
                        if on_retry:
                            on_retry(attempt, e)
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed",
                            function=func.__name__,
                            error=str(e),
                            exc_info=True
                        )
            
            # 所有尝试都失败，抛出最后一个异常
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def measure_performance(func: Callable[..., T]) -> Callable[..., T]:
    """
    性能监控装饰器
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # 记录性能日志
            logger.debug(
                f"Function executed",
                function=func.__name__,
                duration_ms=round(elapsed * 1000, 2)
            )
            
            # 慢查询警告（超过5秒）
            if elapsed > 5:
                logger.warning(
                    f"Slow operation detected",
                    function=func.__name__,
                    duration_ms=round(elapsed * 1000, 2)
                )
            
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Function failed",
                function=func.__name__,
                duration_ms=round(elapsed * 1000, 2),
                error=str(e)
            )
            raise
    
    return wrapper


# ============================================================================
# 错误处理工具类
# ============================================================================

class ErrorHandler:
    """错误处理工具类"""
    
    @staticmethod
    def handle_github_api_error(response_status: int, response_data: Dict[str, Any]) -> GitHubAPIError:
        """
        处理 GitHub API 错误
        
        Args:
            response_status: HTTP 状态码
            response_data: 响应数据
        """
        message = response_data.get('message', 'GitHub API 请求失败')
        
        if response_status == 401:
            return GitHubAPIError(
                message="GitHub Token 无效或已过期",
                status_code=401
            )
        elif response_status == 403:
            # 检查是否是速率限制
            if 'rate limit' in message.lower():
                reset_time = response_data.get('reset')
                retry_after = None
                if reset_time:
                    retry_after = max(0, reset_time - int(time.time()))
                
                return RateLimitError(retry_after=retry_after)
            
            return GitHubAPIError(
                message="GitHub API 权限不足",
                status_code=403
            )
        elif response_status == 404:
            return NotFoundError(resource="GitHub 资源")
        elif response_status >= 500:
            return GitHubAPIError(
                message="GitHub 服务器错误，请稍后重试",
                status_code=response_status
            )
        else:
            return GitHubAPIError(
                message=message,
                status_code=response_status
            )

    @staticmethod
    def handle_database_error(error: Exception, query: Optional[str] = None) -> DatabaseError:
        """
        处理数据库错误
        
        Args:
            error: 原始错误
            query: SQL 查询语句
        """
        error_str = str(error).lower()
        
        if 'unique constraint failed' in error_str:
            return DatabaseError(
                message="数据已存在，请勿重复添加",
                query=query,
                original_error=error
            )
        elif 'foreign key constraint failed' in error_str:
            return DatabaseError(
                message="关联的数据不存在",
                query=query,
                original_error=error
            )
        elif 'not null constraint failed' in error_str:
            return DatabaseError(
                message="必填字段不能为空",
                query=query,
                original_error=error
            )
        elif 'no such table' in error_str:
            return DatabaseError(
                message="数据库表不存在，请检查数据库初始化",
                query=query,
                original_error=error
            )
        else:
            return DatabaseError(
                message="数据库操作失败，请稍后重试",
                query=query,
                original_error=error
            )

    @staticmethod
    def safe_execute(
        operation: Callable[[], T],
        default_value: T = None,
        error_message: str = "操作失败"
    ) -> T:
        """
        安全执行操作，捕获并记录错误
        
        Args:
            operation: 要执行的操作
            default_value: 错误时返回的默认值
            error_message: 错误消息
        """
        try:
            return operation()
        except Exception as e:
            logger.error(error_message, exc_info=True)
            return default_value


# ============================================================================
# 熔断器
# ============================================================================

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"        # 正常状态
    OPEN = "open"            # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


class CircuitBreaker:
    """
    熔断器模式实现
    
    用于防止故障扩散，当错误率超过阈值时自动熔断
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        name: str = "CircuitBreaker"
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值（触发熔断）
            success_threshold: 成功阈值（恢复正常）
            timeout_seconds: 熔断超时时间（秒）
            name: 熔断器名称
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.name = name
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        # 检查熔断器状态
        if self.state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    logger.info(
                        f"Circuit breaker entering HALF_OPEN state",
                        name=self.name
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise AppException(
                        message=f"熔断器已开启，请在 {int(self.timeout_seconds - elapsed)} 秒后重试",
                        code="CIRCUIT_BREAKER_OPEN",
                        category=ErrorCategory.SYSTEM
                    )

        try:
            # 执行函数
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """成功回调"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                logger.info(
                    f"Circuit breaker entering CLOSED state",
                    name=self.name
                )
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker entering OPEN state",
                name=self.name,
                failure_count=self.failure_count
            )
            self.state = CircuitState.OPEN

    def reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker reset", name=self.name)


# ============================================================================
# 错误监控和上报
# ============================================================================

class ErrorReporter:
    """错误监控和上报"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.error_cache = []
        self.max_cache_size = 100

    def report(self, error: AppException, context: Optional[Dict[str, Any]] = None):
        """
        上报错误
        
        Args:
            error: 应用异常
            context: 上下文信息
        """
        if not self.enabled:
            return

        error_data = {
            **error.to_dict(),
            'context': context or {}
        }
        
        # 添加到缓存
        self.error_cache.append(error_data)
        
        # 限制缓存大小
        if len(self.error_cache) > self.max_cache_size:
            self.error_cache.pop(0)
        
        # TODO: 集成第三方监控服务（如 Sentry）
        logger.debug(f"Error reported", code=error.code)

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        if not self.error_cache:
            return {"total": 0, "by_category": {}, "by_code": {}}
        
        by_category = {}
        by_code = {}
        
        for error in self.error_cache:
            category = error.get('category', 'UNKNOWN')
            code = error.get('code', 'UNKNOWN')
            
            by_category[category] = by_category.get(category, 0) + 1
            by_code[code] = by_code.get(code, 0) + 1
        
        return {
            "total": len(self.error_cache),
            "by_category": by_category,
            "by_code": by_code
        }


# 全局错误上报实例
error_reporter = ErrorReporter()


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 错误级别和分类
    'ErrorLevel',
    'ErrorCategory',
    
    # 异常类
    'AppException',
    'ValidationError',
    'AuthenticationError',
    'PermissionError',
    'NotFoundError',
    'RateLimitError',
    'DatabaseError',
    'NetworkError',
    'ExternalServiceError',
    'GitHubAPIError',
    'AIServiceError',
    
    # 日志
    'AppLogger',
    'logger',
    
    # 装饰器
    'handle_errors',
    'retry_on_error',
    'measure_performance',
    
    # 工具类
    'ErrorHandler',
    'CircuitBreaker',
    'CircuitState',
    'ErrorReporter',
    'error_reporter',
]
