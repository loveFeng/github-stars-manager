"""
星标仓库自动同步功能 - 测试示例
演示如何使用同步服务和调度器
"""

import logging
import time
import sys
import os
from datetime import datetime

# 添加服务路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_service import GitHubService, AIConfig
from sync_service import (
    SyncService, SyncConfig, SyncMode, ConflictStrategy, 
    DatabaseManager, SyncProgress
)
from sync_scheduler import (
    SyncScheduler, SchedulerConfig, ScheduleInterval,
    SyncHistoryRecord
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_sync():
    """测试基础同步功能"""
    logger.info("=" * 60)
    logger.info("测试 1: 基础同步功能")
    logger.info("=" * 60)
    
    try:
        # 初始化服务
        github_token = os.getenv("GITHUB_TOKEN", "your-github-token")
        
        if github_token == "your-github-token":
            logger.warning("请设置环境变量 GITHUB_TOKEN 或修改代码中的 token")
            logger.info("跳过测试...")
            return
        
        github_service = GitHubService(token=github_token)
        db_manager = DatabaseManager(db_path="./test_data/github_stars.db")
        
        # 创建同步配置
        sync_config = SyncConfig(
            mode=SyncMode.SMART,
            conflict_strategy=ConflictStrategy.MERGE,
            batch_size=10,
            max_retries=2
        )
        
        sync_service = SyncService(github_service, db_manager, sync_config)
        
        # 添加进度回调
        def show_progress(progress: SyncProgress):
            percentage = progress.get_progress_percentage()
            logger.info(f"进度: {percentage:.1f}% - "
                       f"处理: {progress.processed_repos}/{progress.total_repos} - "
                       f"新增: {progress.added_repos} - "
                       f"更新: {progress.updated_repos}")
        
        sync_service.add_progress_callback(show_progress)
        
        # 执行同步
        logger.info("开始同步...")
        history = sync_service.sync_repositories()
        
        # 显示结果
        logger.info("\n同步结果:")
        logger.info(f"  状态: {history.status}")
        logger.info(f"  处理: {history.items_processed}")
        logger.info(f"  新增: {history.items_added}")
        logger.info(f"  更新: {history.items_updated}")
        logger.info(f"  耗时: {history.execution_time_ms}ms")
        
        # 检查冲突
        conflicts = sync_service.get_unresolved_conflicts()
        if conflicts:
            logger.info(f"\n发现 {len(conflicts)} 个冲突")
            for conflict in conflicts[:5]:
                logger.info(f"  - {conflict.repo_full_name}: {conflict.field_name}")
        
        logger.info("✅ 基础同步测试完成\n")
        
    except Exception as e:
        logger.error(f"❌ 基础同步测试失败: {e}\n")


def test_scheduler():
    """测试调度器功能"""
    logger.info("=" * 60)
    logger.info("测试 2: 调度器功能")
    logger.info("=" * 60)
    
    try:
        github_token = os.getenv("GITHUB_TOKEN", "your-github-token")
        
        if github_token == "your-github-token":
            logger.warning("请设置环境变量 GITHUB_TOKEN 或修改代码中的 token")
            logger.info("跳过测试...")
            return
        
        # 初始化服务
        github_service = GitHubService(token=github_token)
        db_manager = DatabaseManager(db_path="./test_data/github_stars.db")
        sync_service = SyncService(github_service, db_manager)
        
        # 创建调度器配置
        scheduler_config = SchedulerConfig(
            enabled=True,
            interval=ScheduleInterval.MANUAL,  # 手动模式用于测试
            sync_on_startup=False,
            retry_on_failure=True,
            max_retry_attempts=2
        )
        
        scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)
        
        # 设置回调
        def on_sync_start():
            logger.info("🔄 同步开始...")
        
        def on_sync_complete(history: SyncHistoryRecord):
            logger.info(f"✅ 同步完成: {history.status}")
            logger.info(f"   处理: {history.items_processed}")
            logger.info(f"   新增: {history.items_added}")
            logger.info(f"   更新: {history.items_updated}")
        
        def on_sync_error(error: Exception):
            logger.error(f"❌ 同步错误: {error}")
        
        scheduler.on_sync_start = on_sync_start
        scheduler.on_sync_complete = on_sync_complete
        scheduler.on_sync_error = on_sync_error
        
        # 启动调度器
        scheduler.start()
        
        # 获取初始状态
        status = scheduler.get_status()
        logger.info(f"\n调度器状态:")
        logger.info(f"  运行中: {status.is_running}")
        logger.info(f"  同步中: {status.is_syncing}")
        
        # 手动触发同步
        logger.info("\n手动触发同步...")
        success = scheduler.trigger_sync()
        
        if success:
            # 等待同步完成
            timeout = 60  # 60秒超时
            start_time = time.time()
            
            while scheduler.get_status().is_syncing:
                if time.time() - start_time > timeout:
                    logger.warning("同步超时")
                    break
                time.sleep(2)
            
            # 获取统计信息
            stats = scheduler.get_statistics()
            logger.info(f"\n统计信息:")
            logger.info(f"  总同步次数: {stats['total_syncs']}")
            logger.info(f"  成功次数: {stats['successful_syncs']}")
            logger.info(f"  失败次数: {stats['failed_syncs']}")
            logger.info(f"  成功率: {stats['success_rate']}%")
        
        # 停止调度器
        scheduler.stop()
        logger.info("\n✅ 调度器测试完成\n")
        
    except Exception as e:
        logger.error(f"❌ 调度器测试失败: {e}\n")


def test_sync_history():
    """测试同步历史记录"""
    logger.info("=" * 60)
    logger.info("测试 3: 同步历史记录")
    logger.info("=" * 60)
    
    try:
        db_manager = DatabaseManager(db_path="./test_data/github_stars.db")
        
        # 获取同步历史
        history_list = db_manager.get_sync_history(limit=10)
        
        if history_list:
            logger.info(f"\n最近 {len(history_list)} 次同步记录:")
            for i, record in enumerate(history_list, 1):
                logger.info(f"\n{i}. 同步记录:")
                logger.info(f"   状态: {record.status}")
                logger.info(f"   开始时间: {record.started_at}")
                logger.info(f"   完成时间: {record.completed_at}")
                logger.info(f"   处理: {record.items_processed}")
                logger.info(f"   新增: {record.items_added}")
                logger.info(f"   更新: {record.items_updated}")
                
                if record.execution_time_ms:
                    logger.info(f"   耗时: {record.execution_time_ms}ms")
                
                if record.error_message:
                    logger.info(f"   错误: {record.error_message}")
        else:
            logger.info("暂无同步历史记录")
        
        logger.info("\n✅ 同步历史测试完成\n")
        
    except Exception as e:
        logger.error(f"❌ 同步历史测试失败: {e}\n")


def test_database_manager():
    """测试数据库管理器"""
    logger.info("=" * 60)
    logger.info("测试 4: 数据库管理器")
    logger.info("=" * 60)
    
    try:
        db_manager = DatabaseManager(db_path="./test_data/github_stars.db")
        
        # 测试获取仓库
        logger.info("测试数据库连接...")
        local_repos = db_manager._get_local_repos() if hasattr(db_manager, '_get_local_repos') else []
        
        logger.info(f"本地仓库数量: {len(local_repos) if isinstance(local_repos, list) else 0}")
        
        # 测试获取冲突
        conflicts = db_manager.get_unresolved_conflicts()
        logger.info(f"未解决冲突数: {len(conflicts)}")
        
        logger.info("\n✅ 数据库管理器测试完成\n")
        
    except Exception as e:
        logger.error(f"❌ 数据库管理器测试失败: {e}\n")


def test_progress_callback():
    """测试进度回调功能"""
    logger.info("=" * 60)
    logger.info("测试 5: 进度回调功能")
    logger.info("=" * 60)
    
    try:
        github_token = os.getenv("GITHUB_TOKEN", "your-github-token")
        
        if github_token == "your-github-token":
            logger.warning("请设置环境变量 GITHUB_TOKEN 或修改代码中的 token")
            logger.info("跳过测试...")
            return
        
        github_service = GitHubService(token=github_token)
        db_manager = DatabaseManager(db_path="./test_data/github_stars.db")
        sync_service = SyncService(github_service, db_manager)
        
        # 添加多个回调
        progress_history = []
        
        def callback1(progress: SyncProgress):
            progress_history.append({
                'time': datetime.now().isoformat(),
                'percentage': progress.get_progress_percentage(),
                'processed': progress.processed_repos,
                'total': progress.total_repos
            })
        
        def callback2(progress: SyncProgress):
            if progress.processed_repos % 10 == 0:
                logger.info(f"进度检查点: {progress.processed_repos}/{progress.total_repos}")
        
        sync_service.add_progress_callback(callback1)
        sync_service.add_progress_callback(callback2)
        
        # 执行同步
        logger.info("开始同步（带进度回调）...")
        history = sync_service.sync_repositories()
        
        # 显示进度历史
        logger.info(f"\n捕获了 {len(progress_history)} 个进度更新")
        if progress_history:
            logger.info("前5个进度点:")
            for i, record in enumerate(progress_history[:5], 1):
                logger.info(f"  {i}. {record['percentage']:.1f}% - "
                          f"{record['processed']}/{record['total']}")
        
        logger.info("\n✅ 进度回调测试完成\n")
        
    except Exception as e:
        logger.error(f"❌ 进度回调测试失败: {e}\n")


def run_all_tests():
    """运行所有测试"""
    logger.info("🚀 开始运行同步功能测试套件")
    logger.info(f"时间: {datetime.now().isoformat()}")
    logger.info("")
    
    # 创建测试数据目录
    os.makedirs("./test_data", exist_ok=True)
    
    # 运行测试
    test_database_manager()
    test_sync_history()
    test_basic_sync()
    test_progress_callback()
    test_scheduler()
    
    logger.info("=" * 60)
    logger.info("🎉 所有测试完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║     星标仓库自动同步功能 - 测试示例                       ║
╚═══════════════════════════════════════════════════════════╝

使用说明:
1. 设置环境变量 GITHUB_TOKEN 或修改代码中的 token
2. 运行测试: python sync_test_example.py

可选测试:
  - 运行所有测试: run_all_tests()
  - 基础同步: test_basic_sync()
  - 调度器: test_scheduler()
  - 同步历史: test_sync_history()
  - 数据库管理器: test_database_manager()
  - 进度回调: test_progress_callback()

环境变量设置:
  export GITHUB_TOKEN=your_github_token_here

""")
    
    # 检查 GitHub Token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.warning("⚠️  未设置 GITHUB_TOKEN 环境变量")
        logger.info("请先设置: export GITHUB_TOKEN=your_token_here")
        logger.info("或在代码中直接设置 token")
        logger.info("")
        logger.info("将运行部分不需要 token 的测试...")
        logger.info("")
    
    # 运行测试
    run_all_tests()
