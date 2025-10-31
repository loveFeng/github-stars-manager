import { useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { GitPullRequest, Download, ExternalLink, Calendar, FileText, User } from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Release } from '@/types';

export default function ReleasesPage() {
  const {
    releases,
    repositories,
    releaseSubscriptions,
    subscribeToRelease,
    unsubscribeFromRelease,
  } = useAppStore();

  const [filter, setFilter] = useState<'all' | 'subscribed'>('all');

  const filteredReleases = releases.filter((release) =>
    filter === 'all' ? true : releaseSubscriptions.has(release.id)
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Release 订阅</h1>
        <p className="text-muted-foreground mt-2">
          追踪你关注的仓库发布动态
        </p>
      </div>

      <div className="flex gap-2">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          onClick={() => setFilter('all')}
        >
          全部发布
        </Button>
        <Button
          variant={filter === 'subscribed' ? 'default' : 'outline'}
          onClick={() => setFilter('subscribed')}
        >
          已订阅
        </Button>
      </div>

      <div className="space-y-4">
        {filteredReleases.map((release) => {
          const repository = repositories.find((r) => r.id === release.repository_id);
          const isSubscribed = releaseSubscriptions.has(release.id);

          return (
            <ReleaseCard
              key={release.id}
              release={release}
              repository={repository}
              isSubscribed={isSubscribed}
              onSubscribe={() =>
                isSubscribed
                  ? unsubscribeFromRelease(release.id)
                  : subscribeToRelease(release.id)
              }
            />
          );
        })}
      </div>

      {filteredReleases.length === 0 && (
        <div className="text-center py-12">
          <GitPullRequest className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">暂无发布记录</p>
        </div>
      )}
    </div>
  );
}

interface ReleaseCardProps {
  release: Release;
  repository: any;
  isSubscribed: boolean;
  onSubscribe: () => void;
}

function ReleaseCard({ release, repository, isSubscribed, onSubscribe }: ReleaseCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              {repository?.name || 'Unknown Repository'}
              <Badge variant="outline">{release.tag_name}</Badge>
              {release.prerelease && <Badge variant="secondary">预发布</Badge>}
              {release.draft && <Badge variant="secondary">草稿</Badge>}
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {release.name || release.tag_name}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant={isSubscribed ? 'default' : 'outline'}
              size="sm"
              onClick={onSubscribe}
            >
              {isSubscribed ? '已订阅' : '订阅'}
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href={release.html_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <User className="h-4 w-4" />
            {release.author_login}
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            {format(new Date(release.published_at), 'PPP', { locale: zhCN })}
          </div>
        </div>

        {release.body && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                发布说明
              </h4>
              <ScrollArea className="h-32">
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {release.body}
                </p>
              </ScrollArea>
            </div>
          </>
        )}

        {release.assets.length > 0 && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <Download className="h-4 w-4" />
                资产文件 ({release.assets.length})
              </h4>
              <div className="space-y-2">
                {release.assets.map((asset) => (
                  <div
                    key={asset.id}
                    className="flex items-center justify-between p-2 rounded-md hover:bg-accent"
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium">{asset.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(asset.size_bytes / 1024 / 1024).toFixed(2)} MB · 下载 {asset.download_count.toLocaleString()} 次
                      </p>
                    </div>
                    <Button variant="ghost" size="sm" asChild>
                      <a href={asset.browser_download_url} download>
                        <Download className="h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
