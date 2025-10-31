import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import Database from 'better-sqlite3';
import axios from 'axios';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());

// 数据库初始化
const db = new Database('./data/github-stars.db');

// 初始化数据库表
db.exec(`
  CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_id INTEGER UNIQUE NOT NULL,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    description TEXT,
    html_url TEXT NOT NULL,
    clone_url TEXT,
    ssh_url TEXT,
    language TEXT,
    languages TEXT,
    topics TEXT,
    stars_count INTEGER DEFAULT 0,
    forks_count INTEGER DEFAULT 0,
    watchers_count INTEGER DEFAULT 0,
    open_issues_count INTEGER DEFAULT 0,
    size_kb INTEGER DEFAULT 0,
    license TEXT,
    default_branch TEXT,
    archived INTEGER DEFAULT 0,
    disabled INTEGER DEFAULT 0,
    is_private INTEGER DEFAULT 0,
    user_notes TEXT,
    user_rating INTEGER,
    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_release_id INTEGER UNIQUE NOT NULL,
    repository_id INTEGER NOT NULL,
    tag_name TEXT NOT NULL,
    name TEXT,
    body TEXT,
    draft INTEGER DEFAULT 0,
    prerelease INTEGER DEFAULT 0,
    created_at TEXT,
    published_at TEXT,
    html_url TEXT NOT NULL,
    zipball_url TEXT,
    tarball_url TEXT,
    target_commitish TEXT,
    author_login TEXT,
    author_avatar_url TEXT,
    is_subscribed INTEGER DEFAULT 0,
    is_read INTEGER DEFAULT 0,
    user_notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS release_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_asset_id INTEGER UNIQUE NOT NULL,
    release_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    label TEXT,
    content_type TEXT,
    size_bytes INTEGER NOT NULL,
    download_count INTEGER DEFAULT 0,
    browser_download_url TEXT NOT NULL,
    created_at TEXT,
    is_downloaded INTEGER DEFAULT 0,
    local_path TEXT,
    download_time TEXT,
    file_hash TEXT,
    user_notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (release_id) REFERENCES releases(id) ON DELETE CASCADE
  );
`);

// GitHub API 辅助函数
async function fetchGitHubAPI(endpoint: string, token: string) {
  try {
    const response = await axios.get(`https://api.github.com${endpoint}`, {
      headers: {
        Authorization: `token ${token}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message);
  }
}

// 认证中间件
function authMiddleware(req: any, res: any, next: any) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  req.githubToken = token;
  next();
}

// 路由

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 获取所有仓库
app.get('/api/repositories', authMiddleware, (req, res) => {
  try {
    const repos = db.prepare('SELECT * FROM repositories ORDER BY stars_count DESC').all();
    const formattedRepos = repos.map((repo: any) => ({
      ...repo,
      languages: repo.languages ? JSON.parse(repo.languages) : null,
      topics: repo.topics ? JSON.parse(repo.topics) : [],
      archived: Boolean(repo.archived),
      disabled: Boolean(repo.disabled),
      is_private: Boolean(repo.is_private),
    }));
    res.json(formattedRepos);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 获取单个仓库
app.get('/api/repositories/:id', authMiddleware, (req, res) => {
  try {
    const repo = db.prepare('SELECT * FROM repositories WHERE id = ?').get(req.params.id);
    if (!repo) {
      return res.status(404).json({ error: 'Repository not found' });
    }
    res.json({
      ...repo,
      languages: repo.languages ? JSON.parse(repo.languages) : null,
      topics: repo.topics ? JSON.parse(repo.topics) : [],
      archived: Boolean(repo.archived),
      disabled: Boolean(repo.disabled),
      is_private: Boolean(repo.is_private),
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 同步星标仓库
app.post('/api/repositories/sync', authMiddleware, async (req, res) => {
  try {
    const token = req.githubToken;
    let page = 1;
    let allRepos: any[] = [];
    let hasMore = true;

    // 获取所有星标仓库
    while (hasMore) {
      const repos = await fetchGitHubAPI(`/user/starred?page=${page}&per_page=100`, token);
      if (repos.length === 0) {
        hasMore = false;
      } else {
        allRepos = allRepos.concat(repos);
        page++;
      }
    }

    // 存储到数据库
    const insertStmt = db.prepare(`
      INSERT OR REPLACE INTO repositories (
        github_id, owner, name, full_name, description, html_url, clone_url, ssh_url,
        language, topics, stars_count, forks_count, watchers_count, open_issues_count,
        size_kb, license, default_branch, archived, disabled, is_private,
        last_updated_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    `);

    const insertMany = db.transaction((repos: any[]) => {
      for (const repo of repos) {
        insertStmt.run(
          repo.id,
          repo.owner.login,
          repo.name,
          repo.full_name,
          repo.description,
          repo.html_url,
          repo.clone_url,
          repo.ssh_url,
          repo.language,
          JSON.stringify(repo.topics || []),
          repo.stargazers_count,
          repo.forks_count,
          repo.watchers_count,
          repo.open_issues_count,
          repo.size,
          repo.license?.spdx_id || null,
          repo.default_branch,
          repo.archived ? 1 : 0,
          repo.disabled ? 1 : 0,
          repo.private ? 1 : 0
        );
      }
    });

    insertMany(allRepos);

    res.json({
      success: true,
      synced: allRepos.length,
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 更新仓库
app.patch('/api/repositories/:id', authMiddleware, (req, res) => {
  try {
    const { user_notes, user_rating } = req.body;
    db.prepare(`
      UPDATE repositories 
      SET user_notes = ?, user_rating = ?, updated_at = datetime('now')
      WHERE id = ?
    `).run(user_notes, user_rating, req.params.id);

    const repo = db.prepare('SELECT * FROM repositories WHERE id = ?').get(req.params.id);
    res.json(repo);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 获取所有 releases
app.get('/api/releases', authMiddleware, (req, res) => {
  try {
    const releases = db.prepare(`
      SELECT r.*, 
        json_object(
          'id', repo.id,
          'name', repo.name,
          'full_name', repo.full_name,
          'owner', repo.owner
        ) as repository
      FROM releases r
      LEFT JOIN repositories repo ON r.repository_id = repo.id
      ORDER BY r.published_at DESC
    `).all();

    const formattedReleases = releases.map((release: any) => ({
      ...release,
      repository: JSON.parse(release.repository),
      draft: Boolean(release.draft),
      prerelease: Boolean(release.prerelease),
      is_subscribed: Boolean(release.is_subscribed),
      is_read: Boolean(release.is_read),
      assets: [],
    }));

    res.json(formattedReleases);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 同步仓库的 releases
app.post('/api/repositories/:id/releases/sync', authMiddleware, async (req, res) => {
  try {
    const token = req.githubToken;
    const repo: any = db.prepare('SELECT * FROM repositories WHERE id = ?').get(req.params.id);
    
    if (!repo) {
      return res.status(404).json({ error: 'Repository not found' });
    }

    const releases = await fetchGitHubAPI(`/repos/${repo.full_name}/releases`, token);

    const insertStmt = db.prepare(`
      INSERT OR REPLACE INTO releases (
        github_release_id, repository_id, tag_name, name, body, draft, prerelease,
        created_at, published_at, html_url, zipball_url, tarball_url, target_commitish,
        author_login, author_avatar_url, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    `);

    const insertMany = db.transaction((releases: any[]) => {
      for (const release of releases) {
        insertStmt.run(
          release.id,
          repo.id,
          release.tag_name,
          release.name,
          release.body,
          release.draft ? 1 : 0,
          release.prerelease ? 1 : 0,
          release.created_at,
          release.published_at,
          release.html_url,
          release.zipball_url,
          release.tarball_url,
          release.target_commitish,
          release.author?.login || null,
          release.author?.avatar_url || null
        );

        // 插入 assets
        if (release.assets && release.assets.length > 0) {
          const assetStmt = db.prepare(`
            INSERT OR REPLACE INTO release_assets (
              github_asset_id, release_id, name, label, content_type, size_bytes,
              download_count, browser_download_url, created_at, updated_at
            ) VALUES (?, (SELECT id FROM releases WHERE github_release_id = ?), ?, ?, ?, ?, ?, ?, ?, datetime('now'))
          `);

          for (const asset of release.assets) {
            assetStmt.run(
              asset.id,
              release.id,
              asset.name,
              asset.label,
              asset.content_type,
              asset.size,
              asset.download_count,
              asset.browser_download_url,
              asset.created_at
            );
          }
        }
      }
    });

    insertMany(releases);

    res.json({
      success: true,
      synced: releases.length,
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 订阅 release
app.post('/api/releases/:id/subscribe', authMiddleware, (req, res) => {
  try {
    db.prepare('UPDATE releases SET is_subscribed = 1 WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 取消订阅 release
app.delete('/api/releases/:id/subscribe', authMiddleware, (req, res) => {
  try {
    db.prepare('UPDATE releases SET is_subscribed = 0 WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 标记为已读
app.post('/api/releases/:id/read', authMiddleware, (req, res) => {
  try {
    db.prepare('UPDATE releases SET is_read = 1 WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

// 优雅关闭
process.on('SIGINT', () => {
  db.close();
  process.exit(0);
});
