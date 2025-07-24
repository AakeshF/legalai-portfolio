# ⚠️ IMPORTANT NOTICE - Frontend Team

**Date:** January 2025

## New Authoritative Documentation

The frontend team should now follow **FRONTEND_TEAM_TASKS.md** located in the parent directory as the primary source of implementation instructions.

## Document Status

### Active Documents ✅
- `/legal-ai/FRONTEND_TEAM_TASKS.md` - Your primary task list
- `/legal-ai/frontend/README.md` - Basic Vite setup (still valid)
- `/legal-ai/CTO_ROADMAP.md` - Overall strategy
- `/legal-ai/EXECUTION_PLAN.md` - Detailed implementation

### Deprecated Documents ❌
All other .md files in this directory contain conflicting or outdated information and should be considered historical reference only.

## Critical Actions Required

1. **Fix authentication integration** - Backend auth is ready but frontend isn't sending tokens
2. **Implement token management** as specified in TASK-FE-001
3. **Update all API calls** to use the new authenticated client
4. **Remove demo mode fallbacks** after auth is working

## Key Decisions Made

### Authentication
- Access tokens: **In-memory only** (not localStorage)
- Refresh tokens: **localStorage** (for MVP, httpOnly cookies later)
- Use **Authorization header** with Bearer tokens

### API Integration
- Use **individual REST endpoints** (not the unified endpoint)
- Implement **automatic retry** with token refresh
- Add **request interceptors** for auth

### State Management
- Use **React Context** for auth state
- Use **React Query** for server state
- No Redux/Zustand for now

## Where to Start

1. Read `/legal-ai/TASK_MIGRATION_GUIDE.md` for conflict resolutions
2. Start with **TASK-FE-001** in FRONTEND_TEAM_TASKS.md
3. Coordinate with backend team on auth testing

## Questions?

Contact the tech lead or refer to the CTO_ROADMAP.md for strategic decisions.