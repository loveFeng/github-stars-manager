# Docker 单容器运行配置总结

## 🎯 概述

为 GitHub Stars Manager 项目添加了完整的单容器 Docker 运行方案，适用于快速部署和开发测试环境。

## 📦 新增文件

### 核心配置文件
- `Docker/Dockerfile.single` - 单容器多阶段构建文件
- `Docker/docker-compose.single.yml` - 单容器部署配置
- `Docker/start-single-container.sh` - 容器启动脚本

### Nginx 配置
- `Docker/nginx/docker-nginx.conf` - 单容器专用 Nginx 配置

### 文档和脚本
- `Docker/SINGLE_CONTAINER_GUIDE.md` - 详细使用指南 (421行)
- `Docker/.env.example.single` - 环境变量配置示例 (137行)
- `Docker/start-single.sh` - 一键启动脚本 (358行)

## 🚀 快速开始

### 最简单的启动方式

```bash
cd Docker
cp .env.example.single .env
# 编辑 .env 文件，填入 GitHub Token
./start-single.sh
```

### 标准 Docker Compose 方式

```bash
cd Docker
docker-compose -f docker-compose.single.yml up -d
```

### 直接 Docker 命令

```bash
docker build -f Docker/Dockerfile.single -t github-stars-manager .
docker run -d --name github-stars-manager -p 3000:3000 \
  -e GITHUB_TOKEN=your_token_here \
  github-stars-manager
```

## 🔧 技术特性

### 多阶段构建优化
- **前端构建**: Node.js Alpine，编译 React 应用
- **后端服务**: Python 3.9-slim，包含所有依赖
- **最终镜像**: 合并前端和后端，最小化镜像大小

### 资源管理
- **内存限制**: 2GB 限制，1GB 预留
- **CPU 限制**: 1 核心限制，0.5 核心预留
- **卷管理**: 3 个命名卷持久化数据

### 健康检查
- **端点**: `http://localhost:3000/health`
- **间隔**: 30秒
- **超时**: 10秒
- **重试**: 3次

### 网络架构
- **单一端口**: 3000 (外部) -> 3000 (内部)
- **Nginx 反向代理**: 静态文件 + API 代理
- **Python FastAPI**: 后端 API 服务

## 📊 对比优势

### 单容器 vs 多容器

| 特性 | 单容器 | 多容器 |
|------|--------|--------|
| 部署复杂度 | ⭐ 简单 | ⭐⭐⭐ 复杂 |
| 资源使用 | ⭐⭐ 较低 | ⭐ 较高 |
| 启动速度 | ⭐⭐⭐ 快 | ⭐⭐ 中等 |
| 维护难度 | ⭐⭐⭐ 容易 | ⭐ 中等 |
| 扩展能力 | ⭐ 有限 | ⭐⭐⭐ 优秀 |
| 监控能力 | ⭐⭐ 基础 | ⭐⭐⭐ 完整 |

### 适用场景

**单容器适合**:
- ✅ 个人使用和学习
- ✅ 开发环境测试
- ✅ 资源受限环境
- ✅ 快速原型验证

**多容器适合**:
- ✅ 生产环境部署
- ✅ 高并发访问
- ✅ 微服务架构
- ✅ 企业级应用

## 🔒 安全考虑

### 默认安全措施
- **非 root 运行**: Nginx 用户权限
- **网络隔离**: Bridge 网络模式
- **资源限制**: CPU 和内存限制
- **健康检查**: 自动监控服务状态

### 安全建议
- ✅ 修改默认密码和密钥
- ✅ 使用 HTTPS 生产部署
- ✅ 定期更新基础镜像
- ✅ 启用防火墙限制访问
- ✅ 配置数据备份策略

## 📈 性能优化

### 镜像优化
- **多阶段构建**: 减少最终镜像大小
- **Alpine Linux**: 轻量级基础镜像
- **依赖优化**: 仅安装必需包

### 运行时优化
- **Nginx 缓存**: 静态资源缓存
- **连接池**: HTTP keep-alive
- **压缩**: Gzip 压缩支持
- **数据库优化**: SQLite 索引和缓存

### 监控指标
- **内存使用**: < 1.5GB
- **CPU 使用**: < 80%
- **磁盘空间**: < 5GB
- **启动时间**: < 60秒

## 📁 文件结构

```
Docker/
├── Dockerfile.single           # 单容器构建文件
├── docker-compose.single.yml   # 单容器编排
├── start-single.sh             # 一键启动脚本
├── start-single-container.sh   # 容器内启动脚本
├── .env.example.single         # 环境变量示例
├── nginx/
│   └── docker-nginx.conf       # Nginx 配置
└── SINGLE_CONTAINER_GUIDE.md   # 详细指南文档
```

## 🔄 更新流程

### 应用更新
```bash
git pull origin main
docker-compose -f docker-compose.single.yml up -d --build
```

### 配置更新
```bash
# 修改 Docker/.env 文件
docker-compose -f docker-compose.single.yml restart
```

### 版本升级
```bash
# 备份数据
docker exec github-stars-manager sqlite3 /app/data/github_stars.db \
  ".backup /app/backup/v2_backup_$(date +%Y%m%d).db"

# 升级应用
docker-compose -f docker-compose.single.yml up -d --build
```

## 🛠️ 故障排除

### 常见问题解决

#### 1. 容器启动失败
```bash
# 查看详细错误
docker-compose -f docker-compose.single.yml up --build --verbose

# 检查端口占用
netstat -tulpn | grep 3000

# 重置环境
./start-single.sh --reset
```

#### 2. GitHub 认证问题
```bash
# 检查 Token 配置
docker exec github-stars-manager env | grep GITHUB_TOKEN

# 重新配置
docker-compose -f docker-compose.single.yml down
# 编辑 .env 文件
docker-compose -f docker-compose.single.yml up -d
```

#### 3. 资源不足
```bash
# 查看资源使用
docker stats github-stars-manager

# 调整资源限制
# 编辑 docker-compose.single.yml 中的 deploy.resources
```

## 📚 相关文档

- `Docker/SINGLE_CONTAINER_GUIDE.md` - 完整使用指南
- `Docker/.env.example.single` - 配置参数说明
- `Docker/start-single.sh` - 脚本帮助信息

## ✅ 验证清单

启动后请验证以下功能：

- [ ] 访问 http://localhost:3000 正常显示
- [ ] 健康检查 http://localhost:3000/health 返回正常
- [ ] GitHub Token 认证成功
- [ ] 仓库列表正常加载
- [ ] 数据持久化正常（重启后数据保留）
- [ ] 日志记录正常
- [ ] 资源使用在预期范围内

---

**创建时间**: 2025-10-31  
**适用版本**: v2.0.0+  
**维护状态**: ✅ 完成  
**文档状态**: ✅ 完整