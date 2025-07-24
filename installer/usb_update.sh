#!/bin/bash
# PrivateLegal AI - USB Update System
# Allows offline updates via USB drive

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
INSTALL_DIR="/opt/privatelegal"
UPDATE_MARKER=".privatelegal_update"
BACKUP_DIR="/var/backups/privatelegal/pre-update"
LOG_FILE="/var/log/privatelegal/update_$(date +%Y%m%d_%H%M%S).log"

# Ensure running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   PrivateLegal AI - USB Update System${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Function to find USB drive with update
find_update_drive() {
    echo -e "${YELLOW}Searching for update USB drive...${NC}"
    
    for device in /media/*/ /mnt/*/; do
        if [ -f "$device/$UPDATE_MARKER" ]; then
            echo -e "${GREEN}✓ Found update drive at: $device${NC}"
            USB_PATH="$device"
            return 0
        fi
    done
    
    echo -e "${RED}✗ No update USB drive found${NC}"
    echo "Please insert the PrivateLegal AI update USB drive and try again."
    echo "The drive must contain a file named: $UPDATE_MARKER"
    return 1
}

# Find the update drive
if ! find_update_drive; then
    exit 1
fi

# Verify update package
UPDATE_PACKAGE="$USB_PATH/privatelegal_update.tar.gz"
UPDATE_SIGNATURE="$USB_PATH/privatelegal_update.sig"
UPDATE_MANIFEST="$USB_PATH/update_manifest.json"

if [ ! -f "$UPDATE_PACKAGE" ]; then
    echo -e "${RED}✗ Update package not found: $UPDATE_PACKAGE${NC}"
    exit 1
fi

if [ ! -f "$UPDATE_MANIFEST" ]; then
    echo -e "${RED}✗ Update manifest not found: $UPDATE_MANIFEST${NC}"
    exit 1
fi

# Read update information
echo -e "${YELLOW}Reading update manifest...${NC}"
UPDATE_VERSION=$(jq -r '.version' "$UPDATE_MANIFEST")
UPDATE_DATE=$(jq -r '.date' "$UPDATE_MANIFEST")
UPDATE_DESCRIPTION=$(jq -r '.description' "$UPDATE_MANIFEST")
CURRENT_VERSION=$(cat "$INSTALL_DIR/VERSION" 2>/dev/null || echo "1.0.0")

echo ""
echo "Current version: $CURRENT_VERSION"
echo "Update version:  $UPDATE_VERSION"
echo "Update date:     $UPDATE_DATE"
echo ""
echo "Update description:"
echo "$UPDATE_DESCRIPTION"
echo ""

# Confirm update
read -p "Do you want to proceed with this update? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Update cancelled."
    exit 0
fi

# Create pre-update backup
echo -e "${YELLOW}Creating pre-update backup...${NC}"
mkdir -p "$BACKUP_DIR"
/usr/local/bin/privatelegal-backup
BACKUP_FILE=$(ls -t /var/backups/privatelegal/privatelegal_backup_*.tar.gz | head -1)
cp "$BACKUP_FILE" "$BACKUP_DIR/"
echo -e "${GREEN}✓ Backup saved to: $BACKUP_DIR${NC}"

# Stop services
echo -e "${YELLOW}Stopping services...${NC}"
systemctl stop privatelegal-backend nginx

# Extract update package
echo -e "${YELLOW}Extracting update package...${NC}"
TEMP_DIR=$(mktemp -d)
tar -xzf "$UPDATE_PACKAGE" -C "$TEMP_DIR"

# Check for update scripts
if [ -f "$TEMP_DIR/pre_update.sh" ]; then
    echo -e "${YELLOW}Running pre-update script...${NC}"
    bash "$TEMP_DIR/pre_update.sh"
fi

# Update application files
echo -e "${YELLOW}Updating application files...${NC}"
if [ -d "$TEMP_DIR/backend" ]; then
    rsync -av --delete "$TEMP_DIR/backend/" "$INSTALL_DIR/legal-ai/backend/"
fi

if [ -d "$TEMP_DIR/frontend" ]; then
    rsync -av --delete "$TEMP_DIR/frontend/" "$INSTALL_DIR/legal-ai/frontend/"
fi

# Update Python dependencies
if [ -f "$TEMP_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}Updating Python dependencies...${NC}"
    sudo -u privatelegal bash << EOF
cd "$INSTALL_DIR/legal-ai/backend"
source venv/bin/activate
pip install -r requirements.txt
EOF
fi

# Rebuild frontend if needed
if [ -d "$TEMP_DIR/frontend" ]; then
    echo -e "${YELLOW}Rebuilding frontend...${NC}"
    sudo -u privatelegal bash << EOF
cd "$INSTALL_DIR/legal-ai/frontend"
npm install
npm run build
EOF
fi

# Update AI models if included
if [ -d "$TEMP_DIR/models" ]; then
    echo -e "${YELLOW}Updating AI models...${NC}"
    for model in "$TEMP_DIR/models"/*.gguf; do
        if [ -f "$model" ]; then
            model_name=$(basename "$model")
            echo "Installing model: $model_name"
            cp "$model" "/var/lib/privatelegal/models/"
        fi
    done
fi

# Run database migrations
if [ -f "$TEMP_DIR/migrations.sql" ]; then
    echo -e "${YELLOW}Running database migrations...${NC}"
    sudo -u postgres psql privatelegal_db < "$TEMP_DIR/migrations.sql"
fi

# Update configuration if needed
if [ -f "$TEMP_DIR/config_updates.sh" ]; then
    echo -e "${YELLOW}Updating configuration...${NC}"
    bash "$TEMP_DIR/config_updates.sh"
fi

# Run post-update script
if [ -f "$TEMP_DIR/post_update.sh" ]; then
    echo -e "${YELLOW}Running post-update script...${NC}"
    bash "$TEMP_DIR/post_update.sh"
fi

# Update version file
echo "$UPDATE_VERSION" > "$INSTALL_DIR/VERSION"

# Clean up
rm -rf "$TEMP_DIR"

# Start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl start privatelegal-backend nginx

# Wait for services to be ready
sleep 10

# Run health check
echo -e "${YELLOW}Running health check...${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health | grep -q "200"; then
    echo -e "${GREEN}✓ System is healthy${NC}"
    UPDATE_SUCCESS=true
else
    echo -e "${RED}✗ System health check failed${NC}"
    UPDATE_SUCCESS=false
fi

# Generate update report
cat > "$USB_PATH/update_report_$(date +%Y%m%d_%H%M%S).txt" << EOF
PrivateLegal AI Update Report
============================
Date: $(date)
Previous Version: $CURRENT_VERSION
New Version: $UPDATE_VERSION
Status: $([ "$UPDATE_SUCCESS" = true ] && echo "SUCCESS" || echo "FAILED")
Backup Location: $BACKUP_DIR

Update Log: $LOG_FILE
EOF

if [ "$UPDATE_SUCCESS" = true ]; then
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}   Update Completed Successfully!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "System updated from v$CURRENT_VERSION to v$UPDATE_VERSION"
    echo ""
    echo "Please remove the USB drive and restart your browser."
else
    echo ""
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}   Update Failed!${NC}"
    echo -e "${RED}================================================${NC}"
    echo ""
    echo "The update process encountered errors."
    echo "The system has been rolled back to the previous version."
    echo ""
    echo "Please contact support with the update report from the USB drive."
    
    # Attempt rollback
    echo -e "${YELLOW}Attempting rollback...${NC}"
    systemctl stop privatelegal-backend nginx
    # Restore from backup
    tar -xzf "$BACKUP_DIR/$(basename $BACKUP_FILE)" -C /
    systemctl start privatelegal-backend nginx
fi