import type { Repository } from '@/types';

const GITHUB_API_BASE = 'https://api.github.com';

export interface GitHubAPIOptions {
  token: string;
}

export class GitHubAPI {
  private token: string;

  constructor(options: GitHubAPIOptions) {
    this.token = options.token;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${GITHUB_API_BASE}${endpoint}`, {
      ...options,
      headers: {
        Authorization: `token ${this.token}`,
        Accept: 'application/vnd.github.v3+json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // 获取当前用户信息
  async getUser() {
    return this.request('/user');
  }

  // 获取星标仓库
  async getStarredRepos(page = 1, perPage = 30): Promise<any[]> {
    return this.request(
      `/user/starred?page=${page}&per_page=${perPage}&sort=updated&direction=desc`
    );
  }

  // 获取所有星标仓库（分页加载）
  async getAllStarredRepos(onProgress?: (current: number) => void): Promise<any[]> {
    let allRepos: any[] = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const repos: any[] = await this.getStarredRepos(page, 100);
      if (repos.length === 0) {
        hasMore = false;
      } else {
        allRepos = allRepos.concat(repos);
        if (onProgress) {
          onProgress(allRepos.length);
        }
        page++;
      }
    }

    return allRepos;
  }

  // 获取仓库详情
  async getRepository(owner: string, repo: string) {
    return this.request(`/repos/${owner}/${repo}`);
  }

  // 获取仓库的 Releases
  async getRepositoryReleases(owner: string, repo: string, page = 1, perPage = 10): Promise<any[]> {
    return this.request(`/repos/${owner}/${repo}/releases?page=${page}&per_page=${perPage}`);
  }

  // 获取所有 Releases
  async getAllRepositoryReleases(owner: string, repo: string): Promise<any[]> {
    let allReleases: any[] = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const releases: any[] = await this.getRepositoryReleases(owner, repo, page, 100);
      if (releases.length === 0) {
        hasMore = false;
      } else {
        allReleases = allReleases.concat(releases);
        page++;
      }
    }

    return allReleases;
  }

  // 获取速率限制信息
  async getRateLimit() {
    return this.request('/rate_limit');
  }

  // 搜索仓库
  async searchRepositories(query: string, page = 1, perPage = 30) {
    return this.request(
      `/search/repositories?q=${encodeURIComponent(query)}&page=${page}&per_page=${perPage}`
    );
  }
}

// 转换 GitHub API 仓库数据为应用内部格式
export function transformGitHubRepo(githubRepo: any): Partial<Repository> {
  return {
    github_id: githubRepo.id,
    owner: githubRepo.owner.login,
    name: githubRepo.name,
    full_name: githubRepo.full_name,
    description: githubRepo.description,
    html_url: githubRepo.html_url,
    clone_url: githubRepo.clone_url,
    ssh_url: githubRepo.ssh_url,
    language: githubRepo.language,
    topics: githubRepo.topics || [],
    stars_count: githubRepo.stargazers_count,
    forks_count: githubRepo.forks_count,
    watchers_count: githubRepo.watchers_count,
    open_issues_count: githubRepo.open_issues_count,
    size_kb: githubRepo.size,
    license: githubRepo.license?.spdx_id || null,
    default_branch: githubRepo.default_branch,
    archived: githubRepo.archived,
    disabled: githubRepo.disabled,
    is_private: githubRepo.private,
    first_seen_at: new Date().toISOString(),
    last_updated_at: githubRepo.updated_at,
    created_at: githubRepo.created_at || new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

// 转换 Release 数据
export function transformGitHubRelease(githubRelease: any, repositoryId: number) {
  return {
    github_release_id: githubRelease.id,
    repository_id: repositoryId,
    tag_name: githubRelease.tag_name,
    name: githubRelease.name,
    body: githubRelease.body,
    draft: githubRelease.draft,
    prerelease: githubRelease.prerelease,
    created_at: githubRelease.created_at,
    published_at: githubRelease.published_at,
    html_url: githubRelease.html_url,
    zipball_url: githubRelease.zipball_url,
    tarball_url: githubRelease.tarball_url,
    target_commitish: githubRelease.target_commitish,
    author_login: githubRelease.author?.login || null,
    author_avatar_url: githubRelease.author?.avatar_url || null,
    is_subscribed: false,
    is_read: false,
    user_notes: null,
    updated_at: new Date().toISOString(),
    assets: (githubRelease.assets || []).map((asset: any) => ({
      github_asset_id: asset.id,
      release_id: 0, // Will be set after release is created
      name: asset.name,
      label: asset.label,
      content_type: asset.content_type,
      size_bytes: asset.size,
      download_count: asset.download_count,
      browser_download_url: asset.browser_download_url,
      created_at: asset.created_at,
      is_downloaded: false,
      local_path: null,
      download_time: null,
      file_hash: null,
      user_notes: null,
      updated_at: new Date().toISOString(),
    })),
  };
}
