#!/bin/bash
# =============================================================================
# 数据库备份脚本
# 用途: 自动备份 PostgreSQL 数据库
# =============================================================================

set -e

# 配置
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 检查环境变量
check_env() {
    if [ -z "$POSTGRES_DB" ]; then
        log_error "POSTGRES_DB is not set"
        exit 1
    fi
    
    if [ -z "$POSTGRES_USER" ]; then
        log_error "POSTGRES_USER is not set"
        exit 1
    fi
    
    if [ -f "/run/secrets/db_password" ]; then
        export PGPASSWORD=$(cat /run/secrets/db_password)
    elif [ -n "$POSTGRES_PASSWORD" ]; then
        export PGPASSWORD=$POSTGRES_PASSWORD
    else
        log_error "Database password not found"
        exit 1
    fi
}

# 创建备份目录
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# 执行备份
perform_backup() {
    log_info "Starting backup of database: $POSTGRES_DB"
    
    # 使用 pg_dump 备份
    pg_dump \
        -h "${DB_HOST:-postgres}" \
        -p "${DB_PORT:-5432}" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -F c \
        -b \
        -v \
        -f "$BACKUP_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log_info "Backup completed successfully: $BACKUP_FILE"
        
        # 获取文件大小
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_info "Backup size: $BACKUP_SIZE"
        
        # 压缩备份
        log_info "Compressing backup..."
        gzip "$BACKUP_FILE"
        
        if [ $? -eq 0 ]; then
            COMPRESSED_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
            log_info "Compressed size: $COMPRESSED_SIZE"
        else
            log_warn "Failed to compress backup"
        fi
    else
        log_error "Backup failed"
        exit 1
    fi
}

# 清理旧备份
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    DELETED_COUNT=$(find "$BACKUP_DIR" -name "backup_*.dump.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    
    if [ "$DELETED_COUNT" -gt 0 ]; then
        log_info "Deleted $DELETED_COUNT old backup(s)"
    else
        log_info "No old backups to delete"
    fi
}

# 验证备份
verify_backup() {
    log_info "Verifying backup integrity..."
    
    if [ -f "${BACKUP_FILE}.gz" ]; then
        gzip -t "${BACKUP_FILE}.gz"
        
        if [ $? -eq 0 ]; then
            log_info "Backup verification successful"
        else
            log_error "Backup verification failed"
            exit 1
        fi
    else
        log_error "Backup file not found for verification"
        exit 1
    fi
}

# 生成备份报告
generate_report() {
    REPORT_FILE="${BACKUP_DIR}/backup_report_${TIMESTAMP}.txt"
    
    cat > "$REPORT_FILE" << EOF
==========================================
数据库备份报告
==========================================
时间: $(date '+%Y-%m-%d %H:%M:%S')
数据库: $POSTGRES_DB
用户: $POSTGRES_USER
主机: ${DB_HOST:-postgres}
端口: ${DB_PORT:-5432}
备份文件: ${BACKUP_FILE}.gz
备份大小: $(du -h "${BACKUP_FILE}.gz" | cut -f1)
保留天数: $RETENTION_DAYS
状态: 成功
==========================================
EOF
    
    log_info "Backup report generated: $REPORT_FILE"
}

# 主函数
main() {
    log_info "=== Starting Database Backup ==="
    
    check_env
    create_backup_dir
    perform_backup
    verify_backup
    cleanup_old_backups
    generate_report
    
    log_info "=== Backup Completed Successfully ==="
}

# 执行主函数
main
