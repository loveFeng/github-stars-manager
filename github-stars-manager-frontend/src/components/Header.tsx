import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Github, RefreshCw, LogOut, Settings } from 'lucide-react';
import { GitHubAPI, transformGitHubRepo } from '@/services/github';
import { useToast } from '@/hooks/use-toast';

export default function Header() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, logout, isSyncing, setIsSyncing, githubToken, setRepositories, setLastSync } = useAppStore();

  const handleSync = async () => {
    if (!githubToken) return;
    
    setIsSyncing(true);
    try {
      toast({
        title: '开始同步',
        description: '正在获取星标仓库...',
      });

      const api = new GitHubAPI({ token: githubToken });
      const repos = await api.getAllStarredRepos();

      const formattedRepos = repos.map((repo, index) => ({
        id: index + 1,
        ...transformGitHubRepo(repo),
      })) as any;

      setRepositories(formattedRepos);
      setLastSync(new Date().toISOString());

      toast({
        title: '同步成功',
        description: `已同步 ${repos.length} 个星标仓库`,
      });
    } catch (error) {
      toast({
        title: '同步失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center px-4">
        <div className="flex items-center gap-2">
          <Github className="h-6 w-6" />
          <h1 className="text-xl font-bold">GitHub Stars Manager</h1>
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={isSyncing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? '同步中...' : '同步'}
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                <Avatar>
                  <AvatarImage src={user?.avatar_url} alt={user?.login} />
                  <AvatarFallback>{user?.login?.[0]?.toUpperCase()}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name || user?.login}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/settings')}>
                <Settings className="mr-2 h-4 w-4" />
                设置
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
