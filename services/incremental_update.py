"""
增量更新服务
提供高效的增量更新机制，最小化数据传输和处理
包括变更检测、差异计算、时间戳管理、批量更新优化、数据一致性保证、更新日志记录和回滚机制
"""

import os
import json
import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import threading
import time


logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """变更类型"""
    METADATA_UPDATE = "metadata_update"  # 仓库元数据变更
    RELEASE_UPDATE = "release_update"    # Release 更新
    STAR_STATUS = "star_status"          # 星标状态变更
    NEW_REPO = "new_repo"                # 新增仓库
    REMOVED_REPO = "removed_repo"        # 移除仓库
    TAGS_UPDATE = "tags_update"          # 标签更新
    DESCRIPTION_UPDATE = "description_update"  # 描述更新


@dataclass
class Change:
    """变更记录"""
    change_id: str
    change_type: ChangeType
    repo_id: int
    repo_full_name: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    detected_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'change_id': self.change_id,
            'change_type': self.change_type.value,
            'repo_id': self.repo_id,
            'repo_full_name': self.repo_full_name,
            'old_value': json.dumps(self.old_value) if self.old_value else None,
            'new_value': json.dumps(self.new_value) if self.new_value else None,
            'detected_at': self.detected_at.isoformat(),
            'metadata': json.dumps(self.metadata)
        }


@dataclass
class SyncState:
    """同步状态"""
    repo_id: int
    repo_full_name: str
    last_sync: datetime
    last_modified: datetime
    sync_checksum: str
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateBatch:
    """更新批次"""
    batch_id: str
    changes: List[Change]
    created_at: datetime
    status: str  # pending, processing, completed, failed, rolled_back
    error_message: Optional[str] = None
    applied_at: Optional[datetime] = None


@dataclass
class RollbackPoint:
    """回滚点"""
    rollback_id: str
    batch_id: str
    created_at: datetime
    snapshot_data: Dict[str, Any]
    description: str


class UpdateLogger:
    """更新日志记录器"""
    
    def __init__(self, log_db_path: str):
        """
        初始化更新日志记录器
        
        Args:
            log_db_path: 日志数据库路径
        """
        self.log_db_path = Path(log_db_path)
        self.log_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.lock = threading.Lock()
    
    def _init_database(self):
        """初始化日志数据库"""
        with sqlite3.connect(self.log_db_path) as conn:
            # 变更日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS change_logs (
                    change_id TEXT PRIMARY KEY,
                    change_type TEXT NOT NULL,
                    repo_id INTEGER NOT NULL,
                    repo_full_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    detected_at TIMESTAMP NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 更新批次表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS update_batches (
                    batch_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    applied_at TIMESTAMP,
                    changes_count INTEGER DEFAULT 0
                )
            """)
            
            # 同步状态表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_states (
                    repo_id INTEGER PRIMARY KEY,
                    repo_full_name TEXT NOT NULL,
                    last_sync TIMESTAMP NOT NULL,
                    last_modified TIMESTAMP NOT NULL,
                    sync_checksum TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    metadata TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 回滚点表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rollback_points (
                    rollback_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (batch_id) REFERENCES update_batches (batch_id)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_change_logs_repo ON change_logs (repo_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_change_logs_type ON change_logs (change_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_change_logs_detected ON change_logs (detected_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_update_batches_status ON update_batches (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_states_modified ON sync_states (last_modified)")
    
    def log_change(self, change: Change) -> bool:
        """
        记录变更
        
        Args:
            change: 变更记录
            
        Returns:
            是否记录成功
        """
        try:
            with self.lock:
                with sqlite3.connect(self.log_db_path) as conn:
                    change_dict = change.to_dict()
                    conn.execute("""
                        INSERT OR REPLACE INTO change_logs 
                        (change_id, change_type, repo_id, repo_full_name, 
                         old_value, new_value, detected_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        change_dict['change_id'],
                        change_dict['change_type'],
                        change_dict['repo_id'],
                        change_dict['repo_full_name'],
                        change_dict['old_value'],
                        change_dict['new_value'],
                        change_dict['detected_at'],
                        change_dict['metadata']
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"记录变更失败: {e}")
            return False
    
    def log_batch(self, batch: UpdateBatch) -> bool:
        """
        记录更新批次
        
        Args:
            batch: 更新批次
            
        Returns:
            是否记录成功
        """
        try:
            with self.lock:
                with sqlite3.connect(self.log_db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO update_batches 
                        (batch_id, created_at, status, error_message, applied_at, changes_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        batch.batch_id,
                        batch.created_at.isoformat(),
                        batch.status,
                        batch.error_message,
                        batch.applied_at.isoformat() if batch.applied_at else None,
                        len(batch.changes)
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"记录更新批次失败: {e}")
            return False
    
    def save_sync_state(self, state: SyncState) -> bool:
        """
        保存同步状态
        
        Args:
            state: 同步状态
            
        Returns:
            是否保存成功
        """
        try:
            with self.lock:
                with sqlite3.connect(self.log_db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO sync_states 
                        (repo_id, repo_full_name, last_sync, last_modified, 
                         sync_checksum, version, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        state.repo_id,
                        state.repo_full_name,
                        state.last_sync.isoformat(),
                        state.last_modified.isoformat(),
                        state.sync_checksum,
                        state.version,
                        json.dumps(state.metadata)
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"保存同步状态失败: {e}")
            return False
    
    def get_sync_state(self, repo_id: int) -> Optional[SyncState]:
        """
        获取同步状态
        
        Args:
            repo_id: 仓库 ID
            
        Returns:
            同步状态或 None
        """
        try:
            with sqlite3.connect(self.log_db_path) as conn:
                cursor = conn.execute("""
                    SELECT repo_id, repo_full_name, last_sync, last_modified, 
                           sync_checksum, version, metadata
                    FROM sync_states WHERE repo_id = ?
                """, (repo_id,))
                
                row = cursor.fetchone()
                if row:
                    return SyncState(
                        repo_id=row[0],
                        repo_full_name=row[1],
                        last_sync=datetime.fromisoformat(row[2]),
                        last_modified=datetime.fromisoformat(row[3]),
                        sync_checksum=row[4],
                        version=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
            return None
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return None
    
    def get_changes_since(self, since: datetime, change_type: Optional[ChangeType] = None) -> List[Change]:
        """
        获取指定时间之后的变更
        
        Args:
            since: 起始时间
            change_type: 变更类型过滤
            
        Returns:
            变更列表
        """
        try:
            with sqlite3.connect(self.log_db_path) as conn:
                if change_type:
                    cursor = conn.execute("""
                        SELECT change_id, change_type, repo_id, repo_full_name,
                               old_value, new_value, detected_at, metadata
                        FROM change_logs 
                        WHERE detected_at > ? AND change_type = ?
                        ORDER BY detected_at DESC
                    """, (since.isoformat(), change_type.value))
                else:
                    cursor = conn.execute("""
                        SELECT change_id, change_type, repo_id, repo_full_name,
                               old_value, new_value, detected_at, metadata
                        FROM change_logs 
                        WHERE detected_at > ?
                        ORDER BY detected_at DESC
                    """, (since.isoformat(),))
                
                changes = []
                for row in cursor.fetchall():
                    changes.append(Change(
                        change_id=row[0],
                        change_type=ChangeType(row[1]),
                        repo_id=row[2],
                        repo_full_name=row[3],
                        old_value=json.loads(row[4]) if row[4] else None,
                        new_value=json.loads(row[5]) if row[5] else None,
                        detected_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    ))
                
                return changes
        except Exception as e:
            logger.error(f"获取变更记录失败: {e}")
            return []
    
    def save_rollback_point(self, rollback_point: RollbackPoint) -> bool:
        """
        保存回滚点
        
        Args:
            rollback_point: 回滚点
            
        Returns:
            是否保存成功
        """
        try:
            with self.lock:
                with sqlite3.connect(self.log_db_path) as conn:
                    conn.execute("""
                        INSERT INTO rollback_points 
                        (rollback_id, batch_id, created_at, snapshot_data, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        rollback_point.rollback_id,
                        rollback_point.batch_id,
                        rollback_point.created_at.isoformat(),
                        json.dumps(rollback_point.snapshot_data),
                        rollback_point.description
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"保存回滚点失败: {e}")
            return False
    
    def get_rollback_point(self, batch_id: str) -> Optional[RollbackPoint]:
        """
        获取回滚点
        
        Args:
            batch_id: 批次 ID
            
        Returns:
            回滚点或 None
        """
        try:
            with sqlite3.connect(self.log_db_path) as conn:
                cursor = conn.execute("""
                    SELECT rollback_id, batch_id, created_at, snapshot_data, description
                    FROM rollback_points WHERE batch_id = ?
                """, (batch_id,))
                
                row = cursor.fetchone()
                if row:
                    return RollbackPoint(
                        rollback_id=row[0],
                        batch_id=row[1],
                        created_at=datetime.fromisoformat(row[2]),
                        snapshot_data=json.loads(row[3]),
                        description=row[4]
                    )
            return None
        except Exception as e:
            logger.error(f"获取回滚点失败: {e}")
            return None


class ChangeDetector:
    """变更检测器"""
    
    def __init__(self, logger: UpdateLogger):
        """
        初始化变更检测器
        
        Args:
            logger: 更新日志记录器
        """
        self.logger = logger
    
    def detect_repo_changes(self, old_repo: Dict[str, Any], new_repo: Dict[str, Any]) -> List[Change]:
        """
        检测仓库变更
        
        Args:
            old_repo: 旧仓库数据
            new_repo: 新仓库数据
            
        Returns:
            变更列表
        """
        changes = []
        repo_id = new_repo.get('id')
        repo_full_name = new_repo.get('full_name')
        now = datetime.now()
        
        # 检测元数据变更
        metadata_fields = ['description', 'language', 'stargazers_count', 'topics', 
                          'updated_at', 'archived', 'fork']
        
        for field in metadata_fields:
            old_value = old_repo.get(field)
            new_value = new_repo.get(field)
            
            if old_value != new_value:
                change_id = f"{repo_id}_{field}_{int(now.timestamp())}"
                change = Change(
                    change_id=change_id,
                    change_type=ChangeType.METADATA_UPDATE,
                    repo_id=repo_id,
                    repo_full_name=repo_full_name,
                    old_value=old_value,
                    new_value=new_value,
                    detected_at=now,
                    metadata={'field': field}
                )
                changes.append(change)
                self.logger.log_change(change)
        
        return changes
    
    def detect_release_changes(self, repo_id: int, repo_full_name: str,
                              old_releases: List[Dict], new_releases: List[Dict]) -> List[Change]:
        """
        检测 Release 变更
        
        Args:
            repo_id: 仓库 ID
            repo_full_name: 仓库全名
            old_releases: 旧 Release 列表
            new_releases: 新 Release 列表
            
        Returns:
            变更列表
        """
        changes = []
        now = datetime.now()
        
        # 构建 Release 映射
        old_release_map = {r['id']: r for r in old_releases}
        new_release_map = {r['id']: r for r in new_releases}
        
        # 检测新增的 Release
        for release_id, release in new_release_map.items():
            if release_id not in old_release_map:
                change_id = f"{repo_id}_release_new_{release_id}_{int(now.timestamp())}"
                change = Change(
                    change_id=change_id,
                    change_type=ChangeType.RELEASE_UPDATE,
                    repo_id=repo_id,
                    repo_full_name=repo_full_name,
                    old_value=None,
                    new_value=release,
                    detected_at=now,
                    metadata={'action': 'new', 'release_id': release_id}
                )
                changes.append(change)
                self.logger.log_change(change)
        
        # 检测更新的 Release
        for release_id, old_release in old_release_map.items():
            if release_id in new_release_map:
                new_release = new_release_map[release_id]
                if old_release.get('published_at') != new_release.get('published_at') or \
                   old_release.get('tag_name') != new_release.get('tag_name'):
                    change_id = f"{repo_id}_release_update_{release_id}_{int(now.timestamp())}"
                    change = Change(
                        change_id=change_id,
                        change_type=ChangeType.RELEASE_UPDATE,
                        repo_id=repo_id,
                        repo_full_name=repo_full_name,
                        old_value=old_release,
                        new_value=new_release,
                        detected_at=now,
                        metadata={'action': 'update', 'release_id': release_id}
                    )
                    changes.append(change)
                    self.logger.log_change(change)
        
        return changes
    
    def detect_star_status_change(self, repo_id: int, repo_full_name: str,
                                  was_starred: bool, is_starred: bool) -> Optional[Change]:
        """
        检测星标状态变更
        
        Args:
            repo_id: 仓库 ID
            repo_full_name: 仓库全名
            was_starred: 之前是否星标
            is_starred: 现在是否星标
            
        Returns:
            变更记录或 None
        """
        if was_starred != is_starred:
            now = datetime.now()
            change_id = f"{repo_id}_star_{int(now.timestamp())}"
            change = Change(
                change_id=change_id,
                change_type=ChangeType.STAR_STATUS,
                repo_id=repo_id,
                repo_full_name=repo_full_name,
                old_value=was_starred,
                new_value=is_starred,
                detected_at=now,
                metadata={'action': 'starred' if is_starred else 'unstarred'}
            )
            self.logger.log_change(change)
            return change
        
        return None


class DiffCalculator:
    """差异计算器"""
    
    @staticmethod
    def calculate_checksum(data: Dict[str, Any]) -> str:
        """
        计算数据校验和
        
        Args:
            data: 数据字典
            
        Returns:
            校验和
        """
        # 排序键以确保一致性
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    @staticmethod
    def calculate_diff(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算数据差异
        
        Args:
            old_data: 旧数据
            new_data: 新数据
            
        Returns:
            差异字典
        """
        diff = {
            'added': {},
            'removed': {},
            'modified': {}
        }
        
        # 检测新增和修改
        for key, new_value in new_data.items():
            if key not in old_data:
                diff['added'][key] = new_value
            elif old_data[key] != new_value:
                diff['modified'][key] = {
                    'old': old_data[key],
                    'new': new_value
                }
        
        # 检测删除
        for key in old_data:
            if key not in new_data:
                diff['removed'][key] = old_data[key]
        
        return diff
    
    @staticmethod
    def is_significant_change(diff: Dict[str, Any], threshold: float = 0.1) -> bool:
        """
        判断变更是否显著
        
        Args:
            diff: 差异字典
            threshold: 变更阈值（0-1之间）
            
        Returns:
            是否显著变更
        """
        total_changes = len(diff['added']) + len(diff['removed']) + len(diff['modified'])
        
        # 如果没有旧数据，则认为是新增
        if not diff.get('removed') and not diff.get('modified'):
            return True
        
        # 计算变更比例
        total_fields = total_changes + len(diff.get('removed', {})) + len(diff.get('modified', {}))
        if total_fields == 0:
            return False
        
        change_ratio = total_changes / total_fields
        return change_ratio >= threshold


class DiffApplicator:
    """差异应用器"""
    
    @staticmethod
    def apply_diff(base_data: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用差异到基础数据
        
        Args:
            base_data: 基础数据
            diff: 差异字典
            
        Returns:
            应用差异后的数据
        """
        result = base_data.copy()
        
        # 应用新增
        for key, value in diff.get('added', {}).items():
            result[key] = value
        
        # 应用修改
        for key, change in diff.get('modified', {}).items():
            result[key] = change['new']
        
        # 应用删除
        for key in diff.get('removed', {}).keys():
            result.pop(key, None)
        
        return result
    
    @staticmethod
    def merge_changes(changes: List[Change]) -> Dict[int, Dict[str, Any]]:
        """
        合并多个变更
        
        Args:
            changes: 变更列表
            
        Returns:
            合并后的变更映射 {repo_id: merged_data}
        """
        merged = {}
        
        for change in sorted(changes, key=lambda c: c.detected_at):
            repo_id = change.repo_id
            
            if repo_id not in merged:
                merged[repo_id] = {}
            
            # 根据变更类型合并
            if change.change_type == ChangeType.METADATA_UPDATE:
                field = change.metadata.get('field')
                if field:
                    merged[repo_id][field] = change.new_value
            elif change.change_type == ChangeType.RELEASE_UPDATE:
                if 'releases' not in merged[repo_id]:
                    merged[repo_id]['releases'] = []
                merged[repo_id]['releases'].append(change.new_value)
            elif change.change_type == ChangeType.STAR_STATUS:
                merged[repo_id]['is_starred'] = change.new_value
        
        return merged


class BatchUpdateOptimizer:
    """批量更新优化器"""
    
    def __init__(self, batch_size: int = 50, max_concurrent: int = 5):
        """
        初始化批量更新优化器
        
        Args:
            batch_size: 批次大小
            max_concurrent: 最大并发数
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
    
    def create_batches(self, changes: List[Change]) -> List[UpdateBatch]:
        """
        创建更新批次
        
        Args:
            changes: 变更列表
            
        Returns:
            更新批次列表
        """
        batches = []
        
        for i in range(0, len(changes), self.batch_size):
            batch_changes = changes[i:i + self.batch_size]
            batch_id = f"batch_{int(datetime.now().timestamp())}_{i // self.batch_size}"
            
            batch = UpdateBatch(
                batch_id=batch_id,
                changes=batch_changes,
                created_at=datetime.now(),
                status='pending'
            )
            batches.append(batch)
        
        return batches
    
    def optimize_update_order(self, changes: List[Change]) -> List[Change]:
        """
        优化更新顺序
        
        Args:
            changes: 变更列表
            
        Returns:
            优化后的变更列表
        """
        # 按优先级排序：新增仓库 > 元数据更新 > Release 更新 > 星标状态
        priority_map = {
            ChangeType.NEW_REPO: 0,
            ChangeType.METADATA_UPDATE: 1,
            ChangeType.RELEASE_UPDATE: 2,
            ChangeType.STAR_STATUS: 3,
            ChangeType.REMOVED_REPO: 4
        }
        
        return sorted(changes, key=lambda c: (priority_map.get(c.change_type, 999), c.detected_at))
    
    def deduplicate_changes(self, changes: List[Change]) -> List[Change]:
        """
        去重变更（保留最新的）
        
        Args:
            changes: 变更列表
            
        Returns:
            去重后的变更列表
        """
        # 按 repo_id 和 change_type 分组
        change_map = {}
        
        for change in changes:
            key = f"{change.repo_id}_{change.change_type.value}"
            
            if key not in change_map or change.detected_at > change_map[key].detected_at:
                change_map[key] = change
        
        return list(change_map.values())


class ConsistencyGuard:
    """数据一致性保证"""
    
    def __init__(self, logger: UpdateLogger):
        """
        初始化一致性保证
        
        Args:
            logger: 更新日志记录器
        """
        self.logger = logger
        self.lock = threading.Lock()
    
    def verify_consistency(self, repo_id: int, expected_checksum: str, 
                          actual_data: Dict[str, Any]) -> bool:
        """
        验证数据一致性
        
        Args:
            repo_id: 仓库 ID
            expected_checksum: 期望的校验和
            actual_data: 实际数据
            
        Returns:
            是否一致
        """
        actual_checksum = DiffCalculator.calculate_checksum(actual_data)
        return actual_checksum == expected_checksum
    
    def create_snapshot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建数据快照
        
        Args:
            data: 数据
            
        Returns:
            快照数据
        """
        return {
            'data': data.copy(),
            'checksum': DiffCalculator.calculate_checksum(data),
            'timestamp': datetime.now().isoformat()
        }
    
    def compare_snapshots(self, snapshot1: Dict[str, Any], 
                         snapshot2: Dict[str, Any]) -> Dict[str, Any]:
        """
        比较两个快照
        
        Args:
            snapshot1: 快照1
            snapshot2: 快照2
            
        Returns:
            差异信息
        """
        return DiffCalculator.calculate_diff(snapshot1['data'], snapshot2['data'])


class RollbackManager:
    """回滚管理器"""
    
    def __init__(self, logger: UpdateLogger):
        """
        初始化回滚管理器
        
        Args:
            logger: 更新日志记录器
        """
        self.logger = logger
    
    def create_rollback_point(self, batch: UpdateBatch, 
                            snapshot_data: Dict[str, Any]) -> RollbackPoint:
        """
        创建回滚点
        
        Args:
            batch: 更新批次
            snapshot_data: 快照数据
            
        Returns:
            回滚点
        """
        rollback_id = f"rollback_{batch.batch_id}_{int(datetime.now().timestamp())}"
        
        rollback_point = RollbackPoint(
            rollback_id=rollback_id,
            batch_id=batch.batch_id,
            created_at=datetime.now(),
            snapshot_data=snapshot_data,
            description=f"回滚点：{batch.batch_id}，变更数：{len(batch.changes)}"
        )
        
        self.logger.save_rollback_point(rollback_point)
        return rollback_point
    
    def rollback(self, batch_id: str) -> bool:
        """
        执行回滚
        
        Args:
            batch_id: 批次 ID
            
        Returns:
            是否回滚成功
        """
        try:
            rollback_point = self.logger.get_rollback_point(batch_id)
            if not rollback_point:
                logger.error(f"回滚点不存在: {batch_id}")
                return False
            
            # 恢复快照数据
            snapshot_data = rollback_point.snapshot_data
            
            # 这里需要根据实际业务逻辑实现数据恢复
            # 示例：更新数据库记录
            logger.info(f"执行回滚: {batch_id}，恢复到 {rollback_point.created_at}")
            
            return True
            
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False


class IncrementalUpdateService:
    """增量更新服务"""
    
    def __init__(self, log_db_path: str = "./data/update_logs.db",
                 batch_size: int = 50, max_concurrent: int = 5):
        """
        初始化增量更新服务
        
        Args:
            log_db_path: 日志数据库路径
            batch_size: 批次大小
            max_concurrent: 最大并发数
        """
        self.update_logger = UpdateLogger(log_db_path)
        self.change_detector = ChangeDetector(self.update_logger)
        self.batch_optimizer = BatchUpdateOptimizer(batch_size, max_concurrent)
        self.consistency_guard = ConsistencyGuard(self.update_logger)
        self.rollback_manager = RollbackManager(self.update_logger)
        
        self.lock = threading.Lock()
    
    def detect_and_record_changes(self, old_repos: List[Dict[str, Any]], 
                                  new_repos: List[Dict[str, Any]]) -> List[Change]:
        """
        检测并记录变更
        
        Args:
            old_repos: 旧仓库列表
            new_repos: 新仓库列表
            
        Returns:
            变更列表
        """
        changes = []
        
        # 构建仓库映射
        old_repo_map = {r['id']: r for r in old_repos}
        new_repo_map = {r['id']: r for r in new_repos}
        
        # 检测新增和更新的仓库
        for repo_id, new_repo in new_repo_map.items():
            if repo_id in old_repo_map:
                # 检测变更
                repo_changes = self.change_detector.detect_repo_changes(
                    old_repo_map[repo_id], new_repo
                )
                changes.extend(repo_changes)
            else:
                # 新增仓库
                now = datetime.now()
                change_id = f"{repo_id}_new_{int(now.timestamp())}"
                change = Change(
                    change_id=change_id,
                    change_type=ChangeType.NEW_REPO,
                    repo_id=repo_id,
                    repo_full_name=new_repo['full_name'],
                    old_value=None,
                    new_value=new_repo,
                    detected_at=now
                )
                changes.append(change)
                self.update_logger.log_change(change)
        
        # 检测移除的仓库
        for repo_id, old_repo in old_repo_map.items():
            if repo_id not in new_repo_map:
                now = datetime.now()
                change_id = f"{repo_id}_removed_{int(now.timestamp())}"
                change = Change(
                    change_id=change_id,
                    change_type=ChangeType.REMOVED_REPO,
                    repo_id=repo_id,
                    repo_full_name=old_repo['full_name'],
                    old_value=old_repo,
                    new_value=None,
                    detected_at=now
                )
                changes.append(change)
                self.update_logger.log_change(change)
        
        return changes
    
    def process_incremental_update(self, changes: List[Change], 
                                   update_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        处理增量更新
        
        Args:
            changes: 变更列表
            update_callback: 更新回调函数
            
        Returns:
            更新结果
        """
        try:
            # 去重和优化
            changes = self.batch_optimizer.deduplicate_changes(changes)
            changes = self.batch_optimizer.optimize_update_order(changes)
            
            # 创建批次
            batches = self.batch_optimizer.create_batches(changes)
            
            results = {
                'total_changes': len(changes),
                'total_batches': len(batches),
                'successful_batches': 0,
                'failed_batches': 0,
                'errors': []
            }
            
            # 处理每个批次
            for batch in batches:
                try:
                    # 创建回滚点
                    snapshot_data = self._create_batch_snapshot(batch)
                    rollback_point = self.rollback_manager.create_rollback_point(
                        batch, snapshot_data
                    )
                    
                    # 更新批次状态
                    batch.status = 'processing'
                    self.update_logger.log_batch(batch)
                    
                    # 应用变更
                    if update_callback:
                        update_callback(batch.changes)
                    
                    # 标记完成
                    batch.status = 'completed'
                    batch.applied_at = datetime.now()
                    self.update_logger.log_batch(batch)
                    
                    results['successful_batches'] += 1
                    
                    # 更新同步状态
                    self._update_sync_states(batch.changes)
                    
                except Exception as e:
                    batch.status = 'failed'
                    batch.error_message = str(e)
                    self.update_logger.log_batch(batch)
                    
                    results['failed_batches'] += 1
                    results['errors'].append({
                        'batch_id': batch.batch_id,
                        'error': str(e)
                    })
                    
                    logger.error(f"批次处理失败 {batch.batch_id}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"增量更新处理失败: {e}")
            return {
                'error': str(e),
                'total_changes': len(changes),
                'successful_batches': 0,
                'failed_batches': 0
            }
    
    def _create_batch_snapshot(self, batch: UpdateBatch) -> Dict[str, Any]:
        """
        创建批次快照
        
        Args:
            batch: 更新批次
            
        Returns:
            快照数据
        """
        snapshot = {}
        
        for change in batch.changes:
            repo_id = change.repo_id
            if repo_id not in snapshot:
                snapshot[repo_id] = {
                    'repo_id': repo_id,
                    'repo_full_name': change.repo_full_name,
                    'changes': []
                }
            
            snapshot[repo_id]['changes'].append({
                'change_id': change.change_id,
                'change_type': change.change_type.value,
                'old_value': change.old_value,
                'new_value': change.new_value
            })
        
        return snapshot
    
    def _update_sync_states(self, changes: List[Change]):
        """
        更新同步状态
        
        Args:
            changes: 变更列表
        """
        for change in changes:
            # 获取或创建同步状态
            sync_state = self.update_logger.get_sync_state(change.repo_id)
            
            if sync_state:
                sync_state.last_sync = datetime.now()
                sync_state.last_modified = change.detected_at
                sync_state.version += 1
            else:
                sync_state = SyncState(
                    repo_id=change.repo_id,
                    repo_full_name=change.repo_full_name,
                    last_sync=datetime.now(),
                    last_modified=change.detected_at,
                    sync_checksum='',
                    version=1
                )
            
            # 计算新的校验和
            if change.new_value:
                sync_state.sync_checksum = DiffCalculator.calculate_checksum(
                    change.new_value if isinstance(change.new_value, dict) else {'value': change.new_value}
                )
            
            self.update_logger.save_sync_state(sync_state)
    
    def get_update_statistics(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取更新统计信息
        
        Args:
            since: 起始时间（可选）
            
        Returns:
            统计信息
        """
        if since is None:
            since = datetime.now() - timedelta(days=7)
        
        changes = self.update_logger.get_changes_since(since)
        
        # 按类型统计
        type_counts = {}
        for change in changes:
            change_type = change.change_type.value
            type_counts[change_type] = type_counts.get(change_type, 0) + 1
        
        # 按仓库统计
        repo_counts = {}
        for change in changes:
            repo_id = change.repo_id
            repo_counts[repo_id] = repo_counts.get(repo_id, 0) + 1
        
        return {
            'total_changes': len(changes),
            'by_type': type_counts,
            'affected_repos': len(repo_counts),
            'most_active_repo': max(repo_counts.items(), key=lambda x: x[1])[0] if repo_counts else None,
            'time_range': {
                'start': since.isoformat(),
                'end': datetime.now().isoformat()
            }
        }
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        清理旧日志
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.update_logger.log_db_path) as conn:
                # 清理变更日志
                cursor = conn.execute("""
                    DELETE FROM change_logs WHERE detected_at < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"清理了 {deleted_count} 条旧日志记录")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            return 0


# 使用示例
if __name__ == "__main__":
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # 初始化增量更新服务
    service = IncrementalUpdateService(
        log_db_path="./data/update_logs.db",
        batch_size=50,
        max_concurrent=5
    )
    
    # 模拟仓库数据
    old_repos = [
        {
            'id': 1,
            'full_name': 'user/repo1',
            'description': 'Old description',
            'stargazers_count': 100,
            'language': 'Python'
        }
    ]
    
    new_repos = [
        {
            'id': 1,
            'full_name': 'user/repo1',
            'description': 'New description',  # 描述变更
            'stargazers_count': 150,  # 星标数变更
            'language': 'Python'
        },
        {
            'id': 2,
            'full_name': 'user/repo2',
            'description': 'A new repository',
            'stargazers_count': 50,
            'language': 'JavaScript'
        }
    ]
    
    # 检测变更
    changes = service.detect_and_record_changes(old_repos, new_repos)
    print(f"检测到 {len(changes)} 个变更")
    
    # 处理增量更新
    def update_callback(changes):
        print(f"应用 {len(changes)} 个变更")
        for change in changes:
            print(f"  - {change.change_type.value}: {change.repo_full_name}")
    
    results = service.process_incremental_update(changes, update_callback)
    print(f"更新结果: {results}")
    
    # 获取统计信息
    stats = service.get_update_statistics()
    print(f"统计信息: {stats}")
