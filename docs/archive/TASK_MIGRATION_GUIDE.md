# Task Migration Guide - Resolving Documentation Conflicts

**Date:** January 2025  
**Purpose:** Establish clear hierarchy and resolve conflicts between existing and new documentation

---

## Document Hierarchy

### Primary Documents (Authoritative)
1. **CTO_ROADMAP.md** - Overall strategic direction
2. **EXECUTION_PLAN.md** - High-level implementation guide
3. **BACKEND_TEAM_TASKS.md** - Backend team's specific tasks
4. **FRONTEND_TEAM_TASKS.md** - Frontend team's specific tasks

### Secondary Documents (Reference Only)
All existing documentation in frontend/ and backend/ folders should be considered historical reference.

---

## Critical Conflicts to Resolve

### Frontend Team

#### 1. Authentication Storage
**Conflict:** localStorage vs sessionStorage for tokens  
**Resolution:** Use approach in FRONTEND_TEAM_TASKS.md
- Access tokens: In-memory only
- Refresh tokens: localStorage (with httpOnly cookie preference in future)

#### 2. API Architecture
**Conflict:** Individual endpoints vs unified endpoint  
**Resolution:** 
- Use individual endpoints as specified in BACKEND_TEAM_TASKS.md
- Unified endpoint is deprecated

#### 3. State Management
**Conflict:** Various approaches mentioned  
**Resolution:** Use React Context + React Query as specified in new tasks

### Backend Team

#### 1. Authentication Status
**Conflict:** Implemented vs not enforced  
**Resolution:** Auth is implemented but DISABLED - must be re-enabled per BACKEND_TEAM_TASKS.md

#### 2. Security Implementation
**Conflict:** "Bank-grade" vs needs work  
**Resolution:** Security has vulnerabilities that MUST be fixed per Phase 0 tasks

#### 3. Multi-tenancy
**Conflict:** Simple vs comprehensive  
**Resolution:** Basic implementation exists, needs enhancement per Phase 2 tasks

---

## Migration Steps

### Week 1: Documentation Cleanup
1. **Archive conflicting documents**
   ```bash
   mkdir -p frontend/archive backend/archive
   
   # Frontend
   mv frontend/{BACKEND_INTEGRATION.md,ENTERPRISE_EVALUATION_REPORT.md,INTEGRATION_STATUS.md} frontend/archive/
   
   # Backend  
   mv backend/{BACKEND_COMPLETION_SUMMARY.md,BACKEND_READY_FOR_FRONTEND.md,PRODUCTION_READY_SUMMARY.md} backend/archive/
   ```

2. **Add deprecation notices** to remaining docs
   ```markdown
   > ⚠️ **DEPRECATED**: This document contains outdated information. 
   > Please refer to BACKEND_TEAM_TASKS.md / FRONTEND_TEAM_TASKS.md for current instructions.
   ```

3. **Create new structure**
   ```
   legal-ai/
   ├── CTO_ROADMAP.md (authoritative)
   ├── EXECUTION_PLAN.md (authoritative)
   ├── TASK_MIGRATION_GUIDE.md (this file)
   ├── backend/
   │   ├── BACKEND_TEAM_TASKS.md (authoritative)
   │   ├── CLAUDE.md (keep - useful for Claude agents)
   │   └── archive/ (historical docs)
   └── frontend/
       ├── FRONTEND_TEAM_TASKS.md (authoritative)
       ├── README.md (keep - basic setup)
       └── archive/ (historical docs)
   ```

---

## Key Decisions

### Authentication
- **JWT in Authorization header** (not cookies for now)
- **Refresh token in localStorage** (secure enough for MVP)
- **Access token in memory only**
- **Silent refresh before expiry**

### API Architecture
- **RESTful individual endpoints** (not GraphQL or unified)
- **Consistent /api prefix**
- **Version in URL when needed** (/api/v2)

### Security
- **Remove ALL hardcoded secrets immediately**
- **Implement proper CORS**
- **Enable auth middleware**
- **Add rate limiting**

### Testing
- **80% coverage minimum**
- **Jest/Vitest for unit tests**
- **Playwright for E2E**
- **MSW for API mocking**

---

## Communication Plan

1. **Team Meeting Required**
   - Review this migration guide
   - Assign owners for each conflict resolution
   - Set deadlines for archive/cleanup

2. **Update Sprint Board**
   - Create tickets for documentation cleanup
   - Link new authoritative docs
   - Archive old tickets referencing deprecated docs

3. **Notify Stakeholders**
   - Send summary of new documentation structure
   - Highlight critical security fixes needed
   - Update project wiki/confluence

---

## Verification Checklist

Before proceeding with Phase 0:

- [ ] All team members have read new task documents
- [ ] Conflicting documents are archived
- [ ] Deprecation notices added where needed
- [ ] Git history cleaned of sensitive data
- [ ] Environment variables properly configured
- [ ] CI/CD pipelines updated with new structure
- [ ] No hardcoded secrets remain in codebase

---

## Questions?

If any conflicts arise during implementation:
1. Check this guide first
2. Refer to CTO_ROADMAP.md for strategic decisions
3. Escalate to tech lead if still unclear

Remember: The new task documents supersede ALL previous instructions.