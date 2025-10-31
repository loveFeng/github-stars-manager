"""
AI 任务队列系统使用示例
演示如何使用任务队列进行批量仓库分析
"""

import asyncio
import logging
from services.ai_task_manager import create_ai_task_manager
from services.task_queue import TaskType, Priority, TaskConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def example_1_basic_usage():
    """示例1: 基本使用"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 创建管理器
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=3,
        budget_limit=10.0
    )
    
    # 提交任务
    task_id = await manager.submit_task(
        task_type=TaskType.REPOSITORY_ANALYSIS,
        data={
            "repo_info": {
                "name": "flask",
                "description": "A micro web framework",
                "language": "Python",
                "stargazers_count": 60000
            },
            "readme_content": "# Flask\n\nFlask is a lightweight WSGI web application framework."
        },
        priority=Priority.HIGH
    )
    
    print(f"✓ 任务已提交: {task_id}")
    
    # 等待完成
    result = await manager.wait_for_task(task_id, timeout=60)
    
    if result:
        print(f"✓ 分析完成!")
        print(f"  摘要: {result.get('summary', 'N/A')[:100]}...")
    else:
        print("✗ 任务失败或超时")
    
    # 停止管理器
    await manager.stop()
    print()


async def example_2_batch_analysis():
    """示例2: 批量仓库分析"""
    print("=" * 60)
    print("示例2: 批量仓库分析")
    print("=" * 60)
    
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=3,
        budget_limit=20.0
    )
    
    # 准备仓库列表
    repositories = [
        {
            "name": "flask",
            "description": "A micro web framework",
            "language": "Python",
            "stargazers_count": 60000,
            "readme": "# Flask\n\nFlask is a lightweight..."
        },
        {
            "name": "django",
            "description": "The Web framework for perfectionists",
            "language": "Python",
            "stargazers_count": 70000,
            "readme": "# Django\n\nDjango is a high-level..."
        },
        {
            "name": "fastapi",
            "description": "Modern, fast web framework",
            "language": "Python",
            "stargazers_count": 50000,
            "readme": "# FastAPI\n\nFastAPI is a modern..."
        }
    ]
    
    # 进度回调
    async def on_progress(progress, current, total):
        bar_length = 40
        filled = int(bar_length * progress)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\r进度: [{bar}] {progress*100:.0f}% ({current}/{total})", end='')
    
    # 提交批量分析
    task_id = await manager.submit_task(
        task_type=TaskType.BATCH_ANALYSIS,
        data={"repositories": repositories},
        priority=Priority.HIGH,
        config=TaskConfig(
            progress_callback=on_progress,
            max_retries=3
        )
    )
    
    print(f"批量分析任务已提交: {task_id}")
    
    # 等待完成
    results = await manager.wait_for_task(task_id, timeout=300)
    
    print("\n")  # 换行
    
    if results:
        print(f"✓ 批量分析完成! 共 {len(results)} 个仓库")
        for i, result in enumerate(results, 1):
            if result['success']:
                print(f"  {i}. {result['repo_name']}: ✓")
            else:
                print(f"  {i}. {result['repo_name']}: ✗ ({result.get('error', 'Unknown')})")
    
    # 显示统计
    stats = manager.get_statistics()
    print(f"\n统计信息:")
    print(f"  总成本: ${stats['cost']['total']['cost']:.4f}")
    print(f"  成功率: {stats['performance']['success_rate']:.1f}%")
    
    await manager.stop()
    print()


async def example_3_concurrent_tasks():
    """示例3: 并发任务处理"""
    print("=" * 60)
    print("示例3: 并发任务处理")
    print("=" * 60)
    
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=5,
        budget_limit=30.0
    )
    
    # 提交多个独立任务
    task_count = 10
    task_ids = []
    
    print(f"提交 {task_count} 个任务...")
    
    for i in range(task_count):
        task_id = await manager.submit_task(
            task_type=TaskType.REPOSITORY_ANALYSIS,
            data={
                "repo_info": {
                    "name": f"repo-{i+1}",
                    "description": f"Repository {i+1}",
                    "language": "Python"
                },
                "readme_content": f"# Repo {i+1}\n\nExample repository"
            },
            priority=Priority.HIGH if i < 3 else Priority.MEDIUM
        )
        task_ids.append(task_id)
    
    print(f"✓ 已提交 {len(task_ids)} 个任务\n")
    
    # 实时监控
    print("处理中...")
    last_completed = 0
    
    while True:
        stats = manager.get_statistics()
        
        # 获取完成数量
        completed = stats['tasks']['by_status'].get('completed', 0)
        
        # 只在有变化时打印
        if completed != last_completed:
            print(f"  已完成: {completed}/{task_count}")
            last_completed = completed
        
        # 检查是否全部完成
        pending = stats['queue']['size']
        running = stats['concurrency']['running_tasks']
        if pending == 0 and running == 0:
            break
        
        await asyncio.sleep(0.5)
    
    print(f"\n✓ 所有任务已完成!")
    
    # 统计结果
    success_count = 0
    failed_count = 0
    
    for task_id in task_ids:
        status = manager.get_task_status(task_id)
        if status['status'] == 'completed':
            success_count += 1
        elif status['status'] == 'failed':
            failed_count += 1
    
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    
    await manager.stop()
    print()


async def example_4_cost_control():
    """示例4: 成本控制"""
    print("=" * 60)
    print("示例4: 成本控制")
    print("=" * 60)
    
    # 设置严格的预算
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=3,
        budget_limit=2.0  # 总预算 $2
    )
    
    # 设置每日和每小时限制
    manager.adjust_settings(
        daily_limit=1.0,
        hourly_limit=0.5
    )
    
    print("预算设置:")
    print(f"  总预算: $2.00")
    print(f"  日预算: $1.00")
    print(f"  时预算: $0.50\n")
    
    task_count = 0
    rejected_count = 0
    
    # 持续提交直到预算耗尽
    for i in range(20):
        try:
            task_id = await manager.submit_task(
                task_type=TaskType.REPOSITORY_ANALYSIS,
                data={
                    "repo_info": {"name": f"repo-{i+1}"},
                    "readme_content": "Example"
                }
            )
            task_count += 1
            
            # 显示成本
            stats = manager.get_statistics()
            cost = stats['cost']['total']
            print(f"任务 {i+1}: ✓ (成本: ${cost['cost']:.4f} / ${cost['limit']:.2f})")
            
        except Exception as e:
            rejected_count += 1
            print(f"任务 {i+1}: ✗ ({str(e)})")
            break
    
    print(f"\n结果:")
    print(f"  提交成功: {task_count}")
    print(f"  被拒绝: {rejected_count}")
    
    # 等待完成
    while True:
        stats = manager.get_statistics()
        if stats['queue']['size'] == 0 and stats['concurrency']['running_tasks'] == 0:
            break
        await asyncio.sleep(1)
    
    # 最终成本
    final_stats = manager.get_statistics()
    print(f"  最终成本: ${final_stats['cost']['total']['cost']:.4f}")
    
    await manager.stop()
    print()


async def example_5_task_control():
    """示例5: 任务控制（取消、暂停）"""
    print("=" * 60)
    print("示例5: 任务控制")
    print("=" * 60)
    
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=2,
        budget_limit=10.0
    )
    
    # 提交多个任务
    task_ids = []
    for i in range(10):
        task_id = await manager.submit_task(
            task_type=TaskType.REPOSITORY_ANALYSIS,
            data={
                "repo_info": {"name": f"repo-{i+1}"},
                "readme_content": "Example"
            }
        )
        task_ids.append(task_id)
    
    print(f"✓ 已提交 {len(task_ids)} 个任务")
    
    # 等待一会儿
    await asyncio.sleep(2)
    
    # 取消部分任务
    cancel_ids = task_ids[5:]
    print(f"\n取消 {len(cancel_ids)} 个任务...")
    results = await manager.cancel_batch(cancel_ids)
    
    cancelled_count = sum(1 for success in results.values() if success)
    print(f"✓ 成功取消 {cancelled_count} 个任务")
    
    # 暂停处理
    print("\n暂停任务处理 3 秒...")
    manager.pause()
    await asyncio.sleep(3)
    
    # 恢复处理
    print("恢复任务处理...")
    manager.resume()
    
    # 等待完成
    while True:
        stats = manager.get_statistics()
        if stats['queue']['size'] == 0 and stats['concurrency']['running_tasks'] == 0:
            break
        await asyncio.sleep(0.5)
    
    # 统计
    stats = manager.get_statistics()
    print(f"\n最终统计:")
    print(f"  已完成: {stats['tasks']['by_status'].get('completed', 0)}")
    print(f"  已取消: {stats['tasks']['by_status'].get('cancelled', 0)}")
    print(f"  失败: {stats['tasks']['by_status'].get('failed', 0)}")
    
    await manager.stop()
    print()


async def example_6_monitoring():
    """示例6: 实时监控"""
    print("=" * 60)
    print("示例6: 实时监控")
    print("=" * 60)
    
    manager = await create_ai_task_manager(
        api_key="your-openai-api-key",
        max_concurrent=3,
        budget_limit=15.0
    )
    
    # 提交任务
    for i in range(15):
        await manager.submit_task(
            task_type=TaskType.REPOSITORY_ANALYSIS,
            data={
                "repo_info": {"name": f"repo-{i+1}"},
                "readme_content": "Example"
            }
        )
    
    print("✓ 已提交 15 个任务\n")
    print("实时监控 (每秒更新):")
    print("-" * 60)
    
    # 监控循环
    while True:
        stats = manager.get_statistics()
        
        # 清屏效果 (简化版)
        print("\r" + " " * 100, end="")
        
        # 显示状态
        queue_size = stats['queue']['size']
        running = stats['concurrency']['running_tasks']
        completed = stats['tasks']['by_status'].get('completed', 0)
        failed = stats['tasks']['by_status'].get('failed', 0)
        cost = stats['cost']['total']['cost']
        
        status_line = (
            f"\r队列: {queue_size:2d} | "
            f"运行: {running} | "
            f"完成: {completed:2d} | "
            f"失败: {failed:2d} | "
            f"成本: ${cost:.4f}"
        )
        print(status_line, end="", flush=True)
        
        # 检查是否完成
        if queue_size == 0 and running == 0:
            break
        
        await asyncio.sleep(1)
    
    print("\n" + "-" * 60)
    print("✓ 所有任务已完成!\n")
    
    # 详细统计
    final_stats = manager.get_statistics()
    print("最终统计:")
    print(f"  总处理: {final_stats['performance']['total_processed']}")
    print(f"  成功: {final_stats['performance']['total_succeeded']}")
    print(f"  失败: {final_stats['performance']['total_failed']}")
    print(f"  成功率: {final_stats['performance']['success_rate']:.1f}%")
    print(f"  总成本: ${final_stats['cost']['total']['cost']:.4f}")
    
    await manager.stop()
    print()


async def run_all_examples():
    """运行所有示例"""
    print("\n")
    print("*" * 60)
    print("AI 任务队列系统 - 使用示例")
    print("*" * 60)
    print("\n")
    
    try:
        await example_1_basic_usage()
        await example_2_batch_analysis()
        await example_3_concurrent_tasks()
        await example_4_cost_control()
        await example_5_task_control()
        await example_6_monitoring()
        
        print("=" * 60)
        print("所有示例运行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("\n请确保:")
        print("1. 已安装所有依赖: pip install aiohttp numpy")
        print("2. 已设置有效的 OpenAI API 密钥")
        print("3. API 密钥有足够的配额")


if __name__ == "__main__":
    # 运行所有示例
    asyncio.run(run_all_examples())
    
    # 或者运行单个示例:
    # asyncio.run(example_1_basic_usage())
    # asyncio.run(example_2_batch_analysis())
    # asyncio.run(example_3_concurrent_tasks())
    # asyncio.run(example_4_cost_control())
    # asyncio.run(example_5_task_control())
    # asyncio.run(example_6_monitoring())
