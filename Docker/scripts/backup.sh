#!/bin/bash
# =============================================================================
# 数据库备份脚本
# 自动备份 PostgreSQL 数据库和上传文件
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y%m%d)

# 数据库配置 (从 docker-compose.yml 获取)
DB_CONTAINER="docker_app-postgres-1"  # docker_app 是默认项目名
DB_NAME="myapp_db"
DB_USER="app_user"
DB_PASSWORD="${DB_PASSWORD:-}"

# Redis 配置
REDIS_CONTAINER="docker_app-redis-1"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# 日志配置
LOG_FILE="$BACKUP_DIR/backup_$DATE.log"
mkdir -p "$BACKUP_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

# 检查依赖
check_dependencies() {
    log "检查依赖..."
    
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker 未安装"
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose 未安装"
    fi
    
    # 检查容器是否运行
    if ! docker ps | grep -q "$DB_CONTAINER"; then
        error "数据库容器未运行: $DB_CONTAINER"
    fi
    
    log "依赖检查通过"
}

# 备份数据库
backup_database() {
    log "开始备份数据库..."
    
    local db_backup_file="$BACKUP_DIR/database_$TIMESTAMP.sql"
    local db_gz_file="$db_backup_file.gz"
    
    # 设置数据库密码
    export PGPASSWORD="$DB_PASSWORD"
    
    # 执行备份
    if docker exec "$DB_CONTAINER" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges > "$db_backup_file" 2>>"$LOG_FILE"; then
        
        # 压缩备份文件
        gzip "$db_backup_file"
        log "数据库备份完成: $db_gz_file"
        
        # 计算文件大小
        local size=$(du -h "$db_gz_file" | cut -f1)
        log "备份文件大小: $size"
        
        return 0
    else
        error "数据库备份失败"
    fi
}

# 备份 Redis 数据
backup_redis() {
    log "开始备份 Redis 数据..."
    
    local redis_backup_file="$BACKUP_DIR/redis_$TIMESTAMP.rdb"
    local redis_gz_file="$redis_backup_file.gz"
    
    # 复制 Redis RDB 文件
    if docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$redis_backup_file" 2>>"$LOG_FILE"; then
        # 压缩备份文件
        gzip "$redis_backup_file"
        log "Redis 备份完成: $redis_gz_file"
        
        local size=$(du -h "$redis_gz_file" | cut -f1)
        log "Redis 备份文件大小: $size"
        
        return 0
    else
        warning "Redis 备份失败，跳过"
        return 1
    fi
}

# 备份上传文件
backup_uploads() {
    log "开始备份上传文件..."
    
    local uploads_backup_file="$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz"
    
    # 创建上传文件备份
    if tar -czf "$uploads_backup_file" \
        -C "$(dirname "$PROJECT_ROOT")" \
        "$(basename "$PROJECT_ROOT")/uploads" 2>>"$LOG_FILE"; then
        
        log "上传文件备份完成: $uploads_backup_file"
        
        local size=$(du -h "$uploads_backup_file" | cut -f1)
        log "上传文件备份大小: $size"
        
        return 0
    else
        warning "上传文件备份失败，跳过"
        return 1
    fi
}

# 备份配置文件
backup_configs() {
    log "开始备份配置文件..."
    
    local config_backup_file="$BACKUP_DIR/configs_$TIMESTAMP.tar.gz"
    
    # 备份重要的配置文件
    tar -czf "$config_backup_file" \
        -C "$PROJECT_ROOT" \
        docker-compose.yml \
        .env \
        docker/ \
        2>>"$LOG_FILE" || warning "配置文件备份失败"
    
    log "配置文件备份完成: $config_backup_file"
}

# 清理旧备份
cleanup_old_backups() {
    log "清理 30 天前的备份文件..."
    
    local deleted_count=0
    
    # 清理数据库备份
    find "$BACKUP_DIR" -name "database_*.sql.gz" -mtime +30 -type f | while read -r file; do
        rm -f "$file"
        ((deleted_count++))
        log "删除旧备份: $(basename "$file")"
    done
    
    # 清理 Redis 备份
    find "$BACKUP_DIR" -name "redis_*.rdb.gz" -mtime +30 -type f | while read -r file; do
        rm -f "$file"
        ((deleted_count++))
        log "删除旧备份: $(basename "$file")"
    done
    
    # 清理上传文件备份
    find "$BACKUP_DIR" -name "uploads_*.tar.gz" -mtime +30 -type f | while read -r file; do
        rm -f "$file"
        ((deleted_count++))
        log "删除旧备份: $(basename "$file")"
    done
    
    # 清理配置文件备份
    find "$BACKUP_DIR" -name "configs_*.tar.gz" -mtime +30 -type f | while read -r file; do
        rm -f "$file"
        ((deleted_count++))
        log "删除旧备份: $(basename "$file")"
    done
    
    # 清理旧日志文件
    find "$BACKUP_DIR" -name "backup_*.log" -mtime +7 -type f | while read -r file; do
        rm -f "$file"
        ((deleted_count++))
        log "删除旧日志: $(basename "$file")"
    done
    
    log "清理完成，删除了 $deleted_count 个文件"
}

# 生成备份报告
generate_backup_report() {
    log "生成备份报告..."
    
    local report_file="$BACKUP_DIR/backup_report_$DATE.txt"
    
    cat > "$report_file" << EOF
=== 备份报告 ===
日期: $(date)
项目: $(basename "$PROJECT_ROOT")

=== 备份文件列表 ===
$(find "$BACKUP_DIR" -name "*_$DATE*" -type f -exec ls -lh {} \; | sort)

=== 磁盘使用情况 ===
$(df -h "$BACKUP_DIR")

=== 数据库信息 ===
$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'app'
ORDER BY tablename, attname
LIMIT 20;" 2>/dev/null || echo "无法获取数据库统计信息")

=== 备份完成时间 ===
$(date)

EOF
    
    log "备份报告生成完成: $report_file"
}

# 验证备份
verify_backup() {
    log "验证备份文件..."
    
    local issues=0
    
    # 检查数据库备份
    if [[ -f "$BACKUP_DIR/database_$TIMESTAMP.sql.gz" ]]; then
        if gunzip -t "$BACKUP_DIR/database_$TIMESTAMP.sql.gz" 2>/dev/null; then
            log "✓ 数据库备份文件完整性检查通过"
        else
            error "✗ 数据库备份文件损坏"
            ((issues++))
        fi
    fi
    
    # 检查配置文件备份
    if [[ -f "$BACKUP_DIR/configs_$TIMESTAMP.tar.gz" ]]; then
        if tar -tzf "$BACKUP_DIR/configs_$TIMESTAMP.tar.gz" >/dev/null 2>&1; then
            log "✓ 配置文件备份文件完整性检查通过"
        else
            error "✗ 配置文件备份文件损坏"
            ((issues++))
        fi
    fi
    
    if [[ $issues -eq 0 ]]; then
        log "备份验证完成，所有文件正常"
    else
        warning "备份验证完成，发现 $issues 个问题"
    fi
}

# 发送通知 (可选)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Slack 通知 (如果配置了 SLACK_WEBHOOK)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Backup $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
    
    # Email 通知 (如果配置了 SMTP)
    if [[ -n "${SMTP_SERVER:-}" ]]; then
        echo "$message" | mail -s "Backup $status" "$NOTIFICATION_EMAIL" 2>/dev/null || true
    fi
}

# 主函数
main() {
    log "=== 开始备份任务 ==="
    
    # 设置错误处理
    trap 'error "备份过程中发生错误"' ERR
    
    # 检查依赖
    check_dependencies
    
    # 执行备份
    if backup_database && \
       backup_redis && \
       backup_uploads && \
       backup_configs; then
        
        # 清理旧备份
        cleanup_old_backups
        
        # 验证备份
        verify_backup
        
        # 生成报告
        generate_backup_report
        
        log "=== 备份任务完成 ==="
        
        # 发送成功通知
        send_notification "SUCCESS" "备份任务完成，时间: $(date)"
        
        exit 0
    else
        error "备份任务失败"
        send_notification "FAILED" "备份任务失败，时间: $(date)"
        exit 1
    fi
}

# 显示帮助
show_help() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help     显示此帮助信息
  -d, --date     指定备份日期 (格式: YYYYMMDD)
  -c, --config   仅备份配置文件
  -db, --database 仅备份数据库
  -u, --uploads  仅备份上传文件
  -r, --redis    仅备份 Redis
  -v, --verify   仅验证备份文件
  --no-cleanup   跳过清理旧备份
  --no-notify    跳过发送通知

示例:
  $0                    # 执行完整备份
  $0 --database         # 仅备份数据库
  $0 -d 20231201        # 备份特定日期的文件
  $0 --verify           # 验证备份文件

EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--date)
            DATE="$2"
            shift 2
            ;;
        -c|--config)
            backup_configs
            exit 0
            ;;
        --database|-db)
            backup_database
            exit 0
            ;;
        -u|--uploads)
            backup_uploads
            exit 0
            ;;
        -r|--redis)
            backup_redis
            exit 0
            ;;
        -v|--verify)
            verify_backup
            exit 0
            ;;
        --no-cleanup)
            cleanup_old_backups() { log "跳过清理旧备份"; }
            shift
            ;;
        --no-notify)
            send_notification() { true; }
            shift
            ;;
        *)
            error "未知选项: $1"
            ;;
    esac
done

# 执行主函数
main