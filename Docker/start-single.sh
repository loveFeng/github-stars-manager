#!/bin/bash

# GitHub Stars Manager - 一键启动单容器版本
# Quick Start Script for Single Container Deployment

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 表情符号
ROCKET="🚀"
CHECK="✅"
WARN="⚠️"
INFO="ℹ️"
ERROR="❌"
ROBOT="🤖"

# 配置
CONTAINER_NAME="github-stars-manager"
IMAGE_NAME="github-stars-manager"
COMPOSE_FILE="docker-compose.single.yml"
ENV_FILE="Docker/.env"

print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
┌─────────────────────────────────────────────────────────────┐
│                     🤖 GitHub Stars Manager                 │
│                    单容器一键启动脚本                        │
│                                                             │
│  🚀 快速部署 | 🐳 单容器运行 | ⚡ 简单易用                   │
└─────────────────────────────────────────────────────────────┘
EOF
    echo -e "${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO}${NC} $1"
}

print_success() {
    echo -e "${GREEN}${CHECK}${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}${WARN}${NC} $1"
}

print_error() {
    echo -e "${RED}${ERROR}${NC} $1"
}

check_docker() {
    print_info "检查 Docker 环境..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        echo "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查 Docker 服务是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker 服务未运行，请启动 Docker 服务"
        exit 1
    fi
    
    print_success "Docker 环境检查通过"
}

check_project_structure() {
    print_info "检查项目结构..."
    
    required_files=(
        "Docker/Dockerfile.single"
        "Docker/docker-compose.single.yml"
        "Docker/start-single-container.sh"
        "Docker/nginx/docker-nginx.conf"
        "services/requirements.txt"
        "database/init.sql"
        "github-stars-manager-frontend/package.json"
    )
    
    missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "缺少必要文件:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi
    
    print_success "项目结构检查通过"
}

setup_environment() {
    print_info "设置环境配置..."
    
    # 创建 Docker 目录
    mkdir -p Docker
    
    if [ ! -f "$ENV_FILE" ]; then
        print_info "创建环境配置文件..."
        cp "Docker/.env.example.single" "$ENV_FILE"
        print_warning "请编辑 $ENV_FILE 文件，填入您的 GitHub Token"
        print_warning "必需的 GITHUB_TOKEN 必须配置才能正常运行"
        
        echo ""
        print_info "快速配置指南:"
        echo "1. 访问 https://github.com/settings/tokens"
        echo "2. 创建 Personal Access Token"
        echo "3. 编辑 $ENV_FILE 文件"
        echo "4. 运行此脚本再次启动"
        echo ""
        
        read -p "是否现在编辑配置文件? (y/n): " edit_now
        if [[ $edit_now =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} "$ENV_FILE"
        fi
    else
        print_success "环境配置文件已存在"
    fi
    
    # 检查必需的 GitHub Token
    source "$ENV_FILE"
    if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" ]; then
        print_error "GitHub Token 未配置或仍为示例值"
        print_error "请编辑 $ENV_FILE 文件，设置有效的 GITHUB_TOKEN"
        exit 1
    fi
    
    print_success "环境配置检查通过"
}

build_image() {
    print_info "构建 Docker 镜像..."
    
    cd "$(dirname "$0")/.."
    
    if docker build -f "Docker/Dockerfile.single" -t "$IMAGE_NAME" .; then
        print_success "镜像构建完成"
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

start_services() {
    print_info "启动服务..."
    
    cd "$(dirname "$0")/.."
    
    # 检查并停止现有容器
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_warning "检测到现有容器，正在停止..."
        docker-compose -f "Docker/$COMPOSE_FILE" down
    fi
    
    # 启动服务
    if docker-compose -f "Docker/$COMPOSE_FILE" up -d; then
        print_success "服务启动成功"
    else
        print_error "服务启动失败"
        exit 1
    fi
}

wait_for_startup() {
    print_info "等待服务启动..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f http://localhost:3000/health > /dev/null 2>&1; then
            print_success "服务启动完成"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "服务启动超时"
    return 1
}

show_status() {
    print_info "服务状态:"
    
    echo ""
    echo -e "${GREEN}${ROCKET} 应用已启动${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "🌐  Web 界面: ${CYAN}http://localhost:3000${NC}"
    echo -e "💬 GitHub Token: ${YELLOW}$([ -n "$GITHUB_TOKEN" ] && echo "已配置" || echo "未配置")${NC}"
    echo -e "🤖 AI 功能: ${YELLOW}$([ -n "$OPENAI_API_KEY" ] && echo "已配置" || echo "未配置")${NC}"
    echo -e "💾 备份功能: ${YELLOW}$([ -n "$WEBDAV_URL" ] && echo "已配置" || echo "未配置")${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    print_info "常用管理命令:"
    echo "  查看日志:    docker logs -f $CONTAINER_NAME"
    echo "  停止服务:    docker-compose -f Docker/$COMPOSE_FILE down"
    echo "  重启服务:    docker-compose -f Docker/$COMPOSE_FILE restart"
    echo "  进入容器:    docker exec -it $CONTAINER_NAME /bin/bash"
    echo ""
    
    print_info "健康检查:"
    echo "  本地访问:    curl http://localhost:3000/health"
    echo "  容器状态:    docker ps | grep $CONTAINER_NAME"
    echo ""
    
    print_info "数据目录:"
    echo "  数据库:      Docker 数据卷 github_stars_data"
    echo "  日志:        Docker 数据卷 github_stars_logs"
    echo "  备份:        Docker 数据卷 github_stars_backup"
    echo ""
    
    print_info "更多信息请查看:"
    echo "  - Docker/SINGLE_CONTAINER_GUIDE.md"
    echo "  - Docker/.env.example.single"
    echo ""
}

cleanup() {
    if [ $? -eq 0 ]; then
        print_success "启动完成！🎉"
    else
        print_error "启动过程中出现错误"
        print_info "查看日志: docker logs $CONTAINER_NAME"
        print_info "或运行: docker-compose -f Docker/$COMPOSE_FILE logs"
    fi
}

# 主程序
main() {
    # 设置错误处理
    trap cleanup EXIT
    
    print_banner
    
    print_info "开始启动 GitHub Stars Manager 单容器版本..."
    echo ""
    
    # 执行启动步骤
    check_docker
    echo ""
    
    check_project_structure
    echo ""
    
    setup_environment
    echo ""
    
    build_image
    echo ""
    
    start_services
    echo ""
    
    if wait_for_startup; then
        show_status
    else
        print_error "服务启动失败，请检查配置和日志"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "GitHub Stars Manager 单容器启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  --reset        重置所有配置和数据"
    echo "  --stop         停止服务"
    echo "  --restart      重启服务"
    echo "  --logs         查看服务日志"
    echo "  --status       查看服务状态"
    echo ""
    echo "示例:"
    echo "  $0                    # 启动服务"
    echo "  $0 --reset           # 重置配置和数据"
    echo "  $0 --stop            # 停止服务"
    echo "  $0 --restart         # 重启服务"
    echo ""
}

# 处理命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --reset)
        print_warning "重置配置和数据?"
        read -p "这将删除所有数据，确定吗? (y/n): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            print_info "正在重置..."
            docker-compose -f Docker/docker-compose.single.yml down -v
            docker system prune -f
            rm -f Docker/.env
            print_success "重置完成"
        else
            print_info "取消重置"
        fi
        exit 0
        ;;
    --stop)
        print_info "停止服务..."
        docker-compose -f Docker/docker-compose.single.yml down
        print_success "服务已停止"
        exit 0
        ;;
    --restart)
        print_info "重启服务..."
        docker-compose -f Docker/docker-compose.single.yml restart
        print_success "服务已重启"
        exit 0
        ;;
    --logs)
        docker-compose -f Docker/docker-compose.single.yml logs -f
        exit 0
        ;;
    --status)
        docker ps | grep github-stars-manager || echo "服务未运行"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "未知选项: $1"
        show_help
        exit 1
        ;;
esac