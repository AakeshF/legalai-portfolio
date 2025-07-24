# ⚠️ IMPORTANT NOTICE - Backend Team

**Date:** January 2025

## New Authoritative Documentation

The backend team should now follow **BACKEND_TEAM_TASKS.md** located in the parent directory as the primary source of implementation instructions.

## Document Status

### Active Documents ✅
- `/legal-ai/BACKEND_TEAM_TASKS.md` - Your primary task list
- `/legal-ai/backend/CLAUDE.md` - Still useful for Claude Code agents
- `/legal-ai/CTO_ROADMAP.md` - Overall strategy
- `/legal-ai/EXECUTION_PLAN.md` - Detailed implementation

### Deprecated Documents ❌
All other .md files in this directory should be considered historical reference only. They contain conflicting or outdated information.

## Critical Actions Required

1. **IMMEDIATELY remove hardcoded secrets** from config.py
2. **Clean git history** of sensitive data
3. **Re-enable authentication middleware** that is currently disabled
4. **Fix security vulnerabilities** identified in Phase 0

## Where to Start

1. Read `/legal-ai/TASK_MIGRATION_GUIDE.md` for conflict resolutions
2. Start with **TASK-BE-001** in BACKEND_TEAM_TASKS.md
3. Follow the weekly sprint structure outlined

## Questions?

Contact the tech lead or refer to the CTO_ROADMAP.md for strategic decisions.