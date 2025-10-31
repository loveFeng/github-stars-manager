import { useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Brain, Cloud, Palette, Globe } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">设置</h1>
        <p className="text-muted-foreground mt-2">
          管理应用程序配置和偏好设置
        </p>
      </div>

      <Tabs defaultValue="ai" className="w-full">
        <TabsList>
          <TabsTrigger value="ai">
            <Brain className="mr-2 h-4 w-4" />
            AI 配置
          </TabsTrigger>
          <TabsTrigger value="webdav">
            <Cloud className="mr-2 h-4 w-4" />
            WebDAV 备份
          </TabsTrigger>
          <TabsTrigger value="appearance">
            <Palette className="mr-2 h-4 w-4" />
            外观
          </TabsTrigger>
          <TabsTrigger value="general">
            <Globe className="mr-2 h-4 w-4" />
            常规
          </TabsTrigger>
        </TabsList>

        <TabsContent value="ai" className="space-y-4">
          <AIConfigSection />
        </TabsContent>

        <TabsContent value="webdav" className="space-y-4">
          <WebDAVConfigSection />
        </TabsContent>

        <TabsContent value="appearance" className="space-y-4">
          <AppearanceSection />
        </TabsContent>

        <TabsContent value="general" className="space-y-4">
          <GeneralSection />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function AIConfigSection() {
  const { aiConfigs, addAIConfig, updateAIConfig, deleteAIConfig, activeAIConfig, setActiveAIConfig } = useAppStore();
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    api_url: '',
    api_key: '',
    model_name: '',
    max_tokens: 4000,
    temperature: 0.7,
  });

  const handleSubmit = () => {
    const newConfig = {
      id: Date.now(),
      ...formData,
      timeout_seconds: 30,
      is_active: false,
      is_default: aiConfigs.length === 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    addAIConfig(newConfig);
    setFormData({
      name: '',
      api_url: '',
      api_key: '',
      model_name: '',
      max_tokens: 4000,
      temperature: 0.7,
    });
    setEditing(false);
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>AI 模型配置</CardTitle>
          <CardDescription>
            配置 OpenAI 兼容的 AI 服务用于生成仓库摘要和标签
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {aiConfigs.map((config) => (
            <div key={config.id} className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium">{config.name}</p>
                <p className="text-sm text-muted-foreground">{config.model_name}</p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={activeAIConfig === config.id ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveAIConfig(config.id)}
                >
                  {activeAIConfig === config.id ? '当前使用' : '设为默认'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => deleteAIConfig(config.id)}
                >
                  删除
                </Button>
              </div>
            </div>
          ))}

          {!editing && (
            <Button onClick={() => setEditing(true)} className="w-full">
              添加 AI 配置
            </Button>
          )}

          {editing && (
            <div className="space-y-4 p-4 border rounded-lg">
              <div className="space-y-2">
                <Label htmlFor="ai-name">配置名称</Label>
                <Input
                  id="ai-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如: OpenAI GPT-4"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ai-url">API URL</Label>
                <Input
                  id="ai-url"
                  value={formData.api_url}
                  onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                  placeholder="https://api.openai.com/v1/chat/completions"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ai-key">API Key</Label>
                <Input
                  id="ai-key"
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  placeholder="sk-..."
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ai-model">模型名称</Label>
                <Input
                  id="ai-model"
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  placeholder="gpt-4"
                />
              </div>

              <div className="flex gap-2">
                <Button onClick={handleSubmit}>保存</Button>
                <Button variant="outline" onClick={() => setEditing(false)}>
                  取消
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function WebDAVConfigSection() {
  const { webdavConfigs, addWebDAVConfig, deleteWebDAVConfig, activeWebDAVConfig, setActiveWebDAVConfig } = useAppStore();
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    server_url: '',
    username: '',
    password: '',
    remote_path: '/GithubStarsManager',
  });

  const handleSubmit = () => {
    const newConfig = {
      id: Date.now(),
      ...formData,
      is_active: false,
      is_default: webdavConfigs.length === 0,
      last_sync_at: null,
      sync_status: null,
      error_message: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    addWebDAVConfig(newConfig as any);
    setFormData({
      name: '',
      server_url: '',
      username: '',
      password: '',
      remote_path: '/GithubStarsManager',
    });
    setEditing(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>WebDAV 备份配置</CardTitle>
        <CardDescription>
          配置 WebDAV 服务进行数据备份和同步
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {webdavConfigs.map((config) => (
          <div key={config.id} className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">{config.name}</p>
              <p className="text-sm text-muted-foreground">{config.server_url}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant={activeWebDAVConfig === config.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveWebDAVConfig(config.id)}
              >
                {activeWebDAVConfig === config.id ? '当前使用' : '设为默认'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => deleteWebDAVConfig(config.id)}
              >
                删除
              </Button>
            </div>
          </div>
        ))}

        {!editing && (
          <Button onClick={() => setEditing(true)} className="w-full">
            添加 WebDAV 配置
          </Button>
        )}

        {editing && (
          <div className="space-y-4 p-4 border rounded-lg">
            <div className="space-y-2">
              <Label htmlFor="webdav-name">配置名称</Label>
              <Input
                id="webdav-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="例如: 坚果云"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="webdav-url">服务器 URL</Label>
              <Input
                id="webdav-url"
                value={formData.server_url}
                onChange={(e) => setFormData({ ...formData, server_url: e.target.value })}
                placeholder="https://dav.jianguoyun.com/dav"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="webdav-username">用户名</Label>
              <Input
                id="webdav-username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="webdav-password">密码</Label>
              <Input
                id="webdav-password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="webdav-path">远程路径</Label>
              <Input
                id="webdav-path"
                value={formData.remote_path}
                onChange={(e) => setFormData({ ...formData, remote_path: e.target.value })}
                placeholder="/GithubStarsManager"
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={handleSubmit}>保存</Button>
              <Button variant="outline" onClick={() => setEditing(false)}>
                取消
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AppearanceSection() {
  const { settings, updateSettings } = useAppStore();

  return (
    <Card>
      <CardHeader>
        <CardTitle>外观设置</CardTitle>
        <CardDescription>
          自定义应用程序的外观
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="theme">主题</Label>
          <Select
            value={settings.theme}
            onValueChange={(value: any) => updateSettings({ theme: value })}
          >
            <SelectTrigger id="theme">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">浅色</SelectItem>
              <SelectItem value="dark">深色</SelectItem>
              <SelectItem value="system">跟随系统</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="language">语言</Label>
          <Select
            value={settings.language}
            onValueChange={(value: any) => updateSettings({ language: value })}
          >
            <SelectTrigger id="language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="zh">中文</SelectItem>
              <SelectItem value="en">English</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}

function GeneralSection() {
  const { settings, updateSettings } = useAppStore();

  return (
    <Card>
      <CardHeader>
        <CardTitle>常规设置</CardTitle>
        <CardDescription>
          配置应用程序的常规行为
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="auto-sync">自动同步</Label>
            <p className="text-sm text-muted-foreground">
              定期自动同步星标仓库
            </p>
          </div>
          <Switch
            id="auto-sync"
            checked={settings.autoSync}
            onCheckedChange={(checked) => updateSettings({ autoSync: checked })}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="notifications">通知</Label>
            <p className="text-sm text-muted-foreground">
              启用桌面通知
            </p>
          </div>
          <Switch
            id="notifications"
            checked={settings.enableNotifications}
            onCheckedChange={(checked) => updateSettings({ enableNotifications: checked })}
          />
        </div>

        {settings.autoSync && (
          <div className="space-y-2">
            <Label htmlFor="sync-interval">同步间隔（秒）</Label>
            <Input
              id="sync-interval"
              type="number"
              value={settings.syncInterval}
              onChange={(e) => updateSettings({ syncInterval: parseInt(e.target.value) })}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
