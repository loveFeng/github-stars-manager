# Docker 容器化方案概览

## 项目简介

本 Docker 容器化方案为全栈应用提供了完整的容器化部署解决方案，支持生产环境的高可用、高性能部署。

## 架构组件

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│      Nginx      │    │     Frontend    │    │     Backend     │
│   (反向代理)     │    │   (React/Vue)   │    │   (Node.js)     │
│   端口: 80/443  │    │   端口: 3000    │    │   端口: 3001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │      Redis      │    │     监控服务     │
│    (数据库)      │    │     (缓存)      │    │  (Prometheus    │
│   端口: 5432    │    │   端口: 6379    │    │   + Grafana)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 核心特性

### 🚀 高性能
- **多阶段构建**: 优化镜像大小，提升构建效率
- **缓存策略**: 静态资源缓存，API 响应缓存
- **Gzip 压缩**: 减少传输大小，提升加载速度
- **连接池**: 数据库连接复用，降低连接开销

### 🔒 安全加固
- **CORS 配置**: 完善的跨域资源共享配置
- **安全头**: XSS 防护、内容类型嗅探保护等
- **限流控制**: API 访问频率限制
- **容器安全**: 非 root 用户运行，最小权限原则

### 📊 监控告警
- **应用指标**: 响应时间、错误率、吞吐量
- **系统指标**: CPU、内存、磁盘、网络使用率
- **业务指标**: 用户活跃度、API 调用统计
- **告警通知**: 多渠道告警推送

### 🔄 高可用
- **健康检查**: 容器和应用健康状态监控
- **自动重启**: 故障容器自动重启
- **负载均衡**: Nginx 反向代理负载均衡
- **数据持久化**: 数据卷持久化存储

### 🛠 开发友好
- **开发模式**: 热重载、调试端口、pgAdmin
- **一键部署**: Makefile 简化部署操作
- **环境隔离**: 多环境配置支持
- **文档完善**: 详细的部署和维护文档

## 文件结构

```
Docker/
├── 📄 docker-compose.yml              # 主服务编排配置
├── 📄 Dockerfile                      # 多阶段构建配置
├── 📄 nginx.conf                      # Nginx 反向代理配置
├── 📄 .env.example                    # 环境变量模板
├── 📄 redis.conf                      # Redis 配置
├── 📄 init.sql                        # 数据库初始化脚本
├── 📄 nginx-frontend.conf             # 前端专用 Nginx 配置
├── 📄 prometheus.yml                  # Prometheus 监控配置
├── 📄 pgadmin-servers.json            # pgAdmin 服务器配置
├── 📄 Makefile                        # 便捷部署命令
├── 📄 deploy.md                       # 详细部署指南
├── 📄 trivy.yaml.example              # 安全扫描配置
├── 📄 .dockerignore.example           # Docker 忽略文件示例
│
├── 📁 grafana/                        # Grafana 配置
│   ├── 📁 datasources/
│   │   └── 📄 prometheus.yml
│   └── 📁 dashboards/
│       └── 📄 dashboard.yml
│
├── 📁 scripts/                        # 辅助脚本
│   ├── 📄 backup.sh                   # 数据备份脚本
│   └── 📄 restore.sh                  # 数据恢复脚本
│
└── 📁 ci-cd/                          # CI/CD 配置
    └── 📁 .github/workflows/
        └── 📄 docker-build-deploy.yml # GitHub Actions 工作流
```

## 快速开始

### 1️⃣ 环境准备
```bash
# 安装 Docker 和 Docker Compose
sudo apt update
sudo apt install docker.io docker-compose

# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 验证安装
docker --version
docker-compose --version
```

### 2️⃣ 项目配置
```bash
# 进入项目目录
cd /path/to/your/project

# 复制环境变量模板
cp Docker/.env.example .env

# 编辑配置文件
nano .env
```

### 3️⃣ 一键部署
```bash
# 使用 Makefile 快速部署
cd Docker
make setup    # 初始化环境
make up       # 启动所有服务

# 或使用 Docker Compose
docker-compose up -d
```

### 4️⃣ 验证部署
```bash
# 检查服务状态
make status

# 查看日志
make logs

# 健康检查
make health
```

## 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端应用 | http://localhost | 主应用界面 |
| 后端 API | http://localhost/api | API 接口 |
| pgAdmin | http://localhost:5050 | 数据库管理工具 |
| Prometheus | http://localhost:9090 | 监控指标 |
| Grafana | http://localhost:3000 | 监控面板 |

## 常用命令

### 基础操作
```bash
make setup          # 初始化项目
make up             # 启动所有服务
make down           # 停止所有服务
make restart        # 重启所有服务
make status         # 查看服务状态
make logs           # 查看日志
```

### 开发环境
```bash
make dev            # 启动开发环境
make dev-down       # 停止开发环境
make shell-backend  # 进入后端容器
make shell-frontend # 进入前端容器
```

### 监控环境
```bash
make monitoring     # 启动监控环境
make monitoring-down # 停止监控环境
```

### 数据库操作
```bash
make db-shell       # 连接数据库
make db-backup      # 备份数据库
make db-restore     # 恢复数据库
make db-migrate     # 运行数据库迁移
```

### 维护操作
```bash
make build          # 构建镜像
make rebuild        # 重新构建
make update         # 更新服务
make clean          # 清理资源
make clean-logs     # 清理日志
```

## 配置说明

### 环境变量
- `.env`: 主要配置文件，包含数据库、Redis、邮件等服务配置
- 支持多环境配置：开发、测试、生产

### 数据卷
- `postgres-data`: PostgreSQL 数据持久化
- `redis-data`: Redis 数据持久化
- `static-files`: 前端静态文件
- `uploads`: 用户上传文件

### 网络配置
- `app-network`: 应用内部网络，172.20.0.0/16
- 容器间通过服务名通信
- 外部访问通过 Nginx 代理

## 监控告警

### 指标监控
- **应用指标**: 响应时间、吞吐量、错误率
- **资源指标**: CPU、内存、磁盘使用率
- **业务指标**: 用户注册、登录、数据操作

### 告警规则
- **服务不可用**: 容器退出、健康检查失败
- **资源过载**: CPU > 80%、内存 > 85%
- **响应异常**: API 响应时间 > 3秒、错误率 > 5%

### 通知渠道
- **邮件**: 运维团队邮件通知
- **Slack/Teams**: 团队协作平台通知
- **WebHook**: 自定义回调通知

## 安全考虑

### 网络安全
- 容器间网络隔离
- 外部访问通过 Nginx 代理
- HTTPS 强制重定向

### 身份认证
- JWT 令牌认证
- API 密钥认证
- 数据库连接密码

### 数据保护
- 敏感数据加密存储
- 定期数据备份
- 访问日志审计

### 容器安全
- 非 root 用户运行
- 最小权限原则
- 定期安全扫描

## 性能优化

### 构建优化
- 多阶段构建减少镜像大小
- 层缓存提升构建速度
- .dockerignore 排除不必要文件

### 运行时优化
- 连接池复用数据库连接
- Redis 缓存热点数据
- 静态资源 CDN 加速

### 监控优化
- 指标采样减少性能影响
- 异步日志记录
- 智能告警降噪

## 扩展能力

### 水平扩展
```yaml
# docker-compose.yml 中的扩展配置
backend:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: '0.50'
        memory: 512M
      reservations:
        cpus: '0.25'
        memory: 256M
```

### 垂直扩展
- 调整容器资源限制
- 数据库参数优化
- Nginx 连接数优化

### 功能扩展
- 添加消息队列 (RabbitMQ)
- 搜索引擎 (Elasticsearch)
- 对象存储 (MinIO)
- 任务调度 (Celery)

## 故障排除

### 常见问题
1. **端口冲突**: 修改 docker-compose.yml 中的端口映射
2. **权限问题**: 设置正确的文件权限和用户组
3. **内存不足**: 增加 Docker 内存限制
4. **网络问题**: 检查容器网络配置

### 日志分析
```bash
# 查看服务日志
make logs-nginx
make logs-backend
make logs-postgres

# 查看系统资源
make stats
make top
```

### 健康检查
```bash
# 检查所有服务
make health

# 检查特定服务
docker-compose ps
docker inspect <container_id>
```

## 最佳实践

### 开发阶段
1. 使用开发模式进行热重载
2. 启用 pgAdmin 进行数据库管理
3. 使用 Redis 进行缓存开发
4. 配置适当的日志级别

### 测试阶段
1. 运行集成测试验证功能
2. 执行性能测试评估性能
3. 进行安全扫描排查漏洞
4. 测试备份恢复流程

### 生产阶段
1. 配置 SSL 证书启用 HTTPS
2. 设置监控告警及时发现问题
3. 定期备份数据确保安全
4. 持续更新依赖保持安全

### 维护阶段
1. 定期更新容器镜像
2. 清理日志文件防止磁盘满
3. 监控系统资源使用情况
4. 更新文档保持同步

## 总结

本 Docker 容器化方案提供了：

✅ **完整的部署方案**: 从开发到生产的全流程支持  
✅ **高可用架构**: 负载均衡、健康检查、自动重启  
✅ **安全加固**: 多层安全防护、容器安全、权限控制  
✅ **监控告警**: 全面监控指标、智能告警通知  
✅ **开发友好**: 一键部署、便捷操作、详细文档  
✅ **可扩展性**: 支持水平和垂直扩展、功能扩展  

适用于中小型团队的全栈应用部署需求，可根据实际项目特点进行调整和优化。

---

**更多详细信息请参考**: [deploy.md](./deploy.md) | [Makefile](./Makefile) | [docker-compose.yml](./docker-compose.yml)