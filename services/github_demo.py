#!/usr/bin/env python3
"""
GitHub API 集成服务使用示例

展示如何使用 GitHubStarsManager 的 GitHub API 集成服务
实现星标仓库管理、发布跟踪、AI 摘要等功能
"""

import os
import sys
import json
from datetime import datetime
from typing import List

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import (
    GitHubService,
    GitHubAPIClient,
    AIConfig,
    CacheManager,
    AssetFilter,
    RateLimitExceededError,
    AuthenticationError,
    GitHubAPIError
)


def demo_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("GitHub API 集成服务 - 基本使用示例")
    print("=" * 60)
    
    # 获取 GitHub token (从环境变量或用户输入)
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        token = input("请输入 GitHub Personal Access Token: ").strip()
        if not token:
            print("❌ 未提供 GitHub token，示例终止")
            return
    
    # 配置 AI 服务 (可选)
    ai_config = None
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        ai_config = AIConfig(
            id="openai",
            name="OpenAI",
            api_url="https://api.openai.com/v1/chat/completions",
            api_key=openai_key,
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7
        )
        print("✅ AI 服务已配置")
    else:
        print("ℹ️  未配置 AI 服务，将跳过 AI 功能")
    
    # 初始化服务
    try:
        github_service = GitHubService(
            token=token,
            ai_config=ai_config
        )
        print("✅ GitHub 服务初始化成功")
        
        # 认证测试
        user = github_service.authenticate()
        print(f"✅ 认证成功: {user.login} ({user.name})")
        print(f"   头像: {user.avatar_url}")
        print(f"   简介: {user.bio or '无'}")
        
    except AuthenticationError as e:
        print(f"❌ GitHub 认证失败: {e}")
        return
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    return github_service


def demo_sync_repos(github_service: GitHubService):
    """同步星标仓库示例"""
    print("\n" + "=" * 60)
    print("星标仓库同步示例")
    print("=" * 60)
    
    try:
        # 同步星标仓库
        print("🔄 开始同步星标仓库...")
        sync_result = github_service.sync_starred_repos()
        
        if sync_result.success:
            print(f"✅ 同步成功!")
            print(f"   总仓库数: {sync_result.total_repos}")
            print(f"   成功同步: {sync_result.synced_repos}")
            print(f"   同步失败: {sync_result.failed_repos}")
            print(f"   开始时间: {sync_result.start_time}")
            print(f"   结束时间: {sync_result.end_time}")
            
            if sync_result.errors:
                print(f"   错误列表:")
                for error in sync_result.errors:
                    print(f"     - {error}")
        else:
            print(f"❌ 同步失败: {sync_result.errors}")
            
    except RateLimitExceededError as e:
        print(f"❌ 速率限制已用尽: {e}")
        print(f"   重置时间: {e.rate_limit_info.reset}")
        
    except Exception as e:
        print(f"❌ 同步过程中出错: {e}")


def demo_search_and_filter(github_service: GitHubService):
    """搜索和过滤示例"""
    print("\n" + "=" * 60)
    print("仓库搜索和过滤示例")
    print("=" * 60)
    
    # 这里模拟从同步结果获取的仓库数据
    # 实际使用时应该从 sync_starred_repos() 返回的数据中获取
    print("📝 注意: 此示例需要先运行 sync_starred_repos() 获取真实数据")
    print("   实际的搜索和过滤功能演示需要真实的仓库数据")
    
    # 模拟搜索功能
    print("\n🔍 搜索功能示例:")
    print("   github_service.search_repos(repos, query='Python')")
    print("   github_service.search_repos(repos, language='JavaScript')")
    print("   github_service.search_repos(repos, topic='machine-learning')")


def demo_ai_features(github_service: GitHubService):
    """AI 功能示例"""
    print("\n" + "=" * 60)
    print("AI 功能示例")
    print("=" * 60)
    
    if not github_service.ai_service.config:
        print("ℹ️  未配置 AI 服务，跳过 AI 功能演示")
        return
    
    print("🤖 AI 功能示例:")
    print("   - 生成仓库摘要")
    print("   - 生成仓库标签")
    print("   - 批量处理")
    print("\n📝 注意: 实际使用需要真实的仓库数据")


def demo_release_tracking(github_service: GitHubService):
    """发布跟踪示例"""
    print("\n" + "=" * 60)
    print("发布跟踪示例")
    print("=" * 60)
    
    # 订阅一些知名仓库作为示例
    sample_repos = [
        ("microsoft", "vscode"),
        ("facebook", "react"),
        ("vuejs", "vue"),
        ("tensorflow", "tensorflow")
    ]
    
    print("📡 订阅示例仓库...")
    for owner, repo_name in sample_repos:
        success = github_service.subscribe_repo(owner, repo_name)
        status = "✅" if success else "❌"
        print(f"   {status} {owner}/{repo_name}")
    
    # 检查发布更新
    print("\n🔍 检查发布更新...")
    try:
        updates = github_service.check_release_updates()
        
        if updates.get("success"):
            print(f"✅ 检查完成")
            print(f"   订阅仓库数: {updates.get('total_subscribed', 0)}")
            
            update_list = updates.get("updates", [])
            if update_list:
                print(f"   发现 {len(update_list)} 个新发布:")
                for update in update_list[:5]:  # 只显示前5个
                    repo_name = update.get("repo_full_name")
                    print(f"     - {repo_name}")
            else:
                print("   没有发现新发布")
        else:
            print("❌ 检查发布更新失败")
            
    except Exception as e:
        print(f"❌ 检查过程中出错: {e}")


def demo_asset_filtering(github_service: GitHubService):
    """资产过滤示例"""
    print("\n" + "=" * 60)
    print("发布资产过滤示例")
    print("=" * 60)
    
    # 创建一些示例过滤器
    print("🛠️  创建资产过滤器...")
    
    # Windows 过滤器
    filter1 = github_service.add_asset_filter(
        "Windows 安装包",
        ["exe", "msi", "win32", "win64"]
    )
    print(f"   ✅ {filter1.name}: {filter1.keywords}")
    
    # macOS 过滤器
    filter2 = github_service.add_asset_filter(
        "macOS 安装包", 
        ["dmg", "pkg", "mac", "osx"]
    )
    print(f"   ✅ {filter2.name}: {filter2.keywords}")
    
    # Linux 过滤器
    filter3 = github_service.add_asset_filter(
        "Linux 安装包",
        ["deb", "rpm", "AppImage", "linux"]
    )
    print(f"   ✅ {filter3.name}: {filter3.keywords}")
    
    print("\n🔍 获取仓库资产示例:")
    print("   assets = github_service.get_repo_assets('microsoft', 'vscode')")
    print("   # 自动检测平台关键词并匹配过滤器")


def demo_statistics(github_service: GitHubService):
    """统计信息示例"""
    print("\n" + "=" * 60)
    print("统计信息示例")
    print("=" * 60)
    
    print("📊 统计功能示例:")
    print("   - 编程语言分布")
    print("   - 主题标签统计")
    print("   - 分类统计")
    print("   - 仓库规模分析")
    
    print("\n📝 注意: 需要真实的仓库数据才能生成统计信息")


def demo_rate_limit_monitoring(github_service: GitHubService):
    """速率限制监控示例"""
    print("\n" + "=" * 60)
    print("API 速率限制监控")
    print("=" * 60)
    
    try:
        rate_status = github_service.get_rate_limit_status()
        
        if "error" not in rate_status:
            print(f"✅ API 速率限制状态:")
            print(f"   限制: {rate_status['limit']}")
            print(f"   剩余: {rate_status['remaining']}")
            print(f"   已用: {rate_status['used']}")
            print(f"   使用率: {rate_status['percentage_used']}%")
            print(f"   重置时间: {rate_status['reset_time']}")
            
            if rate_status['remaining'] < 10:
                print("⚠️  API 调用次数接近限制，建议等待或减少调用")
        else:
            print(f"❌ 获取速率限制状态失败: {rate_status['error']}")
            
    except Exception as e:
        print(f"❌ 监控过程中出错: {e}")


def demo_cache_management(github_service: GitHubService):
    """缓存管理示例"""
    print("\n" + "=" * 60)
    print("缓存管理示例")
    print("=" * 60)
    
    print("💾 缓存管理功能:")
    print("   - 自动缓存 API 响应")
    print("   - 智能过期清理")
    print("   - 手动清理缓存")
    
    try:
        cleanup_result = github_service.cleanup_cache()
        print(f"🧹 缓存清理结果:")
        print(f"   清理过期缓存: {cleanup_result['expired_cleaned']} 项")
        print(f"   清理全部缓存: {cleanup_result['total_cleaned']} 项")
        
    except Exception as e:
        print(f"❌ 缓存清理失败: {e}")


def demo_data_export(github_service: GitHubService):
    """数据导出示例"""
    print("\n" + "=" * 60)
    print("数据导出示例")
    print("=" * 60)
    
    print("💾 数据导出功能:")
    print("   - JSON 格式导出")
    print("   - CSV 格式导出")
    print("   - 带时间戳的导出文件名")
    
    print("\n📝 使用示例:")
    print("   filename = github_service.export_data(repos, format='json')")
    print("   filename = github_service.export_data(repos, format='csv')")


def main():
    """主函数"""
    print("GitHubStarsManager - GitHub API 集成服务演示")
    print("基于原项目功能实现的完整 GitHub API 解决方案")
    
    # 基本使用示例
    github_service = demo_basic_usage()
    if not github_service:
        return
    
    # 功能演示
    demo_sync_repos(github_service)
    demo_search_and_filter(github_service)
    demo_ai_features(github_service)
    demo_release_tracking(github_service)
    demo_asset_filtering(github_service)
    demo_statistics(github_service)
    demo_rate_limit_monitoring(github_service)
    demo_cache_management(github_service)
    demo_data_export(github_service)
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n💡 使用提示:")
    print("1. 需要有效的 GitHub Personal Access Token")
    print("2. 建议配置 AI 服务以获得完整功能")
    print("3. 注意 API 速率限制，合理控制调用频率")
    print("4. 定期备份重要数据")
    print("5. 遵循 GitHub API 使用条款")


if __name__ == "__main__":
    main()