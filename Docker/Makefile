# =============================================================================
# Docker 部署 Makefile
# 提供便捷的部署和管理命令
# =============================================================================

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

# 项目配置
PROJECT_NAME := myapp
COMPOSE_FILE := docker-compose.yml
ENV_FILE := .env

# Docker Compose 命令
DC := docker-compose -f $(COMPOSE_FILE)

# =============================================================================
# 帮助信息
# =============================================================================

help: ## 显示帮助信息
	@echo "$(BLUE)Docker 部署管理命令$(NC)"
	@echo ""
	@echo "$(GREEN)可用命令:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)示例用法:$(NC)"
	@echo "  make setup      # 初始化项目"
	@echo "  make up         # 启动所有服务"
	@echo "  make logs       # 查看日志"
	@echo "  make status     # 查看服务状态"

# =============================================================================
# 环境设置
# =============================================================================

setup: ## 初始化项目环境
	@echo "$(BLUE)初始化项目环境...$(NC)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(YELLOW)复制环境变量模板...$(NC)"; \
		cp .env.example $(ENV_FILE); \
		echo "$(GREEN)已创建 $(ENV_FILE)，请编辑配置$(NC)"; \
	else \
		echo "$(YELLOW)环境变量文件已存在$(NC)"; \
	fi
	@mkdir -p ssl logs/{nginx,backend,postgres} data backups
	@echo "$(GREEN)项目环境初始化完成$(NC)"

install-deps: ## 安装 Docker 依赖
	@echo "$(BLUE)检查 Docker 和 Docker Compose...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Docker 未安装$(NC)"; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "$(RED)Docker Compose 未安装$(NC)"; exit 1; }
	@echo "$(GREEN)Docker 环境检查通过$(NC)"

check-config: ## 检查配置文件
	@echo "$(BLUE)检查配置文件...$(NC)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)错误: 缺少 $(ENV_FILE) 文件$(NC)"; \
		echo "$(YELLOW)请运行: make setup$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)配置文件检查通过$(NC)"

# =============================================================================
# 服务管理
# =============================================================================

up: install-deps check-config ## 启动所有服务
	@echo "$(BLUE)启动所有服务...$(NC)"
	@$(DC) up -d
	@echo "$(GREEN)服务启动完成$(NC)"
	@make status

down: ## 停止所有服务
	@echo "$(BLUE)停止所有服务...$(NC)"
	@$(DC) down
	@echo "$(GREEN)服务已停止$(NC)"

restart: ## 重启所有服务
	@echo "$(BLUE)重启所有服务...$(NC)"
	@$(DC) restart
	@echo "$(GREEN)服务重启完成$(NC)"

rebuild: ## 重新构建并启动服务
	@echo "$(BLUE)重新构建镜像...$(NC)"
	@$(DC) build --no-cache
	@$(DC) up -d
	@echo "$(GREEN)重建完成$(NC)"

reload: ## 重新加载配置 (不重建)
	@echo "$(BLUE)重新加载配置...$(NC)"
	@$(DC) up -d --force-recreate
	@echo "$(GREEN)配置重载完成$(NC)"

# =============================================================================
# 开发环境
# =============================================================================

dev: ## 启动开发环境 (包含开发工具)
	@echo "$(BLUE)启动开发环境...$(NC)"
	@$(DC) --profile development up -d
	@echo "$(GREEN)开发环境启动完成$(NC)"
	@echo "$(YELLOW)pgAdmin 可通过 http://localhost:5050 访问$(NC)"

dev-down: ## 停止开发环境
	@echo "$(BLUE)停止开发环境...$(NC)"
	@$(DC) --profile development down
	@echo "$(GREEN)开发环境已停止$(NC)"

# =============================================================================
# 监控环境
# =============================================================================

monitoring: ## 启动监控环境
	@echo "$(BLUE)启动监控环境...$(NC)"
	@$(DC) --profile monitoring up -d
	@echo "$(GREEN)监控环境启动完成$(NC)"
	@echo "$(YELLOW)访问地址:$(NC)"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000 (admin/admin123)"

monitoring-down: ## 停止监控环境
	@echo "$(BLUE)停止监控环境...$(NC)"
	@$(DC) --profile monitoring down
	@echo "$(GREEN)监控环境已停止$(NC)"

# =============================================================================
# 状态和日志
# =============================================================================

status: ## 查看服务状态
	@echo "$(BLUE)服务状态:$(NC)"
	@$(DC) ps

logs: ## 查看所有服务日志
	@echo "$(BLUE)服务日志 (按 Ctrl+C 退出):$(NC)"
	@$(DC) logs -f

logs-%: ## 查看指定服务日志 (例: make logs-nginx)
	@echo "$(BLUE)$* 服务日志:$(NC)"
	@$(DC) logs -f $*

health: ## 检查所有服务健康状态
	@echo "$(BLUE)检查服务健康状态...$(NC)"
	@echo "$(YELLOW)前端健康检查:$(NC)"
	@curl -s http://localhost/health | head -1 || echo "$(RED)前端服务异常$(NC)"
	@echo "$(YELLOW)后端健康检查:$(NC)"
	@curl -s http://localhost/api/health | head -1 || echo "$(RED)后端服务异常$(NC)"
	@echo "$(YELLOW)数据库连接检查:$(NC)"
	@$(DC) exec -T postgres pg_isready -U app_user 2>/dev/null && echo "$(GREEN)数据库正常$(NC)" || echo "$(RED)数据库异常$(NC)"

# =============================================================================
# 数据库操作
# =============================================================================

db-shell: ## 连接数据库 Shell
	@echo "$(BLUE)连接数据库...$(NC)"
	@$(DC) exec postgres psql -U app_user -d myapp_db

db-backup: ## 备份数据库
	@echo "$(BLUE)备份数据库...$(NC)"
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	$(DC) exec -T postgres pg_dump -U app_user myapp_db > backups/backup_$$TIMESTAMP.sql
	@echo "$(GREEN)数据库已备份到 backups/backup_$$(date +%Y%m%d_%H%M%S).sql$(NC)"

db-restore: ## 恢复数据库 (需要指定备份文件)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)请指定备份文件: make db-restore FILE=backups/backup_20231201.sql$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)恢复数据库从 $(FILE)...$(NC)"
	@$(DC) exec -T postgres psql -U app_user myapp_db < $(FILE)
	@echo "$(GREEN)数据库恢复完成$(NC)"

db-migrate: ## 运行数据库迁移
	@echo "$(BLUE)运行数据库迁移...$(NC)"
	@$(DC) exec backend npm run migrate
	@echo "$(GREEN)迁移完成$(NC)"

# =============================================================================
# 构建和镜像管理
# =============================================================================

build: ## 构建所有镜像
	@echo "$(BLUE)构建镜像...$(NC)"
	@$(DC) build
	@echo "$(GREEN)镜像构建完成$(NC)"

build-no-cache: ## 不使用缓存构建镜像
	@echo "$(BLUE)重新构建镜像 (无缓存)...$(NC)"
	@$(DC) build --no-cache
	@echo "$(GREEN)镜像构建完成$(NC)"

build-frontend: ## 仅构建前端镜像
	@echo "$(BLUE)构建前端镜像...$(NC)"
	@$(DC) build frontend
	@echo "$(GREEN)前端镜像构建完成$(NC)"

build-backend: ## 仅构建后端镜像
	@echo "$(BLUE)构建后端镜像...$(NC)"
	@$(DC) build backend
	@echo "$(GREEN)后端镜像构建完成$(NC)"

clean: ## 清理未使用的镜像和容器
	@echo "$(BLUE)清理未使用的资源...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)清理完成$(NC)"

clean-all: ## 清理所有 Docker 资源 (危险操作)
	@echo "$(RED)警告: 这将删除所有未使用的 Docker 资源!$(NC)"
	@read -p "确认继续? [y/N] " confirm && [ "$$confirm" = "y" ]
	@docker system prune -af
	@docker volume prune -f
	@echo "$(GREEN)清理完成$(NC)"

# =============================================================================
# 维护操作
# =============================================================================

update: ## 更新所有服务
	@echo "$(BLUE)更新服务...$(NC)"
	@$(DC) pull
	@$(DC) up -d
	@echo "$(GREEN)更新完成$(NC)"

rotate-logs: ## 轮转日志文件
	@echo "$(BLUE)轮转日志文件...$(NC)"
	@$(DC) exec nginx logrotate -f /etc/logrotate.conf || true
	@$(DC) restart nginx
	@echo "$(GREEN)日志轮转完成$(NC)"

clean-logs: ## 清理日志文件
	@echo "$(BLUE)清理日志文件...$(NC)"
	@find logs/ -name "*.log" -type f -delete || true
	@$(DC) exec -T nginx sh -c "echo '' > /var/log/nginx/access.log" || true
	@$(DC) exec -T nginx sh -c "echo '' > /var/log/nginx/error.log" || true
	@echo "$(GREEN)日志清理完成$(NC)"

# =============================================================================
# 安全操作
# =============================================================================

ssl-cert: ## 生成自签名 SSL 证书 (测试用)
	@echo "$(BLUE)生成自签名 SSL 证书...$(NC)"
	@mkdir -p ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout ssl/key.pem -out ssl/cert.pem \
		-subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"
	@echo "$(GREEN)SSL 证书已生成$(NC)"

check-security: ## 安全检查
	@echo "$(BLUE)执行安全检查...$(NC)"
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v $(PWD):/src \
		aquasec/trivy fs /src
	@echo "$(GREEN)安全检查完成$(NC)"

# =============================================================================
# 调试和故障排除
# =============================================================================

debug: ## 进入调试模式
	@echo "$(BLUE)启动调试环境...$(NC)"
	@$(DC) --profile development up -d
	@echo "$(GREEN)调试环境已启动$(NC)"

shell-backend: ## 进入后端容器 Shell
	@$(DC) exec backend sh

shell-frontend: ## 进入前端容器 Shell
	@$(DC) exec frontend sh

shell-nginx: ## 进入 Nginx 容器 Shell
	@$(DC) exec nginx sh

shell-postgres: ## 进入数据库容器 Shell
	@$(DC) exec postgres sh

inspect: ## 检查容器配置
	@echo "$(BLUE)容器配置信息:$(NC)"
	@$(DC) config

# =============================================================================
# 测试操作
# =============================================================================

test: ## 运行测试
	@echo "$(BLUE)运行测试...$(NC)"
	@$(DC) exec backend npm test
	@echo "$(GREEN)测试完成$(NC)"

test-integration: ## 运行集成测试
	@echo "$(BLUE)运行集成测试...$(NC)"
	@$(DC) exec backend npm run test:integration
	@echo "$(GREEN)集成测试完成$(NC)"

test-e2e: ## 运行端到端测试
	@echo "$(BLUE)运行端到端测试...$(NC)"
	@$(DC) exec backend npm run test:e2e
	@echo "$(GREEN)端到端测试完成$(NC)"

# =============================================================================
# 性能监控
# =============================================================================

stats: ## 查看容器资源使用情况
	@echo "$(BLUE)容器资源使用情况:$(NC)"
	@docker stats $$(docker-compose -f $(COMPOSE_FILE) ps -q)

top: ## 查看容器进程
	@echo "$(BLUE)容器进程信息:$(NC)"
	@$(DC) top

network: ## 检查网络配置
	@echo "$(BLUE)网络配置:$(NC)"
	@docker network ls
	@echo ""
	@docker network inspect docker_app-network || echo "网络未找到"

# =============================================================================
# 文档和帮助
# =============================================================================

docs: ## 生成文档
	@echo "$(BLUE)生成项目文档...$(NC)"
	@$(DC) exec backend npm run docs
	@echo "$(GREEN)文档生成完成$(NC)"

version: ## 显示版本信息
	@echo "$(BLUE)版本信息:$(NC)"
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"
	@echo "项目: $(PROJECT_NAME)"

info: ## 显示项目信息
	@echo "$(BLUE)项目信息:$(NC)"
	@echo "项目名称: $(PROJECT_NAME)"
	@echo "Compose 文件: $(COMPOSE_FILE)"
	@echo "环境文件: $(ENV_FILE)"
	@echo ""
	@echo "$(GREEN)服务地址:$(NC)"
	@echo "  - 前端: http://localhost"
	@echo "  - API: http://localhost/api"
	@echo "  - pgAdmin: http://localhost:5050"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000"

.PHONY: help setup install-deps check-config up down restart rebuild reload dev dev-down monitoring monitoring-down status logs logs-% health db-shell db-backup db-restore db-migrate build build-no-cache build-frontend build-backend clean clean-all update rotate-logs clean-logs ssl-cert check-security debug shell-backend shell-frontend shell-nginx shell-postgres inspect test test-integration test-e2e stats top network docs version info