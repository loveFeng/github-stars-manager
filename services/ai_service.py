"""
AI服务整合层 - 高级AI功能实现
包含仓库摘要生成、自动分类、语义搜索、任务队列等功能
"""

import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import hashlib
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .ai_client import OpenAICompatibleClient, APIConfig, ModelType, TaskType, APIResponse


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class RepositorySummary:
    """仓库摘要"""
    repo_name: str
    repo_url: str
    description: str
    main_language: str
    technologies: List[str]
    features: List[str]
    target_audience: str
    installation_guide: str
    usage_examples: List[str]
    pros: List[str]
    cons: List[str]
    alternatives: List[str]
    license: Optional[str]
    last_updated: Optional[str]
    stars: Optional[int]
    summary: str
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ClassificationResult:
    """分类结果"""
    text: str
    primary_category: str
    confidence: float
    all_categories: Dict[str, float]
    tags: List[str]
    reasoning: str
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmbeddingVector:
    """嵌入向量"""
    content_id: str
    content: str
    vector: List[float]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """任务对象"""
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: Priority
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    callback: Optional[Callable] = None


class TaskQueue:
    """任务队列"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queues = {
            Priority.URGENT: deque(),
            Priority.HIGH: deque(),
            Priority.MEDIUM: deque(),
            Priority.LOW: deque()
        }
        self._task_map = {}  # task_id -> task
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def add_task(self, task: Task) -> bool:
        """添加任务"""
        with self._lock:
            if len(self._task_map) >= self.max_size:
                self.logger.warning(f"Task queue full (max: {self.max_size})")
                return False
            
            self._task_map[task.task_id] = task
            self._queues[task.priority].append(task)
            self.logger.debug(f"Added task {task.task_id} with priority {task.priority.name}")
            return True
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个任务"""
        with self._lock:
            for priority in [Priority.URGENT, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                if self._queues[priority]:
                    task = self._queues[priority].popleft()
                    return task
            return None
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取特定任务"""
        return self._task_map.get(task_id)
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if task_id in self._task_map:
                task = self._task_map.pop(task_id)
                # 从队列中移除（需要遍历所有优先级队列）
                for queue in self._queues.values():
                    if task in queue:
                        queue.remove(task)
                        break
                return True
            return False
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return sum(len(queue) for queue in self._queues.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return [task for task in self._task_map.values() if task.status == status]


class RepositoryAnalyzer:
    """仓库分析器"""
    
    def __init__(self, ai_client: OpenAICompatibleClient):
        self.ai_client = ai_client
        self.logger = logging.getLogger(__name__)
    
    async def analyze_repository(
        self,
        repo_info: Dict[str, Any],
        readme_content: str = "",
        file_structure: str = ""
    ) -> RepositorySummary:
        """分析GitHub仓库"""
        
        try:
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(repo_info, readme_content, file_structure)
            
            # 生成详细分析
            response = await self.ai_client.generate_text(
                prompt=analysis_prompt,
                system_prompt=self._get_analysis_system_prompt(),
                model=ModelType.GPT_4,
                max_tokens=3000,
                temperature=0.3
            )
            
            if not response.success:
                raise Exception(f"仓库分析失败: {response.error_message}")
            
            # 解析结果
            analysis_data = self._parse_repository_analysis(response.content)
            
            # 创建摘要对象
            summary = RepositorySummary(
                repo_name=repo_info.get("name", ""),
                repo_url=repo_info.get("html_url", ""),
                description=analysis_data.get("description", ""),
                main_language=analysis_data.get("main_language", ""),
                technologies=analysis_data.get("technologies", []),
                features=analysis_data.get("features", []),
                target_audience=analysis_data.get("target_audience", ""),
                installation_guide=analysis_data.get("installation_guide", ""),
                usage_examples=analysis_data.get("usage_examples", []),
                pros=analysis_data.get("pros", []),
                cons=analysis_data.get("cons", []),
                alternatives=analysis_data.get("alternatives", []),
                license=repo_info.get("license", {}).get("name") if repo_info.get("license") else None,
                last_updated=repo_info.get("updated_at"),
                stars=repo_info.get("stargazers_count"),
                summary=analysis_data.get("summary", "")
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Repository analysis error: {str(e)}")
            raise
    
    def _build_analysis_prompt(self, repo_info: Dict[str, Any], readme: str, file_structure: str) -> str:
        """构建分析提示"""
        return f"""
请分析以下GitHub仓库，提供详细的结构化信息：

=== 仓库基本信息 ===
名称: {repo_info.get("name", "N/A")}
描述: {repo_info.get("description", "N/A")}
主要语言: {repo_info.get("language", "N/A")}
Star数: {repo_info.get("stargazers_count", 0)}
更新时间: {repo_info.get("updated_at", "N/A")}

=== README内容 ===
{readme[:3000] if readme else "无README内容"}

=== 文件结构 ===
{file_structure[:2000] if file_structure else "无文件结构信息"}

请提供JSON格式的分析结果，包含以下字段：
- description: 详细描述
- main_language: 主要编程语言
- technologies: 使用的技术栈 (数组)
- features: 主要功能特性 (数组)
- target_audience: 目标用户群体
- installation_guide: 安装说明
- usage_examples: 使用示例 (数组)
- pros: 优点 (数组)
- cons: 缺点 (数组)
- alternatives: 类似项目推荐 (数组)
- summary: 整体总结
"""
    
    def _get_analysis_system_prompt(self) -> str:
        """获取分析系统提示"""
        return """
你是一个专业的代码仓库分析师，具有丰富的开源项目评估经验。
请基于提供的仓库信息，客观、专业地分析项目的各个方面。
确保分析结果准确、有价值，并给出实用建议。
"""
    
    def _parse_repository_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """解析分析结果"""
        try:
            # 尝试直接解析JSON
            return json.loads(analysis_text)
        except json.JSONDecodeError:
            # 如果不是纯JSON，提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # 最后备用方案：结构化解析
            return self._structured_parse(analysis_text)
    
    def _structured_parse(self, text: str) -> Dict[str, Any]:
        """结构化解析文本"""
        result = {}
        lines = text.split('\n')
        current_key = None
        current_value = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找键值对
            if ':' in line and line.count(':') == 1:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if current_key and current_value:
                    result[current_key] = '\n'.join(current_value).strip()
                
                current_key = key
                current_value = [value]
            else:
                if current_key:
                    current_value.append(line)
        
        if current_key and current_value:
            result[current_key] = '\n'.join(current_value).strip()
        
        # 转换数组字段
        array_fields = ["technologies", "features", "usage_examples", "pros", "cons", "alternatives"]
        for field in array_fields:
            if field in result:
                if isinstance(result[field], str):
                    items = [item.strip() for item in result[field].split('\n') if item.strip()]
                    result[field] = items if items else [result[field]]
                elif not isinstance(result[field], list):
                    result[field] = []
        
        return result


class SemanticSearch:
    """语义搜索服务"""
    
    def __init__(self, ai_client: OpenAICompatibleClient):
        self.ai_client = ai_client
        self.vector_db = {}  # 简化的向量数据库
        self.logger = logging.getLogger(__name__)
    
    async def add_content(
        self,
        content_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加内容到语义搜索索引"""
        
        # 生成嵌入向量
        embedding_response = await self.ai_client.generate_embedding(content)
        
        if not embedding_response.success:
            raise Exception(f"生成嵌入向量失败: {embedding_response.error_message}")
        
        # 存储向量
        vector_obj = EmbeddingVector(
            content_id=content_id,
            content=content,
            vector=embedding_response.content,
            metadata=metadata or {}
        )
        
        self.vector_db[content_id] = vector_obj
        self.logger.debug(f"Added content {content_id} to semantic search index")
        
        return content_id
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        
        # 生成查询向量
        query_embedding = await self.ai_client.generate_embedding(query)
        if not query_embedding.success:
            return []
        
        # 计算相似度
        similarities = []
        for content_id, vector_obj in self.vector_db.items():
            similarity = self.cosine_similarity(query_embedding.content, vector_obj.vector)
            if similarity >= threshold:
                similarities.append({
                    "content_id": content_id,
                    "content": vector_obj.content,
                    "similarity": similarity,
                    "metadata": vector_obj.metadata
                })
        
        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:top_k]
    
    def remove_content(self, content_id: str) -> bool:
        """从索引中移除内容"""
        if content_id in self.vector_db:
            del self.vector_db[content_id]
            return True
        return False
    
    def get_index_size(self) -> int:
        """获取索引大小"""
        return len(self.vector_db)


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, ai_client: OpenAICompatibleClient, max_workers: int = 5):
        self.ai_client = ai_client
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
    
    async def batch_classify(
        self,
        texts: List[str],
        categories: List[str],
        progress_callback: Optional[Callable] = None
    ) -> List[ClassificationResult]:
        """批量文本分类"""
        
        results = []
        total = len(texts)
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建任务
            future_to_text = {
                executor.submit(self._classify_single, text, categories): text 
                for text in texts
            }
            
            # 收集结果
            for future in as_completed(future_to_text):
                text = future_to_text[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Classification failed for text: {text[:100]}... Error: {str(e)}")
                    results.append(ClassificationResult(
                        text=text,
                        primary_category="unknown",
                        confidence=0.0,
                        all_categories={},
                        tags=[],
                        reasoning=f"Error: {str(e)}"
                    ))
                
                # 进度回调
                if progress_callback:
                    progress = len(results) / total
                    progress_callback(progress, len(results), total)
        
        return results
    
    def _classify_single(self, text: str, categories: List[str]) -> ClassificationResult:
        """单条分类"""
        import asyncio
        
        try:
            response = asyncio.run(self.ai_client.classify_text(text, categories))
            
            if response.success:
                result_data = response.content
                return ClassificationResult(
                    text=text,
                    primary_category=result_data.get("category", "unknown"),
                    confidence=result_data.get("confidence", 0.0),
                    all_categories=result_data.get("all_categories", {}),
                    tags=result_data.get("tags", []),
                    reasoning=result_data.get("reasoning", "")
                )
            else:
                raise Exception(response.error_message)
                
        except Exception as e:
            raise Exception(f"Classification error: {str(e)}")
    
    async def batch_summarize(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """批量文档摘要"""
        
        summaries = []
        total = len(documents)
        
        for i, doc in enumerate(documents):
            try:
                # 构建文档摘要提示
                summary_prompt = f"""
请为以下文档生成简洁的摘要：

标题: {doc.get('title', 'N/A')}
内容: {doc.get('content', '')[:2000]}

请提供：
1. 主要摘要 (不超过200字)
2. 关键要点 (5-8个要点)
3. 情感倾向 (positive/neutral/negative)
4. 重要性评级 (1-10)
"""
                
                response = await self.ai_client.generate_text(
                    prompt=summary_prompt,
                    max_tokens=500,
                    temperature=0.3
                )
                
                if response.success:
                    summary_data = {
                        "doc_id": doc.get("id", f"doc_{i}"),
                        "title": doc.get("title", ""),
                        "summary": response.content,
                        "processed_at": datetime.now().isoformat(),
                        "success": True
                    }
                else:
                    summary_data = {
                        "doc_id": doc.get("id", f"doc_{i}"),
                        "title": doc.get("title", ""),
                        "summary": "",
                        "error": response.error_message,
                        "processed_at": datetime.now().isoformat(),
                        "success": False
                    }
                
                summaries.append(summary_data)
                
                if progress_callback:
                    progress = (i + 1) / total
                    progress_callback(progress, i + 1, total)
                
                # 添加小延迟
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Document summarization failed: {str(e)}")
                summaries.append({
                    "doc_id": doc.get("id", f"doc_{i}"),
                    "title": doc.get("title", ""),
                    "summary": "",
                    "error": str(e),
                    "processed_at": datetime.now().isoformat(),
                    "success": False
                })
        
        return summaries


class AIService:
    """AI服务整合类"""
    
    def __init__(self, api_key: str, **config_kwargs):
        # 初始化AI客户端
        self.ai_client = OpenAICompatibleClient(APIConfig(api_key=api_key, **config_kwargs))
        
        # 初始化各个组件
        self.repository_analyzer = RepositoryAnalyzer(self.ai_client)
        self.semantic_search = SemanticSearch(self.ai_client)
        self.batch_processor = BatchProcessor(self.ai_client)
        
        # 初始化任务队列
        self.task_queue = TaskQueue()
        self.task_executor = None
        self.is_running = False
        
        self.logger = logging.getLogger(__name__)
    
    async def start_task_processor(self):
        """启动任务处理器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.task_executor = threading.Thread(target=self._task_processor_loop, daemon=True)
        self.task_executor.start()
        self.logger.info("Task processor started")
    
    def stop_task_processor(self):
        """停止任务处理器"""
        self.is_running = False
        if self.task_executor:
            self.task_executor.join(timeout=5)
        self.logger.info("Task processor stopped")
    
    def _task_processor_loop(self):
        """任务处理循环"""
        asyncio.run(self._async_task_processor())
    
    async def _async_task_processor(self):
        """异步任务处理器"""
        while self.is_running:
            try:
                task = self.task_queue.get_next_task()
                if task:
                    await self._process_task(task)
                else:
                    await asyncio.sleep(1)  # 没有任务时等待
            except Exception as e:
                self.logger.error(f"Task processor error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_task(self, task: Task):
        """处理单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            if task.task_type == "repository_analysis":
                result = await self._process_repository_analysis_task(task)
            elif task.task_type == "text_classification":
                result = await self._process_classification_task(task)
            elif task.task_type == "embedding_generation":
                result = await self._process_embedding_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            
            # 执行回调
            if task.callback:
                task.callback(task)
                
        except Exception as e:
            task.error_message = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                self.task_queue.add_task(task)
            else:
                task.status = TaskStatus.FAILED
            
            self.logger.error(f"Task {task.task_id} failed: {str(e)}")
        
        finally:
            task.completed_at = datetime.now()
    
    async def _process_repository_analysis_task(self, task: Task) -> RepositorySummary:
        """处理仓库分析任务"""
        repo_info = task.data.get("repo_info")
        readme_content = task.data.get("readme_content", "")
        file_structure = task.data.get("file_structure", "")
        
        return await self.repository_analyzer.analyze_repository(
            repo_info, readme_content, file_structure
        )
    
    async def _process_classification_task(self, task: Task) -> List[ClassificationResult]:
        """处理分类任务"""
        texts = task.data.get("texts", [])
        categories = task.data.get("categories", [])
        
        return await self.batch_processor.batch_classify(texts, categories)
    
    async def _process_embedding_task(self, task: Task) -> List[str]:
        """处理嵌入向量生成任务"""
        contents = task.data.get("contents", [])
        content_ids = task.data.get("content_ids", [])
        
        results = []
        for i, content in enumerate(contents):
            content_id = content_ids[i] if i < len(content_ids) else f"embed_{i}"
            await self.semantic_search.add_content(content_id, content)
            results.append(content_id)
        
        return results
    
    # 公开的API方法
    
    async def analyze_repository(
        self,
        repo_info: Dict[str, Any],
        readme_content: str = "",
        file_structure: str = ""
    ) -> RepositorySummary:
        """分析仓库（直接执行）"""
        return await self.repository_analyzer.analyze_repository(
            repo_info, readme_content, file_structure
        )
    
    def create_analysis_task(
        self,
        repo_info: Dict[str, Any],
        readme_content: str = "",
        file_structure: str = "",
        priority: Priority = Priority.MEDIUM,
        callback: Optional[Callable] = None
    ) -> str:
        """创建仓库分析任务"""
        task_id = hashlib.md5(f"{time.time()}_{repo_info.get('name', '')}".encode()).hexdigest()
        
        task = Task(
            task_id=task_id,
            task_type="repository_analysis",
            data={
                "repo_info": repo_info,
                "readme_content": readme_content,
                "file_structure": file_structure
            },
            priority=priority,
            callback=callback
        )
        
        if self.task_queue.add_task(task):
            return task_id
        else:
            raise Exception("Failed to add task to queue")
    
    async def batch_classify_texts(
        self,
        texts: List[str],
        categories: List[str]
    ) -> List[ClassificationResult]:
        """批量文本分类（直接执行）"""
        return await self.batch_processor.batch_classify(texts, categories)
    
    async def add_to_search_index(
        self,
        content_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加到语义搜索索引"""
        return await self.semantic_search.add_content(content_id, content, metadata)
    
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        return await self.semantic_search.search(query, top_k, threshold)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.task_queue.get_task(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "retry_count": task.retry_count,
            "error_message": task.error_message
        }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        return {
            "queue_size": self.task_queue.get_queue_size(),
            "pending_tasks": len(self.task_queue.get_tasks_by_status(TaskStatus.PENDING)),
            "running_tasks": len(self.task_queue.get_tasks_by_status(TaskStatus.RUNNING)),
            "completed_tasks": len(self.task_queue.get_tasks_by_status(TaskStatus.COMPLETED)),
            "failed_tasks": len(self.task_queue.get_tasks_by_status(TaskStatus.FAILED))
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取AI使用统计"""
        return self.ai_client.get_usage_stats()
    
    async def health_check(self) -> bool:
        """健康检查"""
        return await self.ai_client.health_check()
    
    def cleanup(self):
        """清理资源"""
        self.stop_task_processor()
        self.ai_client.clear_cache()