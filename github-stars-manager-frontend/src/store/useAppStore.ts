import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  GitHubUser,
  Repository,
  Release,
  Category,
  AIConfig,
  WebDAVConfig,
  AssetFilter,
  SearchFilters,
  AppSettings,
} from '@/types';

interface AppState {
  // 用户状态
  user: GitHubUser | null;
  githubToken: string | null;
  isAuthenticated: boolean;

  // 仓库数据
  repositories: Repository[];
  searchResults: Repository[];
  selectedRepository: Repository | null;

  // Release 数据
  releases: Release[];
  releaseSubscriptions: Set<number>;
  readReleases: Set<number>;

  // 分类数据
  customCategories: Category[];
  defaultCategories: Category[];

  // 过滤器
  assetFilters: AssetFilter[];
  activeFilters: number[];

  // AI 配置
  aiConfigs: AIConfig[];
  activeAIConfig: number | null;

  // WebDAV 配置
  webdavConfigs: WebDAVConfig[];
  activeWebDAVConfig: number | null;

  // 搜索过滤器
  searchFilters: SearchFilters;

  // 应用设置
  settings: AppSettings;

  // 同步状态
  lastSync: string | null;
  lastBackup: string | null;
  isSyncing: boolean;

  // Actions
  setUser: (user: GitHubUser | null) => void;
  setGithubToken: (token: string | null) => void;
  setAuthenticated: (authenticated: boolean) => void;
  logout: () => void;

  setRepositories: (repositories: Repository[]) => void;
  addRepository: (repository: Repository) => void;
  updateRepository: (id: number, updates: Partial<Repository>) => void;
  deleteRepository: (id: number) => void;

  setSearchResults: (results: Repository[]) => void;
  setSelectedRepository: (repository: Repository | null) => void;

  setReleases: (releases: Release[]) => void;
  addRelease: (release: Release) => void;
  updateRelease: (id: number, updates: Partial<Release>) => void;
  subscribeToRelease: (releaseId: number) => void;
  unsubscribeFromRelease: (releaseId: number) => void;
  markReleaseAsRead: (releaseId: number) => void;

  setCustomCategories: (categories: Category[]) => void;
  addCategory: (category: Category) => void;
  updateCategory: (id: number, updates: Partial<Category>) => void;
  deleteCategory: (id: number) => void;

  setAssetFilters: (filters: AssetFilter[]) => void;
  addAssetFilter: (filter: AssetFilter) => void;
  updateAssetFilter: (id: number, updates: Partial<AssetFilter>) => void;
  deleteAssetFilter: (id: number) => void;
  toggleFilterActive: (filterId: number) => void;

  setAIConfigs: (configs: AIConfig[]) => void;
  addAIConfig: (config: AIConfig) => void;
  updateAIConfig: (id: number, updates: Partial<AIConfig>) => void;
  deleteAIConfig: (id: number) => void;
  setActiveAIConfig: (id: number | null) => void;

  setWebDAVConfigs: (configs: WebDAVConfig[]) => void;
  addWebDAVConfig: (config: WebDAVConfig) => void;
  updateWebDAVConfig: (id: number, updates: Partial<WebDAVConfig>) => void;
  deleteWebDAVConfig: (id: number) => void;
  setActiveWebDAVConfig: (id: number | null) => void;

  setSearchFilters: (filters: Partial<SearchFilters>) => void;
  resetSearchFilters: () => void;

  updateSettings: (settings: Partial<AppSettings>) => void;

  setLastSync: (date: string) => void;
  setLastBackup: (date: string) => void;
  setIsSyncing: (syncing: boolean) => void;
}

const defaultSearchFilters: SearchFilters = {
  query: '',
  language: null,
  category: null,
  tags: [],
  sortBy: 'updated',
  sortOrder: 'desc',
  showArchived: false,
};

const defaultSettings: AppSettings = {
  theme: 'system',
  language: 'zh',
  autoSync: false,
  syncInterval: 3600,
  enableNotifications: true,
};

const defaultCategories: Category[] = [
  { id: 1, name: '前端开发', description: '前端相关技术和框架', color: '#3B82F6', icon: 'Code', is_default: true, sort_order: 1, parent_id: null, created_at: '', updated_at: '' },
  { id: 2, name: '后端开发', description: '后端相关技术和框架', color: '#10B981', icon: 'Server', is_default: true, sort_order: 2, parent_id: null, created_at: '', updated_at: '' },
  { id: 3, name: '数据库', description: '数据库相关技术', color: '#F59E0B', icon: 'Database', is_default: true, sort_order: 3, parent_id: null, created_at: '', updated_at: '' },
  { id: 4, name: '工具', description: '开发工具和实用工具', color: '#8B5CF6', icon: 'Wrench', is_default: true, sort_order: 4, parent_id: null, created_at: '', updated_at: '' },
  { id: 5, name: 'AI/ML', description: '人工智能和机器学习', color: '#EC4899', icon: 'Brain', is_default: true, sort_order: 5, parent_id: null, created_at: '', updated_at: '' },
];

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      githubToken: null,
      isAuthenticated: false,

      repositories: [],
      searchResults: [],
      selectedRepository: null,

      releases: [],
      releaseSubscriptions: new Set(),
      readReleases: new Set(),

      customCategories: [],
      defaultCategories,

      assetFilters: [],
      activeFilters: [],

      aiConfigs: [],
      activeAIConfig: null,

      webdavConfigs: [],
      activeWebDAVConfig: null,

      searchFilters: defaultSearchFilters,
      settings: defaultSettings,

      lastSync: null,
      lastBackup: null,
      isSyncing: false,

      // Actions
      setUser: (user) => set({ user }),
      setGithubToken: (token) => set({ githubToken: token }),
      setAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),
      logout: () => set({
        user: null,
        githubToken: null,
        isAuthenticated: false,
        repositories: [],
        searchResults: [],
        releases: [],
      }),

      setRepositories: (repositories) => set({ 
        repositories,
        searchResults: repositories,
      }),
      addRepository: (repository) => set((state) => ({
        repositories: [...state.repositories, repository],
      })),
      updateRepository: (id, updates) => set((state) => ({
        repositories: state.repositories.map((repo) =>
          repo.id === id ? { ...repo, ...updates } : repo
        ),
      })),
      deleteRepository: (id) => set((state) => ({
        repositories: state.repositories.filter((repo) => repo.id !== id),
      })),

      setSearchResults: (results) => set({ searchResults: results }),
      setSelectedRepository: (repository) => set({ selectedRepository: repository }),

      setReleases: (releases) => set({ releases }),
      addRelease: (release) => set((state) => ({
        releases: [...state.releases, release],
      })),
      updateRelease: (id, updates) => set((state) => ({
        releases: state.releases.map((release) =>
          release.id === id ? { ...release, ...updates } : release
        ),
      })),
      subscribeToRelease: (releaseId) => set((state) => {
        const newSubscriptions = new Set(state.releaseSubscriptions);
        newSubscriptions.add(releaseId);
        return { releaseSubscriptions: newSubscriptions };
      }),
      unsubscribeFromRelease: (releaseId) => set((state) => {
        const newSubscriptions = new Set(state.releaseSubscriptions);
        newSubscriptions.delete(releaseId);
        return { releaseSubscriptions: newSubscriptions };
      }),
      markReleaseAsRead: (releaseId) => set((state) => {
        const newReadReleases = new Set(state.readReleases);
        newReadReleases.add(releaseId);
        return { readReleases: newReadReleases };
      }),

      setCustomCategories: (categories) => set({ customCategories: categories }),
      addCategory: (category) => set((state) => ({
        customCategories: [...state.customCategories, category],
      })),
      updateCategory: (id, updates) => set((state) => ({
        customCategories: state.customCategories.map((cat) =>
          cat.id === id ? { ...cat, ...updates } : cat
        ),
      })),
      deleteCategory: (id) => set((state) => ({
        customCategories: state.customCategories.filter((cat) => cat.id !== id),
      })),

      setAssetFilters: (filters) => set({ assetFilters: filters }),
      addAssetFilter: (filter) => set((state) => ({
        assetFilters: [...state.assetFilters, filter],
      })),
      updateAssetFilter: (id, updates) => set((state) => ({
        assetFilters: state.assetFilters.map((filter) =>
          filter.id === id ? { ...filter, ...updates } : filter
        ),
      })),
      deleteAssetFilter: (id) => set((state) => ({
        assetFilters: state.assetFilters.filter((filter) => filter.id !== id),
      })),
      toggleFilterActive: (filterId) => set((state) => {
        const activeFilters = state.activeFilters.includes(filterId)
          ? state.activeFilters.filter((id) => id !== filterId)
          : [...state.activeFilters, filterId];
        return { activeFilters };
      }),

      setAIConfigs: (configs) => set({ aiConfigs: configs }),
      addAIConfig: (config) => set((state) => ({
        aiConfigs: [...state.aiConfigs, config],
      })),
      updateAIConfig: (id, updates) => set((state) => ({
        aiConfigs: state.aiConfigs.map((config) =>
          config.id === id ? { ...config, ...updates } : config
        ),
      })),
      deleteAIConfig: (id) => set((state) => ({
        aiConfigs: state.aiConfigs.filter((config) => config.id !== id),
      })),
      setActiveAIConfig: (id) => set({ activeAIConfig: id }),

      setWebDAVConfigs: (configs) => set({ webdavConfigs: configs }),
      addWebDAVConfig: (config) => set((state) => ({
        webdavConfigs: [...state.webdavConfigs, config],
      })),
      updateWebDAVConfig: (id, updates) => set((state) => ({
        webdavConfigs: state.webdavConfigs.map((config) =>
          config.id === id ? { ...config, ...updates } : config
        ),
      })),
      deleteWebDAVConfig: (id) => set((state) => ({
        webdavConfigs: state.webdavConfigs.filter((config) => config.id !== id),
      })),
      setActiveWebDAVConfig: (id) => set({ activeWebDAVConfig: id }),

      setSearchFilters: (filters) => set((state) => ({
        searchFilters: { ...state.searchFilters, ...filters },
      })),
      resetSearchFilters: () => set({ searchFilters: defaultSearchFilters }),

      updateSettings: (settings) => set((state) => ({
        settings: { ...state.settings, ...settings },
      })),

      setLastSync: (date) => set({ lastSync: date }),
      setLastBackup: (date) => set({ lastBackup: date }),
      setIsSyncing: (syncing) => set({ isSyncing: syncing }),
    }),
    {
      name: 'github-stars-manager-storage',
      partialize: (state) => ({
        user: state.user,
        githubToken: state.githubToken,
        isAuthenticated: state.isAuthenticated,
        repositories: state.repositories,
        customCategories: state.customCategories,
        assetFilters: state.assetFilters,
        aiConfigs: state.aiConfigs,
        activeAIConfig: state.activeAIConfig,
        webdavConfigs: state.webdavConfigs,
        activeWebDAVConfig: state.activeWebDAVConfig,
        settings: state.settings,
        lastSync: state.lastSync,
        lastBackup: state.lastBackup,
        releaseSubscriptions: Array.from(state.releaseSubscriptions),
        readReleases: Array.from(state.readReleases),
        searchFilters: {
          sortBy: state.searchFilters.sortBy,
          sortOrder: state.searchFilters.sortOrder,
        },
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.releaseSubscriptions = new Set(state.releaseSubscriptions as any || []);
          state.readReleases = new Set(state.readReleases as any || []);
          state.searchResults = state.repositories;
        }
      },
    }
  )
);
