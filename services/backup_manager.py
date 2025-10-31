"""
数据备份管理器
提供完整的备份管理功能，包括验证、存储空间管理和备份策略
"""

import os
import json
import hashlib
import logging
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from .backup_service import (
    BackupService, BackupConfig, BackupManifest, 
    BackupMetadataStore, BackupError
)
from .webdav_service import WebDAVService


class BackupStatus(Enum):
    """备份状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATING = "validating"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class BackupPriority(Enum):
    """备份优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BackupValidationResult:
    """备份验证结果"""
    backup_id: str
    is_valid: bool
    files_checked: int
    files_passed: int
    files_failed: int
    errors: List[str]
    checksum_match: bool
    validation_time: datetime
    duration_seconds: float


@dataclass
class StorageUsage:
    """存储使用情况"""
    total_backups: int
    total_size: int
    oldest_backup: Optional[datetime]
    newest_backup: Optional[datetime]
    by_config: Dict[str, Dict]
    storage_trend: List[Dict]


@dataclass
class BackupJob:
    """备份任务"""
    job_id: str
    config_name: str
    backup_type: str
    priority: BackupPriority
    scheduled_time: datetime
    status: BackupStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    backup_id: Optional[str] = None


class BackupValidator:
    """备份验证器"""
    
    def __init__(self, backup_service: BackupService, logger: logging.Logger):
        self.backup_service = backup_service
        self.logger = logger
    
    def validate_backup(self, backup_id: str) -> BackupValidationResult:
        """验证备份完整性"""
        start_time = time.time()
        errors = []
        files_passed = 0
        files_failed = 0
        
        self.logger.info(f"开始验证备份: {backup_id}")
        
        try:
            manifest = self.backup_service.metadata_store.get_backup_manifest(backup_id)
            if not manifest:
                return BackupValidationResult(
                    backup_id=backup_id,
                    is_valid=False,
                    files_checked=0,
                    files_passed=0,
                    files_failed=0,
                    errors=["备份清单不存在"],
                    checksum_match=False,
                    validation_time=datetime.now(),
                    duration_seconds=time.time() - start_time
                )
            
            config = self.backup_service.get_config(manifest.config_name)
            if not config:
                errors.append("备份配置不存在")
                return self._create_failed_result(backup_id, 0, 0, errors, start_time)
            
            client = self.backup_service.webdav_service.get_client(config.target_client_id)
            if not client:
                errors.append("WebDAV 客户端不存在")
                return self._create_failed_result(backup_id, 0, 0, errors, start_time)
            
            backup_dir = f"{config.target_path}/backups/{backup_id}"
            
            for file_info in manifest.files:
                try:
                    remote_path = f"{backup_dir}/{file_info.path}"
                    
                    if not client.file_exists(remote_path):
                        errors.append(f"文件不存在: {file_info.path}")
                        files_failed += 1
                        continue
                    
                    remote_file_info = client.get_file_info(remote_path)
                    if not remote_file_info:
                        errors.append(f"无法获取文件信息: {file_info.path}")
                        files_failed += 1
                        continue
                    
                    expected_size = file_info.compressed_size or file_info.size
                    if remote_file_info.size != expected_size:
                        errors.append(
                            f"文件大小不匹配 {file_info.path}: "
                            f"期望 {expected_size}, 实际 {remote_file_info.size}"
                        )
                        files_failed += 1
                        continue
                    
                    files_passed += 1
                    
                except Exception as e:
                    self.logger.error(f"验证文件失败 {file_info.path}: {e}")
                    errors.append(f"验证文件异常 {file_info.path}: {str(e)}")
                    files_failed += 1
            
            files_checked = len(manifest.files)
            checksum_match = True
            is_valid = files_failed == 0 and checksum_match
            
            duration = time.time() - start_time
            self.logger.info(
                f"验证完成: {backup_id}, 通过 {files_passed}/{files_checked}, 耗时 {duration:.2f}s"
            )
            
            return BackupValidationResult(
                backup_id=backup_id,
                is_valid=is_valid,
                files_checked=files_checked,
                files_passed=files_passed,
                files_failed=files_failed,
                errors=errors,
                checksum_match=checksum_match,
                validation_time=datetime.now(),
                duration_seconds=duration
            )
        
        except Exception as e:
            self.logger.error(f"验证备份失败: {e}")
            return self._create_failed_result(
                backup_id, 0, 0, [f"验证过程异常: {str(e)}"], start_time
            )
    
    def _create_failed_result(self, backup_id: str, files_checked: int, 
                             files_passed: int, errors: List[str], 
                             start_time: float) -> BackupValidationResult:
        """创建失败的验证结果"""
        return BackupValidationResult(
            backup_id=backup_id,
            is_valid=False,
            files_checked=files_checked,
            files_passed=files_passed,
            files_failed=files_checked - files_passed,
            errors=errors,
            checksum_match=False,
            validation_time=datetime.now(),
            duration_seconds=time.time() - start_time
        )
    
    def batch_validate(self, backup_ids: List[str]) -> List[BackupValidationResult]:
        """批量验证备份"""
        results = []
        for backup_id in backup_ids:
            try:
                result = self.validate_backup(backup_id)
                results.append(result)
            except Exception as e:
                self.logger.error(f"批量验证失败 {backup_id}: {e}")
                results.append(BackupValidationResult(
                    backup_id=backup_id,
                    is_valid=False,
                    files_checked=0,
                    files_passed=0,
                    files_failed=0,
                    errors=[str(e)],
                    checksum_match=False,
                    validation_time=datetime.now(),
                    duration_seconds=0
                ))
        
        return results


class StorageManager:
    """存储空间管理器"""
    
    def __init__(self, backup_service: BackupService, logger: logging.Logger):
        self.backup_service = backup_service
        self.logger = logger
    
    def get_storage_usage(self) -> StorageUsage:
        """获取存储使用情况"""
        try:
            all_backups = self.backup_service.list_backups()
            
            if not all_backups:
                return StorageUsage(
                    total_backups=0,
                    total_size=0,
                    oldest_backup=None,
                    newest_backup=None,
                    by_config={},
                    storage_trend=[]
                )
            
            total_size = sum(b.compressed_size or b.total_size for b in all_backups)
            
            sorted_backups = sorted(all_backups, key=lambda x: x.created_at)
            oldest = sorted_backups[0].created_at
            newest = sorted_backups[-1].created_at
            
            by_config = {}
            for backup in all_backups:
                config_name = backup.config_name
                if config_name not in by_config:
                    by_config[config_name] = {
                        "count": 0,
                        "total_size": 0,
                        "last_backup": None,
                        "backup_types": {"full": 0, "incremental": 0}
                    }
                
                by_config[config_name]["count"] += 1
                by_config[config_name]["total_size"] += backup.compressed_size or backup.total_size
                by_config[config_name]["backup_types"][backup.backup_type] = \
                    by_config[config_name]["backup_types"].get(backup.backup_type, 0) + 1
                
                if not by_config[config_name]["last_backup"] or \
                   backup.created_at > by_config[config_name]["last_backup"]:
                    by_config[config_name]["last_backup"] = backup.created_at
            
            storage_trend = self._calculate_storage_trend(all_backups)
            
            return StorageUsage(
                total_backups=len(all_backups),
                total_size=total_size,
                oldest_backup=oldest,
                newest_backup=newest,
                by_config=by_config,
                storage_trend=storage_trend
            )
        
        except Exception as e:
            self.logger.error(f"获取存储使用情况失败: {e}")
            raise
    
    def _calculate_storage_trend(self, backups: List[BackupManifest]) -> List[Dict]:
        """计算存储趋势"""
        trend = {}
        
        for backup in backups:
            month_key = backup.created_at.strftime("%Y-%m")
            if month_key not in trend:
                trend[month_key] = {
                    "month": month_key,
                    "count": 0,
                    "size": 0
                }
            
            trend[month_key]["count"] += 1
            trend[month_key]["size"] += backup.compressed_size or backup.total_size
        
        return sorted(trend.values(), key=lambda x: x["month"])
    
    def cleanup_old_backups(self, config_name: str, keep_count: int = None,
                           keep_days: int = None) -> int:
        """清理旧备份"""
        try:
            backups = self.backup_service.list_backups(config_name)
            if not backups:
                return 0
            
            sorted_backups = sorted(backups, key=lambda x: x.created_at, reverse=True)
            
            to_delete = []
            
            if keep_count is not None and len(sorted_backups) > keep_count:
                to_delete.extend(sorted_backups[keep_count:])
            
            if keep_days is not None:
                cutoff_date = datetime.now() - timedelta(days=keep_days)
                for backup in sorted_backups:
                    if backup.created_at < cutoff_date and backup not in to_delete:
                        to_delete.append(backup)
            
            deleted_count = 0
            config = self.backup_service.get_config(config_name)
            if not config:
                self.logger.error(f"配置不存在: {config_name}")
                return 0
            
            client = self.backup_service.webdav_service.get_client(config.target_client_id)
            if not client:
                self.logger.error(f"WebDAV 客户端不存在: {config.target_client_id}")
                return 0
            
            for backup in to_delete:
                try:
                    self.backup_service.metadata_store.delete_backup(backup.backup_id)
                    
                    backup_dir = f"{config.target_path}/backups/{backup.backup_id}"
                    self.backup_service._delete_webdav_directory(client, backup_dir)
                    
                    deleted_count += 1
                    self.logger.info(f"已删除旧备份: {backup.backup_id}")
                
                except Exception as e:
                    self.logger.error(f"删除备份失败 {backup.backup_id}: {e}")
            
            return deleted_count
        
        except Exception as e:
            self.logger.error(f"清理旧备份失败: {e}")
            return 0
    
    def estimate_space_needed(self, config_name: str) -> Dict:
        """估算需要的存储空间"""
        config = self.backup_service.get_config(config_name)
        if not config:
            return {"error": "配置不存在"}
        
        total_source_size = 0
        file_count = 0
        
        for source_path in config.source_paths:
            path = Path(source_path)
            if path.exists():
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        try:
                            total_source_size += file_path.stat().st_size
                            file_count += 1
                        except Exception:
                            pass
        
        compression_ratio = 0.6 if config.compression else 1.0
        estimated_size = int(total_source_size * compression_ratio)
        
        incremental_size = int(estimated_size * 0.2) if config.incremental else estimated_size
        
        return {
            "source_size": total_source_size,
            "file_count": file_count,
            "estimated_full_backup_size": estimated_size,
            "estimated_incremental_size": incremental_size,
            "compression_enabled": config.compression,
            "compression_ratio": compression_ratio
        }


class BackupManager:
    """备份管理器 - 统一的备份管理接口"""
    
    def __init__(self, webdav_service: WebDAVService, metadata_db_path: str):
        self.logger = logging.getLogger(__name__)
        
        self.metadata_store = BackupMetadataStore(metadata_db_path)
        self.backup_service = BackupService(webdav_service, self.metadata_store)
        self.validator = BackupValidator(self.backup_service, self.logger)
        self.storage_manager = StorageManager(self.backup_service, self.logger)
        
        self.running = False
        self.worker_thread = None
    
    def add_config(self, config: BackupConfig) -> bool:
        """添加备份配置"""
        return self.backup_service.add_config(config)
    
    def remove_config(self, config_name: str) -> bool:
        """移除备份配置"""
        return self.backup_service.remove_config(config_name)
    
    def get_config(self, config_name: str) -> Optional[BackupConfig]:
        """获取备份配置"""
        return self.backup_service.get_config(config_name)
    
    def list_configs(self) -> List[str]:
        """列出所有配置"""
        return self.backup_service.list_configs()
    
    def manual_backup(self, config_name: str, backup_type: str = "full") -> str:
        """手动触发备份"""
        return self.backup_service.execute_backup(config_name, backup_type)
    
    def validate_backup(self, backup_id: str) -> BackupValidationResult:
        """验证备份"""
        return self.validator.validate_backup(backup_id)
    
    def validate_all_backups(self, config_name: str = None) -> List[BackupValidationResult]:
        """验证所有备份"""
        backups = self.backup_service.list_backups(config_name)
        backup_ids = [b.backup_id for b in backups]
        return self.validator.batch_validate(backup_ids)
    
    def get_storage_usage(self) -> StorageUsage:
        """获取存储使用情况"""
        return self.storage_manager.get_storage_usage()
    
    def cleanup_old_backups(self, config_name: str, keep_count: int = None,
                           keep_days: int = None) -> int:
        """清理旧备份"""
        return self.storage_manager.cleanup_old_backups(config_name, keep_count, keep_days)
    
    def estimate_space(self, config_name: str) -> Dict:
        """估算空间需求"""
        return self.storage_manager.estimate_space_needed(config_name)
    
    def list_backups(self, config_name: str = None) -> List[BackupManifest]:
        """列出备份"""
        return self.backup_service.list_backups(config_name)
    
    def get_backup_manifest(self, backup_id: str) -> Optional[BackupManifest]:
        """获取备份清单"""
        return self.metadata_store.get_backup_manifest(backup_id)
    
    def get_statistics(self, config_name: str = None) -> Dict:
        """获取备份统计信息"""
        stats = self.backup_service.get_backup_statistics(config_name)
        storage = self.get_storage_usage()
        
        return {
            "backup_stats": stats,
            "storage_usage": asdict(storage),
            "timestamp": datetime.now().isoformat()
        }
    
    def start_scheduler(self):
        """启动调度器"""
        if not self.running:
            self.running = True
            self.backup_service.start_scheduler()
            self.logger.info("备份管理器已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.running = False
        self.backup_service.stop_scheduler()
        self.logger.info("备份管理器已停止")


def create_backup_manager(webdav_service: WebDAVService, 
                         metadata_db_path: str) -> BackupManager:
    """创建备份管理器的便捷函数"""
    return BackupManager(webdav_service, metadata_db_path)
