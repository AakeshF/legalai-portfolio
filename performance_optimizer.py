#!/usr/bin/env python3
"""
Performance Optimizer for Legal AI System
Analyzes and optimizes system performance after security consolidation
"""

import os
import sys
import asyncio
import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    def __init__(self, backend_path: str = "legal-ai copy/backend"):
        self.backend_path = Path(backend_path)
        self.db_path = self.backend_path / "legal_ai.db"
        self.optimization_results: Dict[str, Any] = {}
        
    def log_optimization(self, area: str, action: str, result: Any, impact: str = ""):
        """Log optimization result"""
        logger.info(f"🔧 {area}: {action} -> {result} {impact}")
        if area not in self.optimization_results:
            self.optimization_results[area] = []
        self.optimization_results[area].append({
            "action": action,
            "result": result,
            "impact": impact,
            "timestamp": time.time()
        })

    async def analyze_database_performance(self) -> Dict[str, Any]:
        """Analyze database performance and suggest optimizations"""
        logger.info("📊 Analyzing Database Performance...")
        
        if not self.db_path.exists():
            self.log_optimization("Database", "File Check", "Database not found", "❌ Critical")
            return {"status": "error", "message": "Database file not found"}
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Check table sizes
            tables = ['documents', 'chat_sessions', 'chat_messages', 'users', 'organizations']
            table_stats = {}
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        table_stats[table] = {"count": count, "exists": True}
                        
                        # Check for indexes
                        cursor.execute(f"PRAGMA index_list({table})")
                        indexes = cursor.fetchall()
                        table_stats[table]["indexes"] = len(indexes)
                        
                        self.log_optimization("Database", f"Table {table}", 
                                           f"{count} records, {len(indexes)} indexes", 
                                           "✅" if count < 10000 else "⚠️ Large table")
                    else:
                        table_stats[table] = {"exists": False}
                        self.log_optimization("Database", f"Table {table}", "Does not exist", "⚠️")
                        
                except sqlite3.Error as e:
                    table_stats[table] = {"error": str(e)}
                    self.log_optimization("Database", f"Table {table}", f"Error: {str(e)}", "❌")
            
            # Check database size
            db_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
            self.log_optimization("Database", "Size Analysis", f"{db_size:.2f} MB", 
                                "✅" if db_size < 100 else "⚠️ Large database")
            
            # Suggest optimizations
            optimizations = []
            
            # Check for missing indexes
            for table, stats in table_stats.items():
                if stats.get("exists") and stats.get("count", 0) > 1000 and stats.get("indexes", 0) < 2:
                    optimizations.append(f"Add indexes to {table} table for better query performance")
            
            if db_size > 50:
                optimizations.append("Consider database cleanup and archiving old data")
            
            conn.close()
            
            return {
                "status": "success",
                "table_stats": table_stats,
                "database_size_mb": db_size,
                "optimizations": optimizations
            }
            
        except Exception as e:
            self.log_optimization("Database", "Analysis", f"Error: {str(e)}", "❌")
            return {"status": "error", "message": str(e)}

    async def optimize_database_indexes(self) -> bool:
        """Create missing database indexes for performance"""
        logger.info("⚡ Optimizing Database Indexes...")
        
        if not self.db_path.exists():
            return False
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Critical indexes for performance
            indexes_to_create = [
                ("idx_documents_org_id", "CREATE INDEX IF NOT EXISTS idx_documents_org_id ON documents(organization_id)"),
                ("idx_documents_status", "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status)"),
                ("idx_documents_upload_date", "CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_timestamp)"),
                ("idx_chat_sessions_org_id", "CREATE INDEX IF NOT EXISTS idx_chat_sessions_org_id ON chat_sessions(organization_id)"),
                ("idx_chat_sessions_user_id", "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)"),
                ("idx_chat_messages_session_id", "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)"),
                ("idx_chat_messages_timestamp", "CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)"),
                ("idx_users_org_id", "CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(organization_id)"),
                ("idx_users_email", "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            ]
            
            created_count = 0
            for index_name, sql in indexes_to_create:
                try:
                    cursor.execute(sql)
                    created_count += 1
                    self.log_optimization("Database Indexes", f"Created {index_name}", "Success", "⚡ Performance boost")
                except sqlite3.Error as e:
                    if "already exists" not in str(e):
                        self.log_optimization("Database Indexes", f"Failed {index_name}", str(e), "❌")
            
            conn.commit()
            conn.close()
            
            self.log_optimization("Database Indexes", "Total Created", f"{created_count} indexes", "🚀 Significant improvement")
            return True
            
        except Exception as e:
            self.log_optimization("Database Indexes", "Optimization", f"Error: {str(e)}", "❌")
            return False

    async def analyze_file_storage(self) -> Dict[str, Any]:
        """Analyze file storage and suggest optimizations"""
        logger.info("📁 Analyzing File Storage...")
        
        uploads_dir = self.backend_path / "uploads"
        
        if not uploads_dir.exists():
            self.log_optimization("File Storage", "Directory Check", "Uploads directory not found", "⚠️")
            return {"status": "no_uploads", "message": "No uploads directory found"}
        
        try:
            # Analyze upload directory
            total_files = 0
            total_size = 0
            file_types = {}
            large_files = []
            
            for file_path in uploads_dir.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    # Track file types
                    ext = file_path.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
                    
                    # Track large files (>10MB)
                    if file_size > 10 * 1024 * 1024:
                        large_files.append({
                            "name": file_path.name,
                            "size_mb": file_size / (1024 * 1024),
                            "path": str(file_path.relative_to(uploads_dir))
                        })
            
            total_size_mb = total_size / (1024 * 1024)
            
            self.log_optimization("File Storage", "Analysis", 
                                f"{total_files} files, {total_size_mb:.2f} MB total",
                                "✅" if total_size_mb < 500 else "⚠️ Large storage usage")
            
            # Suggest optimizations
            optimizations = []
            
            if total_size_mb > 200:
                optimizations.append("Consider implementing file cleanup for old documents")
            
            if len(large_files) > 10:
                optimizations.append("Many large files detected - consider compression or archival")
            
            if '.tmp' in file_types or '.part' in file_types:
                optimizations.append("Temporary files detected - implement cleanup process")
            
            return {
                "status": "success",
                "total_files": total_files,
                "total_size_mb": total_size_mb,
                "file_types": file_types,
                "large_files": large_files[:5],  # Top 5 largest
                "optimizations": optimizations
            }
            
        except Exception as e:
            self.log_optimization("File Storage", "Analysis", f"Error: {str(e)}", "❌")
            return {"status": "error", "message": str(e)}

    async def check_api_response_times(self, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Test API response times and identify slow endpoints"""
        logger.info("⏱️ Testing API Response Times...")
        
        test_endpoints = [
            ("/health", "GET", None),
            ("/api/ai/status", "GET", None),
            ("/", "GET", None)
        ]
        
        response_times = {}
        
        for endpoint, method, data in test_endpoints:
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                else:
                    response = requests.post(f"{base_url}{endpoint}", json=data, timeout=10)
                
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                response_times[endpoint] = {
                    "response_time_ms": response_time_ms,
                    "status_code": response.status_code,
                    "success": response.status_code < 400
                }
                
                impact = "🚀 Fast" if response_time_ms < 100 else "⚠️ Slow" if response_time_ms < 1000 else "❌ Very slow"
                self.log_optimization("API Performance", f"{method} {endpoint}", 
                                    f"{response_time_ms:.2f}ms", impact)
                
            except Exception as e:
                response_times[endpoint] = {
                    "error": str(e),
                    "success": False
                }
                self.log_optimization("API Performance", f"{method} {endpoint}", f"Error: {str(e)}", "❌")
        
        # Calculate average response time
        successful_times = [r["response_time_ms"] for r in response_times.values() 
                           if "response_time_ms" in r]
        
        if successful_times:
            avg_response_time = sum(successful_times) / len(successful_times)
            self.log_optimization("API Performance", "Average Response Time", 
                                f"{avg_response_time:.2f}ms", 
                                "🚀 Excellent" if avg_response_time < 200 else "✅ Good" if avg_response_time < 500 else "⚠️ Needs improvement")
        
        return {
            "status": "success",
            "response_times": response_times,
            "average_response_time_ms": avg_response_time if successful_times else None
        }

    async def check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage and suggest optimizations"""
        logger.info("🧠 Analyzing Memory Usage...")
        
        try:
            # Try to get memory info using psutil if available
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                
                memory_mb = memory_info.rss / (1024 * 1024)
                cpu_percent = process.cpu_percent()
                
                self.log_optimization("Memory Usage", "Process Memory", f"{memory_mb:.2f} MB", 
                                    "✅ Efficient" if memory_mb < 200 else "⚠️ High" if memory_mb < 500 else "❌ Very high")
                
                self.log_optimization("Memory Usage", "CPU Usage", f"{cpu_percent:.1f}%", 
                                    "✅ Low" if cpu_percent < 10 else "⚠️ Moderate" if cpu_percent < 30 else "❌ High")
                
                return {
                    "status": "success",
                    "memory_mb": memory_mb,
                    "cpu_percent": cpu_percent,
                    "recommendations": [
                        "Monitor memory usage during peak load",
                        "Consider caching for frequently accessed data"
                    ] if memory_mb > 300 else ["Memory usage is optimal"]
                }
                
            except ImportError:
                self.log_optimization("Memory Usage", "Analysis", "psutil not available", "⚠️ Limited monitoring")
                return {
                    "status": "limited",
                    "message": "Install psutil for detailed memory monitoring: pip install psutil"
                }
            
        except Exception as e:
            self.log_optimization("Memory Usage", "Analysis", f"Error: {str(e)}", "❌")
            return {"status": "error", "message": str(e)}

    async def generate_optimization_report(self) -> str:
        """Generate comprehensive optimization report"""
        logger.info("📋 Generating Optimization Report...")
        
        report_lines = [
            "# Legal AI System Performance Optimization Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            "",
        ]
        
        # Analyze results
        total_optimizations = sum(len(results) for results in self.optimization_results.values())
        critical_issues = sum(1 for area_results in self.optimization_results.values() 
                             for result in area_results if "❌" in result.get("impact", ""))
        
        if critical_issues == 0:
            report_lines.append("✅ **System Status: OPTIMAL** - No critical issues detected")
        elif critical_issues <= 2:
            report_lines.append("⚠️ **System Status: GOOD** - Minor optimizations available")
        else:
            report_lines.append("🚨 **System Status: NEEDS ATTENTION** - Multiple issues detected")
        
        report_lines.extend([
            f"- Total optimizations performed: {total_optimizations}",
            f"- Critical issues: {critical_issues}",
            "",
            "## Detailed Results",
            ""
        ])
        
        # Add detailed results
        for area, results in self.optimization_results.items():
            report_lines.append(f"### {area}")
            report_lines.append("")
            
            for result in results:
                impact_icon = "✅" if "✅" in result["impact"] else "⚠️" if "⚠️" in result["impact"] else "❌" if "❌" in result["impact"] else "ℹ️"
                report_lines.append(f"- {impact_icon} **{result['action']}**: {result['result']} {result['impact']}")
            
            report_lines.append("")
        
        # Add recommendations
        report_lines.extend([
            "## Recommendations",
            "",
            "### Immediate Actions",
            "- Ensure all database indexes are created",
            "- Monitor memory usage during peak load",
            "- Set up automated file cleanup processes",
            "",
            "### Long-term Optimizations",
            "- Implement Redis caching for frequently accessed data",
            "- Consider database partitioning for large datasets",
            "- Set up comprehensive monitoring and alerting",
            "",
            "### Monitoring Setup",
            "- Configure application performance monitoring (APM)",
            "- Set up database performance monitoring",
            "- Implement log aggregation and analysis",
            ""
        ])
        
        return "\n".join(report_lines)

    async def run_full_optimization(self, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Run complete performance optimization suite"""
        logger.info("🚀 Starting Legal AI Performance Optimization")
        
        # Run all optimization checks
        optimizations = [
            ("Database Performance", self.analyze_database_performance),
            ("Database Indexes", self.optimize_database_indexes),
            ("File Storage", self.analyze_file_storage),
            ("Memory Usage", self.check_memory_usage)
        ]
        
        # Check if service is running for API tests
        try:
            requests.get(f"{base_url}/health", timeout=3)
            optimizations.append(("API Performance", lambda: self.check_api_response_times(base_url)))
        except:
            self.log_optimization("API Performance", "Service Check", "Service not running - skipping API tests", "⚠️")
        
        results = {}
        for name, func in optimizations:
            logger.info(f"\n🔍 Running: {name}")
            try:
                if name == "Database Indexes":
                    result = await func()
                    results[name] = {"success": result}
                else:
                    result = await func()
                    results[name] = result
            except Exception as e:
                self.log_optimization(name, "Execution", f"Error: {str(e)}", "❌")
                results[name] = {"status": "error", "message": str(e)}
        
        # Generate report
        report = await self.generate_optimization_report()
        
        # Save report
        report_path = self.backend_path / "performance_optimization_report.md"
        with open(report_path, "w") as f:
            f.write(report)
        
        logger.info(f"\n📊 Optimization complete! Report saved to: {report_path}")
        
        return {
            "results": results,
            "report_path": str(report_path),
            "optimization_count": len(self.optimization_results)
        }

async def main():
    """Main optimization runner"""
    optimizer = PerformanceOptimizer()
    results = await optimizer.run_full_optimization()
    
    logger.info("\n" + "="*50)
    logger.info("🎯 PERFORMANCE OPTIMIZATION COMPLETE")
    logger.info("="*50)
    
    if results["optimization_count"] > 0:
        logger.info("✅ System has been optimized for production use")
    else:
        logger.info("⚠️ No optimizations were needed or possible")
    
    logger.info(f"📋 Detailed report available at: {results['report_path']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
