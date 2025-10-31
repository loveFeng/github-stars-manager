import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Github, Key } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setGithubToken, setAuthenticated, setUser } = useAppStore();
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTokenLogin = async () => {
    if (!token.trim()) {
      setError('请输入 GitHub Personal Access Token');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 验证 token 并获取用户信息
      const response = await fetch('https://api.github.com/user', {
        headers: {
          Authorization: `token ${token}`,
          Accept: 'application/vnd.github.v3+json',
        },
      });

      if (!response.ok) {
        throw new Error('Token 无效或已过期');
      }

      const userData = await response.json();

      setUser({
        id: userData.id,
        login: userData.login,
        name: userData.name,
        email: userData.email,
        avatar_url: userData.avatar_url,
        html_url: userData.html_url,
        bio: userData.bio,
        public_repos: userData.public_repos,
        followers: userData.followers,
        following: userData.following,
      });

      setGithubToken(token);
      setAuthenticated(true);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请检查 Token 是否正确');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = () => {
    // OAuth 登录逻辑
    alert('OAuth 登录功能开发中');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <Github className="h-12 w-12 text-primary" />
          </div>
          <CardTitle className="text-2xl text-center">GitHub Stars Manager</CardTitle>
          <CardDescription className="text-center">
            管理你的 GitHub 星标仓库
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="token" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="token">Personal Access Token</TabsTrigger>
              <TabsTrigger value="oauth">OAuth</TabsTrigger>
            </TabsList>

            <TabsContent value="token" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="token">GitHub Personal Access Token</Label>
                <div className="relative">
                  <Key className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="token"
                    type="password"
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleTokenLogin()}
                    className="pl-10"
                    disabled={loading}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  需要 repo 和 user 权限。
                  <a
                    href="https://github.com/settings/tokens/new"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline ml-1"
                  >
                    创建 Token
                  </a>
                </p>
              </div>

              {error && (
                <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md">
                  {error}
                </div>
              )}

              <Button
                onClick={handleTokenLogin}
                className="w-full"
                disabled={loading}
              >
                {loading ? '登录中...' : '登录'}
              </Button>
            </TabsContent>

            <TabsContent value="oauth" className="space-y-4">
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground mb-4">
                  使用 GitHub OAuth 登录
                </p>
                <Button onClick={handleOAuthLogin} className="w-full">
                  <Github className="mr-2 h-4 w-4" />
                  使用 GitHub 登录
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
