/**
 * 数据库服务使用示例
 * 演示如何使用 SQLite 数据库服务进行各种操作
 */

import { DatabaseManager } from '../database/dao/database_manager';
import { DatabaseMigrator } from '../database/migration/migrator';
import { SQLiteConnectionManager } from '../services/database_service';
import { User, Repository, Category, Release, ReleaseAsset, AssetFilter } from '../database/dao/types';

// 配置
const DATABASE_CONFIG = {
  filename: './data/github_stars_manager.db',
  walMode: true,
  cacheSize: 20000,
  synchronousMode: 'NORMAL' as const
};

class DatabaseServiceExample {
  private dbManager: DatabaseManager;
  private migrator: DatabaseMigrator;
  private db: SQLiteConnectionManager;

  constructor() {
    this.db = new SQLiteConnectionManager(DATABASE_CONFIG);
    this.dbManager = new DatabaseManager(this.db);
    this.migrator = new DatabaseMigrator(this.db);
  }

  /**
   * 初始化数据库服务
   */
  async initialize(): Promise<void> {
    try {
      console.log('🔧 正在初始化数据库服务...');
      
      // 连接数据库
      await this.db.connect();
      console.log('✅ 数据库连接成功');

      // 初始化迁移系统
      await this.migrator.initialize();
      console.log('✅ 迁移系统初始化成功');

      // 检查迁移状态
      const status = await this.migrator.getStatus();
      console.log(`📊 当前数据库版本: ${status.currentVersion}`);
      console.log(`📋 待执行迁移: ${status.pendingMigrations.length}`);

      // 如果有待执行的迁移，执行它们
      if (status.pendingMigrations.length > 0) {
        console.log('🚀 开始执行数据库迁移...');
        const results = await this.migrator.migrate();
        
        results.forEach(result => {
          if (result.success) {
            console.log(`✅ 迁移成功: ${result.migration?.version} - ${result.migration?.description}`);
          } else {
            console.log(`❌ 迁移失败: ${result.migration?.version} - ${result.error}`);
          }
        });
      }

      console.log('🎉 数据库服务初始化完成');
    } catch (error) {
      console.error('❌ 初始化数据库服务失败:', error);
      throw error;
    }
  }

  /**
   * 示例1: 用户管理
   */
  async demonstrateUserManagement(): Promise<void> {
    console.log('\n=== 示例1: 用户管理 ===');
    
    try {
      // 创建用户
      const user: Omit<User, 'id' | 'created_at' | 'updated_at'> = {
        github_id: 123456,
        username: 'john_doe',
        access_token: 'encrypted_token_here',
        email: 'john@example.com',
        avatar_url: 'https://avatars.githubusercontent.com/u/123456'
      };

      const createdUser = await this.dbManager.userDAO.create(user);
      console.log('✅ 用户创建成功:', createdUser);

      // 查找用户
      const foundUser = await this.dbManager.userDAO.findByGithubId(123456);
      console.log('✅ 用户查找成功:', foundUser);

      // 更新用户
      const updatedUser = await this.dbManager.userDAO.update(createdUser.id!, {
        email: 'john.doe@example.com'
      });
      console.log('✅ 用户更新成功:', updatedUser.username);

      // 分页查询用户
      const users = await this.dbManager.userDAO.findPaginated({
        page: 1,
        limit: 10
      });
      console.log(`✅ 用户列表 (${users.total} 个用户):`, users.data.map(u => u.username));

    } catch (error) {
      console.error('❌ 用户管理示例失败:', error);
    }
  }

  /**
   * 示例2: 仓库管理
   */
  async demonstrateRepositoryManagement(): Promise<void> {
    console.log('\n=== 示例2: 仓库管理 ===');
    
    try {
      // 创建仓库
      const repository: Omit<Repository, 'id' | 'created_at' | 'updated_at'> = {
        github_id: 654321,
        owner: 'octocat',
        name: 'Hello-World',
        full_name: 'octocat/Hello-World',
        description: '我的第一个仓库',
        html_url: 'https://github.com/octocat/Hello-World',
        clone_url: 'https://github.com/octocat/Hello-World.git',
        ssh_url: 'git@github.com:octocat/Hello-World.git',
        stars_count: 42,
        forks_count: 5,
        watchers_count: 10,
        language: 'JavaScript',
        topics: JSON.stringify(['hello-world', 'tutorial']),
        archived: false,
        disabled: false,
        private: false,
        is_starred: true
      };

      const createdRepo = await this.dbManager.repositoryDAO.create(repository);
      console.log('✅ 仓库创建成功:', createdRepo.full_name);

      // 搜索仓库
      const searchResults = await this.dbManager.repositoryDAO.searchByKeyword('Hello');
      console.log(`✅ 搜索到 ${searchResults.length} 个仓库:`, searchResults.map(r => r.full_name));

      // 按语言统计
      const statsByLanguage = await this.dbManager.repositoryDAO.getStatsByLanguage();
      console.log('✅ 按语言统计:', statsByLanguage);

    } catch (error) {
      console.error('❌ 仓库管理示例失败:', error);
    }
  }

  /**
   * 示例3: 分类管理
   */
  async demonstrateCategoryManagement(): Promise<void> {
    console.log('\n=== 示例3: 分类管理 ===');
    
    try {
      // 创建分类
      const category: Omit<Category, 'id' | 'created_at' | 'updated_at'> = {
        name: '前端框架',
        description: 'React、Vue、Angular 等前端框架',
        color: '#61dafb',
        is_default: false,
        sort_order: 1
      };

      const createdCategory = await this.dbManager.categoryDAO.create(category);
      console.log('✅ 分类创建成功:', createdCategory.name);

      // 获取默认分类
      const defaultCategory = await this.dbManager.categoryDAO.findDefault();
      console.log('✅ 默认分类:', defaultCategory?.name);

      // 为仓库分配分类
      const repositories = await this.dbManager.repositoryDAO.findAll({ limit: 1 });
      if (repositories.length > 0) {
        await this.dbManager.repositoryCategoryDAO.addCategory(
          repositories[0].id!,
          createdCategory.id!
        );
        console.log('✅ 仓库分类分配成功');
      }

    } catch (error) {
      console.error('❌ 分类管理示例失败:', error);
    }
  }

  /**
   * 示例4: 发布版本管理
   */
  async demonstrateReleaseManagement(): Promise<void> {
    console.log('\n=== 示例4: 发布版本管理 ===');
    
    try {
      // 首先获取一个仓库
      const repositories = await this.dbManager.repositoryDAO.findAll({ limit: 1 });
      if (repositories.length === 0) {
        console.log('❌ 没有可用的仓库，跳过发布版本示例');
        return;
      }

      const repository = repositories[0];

      // 创建发布版本
      const release: Omit<Release, 'id' | 'created_at' | 'updated_at'> = {
        github_id: 987654,
        repository_id: repository.id!,
        tag_name: 'v1.0.0',
        name: '第一个正式版本',
        body: '这是第一个正式版本发布',
        draft: false,
        prerelease: false,
        published_at: new Date().toISOString()
      };

      const createdRelease = await this.dbManager.releaseDAO.create(release);
      console.log('✅ 发布版本创建成功:', createdRelease.tag_name);

      // 创建发布资产
      const asset: Omit<ReleaseAsset, 'id' | 'created_at' | 'updated_at'> = {
        github_id: 111111,
        release_id: createdRelease.id!,
        name: 'release-1.0.0.zip',
        download_url: 'https://example.com/download.zip',
        size: 1024000,
        content_type: 'application/zip',
        asset_type: JSON.stringify({ type: 'source', platform: 'all' }),
        is_downloaded: false
      };

      const createdAsset = await this.dbManager.releaseAssetDAO.create(asset);
      console.log('✅ 发布资产创建成功:', createdAsset.name);

      // 查找未读发布
      const unreadReleases = await this.dbManager.releaseDAO.findUnread(10);
      console.log(`✅ 未读发布数量: ${unreadReleases.data.length}`);

    } catch (error) {
      console.error('❌ 发布版本管理示例失败:', error);
    }
  }

  /**
   * 示例5: 资产过滤器管理
   */
  async demonstrateAssetFilterManagement(): Promise<void> {
    console.log('\n=== 示例5: 资产过滤器管理 ===');
    
    try {
      // 创建资产过滤器
      const filter: Omit<AssetFilter, 'id' | 'created_at' | 'updated_at'> = {
        name: 'Windows 安装包',
        description: '匹配 Windows .exe 安装包',
        asset_type: JSON.stringify({ type: 'installer', platform: 'windows' }),
        regex_pattern: '.*\\.exe$',
        match_rules: JSON.stringify([
          { field: 'content_type', operator: 'contains', value: 'application/x-msdownload' },
          { field: 'name', operator: 'regex', value: '.*setup.*|.*installer.*' }
        ]),
        is_active: true,
        priority: 1,
        auto_download: false
      };

      const createdFilter = await this.dbManager.assetFilterDAO.create(filter);
      console.log('✅ 资产过滤器创建成功:', createdFilter.name);

      // 获取活跃过滤器
      const activeFilters = await this.dbManager.assetFilterDAO.findActive();
      console.log(`✅ 活跃过滤器数量: ${activeFilters.length}`);

      // 创建测试资产来测试过滤器
      const testAsset = {
        name: 'setup.exe',
        content_type: 'application/x-msdownload',
        size: 1024000
      };

      // 测试过滤器匹配
      const matchResult = await this.dbManager.assetFilterDAO.matchAsset(testAsset);
      console.log('✅ 过滤器匹配结果:', matchResult);

    } catch (error) {
      console.error('❌ 资产过滤器管理示例失败:', error);
    }
  }

  /**
   * 示例6: 应用设置管理
   */
  async demonstrateAppSettings(): Promise<void> {
    console.log('\n=== 示例6: 应用设置管理 ===');
    
    try {
      // 设置各种类型的配置
      await this.dbManager.appSettingDAO.setSetting('theme', 'dark', 'string', '界面主题');
      await this.dbManager.appSettingDAO.setSetting('auto_sync', true, 'boolean', '自动同步设置');
      await this.dbManager.appSettingDAO.setSetting('sync_interval', 30, 'number', '同步间隔(分钟)');
      await this.dbManager.appSettingDAO.setSetting('ui_layout', { sidebar: true, toolbar: false }, 'json', '界面布局配置');

      console.log('✅ 应用设置保存成功');

      // 读取设置
      const theme = await this.dbManager.appSettingDAO.getString('theme');
      const autoSync = await this.dbManager.appSettingDAO.getBoolean('auto_sync');
      const syncInterval = await this.dbManager.appSettingDAO.getNumber('sync_interval');
      const uiLayout = await this.dbManager.appSettingDAO.getJSON('ui_layout');

      console.log('✅ 应用设置读取成功:', {
        theme,
        autoSync,
        syncInterval,
        uiLayout
      });

    } catch (error) {
      console.error('❌ 应用设置管理示例失败:', error);
    }
  }

  /**
   * 示例7: 数据备份和恢复
   */
  async demonstrateDataBackup(): Promise<void> {
    console.log('\n=== 示例7: 数据备份和恢复 ===');
    
    try {
      // 创建备份
      const backupPath = './data/backup_' + Date.now() + '.db';
      await this.db.backup(backupPath);
      console.log('✅ 数据备份创建成功:', backupPath);

      // 获取备份信息
      const stats = await this.dbManager.repositoryDAO.getTableStats();
      console.log('✅ 数据库统计信息:', {
        总仓库数: stats.total_rows,
        最后创建: stats.last_created,
        最后更新: stats.last_updated
      });

    } catch (error) {
      console.error('❌ 数据备份示例失败:', error);
    }
  }

  /**
   * 示例8: 全文搜索
   */
  async demonstrateFullTextSearch(): Promise<void> {
    console.log('\n=== 示例8: 全文搜索 ===');
    
    try {
      // 创建测试数据
      await this.dbManager.repositoryDAO.createBatch([
        {
          github_id: 200001,
          owner: 'vuejs',
          name: 'vue',
          full_name: 'vuejs/vue',
          description: 'Vue.js 是一套用于构建用户界面的渐进式框架',
          html_url: 'https://github.com/vuejs/vue',
          stars_count: 203000,
          language: 'TypeScript',
          is_starred: true
        } as any,
        {
          github_id: 200002,
          owner: 'facebook',
          name: 'react',
          full_name: 'facebook/react',
          description: '一个用于构建用户界面的库',
          html_url: 'https://github.com/facebook/react',
          stars_count: 221000,
          language: 'JavaScript',
          is_starred: true
        } as any
      ]);

      // 搜索仓库
      const vueRepos = await this.dbManager.repositoryDAO.searchByKeyword('Vue');
      const frameworkRepos = await this.dbManager.repositoryDAO.searchByKeyword('框架');

      console.log(`✅ 搜索 "Vue" 找到 ${vueRepos.length} 个仓库`);
      console.log(`✅ 搜索 "框架" 找到 ${frameworkRepos.length} 个仓库`);

      // 搜索发布
      const releaseSearchResults = await this.dbManager.releaseDAO.searchByKeyword('版本');
      console.log(`✅ 发布搜索找到 ${releaseSearchResults.length} 个结果`);

    } catch (error) {
      console.error('❌ 全文搜索示例失败:', error);
    }
  }

  /**
   * 示例9: 事务处理
   */
  async demonstrateTransactionHandling(): Promise<void> {
    console.log('\n=== 示例9: 事务处理 ===');
    
    try {
      // 使用事务创建用户和仓库
      await this.db.executeInTransaction(async (tx) => {
        const user: Omit<User, 'id' | 'created_at' | 'updated_at'> = {
          github_id: 300001,
          username: 'transaction_user',
          access_token: 'test_token'
        };

        const createdUser = await this.dbManager.userDAO.create(user);
        console.log('✅ 事务中创建用户成功');

        const repository: Omit<Repository, 'id' | 'created_at' | 'updated_at'> = {
          github_id: 300002,
          owner: createdUser.username,
          name: 'transaction_repo',
          full_name: `${createdUser.username}/transaction_repo`,
          html_url: `https://github.com/${createdUser.username}/transaction_repo`,
          is_starred: true
        };

        const createdRepo = await this.dbManager.repositoryDAO.create(repository);
        console.log('✅ 事务中创建仓库成功');

        return { user: createdUser, repository: createdRepo };
      });

      console.log('✅ 事务执行成功');

    } catch (error) {
      console.error('❌ 事务处理示例失败:', error);
    }
  }

  /**
   * 示例10: 数据库维护
   */
  async demonstrateDatabaseMaintenance(): Promise<void> {
    console.log('\n=== 示例10: 数据库维护 ===');
    
    try {
      // 获取数据库统计信息
      const stats = await this.db.getMetrics();
      console.log('✅ 数据库性能指标:', stats);

      // 清理过期数据（模拟）
      const expiredAssets = await this.dbManager.releaseAssetDAO.findExpiredAssets(30); // 30天前
      console.log(`✅ 找到 ${expiredAssets.length} 个过期资产`);

      // 优化数据库
      await this.db.optimize();
      console.log('✅ 数据库优化完成');

    } catch (error) {
      console.error('❌ 数据库维护示例失败:', error);
    }
  }

  /**
   * 运行所有示例
   */
  async runAllExamples(): Promise<void> {
    try {
      await this.initialize();
      
      await this.demonstrateUserManagement();
      await this.demonstrateRepositoryManagement();
      await this.demonstrateCategoryManagement();
      await this.demonstrateReleaseManagement();
      await this.demonstrateAssetFilterManagement();
      await this.demonstrateAppSettings();
      await this.demonstrateDataBackup();
      await this.demonstrateFullTextSearch();
      await this.demonstrateTransactionHandling();
      await this.demonstrateDatabaseMaintenance();

      console.log('\n🎉 所有示例执行完成！');
      
    } catch (error) {
      console.error('❌ 执行示例失败:', error);
    } finally {
      // 关闭数据库连接
      if (this.db) {
        await this.db.close();
        console.log('✅ 数据库连接已关闭');
      }
    }
  }

  /**
   * 清理测试数据
   */
  async cleanupTestData(): Promise<void> {
    try {
      console.log('🧹 清理测试数据...');
      
      await this.dbManager.userDAO.truncate();
      await this.dbManager.repositoryDAO.truncate();
      await this.dbManager.categoryDAO.truncate();
      await this.dbManager.releaseDAO.truncate();
      await this.dbManager.releaseAssetDAO.truncate();
      await this.dbManager.assetFilterDAO.truncate();
      await this.dbManager.aiConfigDAO.truncate();
      await this.dbManager.webdavConfigDAO.truncate();
      await this.dbManager.appSettingDAO.truncate();

      console.log('✅ 测试数据清理完成');
    } catch (error) {
      console.error('❌ 清理测试数据失败:', error);
    }
  }

  /**
   * 获取数据库使用统计
   */
  async getDatabaseStats(): Promise<any> {
    try {
      const stats = {
        users: await this.dbManager.userDAO.count(),
        repositories: await this.dbManager.repositoryDAO.count(),
        categories: await this.dbManager.categoryDAO.count(),
        releases: await this.dbManager.releaseDAO.count(),
        releaseAssets: await this.dbManager.releaseAssetDAO.count(),
        assetFilters: await this.dbManager.assetFilterDAO.count(),
        aiConfigs: await this.dbManager.aiConfigDAO.count(),
        webdavConfigs: await this.dbManager.webdavConfigDAO.count(),
        appSettings: await this.dbManager.appSettingDAO.count()
      };

      return stats;
    } catch (error) {
      console.error('❌ 获取数据库统计失败:', error);
      return {};
    }
  }
}

// 使用示例
async function main() {
  const example = new DatabaseServiceExample();
  
  console.log('🚀 开始数据库服务示例演示');
  
  try {
    await example.runAllExamples();
  } catch (error) {
    console.error('❌ 示例执行失败:', error);
  }
}

// 如果直接运行此文件，执行示例
if (require.main === module) {
  main().catch(console.error);
}

export { DatabaseServiceExample };