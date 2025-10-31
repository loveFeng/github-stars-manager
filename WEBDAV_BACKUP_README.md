# WebDAV 备份服务

一个功能完整的 WebDAV 备份解决方案，支持多云存储、增量备份、加密存储和自动化调度。

## 🌟 功能特性

### 🌐 WebDAV 客户端
- **多服务商支持**: 坚果云、Nextcloud、ownCloud、自定义 WebDAV
- **完整文件操作**: 上传、下载、删除、目录操作、文件列表
- **连接管理**: 自动重试、会话管理、错误处理
- **空间监控**: 存储配额和使用情况查询

### 💾 备份功能
- **全量备份**: 完整数据备份
- **增量备份**: 仅备份变更文件，提高效率
- **文件过滤**: 支持包含/排除模式
- **压缩存储**: 自动压缩减少存储空间
- **多版本管理**: 自动清理旧备份，保留指定版本数

### 🔒 安全特性
- **数据加密**: 支持 AES 加密保护敏感数据
- **校验和验证**: SHA256 校验确保数据完整性
- **访问控制**: WebDAV 基础认证

### 🔄 智能冲突解决
- **时间戳策略**: 自动选择最新版本
- **版本比较**: 基于文件版本信息决策
- **手动处理**: 支持跳过冲突文件

### ⏰ 自动化调度
- **定时备份**: 支持每日定时自动备份
- **后台运行**: 无需人工干预
- **状态监控**: 实时备份状态和进度跟踪

## 📦 安装依赖

```bash
# 安装必要的 Python 包
pip install requests cryptography schedule
```

## 🚀 快速开始

### 1. 基本 WebDAV 连接测试

```python
from services import create_webdav_client

# 创建 WebDAV 客户端
client = create_webdav_client(
    service_type="nutstore",  # 或 "nextcloud", "owncloud"
    url="https://dav.jianguoyun.com/dav/",
    username="your-username",
    password="your-password"
)

# 测试连接
try:
    client._test_connection()
    print("连接成功！")
except Exception as e:
    print(f"连接失败: {e}")

# 列出文件
files = client.list_files()
print(f"找到 {len(files)} 个文件")
```

### 2. 配置备份任务

```python
from services import WebDAVService, BackupService, BackupConfig

# 创建 WebDAV 服务
webdav_service = WebDAVService()
webdav_service.add_client("my_cloud", credentials)

# 创建备份服务
backup_service = BackupService(webdav_service, metadata_store)

# 配置备份任务
config = BackupConfig(
    name="文档备份",
    source_paths=["/path/to/documents"],
    target_client_id="my_cloud",
    target_path="/backups",
    include_patterns=["*.txt", "*.pdf", "*.doc*"],
    exclude_patterns=["*.tmp", "*.log", "__pycache__/*"],
    encrypt=True,
    encryption_key="your-secret-key",
    compression=True,
    incremental=True,
    max_versions=30,
    schedule_time="02:00",  # 每日凌晨2点
    conflict_resolution="timestamp"
)

# 添加配置
backup_service.add_config(config)
```

### 3. 执行备份

```python
# 执行全量备份
backup_id = backup_service.execute_backup("文档备份", "full")
print(f"备份完成，ID: {backup_id}")

# 执行增量备份（推荐）
backup_id = backup_service.execute_backup("文档备份", "incremental")
```

### 4. 恢复数据

```python
# 查看可用备份
backups = backup_service.list_backups("文档备份")
for backup in backups:
    print(f"备份: {backup.backup_id} - {backup.created_at}")

# 恢复备份
backup_id = backups[0].backup_id
session_id = backup_service.restore_backup(backup_id, "/path/to/restore")

# 监控恢复进度
while True:
    session = backup_service.get_restore_session(session_id)
    print(f"恢复进度: {session.files_restored}/{session.total_files}")
    if session.status in ["completed", "failed"]:
        break
    time.sleep(1)
```

### 5. 启动自动调度

```python
# 启动调度器
backup_service.start_scheduler()

# 程序将持续运行，执行定时备份
# 使用 Ctrl+C 停止
```

## ☁️ 支持的 WebDAV 服务商

### 坚果云
```python
client = create_webdav_client(
    service_type="nutstore",
    url="https://dav.jianguoyun.com/dav/",
    username="your-username",
    password="your-password"
)
```

### Nextcloud
```python
client = create_webdav_client(
    service_type="nextcloud",
    url="https://your-domain.com/remote.php/webdav/",
    username="your-username",
    password="your-password"
)
```

### ownCloud
```python
client = create_webdav_client(
    service_type="owncloud",
    url="https://your-domain.com/remote.php/webdav/",
    username="your-username", 
    password="your-password"
)
```

## ⚙️ 配置选项说明

### BackupConfig 参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `name` | str | 备份任务名称 | 必需 |
| `source_paths` | List[str] | 源文件路径列表 | 必需 |
| `target_client_id` | str | 目标 WebDAV 客户端 ID | 必需 |
| `target_path` | str | 远程备份路径 | 必需 |
| `include_patterns` | List[str] | 包含文件模式 | [] |
| `exclude_patterns` | List[str] | 排除文件模式 | [] |
| `encrypt` | bool | 是否加密 | False |
| `encrypt_key` | str | 加密密钥 | "" |
| `compression` | bool | 是否压缩 | True |
| `incremental` | bool | 是否增量备份 | True |
| `max_versions` | int | 最大版本数 | 10 |
| `schedule_time` | str | 调度时间（HH:MM） | "" |
| `auto_delete_old` | bool | 自动删除旧版本 | True |
| `conflict_resolution` | str | 冲突解决策略 | "timestamp" |

### 文件过滤模式

支持 Unix shell 风格的文件匹配模式：

```python
include_patterns = [
    "*.txt",        # 所有 .txt 文件
    "*.pdf",        # 所有 .pdf 文件
    "docs/*.doc",   # docs 目录下的 .doc 文件
    "images/**/*",  # images 目录下的所有文件
]

exclude_patterns = [
    "*.tmp",        # 临时文件
    "*.log",        # 日志文件
    "__pycache__/*", # Python 缓存
    ".git/*",       # Git 目录
    "node_modules/*" # Node.js 依赖
]
```

## 🎯 高级用法

### 1. 批量备份多个目录

```python
config = BackupConfig(
    name="多目录备份",
    source_paths=[
        "/path/to/documents",
        "/path/to/photos", 
        "/path/to/projects"
    ],
    target_client_id="my_cloud",
    target_path="/backups",
    # ... 其他配置
)
```

### 2. 不同类型文件使用不同策略

```python
# 为重要文档启用加密
config_docs = BackupConfig(
    name="重要文档备份",
    source_paths=["/path/to/important"],
    target_client_id="my_cloud",
    target_path="/backups/important",
    encrypt=True,
    encrypt_key="secure-key-123"
)

# 为媒体文件启用压缩但不加密
config_media = BackupConfig(
    name="媒体文件备份",
    source_paths=["/path/to/media"],
    target_client_id="my_cloud",
    target_path="/backups/media",
    encrypt=False,
    compression=True
)
```

### 3. 监控和统计

```python
# 获取备份统计信息
stats = backup_service.get_backup_statistics("文档备份")
print(f"总备份数: {stats['total_backups']}")
print(f"总大小: {stats['total_size']} 字节")
print(f"平均大小: {stats['average_size']} 字节")
print(f"最后备份: {stats['last_backup']}")

# 获取所有备份状态
all_backups = backup_service.list_backups()
for backup in all_backups:
    print(f"备份 {backup.backup_id}: {backup.backup_type} - {backup.created_at}")
```

## 📊 API 参考

### WebDAVClient

主要的 WebDAV 客户端类：

- `list_files(remote_path)`: 列出远程目录文件
- `upload_file(local_path, remote_path)`: 上传文件
- `download_file(remote_path, local_path)`: 下载文件
- `create_directory(remote_path)`: 创建远程目录
- `delete_file(remote_path)`: 删除远程文件/目录
- `file_exists(remote_path)`: 检查文件是否存在
- `get_file_info(remote_path)`: 获取文件信息
- `get_space_usage()`: 获取存储空间使用情况

### BackupService

主要的备份服务类：

- `add_config(config)`: 添加备份配置
- `execute_backup(config_name, backup_type)`: 执行备份
- `restore_backup(backup_id, target_path)`: 恢复备份
- `list_backups(config_name)`: 列出备份
- `start_scheduler()`: 启动调度器
- `stop_scheduler()`: 停止调度器
- `get_backup_statistics(config_name)`: 获取统计信息

## 🐛 故障排除

### 常见问题

1. **连接失败**
   ```
   WebDAVConnectionError: 连接测试失败，状态码: 401
   ```
   检查用户名、密码和 URL 是否正确

2. **认证错误**
   ```
   WebDAVAuthError: 认证失败
   ```
   确认 WebDAV 服务商支持基础认证

3. **文件上传失败**
   ```
   BackupExecutionError: 上传文件失败
   ```
   检查文件权限和磁盘空间

4. **加密相关错误**
   ```
   错误: No module named 'cryptography'
   ```
   安装加密依赖：`pip install cryptography`

### 调试模式

启用详细日志输出：

```python
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('services')
logger.setLevel(logging.DEBUG)
```

### 测试连接

使用提供的演示脚本测试连接：

```bash
python webdav_backup_demo.py
```

## ⚡ 性能优化

1. **增量备份**: 对于大型数据集，优先使用增量备份
2. **并发上传**: 考虑为大量小文件实现并发上传
3. **压缩策略**: 对于文本文件启用压缩，媒体文件可能不需要
4. **网络优化**: 调整 HTTP 超时和重试参数

## 🔐 安全建议

1. **密钥管理**: 使用环境变量或安全的密钥管理服务
2. **网络安全**: 确保 WebDAV 服务器使用 HTTPS
3. **访问控制**: 限制 WebDAV 账户权限
4. **定期检查**: 监控备份完整性和访问日志

## 📝 示例运行

```bash
# 运行演示程序
python webdav_backup_demo.py
```

## 📂 项目结构

```
services/
├── __init__.py          # 包初始化文件
├── webdav_service.py    # WebDAV 客户端服务
├── backup_service.py    # 备份服务
└── README.md           # 服务包说明（AI服务）

webdav_backup_demo.py   # WebDAV 备份演示程序
WEBDAV_BACKUP_README.md # WebDAV 备份服务说明文档
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 📄 许可证

本项目采用 MIT 许可证。

## 🗓️ 更新日志

### v1.0.0
- 初始版本发布
- 支持主流 WebDAV 服务商（坚果云、Nextcloud、ownCloud）
- 实现全量和增量备份
- 添加加密和压缩功能
- 支持自动调度和冲突解决
- 提供完整的恢复功能