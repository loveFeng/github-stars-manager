"""
数据恢复服务
提供完整的数据恢复功能，包括一键恢复、选择性恢复和灾难恢复
"""

import os
import json
import logging
import threading
import time
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from .backup_service import (
    BackupService, BackupManifest, BackupFileInfo,
    BackupMetadataStore, RestoreSession
)
from .webdav_service import WebDAVService


class RecoveryStatus(Enum):
    """恢复状态枚举"""
    PENDING = "pending"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryMode(Enum):
    """恢复模式"""
    FULL = "full"  # 完全恢复
    SELECTIVE = "selective"  # 选择性恢复
    INCREMENTAL = "incremental"  # 增量恢复
    POINT_IN_TIME = "point_in_time"  # 时间点恢复


@dataclass
class RecoveryPoint:
    """恢复点"""
    backup_id: str
    created_at: datetime
    backup_type: str
    config_name: str
    total_size: int
    file_count: int
    is_verified: bool
    description: str = ""


@dataclass
class RecoveryPlan:
    """恢复计划"""
    plan_id: str
    recovery_points: List[str]  # 备份 ID 列表
    target_path: str
    recovery_mode: RecoveryMode
    selected_files: List[str]  # 选择性恢复的文件列表
    overwrite_existing: bool
    verify_after_recovery: bool
    created_at: datetime


@dataclass
class RecoveryProgress:
    """恢复进度"""
    session_id: str
    status: RecoveryStatus
    total_files: int
    processed_files: int
    total_size: int
    processed_size: int
    current_file: str
    elapsed_time: float
    estimated_time_remaining: float
    errors: List[str]


@dataclass
class DisasterRecoveryPlan:
    """灾难恢复计划"""
    plan_id: str
    name: str
    description: str
    recovery_order: List[str]  # 配置名称列表，按恢复顺序
    target_base_path: str
    auto_verify: bool
    notification_email: Optional[str]
    created_at: datetime
    last_tested: Optional[datetime]


class RecoveryPointManager:
    """恢复点管理器"""
    
    def __init__(self, backup_service: BackupService, logger: logging.Logger):
        self.backup_service = backup_service
        self.logger = logger
    
    def list_recovery_points(self, config_name: str = None, 
                            days: int = None) -> List[RecoveryPoint]:
        """
        列出可用的恢复点
        
        Args:
            config_name: 配置名称过滤
            days: 最近天数过滤
            
        Returns:
            恢复点列表
        """
        backups = self.backup_service.list_backups(config_name)
        
        if days is not None:
            cutoff_date = datetime.now() - timedelta(days=days)
            backups = [b for b in backups if b.created_at >= cutoff_date]
        
        recovery_points = []
        for backup in backups:
            rp = RecoveryPoint(
                backup_id=backup.backup_id,
                created_at=backup.created_at,
                backup_type=backup.backup_type,
                config_name=backup.config_name,
                total_size=backup.total_size,
                file_count=len(backup.files),
                is_verified=False,  # 可以从验证结果中获取
                description=f"{backup.backup_type} 备份"
            )
            recovery_points.append(rp)
        
        # 按创建时间降序排列
        return sorted(recovery_points, key=lambda x: x.created_at, reverse=True)
    
    def get_recovery_point(self, backup_id: str) -> Optional[RecoveryPoint]:
        """获取特定恢复点"""
        manifest = self.backup_service.metadata_store.get_backup_manifest(backup_id)
        if not manifest:
            return None
        
        return RecoveryPoint(
            backup_id=manifest.backup_id,
            created_at=manifest.created_at,
            backup_type=manifest.backup_type,
            config_name=manifest.config_name,
            total_size=manifest.total_size,
            file_count=len(manifest.files),
            is_verified=False,
            description=f"{manifest.backup_type} 备份"
        )
    
    def find_point_in_time(self, config_name: str, target_time: datetime) -> Optional[RecoveryPoint]:
        """
        查找最接近目标时间的恢复点
        
        Args:
            config_name: 配置名称
            target_time: 目标时间
            
        Returns:
            最接近的恢复点
        """
        points = self.list_recovery_points(config_name)
        
        # 找到目标时间之前最近的备份
        valid_points = [p for p in points if p.created_at <= target_time]
        
        if not valid_points:
            return None
        
        # 返回最接近的
        return min(valid_points, key=lambda p: abs((p.created_at - target_time).total_seconds()))


class RecoveryExecutor:
    """恢复执行器"""
    
    def __init__(self, backup_service: BackupService, logger: logging.Logger):
        self.backup_service = backup_service
        self.logger = logger
        self.active_sessions: Dict[str, RecoveryProgress] = {}
        self.session_lock = threading.Lock()
    
    def create_recovery_plan(self, backup_ids: List[str], target_path: str,
                           recovery_mode: RecoveryMode = RecoveryMode.FULL,
                           selected_files: List[str] = None,
                           overwrite: bool = False,
                           verify: bool = True) -> RecoveryPlan:
        """创建恢复计划"""
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return RecoveryPlan(
            plan_id=plan_id,
            recovery_points=backup_ids,
            target_path=target_path,
            recovery_mode=recovery_mode,
            selected_files=selected_files or [],
            overwrite_existing=overwrite,
            verify_after_recovery=verify,
            created_at=datetime.now()
        )
    
    def execute_recovery(self, plan: RecoveryPlan,
                        progress_callback: Callable[[RecoveryProgress], None] = None) -> str:
        """
        执行恢复操作
        
        Args:
            plan: 恢复计划
            progress_callback: 进度回调函数
            
        Returns:
            会话 ID
        """
        session_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 初始化进度
        progress = RecoveryProgress(
            session_id=session_id,
            status=RecoveryStatus.PREPARING,
            total_files=0,
            processed_files=0,
            total_size=0,
            processed_size=0,
            current_file="",
            elapsed_time=0,
            estimated_time_remaining=0,
            errors=[]
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = progress
        
        # 在新线程中执行恢复
        thread = threading.Thread(
            target=self._perform_recovery,
            args=(session_id, plan, progress_callback),
            daemon=True
        )
        thread.start()
        
        return session_id
    
    def _perform_recovery(self, session_id: str, plan: RecoveryPlan,
                         progress_callback: Callable[[RecoveryProgress], None] = None):
        """执行实际恢复操作"""
        progress = self.active_sessions[session_id]
        start_time = time.time()
        
        try:
            # 准备阶段
            progress.status = RecoveryStatus.PREPARING
            self._update_progress(progress, progress_callback)
            
            # 创建目标目录
            target_path = Path(plan.target_path)
            target_path.mkdir(parents=True, exist_ok=True)
            
            # 计算总量
            total_files = 0
            total_size = 0
            for backup_id in plan.recovery_points:
                manifest = self.backup_service.metadata_store.get_backup_manifest(backup_id)
                if manifest:
                    if plan.recovery_mode == RecoveryMode.SELECTIVE:
                        files = [f for f in manifest.files if f.path in plan.selected_files]
                    else:
                        files = manifest.files
                    
                    total_files += len(files)
                    total_size += sum(f.size for f in files)
            
            progress.total_files = total_files
            progress.total_size = total_size
            
            # 下载和恢复文件
            progress.status = RecoveryStatus.DOWNLOADING
            self._update_progress(progress, progress_callback)
            
            for backup_id in plan.recovery_points:
                manifest = self.backup_service.metadata_store.get_backup_manifest(backup_id)
                if not manifest:
                    progress.errors.append(f"备份清单不存在: {backup_id}")
                    continue
                
                config = self.backup_service.get_config(manifest.config_name)
                if not config:
                    progress.errors.append(f"配置不存在: {manifest.config_name}")
                    continue
                
                client = self.backup_service.webdav_service.get_client(config.target_client_id)
                if not client:
                    progress.errors.append(f"WebDAV 客户端不存在: {config.target_client_id}")
                    continue
                
                # 恢复文件
                files_to_restore = manifest.files
                if plan.recovery_mode == RecoveryMode.SELECTIVE:
                    files_to_restore = [f for f in files_to_restore if f.path in plan.selected_files]
                
                for file_info in files_to_restore:
                    try:
                        progress.current_file = file_info.path
                        self._update_progress(progress, progress_callback)
                        
                        remote_path = f"{config.target_path}/backups/{backup_id}/{file_info.path}"
                        local_path = target_path / file_info.path
                        
                        # 检查是否需要覆盖
                        if local_path.exists() and not plan.overwrite_existing:
                            progress.errors.append(f"文件已存在，跳过: {file_info.path}")
                            continue
                        
                        # 创建父目录
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 下载文件
                        client.download_file(remote_path, str(local_path))
                        
                        # 处理解密
                        if file_info.encrypted:
                            with open(local_path, 'rb') as f:
                                encrypted_data = f.read()
                            
                            decrypted_data = self.backup_service.encryption_manager.decrypt_data(
                                encrypted_data
                            )
                            
                            with open(local_path, 'wb') as f:
                                f.write(decrypted_data)
                        
                        # 恢复文件时间戳
                        timestamp = file_info.modified_time.timestamp()
                        os.utime(local_path, (timestamp, timestamp))
                        
                        progress.processed_files += 1
                        progress.processed_size += file_info.size
                        progress.elapsed_time = time.time() - start_time
                        
                        # 估算剩余时间
                        if progress.processed_size > 0:
                            rate = progress.processed_size / progress.elapsed_time
                            remaining_size = progress.total_size - progress.processed_size
                            progress.estimated_time_remaining = remaining_size / rate if rate > 0 else 0
                        
                        self._update_progress(progress, progress_callback)
                    
                    except Exception as e:
                        error_msg = f"恢复文件失败 {file_info.path}: {e}"
                        progress.errors.append(error_msg)
                        self.logger.error(error_msg)
            
            # 验证阶段
            if plan.verify_after_recovery:
                progress.status = RecoveryStatus.VALIDATING
                self._update_progress(progress, progress_callback)
                
                # 这里可以添加验证逻辑
                time.sleep(1)
            
            # 完成
            progress.status = RecoveryStatus.COMPLETED
            progress.elapsed_time = time.time() - start_time
            self._update_progress(progress, progress_callback)
            
            self.logger.info(f"恢复完成: {session_id}, 处理 {progress.processed_files}/{progress.total_files} 个文件")
        
        except Exception as e:
            progress.status = RecoveryStatus.FAILED
            progress.errors.append(f"恢复过程失败: {e}")
            progress.elapsed_time = time.time() - start_time
            self._update_progress(progress, progress_callback)
            self.logger.error(f"恢复失败: {e}")
    
    def _update_progress(self, progress: RecoveryProgress,
                        callback: Callable[[RecoveryProgress], None] = None):
        """更新进度"""
        if callback:
            try:
                callback(progress)
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    
    def get_progress(self, session_id: str) -> Optional[RecoveryProgress]:
        """获取恢复进度"""
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def cancel_recovery(self, session_id: str) -> bool:
        """取消恢复操作"""
        with self.session_lock:
            progress = self.active_sessions.get(session_id)
            if progress and progress.status in [RecoveryStatus.PREPARING, 
                                               RecoveryStatus.DOWNLOADING]:
                progress.status = RecoveryStatus.CANCELLED
                return True
            return False


class DisasterRecoveryManager:
    """灾难恢复管理器"""
    
    def __init__(self, backup_service: BackupService, 
                 recovery_executor: RecoveryExecutor, logger: logging.Logger):
        self.backup_service = backup_service
        self.recovery_executor = recovery_executor
        self.logger = logger
        self.plans: Dict[str, DisasterRecoveryPlan] = {}
    
    def create_dr_plan(self, name: str, recovery_order: List[str],
                      target_base_path: str, description: str = "",
                      auto_verify: bool = True,
                      notification_email: str = None) -> str:
        """
        创建灾难恢复计划
        
        Args:
            name: 计划名称
            recovery_order: 恢复顺序（配置名称列表）
            target_base_path: 目标基础路径
            description: 描述
            auto_verify: 自动验证
            notification_email: 通知邮箱
            
        Returns:
            计划 ID
        """
        plan_id = f"dr_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        plan = DisasterRecoveryPlan(
            plan_id=plan_id,
            name=name,
            description=description,
            recovery_order=recovery_order,
            target_base_path=target_base_path,
            auto_verify=auto_verify,
            notification_email=notification_email,
            created_at=datetime.now(),
            last_tested=None
        )
        
        self.plans[plan_id] = plan
        self.logger.info(f"创建灾难恢复计划: {plan_id} - {name}")
        
        return plan_id
    
    def execute_dr_plan(self, plan_id: str) -> Dict[str, str]:
        """
        执行灾难恢复计划
        
        Args:
            plan_id: 计划 ID
            
        Returns:
            恢复会话 ID 字典 {配置名称: 会话ID}
        """
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"灾难恢复计划不存在: {plan_id}")
        
        self.logger.info(f"开始执行灾难恢复计划: {plan_id} - {plan.name}")
        
        sessions = {}
        
        for config_name in plan.recovery_order:
            try:
                self.logger.info(f"恢复配置: {config_name}")
                
                # 获取最新的备份
                backups = self.backup_service.list_backups(config_name)
                if not backups:
                    self.logger.error(f"配置 {config_name} 没有可用备份")
                    continue
                
                latest_backup = max(backups, key=lambda x: x.created_at)
                
                # 创建恢复计划
                target_path = os.path.join(plan.target_base_path, config_name)
                recovery_plan = self.recovery_executor.create_recovery_plan(
                    backup_ids=[latest_backup.backup_id],
                    target_path=target_path,
                    recovery_mode=RecoveryMode.FULL,
                    verify=plan.auto_verify
                )
                
                # 执行恢复
                session_id = self.recovery_executor.execute_recovery(recovery_plan)
                sessions[config_name] = session_id
                
                self.logger.info(f"配置 {config_name} 恢复已启动，会话 ID: {session_id}")
                
                # 等待当前恢复完成（按顺序恢复）
                while True:
                    progress = self.recovery_executor.get_progress(session_id)
                    if progress and progress.status in [RecoveryStatus.COMPLETED, 
                                                        RecoveryStatus.FAILED]:
                        break
                    time.sleep(2)
            
            except Exception as e:
                self.logger.error(f"恢复配置 {config_name} 失败: {e}")
        
        # 更新最后测试时间
        plan.last_tested = datetime.now()
        
        self.logger.info(f"灾难恢复计划执行完成: {plan_id}")
        
        return sessions
    
    def test_dr_plan(self, plan_id: str) -> Dict:
        """
        测试灾难恢复计划
        
        Args:
            plan_id: 计划 ID
            
        Returns:
            测试结果
        """
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"灾难恢复计划不存在: {plan_id}")
        
        self.logger.info(f"测试灾难恢复计划: {plan_id}")
        
        results = {
            "plan_id": plan_id,
            "tested_at": datetime.now(),
            "config_tests": {}
        }
        
        for config_name in plan.recovery_order:
            backups = self.backup_service.list_backups(config_name)
            
            results["config_tests"][config_name] = {
                "has_backups": len(backups) > 0,
                "backup_count": len(backups),
                "latest_backup": backups[0].created_at if backups else None
            }
        
        plan.last_tested = datetime.now()
        
        return results
    
    def get_dr_plan(self, plan_id: str) -> Optional[DisasterRecoveryPlan]:
        """获取灾难恢复计划"""
        return self.plans.get(plan_id)
    
    def list_dr_plans(self) -> List[DisasterRecoveryPlan]:
        """列出所有灾难恢复计划"""
        return list(self.plans.values())


class RecoveryService:
    """恢复服务 - 统一的数据恢复接口"""
    
    def __init__(self, backup_service: BackupService):
        self.logger = logging.getLogger(__name__)
        self.backup_service = backup_service
        
        self.recovery_point_manager = RecoveryPointManager(backup_service, self.logger)
        self.recovery_executor = RecoveryExecutor(backup_service, self.logger)
        self.dr_manager = DisasterRecoveryManager(
            backup_service, self.recovery_executor, self.logger
        )
    
    # 恢复点管理
    def list_recovery_points(self, config_name: str = None, days: int = None) -> List[RecoveryPoint]:
        """列出可用的恢复点"""
        return self.recovery_point_manager.list_recovery_points(config_name, days)
    
    def get_recovery_point(self, backup_id: str) -> Optional[RecoveryPoint]:
        """获取特定恢复点"""
        return self.recovery_point_manager.get_recovery_point(backup_id)
    
    def find_point_in_time(self, config_name: str, target_time: datetime) -> Optional[RecoveryPoint]:
        """查找最接近目标时间的恢复点"""
        return self.recovery_point_manager.find_point_in_time(config_name, target_time)
    
    # 一键恢复
    def one_click_restore(self, config_name: str, target_path: str, 
                         point_in_time: datetime = None) -> str:
        """
        一键恢复到最新或指定时间点
        
        Args:
            config_name: 配置名称
            target_path: 目标路径
            point_in_time: 时间点（None 表示最新）
            
        Returns:
            恢复会话 ID
        """
        if point_in_time:
            recovery_point = self.find_point_in_time(config_name, point_in_time)
        else:
            points = self.list_recovery_points(config_name)
            recovery_point = points[0] if points else None
        
        if not recovery_point:
            raise ValueError("没有可用的恢复点")
        
        plan = self.recovery_executor.create_recovery_plan(
            backup_ids=[recovery_point.backup_id],
            target_path=target_path,
            recovery_mode=RecoveryMode.FULL,
            verify=True
        )
        
        return self.recovery_executor.execute_recovery(plan)
    
    # 选择性恢复
    def selective_restore(self, backup_id: str, target_path: str, 
                         file_patterns: List[str]) -> str:
        """
        选择性恢复指定文件
        
        Args:
            backup_id: 备份 ID
            target_path: 目标路径
            file_patterns: 文件模式列表
            
        Returns:
            恢复会话 ID
        """
        manifest = self.backup_service.metadata_store.get_backup_manifest(backup_id)
        if not manifest:
            raise ValueError(f"备份不存在: {backup_id}")
        
        # 匹配文件
        import fnmatch
        selected_files = []
        for file_info in manifest.files:
            for pattern in file_patterns:
                if fnmatch.fnmatch(file_info.path, pattern):
                    selected_files.append(file_info.path)
                    break
        
        if not selected_files:
            raise ValueError("没有匹配的文件")
        
        plan = self.recovery_executor.create_recovery_plan(
            backup_ids=[backup_id],
            target_path=target_path,
            recovery_mode=RecoveryMode.SELECTIVE,
            selected_files=selected_files,
            verify=True
        )
        
        return self.recovery_executor.execute_recovery(plan)
    
    # 恢复进度
    def get_recovery_progress(self, session_id: str) -> Optional[RecoveryProgress]:
        """获取恢复进度"""
        return self.recovery_executor.get_progress(session_id)
    
    def cancel_recovery(self, session_id: str) -> bool:
        """取消恢复"""
        return self.recovery_executor.cancel_recovery(session_id)
    
    # 灾难恢复
    def create_disaster_recovery_plan(self, name: str, recovery_order: List[str],
                                     target_base_path: str, **kwargs) -> str:
        """创建灾难恢复计划"""
        return self.dr_manager.create_dr_plan(
            name, recovery_order, target_base_path, **kwargs
        )
    
    def execute_disaster_recovery(self, plan_id: str) -> Dict[str, str]:
        """执行灾难恢复计划"""
        return self.dr_manager.execute_dr_plan(plan_id)
    
    def test_disaster_recovery_plan(self, plan_id: str) -> Dict:
        """测试灾难恢复计划"""
        return self.dr_manager.test_dr_plan(plan_id)
    
    def list_disaster_recovery_plans(self) -> List[DisasterRecoveryPlan]:
        """列出所有灾难恢复计划"""
        return self.dr_manager.list_dr_plans()


def create_recovery_service(backup_service: BackupService) -> RecoveryService:
    """创建恢复服务的便捷函数"""
    return RecoveryService(backup_service)
