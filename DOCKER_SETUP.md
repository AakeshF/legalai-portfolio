# Docker Setup Guide

## Quick Start

### Development Environment

1. **Copy environment files**:
   ```bash
   # Backend
   cp backend/.env.example backend/.env
   # Edit backend/.env with your API keys

   # Frontend (if needed)
   cp frontend/.env.example frontend/.env
   ```

2. **Start development environment**:
   ```bash
   # Start all services
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

   # Or run in background
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

3. **Access services**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - pgAdmin: http://localhost:5050 (with --profile tools)
   - MailHog: http://localhost:8025 (with --profile tools)

### Running with Development Tools

```bash
# Include optional development tools
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile tools up
```

### Database Management

```bash
# Run migrations
docker-compose exec backend python migrate_db.py

# Access PostgreSQL CLI
docker-compose exec postgres psql -U legalai -d legalai

# Create database backup
docker-compose exec postgres pg_dump -U legalai legalai > backup.sql
```

### Common Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild after code changes
docker-compose build backend
docker-compose build frontend

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Production Deployment

1. **Set up secrets**:
   ```bash
   mkdir -p secrets
   echo "your-secure-password" > secrets/db_password.txt
   chmod 600 secrets/db_password.txt
   ```

2. **Configure environment**:
   ```bash
   # Copy production env template
   cp backend/.env.production backend/.env
   # Edit with production values
   ```

3. **Deploy**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Troubleshooting

### Backend not connecting to database
- Check DATABASE_URL in backend/.env
- Ensure postgres service is running
- Verify postgres credentials match

### Frontend can't reach backend
- Check VITE_API_URL in frontend environment
- Ensure backend is running and healthy
- Check for CORS issues

### Permission errors
- Run `docker-compose down -v` to reset volumes
- Check file ownership in mounted volumes
- Ensure proper permissions on .env files