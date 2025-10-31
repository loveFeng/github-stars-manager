"""
增强的任务队列系统 - 优先级队列、并发控制、状态追踪
提供完整的异步任务管理功能
"""

import asyncio
import uuid
import time
import logging
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading
import json


class TaskStatus(Enum):
    """任务状态"""
    QUEUED = "queued"           # 已加入队列等待处理
    RUNNING = "running"         # 正在处理中
    PAUSED = "paused"           # 已暂停
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    RETRYING = "retrying"       # 重试中


class Priority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    
    def __lt__(self, other):
        if isinstance(other, Priority):
            return self.value < other.value
        return NotImplemented


class TaskType(Enum):
    """任务类型"""
    REPOSITORY_ANALYSIS = "repository_analysis"
    BATCH_ANALYSIS = "batch_analysis"
    TEXT_CLASSIFICATION = "text_classification"
    EMBEDDING_GENERATION = "embedding_generation"
    SEMANTIC_SEARCH = "semantic_search"
    CUSTOM = "custom"


@dataclass
class TaskMetrics:
    """任务指标"""
    queue_time: float = 0.0          # 排队时间（秒）
    execution_time: float = 0.0      # 执行时间（秒）
    total_time: float = 0.0          # 总时间（秒）
    retry_count: int = 0             # 重试次数
    tokens_used: int = 0             # 使用的token数量
    estimated_cost: float = 0.0      # 预估成本（美元）
    actual_cost: float = 0.0         # 实际成本（美元）


@dataclass
class TaskConfig:
    """任务配置"""
    max_retries: int = 3             # 最大重试次数
    retry_delay: float = 1.0         # 重试延迟（秒）
    timeout: Optional[float] = None  # 超时时间（秒）
    estimated_tokens: int = 0        # 预估token使用量
    callback: Optional[Callable] = None  # 完成回调
    error_callback: Optional[Callable] = None  # 错误回调
    progress_callback: Optional[Callable] = None  # 进度回调


@dataclass
class Task:
    """任务对象"""
    task_id: str
    task_type: TaskType
    priority: Priority
    data: Dict[str, Any]
    config: TaskConfig = field(default_factory=TaskConfig)
    
    # 状态信息
    status: TaskStatus = TaskStatus.QUEUED
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 指标
    metrics: TaskMetrics = field(default_factory=TaskMetrics)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": asdict(self.metrics),
            "error": self.error,
            "metadata": self.metadata
        }
    
    def calculate_metrics(self):
        """计算任务指标"""
        if self.queued_at and self.started_at:
            self.metrics.queue_time = (self.started_at - self.queued_at).total_seconds()
        
        if self.started_at and self.completed_at:
            self.metrics.execution_time = (self.completed_at - self.started_at).total_seconds()
        
        if self.created_at and self.completed_at:
            self.metrics.total_time = (self.completed_at - self.created_at).total_seconds()


class PriorityQueue:
    """优先级队列"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queues: Dict[Priority, deque] = {
            Priority.URGENT: deque(),
            Priority.HIGH: deque(),
            Priority.MEDIUM: deque(),
            Priority.LOW: deque()
        }
        self._lock = threading.RLock()
        self._size = 0
    
    def push(self, task: Task) -> bool:
        """添加任务到队列"""
        with self._lock:
            if self._size >= self.max_size:
                return False
            
            self._queues[task.priority].append(task)
            self._size += 1
            task.queued_at = datetime.now()
            return True
    
    def pop(self) -> Optional[Task]:
        """从队列中取出最高优先级的任务"""
        with self._lock:
            # 按优先级从高到低遍历
            for priority in [Priority.URGENT, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                if self._queues[priority]:
                    task = self._queues[priority].popleft()
                    self._size -= 1
                    return task
            return None
    
    def remove(self, task_id: str) -> bool:
        """从队列中移除特定任务"""
        with self._lock:
            for queue in self._queues.values():
                for task in queue:
                    if task.task_id == task_id:
                        queue.remove(task)
                        self._size -= 1
                        return True
            return False
    
    def size(self) -> int:
        """获取队列大小"""
        return self._size
    
    def size_by_priority(self) -> Dict[str, int]:
        """按优先级获取队列大小"""
        with self._lock:
            return {
                priority.name: len(queue)
                for priority, queue in self._queues.items()
            }
    
    def clear(self):
        """清空队列"""
        with self._lock:
            for queue in self._queues.values():
                queue.clear()
            self._size = 0
    
    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return self._size == 0
    
    def is_full(self) -> bool:
        """检查队列是否已满"""
        return self._size >= self.max_size


class TaskRegistry:
    """任务注册表 - 管理所有任务的状态"""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def register(self, task: Task) -> bool:
        """注册任务"""
        with self._lock:
            if task.task_id in self._tasks:
                self.logger.warning(f"Task {task.task_id} already registered")
                return False
            self._tasks[task.task_id] = task
            return True
    
    def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    task.completed_at = datetime.now()
                    task.calculate_metrics()
                return True
            return False
    
    def get_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.status == status]
    
    def get_by_type(self, task_type: TaskType) -> List[Task]:
        """按类型获取任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.task_type == task_type]
    
    def remove(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def clear_completed(self, older_than_hours: int = 24) -> int:
        """清理已完成的任务"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            removed_count = 0
            
            task_ids_to_remove = []
            for task_id, task in self._tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                    and task.completed_at 
                    and task.completed_at < cutoff_time):
                    task_ids_to_remove.append(task_id)
            
            for task_id in task_ids_to_remove:
                del self._tasks[task_id]
                removed_count += 1
            
            return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = {
                "total": len(self._tasks),
                "by_status": {},
                "by_type": {},
                "by_priority": {}
            }
            
            for task in self._tasks.values():
                # 按状态统计
                status_key = task.status.value
                stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1
                
                # 按类型统计
                type_key = task.task_type.value
                stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1
                
                # 按优先级统计
                priority_key = task.priority.name
                stats["by_priority"][priority_key] = stats["by_priority"].get(priority_key, 0) + 1
            
            return stats


class ConcurrencyController:
    """并发控制器"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_tasks: Set[str] = set()
        self._lock = threading.RLock()
    
    async def acquire(self, task_id: str) -> bool:
        """获取执行许可"""
        await self._semaphore.acquire()
        with self._lock:
            self._running_tasks.add(task_id)
        return True
    
    def release(self, task_id: str):
        """释放执行许可"""
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks.remove(task_id)
        self._semaphore.release()
    
    def get_running_count(self) -> int:
        """获取正在运行的任务数量"""
        with self._lock:
            return len(self._running_tasks)
    
    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        with self._lock:
            return list(self._running_tasks)
    
    def set_max_concurrent(self, max_concurrent: int):
        """设置最大并发数"""
        self.max_concurrent = max_concurrent
        # 注意: 动态调整semaphore需要重建
        self._semaphore = asyncio.Semaphore(max_concurrent)


class RateLimiter:
    """速率限制器 - 支持多种限制策略"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 3600,
        tokens_per_minute: int = 90000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.tokens_per_minute = tokens_per_minute
        
        self._minute_requests: deque = deque()
        self._hour_requests: deque = deque()
        self._minute_tokens: deque = deque()
        self._lock = threading.RLock()
    
    async def acquire(self, estimated_tokens: int = 0) -> bool:
        """获取速率许可"""
        with self._lock:
            now = time.time()
            
            # 清理过期记录
            self._cleanup_expired_records(now)
            
            # 检查请求速率限制
            if len(self._minute_requests) >= self.requests_per_minute:
                wait_time = 60 - (now - self._minute_requests[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire(estimated_tokens)
            
            if len(self._hour_requests) >= self.requests_per_hour:
                wait_time = 3600 - (now - self._hour_requests[0])
                if wait_time > 0:
                    await asyncio.sleep(min(wait_time, 60))
                    return await self.acquire(estimated_tokens)
            
            # 检查token速率限制
            minute_tokens = sum(tokens for _, tokens in self._minute_tokens)
            if minute_tokens + estimated_tokens > self.tokens_per_minute:
                wait_time = 60 - (now - self._minute_tokens[0][0]) if self._minute_tokens else 0
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire(estimated_tokens)
            
            # 记录请求
            self._minute_requests.append(now)
            self._hour_requests.append(now)
            self._minute_tokens.append((now, estimated_tokens))
            
            return True
    
    def _cleanup_expired_records(self, now: float):
        """清理过期记录"""
        # 清理分钟级请求
        while self._minute_requests and now - self._minute_requests[0] > 60:
            self._minute_requests.popleft()
        
        # 清理小时级请求
        while self._hour_requests and now - self._hour_requests[0] > 3600:
            self._hour_requests.popleft()
        
        # 清理分钟级token
        while self._minute_tokens and now - self._minute_tokens[0][0] > 60:
            self._minute_tokens.popleft()
    
    def get_current_usage(self) -> Dict[str, Any]:
        """获取当前使用情况"""
        with self._lock:
            now = time.time()
            self._cleanup_expired_records(now)
            
            minute_tokens = sum(tokens for _, tokens in self._minute_tokens)
            
            return {
                "requests_per_minute": {
                    "current": len(self._minute_requests),
                    "limit": self.requests_per_minute,
                    "available": max(0, self.requests_per_minute - len(self._minute_requests))
                },
                "requests_per_hour": {
                    "current": len(self._hour_requests),
                    "limit": self.requests_per_hour,
                    "available": max(0, self.requests_per_hour - len(self._hour_requests))
                },
                "tokens_per_minute": {
                    "current": minute_tokens,
                    "limit": self.tokens_per_minute,
                    "available": max(0, self.tokens_per_minute - minute_tokens)
                }
            }


class CostController:
    """成本控制器"""
    
    def __init__(
        self,
        budget_limit: float = 100.0,
        daily_limit: float = 10.0,
        hourly_limit: float = 1.0
    ):
        self.budget_limit = budget_limit
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        
        self.total_cost = 0.0
        self._daily_costs: deque = deque()
        self._hourly_costs: deque = deque()
        self._lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
    
    def check_budget(self, estimated_cost: float) -> bool:
        """检查预算是否充足"""
        with self._lock:
            now = time.time()
            self._cleanup_expired_costs(now)
            
            # 检查总预算
            if self.total_cost + estimated_cost > self.budget_limit:
                self.logger.warning(f"Total budget limit exceeded: ${self.total_cost + estimated_cost:.4f} > ${self.budget_limit:.2f}")
                return False
            
            # 检查日预算
            daily_cost = sum(cost for _, cost in self._daily_costs)
            if daily_cost + estimated_cost > self.daily_limit:
                self.logger.warning(f"Daily budget limit exceeded: ${daily_cost + estimated_cost:.4f} > ${self.daily_limit:.2f}")
                return False
            
            # 检查小时预算
            hourly_cost = sum(cost for _, cost in self._hourly_costs)
            if hourly_cost + estimated_cost > self.hourly_limit:
                self.logger.warning(f"Hourly budget limit exceeded: ${hourly_cost + estimated_cost:.4f} > ${self.hourly_limit:.2f}")
                return False
            
            return True
    
    def record_cost(self, actual_cost: float):
        """记录实际成本"""
        with self._lock:
            now = time.time()
            self.total_cost += actual_cost
            self._daily_costs.append((now, actual_cost))
            self._hourly_costs.append((now, actual_cost))
    
    def _cleanup_expired_costs(self, now: float):
        """清理过期成本记录"""
        # 清理日成本（保留24小时）
        while self._daily_costs and now - self._daily_costs[0][0] > 86400:
            self._daily_costs.popleft()
        
        # 清理小时成本（保留1小时）
        while self._hourly_costs and now - self._hourly_costs[0][0] > 3600:
            self._hourly_costs.popleft()
    
    def get_usage(self) -> Dict[str, Any]:
        """获取成本使用情况"""
        with self._lock:
            now = time.time()
            self._cleanup_expired_costs(now)
            
            daily_cost = sum(cost for _, cost in self._daily_costs)
            hourly_cost = sum(cost for _, cost in self._hourly_costs)
            
            return {
                "total": {
                    "cost": self.total_cost,
                    "limit": self.budget_limit,
                    "remaining": max(0, self.budget_limit - self.total_cost),
                    "percentage": (self.total_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0
                },
                "daily": {
                    "cost": daily_cost,
                    "limit": self.daily_limit,
                    "remaining": max(0, self.daily_limit - daily_cost),
                    "percentage": (daily_cost / self.daily_limit * 100) if self.daily_limit > 0 else 0
                },
                "hourly": {
                    "cost": hourly_cost,
                    "limit": self.hourly_limit,
                    "remaining": max(0, self.hourly_limit - hourly_cost),
                    "percentage": (hourly_cost / self.hourly_limit * 100) if self.hourly_limit > 0 else 0
                }
            }
    
    def reset_total_cost(self):
        """重置总成本"""
        self.total_cost = 0.0
    
    def adjust_limits(
        self,
        budget_limit: Optional[float] = None,
        daily_limit: Optional[float] = None,
        hourly_limit: Optional[float] = None
    ):
        """调整预算限制"""
        if budget_limit is not None:
            self.budget_limit = budget_limit
        if daily_limit is not None:
            self.daily_limit = daily_limit
        if hourly_limit is not None:
            self.hourly_limit = hourly_limit


def create_task(
    task_type: TaskType,
    data: Dict[str, Any],
    priority: Priority = Priority.MEDIUM,
    config: Optional[TaskConfig] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Task:
    """创建任务的辅助函数"""
    task_id = str(uuid.uuid4())
    
    return Task(
        task_id=task_id,
        task_type=task_type,
        priority=priority,
        data=data,
        config=config or TaskConfig(),
        metadata=metadata or {}
    )
