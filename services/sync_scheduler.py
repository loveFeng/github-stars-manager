"""
星标仓库自动同步调度器
提供定时同步、任务调度、配置管理等功能
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import schedule

from sync_service import (
    SyncService, SyncConfig, SyncProgress, SyncHistoryRecord,
    SyncStatus, SyncMode, ConflictStrategy, DatabaseManager
)
from github_service import GitHubService, AIConfig


logger = logging.getLogger(__name__)


class ScheduleInterval(Enum):
    """调度间隔"""
    MANUAL = "manual"           # 手动触发
    MINUTES_30 = "30min"        # 30分钟
    HOURLY = "hourly"           # 每小时
    HOURS_6 = "6hours"          # 6小时
    HOURS_12 = "12hours"        # 12小时
    DAILY = "daily"             # 每天
    WEEKLY = "weekly"           # 每周


@dataclass
class SchedulerConfig:
    """调度器配置"""
    enabled: bool = True                        # 是否启用自动同步
    interval: ScheduleInterval = ScheduleInterval.HOURS_6  # 同步间隔
    sync_time: Optional[str] = None             # 指定同步时间 (HH:MM 格式)
    retry_on_failure: bool = True               # 失败时是否重试
    max_retry_attempts: int = 3                 # 最大重试次数
    retry_delay_minutes: int = 10               # 重试延迟（分钟）
    sync_on_startup: bool = False               # 启动时是否同步
    quiet_hours_start: Optional[str] = None     # 静默时段开始 (HH:MM)
    quiet_hours_end: Optional[str] = None       # 静默时段结束 (HH:MM)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'enabled': self.enabled,
            'interval': self.interval.value,
            'sync_time': self.sync_time,
            'retry_on_failure': self.retry_on_failure,
            'max_retry_attempts': self.max_retry_attempts,
            'retry_delay_minutes': self.retry_delay_minutes,
            'sync_on_startup': self.sync_on_startup,
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchedulerConfig':
        """从字典创建"""
        return cls(
            enabled=data.get('enabled', True),
            interval=ScheduleInterval(data.get('interval', 'hourly')),
            sync_time=data.get('sync_time'),
            retry_on_failure=data.get('retry_on_failure', True),
            max_retry_attempts=data.get('max_retry_attempts', 3),
            retry_delay_minutes=data.get('retry_delay_minutes', 10),
            sync_on_startup=data.get('sync_on_startup', False),
            quiet_hours_start=data.get('quiet_hours_start'),
            quiet_hours_end=data.get('quiet_hours_end')
        )


@dataclass
class SchedulerStatus:
    """调度器状态"""
    is_running: bool = False
    is_syncing: bool = False
    last_sync_time: Optional[str] = None
    next_sync_time: Optional[str] = None
    last_sync_status: Optional[str] = None
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class SyncScheduler:
    """同步调度器"""
    
    def __init__(self,
                 sync_service: SyncService,
                 db_manager: DatabaseManager,
                 scheduler_config: Optional[SchedulerConfig] = None):
        """
        初始化同步调度器
        
        Args:
            sync_service: 同步服务
            db_manager: 数据库管理器
            scheduler_config: 调度器配置
        """
        self.sync_service = sync_service
        self.db_manager = db_manager
        self.config = scheduler_config or SchedulerConfig()
        
        self.status = SchedulerStatus()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 任务回调
        self.on_sync_start: Optional[Callable[[], None]] = None
        self.on_sync_complete: Optional[Callable[[SyncHistoryRecord], None]] = None
        self.on_sync_error: Optional[Callable[[Exception], None]] = None
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """从数据库加载配置"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT config_value FROM sync_configs
                WHERE config_key = 'scheduler_config'
            """)
            
            row = cursor.fetchone()
            if row:
                config_data = json.loads(row['config_value'])
                self.config = SchedulerConfig.from_dict(config_data)
                logger.info("调度器配置加载成功")
            
            conn.close()
            
        except Exception as e:
            logger.warning(f"加载调度器配置失败: {e}, 使用默认配置")
    
    def _save_config(self):
        """保存配置到数据库"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            config_json = json.dumps(self.config.to_dict())
            
            cursor.execute("""
                INSERT OR REPLACE INTO sync_configs (config_key, config_value, updated_at)
                VALUES ('scheduler_config', ?, CURRENT_TIMESTAMP)
            """, (config_json,))
            
            conn.commit()
            conn.close()
            
            logger.info("调度器配置保存成功")
            
        except Exception as e:
            logger.error(f"保存调度器配置失败: {e}")
    
    def update_config(self, config: SchedulerConfig):
        """
        更新调度器配置
        
        Args:
            config: 新的配置
        """
        with self._lock:
            self.config = config
            self._save_config()
            
            # 如果调度器正在运行，重新启动以应用新配置
            if self.status.is_running:
                logger.info("配置已更新，重新启动调度器...")
                self.stop()
                self.start()
    
    def start(self):
        """启动调度器"""
        with self._lock:
            if self.status.is_running:
                logger.warning("调度器已在运行中")
                return
            
            if not self.config.enabled:
                logger.warning("调度器未启用")
                return
            
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(
                target=self._run_scheduler,
                name="SyncSchedulerThread",
                daemon=True
            )
            self._scheduler_thread.start()
            
            self.status.is_running = True
            logger.info("同步调度器已启动")
            
            # 启动时同步
            if self.config.sync_on_startup:
                threading.Thread(
                    target=self._execute_sync,
                    name="StartupSyncThread",
                    daemon=True
                ).start()
    
    def stop(self):
        """停止调度器"""
        with self._lock:
            if not self.status.is_running:
                logger.warning("调度器未运行")
                return
            
            self._stop_event.set()
            self.status.is_running = False
            
            # 等待线程结束
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                self._scheduler_thread.join(timeout=5)
            
            # 清理调度任务
            schedule.clear()
            
            logger.info("同步调度器已停止")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        try:
            # 设置调度任务
            self._setup_schedule()
            
            # 调度循环
            while not self._stop_event.is_set():
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"调度任务执行异常: {e}")
                    time.sleep(5)
            
        except Exception as e:
            logger.error(f"调度器异常退出: {e}")
            self.status.is_running = False
    
    def _setup_schedule(self):
        """设置调度任务"""
        schedule.clear()
        
        interval = self.config.interval
        sync_time = self.config.sync_time or "02:00"  # 默认凌晨2点
        
        if interval == ScheduleInterval.MANUAL:
            logger.info("调度模式: 手动触发")
            return
        
        elif interval == ScheduleInterval.MINUTES_30:
            schedule.every(30).minutes.do(self._scheduled_sync)
            logger.info("调度模式: 每30分钟")
        
        elif interval == ScheduleInterval.HOURLY:
            schedule.every().hour.do(self._scheduled_sync)
            logger.info("调度模式: 每小时")
        
        elif interval == ScheduleInterval.HOURS_6:
            schedule.every(6).hours.do(self._scheduled_sync)
            logger.info("调度模式: 每6小时")
        
        elif interval == ScheduleInterval.HOURS_12:
            schedule.every(12).hours.do(self._scheduled_sync)
            logger.info("调度模式: 每12小时")
        
        elif interval == ScheduleInterval.DAILY:
            schedule.every().day.at(sync_time).do(self._scheduled_sync)
            logger.info(f"调度模式: 每天 {sync_time}")
        
        elif interval == ScheduleInterval.WEEKLY:
            schedule.every().monday.at(sync_time).do(self._scheduled_sync)
            logger.info(f"调度模式: 每周一 {sync_time}")
        
        # 更新下次同步时间
        self._update_next_sync_time()
    
    def _scheduled_sync(self):
        """调度的同步任务"""
        # 检查是否在静默时段
        if self._is_quiet_hours():
            logger.info("当前处于静默时段，跳过同步")
            return
        
        # 执行同步
        threading.Thread(
            target=self._execute_sync,
            name="ScheduledSyncThread",
            daemon=True
        ).start()
    
    def _is_quiet_hours(self) -> bool:
        """检查是否在静默时段"""
        if not self.config.quiet_hours_start or not self.config.quiet_hours_end:
            return False
        
        try:
            now = datetime.now().time()
            start = datetime.strptime(self.config.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(self.config.quiet_hours_end, "%H:%M").time()
            
            if start <= end:
                return start <= now <= end
            else:
                # 跨越午夜的情况
                return now >= start or now <= end
                
        except Exception as e:
            logger.error(f"检查静默时段失败: {e}")
            return False
    
    def _execute_sync(self):
        """执行同步"""
        with self._lock:
            if self.status.is_syncing:
                logger.warning("已有同步任务正在运行")
                return
            
            self.status.is_syncing = True
        
        retry_count = 0
        max_retries = self.config.max_retry_attempts if self.config.retry_on_failure else 1
        
        while retry_count < max_retries:
            try:
                logger.info(f"开始执行同步任务 (尝试 {retry_count + 1}/{max_retries})...")
                
                # 触发开始回调
                if self.on_sync_start:
                    self.on_sync_start()
                
                # 执行同步
                history = self.sync_service.sync_repositories()
                
                # 更新状态
                self.status.last_sync_time = history.completed_at
                self.status.last_sync_status = history.status
                self.status.total_syncs += 1
                
                if history.status == "success":
                    self.status.successful_syncs += 1
                    self.status.retry_count = 0
                    logger.info("同步任务执行成功")
                    
                    # 触发完成回调
                    if self.on_sync_complete:
                        self.on_sync_complete(history)
                    
                    break  # 成功后退出重试循环
                    
                else:
                    self.status.failed_syncs += 1
                    raise RuntimeError(f"同步失败: {history.error_message}")
                
            except Exception as e:
                logger.error(f"同步任务执行失败: {e}")
                
                retry_count += 1
                self.status.retry_count = retry_count
                
                # 触发错误回调
                if self.on_sync_error:
                    self.on_sync_error(e)
                
                # 如果还有重试机会，等待后重试
                if retry_count < max_retries:
                    delay = self.config.retry_delay_minutes * 60
                    logger.info(f"将在 {self.config.retry_delay_minutes} 分钟后重试...")
                    time.sleep(delay)
                else:
                    self.status.failed_syncs += 1
                    logger.error(f"同步任务失败，已达到最大重试次数")
        
        # 更新下次同步时间
        self._update_next_sync_time()
        
        with self._lock:
            self.status.is_syncing = False
    
    def _update_next_sync_time(self):
        """更新下次同步时间"""
        try:
            next_job = schedule.next_run()
            if next_job:
                self.status.next_sync_time = next_job.isoformat()
            else:
                self.status.next_sync_time = None
        except Exception as e:
            logger.error(f"更新下次同步时间失败: {e}")
    
    def trigger_sync(self, force_full: bool = False) -> bool:
        """
        手动触发同步
        
        Args:
            force_full: 是否强制全量同步
            
        Returns:
            是否成功触发
        """
        if self.status.is_syncing:
            logger.warning("已有同步任务正在运行")
            return False
        
        def sync_task():
            with self._lock:
                if self.status.is_syncing:
                    return
                self.status.is_syncing = True
            
            try:
                logger.info("手动触发同步任务...")
                history = self.sync_service.sync_repositories(force_full=force_full)
                
                self.status.last_sync_time = history.completed_at
                self.status.last_sync_status = history.status
                self.status.total_syncs += 1
                
                if history.status == "success":
                    self.status.successful_syncs += 1
                    logger.info("手动同步成功")
                else:
                    self.status.failed_syncs += 1
                    logger.error(f"手动同步失败: {history.error_message}")
                
            except Exception as e:
                logger.error(f"手动同步异常: {e}")
                self.status.failed_syncs += 1
            
            finally:
                with self._lock:
                    self.status.is_syncing = False
        
        # 在新线程中执行同步
        threading.Thread(
            target=sync_task,
            name="ManualSyncThread",
            daemon=True
        ).start()
        
        return True
    
    def get_status(self) -> SchedulerStatus:
        """获取调度器状态"""
        return self.status
    
    def get_config(self) -> SchedulerConfig:
        """获取调度器配置"""
        return self.config
    
    def get_sync_progress(self) -> SyncProgress:
        """获取同步进度"""
        return self.sync_service.get_progress()
    
    def get_sync_history(self, limit: int = 50, offset: int = 0) -> List[SyncHistoryRecord]:
        """获取同步历史"""
        return self.sync_service.get_sync_history(limit, offset)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        history = self.get_sync_history(limit=100)
        
        if not history:
            return {
                'total_syncs': 0,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'success_rate': 0.0,
                'avg_execution_time_ms': 0,
                'total_repos_synced': 0,
                'total_repos_added': 0,
                'total_repos_updated': 0
            }
        
        total_syncs = len(history)
        successful_syncs = len([h for h in history if h.status == 'success'])
        failed_syncs = total_syncs - successful_syncs
        success_rate = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
        
        execution_times = [h.execution_time_ms for h in history if h.execution_time_ms]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        total_repos_synced = sum(h.items_processed for h in history)
        total_repos_added = sum(h.items_added for h in history)
        total_repos_updated = sum(h.items_updated for h in history)
        
        return {
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'success_rate': round(success_rate, 2),
            'avg_execution_time_ms': int(avg_execution_time),
            'total_repos_synced': total_repos_synced,
            'total_repos_added': total_repos_added,
            'total_repos_updated': total_repos_updated,
            'last_sync_time': self.status.last_sync_time,
            'next_sync_time': self.status.next_sync_time
        }


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    from github_service import GitHubService
    
    # 初始化服务
    github_service = GitHubService(token="your-github-token")
    db_manager = DatabaseManager()
    
    sync_config = SyncConfig(
        mode=SyncMode.SMART,
        conflict_strategy=ConflictStrategy.MERGE
    )
    sync_service = SyncService(github_service, db_manager, sync_config)
    
    # 初始化调度器
    scheduler_config = SchedulerConfig(
        enabled=True,
        interval=ScheduleInterval.HOURS_6,
        sync_on_startup=True,
        retry_on_failure=True,
        max_retry_attempts=3
    )
    scheduler = SyncScheduler(sync_service, db_manager, scheduler_config)
    
    # 设置回调
    def on_sync_start():
        print("同步开始...")
    
    def on_sync_complete(history: SyncHistoryRecord):
        print(f"同步完成: {history.status}")
        print(f"处理: {history.items_processed}, 新增: {history.items_added}, 更新: {history.items_updated}")
    
    def on_sync_error(error: Exception):
        print(f"同步错误: {error}")
    
    scheduler.on_sync_start = on_sync_start
    scheduler.on_sync_complete = on_sync_complete
    scheduler.on_sync_error = on_sync_error
    
    # 启动调度器
    scheduler.start()
    
    # 获取状态
    status = scheduler.get_status()
    print(f"调度器状态: {status.to_dict()}")
    
    # 获取统计信息
    stats = scheduler.get_statistics()
    print(f"统计信息: {stats}")
    
    try:
        # 保持运行
        while True:
            time.sleep(60)
            stats = scheduler.get_statistics()
            print(f"[{datetime.now()}] 统计: {stats}")
    except KeyboardInterrupt:
        print("\n正在停止调度器...")
        scheduler.stop()
        print("调度器已停止")
