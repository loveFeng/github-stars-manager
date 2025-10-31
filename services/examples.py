#!/usr/bin/env python3
"""
AI API集成服务使用示例
演示如何使用AI客户端和服务功能
"""

import asyncio
import json
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 导入AI服务
from services import AIService, Priority, ModelType


async def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 初始化AI服务（需要设置API密钥）
    api_key = "your-openai-api-key-here"  # 替换为实际的API密钥
    ai_service = AIService(
        api_key=api_key,
        timeout=60,
        rate_limit=30
    )
    
    # 健康检查
    if await ai_service.health_check():
        print("✓ AI服务连接正常")
    else:
        print("✗ AI服务连接失败")
        return
    
    # 获取使用统计
    stats = ai_service.get_usage_stats()
    print(f"当前使用统计: {stats}")
    

async def example_text_generation():
    """文本生成示例"""
    print("\n=== 文本生成示例 ===")
    
    api_key = "your-openai-api-key-here"
    ai_service = AIService(api_key=api_key)
    
    try:
        # 简单文本生成
        response = await ai_service.ai_client.generate_text(
            prompt="解释什么是机器学习",
            model=ModelType.GPT_3_5_TURBO,
            max_tokens=500
        )
        
        if response.success:
            print(f"生成的文本: {response.content}")
            print(f"处理时间: {response.processing_time:.2f}秒")
        else:
            print(f"生成失败: {response.error_message}")
            
    except Exception as e:
        print(f"文本生成错误: {str(e)}")


async def example_repository_analysis():
    """仓库分析示例"""
    print("\n=== 仓库分析示例 ===")
    
    api_key = "your-openai-api-key-here"
    ai_service = AIService(api_key=api_key)
    
    # 模拟GitHub仓库信息
    repo_info = {
        "name": "awesome-python",
        "description": "A curated list of awesome Python frameworks, libraries, software and resources",
        "language": "Python",
        "html_url": "https://github.com/vinta/awesome-python",
        "stargazers_count": 152000,
        "updated_at": "2023-12-01T10:00:00Z",
        "license": {"name": "MIT"}
    }
    
    readme_content = """
# Awesome Python

A curated list of awesome Python frameworks, libraries, software and resources.

## Web Frameworks

- Django - The Web framework for perfectionists with deadlines.
- Flask - A lightweight WSGI web application framework.
- FastAPI - FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints.
"""
    
    try:
        # 直接分析
        summary = await ai_service.analyze_repository(repo_info, readme_content)
        
        print(f"仓库名称: {summary.repo_name}")
        print(f"描述: {summary.description}")
        print(f"主要语言: {summary.main_language}")
        print(f"技术栈: {', '.join(summary.technologies)}")
        print(f"Star数: {summary.stars}")
        print(f"总体摘要: {summary.summary}")
        
    except Exception as e:
        print(f"仓库分析错误: {str(e)}")
        
        # 任务队列方式
        try:
            task_id = ai_service.create_analysis_task(
                repo_info=repo_info,
                readme_content=readme_content,
                priority=Priority.HIGH
            )
            
            print(f"已创建分析任务: {task_id}")
            
            # 启动任务处理器
            await ai_service.start_task_processor()
            
            # 等待任务完成
            while True:
                status = ai_service.get_task_status(task_id)
                if status and status["status"] in ["completed", "failed"]:
                    break
                
                print(f"任务状态: {status['status']}")
                await asyncio.sleep(2)
            
            if status["status"] == "completed":
                print("仓库分析完成")
            else:
                print(f"任务失败: {status.get('error_message')}")
                
        except Exception as task_e:
            print(f"任务处理错误: {str(task_e)}")
        finally:
            ai_service.stop_task_processor()


async def example_semantic_search():
    """语义搜索示例"""
    print("\n=== 语义搜索示例 ===")
    
    api_key = "your-openai-api-key-here"
    ai_service = AIService(api_key=api_key)
    
    # 添加一些示例内容到搜索索引
    documents = [
        {
            "id": "doc1",
            "content": "Python是一种高级编程语言，具有简洁的语法和强大的功能",
            "metadata": {"type": "language_info", "language": "zh"}
        },
        {
            "id": "doc2", 
            "content": "机器学习是人工智能的一个分支，让计算机从数据中学习",
            "metadata": {"type": "ai_concept", "category": "ml"}
        },
        {
            "id": "doc3",
            "content": "深度学习使用神经网络来模拟人脑的学习过程",
            "metadata": {"type": "ai_concept", "category": "dl"}
        }
    ]
    
    try:
        # 添加到索引
        for doc in documents:
            await ai_service.add_to_search_index(
                content_id=doc["id"],
                content=doc["content"],
                metadata=doc["metadata"]
            )
        
        print(f"已添加 {len(documents)} 个文档到搜索索引")
        
        # 执行搜索
        query = "神经网络和人工智能"
        results = await ai_service.semantic_search(query, top_k=5, threshold=0.5)
        
        print(f"\n搜索查询: '{query}'")
        print(f"找到 {len(results)} 个相关结果:")
        
        for result in results:
            print(f"- 内容ID: {result['content_id']}")
            print(f"  相似度: {result['similarity']:.3f}")
            print(f"  内容: {result['content']}")
            print(f"  元数据: {result['metadata']}")
            print()
            
    except Exception as e:
        print(f"语义搜索错误: {str(e)}")


async def example_batch_classification():
    """批量分类示例"""
    print("\n=== 批量分类示例 ===")
    
    api_key = "your-openai-api-key-here"
    ai_service = AIService(api_key=api_key)
    
    # 示例文本
    texts = [
        "这部电影太棒了！剧情精彩，演员演技出色",
        "今天的天气真好，阳光明媚",
        "这个产品设计有问题，使用体验很差",
        "公司业绩持续增长，股价表现优异",
        "技术文档写得很清楚，容易理解"
    ]
    
    categories = ["科技", "娱乐", "商业", "生活", "教育"]
    
    try:
        def progress_callback(progress: float, current: int, total: int):
            print(f"分类进度: {progress:.1%} ({current}/{total})")
        
        results = await ai_service.batch_classify_texts(texts, categories)
        
        print(f"分类结果 ({len(results)} 个):")
        for i, result in enumerate(results):
            print(f"{i+1}. 文本: {result.text[:50]}...")
            print(f"   主要类别: {result.primary_category}")
            print(f"   置信度: {result.confidence:.2f}")
            print(f"   标签: {', '.join(result.tags)}")
            print(f"   推理: {result.reasoning}")
            print()
            
    except Exception as e:
        print(f"批量分类错误: {str(e)}")


async def example_cost_control():
    """成本控制示例"""
    print("\n=== 成本控制示例 ===")
    
    api_key = "your-openai-api-key-here"
    ai_service = AIService(api_key=api_key, cost_budget=10.0)  # 设置10美元预算
    
    try:
        # 执行几个操作
        operations = [
            ("生成文本1", lambda: ai_service.ai_client.generate_text("Hello world", max_tokens=50)),
            ("生成文本2", lambda: ai_service.ai_client.generate_text("What is AI?", max_tokens=50)),
            ("生成嵌入1", lambda: ai_service.ai_client.generate_embedding("Sample text for embedding")),
        ]
        
        total_cost = 0
        for op_name, operation in operations:
            try:
                response = operation()
                if response.success:
                    cost_increase = response.usage.get("total_tokens", 0) * 0.001 / 1000  # 简单估算
                    total_cost += cost_increase
                    print(f"✓ {op_name} - 成本: ${cost_increase:.4f}")
                else:
                    print(f"✗ {op_name} 失败: {response.error_message}")
            except Exception as e:
                print(f"✗ {op_name} 异常: {str(e)}")
        
        # 检查预算
        stats = ai_service.get_usage_stats()
        print(f"\n成本统计:")
        print(f"总成本: ${stats['total_cost']:.4f}")
        print(f"预算限制: ${stats['cost_budget']:.2f}")
        print(f"剩余预算: ${stats['budget_remaining']:.2f}")
        print(f"总请求数: {stats['total_requests']}")
        print(f"总Token数: {stats['total_tokens']}")
        
    except Exception as e:
        print(f"成本控制错误: {str(e)}")


async def example_task_queue_management():
    """任务队列管理示例"""
    print("\n=== 任务队列管理示例 ===")
    
    api_key = "your-openai-api-key-here"
    ai_service = AIService(api_key=api_key)
    
    try:
        # 创建多个任务
        tasks = []
        for i in range(3):
            repo_info = {
                "name": f"test-repo-{i}",
                "description": f"测试仓库 {i}",
                "language": "Python"
            }
            
            task_id = ai_service.create_analysis_task(
                repo_info=repo_info,
                priority=Priority.MEDIUM,
                callback=lambda t: print(f"任务 {t.task_id} 完成")
            )
            tasks.append(task_id)
            print(f"创建任务: {task_id}")
        
        # 启动处理器
        await ai_service.start_task_processor()
        
        # 监控任务状态
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < 30:  # 最多等待30秒
            queue_stats = ai_service.get_queue_stats()
            print(f"队列状态: {queue_stats}")
            
            # 检查是否有任务完成
            completed_count = queue_stats["completed_tasks"]
            if completed_count >= len(tasks):
                print("所有任务完成")
                break
            
            await asyncio.sleep(3)
        
        # 获取最终状态
        for task_id in tasks:
            status = ai_service.get_task_status(task_id)
            print(f"任务 {task_id} 最终状态: {status['status']}")
            
    except Exception as e:
        print(f"任务队列管理错误: {str(e)}")
    finally:
        ai_service.stop_task_processor()


async def main():
    """主函数"""
    print("AI API集成服务使用示例")
    print("=" * 50)
    
    # 注意：运行示例需要设置真实的API密钥
    print("⚠️  注意：运行示例需要设置真实的OpenAI API密钥")
    print("请将代码中的 'your-openai-api-key-here' 替换为实际密钥")
    print()
    
    # 可以运行特定示例
    examples = [
        ("基本使用", example_basic_usage),
        ("文本生成", example_text_generation),
        ("仓库分析", example_repository_analysis),
        ("语义搜索", example_semantic_search),
        ("批量分类", example_batch_classification),
        ("成本控制", example_cost_control),
        ("任务队列", example_task_queue_management),
    ]
    
    print("可用的示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    print("\n要运行特定示例，请取消相应函数的注释")
    
    # 运行示例（取消注释以执行）
    # await example_basic_usage()
    # await example_text_generation()
    # await example_repository_analysis()
    # await example_semantic_search()
    # await example_batch_classification()
    # await example_cost_control()
    # await example_task_queue_management()


if __name__ == "__main__":
    asyncio.run(main())