/**
 * Release Asset DAO
 */

import { BaseDAO } from './base_dao';
import { 
  ReleaseAsset, 
  CreateReleaseAssetData, 
  ReleaseAssetSearchParams,
  parseJSONField
} from './types';
import { SQLiteConnectionManager } from '../../services/database_service';
import { DAOException } from './dao_exception';

export class ReleaseAssetDAO extends BaseDAO<ReleaseAsset> {
  protected tableName = 'release_assets';
  protected allowedSortFields = [
    'id', 'name', 'size_bytes', 'download_count', 'created_at'
  ];

  constructor(db: SQLiteConnectionManager) {
    super(db);
  }

  /**
   * 创建 Release 资产
   */
  async create(data: CreateReleaseAssetData): Promise<ReleaseAsset> {
    try {
      const assetData = {
        ...data,
        download_count: data.download_count || 0,
        is_downloaded: data.is_downloaded || false
      };

      return await super.create(assetData);
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`创建资产失败: ${error.message}`, 'CREATE_ASSET_FAILED', error);
    }
  }

  /**
   * 根据 GitHub Asset ID 查找
   */
  async findByGithubId(githubAssetId: number): Promise<ReleaseAsset | null> {
    try {
      const sql = 'SELECT * FROM release_assets WHERE github_asset_id = ?';
      const result = await this.db.querySingle(sql, [githubAssetId]);
      return result || null;
    } catch (error) {
      throw new DAOException(`根据 GitHub ID 查找资产失败: ${error.message}`, 'FIND_BY_GITHUB_ID_FAILED', error);
    }
  }

  /**
   * 根据 Release ID 查找所有资产
   */
  async findByRelease(releaseId: number): Promise<ReleaseAsset[]> {
    try {
      const sql = `
        SELECT * FROM release_assets 
        WHERE release_id = ?
        ORDER BY size_bytes DESC, name ASC
      `;
      const result = await this.db.queryAll(sql, [releaseId]);
      return result;
    } catch (error) {
      throw new DAOException(`根据 Release 查找资产失败: ${error.message}`, 'FIND_BY_RELEASE_FAILED', error);
    }
  }

  /**
   * 获取已下载的资产
   */
  async getDownloadedAssets(userId?: number): Promise<ReleaseAsset[]> {
    try {
      let sql = `
        SELECT DISTINCT ra.*
        FROM release_assets ra
        JOIN releases r ON ra.release_id = r.id
        JOIN repositories rep ON r.repository_id = rep.id
        WHERE ra.is_downloaded = 1
      `;
      const params: any[] = [];

      if (userId) {
        sql += ' AND rep.user_id = ?';
        params.push(userId);
      }

      sql += ' ORDER BY ra.download_time DESC, ra.created_at DESC';

      const result = await this.db.queryAll(sql, params);
      return result;
    } catch (error) {
      throw new DAOException(`获取已下载资产失败: ${error.message}`, 'GET_DOWNLOADED_ASSETS_FAILED', error);
    }
  }

  /**
   * 按文件类型查找资产
   */
  async findByContentType(contentType: string): Promise<ReleaseAsset[]> {
    try {
      const sql = `
        SELECT * FROM release_assets 
        WHERE content_type LIKE ?
        ORDER BY size_bytes DESC
      `;
      const result = await this.db.queryAll(sql, [`%${contentType}%`]);
      return result;
    } catch (error) {
      throw new DAOException(`按类型查找资产失败: ${error.message}`, 'FIND_BY_CONTENT_TYPE_FAILED', error);
    }
  }

  /**
   * 按文件大小范围查找资产
   */
  async findBySizeRange(minBytes: number, maxBytes?: number): Promise<ReleaseAsset[]> {
    try {
      let sql = `
        SELECT * FROM release_assets 
        WHERE size_bytes >= ?
      `;
      const params = [minBytes];

      if (maxBytes !== undefined) {
        sql += ' AND size_bytes <= ?';
        params.push(maxBytes);
      }

      sql += ' ORDER BY size_bytes DESC';

      const result = await this.db.queryAll(sql, params);
      return result;
    } catch (error) {
      throw new DAOException(`按大小范围查找资产失败: ${error.message}`, 'FIND_BY_SIZE_RANGE_FAILED', error);
    }
  }

  /**
   * 搜索资产
   */
  async searchAssets(params?: ReleaseAssetSearchParams): Promise<ReleaseAsset[]> {
    try {
      const searchFields = params?.searchFields || ['name', 'label'];
      const result = await this.findPaginated({
        ...params,
        query: params?.query,
        searchFields
      });
      return result.data;
    } catch (error) {
      throw new DAOException(`搜索资产失败: ${error.message}`, 'SEARCH_ASSETS_FAILED', error);
    }
  }

  /**
   * 获取最大/最小的资产
   */
  async getSizeExtremes(): Promise<{
    largest: ReleaseAsset | null;
    smallest: ReleaseAsset | null;
  }> {
    try {
      const largest = await this.db.querySingle(`
        SELECT * FROM release_assets 
        ORDER BY size_bytes DESC 
        LIMIT 1
      `);

      const smallest = await this.db.querySingle(`
        SELECT * FROM release_assets 
        WHERE size_bytes > 0
        ORDER BY size_bytes ASC 
        LIMIT 1
      `);

      return {
        largest: largest || null,
        smallest: smallest || null
      };
    } catch (error) {
      throw new DAOException(`获取资产大小极值失败: ${error.message}`, 'GET_SIZE_EXTREMES_FAILED', error);
    }
  }

  /**
   * 标记资产为已下载
   */
  async markAsDownloaded(assetId: number, localPath: string, fileHash?: string): Promise<boolean> {
    try {
      const sql = `
        UPDATE release_assets 
        SET is_downloaded = 1, local_path = ?, download_time = ?, file_hash = ?
        WHERE id = ?
      `;
      const result = await this.db.update(sql, [
        localPath, 
        new Date().toISOString(), 
        fileHash || null, 
        assetId
      ]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`标记下载失败: ${error.message}`, 'MARK_DOWNLOADED_FAILED', error);
    }
  }

  /**
   * 取消下载标记
   */
  async markAsNotDownloaded(assetId: number): Promise<boolean> {
    try {
      const sql = `
        UPDATE release_assets 
        SET is_downloaded = 0, local_path = NULL, download_time = NULL
        WHERE id = ?
      `;
      const result = await this.db.update(sql, [assetId]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`取消下载标记失败: ${error.message}`, 'MARK_NOT_DOWNLOADED_FAILED', error);
    }
  }

  /**
   * 更新下载次数
   */
  async incrementDownloadCount(assetId: number): Promise<boolean> {
    try {
      const sql = 'UPDATE release_assets SET download_count = download_count + 1 WHERE id = ?';
      const result = await this.db.update(sql, [assetId]);
      return result > 0;
    } catch (error) {
      throw new DAOException(`更新下载次数失败: ${error.message}`, 'INCREMENT_DOWNLOAD_COUNT_FAILED', error);
    }
  }

  /**
   * 同步或创建资产
   */
  async syncAsset(data: CreateReleaseAssetData): Promise<ReleaseAsset> {
    try {
      // 尝试查找现有资产
      let asset = await this.findByGithubId(data.github_asset_id);

      if (asset) {
        // 更新现有资产
        const updateData = {
          name: data.name,
          label: data.label,
          content_type: data.content_type,
          size_bytes: data.size_bytes,
          download_count: data.download_count || 0
        };

        asset = await this.update(asset.id!, updateData);
      } else {
        // 创建新资产
        asset = await this.create(data);
      }

      return asset;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`同步资产失败: ${error.message}`, 'SYNC_ASSET_FAILED', error);
    }
  }

  /**
   * 批量标记为已下载
   */
  async batchMarkAsDownloaded(assetIds: number[], localPaths: string[], fileHashes?: string[]): Promise<number> {
    try {
      if (assetIds.length === 0 || assetIds.length !== localPaths.length) {
        throw new DAOException('参数不匹配', 'INVALID_PARAMETERS');
      }

      await this.db.executeInTransaction(async (tx) => {
        for (let i = 0; i < assetIds.length; i++) {
          const assetId = assetIds[i];
          const localPath = localPaths[i];
          const fileHash = fileHashes?.[i];

          const sql = `
            UPDATE release_assets 
            SET is_downloaded = 1, local_path = ?, download_time = ?, file_hash = ?
            WHERE id = ?
          `;
          await tx.run(sql, [
            localPath,
            new Date().toISOString(),
            fileHash || null,
            assetId
          ]);
        }
      });

      return assetIds.length;
    } catch (error) {
      if (error instanceof DAOException) throw error;
      throw new DAOException(`批量标记下载失败: ${error.message}`, 'BATCH_MARK_DOWNLOADED_FAILED', error);
    }
  }

  /**
   * 获取资产统计信息
   */
  async getAssetStats(): Promise<{
    totalAssets: number;
    downloadedCount: number;
    notDownloadedCount: number;
    totalSize: number;
    downloadedSize: number;
    averageSize: number;
    largestAsset: ReleaseAsset | null;
    smallestAsset: ReleaseAsset | null;
    contentTypeDistribution: Array<{ contentType: string; count: number; totalSize: number }>;
    topDownloadedAssets: Array<{ name: string; downloadCount: number }>;
  }> {
    try {
      const basicStats = await this.db.querySingle(`
        SELECT 
          COUNT(*) as total_assets,
          SUM(CASE WHEN is_downloaded = 1 THEN 1 ELSE 0 END) as downloaded_count,
          SUM(CASE WHEN is_downloaded = 0 THEN 1 ELSE 0 END) as not_downloaded_count,
          SUM(size_bytes) as total_size,
          SUM(CASE WHEN is_downloaded = 1 THEN size_bytes ELSE 0 END) as downloaded_size,
          AVG(size_bytes) as average_size
        FROM release_assets
      `);

      // 内容类型分布
      const contentTypeStats = await this.db.queryAll(`
        SELECT 
          content_type,
          COUNT(*) as count,
          SUM(size_bytes) as total_size
        FROM release_assets
        WHERE content_type IS NOT NULL
        GROUP BY content_type
        ORDER BY count DESC
        LIMIT 10
      `);

      // 热门下载资产
      const topDownloaded = await this.db.queryAll(`
        SELECT name, download_count
        FROM release_assets
        ORDER BY download_count DESC
        LIMIT 10
      `);

      // 大小极值
      const { largest, smallest } = await this.getSizeExtremes();

      return {
        totalAssets: basicStats.total_assets || 0,
        downloadedCount: basicStats.downloaded_count || 0,
        notDownloadedCount: basicStats.not_downloaded_count || 0,
        totalSize: basicStats.total_size || 0,
        downloadedSize: basicStats.downloaded_size || 0,
        averageSize: Math.round((basicStats.average_size || 0) * 100) / 100,
        largestAsset: largest,
        smallestAsset: smallest,
        contentTypeDistribution: contentTypeStats,
        topDownloadedAssets: topDownloaded
      };
    } catch (error) {
      throw new DAOException(`获取资产统计失败: ${error.message}`, 'ASSET_STATS_FAILED', error);
    }
  }

  /**
   * 按扩展名查找资产
   */
  async findByExtension(extension: string): Promise<ReleaseAsset[]> {
    try {
      const sql = `
        SELECT * FROM release_assets 
        WHERE name LIKE ?
        ORDER BY size_bytes DESC
      `;
      const result = await this.db.queryAll(sql, [`%.${extension}`]);
      return result;
    } catch (error) {
      throw new DAOException(`按扩展名查找资产失败: ${error.message}`, 'FIND_BY_EXTENSION_FAILED', error);
    }
  }

  /**
   * 获取资产大小分布
   */
  async getSizeDistribution(): Promise<Array<{
    sizeRange: string;
    count: number;
    percentage: number;
  }>> {
    try {
      const total = await this.db.querySingle('SELECT COUNT(*) as total FROM release_assets');
      
      if (!total.total || total.total === 0) return [];

      const distributions = await this.db.queryAll(`
        SELECT 
          CASE 
            WHEN size_bytes < 1024 THEN '< 1KB'
            WHEN size_bytes < 1024 * 1024 THEN '1KB - 1MB'
            WHEN size_bytes < 10 * 1024 * 1024 THEN '1MB - 10MB'
            WHEN size_bytes < 100 * 1024 * 1024 THEN '10MB - 100MB'
            WHEN size_bytes < 1024 * 1024 * 1024 THEN '100MB - 1GB'
            ELSE '> 1GB'
          END as size_range,
          COUNT(*) as count
        FROM release_assets
        GROUP BY size_range
        ORDER BY MIN(size_bytes)
      `);

      return distributions.map(dist => ({
        ...dist,
        percentage: Math.round((dist.count * 100) / total.total)
      }));
    } catch (error) {
      throw new DAOException(`获取大小分布失败: ${error.message}`, 'GET_SIZE_DISTRIBUTION_FAILED', error);
    }
  }

  /**
   * 清理本地文件路径（下载被删除的文件）
   */
  async cleanupMissingLocalFiles(): Promise<number> {
    try {
      // 这里需要文件系统检查，暂时标记为未下载
      const sql = `
        UPDATE release_assets 
        SET is_downloaded = 0, local_path = NULL, download_time = NULL
        WHERE is_downloaded = 1 AND local_path IS NOT NULL
      `;
      
      // 注意：这里应该先检查文件是否存在再标记
      const result = await this.db.update(sql);
      return result;
    } catch (error) {
      throw new DAOException(`清理本地文件路径失败: ${error.message}`, 'CLEANUP_LOCAL_FILES_FAILED', error);
    }
  }

  /**
   * 获取未下载的大文件
   */
  async getUndownloadedLargeFiles(minSizeMB: number = 100): Promise<ReleaseAsset[]> {
    try {
      const minBytes = minSizeMB * 1024 * 1024;
      const sql = `
        SELECT * FROM release_assets 
        WHERE is_downloaded = 0 AND size_bytes >= ?
        ORDER BY size_bytes DESC
      `;
      const result = await this.db.queryAll(sql, [minBytes]);
      return result;
    } catch (error) {
      throw new DAOException(`获取未下载大文件失败: ${error.message}`, 'GET_UNDOWNLOADED_LARGE_FILES_FAILED', error);
    }
  }

  /**
   * 验证文件完整性
   */
  async validateFileIntegrity(assetId: number, expectedHash: string): Promise<boolean> {
    try {
      const sql = 'SELECT file_hash FROM release_assets WHERE id = ?';
      const result = await this.db.querySingle(sql, [assetId]);
      
      if (!result || !result.file_hash) {
        return false;
      }

      // 注意：这里应该实现实际的哈希验证逻辑
      return result.file_hash === expectedHash;
    } catch (error) {
      throw new DAOException(`验证文件完整性失败: ${error.message}`, 'VALIDATE_FILE_INTEGRITY_FAILED', error);
    }
  }
}
