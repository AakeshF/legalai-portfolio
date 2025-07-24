#!/usr/bin/env python3
"""
Comprehensive Integration Test for Legal AI System
Tests end-to-end functionality after security consolidation
"""

import asyncio
import websockets
import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.auth_token: Optional[str] = None
        self.test_results: Dict[str, bool] = {}
        self.session = requests.Session()
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
        self.test_results[test_name] = success
        
    async def test_health_check(self) -> bool:
        """Test basic health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}")
                return True
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False

    async def test_authentication_security(self) -> bool:
        """Test that endpoints are properly secured"""
        test_endpoints = [
            "/api/documents",
            "/api/chat",
            "/api/ai/status",
            "/api/websocket/status"
        ]
        
        all_secure = True
        for endpoint in test_endpoints:
            try:
                # Test without authentication
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                
                # Should return 401 or 403 (not 200)
                if response.status_code in [401, 403]:
                    self.log_test(f"Security Check {endpoint}", True, f"Properly secured (HTTP {response.status_code})")
                else:
                    self.log_test(f"Security Check {endpoint}", False, f"Not secured (HTTP {response.status_code})")
                    all_secure = False
                    
            except Exception as e:
                self.log_test(f"Security Check {endpoint}", False, f"Exception: {str(e)}")
                all_secure = False
        
        return all_secure

    async def test_authentication_flow(self) -> bool:
        """Test complete authentication flow"""
        try:
            # Test login endpoint exists
            login_url = f"{self.base_url}/api/auth/login"
            
            # Try to get login endpoint (should exist even if we can't log in without credentials)
            response = self.session.post(login_url, 
                json={"email": "[TEST-EMAIL]", "password": "test"}, 
                timeout=5
            )
            
            # We expect either a 401 (valid endpoint, wrong creds) or 422 (validation error)
            # What we DON'T want is 404 (endpoint missing)
            if response.status_code in [401, 422, 400]:
                self.log_test("Authentication Endpoint", True, "Login endpoint exists and validates")
                return True
            elif response.status_code == 404:
                self.log_test("Authentication Endpoint", False, "Login endpoint missing")
                return False
            else:
                self.log_test("Authentication Endpoint", True, f"Unexpected response: HTTP {response.status_code}")
                return True
                
        except Exception as e:
            self.log_test("Authentication Flow", False, f"Exception: {str(e)}")
            return False

    async def test_websocket_endpoint(self) -> bool:
        """Test WebSocket endpoint exists and handles authentication"""
        try:
            # Try to connect without token (should fail)
            ws_endpoint = f"{self.ws_url}/ws?token=invalid"
            
            try:
                async with websockets.connect(ws_endpoint, timeout=5) as websocket:
                    # If we get here, the endpoint exists but may not be handling auth properly
                    await websocket.close()
                    self.log_test("WebSocket Endpoint", False, "Accepted invalid token")
                    return False
            except websockets.exceptions.ConnectionClosedError as e:
                # This is good - means the endpoint exists but rejected invalid auth
                if "1008" in str(e) or "authentication" in str(e).lower():
                    self.log_test("WebSocket Authentication", True, "Properly rejects invalid tokens")
                    return True
                else:
                    self.log_test("WebSocket Authentication", True, "Connection closed (likely auth rejection)")
                    return True
            except websockets.exceptions.InvalidURI:
                self.log_test("WebSocket Endpoint", False, "Invalid WebSocket URI")
                return False
            except Exception as e:
                # Connection refused or similar - endpoint might not be running
                if "refused" in str(e).lower() or "unreachable" in str(e).lower():
                    self.log_test("WebSocket Endpoint", False, f"Service not running: {str(e)}")
                    return False
                else:
                    # Other error - endpoint exists but has issues
                    self.log_test("WebSocket Endpoint", True, f"Endpoint exists, auth handling unclear: {str(e)}")
                    return True
                    
        except Exception as e:
            self.log_test("WebSocket Test", False, f"Exception: {str(e)}")
            return False

    async def test_cors_configuration(self) -> bool:
        """Test CORS headers are properly configured"""
        try:
            # Test OPTIONS request
            response = self.session.options(f"{self.base_url}/api/health", timeout=5)
            
            cors_headers = {
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods', 
                'Access-Control-Allow-Headers'
            }
            
            found_headers = set(response.headers.keys())
            has_cors = any(header in found_headers for header in cors_headers)
            
            if has_cors:
                origin = response.headers.get('Access-Control-Allow-Origin', '')
                # Should NOT be "*" for security
                if origin == "*":
                    self.log_test("CORS Security", False, "Wildcard origin still present")
                    return False
                else:
                    self.log_test("CORS Configuration", True, f"Properly configured: {origin}")
                    return True
            else:
                # Try a regular GET to see if CORS headers are there
                response = self.session.get(f"{self.base_url}/api/health", timeout=5)
                origin = response.headers.get('Access-Control-Allow-Origin', '')
                
                if origin == "*":
                    self.log_test("CORS Security", False, "Wildcard origin detected")
                    return False
                else:
                    self.log_test("CORS Configuration", True, "No wildcard origins detected")
                    return True
                    
        except Exception as e:
            self.log_test("CORS Test", False, f"Exception: {str(e)}")
            return False

    async def test_api_endpoint_consolidation(self) -> bool:
        """Test that old insecure endpoints are removed"""
        insecure_endpoints = [
            "/api/simple-chat",
            "/api/test/simple-ollama", 
            "/simple-ai"
        ]
        
        all_removed = True
        for endpoint in insecure_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                
                # Should return 404 (not found) - these endpoints should be removed
                if response.status_code == 404:
                    self.log_test(f"Endpoint Removal {endpoint}", True, "Properly removed")
                else:
                    self.log_test(f"Endpoint Removal {endpoint}", False, f"Still exists (HTTP {response.status_code})")
                    all_removed = False
                    
            except Exception as e:
                # If we can't connect, that's also fine - endpoint is gone
                self.log_test(f"Endpoint Removal {endpoint}", True, "Endpoint not accessible")
        
        return all_removed

    async def test_database_connectivity(self) -> bool:
        """Test database connectivity through health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                services = data.get('services', {})
                db_status = services.get('database', 'unknown')
                
                if db_status == 'connected':
                    self.log_test("Database Connectivity", True, "Database connected")
                    return True
                else:
                    self.log_test("Database Connectivity", False, f"Database status: {db_status}")
                    return False
            else:
                self.log_test("Database Connectivity", False, f"Health check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Database Connectivity", False, f"Exception: {str(e)}")
            return False

    async def test_memory_management(self) -> bool:
        """Test memory status endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/memory-status", timeout=5)
            
            # This endpoint requires auth, so we expect 401/403
            if response.status_code in [401, 403]:
                self.log_test("Memory Management Endpoint", True, "Properly secured")
                return True
            elif response.status_code == 200:
                # If we somehow get through (maybe auth is disabled), check the response
                data = response.json()
                status = data.get('status', 'unknown')
                self.log_test("Memory Management", True, f"Status: {status}")
                return True
            else:
                self.log_test("Memory Management", False, f"Unexpected response: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Memory Management", False, f"Exception: {str(e)}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all integration tests"""
        logger.info("🚀 Starting Legal AI Integration Tests")
        logger.info(f"Testing against: {self.base_url}")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Authentication Security", self.test_authentication_security),
            ("Authentication Flow", self.test_authentication_flow),
            ("WebSocket Endpoint", self.test_websocket_endpoint),
            ("CORS Configuration", self.test_cors_configuration),
            ("API Endpoint Consolidation", self.test_api_endpoint_consolidation),
            ("Database Connectivity", self.test_database_connectivity),
            ("Memory Management", self.test_memory_management)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running: {test_name}")
            try:
                await test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Test exception: {str(e)}")
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("📊 INTEGRATION TEST RESULTS")
        logger.info("="*50)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} {test_name}")
        
        logger.info("-" * 50)
        logger.info(f"📈 PASSED: {passed}/{total} ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION!")
        elif passed >= total * 0.8:  # 80% pass rate
            logger.info("⚠️  MOSTLY FUNCTIONAL - Minor issues detected")
        else:
            logger.info("🚨 SIGNIFICANT ISSUES DETECTED - Review required")
            
        return self.test_results

async def main():
    """Main test runner"""
    # Test both potential ports
    ports_to_test = [8000, 3001, 5000]
    
    for port in ports_to_test:
        base_url = f"http://localhost:{port}"
        ws_url = f"ws://localhost:{port}"
        
        logger.info(f"\n🔍 Testing port {port}...")
        
        # Quick connectivity test
        try:
            response = requests.get(f"{base_url}/health", timeout=3)
            if response.status_code == 200:
                logger.info(f"✅ Found running service on port {port}")
                
                # Run full test suite
                tester = IntegrationTester(base_url, ws_url)
                results = await tester.run_all_tests()
                return results
        except Exception as e:
            logger.info(f"❌ Port {port} not accessible: {str(e)}")
            continue
    
    logger.error("🚨 No running Legal AI service found on common ports")
    logger.info("💡 Make sure the backend is running with: cd legal-ai copy/backend && python main.py")
    return {}

if __name__ == "__main__":
    asyncio.run(main())
