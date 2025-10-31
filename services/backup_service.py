"""
备份服务
提供数据备份、恢复、增量备份、冲突解决、加密存储和计划任务等功能
"""

import os
import json
import hashlib
import gzip
import shutil
import logging
import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import mimetypes
import sqlite3
import pickle

from .webdav_service import WebDAVClient, WebDAVCredentials, WebDAVService


@dataclass
class BackupConfig:
    """备份配置"""
    name: str
    source_paths: List[str]
    target_client_id: str
    target_path: str
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    encrypt: bool = False
    encrypt_key: str = ""
    compression: bool = True
    incremental: bool = True
    max_versions: int = 10
    schedule_time: str = ""  # Cron 表达式或时间字符串
    auto_delete_old: bool = True
    conflict_resolution: str = "timestamp"  # timestamp, version, skip
    
    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []


@dataclass
class BackupFileInfo:
    """备份文件信息"""
    path: str
    size: int
    modified_time: datetime
    checksum: str
    compressed_size: int = 0
    encrypted: bool = False


@dataclass
class BackupManifest:
    """备份清单"""
    backup_id: str
    config_name: str
    created_at: datetime
    backup_type: str  # full, incremental
    files: List[BackupFileInfo]
    total_size: int
    compressed_size: int
    encrypted: bool
    checksum: str
    version: str = "1.0"


@dataclass
class RestoreSession:
    """恢复会话"""
    session_id: str
    manifest: BackupManifest
    target_path: str
    started_at: datetime
    status: str  # running, completed, failed
    files_restored: int = 0
    total_files: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class BackupError(Exception):
    """备份错误异常"""
    pass


class BackupConfigError(BackupError):
    """备份配置错误"""
    pass


class BackupExecutionError(BackupError):
    """备份执行错误"""
    pass


class EncryptionManager:
    """加密管理器"""
    
    def __init__(self, key: str = ""):
        self.key = key.encode('utf-8') if key else os.urandom(32)
        self.key_hash = hashlib.sha256(self.key).hexdigest()
    
    def encrypt_data(self, data: bytes) -> bytes:
        """
        加密数据
        
        Args:
            data: 原始数据
            
        Returns:
            加密后的数据
        """
        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(self._derive_key())
            return fernet.encrypt(data)
        except ImportError:
            # 简单的 XOR 加密作为备用方案
            return self._simple_xor_encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """
        解密数据
        
        Args:
            encrypted_data: 加密数据
            
        Returns:
            原始数据
        """
        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(self._derive_key())
            return fernet.decrypt(encrypted_data)
        except ImportError:
            # 简单的 XOR 解密
            return self._simple_xor_decrypt(encrypted_data)
    
    def _derive_key(self) -> bytes:
        """派生加密密钥"""
        # 使用 PBKDF2 派生密钥
        import hashlib
        import os
        salt = b'webdav_backup_salt'
        return hashlib.pbkdf2_hmac('sha256', self.key, salt, 100000)
    
    def _simple_xor_encrypt(self, data: bytes) -> bytes:
        """简单 XOR 加密（备用方案）"""
        key_bytes = self.key * (len(data) // len(self.key) + 1)
        return bytes(a ^ b for a, b in zip(data, key_bytes[:len(data)]))
    
    def _simple_xor_decrypt(self, encrypted_data: bytes) -> bytes:
        """简单 XOR 解密（备用方案）"""
        return self._simple_xor_encrypt(encrypted_data)


class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self, resolution_strategy: str = "timestamp"):
        self.strategy = resolution_strategy
    
    def resolve_conflict(self, local_file: Path, remote_file: Path, 
                        local_info: BackupFileInfo, remote_info: BackupFileInfo) -> str:
        """
        解决文件冲突
        
        Args:
            local_file: 本地文件路径
            remote_file: 远程文件路径
            local_info: 本地文件信息
            remote_info: 远程文件信息
            
        Returns:
            冲突解决策略: "local", "remote", "skip", "rename"
        """
        if self.strategy == "timestamp":
            return self._resolve_by_timestamp(local_info, remote_info)
        elif self.strategy == "version":
            return self._resolve_by_version(local_info, remote_info)
        elif self.strategy == "skip":
            return "skip"
        else:
            return "timestamp"  # 默认策略
    
    def _resolve_by_timestamp(self, local_info: BackupFileInfo, remote_info: BackupFileInfo) -> str:
        """按时间戳解决冲突"""
        if local_info.modified_time > remote_info.modified_time:
            return "local"
        elif remote_info.modified_time > local_info.modified_time:
            return "remote"
        else:
            return "skip"  # 时间相同则跳过
    
    def _resolve_by_version(self, local_info: BackupFileInfo, remote_info: BackupFileInfo) -> str:
        """按版本解决冲突"""
        # 这里可以实现更复杂的版本比较逻辑
        # 暂时使用文件大小作为版本指标
        if local_info.size > remote_info.size:
            return "local"
        elif remote_info.size > local_info.size:
            return "remote"
        else:
            return "skip"


class BackupMetadataStore:
    """备份元数据存储"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id TEXT PRIMARY KEY,
                    config_name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    backup_type TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_info_json TEXT NOT NULL,
                    FOREIGN KEY (backup_id) REFERENCES backups (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_metadata_backup_id 
                ON file_metadata (backup_id)
            """)
    
    def save_backup_manifest(self, manifest: BackupManifest) -> bool:
        """
        保存备份清单
        
        Args:
            manifest: 备份清单
            
        Returns:
            是否保存成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO backups 
                    (id, config_name, created_at, backup_type, manifest_json, checksum, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    manifest.backup_id,
                    manifest.config_name,
                    manifest.created_at,
                    manifest.backup_type,
                    json.dumps(asdict(manifest), default=str),
                    manifest.checksum,
                    "completed"
                ))
                
                # 保存文件元数据
                for file_info in manifest.files:
                    conn.execute("""
                        INSERT INTO file_metadata 
                        (backup_id, file_path, file_info_json)
                        VALUES (?, ?, ?)
                    """, (
                        manifest.backup_id,
                        file_info.path,
                        json.dumps(asdict(file_info), default=str)
                    ))
            
            return True
        except Exception as e:
            logging.error(f"保存备份清单失败: {e}")
            return False
    
    def get_backup_manifest(self, backup_id: str) -> Optional[BackupManifest]:
        """
        获取备份清单
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            备份清单或 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT manifest_json FROM backups WHERE id = ?
                """, (backup_id,))
                
                row = cursor.fetchone()
                if row:
                    manifest_data = json.loads(row[0])
                    return BackupManifest(**manifest_data)
            
            return None
        except Exception as e:
            logging.error(f"获取备份清单失败: {e}")
            return None
    
    def list_backups(self, config_name: str = None) -> List[BackupManifest]:
        """
        列出备份
        
        Args:
            config_name: 配置名称过滤
            
        Returns:
            备份清单列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if config_name:
                    cursor = conn.execute("""
                        SELECT manifest_json FROM backups WHERE config_name = ?
                        ORDER BY created_at DESC
                    """, (config_name,))
                else:
                    cursor = conn.execute("""
                        SELECT manifest_json FROM backups 
                        ORDER BY created_at DESC
                    """)
                
                manifests = []
                for row in cursor.fetchall():
                    try:
                        manifest_data = json.loads(row[0])
                        manifests.append(BackupManifest(**manifest_data))
                    except Exception as e:
                        logging.warning(f"解析备份清单失败: {e}")
                
                return manifests
        except Exception as e:
            logging.error(f"列出备份失败: {e}")
            return []
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            是否删除成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 删除文件元数据
                conn.execute("DELETE FROM file_metadata WHERE backup_id = ?", (backup_id,))
                # 删除备份记录
                conn.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
            
            return True
        except Exception as e:
            logging.error(f"删除备份失败: {e}")
            return False


class BackupService:
    """备份服务"""
    
    def __init__(self, webdav_service: WebDAVService, metadata_store: BackupMetadataStore):
        """
        初始化备份服务
        
        Args:
            webdav_service: WebDAV 服务
            metadata_store: 元数据存储
        """
        self.webdav_service = webdav_service
        self.metadata_store = metadata_store
        self.configs: Dict[str, BackupConfig] = {}
        self.active_backups: Dict[str, Dict] = {}
        self.restore_sessions: Dict[str, RestoreSession] = {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化调度器线程
        self.scheduler_thread = None
        self.scheduler_running = False
        
        # 加密管理器
        self.encryption_manager = EncryptionManager()
        
        # 冲突解决器
        self.conflict_resolver = ConflictResolver()
    
    def add_config(self, config: BackupConfig) -> bool:
        """
        添加备份配置
        
        Args:
            config: 备份配置
            
        Returns:
            是否添加成功
        """
        try:
            # 验证配置
            self._validate_config(config)
            
            self.configs[config.name] = config
            self.logger.info(f"添加备份配置: {config.name}")
            
            # 如果配置了自动备份，启动调度
            if config.schedule_time:
                self._schedule_backup(config)
            
            return True
        except BackupConfigError as e:
            self.logger.error(f"备份配置验证失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"添加备份配置失败: {e}")
            return False
    
    def remove_config(self, config_name: str) -> bool:
        """
        移除备份配置
        
        Args:
            config_name: 配置名称
            
        Returns:
            是否移除成功
        """
        if config_name in self.configs:
            del self.configs[config_name]
            self.logger.info(f"移除备份配置: {config_name}")
            return True
        return False
    
    def get_config(self, config_name: str) -> Optional[BackupConfig]:
        """
        获取备份配置
        
        Args:
            config_name: 配置名称
            
        Returns:
            备份配置或 None
        """
        return self.configs.get(config_name)
    
    def list_configs(self) -> List[str]:
        """
        列出所有备份配置
        
        Returns:
            配置名称列表
        """
        return list(self.configs.keys())
    
    def _validate_config(self, config: BackupConfig):
        """验证备份配置"""
        if not config.name:
            raise BackupConfigError("配置名称不能为空")
        
        if not config.source_paths:
            raise BackupConfigError("源路径不能为空")
        
        if not config.target_client_id:
            raise BackupConfigError("目标客户端 ID 不能为空")
        
        if not config.target_path:
            raise BackupConfigError("目标路径不能为空")
        
        # 检查 WebDAV 客户端是否存在
        if config.target_client_id not in self.webdav_service.clients:
            raise BackupConfigError(f"WebDAV 客户端不存在: {config.target_client_id}")
        
        # 检查源路径是否存在
        for path in config.source_paths:
            if not Path(path).exists():
                raise BackupConfigError(f"源路径不存在: {path}")
    
    def execute_backup(self, config_name: str, backup_type: str = "full") -> str:
        """
        执行备份
        
        Args:
            config_name: 配置名称
            backup_type: 备份类型 (full, incremental)
            
        Returns:
            备份 ID
        """
        config = self.get_config(config_name)
        if not config:
            raise BackupError(f"备份配置不存在: {config_name}")
        
        # 生成备份 ID
        backup_id = f"{config_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_backups[backup_id] = {
            "config": config,
            "start_time": datetime.now(),
            "status": "running"
        }
        
        try:
            # 执行备份
            manifest = self._perform_backup(config, backup_id, backup_type)
            
            # 保存备份清单
            self.metadata_store.save_backup_manifest(manifest)
            
            # 更新备份状态
            self.active_backups[backup_id]["status"] = "completed"
            self.active_backups[backup_id]["manifest"] = manifest
            
            # 清理旧备份
            if config.auto_delete_old:
                self._cleanup_old_backups(config)
            
            self.logger.info(f"备份完成: {backup_id}")
            return backup_id
        
        except Exception as e:
            self.active_backups[backup_id]["status"] = "failed"
            self.active_backups[backup_id]["error"] = str(e)
            self.logger.error(f"备份失败 {backup_id}: {e}")
            raise BackupExecutionError(f"备份执行失败: {e}")
    
    def _perform_backup(self, config: BackupConfig, backup_id: str, backup_type: str) -> BackupManifest:
        """
        执行实际备份操作
        
        Args:
            config: 备份配置
            backup_id: 备份 ID
            backup_type: 备份类型
            
        Returns:
            备份清单
        """
        client = self.webdav_service.get_client(config.target_client_id)
        if not client:
            raise BackupError(f"WebDAV 客户端不存在: {config.target_client_id}")
        
        # 创建备份目录
        backup_dir = f"{config.target_path}/backups/{backup_id}"
        client.create_directory(backup_dir)
        
        files = []
        total_size = 0
        compressed_size = 0
        
        # 获取增量备份的基线
        baseline_files = {}
        if backup_type == "incremental":
            baseline_manifests = self.metadata_store.list_backups(config.name)
            if baseline_manifests:
                latest_baseline = baseline_manifests[0]  # 最新的基线
                for file_info in latest_baseline.files:
                    baseline_files[file_info.path] = file_info
        
        # 扫描源文件
        for source_path in config.source_paths:
            source_files = self._scan_source_files(Path(source_path), config)
            
            for file_info in source_files:
                # 检查是否为增量备份需要备份的文件
                if backup_type == "incremental":
                    baseline_file = baseline_files.get(file_info.path)
                    if baseline_file and baseline_file.modified_time >= file_info.modified_time:
                        continue  # 文件未修改，跳过
                
                # 上传文件
                try:
                    remote_file_path = f"{backup_dir}/{file_info.path}"
                    
                    # 处理加密
                    if config.encrypt:
                        encrypted_data = self.encryption_manager.encrypt_data(file_info.data)
                        file_data = encrypted_data
                        file_info.encrypted = True
                        file_info.compressed_size = len(encrypted_data)
                    else:
                        file_data = file_info.data
                    
                    # 处理压缩
                    if config.compression and not config.encrypt:
                        compressed_data = gzip.compress(file_data)
                        if len(compressed_data) < len(file_data):
                            file_data = compressed_data
                            file_info.compressed_size = len(compressed_data)
                    
                    # 上传到 WebDAV
                    self._upload_file_to_webdav(client, remote_file_path, file_data)
                    
                    file_info.checksum = self._calculate_checksum(file_data)
                    files.append(file_info)
                    
                    total_size += file_info.size
                    compressed_size += file_info.compressed_size or file_info.size
                    
                    self.logger.debug(f"备份文件: {file_info.path}")
                
                except Exception as e:
                    self.logger.error(f"备份文件失败 {file_info.path}: {e}")
                    continue
        
        # 创建清单
        manifest = BackupManifest(
            backup_id=backup_id,
            config_name=config.name,
            created_at=datetime.now(),
            backup_type=backup_type,
            files=files,
            total_size=total_size,
            compressed_size=compressed_size,
            encrypted=config.encrypt,
            checksum=self._calculate_checksum(json.dumps([asdict(f) for f in files], default=str))
        )
        
        # 保存清单到远程
        manifest_path = f"{backup_dir}/manifest.json"
        manifest_data = json.dumps(asdict(manifest), default=str, ensure_ascii=False, indent=2)
        
        if config.encrypt:
            manifest_data = self.encryption_manager.encrypt_data(manifest_data.encode())
        
        self._upload_file_to_webdav(client, manifest_path, manifest_data)
        
        return manifest
    
    def _scan_source_files(self, source_path: Path, config: BackupConfig) -> List[BackupFileInfo]:
        """
        扫描源文件
        
        Args:
            source_path: 源路径
            config: 备份配置
            
        Returns:
            文件信息列表
        """
        files = []
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                # 检查过滤模式
                relative_path = str(file_path.relative_to(source_path))
                
                if not self._match_include_patterns(relative_path, config.include_patterns):
                    continue
                
                if self._match_exclude_patterns(relative_path, config.exclude_patterns):
                    continue
                
                try:
                    # 读取文件内容
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # 获取文件信息
                    stat = file_path.stat()
                    file_info = BackupFileInfo(
                        path=relative_path,
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        checksum="",  # 稍后计算
                        data=file_data  # 临时存储数据
                    )
                    
                    files.append(file_info)
                
                except Exception as e:
                    self.logger.warning(f"读取文件失败 {file_path}: {e}")
                    continue
        
        return files
    
    def _match_include_patterns(self, file_path: str, patterns: List[str]) -> bool:
        """检查文件是否匹配包含模式"""
        if not patterns:
            return True  # 没有包含模式时，返回所有文件
        
        import fnmatch
        for pattern in patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False
    
    def _match_exclude_patterns(self, file_path: str, patterns: List[str]) -> bool:
        """检查文件是否匹配排除模式"""
        import fnmatch
        for pattern in patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False
    
    def _upload_file_to_webdav(self, client: WebDAVClient, remote_path: str, data: bytes):
        """
        上传文件到 WebDAV
        
        Args:
            client: WebDAV 客户端
            remote_path: 远程路径
            data: 文件数据
        """
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            temp_file_path = temp_file.name
        
        try:
            client.upload_file(temp_file_path, remote_path)
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def _calculate_checksum(self, data: bytes) -> str:
        """计算数据校验和"""
        return hashlib.sha256(data).hexdigest()
    
    def _cleanup_old_backups(self, config: BackupConfig):
        """
        清理旧备份
        
        Args:
            config: 备份配置
        """
        try:
            backups = self.metadata_store.list_backups(config.name)
            
            if len(backups) > config.max_versions:
                # 保留最新的配置.max_versions个备份
                old_backups = backups[config.max_versions:]
                
                client = self.webdav_service.get_client(config.target_client_id)
                if not client:
                    return
                
                for old_backup in old_backups:
                    # 从数据库删除
                    self.metadata_store.delete_backup(old_backup.backup_id)
                    
                    # 从 WebDAV 删除
                    backup_dir = f"{config.target_path}/backups/{old_backup.backup_id}"
                    try:
                        # 递归删除目录（这里简化处理）
                        self._delete_webdav_directory(client, backup_dir)
                    except Exception as e:
                        self.logger.warning(f"删除旧备份目录失败 {backup_dir}: {e}")
                
                self.logger.info(f"清理了 {len(old_backups)} 个旧备份")
        
        except Exception as e:
            self.logger.error(f"清理旧备份失败: {e}")
    
    def _delete_webdav_directory(self, client: WebDAVClient, directory_path: str):
        """删除 WebDAV 目录"""
        try:
            # 列出目录中的所有文件
            files = client.list_files(directory_path)
            
            # 删除所有文件
            for file_info in files:
                if not file_info.is_directory:
                    client.delete_file(f"{directory_path}/{file_info.name}")
                else:
                    # 递归删除子目录
                    self._delete_webdav_directory(client, f"{directory_path}/{file_info.name}")
            
            # 删除目录本身
            client.delete_file(directory_path)
        
        except Exception as e:
            self.logger.warning(f"删除 WebDAV 目录失败: {e}")
    
    def restore_backup(self, backup_id: str, target_path: str) -> str:
        """
        恢复备份
        
        Args:
            backup_id: 备份 ID
            target_path: 目标路径
            
        Returns:
            恢复会话 ID
        """
        # 获取备份清单
        manifest = self.metadata_store.get_backup_manifest(backup_id)
        if not manifest:
            raise BackupError(f"备份清单不存在: {backup_id}")
        
        # 获取配置
        config = self.get_config(manifest.config_name)
        if not config:
            raise BackupError(f"备份配置不存在: {manifest.config_name}")
        
        # 创建恢复会话
        session_id = f"restore_{backup_id}_{int(time.time())}"
        session = RestoreSession(
            session_id=session_id,
            manifest=manifest,
            target_path=target_path,
            started_at=datetime.now(),
            status="running",
            total_files=len(manifest.files)
        )
        
        self.restore_sessions[session_id] = session
        
        # 在新线程中执行恢复
        thread = threading.Thread(target=self._perform_restore, args=(session,))
        thread.daemon = True
        thread.start()
        
        return session_id
    
    def _perform_restore(self, session: RestoreSession):
        """
        执行恢复操作
        
        Args:
            session: 恢复会话
        """
        try:
            config = self.get_config(session.manifest.config_name)
            client = self.webdav_service.get_client(config.target_client_id)
            
            if not client:
                session.status = "failed"
                session.errors.append("WebDAV 客户端不存在")
                return
            
            # 创建目标目录
            target_path = Path(session.target_path)
            target_path.mkdir(parents=True, exist_ok=True)
            
            # 下载并恢复文件
            for file_info in session.manifest.files:
                try:
                    remote_file_path = f"{config.target_path}/backups/{session.manifest.backup_id}/{file_info.path}"
                    local_file_path = target_path / file_info.path
                    
                    # 下载文件
                    client.download_file(remote_file_path, local_file_path)
                    
                    # 处理加密
                    if file_info.encrypted:
                        with open(local_file_path, 'rb') as f:
                            encrypted_data = f.read()
                        
                        decrypted_data = self.encryption_manager.decrypt_data(encrypted_data)
                        
                        with open(local_file_path, 'wb') as f:
                            f.write(decrypted_data)
                    
                    # 处理文件时间戳
                    timestamp = file_info.modified_time.timestamp()
                    os.utime(local_file_path, (timestamp, timestamp))
                    
                    session.files_restored += 1
                    
                except Exception as e:
                    error_msg = f"恢复文件失败 {file_info.path}: {e}"
                    session.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            session.status = "completed"
            self.logger.info(f"恢复完成: {session.session_id}")
        
        except Exception as e:
            session.status = "failed"
            session.errors.append(f"恢复过程失败: {e}")
            self.logger.error(f"恢复失败: {e}")
    
    def get_restore_session(self, session_id: str) -> Optional[RestoreSession]:
        """
        获取恢复会话状态
        
        Args:
            session_id: 会话 ID
            
        Returns:
            恢复会话或 None
        """
        return self.restore_sessions.get(session_id)
    
    def list_backups(self, config_name: str = None) -> List[BackupManifest]:
        """
        列出备份
        
        Args:
            config_name: 配置名称过滤
            
        Returns:
            备份清单列表
        """
        return self.metadata_store.list_backups(config_name)
    
    def get_backup_status(self, backup_id: str) -> Optional[Dict]:
        """
        获取备份状态
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            备份状态字典
        """
        return self.active_backups.get(backup_id)
    
    def _schedule_backup(self, config: BackupConfig):
        """
        调度备份任务
        
        Args:
            config: 备份配置
        """
        # 解析调度时间
        try:
            if ':' in config.schedule_time and len(config.schedule_time.split(':')) == 2:
                # 时间格式: "HH:MM"
                hour, minute = map(int, config.schedule_time.split(':'))
                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                    self._scheduled_backup_job, config_name=config.name
                ).tag(config.name)
            else:
                # 其他调度格式可以在这里扩展
                self.logger.warning(f"不支持的调度格式: {config.schedule_time}")
        
        except Exception as e:
            self.logger.error(f"调度备份失败: {e}")
    
    def _scheduled_backup_job(self, config_name: str):
        """
        调度的备份任务
        
        Args:
            config_name: 配置名称
        """
        try:
            self.logger.info(f"开始执行定时备份: {config_name}")
            self.execute_backup(config_name, "incremental")
        except Exception as e:
            self.logger.error(f"定时备份失败: {e}")
    
    def start_scheduler(self):
        """启动调度器"""
        if not self.scheduler_running:
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            self.logger.info("备份调度器已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("备份调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.scheduler_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"调度器错误: {e}")
                time.sleep(60)
    
    def get_backup_statistics(self, config_name: str = None) -> Dict:
        """
        获取备份统计信息
        
        Args:
            config_name: 配置名称
            
        Returns:
            统计信息字典
        """
        backups = self.metadata_store.list_backups(config_name)
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "average_size": 0,
                "last_backup": None
            }
        
        total_size = sum(b.total_size for b in backups)
        last_backup = max(backups, key=lambda x: x.created_at)
        
        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "average_size": total_size // len(backups) if backups else 0,
            "last_backup": last_backup.created_at.isoformat() if last_backup else None,
            "backup_types": {
                "full": len([b for b in backups if b.backup_type == "full"]),
                "incremental": len([b for b in backups if b.backup_type == "incremental"])
            }
        }


# 便捷函数
def create_backup_service(webdav_service: WebDAVService, metadata_db_path: str) -> BackupService:
    """
    创建备份服务的便捷函数
    
    Args:
        webdav_service: WebDAV 服务
        metadata_db_path: 元数据数据库路径
        
    Returns:
        备份服务实例
    """
    metadata_store = BackupMetadataStore(metadata_db_path)
    return BackupService(webdav_service, metadata_store)


# 示例配置
SAMPLE_BACKUP_CONFIG = BackupConfig(
    name="文档备份",
    source_paths=["/path/to/documents"],
    target_client_id="nutstore",
    target_path="/backups",
    include_patterns=["*.txt", "*.pdf", "*.doc*"],
    exclude_patterns=["*.tmp", "*.log", "__pycache__/*"],
    encrypt=True,
    compression=True,
    incremental=True,
    max_versions=30,
    schedule_time="02:00",
    conflict_resolution="timestamp"
)


if __name__ == "__main__":
    # 示例用法
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # 创建 WebDAV 服务
    from .webdav_service import WebDAVService, WebDAVCredentials, create_webdav_client
    
    webdav_service = WebDAVService()
    
    # 添加 WebDAV 客户端
    credentials = WebDAVCredentials(
        username="your-username",
        password="your-password", 
        url="https://dav.jianguoyun.com/dav/",
        service_type="nutstore"
    )
    
    webdav_service.add_client("nutstore", credentials)
    
    # 创建备份服务
    backup_service = create_backup_service(
        webdav_service=webdav_service,
        metadata_db_path="/tmp/backup_metadata.db"
    )
    
    # 添加备份配置
    backup_service.add_config(SAMPLE_BACKUP_CONFIG)
    
    # 执行备份
    try:
        backup_id = backup_service.execute_backup("文档备份", "full")
        print(f"备份完成，ID: {backup_id}")
    except Exception as e:
        print(f"备份失败: {e}")
    
    # 列出备份
    backups = backup_service.list_backups("文档备份")
    print(f"共有 {len(backups)} 个备份")
    
    # 启动调度器
    backup_service.start_scheduler()
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        backup_service.stop_scheduler()
        print("程序已退出")