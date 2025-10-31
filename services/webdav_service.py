"""
WebDAV 客户端服务
提供对多种 WebDAV 服务的统一封装，包括坚果云、Nextcloud、ownCloud 等
"""

import os
import hashlib
import logging
from typing import Dict, List, Optional, Union, BinaryIO, Tuple
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import mimetypes
import json

try:
    import requests
    from requests.auth import HTTPBasicAuth, HTTPDigestAuth
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

from pathlib import Path


@dataclass
class WebDAVCredentials:
    """WebDAV 认证信息"""
    username: str
    password: str
    url: str
    service_type: str = "custom"  # nutstore, nextcloud, owncloud, custom
    
    
@dataclass
class WebDAVFile:
    """WebDAV 文件信息"""
    href: str
    name: str
    size: int
    modified: datetime
    is_directory: bool
    content_type: str = ""
    etag: str = ""
    

class WebDAVError(Exception):
    """WebDAV 错误异常"""
    pass


class WebDAVConnectionError(WebDAVError):
    """WebDAV 连接错误"""
    pass


class WebDAVAuthError(WebDAVError):
    """WebDAV 认证错误"""
    pass


class WebDAVClient:
    """
    WebDAV 客户端
    支持多种 WebDAV 服务商的统一接口
    """
    
    # 支持的 WebDAV 服务商配置
    SERVICE_CONFIGS = {
        "nutstore": {
            "name": "坚果云",
            "base_path": "/",
            "auth_type": "basic",
            "requires_auth": True
        },
        "nextcloud": {
            "name": "Nextcloud",
            "base_path": "/remote.php/webdav/",
            "auth_type": "basic",
            "requires_auth": True
        },
        "owncloud": {
            "name": "ownCloud",
            "base_path": "/remote.php/webdav/",
            "auth_type": "basic", 
            "requires_auth": True
        },
        "custom": {
            "name": "自定义 WebDAV",
            "base_path": "/",
            "auth_type": "basic",
            "requires_auth": True
        }
    }
    
    def __init__(self, credentials: WebDAVCredentials):
        """
        初始化 WebDAV 客户端
        
        Args:
            credentials: WebDAV 认证信息
        """
        self.credentials = credentials
        self.service_type = credentials.service_type.lower()
        self.base_url = credentials.url.rstrip('/')
        
        # 获取服务配置
        if self.service_type not in self.SERVICE_CONFIGS:
            self.service_type = "custom"
        self.config = self.SERVICE_CONFIGS[self.service_type]
        
        # 设置 WebDAV 路径前缀
        self.webdav_path = self.config["base_path"]
        self.full_base_url = urljoin(self.base_url, self.webdav_path)
        
        # 初始化会话
        self._init_session()
        
        # 验证连接
        self._test_connection()
    
    def _init_session(self):
        """初始化请求会话"""
        self.session = requests.Session()
        
        # 设置重试策略
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["HEAD", "GET", "OPTIONS", "PUT", "POST", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置认证
        if self.config["requires_auth"]:
            if self.config["auth_type"] == "basic":
                self.session.auth = HTTPBasicAuth(
                    self.credentials.username, 
                    self.credentials.password
                )
            elif self.config["auth_type"] == "digest":
                self.session.auth = HTTPDigestAuth(
                    self.credentials.username,
                    self.credentials.password
                )
        
        # 设置默认 headers
        self.session.headers.update({
            'User-Agent': 'WebDAV-Backup-Service/1.0',
            'Accept': '*/*'
        })
        
        logging.info(f"WebDAV 客户端初始化完成 - 服务: {self.config['name']}")
    
    def _test_connection(self):
        """测试连接"""
        try:
            response = self.session.options(self.full_base_url)
            if response.status_code not in [200, 207]:
                raise WebDAVConnectionError(
                    f"连接测试失败，状态码: {response.status_code}, "
                    f"响应: {response.text[:200]}"
                )
            logging.info("WebDAV 连接测试成功")
        except Exception as e:
            raise WebDAVConnectionError(f"连接测试失败: {str(e)}")
    
    def _build_url(self, remote_path: str) -> str:
        """
        构建远程文件 URL
        
        Args:
            remote_path: 远程路径（相对于 WebDAV 根目录）
            
        Returns:
            完整的 URL
        """
        # 清理路径
        remote_path = remote_path.strip('/')
        if remote_path:
            remote_path = '/' + remote_path
        
        return urljoin(self.full_base_url, remote_path)
    
    def _parse_propfind_response(self, response_text: str, base_url: str) -> List[WebDAVFile]:
        """
        解析 PROPFIND 响应
        
        Args:
            response_text: XML 响应文本
            base_url: 基础 URL
            
        Returns:
            WebDAV 文件列表
        """
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            raise WebDAVError("需要安装 xml.etree.ElementTree 模块")
        
        files = []
        try:
            root = ET.fromstring(response_text)
            
            # 处理 XML 命名空间
            namespaces = {
                'd': 'DAV:',
                'oc': 'http://owncloud.org/ns',
                'nc': 'http://nextcloud.com/ns'
            }
            
            for response in root.findall('.//d:response', namespaces):
                # 获取文件路径
                href_elem = response.find('.//d:href', namespaces)
                if not href_elem:
                    continue
                
                href = href_elem.text or ''
                name = os.path.basename(href) or '/'
                
                # 获取文件属性
                propstat = response.find('.//d:propstat/d:prop', namespaces)
                if propstat is None:
                    continue
                
                # 获取文件大小
                size_elem = propstat.find('.//d:getcontentlength', namespaces)
                size = int(size_elem.text) if size_elem is not None and size_elem.text else 0
                
                # 获取修改时间
                modified_elem = propstat.find('.//d:getlastmodified', namespaces)
                if modified_elem is not None and modified_elem.text:
                    try:
                        modified = datetime.strptime(modified_elem.text, '%a, %d %b %Y %H:%M:%S %Z')
                    except ValueError:
                        modified = datetime.now()
                else:
                    modified = datetime.now()
                
                # 获取内容类型
                content_type_elem = propstat.find('.//d:getcontenttype', namespaces)
                content_type = content_type_elem.text if content_type_elem is not None else ''
                
                # 获取 ETag
                etag_elem = propstat.find('.//d:getetag', namespaces)
                etag = etag_elem.text if etag_elem is not None else ''
                
                # 判断是否为目录
                is_directory = size_elem is None or size == 0
                
                files.append(WebDAVFile(
                    href=href,
                    name=name,
                    size=size,
                    modified=modified,
                    is_directory=is_directory,
                    content_type=content_type,
                    etag=etag
                ))
        
        except ET.ParseError as e:
            logging.error(f"XML 解析错误: {e}")
            raise WebDAVError(f"解析服务器响应失败: {e}")
        
        return files
    
    def list_files(self, remote_path: str = "") -> List[WebDAVFile]:
        """
        列出远程目录中的文件
        
        Args:
            remote_path: 远程目录路径
            
        Returns:
            文件列表
        """
        url = self._build_url(remote_path)
        
        headers = {
            'Depth': '1',
            'Content-Type': 'application/xml'
        }
        
        # 构建 PROPFIND 请求体
        propfind_request = """<?xml version="1.0" encoding="utf-8"?>
<propfind xmlns="DAV:">
    <prop>
        <resourcetype/>
        <getcontentlength/>
        <getlastmodified/>
        <getcontenttype/>
        <getetag/>
    </prop>
</propfind>"""
        
        try:
            response = self.session.request(
                'PROPFIND',
                url,
                headers=headers,
                data=propfind_request,
                timeout=30
            )
            
            if response.status_code not in [207, 200]:
                raise WebDAVError(f"列表文件失败，状态码: {response.status_code}")
            
            files = self._parse_propfind_response(response.text, url)
            
            # 过滤掉当前目录项
            return [f for f in files if f.name != os.path.basename(url)]
        
        except requests.RequestException as e:
            raise WebDAVError(f"网络请求失败: {str(e)}")
    
    def upload_file(self, local_path: Union[str, Path], remote_path: str = "") -> bool:
        """
        上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径（可选，默认使用本地文件名）
            
        Returns:
            是否上传成功
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        
        if local_path.is_dir():
            raise IsADirectoryError(f"路径是目录而不是文件: {local_path}")
        
        # 确定远程路径
        if not remote_path:
            remote_path = local_path.name
        
        url = self._build_url(remote_path)
        
        # 检测内容类型
        content_type, _ = mimetypes.guess_type(str(local_path))
        if not content_type:
            content_type = 'application/octet-stream'
        
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(local_path.stat().st_size)
        }
        
        try:
            with open(local_path, 'rb') as f:
                response = self.session.put(
                    url,
                    data=f,
                    headers=headers,
                    timeout=300
                )
            
            if response.status_code not in [200, 201, 204]:
                raise WebDAVError(f"上传文件失败，状态码: {response.status_code}")
            
            logging.info(f"文件上传成功: {local_path} -> {remote_path}")
            return True
        
        except requests.RequestException as e:
            raise WebDAVError(f"上传文件失败: {str(e)}")
    
    def download_file(self, remote_path: str, local_path: Union[str, Path]) -> bool:
        """
        下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地保存路径
            
        Returns:
            是否下载成功
        """
        local_path = Path(local_path)
        
        # 确保本地目录存在
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        url = self._build_url(remote_path)
        
        try:
            with self.session.get(url, stream=True, timeout=300) as response:
                if response.status_code != 200:
                    raise WebDAVError(f"下载文件失败，状态码: {response.status_code}")
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            logging.info(f"文件下载成功: {remote_path} -> {local_path}")
            return True
        
        except requests.RequestException as e:
            raise WebDAVError(f"下载文件失败: {str(e)}")
    
    def create_directory(self, remote_path: str) -> bool:
        """
        创建远程目录
        
        Args:
            remote_path: 远程目录路径
            
        Returns:
            是否创建成功
        """
        url = self._build_url(remote_path)
        
        headers = {
            'Content-Type': 'application/xml'
        }
        
        # 构建 MKCOL 请求体
        mkcol_request = """<?xml version="1.0" encoding="utf-8"?>
<D:mkcol xmlns:D="DAV:">
    <D:set>
        <D:prop>
            <D:resourcetype><D:collection/></D:resourcetype>
        </D:prop>
    </D:set>
</D:mkcol>"""
        
        try:
            response = self.session.request(
                'MKCOL',
                url,
                headers=headers,
                data=mkcol_request,
                timeout=30
            )
            
            if response.status_code not in [201, 200, 204]:
                raise WebDAVError(f"创建目录失败，状态码: {response.status_code}")
            
            logging.info(f"目录创建成功: {remote_path}")
            return True
        
        except requests.RequestException as e:
            raise WebDAVError(f"创建目录失败: {str(e)}")
    
    def delete_file(self, remote_path: str) -> bool:
        """
        删除远程文件或目录
        
        Args:
            remote_path: 远程路径
            
        Returns:
            是否删除成功
        """
        url = self._build_url(remote_path)
        
        try:
            response = self.session.delete(url, timeout=30)
            
            if response.status_code not in [200, 204, 404]:
                raise WebDAVError(f"删除文件失败，状态码: {response.status_code}")
            
            logging.info(f"文件删除成功: {remote_path}")
            return True
        
        except requests.RequestException as e:
            raise WebDAVError(f"删除文件失败: {str(e)}")
    
    def file_exists(self, remote_path: str) -> bool:
        """
        检查远程文件是否存在
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            文件是否存在
        """
        url = self._build_url(remote_path)
        
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_file_info(self, remote_path: str) -> Optional[WebDAVFile]:
        """
        获取文件信息
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            文件信息或 None
        """
        try:
            files = self.list_files(os.path.dirname(remote_path))
            filename = os.path.basename(remote_path)
            
            for file_info in files:
                if file_info.name == filename:
                    return file_info
            
            return None
        except Exception:
            return None
    
    def get_space_usage(self) -> Dict[str, Union[int, str]]:
        """
        获取存储空间使用情况
        
        Returns:
            空间使用信息字典
        """
        # 尝试获取 quota 属性
        try:
            url = self.full_base_url
            
            headers = {
                'Depth': '0',
                'Content-Type': 'application/xml'
            }
            
            propfind_request = """<?xml version="1.0" encoding="utf-8"?>
<propfind xmlns="DAV:">
    <prop>
        <quota-available-bytes/>
        <quota-used-bytes/>
    </prop>
</propfind>"""
            
            response = self.session.request(
                'PROPFIND',
                url,
                headers=headers,
                data=propfind_request,
                timeout=30
            )
            
            if response.status_code == 207:
                # 解析响应获取配额信息
                # 这里简化处理，实际实现需要完整的 XML 解析
                pass
        
        except Exception as e:
            logging.warning(f"获取存储空间信息失败: {e}")
        
        # 返回默认信息
        return {
            "available": "未知",
            "used": "未知", 
            "total": "未知"
        }
    
    def sync_directory(self, local_path: Union[str, Path], remote_path: str = "", 
                      create_remote_dirs: bool = True) -> Dict[str, bool]:
        """
        同步目录到远程
        
        Args:
            local_path: 本地目录路径
            remote_path: 远程目录路径
            create_remote_dirs: 是否创建远程目录
            
        Returns:
            同步结果字典 {文件名: 是否成功}
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"本地目录不存在: {local_path}")
        
        if not local_path.is_dir():
            raise NotADirectoryError(f"路径不是目录: {local_path}")
        
        results = {}
        
        # 如果需要创建远程目录
        if create_remote_dirs and remote_path:
            try:
                self.create_directory(remote_path)
            except WebDAVError as e:
                logging.warning(f"创建远程目录失败: {e}")
        
        # 遍历本地文件
        for local_file in local_path.rglob('*'):
            if local_file.is_file():
                # 计算相对路径
                relative_path = local_file.relative_to(local_path)
                remote_file_path = str(Path(remote_path) / relative_path) if remote_path else str(relative_path)
                
                try:
                    success = self.upload_file(local_file, remote_file_path)
                    results[str(relative_path)] = success
                except Exception as e:
                    logging.error(f"同步文件失败 {local_file}: {e}")
                    results[str(relative_path)] = False
        
        return results


class WebDAVService:
    """
    WebDAV 服务管理类
    提供统一的 WebDAV 服务接口
    """
    
    def __init__(self):
        self.clients: Dict[str, WebDAVClient] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_client(self, client_id: str, credentials: WebDAVCredentials) -> WebDAVClient:
        """
        添加 WebDAV 客户端
        
        Args:
            client_id: 客户端 ID
            credentials: 认证信息
            
        Returns:
            WebDAV 客户端实例
        """
        client = WebDAVClient(credentials)
        self.clients[client_id] = client
        self.logger.info(f"添加 WebDAV 客户端: {client_id}")
        return client
    
    def get_client(self, client_id: str) -> Optional[WebDAVClient]:
        """
        获取 WebDAV 客户端
        
        Args:
            client_id: 客户端 ID
            
        Returns:
            WebDAV 客户端实例或 None
        """
        return self.clients.get(client_id)
    
    def remove_client(self, client_id: str) -> bool:
        """
        移除 WebDAV 客户端
        
        Args:
            client_id: 客户端 ID
            
        Returns:
            是否移除成功
        """
        if client_id in self.clients:
            del self.clients[client_id]
            self.logger.info(f"移除 WebDAV 客户端: {client_id}")
            return True
        return False
    
    def list_clients(self) -> List[str]:
        """
        列出所有客户端 ID
        
        Returns:
            客户端 ID 列表
        """
        return list(self.clients.keys())
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        测试所有连接
        
        Returns:
            连接测试结果字典
        """
        results = {}
        for client_id, client in self.clients.items():
            try:
                client._test_connection()
                results[client_id] = True
            except Exception as e:
                self.logger.error(f"客户端 {client_id} 连接测试失败: {e}")
                results[client_id] = False
        
        return results


# 便捷函数
def create_webdav_client(service_type: str, url: str, username: str, password: str) -> WebDAVClient:
    """
    创建 WebDAV 客户端的便捷函数
    
    Args:
        service_type: 服务类型 (nutstore, nextcloud, owncloud, custom)
        url: WebDAV URL
        username: 用户名
        password: 密码
        
    Returns:
        WebDAV 客户端实例
    """
    credentials = WebDAVCredentials(
        username=username,
        password=password,
        url=url,
        service_type=service_type
    )
    return WebDAVClient(credentials)


# 预定义的服务配置
WEBDAV_SERVICES = {
    "nutstore": {
        "name": "坚果云",
        "example_url": "https://dav.jianguoyun.com/dav/",
        "description": "坚果云 WebDAV 服务"
    },
    "nextcloud": {
        "name": "Nextcloud",
        "example_url": "https://your-domain.com/remote.php/webdav/",
        "description": "Nextcloud WebDAV 服务"
    },
    "owncloud": {
        "name": "ownCloud",
        "example_url": "https://your-domain.com/remote.php/webdav/",
        "description": "ownCloud WebDAV 服务"
    }
}


if __name__ == "__main__":
    # 示例用法
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # 创建 WebDAV 客户端示例
    try:
        # 坚果云示例
        client = create_webdav_client(
            service_type="nutstore",
            url="https://dav.jianguoyun.com/dav/",
            username="your-username",
            password="your-password"
        )
        
        # 列出根目录文件
        files = client.list_files()
        print(f"根目录文件数量: {len(files)}")
        
        for file_info in files[:5]:  # 只显示前5个
            print(f"文件名: {file_info.name}, 大小: {file_info.size}, 修改时间: {file_info.modified}")
    
    except Exception as e:
        print(f"错误: {e}")