import axios from 'axios';
import type {
  GitHubUser,
  Repository,
  Release,
  AIConfig,
  WebDAVConfig,
  SyncLog,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加认证 token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('github_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('github_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// GitHub API 服务
export const githubAPI = {
  // 验证 token 并获取用户信息
  async validateToken(token: string): Promise<GitHubUser> {
    const response = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `token ${token}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });

    if (!response.ok) {
      throw new Error('Invalid token');
    }

    const data = await response.json();
    return {
      id: data.id,
      login: data.login,
      name: data.name,
      email: data.email,
      avatar_url: data.avatar_url,
      html_url: data.html_url,
      bio: data.bio,
      public_repos: data.public_repos,
      followers: data.followers,
      following: data.following,
    };
  },

  // 获取星标仓库
  async getStarredRepos(token: string, page = 1, perPage = 30): Promise<any[]> {
    const response = await fetch(
      `https://api.github.com/user/starred?page=${page}&per_page=${perPage}&sort=updated`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: 'application/vnd.github.v3+json',
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch starred repositories');
    }

    return response.json();
  },

  // 获取仓库详情
  async getRepository(token: string, owner: string, repo: string): Promise<any> {
    const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: {
        Authorization: `token ${token}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch repository');
    }

    return response.json();
  },

  // 获取仓库的 Releases
  async getRepositoryReleases(
    token: string,
    owner: string,
    repo: string,
    page = 1,
    perPage = 10
  ): Promise<any[]> {
    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/releases?page=${page}&per_page=${perPage}`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: 'application/vnd.github.v3+json',
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch releases');
    }

    return response.json();
  },

  // 获取速率限制信息
  async getRateLimit(token: string): Promise<any> {
    const response = await fetch('https://api.github.com/rate_limit', {
      headers: {
        Authorization: `token ${token}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch rate limit');
    }

    return response.json();
  },
};

// 仓库 API
export const repositoryAPI = {
  // 获取所有仓库
  async getAll(): Promise<Repository[]> {
    const response = await apiClient.get('/repositories');
    return response.data;
  },

  // 获取单个仓库
  async getById(id: number): Promise<Repository> {
    const response = await apiClient.get(`/repositories/${id}`);
    return response.data;
  },

  // 创建仓库
  async create(data: Partial<Repository>): Promise<Repository> {
    const response = await apiClient.post('/repositories', data);
    return response.data;
  },

  // 更新仓库
  async update(id: number, data: Partial<Repository>): Promise<Repository> {
    const response = await apiClient.patch(`/repositories/${id}`, data);
    return response.data;
  },

  // 删除仓库
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/repositories/${id}`);
  },

  // 同步星标仓库
  async sync(token: string): Promise<SyncLog> {
    const response = await apiClient.post('/repositories/sync', { token });
    return response.data;
  },

  // 搜索仓库
  async search(query: string, filters?: any): Promise<Repository[]> {
    const response = await apiClient.get('/repositories/search', {
      params: { query, ...filters },
    });
    return response.data;
  },
};

// Release API
export const releaseAPI = {
  // 获取所有 releases
  async getAll(): Promise<Release[]> {
    const response = await apiClient.get('/releases');
    return response.data;
  },

  // 获取单个 release
  async getById(id: number): Promise<Release> {
    const response = await apiClient.get(`/releases/${id}`);
    return response.data;
  },

  // 获取仓库的 releases
  async getByRepository(repositoryId: number): Promise<Release[]> {
    const response = await apiClient.get(`/repositories/${repositoryId}/releases`);
    return response.data;
  },

  // 订阅 release
  async subscribe(releaseId: number): Promise<void> {
    await apiClient.post(`/releases/${releaseId}/subscribe`);
  },

  // 取消订阅 release
  async unsubscribe(releaseId: number): Promise<void> {
    await apiClient.delete(`/releases/${releaseId}/subscribe`);
  },

  // 标记为已读
  async markAsRead(releaseId: number): Promise<void> {
    await apiClient.post(`/releases/${releaseId}/read`);
  },

  // 同步 releases
  async sync(repositoryId: number): Promise<Release[]> {
    const response = await apiClient.post(`/repositories/${repositoryId}/releases/sync`);
    return response.data;
  },
};

// AI 配置 API
export const aiConfigAPI = {
  // 获取所有配置
  async getAll(): Promise<AIConfig[]> {
    const response = await apiClient.get('/ai-configs');
    return response.data;
  },

  // 创建配置
  async create(data: Partial<AIConfig>): Promise<AIConfig> {
    const response = await apiClient.post('/ai-configs', data);
    return response.data;
  },

  // 更新配置
  async update(id: number, data: Partial<AIConfig>): Promise<AIConfig> {
    const response = await apiClient.patch(`/ai-configs/${id}`, data);
    return response.data;
  },

  // 删除配置
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/ai-configs/${id}`);
  },

  // 测试配置
  async test(id: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`/ai-configs/${id}/test`);
    return response.data;
  },

  // 生成仓库摘要
  async generateSummary(repositoryId: number): Promise<{ summary: string; tags: string[] }> {
    const response = await apiClient.post(`/repositories/${repositoryId}/ai-summary`);
    return response.data;
  },
};

// WebDAV 配置 API
export const webdavConfigAPI = {
  // 获取所有配置
  async getAll(): Promise<WebDAVConfig[]> {
    const response = await apiClient.get('/webdav-configs');
    return response.data;
  },

  // 创建配置
  async create(data: Partial<WebDAVConfig>): Promise<WebDAVConfig> {
    const response = await apiClient.post('/webdav-configs', data);
    return response.data;
  },

  // 更新配置
  async update(id: number, data: Partial<WebDAVConfig>): Promise<WebDAVConfig> {
    const response = await apiClient.patch(`/webdav-configs/${id}`, data);
    return response.data;
  },

  // 删除配置
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/webdav-configs/${id}`);
  },

  // 测试连接
  async test(id: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`/webdav-configs/${id}/test`);
    return response.data;
  },

  // 备份数据
  async backup(id: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`/webdav-configs/${id}/backup`);
    return response.data;
  },

  // 恢复数据
  async restore(id: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`/webdav-configs/${id}/restore`);
    return response.data;
  },
};

export default {
  github: githubAPI,
  repositories: repositoryAPI,
  releases: releaseAPI,
  aiConfigs: aiConfigAPI,
  webdavConfigs: webdavConfigAPI,
};
