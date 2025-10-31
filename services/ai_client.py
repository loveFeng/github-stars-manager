"""
AI API 客户端 - OpenAI 兼容接口实现
支持文本生成、嵌入向量、分类等功能
"""

import asyncio
import json
import time
import logging
from typing import List, Dict, Any, Optional, Union, AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import aiohttp
from enum import Enum


class ModelType(Enum):
    """支持的模型类型"""
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"


class TaskType(Enum):
    """AI任务类型"""
    TEXT_GENERATION = "text_generation"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"


@dataclass
class APIConfig:
    """API配置"""
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: int = 60  # 每分钟请求数限制
    max_tokens: int = 4000


@dataclass
class UsageStats:
    """API使用统计"""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    last_request_time: Optional[datetime] = None
    cost_budget: float = 100.0  # 默认预算100美元


@dataclass
class APIResponse:
    """API响应"""
    content: Union[str, List[float], Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    task_type: Optional[TaskType] = None
    processing_time: float = 0.0
    success: bool = False
    error_message: Optional[str] = None


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        """获取请求许可"""
        now = time.time()
        # 清理过期的请求记录
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        # 检查是否超出限制
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self.acquire()
        
        # 记录当前请求
        self.requests.append(now)


class OpenAICompatibleClient:
    """OpenAI兼容API客户端"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.usage_stats = UsageStats()
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.logger = logging.getLogger(__name__)
        
        # 缓存配置
        self._cache = {}
        self._cache_ttl = 3600  # 1小时缓存
        
        # 成本配置
        self.model_costs = {
            ModelType.GPT_3_5_TURBO: {"input": 0.0015, "output": 0.002},  # per 1K tokens
            ModelType.GPT_4: {"input": 0.03, "output": 0.06},
            ModelType.GPT_4_TURBO: {"input": 0.01, "output": 0.03},
            ModelType.TEXT_EMBEDDING_3_SMALL: {"input": 0.02, "output": 0.0},  # per 1M tokens
            ModelType.TEXT_EMBEDDING_3_LARGE: {"input": 0.13, "output": 0.0},
        }
    
    async def _make_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> APIResponse:
        """发送API请求"""
        start_time = time.time()
        
        # 速率限制
        await self.rate_limiter.acquire()
        
        # 检查成本预算
        if self.usage_stats.total_cost >= self.usage_stats.cost_budget:
            raise Exception(f"成本预算超限: ${self.usage_stats.total_cost:.2f} >= ${self.usage_stats.cost_budget:.2f}")
        
        url = f"{self.config.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        timeout_obj = aiohttp.ClientTimeout(total=timeout or self.config.timeout)
        
        for attempt in range(self.config.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.post(url, headers=headers, json=data) as response:
                        response_data = await response.json()
                        
                        if response.status == 200:
                            # 更新使用统计
                            usage = response_data.get("usage", {})
                            self._update_usage_stats(response_data.get("model", ""), usage)
                            
                            processing_time = time.time() - start_time
                            return APIResponse(
                                content=response_data,
                                usage=usage,
                                model=response_data.get("model"),
                                processing_time=processing_time,
                                success=True
                            )
                        else:
                            error_msg = response_data.get("error", {}).get("message", "Unknown error")
                            if attempt < self.config.max_retries - 1:
                                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                                continue
                            
                            return APIResponse(
                                content="",
                                processing_time=time.time() - start_time,
                                success=False,
                                error_message=f"HTTP {response.status}: {error_msg}"
                            )
                            
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    continue
                
                return APIResponse(
                    content="",
                    processing_time=time.time() - start_time,
                    success=False,
                    error_message=str(e)
                )
        
        return APIResponse(
            content="",
            processing_time=time.time() - start_time,
            success=False,
            error_message="Max retries exceeded"
        )
    
    def _get_cache_key(self, task_type: TaskType, data: Dict[str, Any]) -> str:
        """生成缓存键"""
        cache_string = f"{task_type.value}:{json.dumps(data, sort_keys=True)}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        cache_time = cache_entry.get("timestamp", 0)
        return time.time() - cache_time < self._cache_ttl
    
    def _update_usage_stats(self, model: str, usage: Dict[str, int]):
        """更新使用统计"""
        self.usage_stats.total_requests += 1
        
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        
        self.usage_stats.total_tokens += total_tokens
        
        # 计算成本
        model_type = None
        for mt in ModelType:
            if mt.value in model:
                model_type = mt
                break
        
        if model_type and model_type in self.model_costs:
            costs = self.model_costs[model_type]
            cost = (prompt_tokens / 1000) * costs["input"] + (completion_tokens / 1000) * costs["output"]
            self.usage_stats.total_cost += cost
        
        self.usage_stats.last_request_time = datetime.now()
    
    async def generate_text(
        self,
        prompt: str,
        model: Union[str, ModelType] = ModelType.GPT_3_5_TURBO,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> APIResponse:
        """生成文本"""
        
        if isinstance(model, ModelType):
            model = model.value
        
        data = {
            "model": model,
            "messages": [],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if system_prompt:
            data["messages"].append({"role": "system", "content": system_prompt})
        
        data["messages"].append({"role": "user", "content": prompt})
        
        # 检查缓存
        cache_key = self._get_cache_key(TaskType.TEXT_GENERATION, data)
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            return self._cache[cache_key]["response"]
        
        response = await self._make_request("chat/completions", data)
        
        if response.success:
            response.content = response.content["choices"][0]["message"]["content"]
            response.task_type = TaskType.TEXT_GENERATION
            
            # 缓存响应
            self._cache[cache_key] = {
                "response": response,
                "timestamp": time.time()
            }
        
        return response
    
    async def generate_embedding(
        self,
        text: str,
        model: Union[str, ModelType] = ModelType.TEXT_EMBEDDING_3_SMALL
    ) -> APIResponse:
        """生成文本嵌入向量"""
        
        if isinstance(model, ModelType):
            model = model.value
        
        data = {
            "model": model,
            "input": text
        }
        
        # 检查缓存
        cache_key = self._get_cache_key(TaskType.EMBEDDING, data)
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            return self._cache[cache_key]["response"]
        
        response = await self._make_request("embeddings", data)
        
        if response.success:
            response.content = response.content["data"][0]["embedding"]
            response.task_type = TaskType.EMBEDDING
            
            # 缓存响应
            self._cache[cache_key] = {
                "response": response,
                "timestamp": time.time()
            }
        
        return response
    
    async def classify_text(
        self,
        text: str,
        categories: List[str],
        model: Union[str, ModelType] = ModelType.GPT_3_5_TURBO
    ) -> APIResponse:
        """文本分类"""
        
        if isinstance(model, ModelType):
            model = model.value
        
        system_prompt = f"""
你是一个文本分类专家。请根据以下类别对文本进行分类：

类别列表：{', '.join(categories)}

请返回JSON格式结果，包含：
- category: 最佳匹配的类别
- confidence: 置信度 (0-1)
- reasoning: 分类理由
"""
        
        user_prompt = f"""
请对以下文本进行分类：

文本内容：{text}

只返回JSON格式，不要其他说明。
"""
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        response = await self._make_request("chat/completions", data)
        
        if response.success:
            try:
                response.content = json.loads(response.content["choices"][0]["message"]["content"])
                response.task_type = TaskType.CLASSIFICATION
            except json.JSONDecodeError:
                response.success = False
                response.error_message = "Failed to parse JSON response"
        
        return response
    
    async def batch_generate_embeddings(
        self,
        texts: List[str],
        model: Union[str, ModelType] = ModelType.TEXT_EMBEDDING_3_SMALL,
        batch_size: int = 100
    ) -> List[APIResponse]:
        """批量生成嵌入向量"""
        
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.generate_embedding(text, model) for text in batch_texts],
                return_exceptions=True
            )
            
            # 处理异常
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append(APIResponse(
                        content=[],
                        success=False,
                        error_message=str(result)
                    ))
                else:
                    results.append(result)
            
            # 添加小延迟避免过载
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        return results
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "total_requests": self.usage_stats.total_requests,
            "total_tokens": self.usage_stats.total_tokens,
            "total_cost": self.usage_stats.total_cost,
            "cost_budget": self.usage_stats.cost_budget,
            "budget_remaining": self.usage_stats.cost_budget - self.usage_stats.total_cost,
            "last_request_time": self.usage_stats.last_request_time.isoformat() if self.usage_stats.last_request_time else None
        }
    
    def reset_usage_stats(self):
        """重置使用统计"""
        self.usage_stats = UsageStats()
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.generate_text("Hello", max_tokens=5)
            return response.success
        except Exception:
            return False


# 创建默认客户端实例的辅助函数
def create_client(api_key: str, **kwargs) -> OpenAICompatibleClient:
    """创建AI客户端实例"""
    config = APIConfig(api_key=api_key, **kwargs)
    return OpenAICompatibleClient(config)