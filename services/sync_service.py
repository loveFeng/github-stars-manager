"""
星标仓库自动同步服务
提供完整的仓库同步、冲突解决、状态跟踪等功能
"""

import json
import sqlite3
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
import time

from github_service import GitHubService, StarredRepo, SyncResult, AIConfig
from github_api import GitHubAPIClient, GitHubRepository


logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """同步状态枚举"""
    IDLE = "idle"                      # 空闲
    RUNNING = "running"                 # 运行中
    SUCCESS = "success"                 # 成功
    FAILED = "failed"                   # 失败
    CANCELLED = "cancelled"             # 已取消
    PAUSED = "paused"                   # 已暂停


class ConflictStrategy(Enum):
    """冲突解决策略"""
    KEEP_LOCAL = "keep_local"           # 保留本地修改
    KEEP_REMOTE = "keep_remote"         # 使用远程更新
    MERGE = "merge"                     # 合并（优先远程数据，保留本地自定义字段）
    ASK_USER = "ask_user"               # 询问用户


class SyncMode(Enum):
    """同步模式"""
    FULL = "full"                       # 全量同步
    INCREMENTAL = "incremental"         # 增量同步
    SMART = "smart"                     # 智能同步（自动选择）


@dataclass
class SyncConfig:
    """同步配置"""
    mode: SyncMode = SyncMode.SMART
    conflict_strategy: ConflictStrategy = ConflictStrategy.MERGE
    batch_size: int = 50                   # 批处理大小
    max_retries: int = 3                    # 最大重试次数
    retry_delay: int = 5                    # 重试延迟（秒）
    timeout: int = 300                      # 超时时间（秒）
    enable_ai_analysis: bool = False        # 是否启用 AI 分析
    sync_releases: bool = True              # 是否同步 Release 信息
    parallel_sync: bool = False             # 是否并行同步
    max_workers: int = 3                    # 最大并行数


@dataclass
class SyncProgress:
    """同步进度"""
    status: SyncStatus
    total_repos: int = 0
    processed_repos: int = 0
    added_repos: int = 0
    updated_repos: int = 0
    deleted_repos: int = 0
    skipped_repos: int = 0
    failed_repos: int = 0
    conflicts: int = 0
    start_time: Optional[str] = None
    current_time: Optional[str] = None
    estimated_time_remaining: Optional[int] = None
    current_repo: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_repos == 0:
            return 0.0
        return (self.processed_repos / self.total_repos) * 100


@dataclass
class SyncHistoryRecord:
    """同步历史记录"""
    id: Optional[int] = None
    sync_type: str = "repositories"         # 同步类型
    status: str = "success"                 # 状态
    started_at: Optional[str] = None        # 开始时间
    completed_at: Optional[str] = None      # 完成时间
    items_processed: int = 0                # 处理项数
    items_added: int = 0                    # 新增项数
    items_updated: int = 0                  # 更新项数
    items_deleted: int = 0                  # 删除项数
    error_message: Optional[str] = None     # 错误信息
    execution_time_ms: Optional[int] = None # 执行时间（毫秒）
    user_id: Optional[int] = None           # 用户ID
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据


@dataclass
class ConflictRecord:
    """冲突记录"""
    repo_id: int
    repo_full_name: str
    field_name: str
    local_value: Any
    remote_value: Any
    resolution: Optional[str] = None
    resolved_at: Optional[str] = None


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "./data/github_stars.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_db_exists()
        self._init_sync_tables()
    
    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _init_sync_tables(self):
        """初始化同步相关表"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 同步配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key VARCHAR(255) UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 同步状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status VARCHAR(50) NOT NULL,
                    progress_data TEXT,
                    last_sync_at DATETIME,
                    next_sync_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 冲突记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_conflicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER NOT NULL,
                    repo_full_name VARCHAR(255) NOT NULL,
                    field_name VARCHAR(100) NOT NULL,
                    local_value TEXT,
                    remote_value TEXT,
                    resolution VARCHAR(50),
                    resolved_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("同步相关表初始化成功")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"初始化同步表失败: {e}")
            raise
        finally:
            conn.close()
    
    def save_sync_history(self, record: SyncHistoryRecord) -> int:
        """
        保存同步历史记录
        
        Args:
            record: 同步历史记录
            
        Returns:
            记录ID
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            metadata_json = json.dumps(record.metadata) if record.metadata else None
            
            cursor.execute("""
                INSERT INTO sync_logs (
                    sync_type, status, started_at, completed_at,
                    items_processed, items_added, items_updated, items_deleted,
                    error_message, execution_time_ms, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.sync_type, record.status, record.started_at, record.completed_at,
                record.items_processed, record.items_added, record.items_updated, record.items_deleted,
                record.error_message, record.execution_time_ms, record.user_id
            ))
            
            conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存同步历史失败: {e}")
            raise
        finally:
            conn.close()
    
    def get_sync_history(self, limit: int = 50, offset: int = 0) -> List[SyncHistoryRecord]:
        """
        获取同步历史记录
        
        Args:
            limit: 返回记录数
            offset: 偏移量
            
        Returns:
            同步历史记录列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_logs
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            records = []
            
            for row in rows:
                records.append(SyncHistoryRecord(
                    id=row['id'],
                    sync_type=row['sync_type'],
                    status=row['status'],
                    started_at=row['started_at'],
                    completed_at=row['completed_at'],
                    items_processed=row['items_processed'],
                    items_added=row['items_added'],
                    items_updated=row['items_updated'],
                    items_deleted=row['items_deleted'],
                    error_message=row['error_message'],
                    execution_time_ms=row['execution_time_ms'],
                    user_id=row['user_id']
                ))
            
            return records
            
        finally:
            conn.close()
    
    def save_conflict(self, conflict: ConflictRecord) -> int:
        """
        保存冲突记录
        
        Args:
            conflict: 冲突记录
            
        Returns:
            记录ID
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sync_conflicts (
                    repo_id, repo_full_name, field_name,
                    local_value, remote_value, resolution, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conflict.repo_id, conflict.repo_full_name, conflict.field_name,
                json.dumps(conflict.local_value), json.dumps(conflict.remote_value),
                conflict.resolution, conflict.resolved_at
            ))
            
            conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存冲突记录失败: {e}")
            raise
        finally:
            conn.close()
    
    def get_unresolved_conflicts(self) -> List[ConflictRecord]:
        """
        获取未解决的冲突
        
        Returns:
            冲突记录列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_conflicts
                WHERE resolution IS NULL
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            conflicts = []
            
            for row in rows:
                conflicts.append(ConflictRecord(
                    repo_id=row['repo_id'],
                    repo_full_name=row['repo_full_name'],
                    field_name=row['field_name'],
                    local_value=json.loads(row['local_value']) if row['local_value'] else None,
                    remote_value=json.loads(row['remote_value']) if row['remote_value'] else None,
                    resolution=row['resolution'],
                    resolved_at=row['resolved_at']
                ))
            
            return conflicts
            
        finally:
            conn.close()
    
    def get_repository_by_github_id(self, github_id: int) -> Optional[Dict[str, Any]]:
        """
        通过 GitHub ID 获取仓库
        
        Args:
            github_id: GitHub 仓库 ID
            
        Returns:
            仓库数据字典
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repositories WHERE github_id = ?", (github_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
        finally:
            conn.close()
    
    def save_repository(self, repo: StarredRepo) -> int:
        """
        保存或更新仓库
        
        Args:
            repo: 星标仓库对象
            
        Returns:
            仓库ID
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 检查仓库是否存在
            existing = self.get_repository_by_github_id(repo.id)
            
            topics_json = json.dumps(repo.topics) if repo.topics else "[]"
            
            if existing:
                # 更新现有仓库
                cursor.execute("""
                    UPDATE repositories SET
                        name = ?, full_name = ?, description = ?,
                        html_url = ?, language = ?, topics = ?,
                        stars_count = ?, archived = ?, license = ?,
                        last_updated_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE github_id = ?
                """, (
                    repo.name, repo.full_name, repo.description,
                    repo.html_url, repo.language, topics_json,
                    repo.stargazers_count, repo.is_archived, repo.license,
                    repo.updated_at, repo.id
                ))
                
                repo_id = existing['id']
                
            else:
                # 插入新仓库
                owner, name = repo.full_name.split('/', 1)
                
                cursor.execute("""
                    INSERT INTO repositories (
                        github_id, owner, name, full_name, description,
                        html_url, language, topics, stars_count,
                        archived, license, first_seen_at, last_updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    repo.id, owner, name, repo.full_name, repo.description,
                    repo.html_url, repo.language, topics_json, repo.stargazers_count,
                    repo.is_archived, repo.license, repo.starred_at, repo.updated_at
                ))
                
                repo_id = cursor.lastrowid
            
            conn.commit()
            return repo_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存仓库失败: {e}")
            raise
        finally:
            conn.close()


class SyncService:
    """同步服务"""
    
    def __init__(self, 
                 github_service: GitHubService,
                 db_manager: DatabaseManager,
                 config: Optional[SyncConfig] = None):
        """
        初始化同步服务
        
        Args:
            github_service: GitHub 服务
            db_manager: 数据库管理器
            config: 同步配置
        """
        self.github_service = github_service
        self.db_manager = db_manager
        self.config = config or SyncConfig()
        
        self.progress = SyncProgress(status=SyncStatus.IDLE)
        self._stop_flag = False
        self._pause_flag = False
        self._lock = threading.Lock()
        
        # 进度回调函数
        self.progress_callbacks: List[Callable[[SyncProgress], None]] = []
    
    def add_progress_callback(self, callback: Callable[[SyncProgress], None]):
        """
        添加进度回调函数
        
        Args:
            callback: 回调函数
        """
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self):
        """通知进度更新"""
        for callback in self.progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
    
    def sync_repositories(self, force_full: bool = False) -> SyncHistoryRecord:
        """
        同步星标仓库
        
        Args:
            force_full: 是否强制全量同步
            
        Returns:
            同步历史记录
        """
        with self._lock:
            if self.progress.status == SyncStatus.RUNNING:
                raise RuntimeError("同步任务正在运行中")
            
            self.progress = SyncProgress(
                status=SyncStatus.RUNNING,
                start_time=datetime.now().isoformat()
            )
            self._stop_flag = False
            self._pause_flag = False
        
        start_time = datetime.now()
        history_record = SyncHistoryRecord(
            sync_type="repositories",
            started_at=start_time.isoformat()
        )
        
        try:
            logger.info("开始同步星标仓库...")
            
            # 获取远程仓库列表
            sync_result = self.github_service.sync_starred_repos(
                force_refresh=force_full or self.config.mode == SyncMode.FULL
            )
            
            if not sync_result.success:
                raise RuntimeError(f"获取远程仓库失败: {', '.join(sync_result.errors)}")
            
            # 从缓存获取仓库数据
            remote_repos = self._get_remote_repos_from_cache()
            
            self.progress.total_repos = len(remote_repos)
            self._notify_progress()
            
            # 获取本地仓库列表
            local_repos = self._get_local_repos()
            local_repo_map = {repo['github_id']: repo for repo in local_repos}
            
            # 处理远程仓库
            for idx, remote_repo in enumerate(remote_repos):
                if self._stop_flag:
                    self.progress.status = SyncStatus.CANCELLED
                    history_record.status = "cancelled"
                    break
                
                while self._pause_flag:
                    time.sleep(1)
                
                self.progress.current_repo = remote_repo.full_name
                self.progress.current_time = datetime.now().isoformat()
                self._notify_progress()
                
                try:
                    local_repo = local_repo_map.get(remote_repo.id)
                    
                    if local_repo:
                        # 检查是否需要更新
                        if self._should_update(local_repo, remote_repo):
                            # 处理冲突
                            if self._has_local_modifications(local_repo):
                                resolved_repo = self._resolve_conflict(local_repo, remote_repo)
                                if resolved_repo:
                                    self.db_manager.save_repository(resolved_repo)
                                    self.progress.updated_repos += 1
                                else:
                                    self.progress.skipped_repos += 1
                                    self.progress.conflicts += 1
                            else:
                                # 直接更新
                                self.db_manager.save_repository(remote_repo)
                                self.progress.updated_repos += 1
                        else:
                            self.progress.skipped_repos += 1
                    else:
                        # 新增仓库
                        self.db_manager.save_repository(remote_repo)
                        self.progress.added_repos += 1
                    
                    self.progress.processed_repos += 1
                    
                except Exception as e:
                    logger.error(f"处理仓库 {remote_repo.full_name} 失败: {e}")
                    self.progress.failed_repos += 1
                
                # 计算预估剩余时间
                if self.progress.processed_repos > 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / self.progress.processed_repos
                    remaining = self.progress.total_repos - self.progress.processed_repos
                    self.progress.estimated_time_remaining = int(remaining * avg_time)
                
                self._notify_progress()
            
            # 检查已删除的仓库
            remote_ids = {repo.id for repo in remote_repos}
            for local_repo in local_repos:
                if local_repo['github_id'] not in remote_ids:
                    # 标记为已删除或从数据库删除
                    # 这里选择保留，但可以添加删除标记
                    self.progress.deleted_repos += 1
            
            # 完成同步
            end_time = datetime.now()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if self.progress.status != SyncStatus.CANCELLED:
                self.progress.status = SyncStatus.SUCCESS
                history_record.status = "success"
            
            history_record.completed_at = end_time.isoformat()
            history_record.items_processed = self.progress.processed_repos
            history_record.items_added = self.progress.added_repos
            history_record.items_updated = self.progress.updated_repos
            history_record.items_deleted = self.progress.deleted_repos
            history_record.execution_time_ms = execution_time_ms
            
            logger.info(f"同步完成: 处理={self.progress.processed_repos}, "
                       f"新增={self.progress.added_repos}, "
                       f"更新={self.progress.updated_repos}, "
                       f"删除={self.progress.deleted_repos}, "
                       f"失败={self.progress.failed_repos}")
            
        except Exception as e:
            logger.error(f"同步失败: {e}")
            
            self.progress.status = SyncStatus.FAILED
            self.progress.error_message = str(e)
            
            history_record.status = "failed"
            history_record.error_message = str(e)
            history_record.completed_at = datetime.now().isoformat()
        
        finally:
            # 保存同步历史
            try:
                self.db_manager.save_sync_history(history_record)
            except Exception as e:
                logger.error(f"保存同步历史失败: {e}")
            
            self._notify_progress()
        
        return history_record
    
    def _get_remote_repos_from_cache(self) -> List[StarredRepo]:
        """从缓存获取远程仓库列表"""
        # 这里简化实现，实际应该从 GitHub 服务的缓存中获取
        # 假设已经在 sync_starred_repos 中缓存了数据
        try:
            cache_key = "starred_repos_list"
            cached = self.github_service.cache.get(cache_key)
            
            if cached:
                return [StarredRepo(**repo_data) for repo_data in cached]
            
            # 如果缓存不存在，重新获取
            sync_result = self.github_service.sync_starred_repos()
            # 这里需要修改 github_service 来返回仓库列表
            return []
            
        except Exception as e:
            logger.error(f"从缓存获取远程仓库失败: {e}")
            return []
    
    def _get_local_repos(self) -> List[Dict[str, Any]]:
        """获取本地仓库列表"""
        conn = self.db_manager._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repositories")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def _should_update(self, local_repo: Dict[str, Any], remote_repo: StarredRepo) -> bool:
        """
        判断是否需要更新
        
        Args:
            local_repo: 本地仓库数据
            remote_repo: 远程仓库数据
            
        Returns:
            是否需要更新
        """
        # 比较更新时间
        local_updated = local_repo.get('last_updated_at', '')
        remote_updated = remote_repo.updated_at
        
        if remote_updated > local_updated:
            return True
        
        # 比较关键字段
        if local_repo.get('stars_count', 0) != remote_repo.stargazers_count:
            return True
        
        if local_repo.get('description') != remote_repo.description:
            return True
        
        return False
    
    def _has_local_modifications(self, local_repo: Dict[str, Any]) -> bool:
        """
        检查是否有本地修改
        
        Args:
            local_repo: 本地仓库数据
            
        Returns:
            是否有本地修改
        """
        # 检查是否有用户自定义字段
        if local_repo.get('user_notes'):
            return True
        
        if local_repo.get('user_rating'):
            return True
        
        # 检查是否有自定义分类
        # 这里简化，实际需要查询 repository_categories 表
        
        return False
    
    def _resolve_conflict(self, 
                         local_repo: Dict[str, Any], 
                         remote_repo: StarredRepo) -> Optional[StarredRepo]:
        """
        解决冲突
        
        Args:
            local_repo: 本地仓库数据
            remote_repo: 远程仓库数据
            
        Returns:
            解决后的仓库数据
        """
        strategy = self.config.conflict_strategy
        
        if strategy == ConflictStrategy.KEEP_LOCAL:
            return None  # 不更新
        
        elif strategy == ConflictStrategy.KEEP_REMOTE:
            return remote_repo  # 直接使用远程数据
        
        elif strategy == ConflictStrategy.MERGE:
            # 合并策略：使用远程数据，保留本地自定义字段
            merged_repo = remote_repo
            # 这里需要将本地自定义字段复制到 merged_repo
            # 由于 StarredRepo 不包含用户自定义字段，这里简化处理
            return merged_repo
        
        elif strategy == ConflictStrategy.ASK_USER:
            # 记录冲突，等待用户处理
            conflict = ConflictRecord(
                repo_id=local_repo['id'],
                repo_full_name=local_repo['full_name'],
                field_name="multiple",
                local_value=local_repo,
                remote_value=asdict(remote_repo)
            )
            self.db_manager.save_conflict(conflict)
            return None
        
        return None
    
    def stop_sync(self):
        """停止同步"""
        self._stop_flag = True
        logger.info("同步任务停止中...")
    
    def pause_sync(self):
        """暂停同步"""
        self._pause_flag = True
        self.progress.status = SyncStatus.PAUSED
        logger.info("同步任务已暂停")
    
    def resume_sync(self):
        """恢复同步"""
        self._pause_flag = False
        self.progress.status = SyncStatus.RUNNING
        logger.info("同步任务已恢复")
    
    def get_progress(self) -> SyncProgress:
        """获取当前进度"""
        return self.progress
    
    def get_sync_history(self, limit: int = 50, offset: int = 0) -> List[SyncHistoryRecord]:
        """获取同步历史"""
        return self.db_manager.get_sync_history(limit, offset)
    
    def get_unresolved_conflicts(self) -> List[ConflictRecord]:
        """获取未解决的冲突"""
        return self.db_manager.get_unresolved_conflicts()


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化服务
    github_service = GitHubService(token="your-github-token")
    db_manager = DatabaseManager()
    sync_service = SyncService(github_service, db_manager)
    
    # 添加进度回调
    def progress_callback(progress: SyncProgress):
        print(f"进度: {progress.get_progress_percentage():.1f}% - "
              f"处理: {progress.processed_repos}/{progress.total_repos} - "
              f"当前: {progress.current_repo}")
    
    sync_service.add_progress_callback(progress_callback)
    
    # 执行同步
    try:
        history = sync_service.sync_repositories()
        print(f"同步完成: {history.status}")
        print(f"新增: {history.items_added}, 更新: {history.items_updated}")
        
    except Exception as e:
        print(f"同步失败: {e}")
