"""
AI任务管理器 - 整合任务队列、并发控制、成本管理等功能
提供完整的AI分析任务编排和执行
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from collections import defaultdict
import json

from .task_queue import (
    Task, TaskStatus, TaskType, Priority, TaskConfig,
    PriorityQueue, TaskRegistry, ConcurrencyController,
    RateLimiter, CostController, create_task
)
from .ai_client import OpenAICompatibleClient, APIConfig, ModelType


class AITaskManager:
    """AI任务管理器"""
    
    def __init__(
        self,
        ai_client: OpenAICompatibleClient,
        max_concurrent: int = 5,
        max_queue_size: int = 10000,
        requests_per_minute: int = 60,
        budget_limit: float = 100.0
    ):
        """
        初始化AI任务管理器
        
        Args:
            ai_client: AI客户端实例
            max_concurrent: 最大并发任务数
            max_queue_size: 队列最大容量
            requests_per_minute: 每分钟最大请求数
            budget_limit: 预算限制（美元）
        """
        self.ai_client = ai_client
        
        # 核心组件
        self.queue = PriorityQueue(max_size=max_queue_size)
        self.registry = TaskRegistry()
        self.concurrency = ConcurrencyController(max_concurrent=max_concurrent)
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        self.cost_controller = CostController(budget_limit=budget_limit)
        
        # 状态控制
        self._running = False
        self._paused = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self._stats = {
            "total_processed": 0,
            "total_succeeded": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "start_time": None
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """启动任务管理器"""
        if self._running:
            self.logger.warning("Task manager already running")
            return
        
        self._running = True
        self._paused = False
        self._stats["start_time"] = datetime.now()
        
        # 启动工作线程
        self._worker_task = asyncio.create_task(self._worker_loop())
        
        self.logger.info("AI Task Manager started")
    
    async def stop(self):
        """停止任务管理器"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待工作线程结束
        if self._worker_task:
            await self._worker_task
        
        self.logger.info("AI Task Manager stopped")
    
    def pause(self):
        """暂停处理任务"""
        self._paused = True
        self.logger.info("Task processing paused")
    
    def resume(self):
        """恢复处理任务"""
        self._paused = False
        self.logger.info("Task processing resumed")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
    
    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return self._paused
    
    async def submit_task(
        self,
        task_type: TaskType,
        data: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        config: Optional[TaskConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交任务到队列
        
        Args:
            task_type: 任务类型
            data: 任务数据
            priority: 优先级
            config: 任务配置
            metadata: 元数据
            
        Returns:
            任务ID
        """
        # 创建任务
        task = create_task(
            task_type=task_type,
            data=data,
            priority=priority,
            config=config,
            metadata=metadata
        )
        
        # 检查预算
        estimated_cost = self._estimate_cost(task)
        if not self.cost_controller.check_budget(estimated_cost):
            raise Exception("预算不足，无法提交任务")
        
        task.metrics.estimated_cost = estimated_cost
        
        # 注册任务
        if not self.registry.register(task):
            raise Exception(f"任务注册失败: {task.task_id}")
        
        # 加入队列
        if not self.queue.push(task):
            self.registry.remove(task.task_id)
            raise Exception("队列已满，无法添加任务")
        
        self.logger.info(f"Task {task.task_id} submitted: type={task_type.value}, priority={priority.name}")
        return task.task_id
    
    async def submit_batch(
        self,
        tasks: List[Dict[str, Any]],
        priority: Priority = Priority.MEDIUM
    ) -> List[str]:
        """
        批量提交任务
        
        Args:
            tasks: 任务列表，每个任务包含 task_type 和 data
            priority: 优先级
            
        Returns:
            任务ID列表
        """
        task_ids = []
        
        for task_data in tasks:
            try:
                task_id = await self.submit_task(
                    task_type=TaskType[task_data.get("task_type", "CUSTOM").upper()],
                    data=task_data.get("data", {}),
                    priority=priority,
                    config=task_data.get("config"),
                    metadata=task_data.get("metadata")
                )
                task_ids.append(task_id)
            except Exception as e:
                self.logger.error(f"Failed to submit task: {str(e)}")
                continue
        
        return task_ids
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        task = self.registry.get(task_id)
        if not task:
            return False
        
        # 只能取消排队中或暂停的任务
        if task.status not in [TaskStatus.QUEUED, TaskStatus.PAUSED]:
            self.logger.warning(f"Cannot cancel task {task_id} with status {task.status.value}")
            return False
        
        # 从队列中移除
        self.queue.remove(task_id)
        
        # 更新状态
        self.registry.update_status(task_id, TaskStatus.CANCELLED)
        self._stats["total_cancelled"] += 1
        
        self.logger.info(f"Task {task_id} cancelled")
        return True
    
    async def cancel_batch(self, task_ids: List[str]) -> Dict[str, bool]:
        """
        批量取消任务
        
        Args:
            task_ids: 任务ID列表
            
        Returns:
            任务ID到取消结果的映射
        """
        results = {}
        for task_id in task_ids:
            results[task_id] = await self.cancel_task(task_id)
        return results
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        task = self.registry.get(task_id)
        if not task:
            return None
        
        return task.to_dict()
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果（如果已完成）
        """
        task = self.registry.get(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            return None
        
        return task.result
    
    async def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        等待任务完成并返回结果
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            任务结果
        """
        start_time = time.time()
        
        while True:
            task = self.registry.get(task_id)
            if not task:
                return None
            
            if task.status == TaskStatus.COMPLETED:
                return task.result
            elif task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return None
            
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning(f"Task {task_id} wait timeout after {timeout}s")
                return None
            
            await asyncio.sleep(0.5)
    
    async def _worker_loop(self):
        """工作循环 - 处理队列中的任务"""
        self.logger.info("Worker loop started")
        
        while self._running:
            try:
                # 检查是否暂停
                if self._paused:
                    await asyncio.sleep(1)
                    continue
                
                # 从队列获取任务
                task = self.queue.pop()
                if not task:
                    await asyncio.sleep(0.5)
                    continue
                
                # 处理任务
                await self._process_task(task)
                
            except Exception as e:
                self.logger.error(f"Worker loop error: {str(e)}")
                await asyncio.sleep(1)
        
        self.logger.info("Worker loop stopped")
    
    async def _process_task(self, task: Task):
        """
        处理单个任务
        
        Args:
            task: 任务对象
        """
        try:
            # 获取并发许可
            await self.concurrency.acquire(task.task_id)
            
            # 速率限制
            await self.rate_limiter.acquire(task.config.estimated_tokens)
            
            # 更新状态
            self.registry.update_status(task.task_id, TaskStatus.RUNNING)
            
            # 执行任务
            result = await self._execute_task(task)
            
            # 记录成本
            if task.metrics.actual_cost > 0:
                self.cost_controller.record_cost(task.metrics.actual_cost)
            
            # 更新结果
            task.result = result
            self.registry.update_status(task.task_id, TaskStatus.COMPLETED)
            self._stats["total_succeeded"] += 1
            
            # 执行回调
            if task.config.callback:
                try:
                    if asyncio.iscoroutinefunction(task.config.callback):
                        await task.config.callback(task)
                    else:
                        task.config.callback(task)
                except Exception as e:
                    self.logger.error(f"Callback error for task {task.task_id}: {str(e)}")
            
            self.logger.info(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            # 处理失败
            task.error = str(e)
            task.metrics.retry_count += 1
            
            # 检查是否需要重试
            if task.metrics.retry_count < task.config.max_retries:
                self.logger.warning(f"Task {task.task_id} failed, retrying ({task.metrics.retry_count}/{task.config.max_retries})")
                
                # 重新加入队列
                self.registry.update_status(task.task_id, TaskStatus.RETRYING)
                await asyncio.sleep(task.config.retry_delay * (2 ** task.metrics.retry_count))
                self.queue.push(task)
            else:
                # 重试次数耗尽
                self.registry.update_status(task.task_id, TaskStatus.FAILED)
                self._stats["total_failed"] += 1
                
                # 执行错误回调
                if task.config.error_callback:
                    try:
                        if asyncio.iscoroutinefunction(task.config.error_callback):
                            await task.config.error_callback(task)
                        else:
                            task.config.error_callback(task)
                    except Exception as cb_error:
                        self.logger.error(f"Error callback failed for task {task.task_id}: {str(cb_error)}")
                
                self.logger.error(f"Task {task.task_id} failed after {task.metrics.retry_count} retries: {str(e)}")
        
        finally:
            # 释放并发许可
            self.concurrency.release(task.task_id)
            self._stats["total_processed"] += 1
    
    async def _execute_task(self, task: Task) -> Any:
        """
        执行任务的具体逻辑
        
        Args:
            task: 任务对象
            
        Returns:
            任务结果
        """
        if task.task_type == TaskType.REPOSITORY_ANALYSIS:
            return await self._execute_repository_analysis(task)
        elif task.task_type == TaskType.BATCH_ANALYSIS:
            return await self._execute_batch_analysis(task)
        elif task.task_type == TaskType.TEXT_CLASSIFICATION:
            return await self._execute_text_classification(task)
        elif task.task_type == TaskType.EMBEDDING_GENERATION:
            return await self._execute_embedding_generation(task)
        elif task.task_type == TaskType.SEMANTIC_SEARCH:
            return await self._execute_semantic_search(task)
        else:
            raise ValueError(f"Unknown task type: {task.task_type.value}")
    
    async def _execute_repository_analysis(self, task: Task) -> Dict[str, Any]:
        """执行仓库分析任务"""
        repo_info = task.data.get("repo_info", {})
        readme_content = task.data.get("readme_content", "")
        
        # 构建分析提示
        prompt = f"""
请分析以下GitHub仓库并提供结构化的信息：

仓库名称: {repo_info.get('name', 'N/A')}
描述: {repo_info.get('description', 'N/A')}
主要语言: {repo_info.get('language', 'N/A')}
Star数: {repo_info.get('stargazers_count', 0)}

README内容:
{readme_content[:2000] if readme_content else '无README'}

请以JSON格式返回分析结果，包含:
- summary: 简短总结
- main_features: 主要功能列表
- tech_stack: 技术栈
- use_cases: 使用场景
- pros: 优点
- cons: 缺点
"""
        
        response = await self.ai_client.generate_text(
            prompt=prompt,
            model=ModelType.GPT_4,
            max_tokens=2000,
            temperature=0.3
        )
        
        if not response.success:
            raise Exception(f"AI request failed: {response.error_message}")
        
        # 更新token使用量和成本
        if response.usage:
            task.metrics.tokens_used = response.usage.get("total_tokens", 0)
            task.metrics.actual_cost = self._calculate_cost(response.usage, ModelType.GPT_4)
        
        # 解析结果
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = {"analysis": response.content}
        
        return result
    
    async def _execute_batch_analysis(self, task: Task) -> List[Dict[str, Any]]:
        """执行批量仓库分析"""
        repositories = task.data.get("repositories", [])
        results = []
        
        total = len(repositories)
        for i, repo in enumerate(repositories):
            try:
                # 创建子任务
                sub_task = create_task(
                    task_type=TaskType.REPOSITORY_ANALYSIS,
                    data={"repo_info": repo, "readme_content": repo.get("readme", "")},
                    priority=task.priority
                )
                
                # 执行分析
                result = await self._execute_repository_analysis(sub_task)
                results.append({
                    "repo_name": repo.get("name", ""),
                    "success": True,
                    "result": result
                })
                
                # 累计成本
                task.metrics.tokens_used += sub_task.metrics.tokens_used
                task.metrics.actual_cost += sub_task.metrics.actual_cost
                
                # 进度回调
                if task.config.progress_callback:
                    progress = (i + 1) / total
                    if asyncio.iscoroutinefunction(task.config.progress_callback):
                        await task.config.progress_callback(progress, i + 1, total)
                    else:
                        task.config.progress_callback(progress, i + 1, total)
                
            except Exception as e:
                self.logger.error(f"Batch analysis error for repo {repo.get('name', '')}: {str(e)}")
                results.append({
                    "repo_name": repo.get("name", ""),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_text_classification(self, task: Task) -> Dict[str, Any]:
        """执行文本分类"""
        text = task.data.get("text", "")
        categories = task.data.get("categories", [])
        
        response = await self.ai_client.classify_text(text, categories)
        
        if not response.success:
            raise Exception(f"Classification failed: {response.error_message}")
        
        if response.usage:
            task.metrics.tokens_used = response.usage.get("total_tokens", 0)
            task.metrics.actual_cost = self._calculate_cost(response.usage, ModelType.GPT_3_5_TURBO)
        
        return response.content
    
    async def _execute_embedding_generation(self, task: Task) -> List[float]:
        """执行嵌入向量生成"""
        text = task.data.get("text", "")
        
        response = await self.ai_client.generate_embedding(text)
        
        if not response.success:
            raise Exception(f"Embedding generation failed: {response.error_message}")
        
        if response.usage:
            task.metrics.tokens_used = response.usage.get("total_tokens", 0)
            task.metrics.actual_cost = self._calculate_cost(response.usage, ModelType.TEXT_EMBEDDING_3_SMALL)
        
        return response.content
    
    async def _execute_semantic_search(self, task: Task) -> List[Dict[str, Any]]:
        """执行语义搜索"""
        query = task.data.get("query", "")
        documents = task.data.get("documents", [])
        top_k = task.data.get("top_k", 5)
        
        # 生成查询向量
        query_response = await self.ai_client.generate_embedding(query)
        if not query_response.success:
            raise Exception(f"Query embedding failed: {query_response.error_message}")
        
        query_vector = query_response.content
        
        # 计算相似度
        similarities = []
        for doc in documents:
            doc_vector = doc.get("embedding", [])
            if doc_vector:
                similarity = self._cosine_similarity(query_vector, doc_vector)
                similarities.append({
                    "document": doc,
                    "similarity": similarity
                })
        
        # 排序并返回top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        if query_response.usage:
            task.metrics.tokens_used = query_response.usage.get("total_tokens", 0)
            task.metrics.actual_cost = self._calculate_cost(query_response.usage, ModelType.TEXT_EMBEDDING_3_SMALL)
        
        return similarities[:top_k]
    
    def _estimate_cost(self, task: Task) -> float:
        """估算任务成本"""
        # 简化的成本估算
        estimated_tokens = task.config.estimated_tokens or 1000
        
        if task.task_type == TaskType.REPOSITORY_ANALYSIS:
            # 使用GPT-4，成本较高
            return (estimated_tokens / 1000) * 0.03
        elif task.task_type == TaskType.BATCH_ANALYSIS:
            # 批量分析，按仓库数量估算
            repo_count = len(task.data.get("repositories", []))
            return repo_count * (2000 / 1000) * 0.03
        elif task.task_type == TaskType.TEXT_CLASSIFICATION:
            # 使用GPT-3.5，成本较低
            return (estimated_tokens / 1000) * 0.0015
        elif task.task_type in [TaskType.EMBEDDING_GENERATION, TaskType.SEMANTIC_SEARCH]:
            # 嵌入向量，成本最低
            return (estimated_tokens / 1000000) * 0.02
        else:
            return (estimated_tokens / 1000) * 0.002
    
    def _calculate_cost(self, usage: Dict[str, int], model: ModelType) -> float:
        """计算实际成本"""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        costs = self.ai_client.model_costs.get(model, {"input": 0.002, "output": 0.002})
        
        return (prompt_tokens / 1000) * costs["input"] + (completion_tokens / 1000) * costs["output"]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = (datetime.now() - self._stats["start_time"]).total_seconds() if self._stats["start_time"] else 0
        
        return {
            "status": {
                "running": self._running,
                "paused": self._paused,
                "uptime_seconds": uptime
            },
            "queue": {
                "size": self.queue.size(),
                "by_priority": self.queue.size_by_priority()
            },
            "concurrency": {
                "running_tasks": self.concurrency.get_running_count(),
                "max_concurrent": self.concurrency.max_concurrent,
                "running_task_ids": self.concurrency.get_running_tasks()
            },
            "rate_limit": self.rate_limiter.get_current_usage(),
            "cost": self.cost_controller.get_usage(),
            "tasks": self.registry.get_stats(),
            "performance": {
                "total_processed": self._stats["total_processed"],
                "total_succeeded": self._stats["total_succeeded"],
                "total_failed": self._stats["total_failed"],
                "total_cancelled": self._stats["total_cancelled"],
                "success_rate": (self._stats["total_succeeded"] / self._stats["total_processed"] * 100) 
                                if self._stats["total_processed"] > 0 else 0
            }
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "total_size": self.queue.size(),
            "by_priority": self.queue.size_by_priority(),
            "is_full": self.queue.is_full(),
            "is_empty": self.queue.is_empty(),
            "max_size": self.queue.max_size
        }
    
    def adjust_settings(
        self,
        max_concurrent: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        budget_limit: Optional[float] = None,
        daily_limit: Optional[float] = None
    ):
        """
        动态调整设置
        
        Args:
            max_concurrent: 最大并发数
            requests_per_minute: 每分钟最大请求数
            budget_limit: 总预算限制
            daily_limit: 每日预算限制
        """
        if max_concurrent is not None:
            self.concurrency.set_max_concurrent(max_concurrent)
            self.logger.info(f"Max concurrent updated to {max_concurrent}")
        
        if requests_per_minute is not None:
            self.rate_limiter.requests_per_minute = requests_per_minute
            self.logger.info(f"Requests per minute updated to {requests_per_minute}")
        
        if budget_limit is not None or daily_limit is not None:
            self.cost_controller.adjust_limits(
                budget_limit=budget_limit,
                daily_limit=daily_limit
            )
            self.logger.info(f"Budget limits updated")
    
    async def cleanup_old_tasks(self, older_than_hours: int = 24) -> int:
        """
        清理旧任务
        
        Args:
            older_than_hours: 清理多少小时前的任务
            
        Returns:
            清理的任务数量
        """
        count = self.registry.clear_completed(older_than_hours)
        self.logger.info(f"Cleaned up {count} old tasks")
        return count


# 便捷函数

async def create_ai_task_manager(
    api_key: str,
    max_concurrent: int = 5,
    budget_limit: float = 100.0,
    **ai_config_kwargs
) -> AITaskManager:
    """
    创建并启动AI任务管理器
    
    Args:
        api_key: OpenAI API密钥
        max_concurrent: 最大并发数
        budget_limit: 预算限制
        **ai_config_kwargs: AI客户端额外配置
        
    Returns:
        AI任务管理器实例
    """
    from .ai_client import APIConfig
    
    # 创建AI客户端
    config = APIConfig(api_key=api_key, **ai_config_kwargs)
    ai_client = OpenAICompatibleClient(config)
    
    # 创建任务管理器
    manager = AITaskManager(
        ai_client=ai_client,
        max_concurrent=max_concurrent,
        budget_limit=budget_limit
    )
    
    # 启动管理器
    await manager.start()
    
    return manager
