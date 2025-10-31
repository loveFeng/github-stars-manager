#!/bin/bash

# GitHub Stars Manager - Single Container Startup Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "🚀 启动 GitHub Stars Manager 单容器版本..."

# 创建必要的目录
mkdir -p /app/data
mkdir -p /app/logs
mkdir -p /app/backup

# 初始化数据库（如果不存在）
if [ ! -f "$DB_PATH" ]; then
    log_info "🗄️  初始化 SQLite 数据库..."
    sqlite3 "$DB_PATH" < /app/database/init.sql
    log_info "✅ 数据库初始化完成"
else
    log_info "ℹ️  数据库已存在，跳过初始化"
fi

# 创建环境变量文件
cat > /app/.env << EOL
# GitHub Stars Manager 配置
GITHUB_TOKEN=$GITHUB_TOKEN
OPENAI_API_KEY=$OPENAI_API_KEY
WEBDAV_URL=$WEBDAV_URL
WEBDAV_USERNAME=$WEBDAV_USERNAME
WEBDAV_PASSWORD=$WEBDAV_PASSWORD
DB_PATH=$DB_PATH
PORT=$PORT
EOL

log_info "🔧 配置环境变量"

# 检查必需的配置文件
log_info "📁 检查配置文件..."

# 创建 nginx 目录
mkdir -p /var/log/nginx
mkdir -p /var/cache/nginx

# 启动 nginx
log_info "🌐 启动 Nginx..."
nginx -g "daemon off;" &

# 等待 nginx 启动
sleep 2

# 启动后端 Python 服务
log_info "🐍 启动 Python 后端服务..."
cd /app/services

# 设置 Python 路径
export PYTHONPATH=/app/services
export DB_PATH=$DB_PATH
export PORT=$PORT

# 启动 FastAPI 应用
python main.py &

BACKEND_PID=$!

# 等待后端服务启动
log_info "⏳ 等待服务启动..."
sleep 5

# 健康检查
log_info "🔍 执行健康检查..."

if curl -f http://localhost:$PORT/health > /dev/null 2>&1; then
    log_info "✅ 服务启动成功！"
    log_info "🌐 应用访问地址: http://localhost:$PORT"
    log_info "📱 使用 GitHub Token 登录"
else
    log_error "❌ 服务启动失败，正在检查日志..."
fi

# 保持容器运行
log_info "🔄 容器运行中，按 Ctrl+C 停止..."

# 等待信号
trap 'log_info "🛑 正在停止服务..."; kill $BACKEND_PID; nginx -s quit; exit 0' INT TERM

# 无限循环保持容器活跃
while true; do
    sleep 30
    # 检查服务状态
    if ! pgrep -f "python.*main.py" > /dev/null; then
        log_warn "⚠️  后端服务似乎停止了，正在重启..."
        cd /app/services
        python main.py &
        BACKEND_PID=$!
    fi
    
    if ! pgrep nginx > /dev/null; then
        log_warn "⚠️  Nginx 似乎停止了，正在重启..."
        nginx -g "daemon off;" &
    fi
done