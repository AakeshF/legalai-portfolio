# Production Deployment Guide - Legal AI Backend

## Overview
This guide covers deploying the Legal AI Backend for production use by solo practitioners and small law firms.

## Prerequisites

### 1. Infrastructure Requirements
- **Server**: 4 vCPUs, 8GB RAM minimum (16GB recommended)
- **Storage**: 100GB SSD (expandable based on document volume)
- **Database**: PostgreSQL 15+ (managed service recommended)
- **Cache**: Redis 7+ (managed service recommended)
- **SSL Certificate**: Valid certificate for your domain

### 2. Domain Setup
- Production domain (e.g., `app.legalai.com`)
- DNS A record pointing to server IP
- SPF/DKIM records for email sending

### 3. Required Services
- **[AI Provider] API Key** for AI processing
- **SMTP Service** (SendGrid, AWS SES, or similar)
- **S3-compatible storage** for backups
- **Sentry** for error tracking (optional but recommended)

## Deployment Steps

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install additional tools
sudo apt install -y git nginx certbot python3-certbot-nginx awscli
```

### 2. SSL Certificate Setup

```bash
# Obtain SSL certificate using Let's Encrypt
sudo certbot --nginx -d app.legalai.com -d www.legalai.com

# Create DH parameters for extra security
sudo openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
```

### 3. Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/legal-ai-backend.git
cd legal-ai-backend

# Create required directories
mkdir -p uploads logs backups
chmod 755 uploads logs backups
```

### 4. Environment Configuration

```bash
# Copy production environment template
cp .env.production.template .env.production

# Edit with your values
nano .env.production
```

Required environment variables:
```env
# Database
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=<your-postgres-host>

# Redis
REDIS_PASSWORD=<strong-password>
REDIS_HOST=<your-redis-host>

# Security
SECRET_KEY=<generate-64-char-key>
JWT_SECRET_KEY=<generate-64-char-key>

# AI Service
DEEPSEEK_API_KEY=<your-[ai-provider]-api-key>

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_USERNAME=apikey
SMTP_PASSWORD=<your-sendgrid-api-key>
EMAIL_FROM_ADDRESS=[email@example.com]

# Monitoring
SENTRY_DSN=<your-sentry-dsn>

# Backup
AWS_ACCESS_KEY_ID=<your-aws-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret>
BACKUP_S3_BUCKET=legalai-backups
```

### 5. Build and Deploy

```bash
# Build Docker images
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# Check logs
docker-compose -f docker-compose.production.yml logs -f
```

### 6. Database Setup

```bash
# Run initial migrations
docker-compose -f docker-compose.production.yml exec backend alembic upgrade head

# Create initial admin user
docker-compose -f docker-compose.production.yml exec backend python scripts/create_admin.py
```

### 7. Nginx Configuration

```bash
# Copy Nginx configuration
sudo cp nginx/conf.d/legalai.conf /etc/nginx/sites-available/legalai
sudo ln -s /etc/nginx/sites-available/legalai /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 8. Configure Backups

```bash
# Make backup script executable
chmod +x scripts/backup.sh

# Test backup
docker-compose -f docker-compose.production.yml exec backup /backup.sh

# Verify cron job is running
docker-compose -f docker-compose.production.yml exec backup crontab -l
```

## Post-Deployment

### 1. Health Checks

```bash
# Check application health
curl https://app.legalai.com/health

# Detailed health check
curl https://app.legalai.com/health/detailed
```

### 2. Security Checklist

- [ ] Change all default passwords
- [ ] Enable firewall (allow only 80, 443, 22)
- [ ] Configure fail2ban for SSH
- [ ] Set up monitoring alerts
- [ ] Review security headers: https://securityheaders.com
- [ ] Enable audit logging
- [ ] Configure rate limiting

### 3. Monitoring Setup

```bash
# View metrics
curl http://localhost:9090/metrics

# Check Prometheus
docker-compose -f docker-compose.production.yml logs prometheus

# Monitor resources
docker stats
```

### 4. Create Organizations

```python
# Connect to container
docker-compose -f docker-compose.production.yml exec backend python

# Create organization
from models import Organization
from database import SessionLocal

db = SessionLocal()
org = Organization(
    name="Smith & Associates",
    billing_email="[email@example.com]",
    subscription_tier="pro"
)
db.add(org)
db.commit()
```

## Maintenance

### Daily Tasks
- Monitor error logs
- Check backup completion
- Review resource usage

### Weekly Tasks
- Update Docker images
- Review security alerts
- Check SSL certificate expiry
- Analyze performance metrics

### Monthly Tasks
- Test backup restoration
- Review and rotate access keys
- Update dependencies
- Performance optimization

## Scaling Considerations

### For Growing Firms
1. **Database**: Move to managed PostgreSQL (AWS RDS, Google Cloud SQL)
2. **Redis**: Use managed Redis (AWS ElastiCache, Redis Cloud)
3. **Storage**: Implement CDN for documents
4. **Application**: Scale horizontally with load balancer

### Performance Tuning
```bash
# Increase worker processes based on CPU cores
docker-compose -f docker-compose.production.yml exec backend \
  gunicorn main:app --workers 8

# Adjust PostgreSQL settings
max_connections = 200
shared_buffers = 2GB
effective_cache_size = 6GB
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL connectivity
   docker-compose -f docker-compose.production.yml exec backend \
     psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB
   ```

2. **Redis Connection Failed**
   ```bash
   # Test Redis connection
   docker-compose -f docker-compose.production.yml exec backend \
     redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD ping
   ```

3. **High Memory Usage**
   ```bash
   # Restart services
   docker-compose -f docker-compose.production.yml restart backend
   
   # Clear Redis cache
   docker-compose -f docker-compose.production.yml exec redis \
     redis-cli -a $REDIS_PASSWORD FLUSHDB
   ```

### Logs Location
- Application logs: `./logs/`
- Nginx logs: `/var/log/nginx/`
- Docker logs: `docker-compose logs [service]`

## Support

- Documentation: https://docs.example.com
- Email: [email@example.com]
- Emergency: +1-XXX-XXX-XXXX (24/7 for enterprise customers)

## Legal Compliance

Ensure your deployment complies with:
- GDPR (if serving EU clients)
- State bar regulations for legal technology
- Data retention requirements (7 years for legal documents)
- Client confidentiality requirements

---

Last Updated: December 2024
Version: 1.0.0