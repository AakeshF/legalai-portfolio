#!/bin/bash
# PrivateLegal AI - Production Deployment Script
# Handles production deployment, monitoring, and maintenance

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION=${1:-"help"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Production configuration
PROD_DIR="/opt/privatelegal"
SERVICE_USER="privatelegal"
SERVICES=("privatelegal-backend" "ollama" "nginx" "postgresql")

# Helper functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This command must be run as root"
        exit 1
    fi
}

# Deploy new version
deploy() {
    check_root
    log "Starting production deployment..."
    
    # Pre-deployment backup
    log "Creating pre-deployment backup..."
    /usr/local/bin/privatelegal-backup
    
    # Stop services
    log "Stopping services..."
    systemctl stop privatelegal-backend
    
    # Pull latest code
    log "Updating code..."
    cd "$PROD_DIR/legal-ai"
    sudo -u "$SERVICE_USER" git pull origin main
    
    # Update dependencies
    log "Updating Python dependencies..."
    sudo -u "$SERVICE_USER" bash -c "cd backend && source venv/bin/activate && pip install -r requirements.txt"
    
    # Build frontend
    log "Building frontend..."
    sudo -u "$SERVICE_USER" bash -c "cd frontend && npm install && npm run build"
    
    # Run migrations
    log "Running database migrations..."
    sudo -u "$SERVICE_USER" bash -c "cd backend && source venv/bin/activate && python -c 'from database import engine, Base; Base.metadata.create_all(bind=engine)'"
    
    # Start services
    log "Starting services..."
    systemctl start privatelegal-backend
    
    # Health check
    sleep 5
    if health_check; then
        log "Deployment successful!"
    else
        error "Deployment failed! Rolling back..."
        rollback
    fi
}

# Health check
health_check() {
    log "Running health checks..."
    
    local all_healthy=true
    
    # Check services
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo -e "  ${GREEN}✓${NC} $service is running"
        else
            echo -e "  ${RED}✗${NC} $service is not running"
            all_healthy=false
        fi
    done
    
    # Check API
    if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health | grep -q "200"; then
        echo -e "  ${GREEN}✓${NC} API is responding"
    else
        echo -e "  ${RED}✗${NC} API is not responding"
        all_healthy=false
    fi
    
    # Check Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama is responding"
    else
        echo -e "  ${RED}✗${NC} Ollama is not responding"
        all_healthy=false
    fi
    
    # Check disk space
    local free_space=$(df -BG /opt | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$free_space" -lt 10 ]; then
        echo -e "  ${YELLOW}⚠${NC} Low disk space: ${free_space}GB free"
        warning "Consider cleaning up old backups"
    else
        echo -e "  ${GREEN}✓${NC} Disk space: ${free_space}GB free"
    fi
    
    # Check memory
    local free_mem=$(free -g | awk '/^Mem:/{print $7}')
    echo -e "  ${GREEN}✓${NC} Available memory: ${free_mem}GB"
    
    $all_healthy
}

# Monitor system
monitor() {
    clear
    echo -e "${GREEN}PrivateLegal AI - System Monitor${NC}"
    echo "Press Ctrl+C to exit"
    echo ""
    
    while true; do
        # System resources
        echo -e "${YELLOW}System Resources:${NC}"
        echo -n "  CPU: "
        top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}'
        
        echo -n "  Memory: "
        free -h | awk '/^Mem:/ {print $3 " / " $2}'
        
        echo -n "  GPU: "
        nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1 | awk '{print $1"%"}'
        
        # Service status
        echo -e "\n${YELLOW}Services:${NC}"
        for service in "${SERVICES[@]}"; do
            if systemctl is-active --quiet "$service"; then
                echo -e "  ${GREEN}●${NC} $service"
            else
                echo -e "  ${RED}●${NC} $service"
            fi
        done
        
        # Active users
        echo -e "\n${YELLOW}Active Sessions:${NC}"
        local sessions=$(sudo -u "$SERVICE_USER" psql -d privatelegal_db -t -c "SELECT COUNT(*) FROM chat_sessions WHERE updated_at > NOW() - INTERVAL '5 minutes'" 2>/dev/null || echo "0")
        echo "  Active users: $sessions"
        
        # Recent activity
        echo -e "\n${YELLOW}Recent Activity:${NC}"
        tail -3 /var/log/privatelegal/app.log 2>/dev/null | sed 's/^/  /'
        
        sleep 5
        clear
        echo -e "${GREEN}PrivateLegal AI - System Monitor${NC}"
        echo "Press Ctrl+C to exit"
        echo ""
    done
}

# View logs
logs() {
    local service=${2:-"all"}
    local lines=${3:-100}
    
    if [ "$service" = "all" ]; then
        log "Showing recent logs from all services..."
        journalctl -u privatelegal-backend -u ollama -u nginx -n "$lines" --no-pager
    else
        log "Showing logs for $service..."
        journalctl -u "$service" -n "$lines" -f
    fi
}

# Backup system
backup() {
    check_root
    log "Running manual backup..."
    /usr/local/bin/privatelegal-backup
    
    # List recent backups
    log "Recent backups:"
    ls -lht /var/backups/privatelegal/*.tar.gz | head -5
}

# Rollback deployment
rollback() {
    check_root
    warning "Rolling back to previous version..."
    
    # Find latest backup
    local latest_backup=$(ls -t /var/backups/privatelegal/privatelegal_backup_*.tar.gz | head -1)
    
    if [ -z "$latest_backup" ]; then
        error "No backup found!"
        exit 1
    fi
    
    log "Using backup: $latest_backup"
    
    # Stop services
    systemctl stop privatelegal-backend nginx
    
    # Extract backup
    tar -xzf "$latest_backup" -C / --strip-components=1
    
    # Start services
    systemctl start privatelegal-backend nginx
    
    # Check health
    sleep 5
    if health_check; then
        log "Rollback successful!"
    else
        error "Rollback failed! Manual intervention required."
    fi
}

# Performance tuning
tune_performance() {
    check_root
    log "Optimizing system performance..."
    
    # PostgreSQL tuning
    log "Tuning PostgreSQL..."
    cat >> /etc/postgresql/*/main/postgresql.conf << EOF

# PrivateLegal AI Performance Tuning
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
EOF
    
    # System tuning
    log "Tuning system parameters..."
    cat >> /etc/sysctl.conf << EOF

# PrivateLegal AI Performance Tuning
vm.swappiness=10
vm.dirty_ratio=15
vm.dirty_background_ratio=5
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 134217728
net.ipv4.tcp_wmem=4096 65536 134217728
EOF
    
    sysctl -p
    
    # NVIDIA GPU tuning
    log "Configuring GPU persistence..."
    nvidia-smi -pm 1
    
    systemctl restart postgresql
    
    log "Performance tuning complete!"
}

# User management
manage_users() {
    local subcommand=${2:-"list"}
    
    case "$subcommand" in
        list)
            log "Listing users..."
            sudo -u "$SERVICE_USER" psql -d privatelegal_db -c "SELECT email, full_name, is_active, created_at FROM users ORDER BY created_at DESC"
            ;;
        add)
            local email=${3:-""}
            local name=${4:-""}
            if [ -z "$email" ] || [ -z "$name" ]; then
                error "Usage: $0 users add <email> <name>"
                exit 1
            fi
            log "Adding user: $email"
            # Generate random password
            local password=$(openssl rand -base64 12)
            # Add user via Python script
            sudo -u "$SERVICE_USER" bash -c "cd $PROD_DIR/legal-ai/backend && source venv/bin/activate && python -c \"
from database import SessionLocal
from models import User
from auth_utils import get_password_hash
import uuid
db = SessionLocal()
user = User(
    id=str(uuid.uuid4()),
    email='$email',
    username='$email',
    full_name='$name',
    hashed_password=get_password_hash('$password'),
    is_active=True
)
db.add(user)
db.commit()
db.close()
print('User created successfully!')
print('Password:', '$password')
\""
            ;;
        disable)
            local email=${3:-""}
            if [ -z "$email" ]; then
                error "Usage: $0 users disable <email>"
                exit 1
            fi
            log "Disabling user: $email"
            sudo -u "$SERVICE_USER" psql -d privatelegal_db -c "UPDATE users SET is_active = false WHERE email = '$email'"
            ;;
        *)
            error "Unknown user command: $subcommand"
            echo "Available commands: list, add, disable"
            ;;
    esac
}

# Show usage
usage() {
    cat << EOF
PrivateLegal AI - Production Management

Usage: $0 <command> [options]

Commands:
    deploy              Deploy latest version from git
    health              Run system health check
    monitor             Real-time system monitoring
    logs [service]      View system logs
    backup              Create manual backup
    rollback            Rollback to previous version
    tune                Optimize system performance
    users [action]      Manage user accounts
    help                Show this help message

Examples:
    $0 deploy                    # Deploy latest version
    $0 health                    # Check system health
    $0 monitor                   # Monitor system in real-time
    $0 logs backend              # View backend logs
    $0 users add [USER-EMAIL] "John Doe"  # Add user

For support: [SUPPORT-EMAIL]
EOF
}

# Main command handler
case "$ACTION" in
    deploy)
        deploy
        ;;
    health)
        health_check
        ;;
    monitor)
        monitor
        ;;
    logs)
        logs "$@"
        ;;
    backup)
        backup
        ;;
    rollback)
        rollback
        ;;
    tune)
        tune_performance
        ;;
    users)
        manage_users "$@"
        ;;
    help|*)
        usage
        ;;
esac