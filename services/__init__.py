"""
GitHubStarsManager 服务包

基于 GitHubStarsManager 项目实现的完整服务解决方案：
1. GitHub API 集成服务 (github_api.py, github_service.py)
2. AI 服务 (ai_client.py, ai_service.py)
3. 数据备份服务 (backup_service.py, webdav_service.py)
"""

# GitHub API 集成服务
from .github_api import (
    GitHubAPIClient,
    GitHubAPIBatchClient,
    GitHubUser,
    GitHubRepository,
    GitHubRelease,
    GitHubAsset,
    RateLimitInfo,
    GitHubAPIError,
    RateLimitExceededError,
    AuthenticationError,
    NotFoundError,
    ValidationError
)

from .github_service import (
    GitHubService,
    StarredRepo,
    RepositoryAsset,
    ReleaseUpdate,
    SyncResult,
    AIConfig,
    CacheManager,
    AIService,
    AssetFilter,
    CategoryManager
)

# AI 服务
from .ai_client import (
    OpenAICompatibleClient,
    APIConfig,
    ModelType,
    TaskType,
    UsageStats,
    APIResponse,
    RateLimiter,
    create_client
)

from .ai_service import (
    AIService as CoreAIService,
    RepositoryAnalyzer,
    SemanticSearch,
    BatchProcessor,
    TaskQueue,
    Task,
    TaskStatus,
    Priority,
    RepositorySummary,
    ClassificationResult,
    EmbeddingVector
)

from .webdav_service import (
    WebDAVClient,
    WebDAVCredentials,
    WebDAVService,
    WebDAVFile,
    WebDAVError,
    WebDAVConnectionError,
    WebDAVAuthError,
    create_webdav_client,
    WEBDAV_SERVICES
)

from .backup_service import (
    BackupService,
    BackupConfig,
    BackupManifest,
    BackupFileInfo,
    RestoreSession,
    BackupError,
    BackupConfigError,
    BackupExecutionError,
    create_backup_service,
    SAMPLE_BACKUP_CONFIG
)

__all__ = [
    # GitHub API 客户端
    "GitHubAPIClient",
    "GitHubAPIBatchClient",
    "GitHubUser",
    "GitHubRepository",
    "GitHubRelease",
    "GitHubAsset",
    "RateLimitInfo",
    "GitHubAPIError",
    "RateLimitExceededError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    
    # GitHub 业务服务
    "GitHubService",
    "StarredRepo",
    "RepositoryAsset",
    "ReleaseUpdate",
    "SyncResult",
    "AIConfig",
    "CacheManager",
    "AIService",
    "AssetFilter",
    "CategoryManager",
    
    # AI 客户端
    "OpenAICompatibleClient",
    "APIConfig", 
    "ModelType",
    "TaskType",
    "UsageStats",
    "APIResponse",
    "RateLimiter",
    "create_client",
    
    # AI 服务
    "CoreAIService",
    "RepositoryAnalyzer", 
    "SemanticSearch",
    "BatchProcessor",
    "TaskQueue",
    "Task",
    "TaskStatus",
    "Priority",
    "RepositorySummary",
    "ClassificationResult",
    "EmbeddingVector",
    
    # WebDAV 服务
    "WebDAVClient",
    "WebDAVCredentials",
    "WebDAVService",
    "WebDAVFile",
    "WebDAVError",
    "WebDAVConnectionError",
    "WebDAVAuthError",
    "create_webdav_client",
    "WEBDAV_SERVICES",
    
    # 备份服务
    "BackupService",
    "BackupConfig",
    "BackupManifest",
    "BackupFileInfo",
    "RestoreSession",
    "BackupError",
    "BackupConfigError",
    "BackupExecutionError",
    "create_backup_service",
    "SAMPLE_BACKUP_CONFIG"
]

__version__ = "1.0.0"
__author__ = "GitHubStarsManager Team"