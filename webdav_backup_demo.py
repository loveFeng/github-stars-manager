#!/usr/bin/env python3
"""
WebDAV 备份服务使用示例
演示如何使用 WebDAV 备份服务进行数据备份和恢复
"""

import os
import sys
import logging
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import (
    WebDAVService,
    WebDAVCredentials,
    BackupService,
    BackupConfig,
    create_webdav_client,
    create_backup_service,
    SAMPLE_BACKUP_CONFIG
)


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('webdav_backup.log', encoding='utf-8')
        ]
    )


def demo_webdav_client():
    """演示 WebDAV 客户端功能"""
    print("\\n=== WebDAV 客户端演示 ===")
    
    # 创建 WebDAV 客户端
    try:
        # 以坚果云为例（需要替换为真实凭据）
        client = create_webdav_client(
            service_type="nutstore",
            url="https://dav.jianguoyun.com/dav/",
            username="your-username",
            password="your-password"
        )
        
        print("✅ WebDAV 客户端创建成功")
        
        # 测试连接
        try:
            client._test_connection()
            print("✅ WebDAV 连接测试成功")
        except Exception as e:
            print(f"❌ WebDAV 连接测试失败: {e}")
            print("（这是正常的，如果没有真实凭据）")
            return None
        
        # 获取存储空间使用情况
        try:
            space_info = client.get_space_usage()
            print(f"存储空间信息: {space_info}")
        except Exception as e:
            print(f"获取存储空间信息失败: {e}")
        
        return client
    
    except Exception as e:
        print(f"❌ WebDAV 客户端创建失败: {e}")
        return None


def demo_backup_service(webdav_service):
    """演示备份服务功能"""
    print("\\n=== 备份服务演示 ===")
    
    if not webdav_service:
        print("❌ WebDAV 服务未初始化，跳过备份演示")
        return
    
    try:
        # 创建备份服务
        backup_service = create_backup_service(
            webdav_service=webdav_service,
            metadata_db_path="backup_metadata.db"
        )
        print("✅ 备份服务创建成功")
        
        # 添加 WebDAV 客户端
        try:
            webdav_service.add_client("demo_client", WebDAVCredentials(
                username="demo",
                password="demo",
                url="https://demo.example.com/dav/",
                service_type="custom"
            ))
            print("✅ 添加 WebDAV 客户端成功")
        except Exception as e:
            print(f"⚠️ 添加 WebDAV 客户端失败: {e}")
        
        # 配置备份任务
        backup_config = BackupConfig(
            name="示例文档备份",
            source_paths=["./demo_files"],  # 演示目录
            target_client_id="demo_client",
            target_path="/backups",
            include_patterns=["*.txt", "*.pdf", "*.doc*"],
            exclude_patterns=["*.tmp", "*.log", "__pycache__/*"],
            encrypt=True,
            encryption_key="demo-encryption-key-123",
            compression=True,
            incremental=True,
            max_versions=10,
            schedule_time="02:00",
            conflict_resolution="timestamp",
            auto_delete_old=True
        )
        
        # 添加备份配置
        try:
            backup_service.add_config(backup_config)
            print("✅ 备份配置添加成功")
        except Exception as e:
            print(f"❌ 备份配置添加失败: {e}")
            return backup_service
        
        # 创建演示文件
        create_demo_files()
        
        # 执行备份（仅演示，实际执行需要真实 WebDAV 连接）
        try:
            print("\\n准备执行备份...")
            backup_id = backup_service.execute_backup("示例文档备份", "full")
            print(f"✅ 备份执行成功，备份 ID: {backup_id}")
        except Exception as e:
            print(f"⚠️ 备份执行失败（预期，因为没有真实 WebDAV 连接）: {e}")
        
        # 列出备份
        try:
            backups = backup_service.list_backups("示例文档备份")
            print(f"📋 备份列表（{len(backups)} 个备份）")
            for backup in backups[:3]:  # 显示前3个
                print(f"  - {backup.backup_id} ({backup.backup_type}) - {backup.created_at}")
        except Exception as e:
            print(f"⚠️ 列出备份失败: {e}")
        
        # 获取备份统计
        try:
            stats = backup_service.get_backup_statistics("示例文档备份")
            print(f"📊 备份统计: {stats}")
        except Exception as e:
            print(f"⚠️ 获取备份统计失败: {e}")
        
        # 演示调度功能
        try:
            print("\\n⏰ 启动备份调度器...")
            backup_service.start_scheduler()
            print("✅ 备份调度器已启动（将在后台运行）")
            
            # 运行一小段时间
            time.sleep(2)
            
            backup_service.stop_scheduler()
            print("🛑 备份调度器已停止")
        except Exception as e:
            print(f"⚠️ 调度器演示失败: {e}")
        
        return backup_service
    
    except Exception as e:
        print(f"❌ 备份服务创建失败: {e}")
        return None


def create_demo_files():
    """创建演示文件"""
    demo_dir = Path("demo_files")
    demo_dir.mkdir(exist_ok=True)
    
    # 创建各种类型的演示文件
    files_to_create = [
        ("readme.txt", "这是一个演示文件\\n包含中文内容用于测试备份功能。"),
        ("document.pdf", "%PDF-1.4 演示PDF内容（实际使用中应替换为真实PDF）"),
        ("data.json", '{"name": "演示数据", "items": ["项目1", "项目2", "项目3"]}'),
        ("config.ini", "[section1]\\nkey1=value1\\nkey2=value2"),
        ("temp.tmp", "临时文件内容（应该被排除）"),
        ("log.log", "日志文件内容（应该被排除）")
    ]
    
    for filename, content in files_to_create:
        file_path = demo_dir / filename
        file_path.write_text(content, encoding='utf-8')
    
    # 创建子目录
    subdir = demo_dir / "subdir"
    subdir.mkdir(exist_ok=True)
    (subdir / "nested.txt").write_text("嵌套文件内容", encoding='utf-8')
    
    print(f"✅ 创建演示文件目录: {demo_dir}")


def demo_restore_functionality(backup_service):
    """演示恢复功能"""
    print("\\n=== 恢复功能演示 ===")
    
    if not backup_service:
        print("❌ 备份服务未初始化，跳过恢复演示")
        return
    
    try:
        # 模拟恢复操作
        print("📥 准备恢复演示...")
        
        # 这里展示恢复会话的概念
        # 实际使用中需要先有备份才能恢复
        
        print("✅ 恢复功能已准备就绪")
        print("💡 恢复功能使用方法:")
        print("   1. 获取备份 ID")
        print("   2. 调用 backup_service.restore_backup(backup_id, target_path)")
        print("   3. 监控恢复进度: backup_service.get_restore_session(session_id)")
    
    except Exception as e:
        print(f"⚠️ 恢复演示失败: {e}")


def demo_conflict_resolution():
    """演示冲突解决机制"""
    print("\\n=== 冲突解决演示 ===")
    
    try:
        from services.backup_service import ConflictResolver, BackupFileInfo
        from datetime import datetime
        
        resolver = ConflictResolver("timestamp")
        
        # 模拟冲突场景
        local_file = BackupFileInfo(
            path="document.txt",
            size=1024,
            modified_time=datetime(2024, 1, 1, 10, 0, 0),
            checksum="abc123"
        )
        
        remote_file = BackupFileInfo(
            path="document.txt", 
            size=2048,
            modified_time=datetime(2024, 1, 1, 12, 0, 0),
            checksum="def456"
        )
        
        resolution = resolver.resolve_conflict(None, None, local_file, remote_file)
        print(f"🔄 冲突解决策略: {resolution}")
        print(f"   本地文件修改时间: {local_file.modified_time}")
        print(f"   远程文件修改时间: {remote_file.modified_time}")
        print("   选择较新的文件（远程）")
        
    except Exception as e:
        print(f"⚠️ 冲突解决演示失败: {e}")


def demo_encryption():
    """演示加密功能"""
    print("\\n=== 加密功能演示 ===")
    
    try:
        from services.backup_service import EncryptionManager
        
        # 创建加密管理器
        encryption_manager = EncryptionManager("demo-encryption-key")
        
        # 演示加密和解密
        original_data = "这是一个需要加密的敏感数据！"
        original_bytes = original_data.encode('utf-8')
        
        print(f"原始数据: {original_data}")
        
        # 加密
        encrypted_data = encryption_manager.encrypt_data(original_bytes)
        print(f"加密后数据长度: {len(encrypted_data)} 字节")
        
        # 解密
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        decrypted_text = decrypted_data.decode('utf-8')
        
        print(f"解密后数据: {decrypted_text}")
        
        if decrypted_text == original_data:
            print("✅ 加密/解密验证成功")
        else:
            print("❌ 加密/解密验证失败")
    
    except Exception as e:
        print(f"⚠️ 加密演示失败: {e}")


def cleanup_demo_files():
    """清理演示文件"""
    demo_dir = Path("demo_files")
    backup_db = Path("backup_metadata.db")
    
    if demo_dir.exists():
        import shutil
        shutil.rmtree(demo_dir)
        print(f"🗑️ 清理演示文件目录: {demo_dir}")
    
    if backup_db.exists():
        backup_db.unlink()
        print(f"🗑️ 清理备份数据库: {backup_db}")


def main():
    """主函数"""
    print("🚀 WebDAV 备份服务演示程序")
    print("=" * 50)
    
    # 设置日志
    setup_logging()
    
    try:
        # 演示 WebDAV 客户端
        webdav_service = demo_webdav_client()
        
        # 演示备份服务
        backup_service = demo_backup_service(webdav_service)
        
        # 演示恢复功能
        demo_restore_functionality(backup_service)
        
        # 演示冲突解决
        demo_conflict_resolution()
        
        # 演示加密功能
        demo_encryption()
        
        print("\\n🎉 演示程序执行完成！")
        print("\\n📖 使用说明:")
        print("1. 配置真实的 WebDAV 服务凭据")
        print("2. 根据需要调整备份配置")
        print("3. 运行备份任务并监控进度")
        print("4. 必要时执行数据恢复")
        
    except KeyboardInterrupt:
        print("\\n\\n⚠️ 程序被用户中断")
    except Exception as e:
        print(f"\\n\\n❌ 程序执行出错: {e}")
        logging.exception("程序执行异常")
    finally:
        # 清理演示文件
        try:
            cleanup_demo_files()
        except Exception as e:
            print(f"清理演示文件失败: {e}")


if __name__ == "__main__":
    main()