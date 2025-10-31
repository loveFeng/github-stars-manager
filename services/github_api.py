"""
GitHub API 客户端封装
基于原项目 GitHubStarsManager 的功能需求，实现完整的 GitHub API 集成
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


@dataclass
class GitHubUser:
    """GitHub 用户信息"""
    login: str
    id: int
    avatar_url: str
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class GitHubRepository:
    """GitHub 仓库信息"""
    id: int
    name: str
    full_name: str
    description: Optional[str]
    html_url: str
    clone_url: str
    ssh_url: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    watchers_count: int
    open_issues_count: int
    size: int
    license: Optional[Dict[str, Any]]
    topics: List[str]
    created_at: str
    updated_at: str
    pushed_at: Optional[str]
    default_branch: str
    archived: bool
    disabled: bool
    is_private: bool
    fork: bool
    parent: Optional[Dict[str, Any]]
    owner: Dict[str, Any]


@dataclass
class GitHubRelease:
    """GitHub Release 信息"""
    id: int
    tag_name: str
    name: Optional[str]
    body: Optional[str]
    html_url: str
    tarball_url: str
    zipball_url: str
    draft: bool
    prerelease: bool
    created_at: str
    published_at: Optional[str]
    author: Dict[str, Any]
    assets: List[Dict[str, Any]]


@dataclass
class GitHubAsset:
    """GitHub Release 资产信息"""
    id: int
    name: str
    size: int
    download_count: int
    created_at: str
    updated_at: str
    browser_download_url: str
    content_type: str
    state: str


@dataclass
class RateLimitInfo:
    """API 速率限制信息"""
    limit: int
    remaining: int
    reset: int
    used: int
    resource: str


class GitHubAPIError(Exception):
    """GitHub API 异常"""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response: Optional[Dict] = None, headers: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        self.headers = headers or {}
        super().__init__(self.message)


class RateLimitExceededError(GitHubAPIError):
    """速率限制异常"""
    def __init__(self, message: str, rate_limit_info: RateLimitInfo):
        super().__init__(message)
        self.rate_limit_info = rate_limit_info


class AuthenticationError(GitHubAPIError):
    """认证异常"""
    pass


class NotFoundError(GitHubAPIError):
    """资源不存在异常"""
    pass


class ValidationError(GitHubAPIError):
    """参数验证异常"""
    pass


class GitHubAPIClient:
    """GitHub API 客户端"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        初始化 GitHub API 客户端
        
        Args:
            token: GitHub Personal Access Token 或 GitHub App Token
            username: GitHub 用户名（用于基本认证）
            password: GitHub 密码或 Personal Access Token（用于基本认证）
        """
        self.token = token
        self.username = username
        self.password = password
        self.session = self._create_session()
        self._rate_limit_info: Optional[RateLimitInfo] = None
        
    def _create_session(self) -> requests.Session:
        """创建带重试机制的会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHubStarsManager/1.0"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        elif self.username and self.password:
            from base64 import b64encode
            credentials = b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """处理 API 响应"""
        # 更新速率限制信息
        if 'X-RateLimit-Limit' in response.headers:
            self._rate_limit_info = RateLimitInfo(
                limit=int(response.headers.get('X-RateLimit-Limit', 0)),
                remaining=int(response.headers.get('X-RateLimit-Remaining', 0)),
                reset=int(response.headers.get('X-RateLimit-Reset', 0)),
                used=int(response.headers.get('X-RateLimit-Used', 0)),
                resource="core"
            )
        
        # 错误处理
        if response.status_code == 401:
            raise AuthenticationError(
                "GitHub 认证失败，请检查 token 或用户名密码",
                status_code=401,
                response=response.json() if response.content else None,
                headers=dict(response.headers)
            )
        
        if response.status_code == 403:
            if self._rate_limit_info and self._rate_limit_info.remaining == 0:
                reset_time = datetime.fromtimestamp(self._rate_limit_info.reset)
                raise RateLimitExceededError(
                    f"GitHub API 速率限制已用尽，重置时间: {reset_time}",
                    self._rate_limit_info
                )
            raise GitHubAPIError(
                "GitHub API 访问被拒绝，可能权限不足",
                status_code=403,
                response=response.json() if response.content else None,
                headers=dict(response.headers)
            )
        
        if response.status_code == 404:
            raise NotFoundError(
                "请求的资源不存在",
                status_code=404,
                response=response.json() if response.content else None,
                headers=dict(response.headers)
            )
        
        if response.status_code == 422:
            raise ValidationError(
                "请求参数无效",
                status_code=422,
                response=response.json() if response.content else None,
                headers=dict(response.headers)
            )
        
        if response.status_code >= 400:
            error_msg = response.json() if response.content else {}
            message = error_msg.get('message', '未知错误')
            raise GitHubAPIError(
                f"GitHub API 错误: {message}",
                status_code=response.status_code,
                response=error_msg,
                headers=dict(response.headers)
            )
        
        return response.json() if response.content else {}
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发起 API 请求"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_auth_headers()
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        
        try:
            response = self.session.request(method, url, **kwargs)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"网络请求失败: {str(e)}")
    
    def get_rate_limit(self) -> RateLimitInfo:
        """获取 API 速率限制信息"""
        try:
            data = self._request('GET', '/rate_limit')
            self._rate_limit_info = RateLimitInfo(
                limit=data['rate']['limit'],
                remaining=data['rate']['remaining'],
                reset=data['rate']['reset'],
                used=data['rate']['used'],
                resource="core"
            )
            return self._rate_limit_info
        except Exception as e:
            logger.error(f"获取速率限制信息失败: {e}")
            raise
    
    def get_user(self, username: Optional[str] = None) -> GitHubUser:
        """获取用户信息"""
        endpoint = f"/user" if not username else f"/users/{username}"
        data = self._request('GET', endpoint)
        return GitHubUser(**data)
    
    def get_authenticated_user(self) -> GitHubUser:
        """获取当前认证用户信息"""
        return self.get_user()
    
    def get_user_repos(self, username: Optional[str] = None, 
                       type: str = "all", sort: str = "updated",
                       direction: str = "desc", per_page: int = 100,
                       page: int = 1) -> List[GitHubRepository]:
        """获取用户仓库列表"""
        if not username:
            username = "user"
            endpoint = f"/user/repos"
        else:
            endpoint = f"/users/{username}/repos"
        
        params = {
            "type": type,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page
        }
        
        data = self._request('GET', endpoint, params=params)
        return [GitHubRepository(**repo) for repo in data]
    
    def get_starred_repos(self, username: Optional[str] = None,
                          sort: str = "created", direction: str = "desc",
                          per_page: int = 100, page: int = 1) -> List[GitHubRepository]:
        """获取用户星标仓库列表"""
        if not username:
            username = "user"
            endpoint = f"/user/starred"
        else:
            endpoint = f"/users/{username}/starred"
        
        params = {
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page
        }
        
        data = self._request('GET', endpoint, params=params)
        return [GitHubRepository(**repo) for repo in data]
    
    def check_starred_repo(self, owner: str, repo: str) -> bool:
        """检查是否已星标仓库"""
        endpoint = f"/user/starred/{owner}/{repo}"
        try:
            self._request('GET', endpoint)
            return True
        except NotFoundError:
            return False
        except GitHubAPIError:
            return False
    
    def star_repo(self, owner: str, repo: str) -> bool:
        """为仓库添加星标"""
        endpoint = f"/user/starred/{owner}/{repo}"
        try:
            self._request('PUT', endpoint)
            return True
        except GitHubAPIError as e:
            if e.status_code == 404:
                # 仓库不存在
                return False
            raise
    
    def unstar_repo(self, owner: str, repo: str) -> bool:
        """取消仓库星标"""
        endpoint = f"/user/starred/{owner}/{repo}"
        try:
            self._request('DELETE', endpoint)
            return True
        except GitHubAPIError as e:
            if e.status_code == 404:
                # 仓库不存在或未星标
                return False
            raise
    
    def get_repo(self, owner: str, repo: str) -> GitHubRepository:
        """获取仓库详细信息"""
        endpoint = f"/repos/{owner}/{repo}"
        data = self._request('GET', endpoint)
        return GitHubRepository(**data)
    
    def get_repo_releases(self, owner: str, repo: str,
                         per_page: int = 100, page: int = 1) -> List[GitHubRelease]:
        """获取仓库发布列表"""
        endpoint = f"/repos/{owner}/{repo}/releases"
        params = {
            "per_page": per_page,
            "page": page
        }
        
        data = self._request('GET', endpoint, params=params)
        return [GitHubRelease(**release) for release in data]
    
    def get_latest_release(self, owner: str, repo: str) -> Optional[GitHubRelease]:
        """获取仓库最新发布"""
        endpoint = f"/repos/{owner}/{repo}/releases/latest"
        try:
            data = self._request('GET', endpoint)
            return GitHubRelease(**data)
        except NotFoundError:
            return None
    
    def get_repo_tags(self, owner: str, repo: str,
                     per_page: int = 100, page: int = 1) -> List[Dict[str, Any]]:
        """获取仓库标签列表"""
        endpoint = f"/repos/{owner}/{repo}/tags"
        params = {
            "per_page": per_page,
            "page": page
        }
        
        return self._request('GET', endpoint, params=params)
    
    def search_repositories(self, query: str, sort: str = "stars",
                           order: str = "desc", per_page: int = 100,
                           page: int = 1) -> Dict[str, Any]:
        """搜索仓库"""
        endpoint = "/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
            "page": page
        }
        
        return self._request('GET', endpoint, params=params)
    
    def search_code(self, query: str, sort: str = "indexed",
                   order: str = "desc", per_page: int = 100,
                   page: int = 1) -> Dict[str, Any]:
        """搜索代码"""
        endpoint = "/search/code"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
            "page": page
        }
        
        return self._request('GET', endpoint, params=params)
    
    def get_repo_topics(self, owner: str, repo: str) -> List[str]:
        """获取仓库话题标签"""
        endpoint = f"/repos/{owner}/{repo}/topics"
        data = self._request('GET', endpoint)
        return data.get('names', [])
    
    def set_repo_topics(self, owner: str, repo: str, topics: List[str]) -> List[str]:
        """设置仓库话题标签"""
        endpoint = f"/repos/{owner}/{repo}/topics"
        data = {"names": topics}
        headers = {"Accept": "application/vnd.github.v3+json"}
        response_data = self._request('PUT', endpoint, json=data, headers=headers)
        return response_data.get('names', [])
    
    def download_asset(self, asset_url: str, headers: Optional[Dict] = None) -> bytes:
        """下载发布资产"""
        auth_headers = self._get_auth_headers()
        if headers:
            auth_headers.update(headers)
        
        response = self.session.get(asset_url, headers=auth_headers)
        if response.status_code >= 400:
            raise GitHubAPIError(
                f"下载资产失败: {response.status_code}",
                status_code=response.status_code
            )
        
        return response.content
    
    def wait_for_rate_limit_reset(self, max_wait_minutes: int = 10) -> bool:
        """等待速率限制重置"""
        if not self._rate_limit_info:
            return True
        
        if self._rate_limit_info.remaining > 0:
            return True
        
        reset_time = datetime.fromtimestamp(self._rate_limit_info.reset)
        wait_time = (reset_time - datetime.now()).total_seconds()
        max_wait = max_wait_minutes * 60
        
        if wait_time > max_wait:
            logger.warning(f"速率限制重置时间过长 ({wait_time:.0f}s), 跳过等待")
            return False
        
        logger.info(f"等待速率限制重置，剩余时间: {wait_time:.0f}s")
        time.sleep(wait_time + 1)  # 多等待1秒确保重置
        return True
    
    def get_repository_summary(self, owner: str, repo: str) -> Dict[str, Any]:
        """获取仓库摘要信息"""
        try:
            repo_info = self.get_repo(owner, repo)
            
            summary = {
                "id": repo_info.id,
                "name": repo_info.name,
                "full_name": repo_info.full_name,
                "description": repo_info.description,
                "html_url": repo_info.html_url,
                "language": repo_info.language,
                "stargazers_count": repo_info.stargazers_count,
                "forks_count": repo_info.forks_count,
                "open_issues_count": repo_info.open_issues_count,
                "created_at": repo_info.created_at,
                "updated_at": repo_info.updated_at,
                "topics": repo_info.topics,
                "is_fork": repo_info.fork,
                "is_archived": repo_info.archived,
                "default_branch": repo_info.default_branch,
                "license": repo_info.license.get('name') if repo_info.license else None,
                "owner": repo_info.owner.get('login') if repo_info.owner else None
            }
            
            # 获取最新发布
            latest_release = self.get_latest_release(owner, repo)
            if latest_release:
                summary["latest_release"] = {
                    "tag_name": latest_release.tag_name,
                    "name": latest_release.name,
                    "published_at": latest_release.published_at,
                    "html_url": latest_release.html_url,
                    "prerelease": latest_release.prerelease
                }
            
            return summary
        except Exception as e:
            logger.error(f"获取仓库 {owner}/{repo} 摘要失败: {e}")
            raise


class GitHubAPIBatchClient:
    """GitHub API 批量操作客户端"""
    
    def __init__(self, client: GitHubAPIClient):
        self.client = client
    
    def batch_get_starred_repos(self, username: Optional[str] = None,
                               batch_size: int = 100) -> List[GitHubRepository]:
        """批量获取所有星标仓库"""
        all_repos = []
        page = 1
        
        while True:
            repos = self.client.get_starred_repos(
                username=username,
                per_page=batch_size,
                page=page
            )
            
            if not repos:
                break
            
            all_repos.extend(repos)
            
            # 检查是否还有更多页面
            if len(repos) < batch_size:
                break
            
            # 速率限制检查
            if self.client._rate_limit_info:
                if self.client._rate_limit_info.remaining < 10:
                    logger.info("API 调用次数接近限制，等待速率限制重置")
                    self.client.wait_for_rate_limit_reset()
            
            page += 1
        
        return all_repos
    
    def batch_sync_starred_repos(self, username: Optional[str] = None,
                                batch_size: int = 100) -> Dict[str, Any]:
        """批量同步星标仓库"""
        start_time = datetime.now()
        
        try:
            repos = self.batch_get_starred_repos(username, batch_size)
            
            sync_result = {
                "success": True,
                "total_count": len(repos),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "repos": [asdict(repo) for repo in repos],
                "rate_limit": asdict(self.client._rate_limit_info) if self.client._rate_limit_info else None
            }
            
            logger.info(f"成功同步 {len(repos)} 个星标仓库")
            return sync_result
            
        except Exception as e:
            logger.error(f"批量同步星标仓库失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            }
    
    def batch_get_releases(self, repos: List[tuple], 
                          max_repos: int = 50) -> Dict[str, Any]:
        """批量获取发布信息"""
        if len(repos) > max_repos:
            logger.warning(f"仓库数量超过限制 {max_repos}，将只处理前 {max_repos} 个")
            repos = repos[:max_repos]
        
        start_time = datetime.now()
        results = []
        
        for i, (owner, repo_name) in enumerate(repos):
            try:
                logger.info(f"获取发布信息 ({i+1}/{len(repos)}): {owner}/{repo_name}")
                
                releases = self.client.get_repo_releases(owner, repo_name)
                latest_release = self.client.get_latest_release(owner, repo_name)
                
                result = {
                    "owner": owner,
                    "repo": repo_name,
                    "releases_count": len(releases),
                    "latest_release": asdict(latest_release) if latest_release else None,
                    "releases": [asdict(release) for release in releases[:10]]  # 只保留最新10个
                }
                
                results.append(result)
                
                # 速率限制检查
                if self.client._rate_limit_info and self.client._rate_limit_info.remaining < 5:
                    logger.info("API 调用次数接近限制，等待速率限制重置")
                    self.client.wait_for_rate_limit_reset()
                
            except Exception as e:
                logger.error(f"获取 {owner}/{repo_name} 发布信息失败: {e}")
                results.append({
                    "owner": owner,
                    "repo": repo_name,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_repos": len(repos),
            "processed_repos": len(results),
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "results": results,
            "rate_limit": asdict(self.client._rate_limit_info) if self.client._rate_limit_info else None
        }