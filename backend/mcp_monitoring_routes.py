"""
MCP Monitoring API Routes

Provides endpoints for monitoring MCP server health, performance analytics,
and cache optimization insights.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from auth_middleware import get_current_user
from models import User
from services.mcp_monitoring import MCPMonitoringService
from services.mcp_cache_monitor import MCPCacheMonitor
from services.mcp_manager_enhanced import EnhancedMCPManager
from logger import get_logger

# from schemas import StandardResponse  # Not needed, will use dict response

logger = get_logger(__name__)

# Initialize services
mcp_monitor = MCPMonitoringService()
cache_monitor = MCPCacheMonitor()
mcp_manager = None  # Will be set by main app

router = APIRouter(prefix="/api/mcp", tags=["MCP Monitoring"])


def set_mcp_manager(manager: EnhancedMCPManager):
    """Set the MCP manager instance"""
    global mcp_manager
    mcp_manager = manager

    # Initialize monitoring with MCP servers
    asyncio.create_task(mcp_monitor.initialize(manager.servers))
    asyncio.create_task(cache_monitor.initialize())


@router.get("/health")
async def get_mcp_health(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current health status of all MCP servers

    Returns detailed health information including:
    - Server status (healthy, degraded, unhealthy, error)
    - Response times
    - Uptime percentages
    - Capabilities and versions
    """
    try:
        health_status = await mcp_monitor.check_all_servers()

        # Convert to dict format
        health_dict = {
            server_name: health.to_dict()
            for server_name, health in health_status.items()
        }

        # Calculate summary
        total_servers = len(health_dict)
        healthy_servers = sum(
            1 for h in health_dict.values() if h["status"] == "healthy"
        )

        return StandardResponse(
            success=True,
            data={
                "summary": {
                    "total_servers": total_servers,
                    "healthy_servers": healthy_servers,
                    "degraded_servers": sum(
                        1 for h in health_dict.values() if h["status"] == "degraded"
                    ),
                    "unhealthy_servers": sum(
                        1
                        for h in health_dict.values()
                        if h["status"] in ["unhealthy", "error"]
                    ),
                    "overall_health": (
                        "healthy" if healthy_servers == total_servers else "degraded"
                    ),
                },
                "servers": health_dict,
                "last_check": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Error getting MCP health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_mcp_analytics(
    timeframe: str = Query(
        "24h", description="Timeframe for analytics (e.g., 1h, 24h, 7d)"
    ),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get MCP performance analytics

    Provides comprehensive analytics including:
    - Server performance metrics
    - Action-specific metrics
    - Error analysis
    - Usage patterns
    - Optimization suggestions
    """
    try:
        analytics = await mcp_monitor.get_analytics_dashboard(timeframe)

        return StandardResponse(success=True, data=analytics)

    except Exception as e:
        logger.error(f"Error getting MCP analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_mcp_alerts(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get active MCP-related alerts

    Returns all unresolved alerts including:
    - Slow response alerts
    - Error alerts
    - High error rate alerts
    - Cache performance alerts
    """
    try:
        alerts = await mcp_monitor.get_active_alerts()

        # Group by severity
        alerts_by_severity = {"critical": [], "high": [], "medium": [], "low": []}

        for alert in alerts:
            severity = alert.get("severity", "medium")
            alerts_by_severity[severity].append(alert)

        return StandardResponse(
            success=True,
            data={
                "total_alerts": len(alerts),
                "alerts_by_severity": alerts_by_severity,
                "alerts": alerts,
            },
        )

    except Exception as e:
        logger.error(f"Error getting MCP alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_mcp_alert(
    alert_id: int, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resolve a specific MCP alert"""
    try:
        await mcp_monitor.resolve_alert(alert_id)

        return StandardResponse(
            success=True, message=f"Alert {alert_id} resolved successfully"
        )

    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{server_id}/restart")
async def restart_mcp_server(
    server_id: str, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Restart a specific MCP server

    This will:
    1. Gracefully stop the server
    2. Clear any cached connections
    3. Restart with fresh configuration
    """
    try:
        if not mcp_manager:
            raise HTTPException(status_code=500, detail="MCP manager not initialized")

        # Stop the server
        await mcp_manager.stop_server(server_id)

        # Wait a moment
        await asyncio.sleep(1)

        # Start the server again
        await mcp_manager.start_server(server_id)

        # Check health
        health = await mcp_monitor.check_all_servers()
        server_health = health.get(server_id)

        return StandardResponse(
            success=True,
            message=f"Server {server_id} restarted successfully",
            data={
                "server_id": server_id,
                "health": server_health.to_dict() if server_health else None,
            },
        )

    except Exception as e:
        logger.error(f"Error restarting server {server_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/analytics")
async def get_cache_analytics(
    cache_name: Optional[str] = Query(None, description="Specific cache to analyze"),
    timeframe_hours: int = Query(24, description="Timeframe in hours"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get cache performance analytics

    Provides insights into:
    - Hit/miss rates
    - Miss patterns
    - Stale data incidents
    - Cache size and eviction rates
    - Optimization recommendations
    """
    try:
        analytics = await cache_monitor.analyze_cache_performance(
            cache_name=cache_name, timeframe_hours=timeframe_hours
        )

        return StandardResponse(success=True, data=analytics.to_dict())

    except Exception as e:
        logger.error(f"Error getting cache analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/health")
async def get_cache_health(
    cache_name: Optional[str] = Query(None, description="Specific cache to check"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get cache health score

    Returns overall health score and component scores for:
    - Hit rate
    - Eviction rate
    - Stale data handling
    """
    try:
        health_score = await cache_monitor.get_cache_health_score(cache_name)

        return StandardResponse(success=True, data=health_score)

    except Exception as e:
        logger.error(f"Error getting cache health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats(
    cache_name: Optional[str] = Query(None, description="Specific cache to check"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get real-time cache statistics"""
    try:
        stats = cache_monitor.get_real_time_stats(cache_name)

        return StandardResponse(success=True, data=stats)

    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/summary")
async def get_performance_summary(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get overall MCP performance summary

    Provides a high-level overview of:
    - Server health status
    - Performance metrics
    - Cache effectiveness
    - Active issues
    """
    try:
        # Get health status
        health_status = await mcp_monitor.check_all_servers()

        # Get recent analytics
        analytics = await mcp_monitor.get_analytics_dashboard("1h")

        # Get cache health
        cache_health = await cache_monitor.get_cache_health_score()

        # Get active alerts
        alerts = await mcp_monitor.get_active_alerts()

        # Calculate summary metrics
        total_servers = len(health_status)
        healthy_servers = sum(
            1 for h in health_status.values() if h.status == "healthy"
        )

        avg_response_time = 0.0
        total_requests = 0
        total_errors = 0

        for server, perf in analytics.get("server_performance", {}).items():
            avg_response_time += perf.get("avg_response_time", 0) * perf.get(
                "total_requests", 0
            )
            total_requests += perf.get("total_requests", 0)
            total_errors += int(
                perf.get("error_rate", 0) * perf.get("total_requests", 0) / 100
            )

        if total_requests > 0:
            avg_response_time /= total_requests

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "health": {
                "overall_status": (
                    "healthy" if healthy_servers == total_servers else "degraded"
                ),
                "healthy_servers": healthy_servers,
                "total_servers": total_servers,
                "health_percentage": (
                    (healthy_servers / total_servers * 100) if total_servers > 0 else 0
                ),
            },
            "performance": {
                "avg_response_time": round(avg_response_time, 3),
                "total_requests_last_hour": total_requests,
                "error_rate": round(
                    (total_errors / total_requests * 100) if total_requests > 0 else 0,
                    2,
                ),
                "cache_health_score": cache_health.get("overall_score", 0),
            },
            "alerts": {
                "total": len(alerts),
                "critical": sum(1 for a in alerts if a.get("severity") == "critical"),
                "high": sum(1 for a in alerts if a.get("severity") == "high"),
                "medium": sum(1 for a in alerts if a.get("severity") == "medium"),
                "low": sum(1 for a in alerts if a.get("severity") == "low"),
            },
            "top_issues": analytics.get("optimization_suggestions", [])[:3],
        }

        return StandardResponse(success=True, data=summary)

    except Exception as e:
        logger.error(f"Error getting performance summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/export")
async def export_metrics(
    timeframe: str = Query("24h", description="Timeframe for export"),
    format: str = Query("json", description="Export format (json, csv)"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Export MCP metrics for external analysis

    Supports JSON and CSV formats for integration with
    monitoring tools like Grafana, Prometheus, etc.
    """
    try:
        analytics = await mcp_monitor.get_analytics_dashboard(timeframe)

        if format == "csv":
            # Convert to CSV format
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write server performance
            writer.writerow(["Server Performance"])
            writer.writerow(
                [
                    "Server",
                    "Total Requests",
                    "Avg Response Time",
                    "Success Rate",
                    "Error Rate",
                ]
            )

            for server, perf in analytics.get("server_performance", {}).items():
                writer.writerow(
                    [
                        server,
                        perf.get("total_requests", 0),
                        perf.get("avg_response_time", 0),
                        perf.get("success_rate", 0),
                        perf.get("error_rate", 0),
                    ]
                )

            content = output.getvalue()

            return JSONResponse(
                content=content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=mcp_metrics_{timeframe}.csv"
                },
            )
        else:
            # Default to JSON
            return StandardResponse(success=True, data=analytics)

    except Exception as e:
        logger.error(f"Error exporting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Import asyncio for async operations
import asyncio
