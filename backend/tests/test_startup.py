#!/usr/bin/env python3
"""
Simple startup test for the legal AI backend
Tests core functionality without heavy dependencies
"""

import sys
import os
import subprocess
import importlib.util

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import(module_name, description):
    """Test if a module can be imported"""
    print(f"Testing {description}...")
    try:
        __import__(module_name)
        print(f"  ✅ {module_name} - OK")
        return True
    except ImportError as e:
        print(f"  ❌ {module_name} - FAILED: {e}")
        return False
    except Exception as e:
        print(f"  ❌ {module_name} - ERROR: {e}")
        return False

def test_database():
    """Test database connectivity"""
    print("Testing database...")
    try:
        from database import get_db, engine
        from sqlalchemy import text
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("  ✅ Database - OK")
        return True
    except Exception as e:
        print(f"  ❌ Database - FAILED: {e}")
        return False

def test_basic_services():
    """Test basic service imports"""
    print("Testing core services...")
    
    services_to_test = [
        ("auth_utils", "Authentication utilities"),
        ("models", "Database models"),
        ("schemas", "Pydantic schemas"),
        ("config", "Configuration"),
    ]
    
    all_passed = True
    for module, desc in services_to_test:
        if not test_import(module, desc):
            all_passed = False
    
    return all_passed

def test_ai_services():
    """Test AI service imports (may fail due to heavy dependencies)"""
    print("Testing AI services...")
    
    ai_services = [
        ("services.ollama_service", "Ollama service"),
        ("services.hybrid_ai_service", "Hybrid AI service"),
        ("services.document_processor", "Document processor"),
    ]
    
    for module, desc in ai_services:
        test_import(module, desc)

def install_missing_packages():
    """Install basic packages that are definitely needed"""
    print("Installing basic required packages...")
    
    basic_packages = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0", 
        "sqlalchemy==2.0.23",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-multipart==0.0.6",
        "pydantic==2.5.0",
        "httpx==0.25.2",
        "python-dotenv==1.0.0"
    ]
    
    for package in basic_packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✅ {package} installed")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install {package}: {e}")

def main():
    """Run all startup tests"""
    print("🚀 Legal AI Backend Startup Test")
    print("=" * 50)
    
    # Test Python basics
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    # Install basic packages first
    install_missing_packages()
    print()
    
    # Test core imports
    core_passed = test_basic_services()
    print()
    
    # Test database
    db_passed = test_database()
    print()
    
    # Test AI services (optional)
    test_ai_services()
    print()
    
    # Summary
    print("=" * 50)
    if core_passed and db_passed:
        print("✅ BASIC STARTUP: READY")
        print("You can try starting the backend with minimal functionality")
    else:
        print("❌ STARTUP ISSUES DETECTED")
        print("Fix the above errors before proceeding")
    
    print("\nTo start the backend:")
    print("  python test_minimal_server.py")

if __name__ == "__main__":
    main()
