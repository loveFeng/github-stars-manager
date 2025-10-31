import { useState, useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { GitHubAPI, transformGitHubRepo } from '@/services/github';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, Star, GitFork, Code, ExternalLink, Loader2, RefreshCw } from 'lucide-react';
import type { Repository } from '@/types';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { toast } from 'sonner';

export default function RepositoriesPage() {
  const {
    repositories,
    searchResults,
    setSearchResults,
    searchFilters,
    setSearchFilters,
    githubToken,
    setRepositories,
    setLastSync,
  } = useAppStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [initialLoading, setInitialLoading] = useState(false);

  // 首次加载时同步数据
  useEffect(() => {
    if (repositories.length === 0 && githubToken && !initialLoading) {
      syncRepositories();
    }
  }, []);

  useEffect(() => {
    filterRepositories();
  }, [searchQuery, searchFilters, repositories]);

  const syncRepositories = async () => {
    if (!githubToken) return;

    setInitialLoading(true);
    try {
      toast.loading('正在加载星标仓库...', { id: 'sync' });
      const api = new GitHubAPI({ token: githubToken });
      const repos = await api.getAllStarredRepos();

      const formattedRepos = repos.map((repo, index) => ({
        id: index + 1,
        ...transformGitHubRepo(repo),
      })) as any;

      setRepositories(formattedRepos);
      setLastSync(new Date().toISOString());

      toast.success(`已加载 ${repos.length} 个星标仓库`, { id: 'sync' });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加载失败', { id: 'sync' });
    } finally {
      setInitialLoading(false);
    }
  };

  const filterRepositories = () => {
    let filtered = repositories;

    // 搜索过滤
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (repo) =>
          repo.name.toLowerCase().includes(query) ||
          repo.description?.toLowerCase().includes(query) ||
          repo.owner.toLowerCase().includes(query) ||
          repo.topics.some((topic) => topic.toLowerCase().includes(query))
      );
    }

    // 语言过滤
    if (searchFilters.language) {
      filtered = filtered.filter((repo) => repo.language === searchFilters.language);
    }

    // 归档过滤
    if (!searchFilters.showArchived) {
      filtered = filtered.filter((repo) => !repo.archived);
    }

    // 排序
    filtered.sort((a, b) => {
      const aValue = a[searchFilters.sortBy];
      const bValue = b[searchFilters.sortBy];
      
      if (searchFilters.sortBy === 'name') {
        return searchFilters.sortOrder === 'asc'
          ? String(aValue).localeCompare(String(bValue))
          : String(bValue).localeCompare(String(aValue));
      }
      
      if (searchFilters.sortBy === 'updated' || searchFilters.sortBy === 'created') {
        const dateA = new Date(String(aValue)).getTime();
        const dateB = new Date(String(bValue)).getTime();
        return searchFilters.sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
      }

      return searchFilters.sortOrder === 'asc'
        ? Number(aValue) - Number(bValue)
        : Number(bValue) - Number(aValue);
    });

    setSearchResults(filtered);
  };

  const languages = Array.from(
    new Set(repositories.map((r) => r.language).filter(Boolean))
  ).sort();

  if (initialLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
        <p className="text-lg font-medium">正在加载星标仓库...</p>
        <p className="text-sm text-muted-foreground mt-2">请稍候，这可能需要一些时间</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">星标仓库</h1>
        <p className="text-muted-foreground mt-2">
          共 {repositories.length} 个仓库，显示 {searchResults.length} 个
        </p>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索仓库名称、描述、标签..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select
          value={searchFilters.language || 'all'}
          onValueChange={(value) =>
            setSearchFilters({ language: value === 'all' ? null : value })
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="选择语言" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有语言</SelectItem>
            {languages.map((lang) => (
              <SelectItem key={lang} value={lang!}>
                {lang}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={searchFilters.sortBy}
          onValueChange={(value: any) => setSearchFilters({ sortBy: value })}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="stars">按星标数</SelectItem>
            <SelectItem value="updated">按更新时间</SelectItem>
            <SelectItem value="created">按创建时间</SelectItem>
            <SelectItem value="name">按名称</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          onClick={() =>
            setSearchFilters({
              sortOrder: searchFilters.sortOrder === 'asc' ? 'desc' : 'asc',
            })
          }
        >
          {searchFilters.sortOrder === 'asc' ? '升序' : '降序'}
        </Button>
      </div>

      {repositories.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">还没有星标仓库数据</p>
          <Button onClick={syncRepositories}>
            <RefreshCw className="mr-2 h-4 w-4" />
            立即同步
          </Button>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {searchResults.map((repo) => (
          <RepositoryCard key={repo.id} repository={repo} />
        ))}
      </div>

      {searchResults.length === 0 && repositories.length > 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">没有找到匹配的仓库</p>
        </div>
      )}
    </div>
  );
}

function RepositoryCard({ repository }: { repository: Repository }) {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
        <div className="space-y-3">
          <div>
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <a
                href={repository.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary flex items-center gap-1"
              >
                {repository.name}
                <ExternalLink className="h-3 w-3" />
              </a>
            </h3>
            <p className="text-sm text-muted-foreground">{repository.owner}</p>
          </div>

          {repository.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {repository.description}
            </p>
          )}

          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4" />
              {repository.stars_count.toLocaleString()}
            </div>
            <div className="flex items-center gap-1">
              <GitFork className="h-4 w-4" />
              {repository.forks_count.toLocaleString()}
            </div>
            {repository.language && (
              <div className="flex items-center gap-1">
                <Code className="h-4 w-4" />
                {repository.language}
              </div>
            )}
          </div>

          {repository.topics.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {repository.topics.slice(0, 3).map((topic) => (
                <Badge key={topic} variant="secondary" className="text-xs">
                  {topic}
                </Badge>
              ))}
              {repository.topics.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{repository.topics.length - 3}
                </Badge>
              )}
            </div>
          )}

          <div className="text-xs text-muted-foreground pt-2 border-t">
            更新于 {format(new Date(repository.last_updated_at), 'PPP', { locale: zhCN })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
