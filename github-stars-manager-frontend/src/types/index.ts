// GitHub 用户类型
export interface GitHubUser {
  id: number;
  login: string;
  name: string | null;
  email: string | null;
  avatar_url: string;
  html_url: string;
  bio: string | null;
  public_repos: number;
  followers: number;
  following: number;
}

// 仓库类型
export interface Repository {
  id: number;
  github_id: number;
  owner: string;
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  clone_url: string;
  ssh_url: string;
  language: string | null;
  languages: Record<string, number> | null;
  topics: string[];
  stars_count: number;
  forks_count: number;
  watchers_count: number;
  open_issues_count: number;
  size_kb: number;
  license: string | null;
  default_branch: string;
  archived: boolean;
  disabled: boolean;
  is_private: boolean;
  user_notes: string | null;
  user_rating: number | null;
  first_seen_at: string;
  last_updated_at: string;
  created_at: string;
  updated_at: string;
  ai_summary?: string;
  ai_tags?: string[];
  categories?: Category[];
}

// AI 分析结果
export interface AIAnalysisResult {
  id: number;
  repository_id: number;
  analysis_type: 'summary' | 'category' | 'tags' | 'platform_support';
  ai_model: string;
  input_prompt: string;
  analysis_result: any;
  confidence_score: number | null;
  tokens_used: number;
  processing_time_ms: number;
  is_validated: boolean;
  created_at: string;
  updated_at: string;
}

// 分类类型
export interface Category {
  id: number;
  name: string;
  description: string | null;
  color: string;
  icon: string | null;
  is_default: boolean;
  sort_order: number;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}

// Release 类型
export interface Release {
  id: number;
  github_release_id: number;
  repository_id: number;
  tag_name: string;
  name: string | null;
  body: string | null;
  draft: boolean;
  prerelease: boolean;
  created_at: string;
  published_at: string;
  html_url: string;
  zipball_url: string;
  tarball_url: string;
  target_commitish: string;
  author_login: string;
  author_avatar_url: string;
  is_subscribed: boolean;
  is_read: boolean;
  user_notes: string | null;
  updated_at: string;
  assets: ReleaseAsset[];
  repository?: Repository;
}

// Release 资产
export interface ReleaseAsset {
  id: number;
  github_asset_id: number;
  release_id: number;
  name: string;
  label: string | null;
  content_type: string;
  size_bytes: number;
  download_count: number;
  browser_download_url: string;
  created_at: string;
  is_downloaded: boolean;
  local_path: string | null;
  download_time: string | null;
  file_hash: string | null;
  user_notes: string | null;
  updated_at: string;
}

// 资产过滤器
export interface AssetFilter {
  id: number;
  name: string;
  description: string | null;
  keywords: string[];
  match_type: 'keyword' | 'regex' | 'extension';
  case_sensitive: boolean;
  is_active: boolean;
  sort_order: number;
  user_id: number | null;
  created_at: string;
  updated_at: string;
}

// AI 配置
export interface AIConfig {
  id: number;
  name: string;
  api_url: string;
  api_key: string;
  model_name: string;
  max_tokens: number;
  temperature: number;
  timeout_seconds: number;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// WebDAV 配置
export interface WebDAVConfig {
  id: number;
  name: string;
  server_url: string;
  username: string;
  password: string;
  remote_path: string;
  is_active: boolean;
  is_default: boolean;
  last_sync_at: string | null;
  sync_status: 'success' | 'failed' | 'in_progress' | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// 同步日志
export interface SyncLog {
  id: number;
  sync_type: 'repositories' | 'releases' | 'backup';
  status: 'started' | 'success' | 'failed' | 'cancelled';
  started_at: string;
  completed_at: string | null;
  items_processed: number;
  items_added: number;
  items_updated: number;
  items_deleted: number;
  error_message: string | null;
  execution_time_ms: number | null;
  user_id: number | null;
}

// 搜索过滤器
export interface SearchFilters {
  query: string;
  language: string | null;
  category: string | null;
  tags: string[];
  sortBy: 'stars' | 'updated' | 'name' | 'created';
  sortOrder: 'asc' | 'desc';
  showArchived: boolean;
}

// 应用设置
export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  language: 'zh' | 'en';
  autoSync: boolean;
  syncInterval: number;
  enableNotifications: boolean;
}
