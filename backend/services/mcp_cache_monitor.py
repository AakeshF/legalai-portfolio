"""
MCP Cache Monitoring and Optimization

Monitors cache performance and provides recommendations for optimizing
cache behavior in the MCP integration layer.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import asyncio
import json
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import MCPCacheMetrics
from logger import get_logger
from config import settings

logger = get_logger(__name__)


class CacheEventType(str, Enum):
    HIT = "hit"
    MISS = "miss"
    EVICTION = "eviction"
    STALE = "stale"
    REFRESH = "refresh"


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: int = 300  # 5 minutes default


@dataclass
class CacheStats:
    total_requests: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    stale_hits: int = 0
    current_size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.misses / self.total_requests


@dataclass
class QueryPattern:
    query_type: str
    frequency: int
    cached: bool
    avg_response_time: float
    cache_benefit_score: float = 0.0


@dataclass
class CacheAnalytics:
    hit_rate: float
    miss_patterns: List[QueryPattern]
    stale_incidents: int
    recommendations: List[str]
    total_requests: int
    cache_size_mb: float
    eviction_rate: float


class MCPCacheMonitor:
    """Monitor and optimize MCP cache performance"""
    
    def __init__(self):
        self.cache_events = []
        self.event_buffer_size = 10000
        self.miss_patterns = defaultdict(int)
        self.query_patterns = defaultdict(lambda: {"count": 0, "total_time": 0.0})
        self.cache_stats = defaultdict(CacheStats)
        self._initialized = False
        
    async def initialize(self):
        """Initialize cache monitoring"""
        if self._initialized:
            return
            
        self._initialized = True
        
        # Start background tasks
        asyncio.create_task(self._periodic_analysis())
        asyncio.create_task(self._periodic_cleanup())
        
        logger.info("MCP Cache Monitor initialized")
    
    async def track_cache_event(
        self,
        cache_name: str,
        event_type: CacheEventType,
        key: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track a cache event"""
        event = {
            "cache_name": cache_name,
            "event_type": event_type,
            "key": key,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        self.cache_events.append(event)
        
        # Update stats
        stats = self.cache_stats[cache_name]
        stats.total_requests += 1
        
        if event_type == CacheEventType.HIT:
            stats.hits += 1
        elif event_type == CacheEventType.MISS:
            stats.misses += 1
            self.miss_patterns[key] += 1
        elif event_type == CacheEventType.EVICTION:
            stats.evictions += 1
        elif event_type == CacheEventType.STALE:
            stats.stale_hits += 1
        
        # Maintain buffer size
        if len(self.cache_events) > self.event_buffer_size:
            self.cache_events = self.cache_events[-self.event_buffer_size:]
        
        # Store in database
        await self._store_cache_event(event)
    
    async def _store_cache_event(self, event: Dict[str, Any]):
        """Store cache event in database"""
        async for db in get_db():
            try:
                db_event = MCPCacheMetrics(
                    cache_name=event["cache_name"],
                    event_type=event["event_type"],
                    key=event["key"],
                    timestamp=event["timestamp"],
                    metadata=json.dumps(event["metadata"])
                )
                db.add(db_event)
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error storing cache event: {str(e)}")
                await db.rollback()
    
    async def track_query_pattern(
        self,
        query_type: str,
        response_time: float,
        cached: bool,
        cache_name: str
    ):
        """Track query patterns for cache optimization"""
        pattern = self.query_patterns[query_type]
        pattern["count"] += 1
        pattern["total_time"] += response_time
        pattern["cached"] = cached
        pattern["cache_name"] = cache_name
    
    async def analyze_cache_performance(
        self,
        cache_name: Optional[str] = None,
        timeframe_hours: int = 24
    ) -> CacheAnalytics:
        """Analyze cache performance and generate recommendations"""
        cutoff = datetime.utcnow() - timedelta(hours=timeframe_hours)
        
        async for db in get_db():
            # Calculate hit rate
            hit_rate = await self._calculate_hit_rate(db, cache_name, cutoff)
            
            # Analyze miss patterns
            miss_patterns = await self._analyze_miss_patterns(db, cache_name, cutoff)
            
            # Count stale data incidents
            stale_incidents = await self._count_stale_incidents(db, cache_name, cutoff)
            
            # Get cache size metrics
            cache_size = await self._get_cache_size(db, cache_name)
            
            # Calculate eviction rate
            eviction_rate = await self._calculate_eviction_rate(db, cache_name, cutoff)
            
            # Generate recommendations
            recommendations = await self._generate_cache_recommendations(
                hit_rate, miss_patterns, stale_incidents, eviction_rate
            )
            
            return CacheAnalytics(
                hit_rate=hit_rate,
                miss_patterns=miss_patterns,
                stale_data_incidents=stale_incidents,
                cache_size=cache_size,
                eviction_rate=eviction_rate,
                recommendations=recommendations
            )
    
    async def _calculate_hit_rate(
        self,
        db: AsyncSession,
        cache_name: Optional[str],
        cutoff: datetime
    ) -> float:
        """Calculate cache hit rate"""
        conditions = [MCPCacheMetrics.timestamp > cutoff]
        if cache_name:
            conditions.append(MCPCacheMetrics.cache_name == cache_name)
        
        # Get total requests
        total_result = await db.execute(
            select(func.count(MCPCacheMetrics.id)).where(
                and_(*conditions)
            )
        )
        total_requests = total_result.scalar() or 0
        
        if total_requests == 0:
            return 0.0
        
        # Get hits
        hit_conditions = conditions + [MCPCacheMetrics.event_type == CacheEventType.HIT]
        hit_result = await db.execute(
            select(func.count(MCPCacheMetrics.id)).where(
                and_(*hit_conditions)
            )
        )
        hits = hit_result.scalar() or 0
        
        return hits / total_requests
    
    async def _analyze_miss_patterns(
        self,
        db: AsyncSession,
        cache_name: Optional[str],
        cutoff: datetime
    ) -> List[Dict[str, Any]]:
        """Analyze cache miss patterns"""
        conditions = [
            MCPCacheMetrics.timestamp > cutoff,
            MCPCacheMetrics.event_type == CacheEventType.MISS
        ]
        if cache_name:
            conditions.append(MCPCacheMetrics.cache_name == cache_name)
        
        result = await db.execute(
            select(
                MCPCacheMetrics.key,
                func.count(MCPCacheMetrics.id).label('miss_count')
            ).where(
                and_(*conditions)
            ).group_by(MCPCacheMetrics.key)
            .order_by(func.count(MCPCacheMetrics.id).desc())
            .limit(20)
        )
        
        patterns = []
        for row in result:
            patterns.append({
                "key_pattern": self._extract_pattern(row.key),
                "miss_count": row.miss_count,
                "recommendation": self._get_pattern_recommendation(row.key, row.miss_count)
            })
        
        return patterns
    
    def _extract_pattern(self, key: str) -> str:
        """Extract pattern from cache key"""
        # Simple pattern extraction - can be enhanced
        parts = key.split(":")
        if len(parts) > 1:
            return f"{parts[0]}:*"
        return key
    
    def _get_pattern_recommendation(self, key: str, miss_count: int) -> str:
        """Get recommendation for a miss pattern"""
        if miss_count > 100:
            return f"Consider pre-warming cache for '{key}' pattern"
        elif miss_count > 50:
            return f"Increase TTL for '{key}' pattern to reduce misses"
        else:
            return f"Monitor '{key}' pattern for optimization opportunities"
    
    async def _count_stale_incidents(
        self,
        db: AsyncSession,
        cache_name: Optional[str],
        cutoff: datetime
    ) -> int:
        """Count stale data incidents"""
        conditions = [
            MCPCacheMetrics.timestamp > cutoff,
            MCPCacheMetrics.event_type == CacheEventType.STALE
        ]
        if cache_name:
            conditions.append(MCPCacheMetrics.cache_name == cache_name)
        
        result = await db.execute(
            select(func.count(MCPCacheMetrics.id)).where(
                and_(*conditions)
            )
        )
        
        return result.scalar() or 0
    
    async def _get_cache_size(
        self,
        db: AsyncSession,
        cache_name: Optional[str]
    ) -> int:
        """Get current cache size"""
        # This would need to be tracked separately in a real implementation
        # For now, return estimated size based on unique keys
        conditions = []
        if cache_name:
            conditions.append(MCPCacheMetrics.cache_name == cache_name)
        
        if conditions:
            result = await db.execute(
                select(func.count(func.distinct(MCPCacheMetrics.key))).where(
                    and_(*conditions)
                )
            )
        else:
            result = await db.execute(
                select(func.count(func.distinct(MCPCacheMetrics.key)))
            )
        
        return result.scalar() or 0
    
    async def _calculate_eviction_rate(
        self,
        db: AsyncSession,
        cache_name: Optional[str],
        cutoff: datetime
    ) -> float:
        """Calculate cache eviction rate"""
        conditions = [MCPCacheMetrics.timestamp > cutoff]
        if cache_name:
            conditions.append(MCPCacheMetrics.cache_name == cache_name)
        
        # Get total events
        total_result = await db.execute(
            select(func.count(MCPCacheMetrics.id)).where(
                and_(*conditions)
            )
        )
        total_events = total_result.scalar() or 0
        
        if total_events == 0:
            return 0.0
        
        # Get evictions
        eviction_conditions = conditions + [MCPCacheMetrics.event_type == CacheEventType.EVICTION]
        eviction_result = await db.execute(
            select(func.count(MCPCacheMetrics.id)).where(
                and_(*eviction_conditions)
            )
        )
        evictions = eviction_result.scalar() or 0
        
        return evictions / total_events
    
    async def _generate_cache_recommendations(
        self,
        hit_rate: float,
        miss_patterns: List[Dict[str, Any]],
        stale_incidents: int,
        eviction_rate: float
    ) -> List[str]:
        """Generate cache optimization recommendations"""
        recommendations = []
        
        # Hit rate recommendations
        if hit_rate < 0.7:
            recommendations.append(
                f"Cache hit rate is {hit_rate:.1%}. Consider increasing cache TTL for frequently accessed data"
            )
        
        if hit_rate < 0.5:
            recommendations.append(
                "Very low cache hit rate. Review cache key strategy and consider pre-warming critical data"
            )
        
        # Miss pattern recommendations
        if miss_patterns:
            top_miss = miss_patterns[0]
            if top_miss["miss_count"] > 100:
                recommendations.append(
                    f"Pattern '{top_miss['key_pattern']}' has {top_miss['miss_count']} misses. "
                    f"{top_miss['recommendation']}"
                )
        
        # Stale data recommendations
        if stale_incidents > 50:
            recommendations.append(
                f"High number of stale data incidents ({stale_incidents}). "
                "Consider implementing cache invalidation strategies"
            )
        
        # Eviction rate recommendations
        if eviction_rate > 0.1:
            recommendations.append(
                f"High eviction rate ({eviction_rate:.1%}). Consider increasing cache size"
            )
        
        # Query pattern recommendations
        query_recommendations = await self._analyze_query_patterns()
        recommendations.extend(query_recommendations)
        
        return recommendations
    
    async def _analyze_query_patterns(self) -> List[str]:
        """Analyze query patterns for caching recommendations"""
        recommendations = []
        
        # Convert to list of QueryPattern objects
        patterns = []
        for query_type, data in self.query_patterns.items():
            if data["count"] > 0:
                avg_time = data["total_time"] / data["count"]
                patterns.append(QueryPattern(
                    query_type=query_type,
                    frequency=data["count"],
                    cached=data.get("cached", False),
                    avg_response_time=avg_time,
                    cache_benefit_score=data["count"] * avg_time
                ))
        
        # Sort by cache benefit score
        patterns.sort(key=lambda p: p.cache_benefit_score, reverse=True)
        
        # Generate recommendations for top patterns
        for pattern in patterns[:5]:
            if pattern.frequency > 100 and not pattern.cached:
                recommendations.append(
                    f"Enable caching for '{pattern.query_type}' queries "
                    f"(frequency: {pattern.frequency}, avg time: {pattern.avg_response_time:.2f}s)"
                )
            elif pattern.cached and pattern.avg_response_time > 1.0:
                recommendations.append(
                    f"Optimize cache strategy for '{pattern.query_type}' queries "
                    f"(still taking {pattern.avg_response_time:.2f}s despite caching)"
                )
        
        return recommendations
    
    async def get_cache_health_score(self, cache_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculate overall cache health score"""
        analytics = await self.analyze_cache_performance(cache_name)
        
        # Calculate component scores (0-100)
        hit_rate_score = min(analytics.hit_rate * 100, 100)
        eviction_score = max(100 - (analytics.eviction_rate * 1000), 0)
        stale_score = max(100 - (analytics.stale_data_incidents / 10), 0)
        
        # Calculate overall score
        overall_score = (hit_rate_score + eviction_score + stale_score) / 3
        
        # Determine health status
        if overall_score >= 80:
            status = "healthy"
        elif overall_score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "overall_score": round(overall_score, 1),
            "status": status,
            "components": {
                "hit_rate_score": round(hit_rate_score, 1),
                "eviction_score": round(eviction_score, 1),
                "stale_score": round(stale_score, 1)
            },
            "metrics": {
                "hit_rate": round(analytics.hit_rate, 3),
                "eviction_rate": round(analytics.eviction_rate, 3),
                "stale_incidents": analytics.stale_data_incidents
            }
        }
    
    async def _periodic_analysis(self):
        """Periodically analyze cache performance"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Analyze each cache
                for cache_name in self.cache_stats.keys():
                    analytics = await self.analyze_cache_performance(cache_name, timeframe_hours=1)
                    
                    # Log warnings if needed
                    if analytics.hit_rate < 0.5:
                        logger.warning(f"Low cache hit rate for {cache_name}: {analytics.hit_rate:.1%}")
                    
                    if analytics.eviction_rate > 0.2:
                        logger.warning(f"High eviction rate for {cache_name}: {analytics.eviction_rate:.1%}")
                    
            except Exception as e:
                logger.error(f"Error in periodic cache analysis: {str(e)}")
    
    async def _periodic_cleanup(self):
        """Periodically clean up old cache metrics"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Clean up old events from memory
                cutoff = datetime.utcnow() - timedelta(hours=24)
                self.cache_events = [
                    e for e in self.cache_events
                    if e["timestamp"] > cutoff
                ]
                
                # Clean up old database records
                async for db in get_db():
                    await db.execute(
                        MCPCacheMetrics.__table__.delete().where(
                            MCPCacheMetrics.timestamp < cutoff - timedelta(days=7)
                        )
                    )
                    await db.commit()
                    
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
    
    def get_real_time_stats(self, cache_name: Optional[str] = None) -> Dict[str, Any]:
        """Get real-time cache statistics"""
        if cache_name:
            stats = self.cache_stats.get(cache_name, CacheStats())
            return {
                "cache_name": cache_name,
                "total_requests": stats.total_requests,
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": round(stats.hit_rate, 3),
                "miss_rate": round(stats.miss_rate, 3),
                "evictions": stats.evictions,
                "stale_hits": stats.stale_hits
            }
        else:
            # Aggregate stats
            total_stats = CacheStats()
            for stats in self.cache_stats.values():
                total_stats.total_requests += stats.total_requests
                total_stats.hits += stats.hits
                total_stats.misses += stats.misses
                total_stats.evictions += stats.evictions
                total_stats.stale_hits += stats.stale_hits
            
            return {
                "total_requests": total_stats.total_requests,
                "hits": total_stats.hits,
                "misses": total_stats.misses,
                "hit_rate": round(total_stats.hit_rate, 3),
                "miss_rate": round(total_stats.miss_rate, 3),
                "evictions": total_stats.evictions,
                "stale_hits": total_stats.stale_hits,
                "cache_count": len(self.cache_stats)
            }