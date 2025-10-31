# =============================================================================
# 多阶段构建 Dockerfile
# 支持前端 (React/Vue) 和后端 (Node.js) 应用
# =============================================================================

# -----------------------------------------------------------------------------
# 阶段1: 前端构建环境
# -----------------------------------------------------------------------------
FROM node:18-alpine AS frontend-builder

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./
COPY frontend/package*.json ./frontend/

# 安装依赖
RUN npm ci --only=production && npm cache clean --force

# 复制前端源代码
COPY frontend/ ./

# 构建前端应用
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

RUN if [ "$NODE_ENV" = "production" ]; then \
    npm run build; \
    else \
    npm run build:dev; \
    fi

# -----------------------------------------------------------------------------
# 阶段2: 后端构建环境
# -----------------------------------------------------------------------------
FROM node:18-alpine AS backend-builder

WORKDIR /app

# 复制 package.json
COPY package*.json ./
COPY backend/package*.json ./backend/

# 安装依赖
RUN npm ci --only=production && npm cache clean --force

# 复制后端源代码
COPY backend/ ./

# 构建后端应用 (如果需要)
RUN npm run build || echo "No build script found"

# -----------------------------------------------------------------------------
# 阶段3: 前端生产镜像
# -----------------------------------------------------------------------------
FROM nginx:alpine AS frontend

# 安装必要的包
RUN apk add --no-cache \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# 复制构建产物
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY Docker/nginx-frontend.conf /etc/nginx/conf.d/default.conf

# 创建日志目录
RUN mkdir -p /var/log/nginx

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["nginx", "-g", "daemon off;"]

# -----------------------------------------------------------------------------
# 阶段4: 后端生产镜像
# -----------------------------------------------------------------------------
FROM node:18-alpine AS backend

# 安装运行时依赖
RUN apk add --no-cache \
    curl \
    bash \
    tini \
    && rm -rf /var/cache/apk/*

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# 设置工作目录
WORKDIR /app

# 复制 package.json
COPY --from=backend-builder /app/package*.json ./

# 安装生产依赖
RUN npm ci --only=production && npm cache clean --force

# 复制应用代码
COPY --from=backend-builder --chown=nextjs:nodejs /app/dist ./dist || true
COPY --chown=nextjs:nodejs backend/ ./src/

# 复制其他必要文件
COPY --chown=nextjs:nodejs backend/ ./

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads && \
    chown -R nextjs:nodejs /app

# 切换到非 root 用户
USER nextjs

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# 暴露端口
EXPOSE 3001

# 使用 tini 作为 init 进程
ENTRYPOINT ["/sbin/tini", "--"]

# 启动命令
CMD ["node", "src/index.js"]

# -----------------------------------------------------------------------------
# 阶段5: 完整应用镜像 (开发和测试)
# -----------------------------------------------------------------------------
FROM node:18-alpine AS development

WORKDIR /app

# 安装开发依赖
COPY package*.json ./
RUN npm ci

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 3000 3001

# 启动命令
CMD ["npm", "run", "dev"]

# -----------------------------------------------------------------------------
# 阶段6: 最小化运行时镜像 (生产)
# -----------------------------------------------------------------------------
FROM alpine:3.18 AS runtime

# 安装运行时依赖
RUN apk add --no-cache \
    nodejs \
    npm \
    curl \
    tini

# 创建应用用户
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app

# 复制应用文件
COPY --from=backend /app /app

# 设置权限
RUN chown -R appuser:appgroup /app

# 切换用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# 暴露端口
EXPOSE 3001

# 启动命令
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "src/index.js"]

# =============================================================================
# 构建和使用说明
# =============================================================================

# 构建特定阶段的镜像:
# docker build --target frontend -t app-frontend .
# docker build --target backend -t app-backend .
# docker build --target development -t app-dev .
# docker build --target runtime -t app-runtime .

# 使用多阶段构建优化镜像大小:
# docker build -t myapp:latest .

# Docker Compose 使用:
# docker-compose up --build