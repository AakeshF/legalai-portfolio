# Production Deployment Guide

## Overview

This guide covers deploying the Legal AI Frontend for production use by law firms and legal professionals.

## Pre-Deployment Checklist

### 1. Environment Configuration

```bash
# Create production .env file
cp .env.example .env.production
```

Required environment variables:
```env
# API Configuration
VITE_API_URL=https://api.legalai.com
VITE_API_TIMEOUT=30000

# Environment
VITE_ENV=production

# Feature Flags
VITE_ENABLE_2FA=true
VITE_ENABLE_AUDIT_LOGS=true
VITE_ENABLE_DATA_EXPORT=true
VITE_ENABLE_DEMO_MODE=false
VITE_ENABLE_ANALYTICS=true

# Third-party Services
VITE_SENTRY_DSN=your-sentry-dsn
VITE_STRIPE_PUBLIC_KEY=your-stripe-key
VITE_INTERCOM_APP_ID=your-intercom-id

# Support
VITE_SUPPORT_EMAIL=[SUPPORT-EMAIL]
VITE_SUPPORT_PHONE=[SUPPORT-PHONE]
```

### 2. Security Checks

- [ ] All API endpoints use HTTPS
- [ ] Authentication tokens are securely stored
- [ ] Content Security Policy (CSP) headers configured
- [ ] CORS properly configured on backend
- [ ] No sensitive data in client-side code
- [ ] All dependencies updated and audited

### 3. Performance Optimization

```bash
# Build optimized production bundle
npm run build:prod

# Analyze bundle size
npm run build:analyze
```

## Deployment Steps

### 1. Build Process

```bash
# Install dependencies
npm ci

# Run tests
npm test

# Type check
npm run typecheck

# Lint
npm run lint

# Build production bundle
npm run build:prod
```

### 2. Deployment Options

#### Option A: AWS S3 + CloudFront

```bash
# Upload to S3
aws s3 sync dist/ s3://legal-ai-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

#### Option B: Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

#### Option C: Docker

```dockerfile
# Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 3. CDN Configuration

Recommended CDN headers:
```
Cache-Control: public, max-age=31536000, immutable  # For assets
Cache-Control: no-cache, no-store, must-revalidate  # For index.html
```

### 4. Monitoring Setup

#### Error Tracking (Sentry)

```javascript
// Already configured in ErrorBoundary
// Ensure VITE_SENTRY_DSN is set
```

#### Analytics

```javascript
// Add to index.html
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
```

#### Performance Monitoring

- Set up Real User Monitoring (RUM)
- Configure Web Vitals tracking
- Monitor API response times

## Post-Deployment

### 1. Health Checks

- [ ] Application loads correctly
- [ ] Authentication works
- [ ] Document upload functions
- [ ] AI chat responds
- [ ] PWA installs correctly
- [ ] Offline mode works

### 2. Performance Verification

```bash
# Run Lighthouse audit
lighthouse https://app.legalai.com --view
```

Target metrics:
- Performance: > 90
- Accessibility: 100
- Best Practices: 100
- SEO: 100
- PWA: Pass

### 3. Security Headers

Ensure these headers are set:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

## Rollback Procedure

1. Keep previous build artifacts
2. Document deployment versions
3. Quick rollback command:
   ```bash
   # S3 example
   aws s3 sync s3://legal-ai-frontend-backup/v1.2.3 s3://legal-ai-frontend --delete
   ```

## Maintenance

### Regular Tasks

- **Daily**: Monitor error rates and performance
- **Weekly**: Review user feedback and analytics
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Performance audit and optimization

### Update Procedure

1. Test updates in staging environment
2. Schedule maintenance window
3. Notify users via in-app banner
4. Deploy with rollback plan ready
5. Verify deployment success
6. Monitor for issues

## Support Integration

### Customer Support Tools

1. **Intercom**: Chat support widget
2. **Zendesk**: Ticket management
3. **StatusPage**: Service status updates

### Documentation

- User guides at `/help`
- API docs at `/docs/api`
- Video tutorials at `/tutorials`

## Legal Compliance

### Required Pages

- [ ] Terms of Service
- [ ] Privacy Policy
- [ ] Cookie Policy
- [ ] Data Processing Agreement
- [ ] Acceptable Use Policy

### Data Handling

- Ensure GDPR compliance
- Implement data retention policies
- Set up data export functionality
- Configure deletion procedures

## Scaling Considerations

### Performance Optimization

1. **Image Optimization**
   - Use WebP format
   - Implement lazy loading
   - Serve responsive images

2. **Code Splitting**
   - Already implemented for major routes
   - Monitor bundle sizes

3. **Caching Strategy**
   - Service Worker caching
   - API response caching
   - CDN caching

### Load Testing

```bash
# Example with Artillery
artillery quick --count 1000 --num 100 https://app.legalai.com
```

## Troubleshooting

### Common Issues

1. **Blank Page**
   - Check console errors
   - Verify API URL configuration
   - Clear browser cache

2. **Authentication Failures**
   - Verify JWT configuration
   - Check CORS settings
   - Confirm API endpoints

3. **Upload Issues**
   - Check file size limits
   - Verify MIME types
   - Test API endpoints

### Debug Mode

Enable debug logging:
```javascript
localStorage.setItem('debug', 'legal-ai:*');
```

## Contact

- **DevOps Team**: [DEVOPS-EMAIL]
- **Emergency**: [EMERGENCY-PHONE]
- **Slack**: #legal-ai-deployment