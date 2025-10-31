#!/bin/bash
# =============================================================================
# 数据库恢复脚本
# 从备份文件恢复 PostgreSQL 数据库和上传文件
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKUP_DIR="$PROJECT_ROOT/backups"

# 数据库配置
DB_CONTAINER="docker_app-postgres-1"
DB_NAME="myapp_db"
DB_USER="app_user"
DB_PASSWORD="${DB_PASSWORD:-}"

# Redis 配置
REDIS_CONTAINER="docker_app-redis-1"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# 恢复确认
RESTORE_CONFIRMED=false

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

# 显示帮助
show_help() {
    cat << EOF
用法: $0 [选项] <备份文件>

选项:
  -h, --help           显示此帮助信息
  -d, --date DATE      按日期恢复 (格式: YYYYMMDD)
  -t, --time TIME      按时间恢复 (格式: HHMMSS)
  --database           仅恢复数据库
  --redis              仅恢复 Redis
  --uploads            仅恢复上传文件
  --configs            仅恢复配置文件
  --force              强制恢复 (不询问确认)
  --verify             仅验证备份文件
  --list               列出可用的备份文件

参数:
  备份文件            完整的备份文件路径

示例:
  $0                           # 交互式恢复
  $0 --list                    # 列出可用备份
  $0 --date 20231201           # 恢复指定日期的最新备份
  $0 --database backups/database_20231201_120000.sql.gz
  $0 --force --database backups/database_20231201_120000.sql.gz

EOF
}

# 列出可用备份
list_backups() {
    echo "=== 可用的数据库备份 ==="
    find "$BACKUP_DIR" -name "database_*.sql.gz" -type f | sort -r | while read -r file; do
        local size=$(du -h "$file" | cut -f1)
        local date=$(basename "$file" | sed 's/database_\([0-9]*\)_\([0-9]*\)\.sql\.gz/\1 \2/')
        local formatted_date=$(echo "$date" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\) \([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
        echo "  $(basename "$file") ($size) - $formatted_date"
    done
    
    echo ""
    echo "=== 可用的 Redis 备份 ==="
    find "$BACKUP_DIR" -name "redis_*.rdb.gz" -type f | sort -r | while read -r file; do
        local size=$(du -h "$file" | cut -f1)
        local date=$(basename "$file" | sed 's/redis_\([0-9]*\)_\([0-9]*\)\.rdb\.gz/\1 \2/')
        local formatted_date=$(echo "$date" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\) \([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
        echo "  $(basename "$file") ($size) - $formatted_date"
    done
    
    echo ""
    echo "=== 可用的上传文件备份 ==="
    find "$BACKUP_DIR" -name "uploads_*.tar.gz" -type f | sort -r | while read -r file; do
        local size=$(du -h "$file" | cut -f1)
        local date=$(basename "$file" | sed 's/uploads_\([0-9]*\)_\([0-9]*\)\.tar\.gz/\1 \2/')
        local formatted_date=$(echo "$date" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\) \([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
        echo "  $(basename "$file") ($size) - $formatted_date"
    done
}

# 查找备份文件
find_backup_file() {
    local type="$1"
    local date="$2"
    local time="${3:-}"
    
    case "$type" in
        database)
            find "$BACKUP_DIR" -name "database_${date}"*"${time}"*.sql.gz -type f | sort -r | head -1
            ;;
        redis)
            find "$BACKUP_DIR" -name "redis_${date}"*"${time}"*.rdb.gz -type f | sort -r | head -1
            ;;
        uploads)
            find "$BACKUP_DIR" -name "uploads_${date}"*"${time}"*.tar.gz -type f | sort -r | head -1
            ;;
        configs)
            find "$BACKUP_DIR" -name "configs_${date}"*"${time}"*.tar.gz -type f | sort -r | head -1
            ;;
    esac
}

# 验证备份文件
verify_backup_file() {
    local file="$1"
    
    if [[ ! -f "$file" ]]; then
        error "备份文件不存在: $file"
    fi
    
    log "验证备份文件: $file"
    
    # 检查文件完整性
    if [[ "$file" == *.gz ]]; then
        if ! gunzip -t "$file" 2>/dev/null; then
            error "备份文件损坏或格式错误: $file"
        fi
    elif [[ "$file" == *.tar.gz ]]; then
        if ! tar -tzf "$file" >/dev/null 2>&1; then
            error "备份文件损坏或格式错误: $file"
        fi
    fi
    
    local size=$(du -h "$file" | cut -f1)
    log "备份文件大小: $size"
    log "备份文件验证通过"
}

# 确认恢复
confirm_restore() {
    local message="$1"
    
    if [[ "$RESTORE_CONFIRMED" == "true" ]]; then
        return 0
    fi
    
    warning "$message"
    echo ""
    echo "此操作将覆盖当前数据，请确认："
    read -r -p "输入 'YES' 确认恢复: " confirm
    
    if [[ "$confirm" != "YES" ]]; then
        error "恢复操作已取消"
    fi
}

# 停止应用服务
stop_app_services() {
    log "停止应用服务..."
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" stop frontend backend 2>/dev/null || true
}

# 启动应用服务
start_app_services() {
    log "启动应用服务..."
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" start frontend backend 2>/dev/null || true
}

# 恢复数据库
restore_database() {
    local backup_file="$1"
    
    confirm_restore "将恢复数据库，这将删除当前所有数据"
    
    log "开始恢复数据库..."
    
    # 停止应用服务
    stop_app_services
    
    # 设置密码
    export PGPASSWORD="$DB_PASSWORD"
    
    # 删除现有数据库
    log "删除现有数据库..."
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
    
    # 创建新数据库
    log "创建新数据库..."
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
    
    # 恢复数据
    log "恢复数据库数据..."
    if gunzip -c "$backup_file" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"; then
        log "数据库恢复完成"
        
        # 设置数据库所有者
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;" 2>/dev/null || true
    else
        error "数据库恢复失败"
    fi
}

# 恢复 Redis
restore_redis() {
    local backup_file="$1"
    
    confirm_restore "将恢复 Redis 数据，这将删除当前所有缓存数据"
    
    log "开始恢复 Redis 数据..."
    
    # 停止相关服务
    stop_app_services
    
    # 复制备份文件到容器
    local temp_file="/tmp/redis_backup_$$.rdb"
    gunzip -c "$backup_file" > "$temp_file"
    docker cp "$temp_file" "$REDIS_CONTAINER:/data/dump.rdb"
    rm -f "$temp_file"
    
    # 重启 Redis 容器
    log "重启 Redis 容器..."
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" restart redis
    
    log "Redis 数据恢复完成"
}

# 恢复上传文件
restore_uploads() {
    local backup_file="$1"
    
    confirm_restore "将恢复上传文件，这将覆盖当前上传目录"
    
    log "开始恢复上传文件..."
    
    local uploads_dir="$PROJECT_ROOT/uploads"
    
    # 备份当前上传目录
    if [[ -d "$uploads_dir" ]]; then
        local backup_dir="$PROJECT_ROOT/uploads_backup_$(date +%Y%m%d_%H%M%S)"
        mv "$uploads_dir" "$backup_dir"
        log "当前上传目录已备份到: $backup_dir"
    fi
    
    # 创建上传目录
    mkdir -p "$uploads_dir"
    
    # 恢复文件
    tar -xzf "$backup_file" -C "$(dirname "$uploads_dir")"
    
    # 设置权限
    chmod -R 755 "$uploads_dir"
    
    log "上传文件恢复完成"
}

# 恢复配置文件
restore_configs() {
    local backup_file="$1"
    
    log "开始恢复配置文件..."
    
    # 创建备份目录
    local backup_dir="$PROJECT_ROOT/configs_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 备份当前配置
    cp -r "$PROJECT_ROOT/docker-compose.yml" "$backup_dir/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/.env" "$backup_dir/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/docker/" "$backup_dir/" 2>/dev/null || true
    
    # 恢复配置
    tar -xzf "$backup_file" -C "$PROJECT_ROOT"
    
    log "配置文件恢复完成，原配置已备份到: $backup_dir"
}

# 交互式选择备份文件
interactive_restore() {
    echo "=== 交互式恢复模式 ==="
    echo ""
    
    # 选择恢复类型
    echo "请选择恢复类型:"
    echo "1) 数据库"
    echo "2) Redis"
    echo "3) 上传文件"
    echo "4) 配置文件"
    echo "5) 全部"
    read -r -p "请输入选择 (1-5): " restore_type
    
    case "$restore_type" in
        1) restore_type="database" ;;
        2) restore_type="redis" ;;
        3) restore_type="uploads" ;;
        4) restore_type="configs" ;;
        5) restore_type="all" ;;
        *) error "无效选择" ;;
    esac
    
    # 选择日期
    read -r -p "请输入备份日期 (YYYYMMDD，留空为最新): " restore_date
    
    if [[ -z "$restore_date" ]]; then
        case "$restore_type" in
            database)
                restore_file=$(find_backup_file "database" "$(date +%Y%m%d)")
                if [[ -z "$restore_file" ]]; then
                    restore_file=$(find_backup_file "database" "$(date -d 'yesterday' +%Y%m%d)")
                fi
                ;;
            redis)
                restore_file=$(find_backup_file "redis" "$(date +%Y%m%d)")
                if [[ -z "$restore_file" ]]; then
                    restore_file=$(find_backup_file "redis" "$(date -d 'yesterday' +%Y%m%d)")
                fi
                ;;
            uploads)
                restore_file=$(find_backup_file "uploads" "$(date +%Y%m%d)")
                if [[ -z "$restore_file" ]]; then
                    restore_file=$(find_backup_file "uploads" "$(date -d 'yesterday' +%Y%m%d)")
                fi
                ;;
            configs)
                restore_file=$(find_backup_file "configs" "$(date +%Y%m%d)")
                if [[ -z "$restore_file" ]]; then
                    restore_file=$(find_backup_file "configs" "$(date -d 'yesterday' +%Y%m%d)")
                fi
                ;;
        esac
    else
        case "$restore_type" in
            database) restore_file=$(find_backup_file "database" "$restore_date") ;;
            redis) restore_file=$(find_backup_file "redis" "$restore_date") ;;
            uploads) restore_file=$(find_backup_file "uploads" "$restore_date") ;;
            configs) restore_file=$(find_backup_file "configs" "$restore_date") ;;
        esac
    fi
    
    if [[ -z "$restore_file" ]]; then
        error "未找到备份文件"
    fi
    
    echo ""
    echo "找到备份文件: $restore_file"
    read -r -p "确认恢复? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        error "恢复操作已取消"
    fi
    
    # 执行恢复
    case "$restore_type" in
        database) restore_database "$restore_file" ;;
        redis) restore_redis "$restore_file" ;;
        uploads) restore_uploads "$restore_file" ;;
        configs) restore_configs "$restore_file" ;;
        all)
            restore_database "$restore_file"
            restore_redis "$(find_backup_file "redis" "$(basename "$restore_file" | cut -d'_' -f2)")"
            restore_uploads "$(find_backup_file "uploads" "$(basename "$restore_file" | cut -d'_' -f2)")"
            restore_configs "$(find_backup_file "configs" "$(basename "$restore_file" | cut -d'_' -f2)")"
            ;;
    esac
}

# 主函数
main() {
    # 检查参数
    if [[ $# -eq 0 ]]; then
        interactive_restore
        exit 0
    fi
    
    # 解析命令行参数
    local restore_type=""
    local backup_file=""
    local date=""
    local time=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --list)
                list_backups
                exit 0
                ;;
            --database)
                restore_type="database"
                shift
                ;;
            --redis)
                restore_type="redis"
                shift
                ;;
            --uploads)
                restore_type="uploads"
                shift
                ;;
            --configs)
                restore_type="configs"
                shift
                ;;
            --force)
                RESTORE_CONFIRMED=true
                shift
                ;;
            --verify)
                if [[ -z "${2:-}" ]]; then
                    error "请指定备份文件路径"
                fi
                verify_backup_file "$2"
                exit 0
                ;;
            -d|--date)
                date="$2"
                shift 2
                ;;
            -t|--time)
                time="$2"
                shift 2
                ;;
            -*)
                error "未知选项: $1"
                ;;
            *)
                backup_file="$1"
                shift
                ;;
        esac
    done
    
    # 验证参数
    if [[ -z "$restore_type" && -z "$backup_file" && -z "$date" ]]; then
        error "请指定恢复类型或备份文件"
    fi
    
    if [[ -n "$date" && -z "$restore_type" ]]; then
        error "使用 --date 选项时必须指定恢复类型"
    fi
    
    # 执行恢复
    if [[ -n "$backup_file" ]]; then
        # 直接指定文件恢复
        verify_backup_file "$backup_file"
        
        case "$restore_type" in
            database) restore_database "$backup_file" ;;
            redis) restore_redis "$backup_file" ;;
            uploads) restore_uploads "$backup_file" ;;
            configs) restore_configs "$backup_file" ;;
            *) error "请指定恢复类型" ;;
        esac
    else
        # 按日期查找文件恢复
        local file=$(find_backup_file "$restore_type" "$date" "$time")
        if [[ -z "$file" ]]; then
            error "未找到备份文件: $restore_type $date $time"
        fi
        
        log "找到备份文件: $file"
        verify_backup_file "$file"
        
        case "$restore_type" in
            database) restore_database "$file" ;;
            redis) restore_redis "$file" ;;
            uploads) restore_uploads "$file" ;;
            configs) restore_configs "$file" ;;
        esac
    fi
    
    # 启动服务
    start_app_services
    
    log "=== 恢复任务完成 ==="
}

# 执行主函数
main "$@"