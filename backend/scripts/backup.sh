#!/bin/bash
# backup.sh - Production database backup script with S3 upload

set -e

# Configuration
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-legalai_production}"
DB_USER="${POSTGRES_USER:-legalai}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="legalai_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# S3 Configuration
S3_BUCKET="${BACKUP_S3_BUCKET}"
S3_PATH="database-backups/${BACKUP_FILE}"

# Retention
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Perform backup
log "Starting database backup..."
export PGPASSWORD="${DB_PASSWORD}"

pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-password \
    --verbose \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    --exclude-table=audit_logs \
    --exclude-table=session_activities \
    | gzip -9 > "${BACKUP_PATH}"

# Check backup size
BACKUP_SIZE=$(stat -c%s "${BACKUP_PATH}" 2>/dev/null || stat -f%z "${BACKUP_PATH}")
log "Backup completed. Size: $(numfmt --to=iec-i --suffix=B ${BACKUP_SIZE})"

# Verify backup integrity
log "Verifying backup integrity..."
if gunzip -t "${BACKUP_PATH}"; then
    log "Backup integrity verified"
else
    log "ERROR: Backup integrity check failed!"
    exit 1
fi

# Upload to S3 if configured
if [ -n "${S3_BUCKET}" ]; then
    log "Uploading backup to S3..."
    aws s3 cp "${BACKUP_PATH}" "s3://${S3_BUCKET}/${S3_PATH}" \
        --storage-class STANDARD_IA \
        --metadata "timestamp=${TIMESTAMP},size=${BACKUP_SIZE}" \
        --no-progress
    
    if [ $? -eq 0 ]; then
        log "Backup uploaded to S3 successfully"
        
        # Create a lifecycle policy JSON for S3
        cat > /tmp/lifecycle.json <<EOF
{
    "Rules": [{
        "Id": "DeleteOldBackups",
        "Status": "Enabled",
        "Filter": {"Prefix": "database-backups/"},
        "Expiration": {"Days": ${RETENTION_DAYS}}
    }]
}
EOF
        
        # Apply lifecycle policy
        aws s3api put-bucket-lifecycle-configuration \
            --bucket "${S3_BUCKET}" \
            --lifecycle-configuration file:///tmp/lifecycle.json 2>/dev/null || true
    else
        log "ERROR: Failed to upload backup to S3"
        exit 1
    fi
fi

# Clean up old local backups
log "Cleaning up old backups..."
find "${BACKUP_DIR}" -name "legalai_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Generate backup report
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "legalai_backup_*.sql.gz" | wc -l)
log "Backup complete. Total local backups: ${BACKUP_COUNT}"

# Send notification (if email is configured)
if [ -n "${SMTP_HOST}" ] && [ -n "${NOTIFICATION_EMAIL}" ]; then
    cat <<EOF | mail -s "Legal AI Database Backup Successful" "${NOTIFICATION_EMAIL}"
Database backup completed successfully.

Backup Details:
- Timestamp: ${TIMESTAMP}
- File: ${BACKUP_FILE}
- Size: $(numfmt --to=iec-i --suffix=B ${BACKUP_SIZE})
- Location: S3://${S3_BUCKET}/${S3_PATH}
- Local backups retained: ${BACKUP_COUNT}

This is an automated message from Legal AI Backup System.
EOF
fi

exit 0