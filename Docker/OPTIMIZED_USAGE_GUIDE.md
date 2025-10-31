# Docker Compose 优化配置使用指南

## 📋 概述

`docker-compose.optimized.yml` 是优化后的 Docker Compose 配置文件，包含以下改进：

- ✅ 资源限制配置
- ✅ 增强的日志管理
- ✅ 安全加固（Secrets、只读文件系统、能力限制）
- ✅ 网络隔离（多个独立网络）
- ✅ 自动备份服务
- ✅ 完整的监控栈
- ✅ Profile 配置（按需启动服务）

## 🚀 快速开始

### 1. 准备密钥文件

```bash
# 创建密钥目录
mkdir -p Docker/secrets
chmod 700 Docker/secrets

# 生成密钥
echo "your_db_password_here" > Docker/secrets/db_password.txt
echo "your_redis_password_here" > Docker/secrets/redis_password.txt
openssl rand -hex 32 > Docker/secrets/jwt_secret.txt

# 设置权限
chmod 600 Docker/secrets/*.txt
```

### 2. 配置环境变量

```bash
cd Docker
cp .env.example .env
# 编辑 .env 文件，设置必要的环境变量
nano .env
```

### 3. 启动服务

#### 基础服务（生产环境）
```bash
docker-compose -f docker-compose.optimized.yml up -d
```

#### 包含开发工具
```bash
docker-compose -f docker-compose.optimized.yml --profile tools up -d
```

#### 包含监控服务
```bash
docker-compose -f docker-compose.optimized.yml --profile monitoring up -d
```

#### 包含备份服务
```bash
docker-compose -f docker-compose.optimized.yml --profile backup up -d
```

#### 完整环境
```bash
docker-compose -f docker-compose.optimized.yml \
  --profile tools \
  --profile monitoring \
  --profile backup \
  up -d
```

## 📊 服务说明

### 核心服务（默认启动）

| 服务 | 端口 | 资源限制 | 说明 |
|------|------|----------|------|
| nginx | 80, 443 | 0.5 CPU / 256M | 反向代理 |
| frontend | - | 0.5 CPU / 512M | React 前端 |
| backend | 3001 | 1.0 CPU / 1G | Node.js API |
| postgres | 5432 | 2.0 CPU / 2G | 数据库 |
| redis | 6379 | 0.5 CPU / 512M | 缓存 |

### 工具服务（--profile tools）

| 服务 | 端口 | 说明 |
|------|------|------|
| pgadmin | 5050 | 数据库管理界面 |

### 监控服务（--profile monitoring）

| 服务 | 端口 | 说明 |
|------|------|------|
| prometheus | 9090 | 监控数据收集 |
| grafana | 3000 | 数据可视化 |
| node-exporter | 9100 | 系统指标导出 |

### 备份服务（--profile backup）

| 服务 | 说明 |
|------|------|
| db-backup | 每日自动备份数据库 |

## 🔒 安全配置

### 1. Secrets 管理

优化配置使用 Docker Secrets 管理敏感信息：

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

### 2. 容器安全

所有容器都配置了：
- `no-new-privileges`: 防止权限提升
- `cap_drop: ALL`: 移除所有能力
- `cap_add`: 仅添加必要的能力

### 3. 网络隔离

- `frontend-network`: 前端服务
- `backend-network`: 后端服务
- `database-network`: 数据库（内部网络）
- `cache-network`: 缓存（内部网络）
- `monitoring-network`: 监控服务

数据库和缓存网络标记为 `internal: true`，无法从外部访问。

### 4. 只读文件系统

前端服务使用只读文件系统，临时文件使用 tmpfs：

```yaml
read_only: true
tmpfs:
  - /tmp
  - /var/cache/nginx
  - /var/run
```

## 📦 资源限制

所有服务都配置了资源限制，防止资源耗尽：

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## 📝 日志管理

### 1. 日志轮转配置

所有服务都配置了日志限制：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"      # 单文件最大 10MB
    max-file: "3"        # 保留 3 个文件
    compress: "true"     # 压缩旧日志
    tag: "service/{{.ID}}"
```

### 2. 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.optimized.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.optimized.yml logs -f backend

# 查看最近 100 行
docker-compose -f docker-compose.optimized.yml logs --tail=100 backend
```

## 💾 备份和恢复

### 自动备份

备份服务每天自动备份数据库：
- 备份时间：每天一次（默认）
- 保留时间：7 天
- 备份格式：PostgreSQL custom format (压缩)
- 存储位置：`postgres-backups` 数据卷

### 手动备份

```bash
# 启动备份服务
docker-compose -f docker-compose.optimized.yml --profile backup up -d db-backup

# 手动触发备份
docker-compose -f docker-compose.optimized.yml exec db-backup /backup.sh
```

### 恢复备份

```bash
# 列出备份文件
docker-compose -f docker-compose.optimized.yml exec db-backup ls -lh /backups

# 恢复备份
docker-compose -f docker-compose.optimized.yml exec -T postgres pg_restore \
  -U app_user \
  -d github_stars_db \
  -c \
  /backups/backup_20251031_020000.dump.gz
```

## 📊 监控和告警

### 访问监控界面

启动监控服务后，可以访问：

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)

### 配置告警

编辑 `alertmanager/alerts.yml` 文件添加告警规则：

```yaml
groups:
  - name: container_alerts
    rules:
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.85
        for: 5m
        labels:
          severity: warning
```

## 🔧 维护操作

### 更新服务

```bash
# 拉取最新镜像
docker-compose -f docker-compose.optimized.yml pull

# 重新启动服务
docker-compose -f docker-compose.optimized.yml up -d
```

### 清理资源

```bash
# 停止所有服务
docker-compose -f docker-compose.optimized.yml down

# 清理未使用的资源
docker system prune -f

# 清理未使用的卷（谨慎！）
docker volume prune -f
```

### 查看资源使用

```bash
# 查看容器资源使用情况
docker stats $(docker-compose -f docker-compose.optimized.yml ps -q)
```

## 🐛 故障排除

### 容器无法启动

```bash
# 查看容器状态
docker-compose -f docker-compose.optimized.yml ps

# 查看错误日志
docker-compose -f docker-compose.optimized.yml logs [service_name]

# 检查健康状态
docker-compose -f docker-compose.optimized.yml ps | grep unhealthy
```

### 网络连接问题

```bash
# 检查网络
docker network ls | grep github-stars

# 检查网络连接
docker-compose -f docker-compose.optimized.yml exec backend ping postgres
```

### 权限问题

```bash
# 检查密钥文件权限
ls -la Docker/secrets/

# 重新设置权限
chmod 600 Docker/secrets/*.txt
```

## 📈 性能调优

### PostgreSQL 优化

数据库已配置性能优化参数：
- `shared_buffers`: 256MB
- `effective_cache_size`: 1GB
- `work_mem`: 16MB
- `maintenance_work_mem`: 128MB

根据实际硬件调整这些参数。

### Redis 优化

Redis 配置文件 `redis.conf` 包含：
- `maxmemory`: 256MB
- `maxmemory-policy`: allkeys-lru
- AOF 持久化

### Nginx 优化

Nginx 配置包含：
- Gzip 压缩
- 静态资源缓存
- 连接池优化

## 🔄 从旧配置迁移

### 1. 备份数据

```bash
# 使用旧配置备份数据
docker-compose exec postgres pg_dump -U app_user github_stars_db > backup.sql
```

### 2. 停止旧服务

```bash
docker-compose down
```

### 3. 启动新配置

```bash
# 准备密钥
mkdir -p Docker/secrets
echo "your_password" > Docker/secrets/db_password.txt

# 启动新服务
docker-compose -f docker-compose.optimized.yml up -d
```

### 4. 恢复数据

```bash
# 恢复数据
docker-compose -f docker-compose.optimized.yml exec -T postgres psql -U app_user github_stars_db < backup.sql
```

## 📚 相关文档

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Docker 安全最佳实践](https://docs.docker.com/engine/security/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)

## ⚠️ 注意事项

1. **首次启动前**：必须创建密钥文件
2. **生产环境**：修改所有默认密码
3. **资源限制**：根据实际硬件调整资源限制
4. **备份**：定期验证备份是否可用
5. **监控**：配置告警通知渠道
6. **更新**：定期更新镜像和依赖

## 🤝 支持

如有问题或建议，请：
1. 查看测试报告 `docker_test_report.md`
2. 查看原始配置 `docker-compose.yml`
3. 提交 Issue 或 Pull Request
