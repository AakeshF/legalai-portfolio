# offline_config.py - Configuration for fully offline operation
"""
PrivateLegal AI Offline Configuration

This configuration ensures the system operates completely offline with no external API calls.
All AI processing uses local Ollama, all communications are stored locally, and no telemetry
or analytics data leaves the machine.
"""

import os
from pathlib import Path

# Disable all external services
OFFLINE_MODE = True

# AI Configuration - Local Only
AI_CONFIG = {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama3:8b",
    "timeout": 300,
    "fallback_enabled": False,  # No fallback to external APIs
}

# Communication Configuration - Local Only
COMMUNICATION_CONFIG = {
    "email": {
        "enabled": False,  # No external SMTP
        "local_storage": True,
        "storage_path": "./local_emails"
    },
    "calendar": {
        "enabled": False,  # No Google/Microsoft integration
        "local_storage": True,
        "storage_path": "./local_calendar"
    },
    "sms": {
        "enabled": False,  # No Twilio
    },
    "phone": {
        "enabled": False,  # No phone integration
    }
}

# Monitoring Configuration - Local Only
MONITORING_CONFIG = {
    "telemetry_enabled": False,  # No Sentry, Datadog, etc.
    "analytics_enabled": False,  # No external analytics
    "local_logging": True,
    "log_level": "INFO",
    "log_path": "./logs"
}

# Security Configuration
SECURITY_CONFIG = {
    "enforce_local_only": True,
    "block_external_requests": True,
    "allowed_hosts": ["localhost", "127.0.0.1", "0.0.0.0"],
    "require_https": False,  # HTTPS not needed for local-only
}

# Storage Configuration
STORAGE_CONFIG = {
    "documents": "./uploads",
    "database": "sqlite:///./privatelegal.db",
    "backups": "./backups",
    "temp": "./temp"
}

# Feature Flags
FEATURES = {
    "ai_analysis": True,
    "document_upload": True,
    "chat_interface": True,
    "user_management": True,
    "organization_support": True,
    "external_integrations": False,  # Disabled
    "cloud_backup": False,  # Disabled
    "email_notifications": False,  # Disabled
    "sms_alerts": False,  # Disabled
    "oauth_login": False,  # Disabled
}

def ensure_directories():
    """Create necessary directories for offline operation"""
    directories = [
        Path(STORAGE_CONFIG["documents"]),
        Path(STORAGE_CONFIG["backups"]),
        Path(STORAGE_CONFIG["temp"]),
        Path(COMMUNICATION_CONFIG["email"]["storage_path"]),
        Path(COMMUNICATION_CONFIG["calendar"]["storage_path"]),
        Path(MONITORING_CONFIG["log_path"]),
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def validate_offline_config():
    """Validate that system is configured for offline operation"""
    checks = []
    
    # Check Ollama is configured
    if AI_CONFIG["provider"] != "ollama":
        checks.append("AI provider must be 'ollama' for offline operation")
    
    # Check no external services are enabled
    if FEATURES["external_integrations"]:
        checks.append("External integrations must be disabled")
    
    if FEATURES["cloud_backup"]:
        checks.append("Cloud backup must be disabled")
    
    if FEATURES["email_notifications"]:
        checks.append("Email notifications must be disabled")
    
    if FEATURES["oauth_login"]:
        checks.append("OAuth login must be disabled")
    
    # Check monitoring is local only
    if MONITORING_CONFIG["telemetry_enabled"]:
        checks.append("Telemetry must be disabled")
    
    if MONITORING_CONFIG["analytics_enabled"]:
        checks.append("Analytics must be disabled")
    
    return checks

# Initialize directories on import
ensure_directories()

# Validate configuration
validation_errors = validate_offline_config()
if validation_errors:
    print("⚠️  Offline configuration warnings:")
    for error in validation_errors:
        print(f"   - {error}")
else:
    print("✅ System configured for fully offline operation")