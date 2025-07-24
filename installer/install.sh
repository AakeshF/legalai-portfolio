#!/bin/bash
# PrivateLegal AI - Hardware Installer
# This script turns a fresh Ubuntu/Debian system into a PrivateLegal AI appliance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/privatelegal"
DATA_DIR="/var/lib/privatelegal"
LOG_DIR="/var/log/privatelegal"
BACKUP_DIR="/var/backups/privatelegal"
SERVICE_USER="privatelegal"

# Logging
LOG_FILE="/tmp/privatelegal_install_$(date +%Y%m%d_%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   PrivateLegal AI - Enterprise Installer${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Check system requirements
echo -e "${YELLOW}Checking system requirements...${NC}"

# Check Ubuntu version
if ! grep -q "Ubuntu" /etc/os-release; then
    echo -e "${RED}This installer requires Ubuntu 22.04 or later${NC}"
    exit 1
fi

# Check NVIDIA GPU
if ! nvidia-smi &> /dev/null; then
    echo -e "${RED}NVIDIA GPU not detected. Please install NVIDIA drivers first.${NC}"
    echo "Run: sudo ubuntu-drivers autoinstall"
    exit 1
fi

# Check available RAM (minimum 32GB)
total_ram=$(free -g | awk '/^Mem:/{print $2}')
if [ "$total_ram" -lt 32 ]; then
    echo -e "${YELLOW}Warning: System has less than 32GB RAM. Performance may be limited.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check disk space (minimum 500GB free)
free_space=$(df -BG /opt | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$free_space" -lt 500 ]; then
    echo -e "${YELLOW}Warning: Less than 500GB free space. Recommended: 1TB+${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓ System requirements met${NC}"

# Create service user
echo -e "${YELLOW}Creating service user...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" "$SERVICE_USER"
fi

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR" "$BACKUP_DIR"
mkdir -p "$DATA_DIR"/{uploads,models,database}
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR" "$BACKUP_DIR"

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    curl \
    git \
    build-essential \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    ufw \
    fail2ban \
    unattended-upgrades \
    htop \
    nvtop \
    ncdu

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install Docker (for Ollama)
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker "$SERVICE_USER"
fi

# Install Ollama
echo -e "${YELLOW}Installing Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh
fi

# Configure PostgreSQL
echo -e "${YELLOW}Configuring PostgreSQL...${NC}"
sudo -u postgres psql << EOF
CREATE USER $SERVICE_USER WITH PASSWORD 'privatelegal_secure_password';
CREATE DATABASE privatelegal_db OWNER $SERVICE_USER;
GRANT ALL PRIVILEGES ON DATABASE privatelegal_db TO $SERVICE_USER;
EOF

# Clone the application
echo -e "${YELLOW}Installing PrivateLegal AI application...${NC}"
cd "$INSTALL_DIR"
if [ ! -d "legal-ai" ]; then
    git clone https://github.com/privatelegal/legal-ai.git
fi
cd legal-ai
chown -R "$SERVICE_USER:$SERVICE_USER" .

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/legal-ai/backend"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF

# Install frontend dependencies and build
echo -e "${YELLOW}Building frontend...${NC}"
sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/legal-ai/frontend"
npm install
npm run build
EOF

# Configure environment
echo -e "${YELLOW}Configuring environment...${NC}"
cat > "$INSTALL_DIR/legal-ai/backend/.env" << EOF
# Database
DATABASE_URL=postgresql://$SERVICE_USER:privatelegal_secure_password@localhost/privatelegal_db

# AI Configuration
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b

# Security
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Paths
UPLOAD_DIRECTORY=$DATA_DIR/uploads
LOG_DIRECTORY=$LOG_DIR

# Features
DISABLE_AUTH=false
EMAIL_ENABLED=false
DEBUG=false
EOF

chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/legal-ai/backend/.env"
chmod 600 "$INSTALL_DIR/legal-ai/backend/.env"

# Download and configure AI models
echo -e "${YELLOW}Downloading AI models (this may take a while)...${NC}"
ollama pull llama3:8b
ollama pull nomic-embed-text  # For embeddings

# Create systemd services
echo -e "${YELLOW}Creating system services...${NC}"

# Backend service
cat > /etc/systemd/system/privatelegal-backend.service << EOF
[Unit]
Description=PrivateLegal AI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/legal-ai/backend
Environment="PATH=$INSTALL_DIR/legal-ai/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/legal-ai/backend/venv/bin/python start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Ollama service
cat > /etc/systemd/system/ollama.service << EOF
[Unit]
Description=Ollama AI Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_MODELS=$DATA_DIR/models"

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo -e "${YELLOW}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/privatelegal << 'EOF'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 500M;
    
    # Frontend
    location / {
        root /opt/privatelegal/legal-ai/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/privatelegal /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Configure firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Create backup script
echo -e "${YELLOW}Setting up automated backups...${NC}"
cat > /usr/local/bin/privatelegal-backup << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/privatelegal"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="privatelegal_backup_$DATE"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup database
sudo -u postgres pg_dump privatelegal_db > "$BACKUP_DIR/$BACKUP_NAME/database.sql"

# Backup uploaded files
tar -czf "$BACKUP_DIR/$BACKUP_NAME/uploads.tar.gz" -C /var/lib/privatelegal uploads/

# Backup configuration
cp /opt/privatelegal/legal-ai/backend/.env "$BACKUP_DIR/$BACKUP_NAME/"

# Compress everything
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
rm -rf "$BACKUP_DIR/$BACKUP_NAME"

# Keep only last 30 backups
find "$BACKUP_DIR" -name "privatelegal_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
EOF

chmod +x /usr/local/bin/privatelegal-backup

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/privatelegal-backup") | crontab -

# Enable and start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl daemon-reload
systemctl enable postgresql ollama privatelegal-backend nginx
systemctl restart postgresql ollama privatelegal-backend nginx

# Wait for services to start
sleep 10

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/legal-ai/backend"
source venv/bin/activate
python -c "from database import engine, Base; Base.metadata.create_all(bind=engine)"
EOF

# Create admin user
echo -e "${YELLOW}Creating admin user...${NC}"
ADMIN_PASSWORD=$(openssl rand -base64 12)
sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/legal-ai/backend"
source venv/bin/activate
python << PYTHON
from database import SessionLocal
from models import User, Organization
from auth_utils import get_password_hash
import uuid

db = SessionLocal()

# Create default organization
org = Organization(
    id=str(uuid.uuid4()),
    name="Default Law Firm",
    domain="privatelegal.local"
)
db.add(org)
db.commit()

# Create admin user
admin = User(
    id=str(uuid.uuid4()),
    email="admin@example.local",
    username="admin",
    full_name="System Administrator",
    hashed_password=get_password_hash("$ADMIN_PASSWORD"),
    is_active=True,
    is_superuser=True,
    organization_id=org.id
)
db.add(admin)
db.commit()
db.close()
PYTHON
EOF

# System health check
echo -e "${YELLOW}Running system health check...${NC}"
sleep 5

# Check if services are running
if systemctl is-active --quiet privatelegal-backend; then
    echo -e "${GREEN}✓ Backend service running${NC}"
else
    echo -e "${RED}✗ Backend service failed to start${NC}"
fi

if systemctl is-active --quiet ollama; then
    echo -e "${GREEN}✓ Ollama service running${NC}"
else
    echo -e "${RED}✗ Ollama service failed to start${NC}"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx service running${NC}"
else
    echo -e "${RED}✗ Nginx service failed to start${NC}"
fi

# Test API endpoint
if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health | grep -q "200"; then
    echo -e "${GREEN}✓ API responding${NC}"
else
    echo -e "${RED}✗ API not responding${NC}"
fi

# Get system IP
SYSTEM_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "Access PrivateLegal AI at: ${GREEN}http://$SYSTEM_IP${NC}"
echo ""
echo -e "Admin credentials:"
echo -e "  Username: ${GREEN}admin@example.local${NC}"
echo -e "  Password: ${GREEN}$ADMIN_PASSWORD${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Save these credentials securely!${NC}"
echo ""
echo -e "Log file saved to: $LOG_FILE"
echo ""
echo -e "Next steps:"
echo -e "1. Access the web interface and change the admin password"
echo -e "2. Create user accounts for attorneys"
echo -e "3. Upload your firm's documents"
echo -e "4. Configure backup retention policies"
echo ""
echo -e "${GREEN}Welcome to truly private AI for law firms!${NC}"