#!/bin/bash
# TASK-BE-002: Clean Git History Script
# WARNING: This script will rewrite git history
# Run from the repository root directory

echo "🔴 CRITICAL: Git History Cleanup Script"
echo "This will permanently remove sensitive data from git history"
echo ""

# Check if BFG is installed
if ! command -v bfg &> /dev/null; then
    echo "❌ BFG Repo Cleaner not found. Please install it first:"
    echo "   macOS: brew install bfg"
    echo "   Linux: wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar"
    exit 1
fi

# Confirm before proceeding
read -p "Have you created a backup? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Please create a backup first:"
    echo "tar -czf legalai_backup_$(date +%Y%m%d_%H%M%S).tar.gz ."
    exit 1
fi

echo "Starting git history cleanup..."

# Clean sensitive strings
echo "Removing sensitive strings..."
bfg --replace-text backend/sensitive_patterns.txt

# Remove sensitive files
echo "Removing sensitive files..."
bfg --delete-files '*.db'
bfg --delete-files '*.sqlite'
bfg --delete-files '*.sqlite3'

# Clean git history
echo "Cleaning git history..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "✅ Git history cleaned"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Review the changes: git log --oneline"
echo "2. Force push to remote: git push --force-with-lease origin main"
echo "3. All team members must re-clone the repository"
echo "4. Delete old backups containing sensitive data"