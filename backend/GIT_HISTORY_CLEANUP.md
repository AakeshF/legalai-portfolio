# Git History Cleanup Instructions

## TASK-BE-002 Status

**Status**: Script prepared, requires manual execution  
**Priority**: 🔴 CRITICAL  
**Blocker**: Requires BFG installation and repository-level access

## Sensitive Data Found in Git History

The following sensitive data exists in commit e40e13b:
- [AI Provider] API key: `YOUR_API_KEY_HERE`
- Encryption key: `YOUR_ENCRYPTION_KEY_HERE`
- JWT secrets: `your-secret-key-change-in-production`
- Hardcoded passwords: `[REMOVED]`

## Steps to Complete

1. **Install BFG Repo Cleaner**:
   ```bash
   # macOS
   brew install bfg
   
   # Linux
   wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
   ```

2. **Create Backup**:
   ```bash
   cd /path/to/legal-ai
   tar -czf ../legalai_backup_$(date +%Y%m%d_%H%M%S).tar.gz .
   ```

3. **Run Cleanup Script**:
   ```bash
   cd /path/to/legal-ai
   ./backend/clean_git_history.sh
   ```

4. **Force Push**:
   ```bash
   git push --force-with-lease origin main
   ```

5. **Team Notification**:
   - All team members must delete local repos
   - Re-clone from remote after cleanup
   - Update any CI/CD credentials

## Files Created

- `sensitive_patterns.txt` - List of patterns to remove
- `clean_git_history.sh` - Automated cleanup script
- This documentation file

## Important Notes

⚠️ This operation will rewrite git history
⚠️ Requires coordination with entire team
⚠️ Must be done before any production deployment