#!/bin/bash
# PrivateLegal AI - Update Package Builder
# Creates USB update packages for air-gapped deployments

set -euo pipefail

# Configuration
VERSION=${1:-""}
DESCRIPTION=${2:-"Regular update with bug fixes and improvements"}
BUILD_DIR="build/update_$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="updates"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   PrivateLegal AI - Update Package Builder${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check version parameter
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> [description]"
    echo "Example: $0 1.2.0 \"Security updates and performance improvements\""
    exit 1
fi

# Create build directory
echo -e "${YELLOW}Creating build directory...${NC}"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

# Copy backend files (excluding venv and cache)
echo -e "${YELLOW}Copying backend files...${NC}"
rsync -av \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='uploads/' \
    --exclude='*.db' \
    backend/ "$BUILD_DIR/backend/"

# Copy frontend dist files
echo -e "${YELLOW}Building frontend...${NC}"
cd frontend
npm run build
cd ..
cp -r frontend/dist "$BUILD_DIR/frontend/"

# Copy requirements
cp backend/requirements.txt "$BUILD_DIR/"

# Create update manifest
echo -e "${YELLOW}Creating update manifest...${NC}"
cat > "$BUILD_DIR/update_manifest.json" << EOF
{
    "version": "$VERSION",
    "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "description": "$DESCRIPTION",
    "type": "full",
    "min_version": "1.0.0",
    "components": {
        "backend": true,
        "frontend": true,
        "models": false,
        "database_migration": false
    }
}
EOF

# Create pre-update script
cat > "$BUILD_DIR/pre_update.sh" << 'EOF'
#!/bin/bash
# Pre-update tasks
echo "Running pre-update tasks..."

# Check disk space
required_space=1000  # MB
available_space=$(df -m /opt | awk 'NR==2 {print $4}')
if [ "$available_space" -lt "$required_space" ]; then
    echo "Error: Not enough disk space. Required: ${required_space}MB, Available: ${available_space}MB"
    exit 1
fi

# Check service status
if ! systemctl is-active --quiet privatelegal-backend; then
    echo "Warning: Backend service is not running"
fi

echo "Pre-update checks completed."
EOF

# Create post-update script
cat > "$BUILD_DIR/post_update.sh" << 'EOF'
#!/bin/bash
# Post-update tasks
echo "Running post-update tasks..."

# Clear caches
find /opt/privatelegal/legal-ai -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Update permissions
chown -R privatelegal:privatelegal /opt/privatelegal/legal-ai

# Restart background tasks
systemctl restart privatelegal-backend

echo "Post-update tasks completed."
EOF

# Make scripts executable
chmod +x "$BUILD_DIR"/*.sh

# Create update package
echo -e "${YELLOW}Creating update package...${NC}"
PACKAGE_NAME="privatelegal_update_v${VERSION}.tar.gz"
cd "$BUILD_DIR"
tar -czf "../$OUTPUT_DIR/$PACKAGE_NAME" .
cd ..

# Create USB package with all required files
echo -e "${YELLOW}Creating USB package...${NC}"
USB_DIR="$OUTPUT_DIR/usb_v${VERSION}"
mkdir -p "$USB_DIR"

# Copy update package
cp "$OUTPUT_DIR/$PACKAGE_NAME" "$USB_DIR/privatelegal_update.tar.gz"

# Create update marker file
touch "$USB_DIR/.privatelegal_update"

# Copy update manifest
cp "$BUILD_DIR/update_manifest.json" "$USB_DIR/"

# Create README for USB
cat > "$USB_DIR/README.txt" << EOF
PrivateLegal AI Update v$VERSION
================================

This USB contains an update for your PrivateLegal AI system.

To install this update:

1. Insert this USB drive into your PrivateLegal AI server
2. Log in to the server as administrator
3. Run: sudo /opt/privatelegal/usb_update.sh
4. Follow the on-screen instructions

The update process will:
- Automatically backup your current system
- Apply the update
- Verify system health
- Generate an update report on this USB

If the update fails, your system will be automatically rolled back.

For support: [SUPPORT-EMAIL]
EOF

# Create offline model updates (if needed)
if [ -d "models" ]; then
    echo -e "${YELLOW}Including model updates...${NC}"
    mkdir -p "$USB_DIR/models"
    cp models/*.gguf "$USB_DIR/models/" 2>/dev/null || true
fi

# Clean up build directory
rm -rf "$BUILD_DIR"

# Create ISO image for USB (optional)
if command -v mkisofs &> /dev/null; then
    echo -e "${YELLOW}Creating ISO image...${NC}"
    mkisofs -r -V "PrivateLegal_v$VERSION" -o "$OUTPUT_DIR/privatelegal_update_v${VERSION}.iso" "$USB_DIR"
fi

# Calculate checksums
echo -e "${YELLOW}Calculating checksums...${NC}"
cd "$OUTPUT_DIR"
sha256sum "$PACKAGE_NAME" > "$PACKAGE_NAME.sha256"
if [ -f "privatelegal_update_v${VERSION}.iso" ]; then
    sha256sum "privatelegal_update_v${VERSION}.iso" > "privatelegal_update_v${VERSION}.iso.sha256"
fi
cd ..

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   Update Package Created Successfully!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Version: $VERSION"
echo "Package: $OUTPUT_DIR/$PACKAGE_NAME"
echo "USB Package: $OUTPUT_DIR/usb_v${VERSION}/"
if [ -f "$OUTPUT_DIR/privatelegal_update_v${VERSION}.iso" ]; then
    echo "ISO Image: $OUTPUT_DIR/privatelegal_update_v${VERSION}.iso"
fi
echo ""
echo "To create a USB update drive:"
echo "1. Format a USB drive as FAT32 or exFAT"
echo "2. Copy all files from $OUTPUT_DIR/usb_v${VERSION}/ to the USB root"
echo "3. Safely eject and label the drive"
echo ""
echo "Or burn the ISO image to a USB/DVD if created."