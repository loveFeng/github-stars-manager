# Docker 容器化部署指南

本指南详细说明了如何使用 Docker 和 Docker Compose 部署全栈应用。

## 目录结构

```
Docker/
├── docker-compose.yml          # 主配置文件
├── Dockerfile                  # 多阶段构建文件
├── nginx.conf                  # Nginx 反向代理配置
├── .env.example                # 环境变量模板
├── redis.conf                  # Redis 配置
├── prometheus.yml              # Prometheus 监控配置
├── pgadmin-servers.json        # pgAdmin 服务器配置
├── grafana/                    # Grafana 配置
│   ├── datasources/
│   └── dashboards/
├── deploy.md                   # 本部署指南
└── Makefile                    # 便捷部署命令
```

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- Docker Engine 20.10+
- Docker Compose 2.0+

```bash
# 检查版本
docker --version
docker-compose --version
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**重要配置项：**
- `DB_PASSWORD`: 设置强密码
- `JWT_SECRET`: 设置 JWT 密钥
- `APP_URL`: 设置实际域名
- `MAIL_*`: 邮件服务配置

### 3. 启动服务

```bash
# 一键启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 访问应用

- **前端应用**: http://localhost
- **后端 API**: http://localhost/api
- **API 文档**: http://localhost/api-docs (如果有)
- **pgAdmin**: http://localhost:5050 (开发工具)

## 详细部署步骤

### 步骤 1: 准备项目文件

确保项目根目录包含以下结构：

```
your-project/
├── backend/                    # 后端代码
│   ├── src/
│   ├── package.json
│   └── ...
├── frontend/                   # 前端代码
│   ├── src/
│   ├── package.json
│   └── ...
├── Docker/
├── docker-compose.yml
└── .env
```

### 步骤 2: 构建镜像

```bash
# 构建所有服务
docker-compose build

# 仅构建特定服务
docker-compose build frontend
docker-compose build backend

# 使用缓存构建
docker-compose build --no-cache
```

### 步骤 3: 初始化数据库

```bash
# 等待数据库启动
docker-compose up -d postgres redis

# 查看数据库日志
docker-compose logs postgres

# 手动运行迁移 (如果需要)
docker-compose exec backend npm run migration
```

### 步骤 4: 配置 SSL (生产环境)

```bash
# 创建 SSL 目录
mkdir -p ssl

# 使用 Let's Encrypt (推荐)
certbot certonly --standalone -d yourdomain.com

# 复制证书
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem

# 或使用自签名证书 (测试环境)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem
```

### 步骤 5: 启动所有服务

```bash
# 后台启动所有服务
docker-compose up -d

# 启动特定配置文件
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 启动开发环境
docker-compose --profile development up -d

# 启动监控环境
docker-compose --profile monitoring up -d
```

## 常用操作命令

### 服务管理

```bash
# 查看所有服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f [service_name]

# 重启特定服务
docker-compose restart [service_name]

# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重新创建服务
docker-compose up -d --force-recreate [service_name]
```

### 数据库操作

```bash
# 连接数据库
docker-compose exec postgres psql -U app_user -d myapp_db

# 备份数据库
docker-compose exec postgres pg_dump -U app_user myapp_db > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U app_user myapp_db < backup.sql

# 查看数据库大小
docker-compose exec postgres psql -U app_user -d myapp_db -c "
  SELECT pg_size_pretty(pg_database_size('myapp_db'));"
```

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f --tail=100

# 查看特定服务日志
docker-compose logs -f nginx

# 查看最近 1 小时的日志
docker-compose logs --since=1h

# 导出日志到文件
docker-compose logs > app.log
```

### 健康检查

```bash
# 检查所有服务健康状态
curl http://localhost/health

# 检查后端 API
curl http://localhost/api/health

# 检查数据库连接
docker-compose exec postgres pg_isready -U app_user

# 检查 Redis 连接
docker-compose exec redis redis-cli ping
```

### 数据备份和恢复

```bash
# 创建备份
./scripts/backup.sh

# 恢复备份
./scripts/restore.sh backup_20231201.sql

# 自动化备份 (添加到 crontab)
0 2 * * * /path/to/scripts/backup.sh
```

## 环境配置

### 开发环境

```bash
# 启动开发环境
docker-compose --profile development up -d

# 功能包括：
# - 热重载
# - 调试端口
# - pgAdmin 管理工具
```

### 生产环境

```bash
# 使用生产配置
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 或直接使用标准配置
docker-compose up -d
```

### 监控环境

```bash
# 启动监控服务
docker-compose --profile monitoring up -d

# 访问地址：
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin123)
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :80
   netstat -tulpn | grep :443
   
   # 修改 docker-compose.yml 中的端口映射
   ports:
     - "8080:80"  # 改为其他端口
   ```

2. **权限问题**
   ```bash
   # 设置正确的文件权限
   sudo chown -R $USER:$USER .
   chmod +x scripts/*.sh
   ```

3. **内存不足**
   ```bash
   # 增加 Docker 内存限制
   # Docker Desktop: Settings > Resources > Memory
   ```

4. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose logs postgres
   
   # 验证连接配置
   docker-compose exec postgres pg_isready -U app_user
   ```

### 日志分析

```bash
# 错误日志分析
docker-compose logs | grep ERROR

# 性能问题排查
docker stats

# 容器资源使用
docker-compose exec backend top
```

### 网络调试

```bash
# 测试容器间网络
docker-compose exec nginx ping backend

# 查看网络配置
docker network ls
docker network inspect docker_app-network

# DNS 解析测试
docker-compose exec nginx nslookup postgres
```

## 性能优化

### 镜像优化

1. **多阶段构建**: 使用构建时依赖减少最终镜像大小
2. **Alpine 基础镜像**: 选择轻量级基础镜像
3. **.dockerignore**: 排除不必要文件

### 容器优化

1. **资源限制**: 在 docker-compose.yml 中设置限制
2. **健康检查**: 配置适当的健康检查
3. **日志轮转**: 避免日志文件过大

### 数据库优化

1. **连接池**: 配置适当的数据库连接池
2. **索引优化**: 确保关键字段有索引
3. **查询优化**: 使用 EXPLAIN 分析查询

## 安全配置

### 网络安全

1. **内部网络**: 容器间使用自定义网络
2. **防火墙**: 配置适当的防火墙规则
3. **SSL/TLS**: 生产环境强制使用 HTTPS

### 身份验证

1. **强密码**: 使用复杂密码
2. **JWT 密钥**: 设置强密钥并定期轮换
3. **API 限流**: 配置 API 访问限流

### 数据保护

1. **数据加密**: 敏感数据加密存储
2. **备份加密**: 备份文件加密
3. **访问控制**: 限制数据库访问权限

## 监控和告警

### 监控指标

- CPU、内存、磁盘使用率
- API 响应时间和错误率
- 数据库连接数和查询性能
- 容器健康状态

### 告警配置

```bash
# Grafana 告警规则示例
# 在 grafana/dashboards/ 中添加告警规则
```

### 日志聚合

```bash
# 使用 ELK Stack 或类似工具
# - Elasticsearch: 日志存储和搜索
# - Logstash: 日志处理和转换
# - Kibana: 日志可视化和分析
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
# .github/workflows/deploy.yml
name: Deploy to Docker

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Docker
        run: |
          docker-compose up -d --build
          docker-compose exec backend npm test
```

### Docker Registry

```bash
# 构建并推送镜像
docker build -t myapp:latest .
docker tag myapp:latest registry.example.com/myapp:latest
docker push registry.example.com/myapp:latest
```

## 维护和更新

### 定期维护

1. **更新依赖**: 定期更新容器镜像
2. **安全补丁**: 及时应用安全更新
3. **性能监控**: 定期检查性能指标
4. **备份验证**: 定期测试备份恢复

### 版本更新

```bash
# 拉取最新镜像
docker-compose pull

# 重新构建并更新
docker-compose up -d --build

# 数据库迁移 (如果需要)
docker-compose exec backend npm run migrate
```

### 灾难恢复

1. **备份策略**: 定期自动备份
2. **恢复流程**: 测试恢复流程
3. **监控告警**: 设置关键指标告警
4. **文档更新**: 保持文档最新

## 支持和帮助

如需技术支持，请：

1. 查看日志文件: `docker-compose logs`
2. 检查服务状态: `docker-compose ps`
3. 参考本文档的故障排除部分
4. 提交 Issue 到项目仓库

## 更新日志

- v1.0.0: 初始版本，支持基础部署
- v1.1.0: 添加监控和告警功能
- v1.2.0: 优化安全配置和性能