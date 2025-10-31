/**
 * 数据库实体类型定义
 */

import { BaseEntity } from './base_dao';

// =============================================================================
// 用户相关类型
// =============================================================================

export interface User extends BaseEntity {
  id?: number;
  github_id: number;
  username: string;
  name?: string;
  email?: string;
  avatar_url?: string;
  github_token_encrypted?: string;
  is_authenticated: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateUserData {
  github_id: number;
  username: string;
  name?: string;
  email?: string;
  avatar_url?: string;
  github_token_encrypted?: string;
  is_authenticated?: boolean;
}

// =============================================================================
// 仓库相关类型
// =============================================================================

export interface Repository extends BaseEntity {
  id?: number;
  github_id: number;
  owner: string;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  clone_url?: string;
  ssh_url?: string;
  language?: string;
  languages?: string; // JSON
  topics?: string; // JSON
  stars_count: number;
  forks_count: number;
  watchers_count: number;
  open_issues_count: number;
  size_kb: number;
  license?: string;
  default_branch?: string;
  archived: boolean;
  disabled: boolean;
  first_seen_at?: string;
  last_updated_at?: string;
  user_notes?: string;
  user_rating?: number;
  is_private: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateRepositoryData {
  github_id: number;
  owner: string;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  clone_url?: string;
  ssh_url?: string;
  language?: string;
  languages?: string;
  topics?: string;
  stars_count?: number;
  forks_count?: number;
  watchers_count?: number;
  open_issues_count?: number;
  size_kb?: number;
  license?: string;
  default_branch?: string;
  archived?: boolean;
  disabled?: boolean;
  user_notes?: string;
  user_rating?: number;
  is_private?: boolean;
}

export interface UpdateRepositoryData {
  description?: string;
  language?: string;
  languages?: string;
  topics?: string;
  stars_count?: number;
  forks_count?: number;
  watchers_count?: number;
  open_issues_count?: number;
  size_kb?: number;
  license?: string;
  default_branch?: string;
  archived?: boolean;
  disabled?: boolean;
  last_updated_at?: string;
  user_notes?: string;
  user_rating?: number;
  is_private?: boolean;
}

export interface RepositorySearchParams extends SearchParams {
  language?: string;
  owner?: string;
  stars_min?: number;
  stars_max?: number;
  archived?: boolean;
  disabled?: boolean;
  is_private?: boolean;
  user_rating?: number;
}

// =============================================================================
// AI 分析结果类型
// =============================================================================

export interface AIAnalysisResult extends BaseEntity {
  id?: number;
  repository_id: number;
  analysis_type: 'summary' | 'category' | 'tags' | 'platform_support' | 'review';
  ai_model: string;
  input_prompt: string;
  analysis_result: string; // JSON
  confidence_score?: number;
  tokens_used: number;
  processing_time_ms: number;
  is_validated: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAIAnalysisResultData {
  repository_id: number;
  analysis_type: 'summary' | 'category' | 'tags' | 'platform_support' | 'review';
  ai_model: string;
  input_prompt: string;
  analysis_result: string;
  confidence_score?: number;
  tokens_used?: number;
  processing_time_ms?: number;
  is_validated?: boolean;
}

export interface AIAnalysisSearchParams extends SearchParams {
  repository_id?: number;
  analysis_type?: string;
  ai_model?: string;
  is_validated?: boolean;
  confidence_min?: number;
  confidence_max?: number;
}

// =============================================================================
// 分类相关类型
// =============================================================================

export interface Category extends BaseEntity {
  id?: number;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  is_default: boolean;
  sort_order: number;
  parent_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateCategoryData {
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  is_default?: boolean;
  sort_order?: number;
  parent_id?: number;
}

export interface UpdateCategoryData {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  is_default?: boolean;
  sort_order?: number;
  parent_id?: number;
}

export interface CategorySearchParams extends SearchParams {
  is_default?: boolean;
  parent_id?: number;
}

// =============================================================================
// 仓库分类关联类型
// =============================================================================

export interface RepositoryCategory extends BaseEntity {
  id?: number;
  repository_id: number;
  category_id: number;
  confidence?: number;
  is_auto_generated: boolean;
  created_at?: string;
}

export interface CreateRepositoryCategoryData {
  repository_id: number;
  category_id: number;
  confidence?: number;
  is_auto_generated?: boolean;
}

export interface RepositoryCategorySearchParams extends SearchParams {
  repository_id?: number;
  category_id?: number;
  is_auto_generated?: boolean;
}

// =============================================================================
// Release 相关类型
// =============================================================================

export interface Release extends BaseEntity {
  id?: number;
  github_release_id: number;
  repository_id: number;
  tag_name: string;
  name?: string;
  body?: string;
  draft: boolean;
  prerelease: boolean;
  created_at?: string;
  published_at?: string;
  html_url: string;
  zipball_url?: string;
  tarball_url?: string;
  target_commitish?: string;
  author_login?: string;
  author_avatar_url?: string;
  is_subscribed: boolean;
  is_read: boolean;
  user_notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateReleaseData {
  github_release_id: number;
  repository_id: number;
  tag_name: string;
  name?: string;
  body?: string;
  draft?: boolean;
  prerelease?: boolean;
  created_at?: string;
  published_at?: string;
  html_url: string;
  zipball_url?: string;
  tarball_url?: string;
  target_commitish?: string;
  author_login?: string;
  author_avatar_url?: string;
  is_subscribed?: boolean;
  is_read?: boolean;
  user_notes?: string;
}

export interface ReleaseSearchParams extends SearchParams {
  repository_id?: number;
  draft?: boolean;
  prerelease?: boolean;
  is_subscribed?: boolean;
  is_read?: boolean;
  tag_name?: string;
  published_after?: string;
  published_before?: string;
}

// =============================================================================
// Release 资产类型
// =============================================================================

export interface ReleaseAsset extends BaseEntity {
  id?: number;
  github_asset_id: number;
  release_id: number;
  name: string;
  label?: string;
  content_type?: string;
  size_bytes: number;
  download_count: number;
  browser_download_url: string;
  created_at?: string;
  is_downloaded: boolean;
  local_path?: string;
  download_time?: string;
  file_hash?: string;
  user_notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateReleaseAssetData {
  github_asset_id: number;
  release_id: number;
  name: string;
  label?: string;
  content_type?: string;
  size_bytes: number;
  download_count?: number;
  browser_download_url: string;
  created_at?: string;
  is_downloaded?: boolean;
  local_path?: string;
  download_time?: string;
  file_hash?: string;
  user_notes?: string;
}

export interface ReleaseAssetSearchParams extends SearchParams {
  release_id?: number;
  is_downloaded?: boolean;
  size_min?: number;
  size_max?: number;
  content_type?: string;
}

// =============================================================================
// 过滤器相关类型
// =============================================================================

export interface AssetFilter extends BaseEntity {
  id?: number;
  name: string;
  description?: string;
  keywords: string; // JSON
  match_type: 'keyword' | 'regex' | 'extension';
  case_sensitive: boolean;
  is_active: boolean;
  sort_order: number;
  user_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAssetFilterData {
  name: string;
  description?: string;
  keywords: string;
  match_type?: 'keyword' | 'regex' | 'extension';
  case_sensitive?: boolean;
  is_active?: boolean;
  sort_order?: number;
  user_id?: number;
}

export interface AssetFilterSearchParams extends SearchParams {
  is_active?: boolean;
  match_type?: string;
  user_id?: number;
}

// =============================================================================
// 过滤器匹配记录类型
// =============================================================================

export interface FilterMatch extends BaseEntity {
  id?: number;
  filter_id: number;
  asset_id: number;
  match_score?: number;
  matched_keywords?: string; // JSON
  created_at?: string;
}

export interface CreateFilterMatchData {
  filter_id: number;
  asset_id: number;
  match_score?: number;
  matched_keywords?: string;
}

export interface FilterMatchSearchParams extends SearchParams {
  filter_id?: number;
  asset_id?: number;
  match_score_min?: number;
  match_score_max?: number;
}

// =============================================================================
// 配置相关类型
// =============================================================================

export interface AIConfig extends BaseEntity {
  id?: number;
  name: string;
  api_url: string;
  api_key_encrypted?: string;
  model_name: string;
  max_tokens?: number;
  temperature?: number;
  timeout_seconds?: number;
  is_active: boolean;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAIConfigData {
  name: string;
  api_url: string;
  api_key_encrypted?: string;
  model_name: string;
  max_tokens?: number;
  temperature?: number;
  timeout_seconds?: number;
  is_active?: boolean;
  is_default?: boolean;
}

export interface WebDAVConfig extends BaseEntity {
  id?: number;
  name: string;
  server_url: string;
  username?: string;
  password_encrypted?: string;
  remote_path?: string;
  is_active: boolean;
  is_default: boolean;
  last_sync_at?: string;
  sync_status?: 'success' | 'failed' | 'in_progress';
  error_message?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateWebDAVConfigData {
  name: string;
  server_url: string;
  username?: string;
  password_encrypted?: string;
  remote_path?: string;
  is_active?: boolean;
  is_default?: boolean;
}

// =============================================================================
// 同步日志类型
// =============================================================================

export interface SyncLog extends BaseEntity {
  id?: number;
  sync_type: 'repositories' | 'releases' | 'backup' | 'ai_analysis';
  status: 'started' | 'success' | 'failed' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  items_processed: number;
  items_added: number;
  items_updated: number;
  items_deleted: number;
  error_message?: string;
  execution_time_ms?: number;
  user_id?: number;
  created_at?: string;
}

export interface CreateSyncLogData {
  sync_type: 'repositories' | 'releases' | 'backup' | 'ai_analysis';
  status?: 'started' | 'success' | 'failed' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  items_processed?: number;
  items_added?: number;
  items_updated?: number;
  items_deleted?: number;
  error_message?: string;
  execution_time_ms?: number;
  user_id?: number;
}

export interface SyncLogSearchParams extends SearchParams {
  sync_type?: string;
  status?: string;
  user_id?: number;
  started_after?: string;
  started_before?: string;
}

// =============================================================================
// 搜索索引类型
// =============================================================================

export interface SearchIndex extends BaseEntity {
  id?: number;
  entity_type: 'repository' | 'release' | 'asset' | 'ai_analysis';
  entity_id: number;
  content_type: 'name' | 'description' | 'summary' | 'tags' | 'body' | 'result';
  content_text: string;
  language?: string;
  keywords?: string; // JSON
  embedding_vector?: Buffer;
  created_at?: string;
  updated_at?: string;
}

export interface CreateSearchIndexData {
  entity_type: 'repository' | 'release' | 'asset' | 'ai_analysis';
  entity_id: number;
  content_type: 'name' | 'description' | 'summary' | 'tags' | 'body' | 'result';
  content_text: string;
  language?: string;
  keywords?: string;
  embedding_vector?: Buffer;
}

export interface SearchIndexSearchParams extends SearchParams {
  entity_type?: string;
  entity_id?: number;
  content_type?: string;
  language?: string;
}

// =============================================================================
// 应用设置类型
// =============================================================================

export interface AppSetting extends BaseEntity {
  id?: number;
  setting_key: string;
  setting_value?: string; // JSON
  data_type: 'string' | 'number' | 'boolean' | 'json';
  description?: string;
  is_encrypted: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAppSettingData {
  setting_key: string;
  setting_value?: string;
  data_type?: 'string' | 'number' | 'boolean' | 'json';
  description?: string;
  is_encrypted?: boolean;
}

export interface UpdateAppSettingData {
  setting_value?: string;
  description?: string;
  is_encrypted?: boolean;
}

// =============================================================================
// 辅助类型
// =============================================================================

export interface SearchParams {
  query?: string;
  searchFields?: string[];
}

// 用于 JSON 字段的类型守卫
export function isJSONField(field: string): boolean {
  const jsonFields = [
    'languages', 'topics', 'analysis_result', 'keywords', 
    'setting_value', 'keywords', 'matched_keywords', 'keywords'
  ];
  return jsonFields.includes(field);
}

// 解析 JSON 字段
export function parseJSONField<T>(value: string | null): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

// 序列化 JSON 字段
export function stringifyJSONField(value: any): string | null {
  if (value === null || value === undefined) return null;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
