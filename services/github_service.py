"""
GitHub API 业务服务层
基于 GitHubStarsManager 功能需求，实现高级业务逻辑
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from github_api import (
    GitHubAPIClient, GitHubAPIBatchClient, GitHubRepository, GitHubRelease,
    GitHubUser, GitHubAPIError, RateLimitExceededError, AuthenticationError,
    NotFoundError, ValidationError
)


logger = logging.getLogger(__name__)


@dataclass
class StarredRepo:
    """星标仓库业务模型"""
    id: int
    name: str
    full_name: str
    description: Optional[str]
    html_url: str
    language: Optional[str]
    stargazers_count: int
    topics: List[str]
    created_at: str
    updated_at: str
    starred_at: str  # 星标时间
    ai_summary: Optional[str] = None
    ai_tags: List[str] = None
    custom_category: Optional[str] = None
    custom_notes: Optional[str] = None
    last_sync_at: Optional[str] = None
    is_archived: bool = False
    is_fork: bool = False
    license: Optional[str] = None


@dataclass
class RepositoryAsset:
    """仓库资产模型"""
    repo_full_name: str
    asset_id: int
    asset_name: str
    size: int
    download_count: int
    created_at: str
    updated_at: str
    download_url: str
    content_type: str
    platform_keywords: List[str]  # 平台关键词
    matched_filters: List[str]  # 匹配的过滤器


@dataclass
class ReleaseUpdate:
    """发布更新模型"""
    repo_full_name: str
    repo_name: str
    latest_release: Optional[Dict[str, Any]]
    new_releases: List[Dict[str, Any]]
    subscribed_at: str
    last_checked_at: str
    is_read: bool = False


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    total_repos: int
    synced_repos: int
    failed_repos: int
    start_time: str
    end_time: str
    errors: List[str]
    rate_limit_info: Optional[Dict[str, Any]] = None


@dataclass
class AIConfig:
    """AI 配置"""
    id: str
    name: str
    api_url: str
    api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    enabled: bool = True


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否过期
                if data.get('expire_at'):
                    expire_time = datetime.fromisoformat(data['expire_at'])
                    if datetime.now() > expire_time:
                        os.remove(cache_path)
                        return None
                
                return data.get('data')
            except Exception as e:
                logger.error(f"读取缓存失败: {e}")
                return None
        return None
    
    def set(self, key: str, data: Any, expire_minutes: int = 60) -> None:
        """设置缓存"""
        cache_path = self._get_cache_path(key)
        cache_data = {
            'data': data,
            'created_at': datetime.now().isoformat(),
            'expire_at': (datetime.now() + timedelta(minutes=expire_minutes)).isoformat()
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"写入缓存失败: {e}")
    
    def clear_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        if not os.path.exists(self.cache_dir):
            return 0
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get('expire_at'):
                        expire_time = datetime.fromisoformat(data['expire_at'])
                        if datetime.now() > expire_time:
                            os.remove(file_path)
                            count += 1
                except Exception:
                    # 删除损坏的缓存文件
                    os.remove(file_path)
                    count += 1
        
        return count
    
    def clear_all(self) -> int:
        """清理所有缓存"""
        count = 0
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        os.remove(file_path)
                        count += 1
                    except Exception as e:
                        logger.error(f"删除缓存文件失败: {e}")
        return count


class AIService:
    """AI 服务"""
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config
        self.cache = CacheManager()
    
    def generate_repo_summary(self, repo: StarredRepo, 
                            force_refresh: bool = False) -> Optional[str]:
        """生成仓库摘要"""
        if not self.config or not self.config.enabled:
            logger.warning("AI 服务未配置或已禁用")
            return None
        
        cache_key = f"summary_{repo.id}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            # 构建提示词
            prompt = self._build_summary_prompt(repo)
            
            # 调用 AI API
            summary = self._call_ai_api(prompt)
            
            if summary:
                self.cache.set(cache_key, summary, expire_minutes=1440)  # 24小时缓存
                return summary
        except Exception as e:
            logger.error(f"生成仓库摘要失败: {e}")
        
        return None
    
    def generate_repo_tags(self, repo: StarredRepo,
                          force_refresh: bool = False) -> List[str]:
        """生成仓库标签"""
        if not self.config or not self.config.enabled:
            return []
        
        cache_key = f"tags_{repo.id}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            # 构建提示词
            prompt = self._build_tags_prompt(repo)
            
            # 调用 AI API
            tags_text = self._call_ai_api(prompt)
            
            if tags_text:
                # 解析标签
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                self.cache.set(cache_key, tags, expire_minutes=1440)
                return tags
        except Exception as e:
            logger.error(f"生成仓库标签失败: {e}")
        
        return []
    
    def _build_summary_prompt(self, repo: StarredRepo) -> str:
        """构建摘要提示词"""
        return f"""
请为以下 GitHub 仓库生成一个简洁的中文摘要（100字以内）：

仓库名称: {repo.name}
描述: {repo.description or '无描述'}
编程语言: {repo.language or '未知'}
标签: {', '.join(repo.topics) if repo.topics else '无'}
星标数: {repo.stargazers_count}

请用简洁的中文描述这个仓库的主要功能、用途和技术特点。
"""
    
    def _build_tags_prompt(self, repo: StarredRepo) -> str:
        """构建标签提示词"""
        return f"""
请为以下 GitHub 仓库生成5-10个相关标签，用英文逗号分隔：

仓库名称: {repo.name}
描述: {repo.description or '无描述'}
编程语言: {repo.language or '未知'}
标签: {', '.join(repo.topics) if repo.topics else '无'}

请基于仓库的功能、用途和技术栈生成相关标签。
只返回标签，用英文逗号分隔。
"""
    
    def _call_ai_api(self, prompt: str) -> Optional[str]:
        """调用 AI API"""
        if not self.config:
            return None
        
        try:
            import requests
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}" if self.config.api_key else ""
            }
            
            data = {
                "model": self.config.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
            
            response = requests.post(
                self.config.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content')
            else:
                logger.error(f"AI API 调用失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"AI API 调用异常: {e}")
            return None


class AssetFilter:
    """资产过滤器"""
    
    def __init__(self, name: str, keywords: List[str], is_active: bool = True):
        self.name = name
        self.keywords = keywords
        self.is_active = is_active
    
    def matches(self, asset: RepositoryAsset) -> bool:
        """检查资产是否匹配过滤器"""
        if not self.is_active:
            return False
        
        # 检查文件名是否包含关键词
        asset_name_lower = asset.asset_name.lower()
        for keyword in self.keywords:
            if keyword.lower() in asset_name_lower:
                return True
        return False


class CategoryManager:
    """分类管理器"""
    
    def __init__(self):
        self.custom_categories: Set[str] = set()
        self.default_categories = [
            "Web开发", "移动开发", "桌面应用", "数据分析", 
            "机器学习", "工具库", "框架", "基础设施",
            "文档工具", "测试工具", "部署工具", "其他"
        ]
    
    def add_category(self, category: str) -> None:
        """添加自定义分类"""
        if category not in self.custom_categories:
            self.custom_categories.add(category)
    
    def remove_category(self, category: str) -> None:
        """删除自定义分类"""
        self.custom_categories.discard(category)
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self.default_categories) + list(self.custom_categories)
    
    def assign_category(self, repo: StarredRepo, category: str) -> None:
        """为仓库分配分类"""
        repo.custom_category = category
        if category not in self.default_categories and category not in self.custom_categories:
            self.add_category(category)


class GitHubService:
    """GitHub 业务服务"""
    
    def __init__(self, token: Optional[str] = None, 
                 ai_config: Optional[AIConfig] = None):
        """
        初始化 GitHub 服务
        
        Args:
            token: GitHub Personal Access Token
            ai_config: AI 配置
        """
        self.api_client = GitHubAPIClient(token=token)
        self.batch_client = GitHubAPIBatchClient(self.api_client)
        self.cache = CacheManager()
        self.ai_service = AIService(ai_config)
        self.category_manager = CategoryManager()
        
        # 订阅的仓库
        self.subscribed_repos: Set[str] = set()
        self.release_updates: Dict[str, ReleaseUpdate] = {}
        
        # 资产过滤器
        self.asset_filters: List[AssetFilter] = []
    
    def authenticate(self) -> GitHubUser:
        """认证并获取用户信息"""
        try:
            user = self.api_client.get_authenticated_user()
            logger.info(f"GitHub 认证成功，用户: {user.login}")
            return user
        except AuthenticationError as e:
            logger.error(f"GitHub 认证失败: {e}")
            raise
        except Exception as e:
            logger.error(f"认证异常: {e}")
            raise
    
    def sync_starred_repos(self, force_refresh: bool = False) -> SyncResult:
        """同步星标仓库"""
        start_time = datetime.now()
        errors = []
        
        try:
            logger.info("开始同步星标仓库...")
            
            # 获取原始仓库数据
            raw_repos = self.batch_client.batch_get_starred_repos()
            
            # 转换为业务模型
            starred_repos = []
            synced_count = 0
            failed_count = 0
            
            for repo_data in raw_repos:
                try:
                    # 生成缓存键
                    cache_key = f"starred_repo_{repo_data.id}"
                    
                    # 检查缓存
                    if not force_refresh:
                        cached = self.cache.get(cache_key)
                        if cached:
                            starred_repos.append(StarredRepo(**cached))
                            continue
                    
                    # 创建业务模型
                    starred_repo = StarredRepo(
                        id=repo_data.id,
                        name=repo_data.name,
                        full_name=repo_data.full_name,
                        description=repo_data.description,
                        html_url=repo_data.html_url,
                        language=repo_data.language,
                        stargazers_count=repo_data.stargazers_count,
                        topics=repo_data.topics,
                        created_at=repo_data.created_at,
                        updated_at=repo_data.updated_at,
                        starred_at=datetime.now().isoformat(),
                        is_archived=repo_data.archived,
                        is_fork=repo_data.fork,
                        license=repo_data.license.get('name') if repo_data.license else None
                    )
                    
                    # 缓存仓库信息
                    self.cache.set(cache_key, asdict(starred_repo), expire_minutes=1440)
                    starred_repos.append(starred_repo)
                    synced_count += 1
                    
                except Exception as e:
                    error_msg = f"处理仓库 {repo_data.full_name} 失败: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    failed_count += 1
            
            end_time = datetime.now()
            
            result = SyncResult(
                success=True,
                total_repos=len(raw_repos),
                synced_repos=synced_count,
                failed_repos=failed_count,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                errors=errors,
                rate_limit_info=asdict(self.api_client._rate_limit_info) if self.api_client._rate_limit_info else None
            )
            
            logger.info(f"同步完成: 成功 {synced_count}, 失败 {failed_count}")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            error_msg = f"同步星标仓库失败: {e}"
            logger.error(error_msg)
            
            return SyncResult(
                success=False,
                total_repos=0,
                synced_repos=0,
                failed_repos=0,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                errors=[error_msg]
            )
    
    def search_repos(self, repos: List[StarredRepo], 
                    query: Optional[str] = None,
                    language: Optional[str] = None,
                    topic: Optional[str] = None,
                    category: Optional[str] = None) -> List[StarredRepo]:
        """搜索仓库"""
        filtered_repos = repos.copy()
        
        if query:
            query_lower = query.lower()
            filtered_repos = [
                repo for repo in filtered_repos
                if (query_lower in repo.name.lower() or
                    query_lower in repo.description.lower() or
                    any(query_lower in topic.lower() for topic in repo.topics))
            ]
        
        if language:
            filtered_repos = [repo for repo in filtered_repos 
                            if repo.language and language.lower() in repo.language.lower()]
        
        if topic:
            filtered_repos = [repo for repo in filtered_repos 
                            if topic in repo.topics]
        
        if category:
            filtered_repos = [repo for repo in filtered_repos 
                            if repo.custom_category == category]
        
        return filtered_repos
    
    def generate_ai_summary(self, repo: StarredRepo) -> Optional[str]:
        """生成 AI 摘要"""
        return self.ai_service.generate_repo_summary(repo)
    
    def generate_ai_tags(self, repo: StarredRepo) -> List[str]:
        """生成 AI 标签"""
        return self.ai_service.generate_repo_tags(repo)
    
    def bulk_generate_ai_summary(self, repos: List[StarredRepo],
                                max_workers: int = 5) -> Dict[str, int]:
        """批量生成 AI 摘要"""
        success_count = 0
        failed_count = 0
        
        def process_repo(repo: StarredRepo):
            try:
                summary = self.generate_ai_summary(repo)
                if summary:
                    repo.ai_summary = summary
                    success_count += 1
                    logger.info(f"生成摘要成功: {repo.name}")
                else:
                    failed_count += 1
                    logger.warning(f"生成摘要失败: {repo.name}")
            except Exception as e:
                failed_count += 1
                logger.error(f"处理仓库 {repo.name} 时出错: {e}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(process_repo, repos)
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(repos)
        }
    
    def subscribe_repo(self, owner: str, repo_name: str) -> bool:
        """订阅仓库发布"""
        repo_key = f"{owner}/{repo_name}"
        self.subscribed_repos.add(repo_key)
        
        # 初始化发布信息
        try:
            releases = self.api_client.get_repo_releases(owner, repo_name)
            latest_release = self.api_client.get_latest_release(owner, repo_name)
            
            self.release_updates[repo_key] = ReleaseUpdate(
                repo_full_name=repo_key,
                repo_name=repo_name,
                latest_release=asdict(latest_release) if latest_release else None,
                new_releases=[asdict(r) for r in releases],
                subscribed_at=datetime.now().isoformat(),
                last_checked_at=datetime.now().isoformat()
            )
            
            logger.info(f"成功订阅仓库: {repo_key}")
            return True
            
        except Exception as e:
            logger.error(f"订阅仓库失败: {e}")
            return False
    
    def unsubscribe_repo(self, owner: str, repo_name: str) -> bool:
        """取消订阅仓库"""
        repo_key = f"{owner}/{repo_name}"
        self.subscribed_repos.discard(repo_key)
        
        if repo_key in self.release_updates:
            del self.release_updates[repo_key]
        
        logger.info(f"已取消订阅: {repo_key}")
        return True
    
    def check_release_updates(self) -> Dict[str, Any]:
        """检查发布更新"""
        if not self.subscribed_repos:
            return {"success": True, "updates": []}
        
        start_time = datetime.now()
        updates = []
        
        for repo_key in list(self.subscribed_repos):
            try:
                owner, repo_name = repo_key.split('/', 1)
                
                # 获取最新发布
                latest_release = self.api_client.get_latest_release(owner, repo_name)
                
                if repo_key in self.release_updates:
                    # 检查是否有新发布
                    old_update = self.release_updates[repo_key]
                    old_latest = old_update.latest_release
                    
                    if (not old_latest and latest_release) or \
                       (old_latest and latest_release and 
                        old_latest['published_at'] != latest_release.published_at):
                        
                        # 有新发布
                        updates.append({
                            "repo_full_name": repo_key,
                            "old_latest": old_latest,
                            "new_latest": asdict(latest_release),
                            "has_update": True
                        })
                
                # 更新发布信息
                self.release_updates[repo_key] = ReleaseUpdate(
                    repo_full_name=repo_key,
                    repo_name=repo_name,
                    latest_release=asdict(latest_release) if latest_release else None,
                    new_releases=[],
                    subscribed_at=old_update.subscribed_at if repo_key in self.release_updates else datetime.now().isoformat(),
                    last_checked_at=datetime.now().isoformat(),
                    is_read=False
                )
                
            except Exception as e:
                logger.error(f"检查发布更新失败 {repo_key}: {e}")
        
        return {
            "success": True,
            "updates": updates,
            "check_time": start_time.isoformat(),
            "total_subscribed": len(self.subscribed_repos)
        }
    
    def get_repo_assets(self, owner: str, repo_name: str) -> List[RepositoryAsset]:
        """获取仓库发布资产"""
        try:
            releases = self.api_client.get_repo_releases(owner, repo_name)
            assets = []
            
            for release in releases:
                for asset_data in release.assets:
                    # 检测平台关键词
                    platform_keywords = self._detect_platform_keywords(asset_data['name'])
                    
                    # 创建资产模型
                    asset = RepositoryAsset(
                        repo_full_name=f"{owner}/{repo_name}",
                        asset_id=asset_data['id'],
                        asset_name=asset_data['name'],
                        size=asset_data['size'],
                        download_count=asset_data['download_count'],
                        created_at=asset_data['created_at'],
                        updated_at=asset_data['updated_at'],
                        download_url=asset_data['browser_download_url'],
                        content_type=asset_data['content_type'],
                        platform_keywords=platform_keywords,
                        matched_filters=[]
                    )
                    
                    # 检查过滤器匹配
                    for filter_obj in self.asset_filters:
                        if filter_obj.matches(asset):
                            asset.matched_filters.append(filter_obj.name)
                    
                    assets.append(asset)
            
            return assets
            
        except Exception as e:
            logger.error(f"获取仓库资产失败 {owner}/{repo_name}: {e}")
            return []
    
    def _detect_platform_keywords(self, filename: str) -> List[str]:
        """检测文件名的平台关键词"""
        filename_lower = filename.lower()
        keywords = []
        
        platform_map = {
            "Windows": ["exe", "msi", "dmg", "pkg", "win32", "win64"],
            "macOS": ["dmg", "pkg", "mac", "osx", "darwin"],
            "Linux": ["deb", "rpm", "AppImage", "tar.gz", "linux"],
            "Android": ["apk", "android"],
            "iOS": ["ipa", "ios"],
            "ARM": ["arm64", "aarch64", "arm"],
            "x86": ["x86", "x64", "amd64"],
            "Docker": ["docker", "container"],
            "Source": ["zip", "tar.gz", "source"]
        }
        
        for platform, platform_keywords in platform_map.items():
            for keyword in platform_keywords:
                if keyword in filename_lower:
                    keywords.append(platform)
                    break
        
        return keywords
    
    def add_asset_filter(self, name: str, keywords: List[str]) -> AssetFilter:
        """添加资产过滤器"""
        filter_obj = AssetFilter(name, keywords)
        self.asset_filters.append(filter_obj)
        return filter_obj
    
    def remove_asset_filter(self, name: str) -> bool:
        """移除资产过滤器"""
        for i, filter_obj in enumerate(self.asset_filters):
            if filter_obj.name == name:
                del self.asset_filters[i]
                return True
        return False
    
    def get_repository_stats(self, repos: List[StarredRepo]) -> Dict[str, Any]:
        """获取仓库统计信息"""
        if not repos:
            return {}
        
        # 语言统计
        language_stats = {}
        topic_stats = {}
        category_stats = {}
        
        for repo in repos:
            # 语言统计
            lang = repo.language or "未知"
            language_stats[lang] = language_stats.get(lang, 0) + 1
            
            # 主题统计
            for topic in repo.topics:
                topic_stats[topic] = topic_stats.get(topic, 0) + 1
            
            # 分类统计
            category = repo.custom_category or "未分类"
            category_stats[category] = category_stats.get(category, 0) + 1
        
        # 按频率排序
        sorted_languages = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)
        sorted_topics = sorted(topic_stats.items(), key=lambda x: x[1], reverse=True)
        sorted_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_repos": len(repos),
            "languages": sorted_languages[:20],  # 前20种语言
            "topics": sorted_topics[:30],        # 前30个主题
            "categories": sorted_categories,
            "archived_repos": len([r for r in repos if r.is_archived]),
            "fork_repos": len([r for r in repos if r.is_fork]),
            "avg_stars": sum(r.stargazers_count for r in repos) / len(repos),
            "repos_with_description": len([r for r in repos if r.description]),
            "repos_with_topics": len([r for r in repos if r.topics])
        }
    
    def export_data(self, repos: List[StarredRepo], 
                   format: str = "json") -> str:
        """导出数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            filename = f"github_stars_export_{timestamp}.json"
            data = {
                "export_time": datetime.now().isoformat(),
                "total_repos": len(repos),
                "repos": [asdict(repo) for repo in repos]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        elif format.lower() == "csv":
            import csv
            filename = f"github_stars_export_{timestamp}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if repos:
                    writer = csv.DictWriter(f, fieldnames=asdict(repos[0]).keys())
                    writer.writeheader()
                    for repo in repos:
                        writer.writerow(asdict(repo))
        
        else:
            raise ValueError(f"不支持的导出格式: {format}")
        
        logger.info(f"数据已导出到: {filename}")
        return filename
    
    def cleanup_cache(self) -> Dict[str, int]:
        """清理缓存"""
        expired_count = self.cache.clear_expired()
        total_count = self.cache.clear_all()
        
        return {
            "expired_cleaned": expired_count,
            "total_cleaned": total_count
        }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """获取速率限制状态"""
        try:
            rate_info = self.api_client.get_rate_limit()
            reset_time = datetime.fromtimestamp(rate_info.reset)
            time_until_reset = (reset_time - datetime.now()).total_seconds()
            
            return {
                "limit": rate_info.limit,
                "remaining": rate_info.remaining,
                "used": rate_info.used,
                "reset_time": reset_time.isoformat(),
                "time_until_reset_seconds": max(0, int(time_until_reset)),
                "percentage_used": round((rate_info.used / rate_info.limit) * 100, 2)
            }
        except Exception as e:
            logger.error(f"获取速率限制状态失败: {e}")
            return {"error": str(e)}


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 初始化服务
    github_service = GitHubService(
        token="your-github-token",
        ai_config=AIConfig(
            id="openai",
            name="OpenAI",
            api_url="https://api.openai.com/v1/chat/completions",
            api_key="your-openai-key",
            model="gpt-3.5-turbo"
        )
    )
    
    try:
        # 认证
        user = github_service.authenticate()
        print(f"认证用户: {user.login}")
        
        # 同步星标仓库
        sync_result = github_service.sync_starred_repos()
        print(f"同步结果: {sync_result}")
        
        # 获取统计信息
        # repos = [StarredRepo(...)]  # 从同步结果获取
        # stats = github_service.get_repository_stats(repos)
        # print(f"统计信息: {stats}")
        
        # 检查发布更新
        updates = github_service.check_release_updates()
        print(f"发布更新: {updates}")
        
    except Exception as e:
        print(f"错误: {e}")