#!/bin/bash
# restore.sh - Database restore script from backup

set -e

# Configuration
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-legalai_production}"
DB_USER="${POSTGRES_USER:-legalai}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

BACKUP_DIR="/backups"
S3_BUCKET="${BACKUP_S3_BUCKET}"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Usage
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file> [--from-s3]"
    echo "Example: $0 legalai_backup_20240101_120000.sql.gz"
    echo "Example: $0 legalai_backup_20240101_120000.sql.gz --from-s3"
    exit 1
fi

BACKUP_FILE="$1"
FROM_S3="${2:-}"

# Download from S3 if requested
if [ "${FROM_S3}" == "--from-s3" ]; then
    if [ -z "${S3_BUCKET}" ]; then
        log "ERROR: S3_BUCKET not configured"
        exit 1
    fi
    
    log "Downloading backup from S3..."
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
    aws s3 cp "s3://${S3_BUCKET}/database-backups/${BACKUP_FILE}" "${BACKUP_PATH}"
    
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to download backup from S3"
        exit 1
    fi
else
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
fi

# Verify backup exists
if [ ! -f "${BACKUP_PATH}" ]; then
    log "ERROR: Backup file not found: ${BACKUP_PATH}"
    exit 1
fi

# Verify backup integrity
log "Verifying backup integrity..."
if ! gunzip -t "${BACKUP_PATH}"; then
    log "ERROR: Backup file is corrupted"
    exit 1
fi

# Confirm restoration
echo "WARNING: This will restore the database from backup."
echo "Current database content will be REPLACED."
echo "Backup file: ${BACKUP_FILE}"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    log "Restoration cancelled"
    exit 0
fi

# Create restore log
RESTORE_LOG="${BACKUP_DIR}/restore_$(date +%Y%m%d_%H%M%S).log"

# Stop application connections
log "Preparing database for restoration..."
export PGPASSWORD="${DB_PASSWORD}"

# Terminate existing connections
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}'
  AND pid <> pg_backend_pid();
EOF

# Perform restoration
log "Starting database restoration..."
gunzip -c "${BACKUP_PATH}" | psql \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-password \
    -v ON_ERROR_STOP=1 \
    2>&1 | tee "${RESTORE_LOG}"

if [ ${PIPESTATUS[1]} -eq 0 ]; then
    log "Database restoration completed successfully"
    
    # Run post-restore tasks
    log "Running post-restore tasks..."
    
    # Update sequences
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" <<EOF
    -- Reset sequences for primary keys
    SELECT setval(pg_get_serial_sequence('organizations', 'id'), COALESCE(MAX(id), 1)) FROM organizations;
    SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users;
    SELECT setval(pg_get_serial_sequence('documents', 'id'), COALESCE(MAX(id), 1)) FROM documents;
    
    -- Analyze tables for query optimization
    ANALYZE;
    
    -- Verify table counts
    SELECT 'organizations' as table_name, COUNT(*) as count FROM organizations
    UNION ALL
    SELECT 'users', COUNT(*) FROM users
    UNION ALL
    SELECT 'documents', COUNT(*) FROM documents;
EOF
    
    log "Post-restore tasks completed"
    
    # Send notification
    if [ -n "${SMTP_HOST}" ] && [ -n "${NOTIFICATION_EMAIL}" ]; then
        cat <<EOF | mail -s "Legal AI Database Restore Successful" "${NOTIFICATION_EMAIL}"
Database restoration completed successfully.

Restore Details:
- Backup File: ${BACKUP_FILE}
- Restore Time: $(date)
- Log File: ${RESTORE_LOG}

Please verify application functionality.

This is an automated message from Legal AI Restore System.
EOF
    fi
else
    log "ERROR: Database restoration failed. Check log: ${RESTORE_LOG}"
    exit 1
fi

log "Restoration process complete"
exit 0