import { useParams } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ExternalLink, Star, GitFork, Eye, Code, Tag } from 'lucide-react';

export default function RepositoryDetailPage() {
  const { id } = useParams();
  const repositories = useAppStore((state) => state.repositories);
  const repository = repositories.find((r) => r.id === Number(id));

  if (!repository) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">仓库未找到</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{repository.name}</h1>
            <p className="text-muted-foreground mt-2">{repository.owner}</p>
          </div>
          <Button asChild>
            <a href={repository.html_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="mr-2 h-4 w-4" />
              在 GitHub 上查看
            </a>
          </Button>
        </div>

        {repository.description && (
          <p className="text-lg mt-4">{repository.description}</p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Star className="h-4 w-4" />
              Stars
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{repository.stars_count.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <GitFork className="h-4 w-4" />
              Forks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{repository.forks_count.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Watchers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{repository.watchers_count.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Code className="h-4 w-4" />
              Language
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{repository.language || 'N/A'}</p>
          </CardContent>
        </Card>
      </div>

      {repository.topics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Tag className="h-5 w-5" />
              标签
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {repository.topics.map((topic) => (
                <Badge key={topic} variant="secondary">
                  {topic}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {repository.ai_summary && (
        <Card>
          <CardHeader>
            <CardTitle>AI 摘要</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{repository.ai_summary}</p>
          </CardContent>
        </Card>
      )}

      {repository.user_notes && (
        <Card>
          <CardHeader>
            <CardTitle>个人笔记</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground whitespace-pre-wrap">{repository.user_notes}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
