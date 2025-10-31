# GitHub Stars Manager - 单容器运行指南

## 📦 概述

本指南将帮助您使用单个 Docker 容器运行 GitHub Stars Manager 项目。这种方式适用于：
- 快速体验和测试
- 开发环境部署
- 资源受限的环境
- 个人使用场景

## 🎯 单容器 vs 多容器对比

| 特性 | 单容器 | 多容器 |
|------|--------|--------|
| 资源使用 | 较低 | 较高 |
| 启动速度 | 快 | 较慢 |
| 维护复杂度 | 简单 | 复杂 |
| 扩展性 | 有限 | 优秀 |
| 监控能力 | 基础 | 完整 |
| 适用场景 | 个人/开发 | 生产/企业 |

## 🚀 快速开始

### 1. 准备环境

确保已安装 Docker 和 Docker Compose：

```bash
# 检查 Docker 版本
docker --version
docker-compose --version

# 或者使用新的 docker compose 命令
docker compose version
```

### 2. 创建配置文件

创建环境变量文件：

```bash
# 在项目根目录创建
cp Docker/.env.example Docker/.env

# 编辑配置
nano Docker/.env
```

编辑 `.env` 文件，填入必要的配置：

```bash
# 必需的 GitHub 配置
GITHUB_TOKEN=your_github_personal_access_token

# 可选的 AI 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_URL=https://api.openai.com/v1

# 可选的 WebDAV 备份配置
WEBDAV_URL=your_webdav_url
WEBDAV_USERNAME=your_webdav_username
WEBDAV_PASSWORD=your_webdav_password
```

### 3. 构建和运行

#### 方式一：使用 Docker Compose（推荐）

```bash
cd Docker

# 构建并启动
docker-compose -f docker-compose.single.yml up -d

# 查看日志
docker-compose -f docker-compose.single.yml logs -f

# 停止服务
docker-compose -f docker-compose.single.yml down
```

#### 方式二：直接使用 Docker 命令

```bash
# 构建镜像
docker build -f Docker/Dockerfile.single -t github-stars-manager .

# 运行容器
docker run -d \
  --name github-stars-manager \
  -p 3000:3000 \
  -v github_stars_data:/app/data \
  -v github_stars_logs:/app/logs \
  -v github_stars_backup:/app/backup \
  -e GITHUB_TOKEN=your_token \
  -e OPENAI_API_KEY=your_key \
  github-stars-manager
```

### 4. 访问应用

启动成功后，访问：
- **Web 界面**: http://localhost:3000
- **健康检查**: http://localhost:3000/health

## 🔧 配置详解

### 环境变量

#### 必需配置
```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 可选配置
```bash
# AI 功能
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_URL=https://api.openai.com/v1

# 备份功能
WEBDAV_URL=https://your-webdav-server.com/backup
WEBDAV_USERNAME=your_username
WEBDAV_PASSWORD=your_password

# 应用配置
PORT=3000
DB_PATH=/app/data/github_stars.db
ENVIRONMENT=production
```

### 数据持久化

容器使用命名卷来持久化数据：

- **github_stars_data**: SQLite 数据库文件
- **github_stars_logs**: 应用日志
- **github_stars_backup**: 备份文件

```bash
# 查看卷
docker volume ls | grep github_stars

# 备份数据卷
docker run --rm -v github_stars_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/github_stars_data_backup.tar.gz /data

# 恢复数据卷
docker run --rm -v github_stars_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/github_stars_data_backup.tar.gz -C /
```

## 📊 监控和管理

### 查看容器状态

```bash
# 查看容器运行状态
docker ps | grep github-stars-manager

# 查看资源使用
docker stats github-stars-manager

# 查看日志
docker logs -f github-stars-manager

# 进入容器
docker exec -it github-stars-manager /bin/bash
```

### 健康检查

```bash
# 手动健康检查
curl http://localhost:3000/health

# 查看容器健康状态
docker inspect --format='{{.State.Health.Status}}' github-stars-manager
```

### 日志管理

```bash
# 查看应用日志
docker exec github-stars-manager tail -f /app/logs/app.log

# 查看 nginx 日志
docker exec github-stars-manager tail -f /var/log/nginx/access.log

# 清理旧日志
docker exec github-stars-manager find /app/logs -name "*.log" -mtime +7 -delete
```

## 🔍 故障排除

### 常见问题

#### 1. 容器无法启动

**症状**: `docker-compose up` 失败

**解决方案**:
```bash
# 查看详细错误信息
docker-compose -f docker-compose.single.yml up --build --verbose

# 检查端口是否被占用
netstat -tulpn | grep 3000

# 清理并重新构建
docker system prune -a
docker-compose -f docker-compose.single.yml up --build --force-recreate
```

#### 2. GitHub 认证失败

**症状**: 无法同步仓库，提示认证错误

**解决方案**:
```bash
# 检查 Token 是否正确
echo $GITHUB_TOKEN | wc -c  # Token 长度应该是 41

# 重新设置环境变量
docker-compose -f docker-compose.single.yml down
# 编辑 Docker/.env 文件
docker-compose -f docker-compose.single.yml up -d
```

#### 3. 端口冲突

**症状**: 端口 3000 已被占用

**解决方案**:
```bash
# 修改 docker-compose.single.yml 中的端口映射
ports:
  - "3001:3000"  # 使用 3001 端口访问

# 或者停止占用端口的进程
docker ps | grep :3000
docker stop <container_id>
```

#### 4. 内存不足

**症状**: 容器频繁重启

**解决方案**:
```bash
# 检查内存使用
docker stats github-stars-manager

# 限制资源使用
# 在 docker-compose.single.yml 中添加：
deploy:
  resources:
    limits:
      memory: 1G
```

### 调试命令

```bash
# 进入容器调试
docker exec -it github-stars-manager /bin/bash

# 检查数据库
sqlite3 /app/data/github_stars.db ".tables"

# 测试网络连接
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/starred

# 查看进程
docker exec github-stars-manager ps aux

# 检查磁盘空间
docker exec github-stars-manager df -h
```

## 🔄 更新和迁移

### 更新应用

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose -f docker-compose.single.yml up -d --build

# 验证更新
docker exec github-stars-manager cat /app/version.txt
```

### 数据迁移

```bash
# 导出数据
docker exec github-stars-manager sqlite3 /app/data/github_stars.db \
  ".backup /app/backup/migration_$(date +%Y%m%d).db"

# 迁移到新的 Docker 环境
docker run --rm -v old_data:/old -v new_data:/new \
  alpine cp -r /old/* /new/
```

## 🛡️ 安全建议

### 1. 网络安全

```bash
# 使用防火墙限制访问
ufw allow 3000
ufw enable

# 考虑使用反向代理（Traefik、Caddy）
```

### 2. 数据安全

```bash
# 定期备份数据
docker run --rm -v github_stars_data:/data \
  -v $(pwd):/backup alpine tar czf \
  /backup/github_stars_$(date +%Y%m%d).tar.gz /data

# 加密重要配置
echo "ENCRYPTED_CONFIG=$(echo 'your_config' | base64)" > .env.encrypted
```

### 3. 容器安全

```bash
# 使用非 root 用户运行
# Dockerfile.single 已配置 nginx 用户

# 限制容器权限
docker run --read-only --tmpfs /tmp github-stars-manager
```

## 📈 性能优化

### 1. 资源优化

```bash
# 调整资源限制
# 在 docker-compose.single.yml 中：
deploy:
  resources:
    limits:
      cpus: '1.5'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 1G
```

### 2. 数据库优化

```bash
# 进入容器执行数据库优化
docker exec -it github-stars-manager sqlite3 /app/data/github_stars.db "
VACUUM;
ANALYZE;
PRAGMA optimize;
"
```

### 3. 缓存优化

```bash
# 配置 nginx 缓存
# 在 docker-nginx.conf 中调整缓存设置
```

## 🚀 生产环境部署

虽然单容器适用于开发和测试，但生产环境建议：

1. **使用反向代理**: Nginx、Caddy、Traefik
2. **启用 HTTPS**: 使用 Let's Encrypt
3. **监控集成**: Prometheus + Grafana
4. **日志聚合**: ELK Stack 或 Loki
5. **备份策略**: 自动化定时备份

示例生产配置：

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    # ... 单容器配置
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
```

---

## 📞 获取帮助

- **项目 Issues**: [GitHub Issues](https://github.com/loveFeng/github-stars-manager/issues)
- **文档**: 查看 `docs/` 目录下的详细文档
- **社区**: 参与 GitHub Discussions

---

**最后更新**: 2025-10-31  
**适用版本**: v2.0.0+  
**维护者**: MiniMax Agent