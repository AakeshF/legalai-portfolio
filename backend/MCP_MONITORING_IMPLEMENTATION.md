# MCP Monitoring and Analytics Implementation

This document describes the comprehensive monitoring and analytics system implemented for the Model Context Protocol (MCP) integration layer in the Legal AI Backend.

## Overview

The MCP monitoring system provides real-time insights into the health, performance, and reliability of all MCP servers integrated with the legal AI platform. It includes automated alerting, performance analytics, cache optimization, and comprehensive dashboards.

## Architecture Components

### 1. Core Monitoring Service (`services/mcp_monitoring.py`)

The main monitoring service that tracks:
- **Metrics Collection**: Buffered collection of performance metrics with periodic database flushing
- **Health Checking**: Automated health checks every minute for all MCP servers
- **Performance Tracking**: Response time analysis with p50, p95, p99 percentiles
- **Alert Management**: Automated alert generation based on configurable thresholds

Key Features:
- Asynchronous metric collection with buffering for performance
- Historical trend analysis
- Server uptime calculation
- Automatic health status determination (healthy, degraded, unhealthy, error)

### 2. Cache Monitoring (`services/mcp_cache_monitor.py`)

Specialized monitoring for MCP cache performance:
- **Hit/Miss Rate Tracking**: Real-time cache effectiveness metrics
- **Pattern Analysis**: Identifies frequently missed queries for optimization
- **Stale Data Detection**: Tracks and alerts on stale cache entries
- **Eviction Monitoring**: Monitors cache eviction rates to optimize size

Key Metrics:
- Cache hit rate with recommendations when below 70%
- Miss pattern analysis for query optimization
- Cache size and eviction rate monitoring
- Automated cache health scoring

### 3. Alert Manager (`services/mcp_alert_manager.py`)

Automated alert system with configurable rules:
- **High Error Rate Rule**: Alerts when error rate exceeds 10%
- **Slow Response Rule**: Alerts for responses over 5 seconds
- **Server Down Rule**: Critical alerts for unresponsive servers
- **Cache Performance Rule**: Alerts for low cache hit rates

Alert Features:
- Severity levels (low, medium, high, critical)
- Auto-resolution for transient issues
- Email notifications for critical alerts
- Recommended actions for each alert type

### 4. API Endpoints (`mcp_monitoring_routes.py`)

RESTful API for monitoring access:

#### Health Endpoints
- `GET /api/mcp/health` - Current health status of all MCP servers
- `GET /api/mcp/health` - Returns:
  ```json
  {
    "summary": {
      "total_servers": 5,
      "healthy_servers": 4,
      "degraded_servers": 1,
      "overall_health": "degraded"
    },
    "servers": {
      "court_system": {
        "status": "healthy",
        "response_time": 0.234,
        "uptime_percentage": 99.8
      }
    }
  }
  ```

#### Analytics Endpoints
- `GET /api/mcp/analytics?timeframe=24h` - Performance analytics dashboard
- Returns server performance, action metrics, error analysis, and optimization suggestions

#### Alert Endpoints
- `GET /api/mcp/alerts` - Active alerts grouped by severity
- `POST /api/mcp/alerts/{alert_id}/resolve` - Manually resolve an alert

#### Cache Analytics
- `GET /api/mcp/cache/analytics` - Cache performance metrics
- `GET /api/mcp/cache/health` - Overall cache health score
- `GET /api/mcp/cache/stats` - Real-time cache statistics

#### Management Endpoints
- `POST /api/mcp/servers/{server_id}/restart` - Restart a specific MCP server
- `GET /api/mcp/performance/summary` - High-level performance overview
- `GET /api/mcp/metrics/export` - Export metrics in JSON or CSV format

## Database Schema

### MCPMetrics Table
```sql
CREATE TABLE mcp_metrics (
    id VARCHAR PRIMARY KEY,
    server_name VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    duration FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    error VARCHAR,
    timestamp TIMESTAMP NOT NULL,
    metadata JSON
);
```

### MCPHealthStatus Table
```sql
CREATE TABLE mcp_health_status (
    id VARCHAR PRIMARY KEY,
    server_name VARCHAR UNIQUE NOT NULL,
    status VARCHAR NOT NULL,
    response_time FLOAT,
    last_check TIMESTAMP NOT NULL,
    error VARCHAR,
    metadata JSON
);
```

### MCPAlert Table
```sql
CREATE TABLE mcp_alerts (
    id VARCHAR PRIMARY KEY,
    severity VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    server_name VARCHAR,
    message TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP
);
```

### MCPCacheMetrics Table
```sql
CREATE TABLE mcp_cache_metrics (
    id VARCHAR PRIMARY KEY,
    cache_name VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    key VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metadata JSON
);
```

## Key Features

### 1. Real-Time Monitoring
- Continuous health checks every 60 seconds
- Immediate alert generation for critical issues
- Live performance metrics with minimal latency

### 2. Historical Analysis
- Configurable timeframes (1h, 24h, 7d)
- Trend analysis for performance optimization
- Pattern recognition for predictive maintenance

### 3. Automated Optimization
- Cache strategy recommendations based on usage patterns
- Query optimization suggestions for slow operations
- Resource allocation recommendations

### 4. Integration Points
- Email notifications for critical alerts
- CSV/JSON export for external monitoring tools
- Grafana/Prometheus compatible metrics format

## Usage Examples

### Check MCP Health
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/mcp/health
```

### Get Performance Analytics
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/mcp/analytics?timeframe=24h"
```

### Export Metrics
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/mcp/metrics/export?format=csv&timeframe=7d" \
  -o mcp_metrics.csv
```

## Configuration

### Alert Thresholds
- Error Rate: 10% triggers high severity alert
- Response Time: >5s medium, >10s high severity
- Cache Hit Rate: <60% triggers medium severity alert
- Server Downtime: >5 minutes triggers critical alert

### Email Notifications
Configure in environment variables:
```env
ALERT_EMAIL_RECIPIENTS=[ADMIN-EMAIL],[OPS-EMAIL]
EMAIL_ENABLED=true
```

## Monitoring Dashboard

The monitoring system provides a comprehensive dashboard with:
1. **Server Health Overview**: Visual status of all MCP servers
2. **Performance Metrics**: Response times, throughput, error rates
3. **Cache Analytics**: Hit rates, miss patterns, optimization suggestions
4. **Alert Center**: Active alerts with recommended actions
5. **Historical Trends**: Performance over time with anomaly detection

## Best Practices

1. **Regular Review**: Check optimization suggestions weekly
2. **Alert Response**: Address critical alerts within 15 minutes
3. **Cache Tuning**: Adjust TTL based on miss pattern analysis
4. **Capacity Planning**: Use metrics export for trend analysis

## Migration

Run the migration to create monitoring tables:
```bash
python migrate_db.py
# or specifically:
python migrations/add_mcp_monitoring_tables.py
```

## Future Enhancements

1. **Machine Learning**: Predictive alerting based on historical patterns
2. **Auto-Scaling**: Automatic resource adjustment based on load
3. **Advanced Analytics**: Correlation analysis between different metrics
4. **Custom Dashboards**: User-configurable monitoring views
5. **Mobile Alerts**: Push notifications for critical issues