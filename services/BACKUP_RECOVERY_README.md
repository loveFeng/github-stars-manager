# 数据备份和恢复系统

一个完整的企业级数据备份和恢复解决方案，提供自动备份、完整性验证、多版本管理和灾难恢复能力。

## 🌟 核心功能

### 📦 备份管理器 (BackupManager)
- ✅ **自动定时备份**: 全量备份和增量备份自动调度
- ✅ **手动备份触发**: 随时手动触发备份任务
- ✅ **备份验证**: 完整性检查和文件验证
- ✅ **多版本管理**: 自动管理多个备份版本
- ✅ **存储空间管理**: 监控存储使用和自动清理
- ✅ **备份加密和压缩**: 保护和优化存储空间

### 🔄 恢复服务 (RecoveryService)
- ✅ **一键恢复**: 快速恢复到最新状态
- ✅ **恢复点选择**: 选择任意时间点进行恢复
- ✅ **选择性恢复**: 仅恢复指定文件或目录
- ✅ **灾难恢复**: 完整的灾难恢复计划和执行
- ✅ **实时进度跟踪**: 详细的恢复进度信息
- ✅ **恢复后验证**: 自动验证恢复数据完整性

## 📋 架构概览

```
┌─────────────────────────────────────────────────┐
│           数据备份和恢复系统                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐    ┌─────────────────┐   │
│  │  BackupManager   │    │ RecoveryService │   │
│  │  备份管理器       │    │  恢复服务        │   │
│  └────────┬─────────┘    └────────┬────────┘   │
│           │                       │            │
│  ┌────────┴─────────┐    ┌────────┴────────┐   │
│  │ BackupValidator  │    │ RecoveryExecutor│   │
│  │ 备份验证器        │    │  恢复执行器      │   │
│  └──────────────────┘    └─────────────────┘   │
│                                                 │
│  ┌──────────────────┐    ┌─────────────────┐   │
│  │ StorageManager   │    │  DR Manager     │   │
│  │ 存储管理器        │    │  灾难恢复管理    │   │
│  └──────────────────┘    └─────────────────┘   │
│                                                 │
│           ┌──────────────────┐                  │
│           │  BackupService   │                  │
│           │   备份服务        │                  │
│           └────────┬─────────┘                  │
│                    │                            │
│           ┌────────┴─────────┐                  │
│           │  WebDAVService   │                  │
│           │  WebDAV服务      │                  │
│           └──────────────────┘                  │
└─────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
uv pip install requests cryptography schedule
```

### 2. 初始化服务

```python
import logging
from services.webdav_service import WebDAVService, WebDAVCredentials
from services.backup_manager import create_backup_manager
from services.recovery_service import create_recovery_service

# 配置日志
logging.basicConfig(level=logging.INFO)

# 创建 WebDAV 服务
webdav_service = WebDAVService()
credentials = WebDAVCredentials(
    username="your-username",
    password="your-password",
    url="https://dav.jianguoyun.com/dav/",
    service_type="nutstore"
)
webdav_service.add_client("cloud", credentials)

# 创建备份管理器
backup_manager = create_backup_manager(
    webdav_service=webdav_service,
    metadata_db_path="/path/to/backup_metadata.db"
)

# 创建恢复服务
recovery_service = create_recovery_service(backup_manager.backup_service)
```

### 3. 配置备份任务

```python
from services.backup_service import BackupConfig

# 创建备份配置
config = BackupConfig(
    name="重要文档",
    source_paths=["/path/to/documents", "/path/to/projects"],
    target_client_id="cloud",
    target_path="/backups",
    include_patterns=["*.txt", "*.pdf", "*.docx"],
    exclude_patterns=["*.tmp", "*.log"],
    encrypt=True,
    encrypt_key="your-secret-key",
    compression=True,
    incremental=True,
    max_versions=30,
    schedule_time="02:00",  # 每天凌晨2点
    auto_delete_old=True
)

# 添加配置
backup_manager.add_config(config)
```

## 💼 使用指南

### 备份管理

#### 手动备份

```python
# 执行全量备份
backup_id = backup_manager.manual_backup("重要文档", backup_type="full")
print(f"备份完成: {backup_id}")

# 执行增量备份
backup_id = backup_manager.manual_backup("重要文档", backup_type="incremental")
print(f"增量备份完成: {backup_id}")
```

#### 自动定时备份

```python
# 启动调度器
backup_manager.start_scheduler()

# 调度器将自动执行定时备份
# 使用 Ctrl+C 停止
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    backup_manager.stop_scheduler()
```

#### 备份验证

```python
# 验证单个备份
result = backup_manager.validate_backup(backup_id)

if result.is_valid:
    print(f"✅ 备份验证通过: {result.files_passed}/{result.files_checked} 文件")
else:
    print(f"❌ 备份验证失败:")
    for error in result.errors:
        print(f"  - {error}")

# 验证所有备份
results = backup_manager.validate_all_backups("重要文档")
for result in results:
    status = "✅" if result.is_valid else "❌"
    print(f"{status} {result.backup_id}: {result.files_passed}/{result.files_checked}")
```

#### 存储空间管理

```python
# 获取存储使用情况
usage = backup_manager.get_storage_usage()

print(f"总备份数: {usage.total_backups}")
print(f"总大小: {usage.total_size / (1024**3):.2f} GB")
print(f"最旧备份: {usage.oldest_backup}")
print(f"最新备份: {usage.newest_backup}")

# 按配置查看
for config_name, info in usage.by_config.items():
    print(f"\n配置: {config_name}")
    print(f"  备份数: {info['count']}")
    print(f"  总大小: {info['total_size'] / (1024**2):.2f} MB")
    print(f"  全量: {info['backup_types']['full']}, 增量: {info['backup_types']['incremental']}")

# 估算空间需求
estimate = backup_manager.estimate_space("重要文档")
print(f"\n源文件大小: {estimate['source_size'] / (1024**2):.2f} MB")
print(f"估算全量备份: {estimate['estimated_full_backup_size'] / (1024**2):.2f} MB")
print(f"估算增量备份: {estimate['estimated_incremental_size'] / (1024**2):.2f} MB")

# 清理旧备份
deleted = backup_manager.cleanup_old_backups(
    config_name="重要文档",
    keep_count=10,      # 保留最新10个
    keep_days=90        # 或保留90天内的
)
print(f"清理了 {deleted} 个旧备份")
```

### 数据恢复

#### 一键恢复

```python
# 恢复到最新状态
session_id = recovery_service.one_click_restore(
    config_name="重要文档",
    target_path="/path/to/restore"
)

# 监控恢复进度
while True:
    progress = recovery_service.get_recovery_progress(session_id)
    if progress:
        print(f"进度: {progress.processed_files}/{progress.total_files} 文件, "
              f"{progress.processed_size / (1024**2):.2f} MB, "
              f"状态: {progress.status.value}")
        
        if progress.status.value in ["completed", "failed"]:
            break
    
    time.sleep(2)

# 恢复到指定时间点
from datetime import datetime, timedelta

target_time = datetime.now() - timedelta(days=7)  # 7天前
session_id = recovery_service.one_click_restore(
    config_name="重要文档",
    target_path="/path/to/restore",
    point_in_time=target_time
)
```

#### 查看恢复点

```python
# 列出所有恢复点
recovery_points = recovery_service.list_recovery_points("重要文档")

print(f"可用恢复点: {len(recovery_points)} 个\n")
for point in recovery_points[:10]:  # 显示最新的10个
    print(f"备份 ID: {point.backup_id}")
    print(f"  时间: {point.created_at}")
    print(f"  类型: {point.backup_type}")
    print(f"  大小: {point.total_size / (1024**2):.2f} MB")
    print(f"  文件数: {point.file_count}")
    print()

# 查找特定时间点的备份
target_time = datetime(2025, 10, 15, 12, 0, 0)
point = recovery_service.find_point_in_time("重要文档", target_time)
if point:
    print(f"找到最接近的恢复点: {point.backup_id} at {point.created_at}")
```

#### 选择性恢复

```python
# 仅恢复特定文件
session_id = recovery_service.selective_restore(
    backup_id="重要文档_20251031_020000",
    target_path="/path/to/restore",
    file_patterns=[
        "*.pdf",                    # 所有PDF文件
        "projects/project1/*",      # project1目录下的所有文件
        "important_document.txt"    # 特定文件
    ]
)

# 监控进度
progress = recovery_service.get_recovery_progress(session_id)
print(f"恢复 {len(file_patterns)} 个模式匹配的文件")
```

### 灾难恢复

#### 创建灾难恢复计划

```python
# 创建DR计划
dr_plan_id = recovery_service.create_disaster_recovery_plan(
    name="主站灾难恢复",
    description="完整的主站数据恢复",
    recovery_order=[
        "数据库备份",      # 第一步：恢复数据库
        "应用程序代码",    # 第二步：恢复代码
        "用户上传文件",    # 第三步：恢复用户文件
        "配置文件"         # 第四步：恢复配置
    ],
    target_base_path="/disaster_recovery",
    auto_verify=True,
    notification_email="admin@example.com"
)

print(f"灾难恢复计划已创建: {dr_plan_id}")
```

#### 测试灾难恢复计划

```python
# 定期测试DR计划
test_result = recovery_service.test_disaster_recovery_plan(dr_plan_id)

print("DR计划测试结果:")
print(f"测试时间: {test_result['tested_at']}")

for config_name, result in test_result['config_tests'].items():
    status = "✅" if result['has_backups'] else "❌"
    print(f"{status} {config_name}:")
    print(f"  备份数: {result['backup_count']}")
    print(f"  最新备份: {result['latest_backup']}")
```

#### 执行灾难恢复

```python
# 执行DR计划
print("⚠️  开始执行灾难恢复计划...")
sessions = recovery_service.execute_disaster_recovery(dr_plan_id)

print(f"已启动 {len(sessions)} 个恢复任务:")
for config_name, session_id in sessions.items():
    print(f"  - {config_name}: {session_id}")

# 监控所有恢复任务
all_completed = False
while not all_completed:
    all_completed = True
    
    for config_name, session_id in sessions.items():
        progress = recovery_service.get_recovery_progress(session_id)
        if progress:
            print(f"{config_name}: {progress.status.value} - "
                  f"{progress.processed_files}/{progress.total_files}")
            
            if progress.status.value not in ["completed", "failed"]:
                all_completed = False
    
    if not all_completed:
        time.sleep(5)
        print("─" * 50)

print("\n✅ 灾难恢复完成!")
```

### 统计和监控

```python
# 获取综合统计
stats = backup_manager.get_statistics("重要文档")

print("备份统计:")
print(f"  总备份数: {stats['backup_stats']['total_backups']}")
print(f"  总大小: {stats['backup_stats']['total_size'] / (1024**3):.2f} GB")
print(f"  最后备份: {stats['backup_stats']['last_backup']}")

print("\n备份类型分布:")
for backup_type, count in stats['backup_stats']['backup_types'].items():
    print(f"  {backup_type}: {count}")

print("\n存储趋势:")
for trend in stats['storage_usage']['storage_trend'][-6:]:  # 最近6个月
    print(f"  {trend['month']}: {trend['count']} 个备份, "
          f"{trend['size'] / (1024**2):.2f} MB")

# 列出所有配置
configs = backup_manager.list_configs()
print(f"\n配置的备份任务: {', '.join(configs)}")

# 查看备份列表
backups = backup_manager.list_backups("重要文档")
print(f"\n最近的备份:")
for backup in backups[:5]:
    print(f"  {backup.backup_id}: {backup.created_at} - {backup.backup_type}")
```

## 📊 API 参考

### BackupManager

#### 配置管理
- `add_config(config: BackupConfig) -> bool`: 添加备份配置
- `remove_config(config_name: str) -> bool`: 移除配置
- `get_config(config_name: str) -> Optional[BackupConfig]`: 获取配置
- `list_configs() -> List[str]`: 列出所有配置

#### 备份操作
- `manual_backup(config_name: str, backup_type: str) -> str`: 手动触发备份
- `start_scheduler()`: 启动自动调度
- `stop_scheduler()`: 停止自动调度

#### 验证
- `validate_backup(backup_id: str) -> BackupValidationResult`: 验证备份
- `validate_all_backups(config_name: str) -> List[BackupValidationResult]`: 验证所有备份

#### 存储管理
- `get_storage_usage() -> StorageUsage`: 获取存储使用情况
- `cleanup_old_backups(config_name, keep_count, keep_days) -> int`: 清理旧备份
- `estimate_space(config_name: str) -> Dict`: 估算空间需求

#### 查询
- `list_backups(config_name: str) -> List[BackupManifest]`: 列出备份
- `get_backup_manifest(backup_id: str) -> Optional[BackupManifest]`: 获取备份清单
- `get_statistics(config_name: str) -> Dict`: 获取统计信息

### RecoveryService

#### 恢复点管理
- `list_recovery_points(config_name: str, days: int) -> List[RecoveryPoint]`: 列出恢复点
- `get_recovery_point(backup_id: str) -> Optional[RecoveryPoint]`: 获取恢复点
- `find_point_in_time(config_name, target_time) -> Optional[RecoveryPoint]`: 查找时间点

#### 恢复操作
- `one_click_restore(config_name, target_path, point_in_time) -> str`: 一键恢复
- `selective_restore(backup_id, target_path, file_patterns) -> str`: 选择性恢复
- `get_recovery_progress(session_id: str) -> Optional[RecoveryProgress]`: 获取进度
- `cancel_recovery(session_id: str) -> bool`: 取消恢复

#### 灾难恢复
- `create_disaster_recovery_plan(name, recovery_order, target_base_path) -> str`: 创建DR计划
- `execute_disaster_recovery(plan_id: str) -> Dict[str, str]`: 执行DR计划
- `test_disaster_recovery_plan(plan_id: str) -> Dict`: 测试DR计划
- `list_disaster_recovery_plans() -> List[DisasterRecoveryPlan]`: 列出DR计划

## 🔐 安全最佳实践

### 1. 加密配置

```python
config = BackupConfig(
    name="敏感数据",
    source_paths=["/path/to/sensitive"],
    target_client_id="cloud",
    target_path="/secure_backups",
    encrypt=True,
    encrypt_key="use-a-strong-key-here",  # 使用强密钥
    # ...
)
```

**密钥管理建议:**
- 使用环境变量或密钥管理服务存储密钥
- 定期轮换加密密钥
- 不要在代码中硬编码密钥

### 2. 访问控制

```python
# 使用应用专用密码，不要使用账户主密码
credentials = WebDAVCredentials(
    username="backup-service",
    password=os.environ.get("WEBDAV_APP_PASSWORD"),
    url="https://dav.jianguoyun.com/dav/",
    service_type="nutstore"
)
```

### 3. 备份验证

```python
# 定期验证备份完整性
def daily_verification():
    backups = backup_manager.list_backups()
    recent_backups = [b for b in backups 
                      if (datetime.now() - b.created_at).days <= 7]
    
    for backup in recent_backups:
        result = backup_manager.validate_backup(backup.backup_id)
        if not result.is_valid:
            send_alert(f"备份验证失败: {backup.backup_id}")
```

### 4. 网络安全

- 始终使用 HTTPS 连接 WebDAV 服务器
- 启用 SSL 证书验证
- 考虑使用 VPN 或专用网络

## 📈 监控和告警

### 监控指标

```python
def monitor_backup_health():
    """监控备份系统健康状态"""
    
    stats = backup_manager.get_statistics()
    
    # 检查最近备份
    last_backup_time = datetime.fromisoformat(stats['backup_stats']['last_backup'])
    hours_since_backup = (datetime.now() - last_backup_time).total_seconds() / 3600
    
    if hours_since_backup > 48:
        alert("警告: 超过48小时没有新备份")
    
    # 检查存储空间
    usage = backup_manager.get_storage_usage()
    if usage.total_size > 100 * 1024**3:  # 100GB
        alert("警告: 备份存储空间超过100GB")
    
    # 检查失败的备份
    validation_results = backup_manager.validate_all_backups()
    failed_count = sum(1 for r in validation_results if not r.is_valid)
    
    if failed_count > 0:
        alert(f"警告: {failed_count} 个备份验证失败")
```

### 自动化任务

```python
import schedule

# 每天凌晨2点执行全量备份
schedule.every().day.at("02:00").do(
    lambda: backup_manager.manual_backup("重要文档", "full")
)

# 每6小时执行增量备份
schedule.every(6).hours.do(
    lambda: backup_manager.manual_backup("重要文档", "incremental")
)

# 每天检查备份健康状态
schedule.every().day.at("09:00").do(monitor_backup_health)

# 每周日清理旧备份
schedule.every().sunday.at("03:00").do(
    lambda: backup_manager.cleanup_old_backups("重要文档", keep_count=30)
)

# 每月测试灾难恢复计划
schedule.every().month.at("00:00").do(
    lambda: recovery_service.test_disaster_recovery_plan(dr_plan_id)
)
```

## 🐛 故障排除

### 常见问题

#### 1. 备份失败

```
BackupExecutionError: 备份执行失败
```

**解决方案:**
- 检查 WebDAV 连接是否正常
- 验证源路径是否存在且有读取权限
- 检查目标存储空间是否充足
- 查看日志获取详细错误信息

#### 2. 验证失败

```
文件大小不匹配或文件不存在
```

**解决方案:**
- 检查网络连接稳定性
- 确认 WebDAV 服务器文件没有被手动修改
- 重新执行备份
- 考虑增加重试机制

#### 3. 恢复缓慢

**优化方案:**
- 使用选择性恢复而不是完全恢复
- 检查网络带宽
- 考虑使用本地缓存
- 并行恢复多个文件

#### 4. 存储空间不足

**解决方案:**
```python
# 清理旧备份
backup_manager.cleanup_old_backups("重要文档", keep_days=30)

# 减少备份频率
# 或增加存储空间
```

### 调试模式

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_debug.log'),
        logging.StreamHandler()
    ]
)
```

## 📝 示例脚本

### 完整的备份脚本

```python
#!/usr/bin/env python3
"""完整的备份脚本示例"""

import logging
from datetime import datetime
from services.webdav_service import WebDAVService, WebDAVCredentials
from services.backup_manager import create_backup_manager
from services.backup_service import BackupConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)

def main():
    # 初始化服务
    webdav_service = WebDAVService()
    credentials = WebDAVCredentials(
        username="your-username",
        password="your-password",
        url="https://dav.jianguoyun.com/dav/",
        service_type="nutstore"
    )
    webdav_service.add_client("cloud", credentials)
    
    manager = create_backup_manager(webdav_service, "backup_metadata.db")
    
    # 配置备份
    config = BackupConfig(
        name="daily_backup",
        source_paths=["/data"],
        target_client_id="cloud",
        target_path="/backups",
        encrypt=True,
        compression=True,
        incremental=True,
        max_versions=30
    )
    manager.add_config(config)
    
    # 执行备份
    try:
        backup_id = manager.manual_backup("daily_backup", "incremental")
        logging.info(f"备份成功: {backup_id}")
        
        # 验证备份
        result = manager.validate_backup(backup_id)
        if result.is_valid:
            logging.info("备份验证通过")
        else:
            logging.error(f"备份验证失败: {result.errors}")
        
        # 清理旧备份
        deleted = manager.cleanup_old_backups("daily_backup", keep_count=30)
        logging.info(f"清理了 {deleted} 个旧备份")
        
    except Exception as e:
        logging.error(f"备份失败: {e}")
        raise

if __name__ == "__main__":
    main()
```

### 灾难恢复脚本

```python
#!/usr/bin/env python3
"""灾难恢复脚本示例"""

import logging
import time
from services.backup_manager import create_backup_manager
from services.recovery_service import create_recovery_service
from services.webdav_service import WebDAVService, WebDAVCredentials

logging.basicConfig(level=logging.INFO)

def main():
    # 初始化服务
    webdav_service = WebDAVService()
    credentials = WebDAVCredentials(
        username="your-username",
        password="your-password",
        url="https://dav.jianguoyun.com/dav/",
        service_type="nutstore"
    )
    webdav_service.add_client("cloud", credentials)
    
    manager = create_backup_manager(webdav_service, "backup_metadata.db")
    recovery = create_recovery_service(manager.backup_service)
    
    # 创建灾难恢复计划
    dr_plan_id = recovery.create_disaster_recovery_plan(
        name="Production DR",
        recovery_order=["database", "application", "uploads"],
        target_base_path="/recovery"
    )
    
    # 测试计划
    test_result = recovery.test_disaster_recovery_plan(dr_plan_id)
    print(f"DR测试结果: {test_result}")
    
    # 确认后执行
    if input("执行灾难恢复? (yes/no): ").lower() == "yes":
        sessions = recovery.execute_disaster_recovery(dr_plan_id)
        
        # 监控进度
        while True:
            all_done = True
            for config_name, session_id in sessions.items():
                progress = recovery.get_recovery_progress(session_id)
                if progress and progress.status.value not in ["completed", "failed"]:
                    all_done = False
                    print(f"{config_name}: {progress.status.value}")
            
            if all_done:
                break
            time.sleep(5)
        
        print("灾难恢复完成!")

if __name__ == "__main__":
    main()
```

## 🎯 性能优化建议

1. **增量备份优先**: 日常使用增量备份，减少传输量
2. **合理设置备份频率**: 根据数据变化频率调整
3. **启用压缩**: 对文本文件启用压缩可节省 40-60% 空间
4. **并行操作**: 对于多个配置，可以并行执行备份
5. **网络优化**: 使用稳定高速的网络连接
6. **定期清理**: 自动清理超过保留期的旧备份

## 📄 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请查看文档或提交 Issue。
