import { NavLink } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';
import { Star, GitPullRequest, Settings, FolderTree } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

const navigation = [
  { name: '星标仓库', href: '/repositories', icon: Star },
  { name: 'Release 订阅', href: '/releases', icon: GitPullRequest },
  { name: '设置', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const { defaultCategories, customCategories } = useAppStore();
  const allCategories = [...defaultCategories, ...customCategories];

  return (
    <div className="fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 border-r bg-background">
      <ScrollArea className="h-full py-4">
        <div className="px-3 space-y-4">
          <div className="space-y-1">
            <h2 className="mb-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              导航
            </h2>
            {navigation.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all hover:bg-accent',
                    isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </NavLink>
            ))}
          </div>

          <Separator />

          <div className="space-y-1">
            <h2 className="mb-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2">
              <FolderTree className="h-3 w-3" />
              分类
            </h2>
            {allCategories.map((category) => (
              <button
                key={category.id}
                className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all hover:bg-accent text-muted-foreground"
              >
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: category.color }}
                />
                {category.name}
              </button>
            ))}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
