#!/bin/bash
# migrate.sh - Production database migration script

set -e

# Configuration
export DATABASE_URL="${DATABASE_URL:-postgresql://legalai:password@localhost/legalai_production}"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    log "ERROR: Alembic is not installed"
    exit 1
fi

# Function to run migrations
run_migrations() {
    log "Running database migrations..."
    
    # Check current revision
    CURRENT_REV=$(alembic current 2>/dev/null | grep -oE '[a-f0-9]{12}' || echo "none")
    log "Current revision: ${CURRENT_REV}"
    
    # Check for pending migrations
    PENDING=$(alembic history --verbose 2>/dev/null | grep -c "(head)" || echo "0")
    
    if [ "${PENDING}" -eq "0" ]; then
        log "No pending migrations found"
    else
        log "Found ${PENDING} pending migration(s)"
        
        # Show pending migrations
        log "Pending migrations:"
        alembic history --verbose | head -n 10
        
        # Create backup before migration
        if [ "${SKIP_BACKUP}" != "true" ]; then
            log "Creating pre-migration backup..."
            ./scripts/backup.sh
        fi
        
        # Run migrations
        log "Applying migrations..."
        alembic upgrade head
        
        # Verify migration
        NEW_REV=$(alembic current | grep -oE '[a-f0-9]{12}')
        log "Migration complete. New revision: ${NEW_REV}"
    fi
}

# Function to create a new migration
create_migration() {
    if [ -z "$1" ]; then
        log "ERROR: Migration message required"
        echo "Usage: $0 create \"migration message\""
        exit 1
    fi
    
    log "Creating new migration: $1"
    alembic revision --autogenerate -m "$1"
    
    log "Migration created. Please review the generated file before applying."
}

# Function to rollback migrations
rollback_migration() {
    TARGET="${1:-'-1'}"
    
    log "WARNING: Rolling back migration to: ${TARGET}"
    read -p "Are you sure you want to rollback? (yes/no): " CONFIRM
    
    if [ "${CONFIRM}" != "yes" ]; then
        log "Rollback cancelled"
        exit 0
    fi
    
    # Create backup before rollback
    log "Creating pre-rollback backup..."
    ./scripts/backup.sh
    
    # Perform rollback
    alembic downgrade "${TARGET}"
    
    log "Rollback complete"
}

# Main script logic
case "${1:-run}" in
    "run"|"upgrade")
        run_migrations
        ;;
    "create")
        create_migration "$2"
        ;;
    "rollback")
        rollback_migration "$2"
        ;;
    "current")
        alembic current
        ;;
    "history")
        alembic history --verbose
        ;;
    *)
        echo "Usage: $0 {run|create|rollback|current|history}"
        echo ""
        echo "Commands:"
        echo "  run/upgrade  - Run pending migrations"
        echo "  create       - Create a new migration"
        echo "  rollback     - Rollback to previous migration"
        echo "  current      - Show current migration"
        echo "  history      - Show migration history"
        exit 1
        ;;
esac

exit 0